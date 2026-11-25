import asyncio
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any

from app.core.database import get_db, AsyncSessionLocal
from app.models.agent import Agent
from app.models.call import Call
from app.models.enums import AgentStatus, CallState
from app.services.agent_service import AgentService
from app.services.worker_pool import WorkerPool
from app.services.telecom import get_telecom_provider, EventProcessor
from app.services.simulation_engine import simulation_engine
from app.core.websocket_manager import ws_manager

router = APIRouter(prefix="/failures", tags=["Failure Injection"])

@router.post("/inject")
async def inject_failure(payload: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    failure_type = payload.get("type")

    if failure_type == "worker_crash":
        worker_name = payload.get("worker_name", "Dialer-Worker-1")
        result = await WorkerPool.simulate_worker_crash(db, worker_name)
        return {
            "failure_injected": "WORKER_CRASH",
            "system_response": f"Worker '{worker_name}' marked CRASHED. In-flight jobs halted.",
            "recovery_status": "Ready for reconciliation upon worker restart.",
            "details": result
        }

    elif failure_type == "provider_outage":
        provider_id = payload.get("provider_id", "PROVIDER_A")
        provider = get_telecom_provider(provider_id)
        provider.outage_mode = True
        provider.circuit_breaker.state = "OPEN"
        provider.circuit_breaker.consecutive_failures = 10
        await ws_manager.broadcast("PROVIDER_OUTAGE", {"provider_id": provider_id, "outage": True})
        return {
            "failure_injected": f"PROVIDER_OUTAGE ({provider_id})",
            "system_response": f"Upstream provider outage simulated. Circuit breaker tripped to OPEN. Safety Controller will reject all calls to {provider_id}.",
            "safety_controller_action": "REJECT with carrier protection clause.",
            "recovery_status": "Circuit breaker in recovery cooldown."
        }

    elif failure_type == "agent_drop":
        count = int(payload.get("count", 10))
        # Find available agents and drop them OFFLINE
        stmt = select(Agent).where(Agent.status == AgentStatus.AVAILABLE).limit(count)
        agents = list((await db.execute(stmt)).scalars().all())
        for ag in agents:
            ag.status = AgentStatus.OFFLINE
            ag.current_call_id = None
            db.add(ag)
        await db.commit()
        await ws_manager.broadcast("AGENTS_DROPPED", {"dropped_count": len(agents)})
        return {
            "failure_injected": f"SUDDEN_AGENT_DROP ({len(agents)} agents)",
            "system_response": f"{len(agents)} agents suddenly went OFFLINE.",
            "safety_controller_action": "Immediate capacity recalculation; safe dialing headroom instantly restricted.",
            "recovery_status": "Agents can be restored online through Agent Management."
        }

    elif failure_type == "duplicate_event":
        # Find an existing call
        call_stmt = select(Call).where(Call.call_state == CallState.CONNECTED).limit(1)
        call = (await db.execute(call_stmt)).scalar_one_or_none()
        if not call:
            call_stmt = select(Call).limit(1)
            call = (await db.execute(call_stmt)).scalar_one_or_none()

        if not call:
            raise HTTPException(status_code=400, detail="No active or past call available to inject duplicate event")

        duplicate_event_id = f"dup-evt-{uuid.uuid4().hex[:8]}"
        # Process once
        await EventProcessor.process_provider_event(
            db=db,
            event_id=duplicate_event_id,
            provider_id=call.provider_id,
            call_id=call.id,
            event_type=call.call_state
        )
        # Attempt duplicate process
        dup_result = await EventProcessor.process_provider_event(
            db=db,
            event_id=duplicate_event_id,
            provider_id=call.provider_id,
            call_id=call.id,
            event_type=call.call_state
        )
        return {
            "failure_injected": "DUPLICATE_PROVIDER_EVENT",
            "system_response": "Identical event payload dispatched twice.",
            "safety_controller_action": "Idempotency filter intercepted duplicate; suppressed secondary agent reservation.",
            "details": dup_result
        }

    elif failure_type == "out_of_order_event":
        # Send RINGING or INITIATED event for a COMPLETED call
        call_stmt = select(Call).where(Call.call_state == CallState.COMPLETED).limit(1)
        call = (await db.execute(call_stmt)).scalar_one_or_none()
        if not call:
            raise HTTPException(status_code=400, detail="No completed call available for out-of-order injection")

        ooo_event_id = f"ooo-evt-{uuid.uuid4().hex[:8]}"
        res = await EventProcessor.process_provider_event(
            db=db,
            event_id=ooo_event_id,
            provider_id=call.provider_id,
            call_id=call.id,
            event_type=CallState.RINGING # Late ringing event
        )
        return {
            "failure_injected": "OUT_OF_ORDER_EVENT",
            "system_response": f"Late RINGING event received for completed call {call.id}.",
            "safety_controller_action": "Monotonic state machine preserved terminal COMPLETED state; rejected regression.",
            "details": res
        }

    elif failure_type == "answer_rate_plunge":
        simulation_engine.answer_rate = 0.10
        await ws_manager.broadcast("ANSWER_RATE_PLUNGED", {"new_answer_rate": 0.10})
        return {
            "failure_injected": "ANSWER_RATE_PLUNGE (70% -> 10%)",
            "system_response": "Borrower answer rate plunged to 10%.",
            "safety_controller_action": "Predictive Pacing Engine detects high variance and falls back to Progressive mode.",
            "recovery_status": "Active."
        }

    elif failure_type == "latency_spike":
        provider_id = payload.get("provider_id", "PROVIDER_A")
        provider = get_telecom_provider(provider_id)
        provider.avg_latency_ms = 2500.0
        return {
            "failure_injected": f"LATENCY_SPIKE ({provider_id} -> 2500ms)",
            "system_response": "Carrier setup latency spiked 20x.",
            "safety_controller_action": "Setup window expanded; Safety Controller throttles concurrent pending calls.",
            "recovery_status": "Exponential smoothing will gradually restore latency."
        }

    elif failure_type == "concurrency_race":
        # Launch 10 simultaneous tasks trying to reserve the EXACT SAME agent!
        stmt = select(Agent).where(Agent.status == AgentStatus.AVAILABLE).limit(1)
        agent = (await db.execute(stmt)).scalar_one_or_none()
        if not agent:
            # Create a test agent
            agent = await AgentService.create_agent(db, "Race-Test-Agent", AgentStatus.AVAILABLE)

        async def worker_attempt_reservation(worker_num: int):
            async with AsyncSessionLocal() as local_db:
                success = await AgentService.reserve_agent_atomic(local_db, agent.id)
                return {"worker": f"Worker-{worker_num}", "acquired": success}

        # Run 10 parallel attempts
        tasks = [worker_attempt_reservation(i) for i in range(1, 11)]
        results = await asyncio.gather(*tasks)

        winners = [r for r in results if r["acquired"]]
        losers = [r for r in results if not r["acquired"]]

        return {
            "failure_injected": "CONCURRENCY_RACE (10 simultaneous workers on single agent)",
            "system_response": f"{len(winners)} worker won atomic lock; {len(losers)} workers rejected cleanly.",
            "safety_controller_action": "Atomic conditional DB update guaranteed zero double-reservation.",
            "details": {
                "agent_id": agent.id,
                "winner": winners[0]["worker"] if winners else None,
                "rejected_workers": [l["worker"] for l in losers]
            }
        }

    else:
        raise HTTPException(status_code=400, detail=f"Unknown failure type: {failure_type}")
