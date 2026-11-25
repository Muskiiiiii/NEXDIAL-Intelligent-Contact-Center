import asyncio
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.campaign import Campaign
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.call import Call
from app.models.safety import SafetyDecision
from app.models.enums import CallState, CallOutcome, AgentStatus, BorrowerStatus, SafetyDecisionType, DialingMode
from app.services.agent_service import AgentService
from app.services.borrower_service import BorrowerService
from app.services.safety_controller import SafetyController
from app.services.pacing_engine import PacingEngine
from app.services.telecom import get_telecom_provider, EventProcessor
from app.core.websocket_manager import ws_manager

logger = logging.getLogger("nexdial.allocator")

class CallAllocator:
    """
    CALL ALLOCATOR
    Executes calls ONLY after explicit approval from the Safety Controller.
    Atomically binds agents and borrowers, dispatches to telecom provider,
    and guarantees atomic rollback if initiation fails.
    """

    @staticmethod
    async def run_allocation_cycle(
        db: AsyncSession,
        campaign: Campaign,
        provider_id: str = "PROVIDER_A",
        risk_factor: float = 0.15,
        worker_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end dialing cycle:
        1. Pacing Engine calculates requested dials.
        2. Safety Controller independently approves, reduces, rejects, or falls back.
        3. If approved > 0, Call Allocator performs atomic reservations and provider dispatch.
        """
        # Step 1: Compute pacing request
        pacing_result = await PacingEngine.compute_dial_request(
            db=db,
            campaign=campaign,
            provider_id=provider_id,
            risk_factor=risk_factor
        )
        requested_count = pacing_result["requested_dial_count"]

        # Step 2: Safety Controller gatekeeping
        safety_decision = await SafetyController.evaluate_dial_request(
            db=db,
            campaign_id=campaign.id,
            requested_calls=requested_count,
            dialing_mode=campaign.dialing_mode,
            provider_id=provider_id,
            predictive_confidence=0.85,
            historical_answer_rate=pacing_result["smoothed_answer_rate"]
        )

        approved_count = safety_decision.approved_calls

        initiated_calls: List[Dict[str, Any]] = []
        aborted_calls: List[str] = []

        if approved_count <= 0:
            return {
                "campaign_id": campaign.id,
                "pacing": pacing_result,
                "safety_decision": safety_decision.to_dict(),
                "initiated_calls": [],
                "message": f"Dialing cycle completed with 0 calls initiated ({safety_decision.reason})"
            }

        provider = get_telecom_provider(provider_id)

        # Step 3: Execute approved calls atomically
        for _ in range(approved_count):
            # 3a. Atomically reserve an agent
            available_agents = await AgentService.get_agents_by_status(db, AgentStatus.AVAILABLE)
            if not available_agents:
                aborted_calls.append("No available agents remained for atomic claim")
                break

            agent_to_reserve = available_agents[0]
            agent_acquired = await AgentService.reserve_agent_atomic(db, agent_to_reserve.id)
            if not agent_acquired:
                # Concurrent worker grabbed agent first
                continue

            # 3b. Atomically reserve an eligible queued borrower
            reserved_borrowers = await BorrowerService.reserve_eligible_borrowers_batch(
                db=db,
                campaign_id=campaign.id,
                limit=1
            )
            if not reserved_borrowers:
                # No eligible borrowers: rollback reserved agent immediately!
                await AgentService.release_agent(db, agent_to_reserve.id, reason="No borrower available, rolling back reservation")
                aborted_calls.append("No queued borrower found, agent released")
                break

            borrower = reserved_borrowers[0]

            # 3c. Create Call record in INITIATED state
            call = Call(
                campaign_id=campaign.id,
                borrower_id=borrower.id,
                agent_id=agent_to_reserve.id,
                provider_id=provider_id,
                worker_id=worker_id,
                call_state=CallState.INITIATED,
                outcome=CallOutcome.PENDING
            )
            db.add(call)
            await db.commit()
            await db.refresh(call)

            # Update agent status to DIALING
            await AgentService.update_agent_status(
                db=db,
                agent_id=agent_to_reserve.id,
                new_status=AgentStatus.DIALING,
                current_call_id=call.id
            )

            # Update borrower status to DIALING
            await BorrowerService.update_borrower_status(
                db=db,
                borrower_id=borrower.id,
                new_status=BorrowerStatus.DIALING
            )

            # 3d. Dispatch to telecom provider
            try:
                provider_response = await provider.initiate_call(
                    call_id=call.id,
                    to_number=borrower.phone_number
                )
                call.provider_call_id = provider_response.get("provider_call_id")
                db.add(call)
                await db.commit()

                # Process initial provider event
                await EventProcessor.process_provider_event(
                    db=db,
                    event_id=provider_response["event_id"],
                    provider_id=provider_id,
                    call_id=call.id,
                    event_type=CallState.INITIATED,
                    payload=provider_response
                )

                initiated_calls.append({
                    "call_id": call.id,
                    "agent_id": agent_to_reserve.id,
                    "borrower_id": borrower.id,
                    "phone": borrower.phone_number,
                    "provider_call_id": call.provider_call_id
                })

            except Exception as e:
                logger.error(f"Telecom provider initiation failed for call {call.id}: {e}")
                # ROLLBACK AND CLEANUP: Never leave agent or borrower orphaned in RESERVED/DIALING
                call.call_state = CallState.FAILED
                call.outcome = CallOutcome.FAILED
                call.error_message = str(e)
                db.add(call)
                await db.commit()

                await AgentService.release_agent(db, agent_to_reserve.id, reason=f"Provider initiation failed: {e}")
                await BorrowerService.release_borrower(db, borrower.id, retry_allowed=True)
                aborted_calls.append(f"Call {call.id} failed provider initiation: {e}")

        return {
            "campaign_id": campaign.id,
            "pacing": pacing_result,
            "safety_decision": safety_decision.to_dict(),
            "initiated_calls": initiated_calls,
            "aborted_calls": aborted_calls,
            "message": f"Successfully initiated {len(initiated_calls)} calls (Approved: {approved_count})"
        }
