import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from app.models.call import Call
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.provider import ProviderEvent
from app.models.audit import AuditLog
from app.models.enums import CallState, CallOutcome, AgentStatus, BorrowerStatus
from app.core.websocket_manager import ws_manager

STATE_RANK = {
    CallState.INITIATED: 1,
    CallState.RINGING: 2,
    CallState.ANSWERED: 3,
    CallState.CONNECTED: 4,
    CallState.COMPLETED: 5,
    CallState.FAILED: 5,
    CallState.CANCELLED: 5,
}

class EventProcessor:
    @staticmethod
    async def process_provider_event(
        db: AsyncSession,
        event_id: str,
        provider_id: str,
        call_id: str,
        event_type: CallState,
        sequence_number: int = 1,
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Idempotent event processing with duplicate detection, sequence tracking,
        and monotonic state machine enforcement.
        """
        # 1. Check if event ID already exists (idempotency check)
        existing_event_stmt = select(ProviderEvent).where(ProviderEvent.id == event_id)
        existing_event = (await db.execute(existing_event_stmt)).scalar_one_or_none()
        if existing_event and existing_event.is_processed:
            # Duplicate event detected!
            return {
                "status": "DUPLICATE_IGNORED",
                "event_id": event_id,
                "call_id": call_id,
                "is_duplicate": True,
                "message": f"Event {event_id} already processed at {existing_event.processed_at}"
            }

        # 2. Fetch call record
        call_stmt = select(Call).where(Call.id == call_id)
        call = (await db.execute(call_stmt)).scalar_one_or_none()
        if not call:
            raise ValueError(f"Call with ID {call_id} not found for event {event_id}")

        # 3. Monotonic state transition validation (prevent regressions)
        current_rank = STATE_RANK.get(call.call_state, 0)
        new_rank = STATE_RANK.get(event_type, 0)

        is_out_of_order = False
        state_applied = False

        if new_rank < current_rank:
            # Out-of-order / late event arrived after call already reached a later state
            is_out_of_order = True
            msg = f"Out-of-order event {event_type.value} received for call {call_id} currently in state {call.call_state.value}. Ignored regression."
        elif new_rank == current_rank and call.call_state == event_type:
            # Repeated state notification
            msg = f"Redundant state notification {event_type.value} for call {call_id}."
        else:
            # Valid state advance!
            state_applied = True
            old_state = call.call_state
            call.call_state = event_type
            now = datetime.datetime.now(datetime.timezone.utc)

            if event_type == CallState.RINGING:
                call.ringing_at = now
                if call.initiated_at:
                    init_dt = call.initiated_at if call.initiated_at.tzinfo else call.initiated_at.replace(tzinfo=datetime.timezone.utc)
                    call.ring_time_seconds = max(0.0, (now - init_dt).total_seconds())

            elif event_type == CallState.ANSWERED:
                call.answered_at = now

            elif event_type == CallState.CONNECTED:
                call.connected_at = now
                # Ensure agent and borrower are updated to CONNECTED
                if call.agent_id:
                    agent_stmt = select(Agent).where(Agent.id == call.agent_id)
                    agent = (await db.execute(agent_stmt)).scalar_one_or_none()
                    if agent and agent.status != AgentStatus.CONNECTED:
                        agent.status = AgentStatus.CONNECTED
                        agent.current_call_id = call.id
                        agent.total_calls += 1
                        db.add(agent)

                borrower_stmt = select(Borrower).where(Borrower.id == call.borrower_id)
                borrower = (await db.execute(borrower_stmt)).scalar_one_or_none()
                if borrower and borrower.status != BorrowerStatus.CONNECTED:
                    borrower.status = BorrowerStatus.CONNECTED
                    db.add(borrower)

            elif event_type in (CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED):
                call.ended_at = now
                if call.connected_at:
                    conn_dt = call.connected_at if call.connected_at.tzinfo else call.connected_at.replace(tzinfo=datetime.timezone.utc)
                    call.talk_time_seconds = max(0.0, (now - conn_dt).total_seconds())
                if call.initiated_at:
                    init_dt = call.initiated_at if call.initiated_at.tzinfo else call.initiated_at.replace(tzinfo=datetime.timezone.utc)
                    call.total_duration_seconds = max(0.0, (now - init_dt).total_seconds())

                if event_type == CallState.COMPLETED:
                    call.outcome = CallOutcome.SUCCESS
                elif event_type == CallState.FAILED:
                    call.outcome = CallOutcome.FAILED
                elif event_type == CallState.CANCELLED:
                    call.outcome = CallOutcome.CANCELLED

                # Clean up / release agent
                if call.agent_id:
                    agent_stmt = select(Agent).where(Agent.id == call.agent_id)
                    agent = (await db.execute(agent_stmt)).scalar_one_or_none()
                    if agent:
                        agent.status = AgentStatus.AVAILABLE
                        agent.current_call_id = None
                        agent.total_talk_time_seconds += call.talk_time_seconds
                        if agent.total_calls > 0:
                            agent.average_talk_time = agent.total_talk_time_seconds / agent.total_calls
                        agent.last_status_change = now
                        db.add(agent)

                # Update borrower
                borrower_stmt = select(Borrower).where(Borrower.id == call.borrower_id)
                borrower = (await db.execute(borrower_stmt)).scalar_one_or_none()
                if borrower:
                    if event_type == CallState.COMPLETED:
                        borrower.status = BorrowerStatus.COMPLETED
                    else:
                        if borrower.attempt_count < borrower.max_attempts:
                            borrower.status = BorrowerStatus.QUEUED
                        else:
                            borrower.status = BorrowerStatus.FAILED
                    db.add(borrower)

            db.add(call)
            msg = f"Call {call_id} transitioned from {old_state.value} to {event_type.value}"

        # 4. Durably persist event record
        provider_event = ProviderEvent(
            id=event_id,
            provider_id=provider_id,
            call_id=call_id,
            event_type=event_type,
            sequence_number=sequence_number,
            payload=payload,
            is_processed=True,
            is_duplicate=False,
            is_out_of_order=is_out_of_order,
            processed_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(provider_event)

        # 5. Audit log
        audit = AuditLog(
            event_type="PROVIDER_EVENT_PROCESSED",
            entity_type="Call",
            entity_id=call_id,
            message=msg,
            metadata_json={
                "event_id": event_id,
                "event_type": event_type.value,
                "is_out_of_order": is_out_of_order,
                "state_applied": state_applied
            }
        )
        db.add(audit)
        await db.commit()
        await db.refresh(call)

        # Broadcast update
        await ws_manager.broadcast("CALL_UPDATED", call.to_dict())
        await ws_manager.broadcast("PROVIDER_EVENT", provider_event.to_dict())

        return {
            "status": "PROCESSED",
            "event_id": event_id,
            "call_id": call_id,
            "state_applied": state_applied,
            "is_out_of_order": is_out_of_order,
            "call_state": call.call_state.value
        }
