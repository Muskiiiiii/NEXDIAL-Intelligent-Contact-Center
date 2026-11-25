import asyncio
import datetime
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_

from app.models.worker import Worker
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.audit import AuditLog
from app.models.enums import WorkerStatus, AgentStatus, BorrowerStatus, CallState, CallOutcome
from app.services.telecom import get_telecom_provider
from app.core.websocket_manager import ws_manager

logger = logging.getLogger("nexdial.workers")

class WorkerPool:
    """
    DISTRIBUTED WORKER POOL & STALE RESERVATION RECONCILER
    Manages concurrent dialing workers, lease tracking, simulated worker crashes,
    and safe idempotent recovery without duplicate call dispatch.
    """

    @staticmethod
    async def initialize_workers(db: AsyncSession, worker_count: int = 3) -> List[Worker]:
        """Ensure standard workers exist in the database."""
        workers = []
        for i in range(1, worker_count + 1):
            name = f"Dialer-Worker-{i}"
            stmt = select(Worker).where(Worker.worker_name == name)
            worker = (await db.execute(stmt)).scalar_one_or_none()
            if not worker:
                worker = Worker(worker_name=name, status=WorkerStatus.IDLE)
                db.add(worker)
            workers.append(worker)
        await db.commit()
        return workers

    @staticmethod
    async def get_all_workers(db: AsyncSession) -> List[Worker]:
        stmt = select(Worker).order_by(Worker.worker_name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def heartbeat(db: AsyncSession, worker_name: str) -> Optional[Worker]:
        stmt = select(Worker).where(Worker.worker_name == worker_name)
        worker = (await db.execute(stmt)).scalar_one_or_none()
        if worker and worker.status != WorkerStatus.CRASHED:
            worker.last_heartbeat = func.now()
            db.add(worker)
            await db.commit()
            await db.refresh(worker)
        return worker

    @staticmethod
    async def simulate_worker_crash(db: AsyncSession, worker_name: str) -> Dict[str, Any]:
        """
        Simulate a sudden worker crash while processing.
        Leaves in-flight reservations orphaned until recovery kicks in.
        """
        stmt = select(Worker).where(Worker.worker_name == worker_name)
        worker = (await db.execute(stmt)).scalar_one_or_none()
        if not worker:
            raise ValueError(f"Worker {worker_name} not found")

        worker.status = WorkerStatus.CRASHED
        worker.jobs_failed += 1
        db.add(worker)

        audit = AuditLog(
            event_type="WORKER_CRASHED",
            entity_type="Worker",
            entity_id=worker.id,
            message=f"SIMULATED CRASH: Worker '{worker_name}' terminated abruptly.",
            metadata_json={"active_job_id": worker.active_job_id}
        )
        db.add(audit)
        await db.commit()
        await db.refresh(worker)

        await ws_manager.broadcast("WORKER_UPDATED", worker.to_dict())
        return {
            "status": "CRASHED",
            "worker_name": worker_name,
            "message": f"Worker '{worker_name}' crashed. Active job was {worker.active_job_id}."
        }

    @staticmethod
    async def recover_worker_and_reconcile(
        db: AsyncSession,
        worker_name: str,
        stale_threshold_seconds: float = 15.0
    ) -> Dict[str, Any]:
        """
        Recover crashed worker and reconcile orphaned calls, agents, and borrowers:
        1. Identifies calls owned by that worker using durable worker/job ownership.
        2. Inspects persisted call state and carrier initiation status.
        3. Reconciles with carrier provider:
           - Never initiated -> FAILED with WORKER_CRASH_ORPHANED, agent released to AVAILABLE.
           - Active (RINGING/CONNECTED) -> preserved, agent remains assigned.
           - Completed/Failed on carrier -> finalized, agent released to AVAILABLE.
           - Provider unreachable -> resources protected (reconciliation deferred).
        4. Reconciles any remaining orphaned reservations.
        5. Restores safe dialing capacity calculation without counting resolved orphans.
        6. Ensures idempotency and records audit logs.
        """
        stmt = select(Worker).where(Worker.worker_name == worker_name)
        worker = (await db.execute(stmt)).scalar_one_or_none()
        if not worker:
            raise ValueError(f"Worker {worker_name} not found")

        # Idempotent state transition
        was_crashed = (worker.status == WorkerStatus.CRASHED)
        if was_crashed:
            worker.status = WorkerStatus.IDLE
            worker.jobs_recovered += 1

        active_job = worker.active_job_id
        worker.active_job_id = None
        worker.last_heartbeat = func.now()
        db.add(worker)

        stale_threshold = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=stale_threshold_seconds)

        # 1. Identify all candidate calls owned by this worker, active job, or associated with stale agents
        call_conditions = [
            and_(
                Call.worker_id == worker.id,
                Call.call_state.in_([CallState.INITIATED, CallState.RINGING, CallState.ANSWERED, CallState.CONNECTED])
            )
        ]
        if active_job:
            call_conditions.append(
                and_(
                    or_(Call.id == active_job, Call.job_id == active_job),
                    Call.call_state.in_([CallState.INITIATED, CallState.RINGING, CallState.ANSWERED, CallState.CONNECTED])
                )
            )

        # Stale agents in RESERVED/DIALING with a call
        stale_agent_calls_subq = (
            select(Agent.current_call_id)
            .where(
                Agent.status.in_([AgentStatus.RESERVED, AgentStatus.DIALING]),
                Agent.last_status_change < stale_threshold,
                Agent.current_call_id.isnot(None)
            )
        )
        call_conditions.append(
            and_(
                Call.id.in_(stale_agent_calls_subq),
                Call.call_state.in_([CallState.INITIATED, CallState.RINGING, CallState.ANSWERED])
            )
        )

        # Calls in INITIATED with no provider_call_id older than threshold
        call_conditions.append(
            and_(
                Call.call_state == CallState.INITIATED,
                Call.provider_call_id.is_(None),
                Call.created_at < stale_threshold
            )
        )

        candidate_calls_stmt = select(Call).where(or_(*call_conditions))
        candidate_calls = list((await db.execute(candidate_calls_stmt)).scalars().all())

        orphaned_calls_failed = 0
        active_calls_preserved = 0
        completed_calls_reconciled = 0
        deferred_calls = 0
        reconciled_agents = 0
        reconciled_borrowers = 0

        preserved_agent_ids = set()
        preserved_borrower_ids = set()
        preserved_call_ids = set()

        # 2. Reconcile each call
        for call in candidate_calls:
            # Monotonic terminal state protection: Never touch already completed/failed calls
            if call.call_state in (CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED):
                continue

            provider = get_telecom_provider(call.provider_id or "PROVIDER_A")
            provider_status: Dict[str, Any] = {}
            try:
                provider_status = await provider.query_call_status(call.id, call.provider_call_id)
            except Exception as e:
                logger.warning(f"Error querying provider {call.provider_id} for call {call.id}: {e}")
                provider_status = {"status": "UNKNOWN", "error": str(e)}

            status_str = provider_status.get("status", "UNKNOWN")

            # Condition A: Call never reached carrier
            is_never_initiated = (call.provider_call_id is None) or (status_str == "NOT_FOUND" and not provider_status.get("initiated", False))

            if is_never_initiated:
                call.call_state = CallState.FAILED
                call.outcome = CallOutcome.WORKER_CRASH_ORPHANED
                call.error_message = f"Worker '{worker_name}' crashed before carrier dispatch completed"
                call.ended_at = datetime.datetime.now(datetime.timezone.utc)
                db.add(call)
                orphaned_calls_failed += 1

                # Safely release assigned agent
                if call.agent_id:
                    agent = (await db.execute(select(Agent).where(Agent.id == call.agent_id))).scalar_one_or_none()
                    if agent and agent.status in (AgentStatus.RESERVED, AgentStatus.DIALING):
                        agent.status = AgentStatus.AVAILABLE
                        agent.current_call_id = None
                        agent.last_status_change = func.now()
                        db.add(agent)
                        reconciled_agents += 1

                # Safely release assigned borrower
                if call.borrower_id:
                    borrower = (await db.execute(select(Borrower).where(Borrower.id == call.borrower_id))).scalar_one_or_none()
                    if borrower and borrower.status in (BorrowerStatus.RESERVED, BorrowerStatus.DIALING):
                        if borrower.attempt_count < borrower.max_attempts:
                            borrower.status = BorrowerStatus.QUEUED
                        else:
                            borrower.status = BorrowerStatus.FAILED
                        db.add(borrower)
                        reconciled_borrowers += 1

                audit = AuditLog(
                    event_type="CALL_ORPHAN_FAILED",
                    entity_type="Call",
                    entity_id=call.id,
                    message=f"Call {call.id} confirmed uninitiated during worker '{worker_name}' recovery. Marked FAILED ({CallOutcome.WORKER_CRASH_ORPHANED.value}) and resources safely released.",
                    metadata_json={"worker_name": worker_name, "call_id": call.id}
                )
                db.add(audit)

            # Condition B: Provider confirms call is ACTIVE (RINGING or CONNECTED)
            elif status_str == "ACTIVE":
                prov_state = provider_status.get("call_state", "CONNECTED")
                now_utc = datetime.datetime.now(datetime.timezone.utc)

                preserved_call_ids.add(call.id)
                if call.agent_id:
                    preserved_agent_ids.add(call.agent_id)
                if call.borrower_id:
                    preserved_borrower_ids.add(call.borrower_id)

                if prov_state in ("CONNECTED", "ANSWERED"):
                    call.call_state = CallState.CONNECTED
                    if not call.connected_at:
                        call.connected_at = now_utc
                    if call.agent_id:
                        agent = (await db.execute(select(Agent).where(Agent.id == call.agent_id))).scalar_one_or_none()
                        if agent and agent.status != AgentStatus.CONNECTED:
                            agent.status = AgentStatus.CONNECTED
                            agent.current_call_id = call.id
                            db.add(agent)
                    if call.borrower_id:
                        borrower = (await db.execute(select(Borrower).where(Borrower.id == call.borrower_id))).scalar_one_or_none()
                        if borrower and borrower.status != BorrowerStatus.CONNECTED:
                            borrower.status = BorrowerStatus.CONNECTED
                            db.add(borrower)
                elif prov_state == "RINGING":
                    call.call_state = CallState.RINGING
                    if not call.ringing_at:
                        call.ringing_at = now_utc
                    if call.agent_id:
                        agent = (await db.execute(select(Agent).where(Agent.id == call.agent_id))).scalar_one_or_none()
                        if agent:
                            agent.status = AgentStatus.DIALING
                            agent.current_call_id = call.id
                            db.add(agent)
                    if call.borrower_id:
                        borrower = (await db.execute(select(Borrower).where(Borrower.id == call.borrower_id))).scalar_one_or_none()
                        if borrower:
                            borrower.status = BorrowerStatus.DIALING
                            db.add(borrower)

                db.add(call)
                active_calls_preserved += 1

                audit = AuditLog(
                    event_type="CALL_PRESERVED_ACTIVE",
                    entity_type="Call",
                    entity_id=call.id,
                    message=f"Call {call.id} confirmed active ({prov_state}) on carrier during worker '{worker_name}' recovery. Preserved call and agent assignment.",
                    metadata_json={"worker_name": worker_name, "call_state": prov_state}
                )
                db.add(audit)

            # Condition C: Provider confirms call has TERMINATED on carrier
            elif status_str in ("COMPLETED", "FAILED"):
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                call.call_state = CallState.COMPLETED if status_str == "COMPLETED" else CallState.FAILED
                call.outcome = CallOutcome.SUCCESS if status_str == "COMPLETED" else CallOutcome.FAILED
                call.ended_at = now_utc
                db.add(call)
                completed_calls_reconciled += 1

                if call.agent_id:
                    agent = (await db.execute(select(Agent).where(Agent.id == call.agent_id))).scalar_one_or_none()
                    if agent:
                        agent.status = AgentStatus.AVAILABLE
                        agent.current_call_id = None
                        agent.last_status_change = func.now()
                        db.add(agent)
                        reconciled_agents += 1

                if call.borrower_id:
                    borrower = (await db.execute(select(Borrower).where(Borrower.id == call.borrower_id))).scalar_one_or_none()
                    if borrower:
                        if status_str == "COMPLETED":
                            borrower.status = BorrowerStatus.COMPLETED
                        else:
                            borrower.status = BorrowerStatus.QUEUED if borrower.attempt_count < borrower.max_attempts else BorrowerStatus.FAILED
                        db.add(borrower)
                        reconciled_borrowers += 1

                audit = AuditLog(
                    event_type="CALL_RECONCILED_TERMINATED",
                    entity_type="Call",
                    entity_id=call.id,
                    message=f"Call {call.id} confirmed terminated ({status_str}) on carrier. Resources released to AVAILABLE/QUEUED.",
                    metadata_json={"worker_name": worker_name, "call_outcome": call.outcome.value}
                )
                db.add(audit)

            # Condition D: Provider is UNREACHABLE / status UNKNOWN
            elif status_str == "UNKNOWN":
                # Defensive distributed systems principle:
                # Do NOT blindly release agent or borrower when carrier state is unconfirmed.
                # Keep them protected in current state to prevent double allocation.
                deferred_calls += 1
                call.error_message = "Reconciliation deferred: carrier status unknown"
                db.add(call)

                preserved_call_ids.add(call.id)
                if call.agent_id:
                    preserved_agent_ids.add(call.agent_id)
                if call.borrower_id:
                    preserved_borrower_ids.add(call.borrower_id)

                audit = AuditLog(
                    event_type="RECONCILIATION_DEFERRED",
                    entity_type="Call",
                    entity_id=call.id,
                    message=f"Carrier {call.provider_id} unreachable during recovery of worker '{worker_name}'. Call {call.id} and agent {call.agent_id} kept protected.",
                    metadata_json={"worker_name": worker_name, "call_id": call.id, "error": provider_status.get("error")}
                )
                db.add(audit)

        # Flush session so all call/agent updates are visible to subsequent queries
        await db.flush()

        # 3. Reconcile any remaining stale agents stuck with no active in-flight call
        stale_agents_stmt = select(Agent).where(
            Agent.status.in_([AgentStatus.RESERVED, AgentStatus.DIALING]),
            Agent.last_status_change < stale_threshold
        )
        stale_agents = list((await db.execute(stale_agents_stmt)).scalars().all())
        for ag in stale_agents:
            if ag.id in preserved_agent_ids or ag.current_call_id in preserved_call_ids:
                continue

            # If agent has a call, check if it's currently active
            if ag.current_call_id:
                c_stmt = select(Call).where(Call.id == ag.current_call_id)
                c = (await db.execute(c_stmt)).scalar_one_or_none()
                if c and c.call_state in (CallState.RINGING, CallState.CONNECTED):
                    # Real active conversation: do NOT release!
                    continue
                if c and c.call_state == CallState.INITIATED and deferred_calls > 0:
                    # Might be part of deferred reconciliation
                    continue

            ag.status = AgentStatus.AVAILABLE
            ag.current_call_id = None
            ag.last_status_change = func.now()
            db.add(ag)
            reconciled_agents += 1

        # 4. Reconcile any remaining stale borrowers stuck with no active in-flight call
        stale_borrowers_stmt = select(Borrower).where(
            Borrower.status.in_([BorrowerStatus.RESERVED, BorrowerStatus.DIALING]),
            Borrower.last_attempted_at < stale_threshold
        )
        stale_borrowers = list((await db.execute(stale_borrowers_stmt)).scalars().all())
        for b in stale_borrowers:
            if b.id in preserved_borrower_ids:
                continue

            b_call_stmt = select(Call).where(
                Call.borrower_id == b.id,
                Call.call_state.in_([CallState.RINGING, CallState.CONNECTED])
            )
            b_call = (await db.execute(b_call_stmt)).scalar_one_or_none()
            if b_call:
                # Real active conversation: do NOT release!
                continue

            if b.attempt_count < b.max_attempts:
                b.status = BorrowerStatus.QUEUED
            else:
                b.status = BorrowerStatus.FAILED
            db.add(b)
            reconciled_borrowers += 1
            db.add(b)
            reconciled_borrowers += 1

        # 5. Commit audit and broadcast
        audit = AuditLog(
            event_type="WORKER_RECOVERED",
            entity_type="Worker",
            entity_id=worker.id,
            message=(
                f"Worker '{worker_name}' recovery complete: "
                f"{orphaned_calls_failed} uninitiated calls failed, "
                f"{active_calls_preserved} active calls preserved, "
                f"{completed_calls_reconciled} carrier-completed calls finalized, "
                f"{deferred_calls} calls deferred (carrier unreachable), "
                f"{reconciled_agents} agents restored, "
                f"{reconciled_borrowers} borrowers restored."
            ),
            metadata_json={
                "orphaned_calls_failed": orphaned_calls_failed,
                "active_calls_preserved": active_calls_preserved,
                "completed_calls_reconciled": completed_calls_reconciled,
                "deferred_calls": deferred_calls,
                "reconciled_agents": reconciled_agents,
                "reconciled_borrowers": reconciled_borrowers,
                "previous_job": active_job
            }
        )
        db.add(audit)
        await db.commit()
        await db.refresh(worker)

        await ws_manager.broadcast("WORKER_UPDATED", worker.to_dict())

        return {
            "status": "RECOVERED",
            "worker_name": worker_name,
            "orphaned_calls_failed": orphaned_calls_failed,
            "active_calls_preserved": active_calls_preserved,
            "completed_calls_reconciled": completed_calls_reconciled,
            "deferred_calls": deferred_calls,
            "reconciled_agents": reconciled_agents,
            "reconciled_borrowers": reconciled_borrowers,
            "message": (
                f"Worker '{worker_name}' restored to IDLE. Reconciled {orphaned_calls_failed} uninitiated calls, "
                f"preserved {active_calls_preserved} active calls, restored {reconciled_agents} agents and {reconciled_borrowers} borrowers."
            )
        }
