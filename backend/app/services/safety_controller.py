from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import datetime

from app.models.agent import Agent
from app.models.call import Call
from app.models.safety import SafetyDecision
from app.models.enums import AgentStatus, CallState, SafetyDecisionType, DialingMode
from app.services.telecom import get_telecom_provider
from app.core.websocket_manager import ws_manager

class SafetyController:
    """
    INDEPENDENT SAFETY CONTROLLER
    Central authority governing all call initiation.
    Predictive pacing and campaign managers must submit requests here.
    No call can be initiated without Safety Controller authorization.
    """

    @staticmethod
    async def get_system_capacity_snapshot(db: AsyncSession) -> Dict[str, Any]:
        """
        Query current agent, call, and system states directly from the database.
        """
        # Count agent distribution
        stmt = select(Agent.status, func.count(Agent.id)).group_by(Agent.status)
        agent_counts = dict((await db.execute(stmt)).all())

        available_agents = agent_counts.get(AgentStatus.AVAILABLE, 0)
        reserved_agents = agent_counts.get(AgentStatus.RESERVED, 0)
        dialing_agents = agent_counts.get(AgentStatus.DIALING, 0)
        connected_agents = agent_counts.get(AgentStatus.CONNECTED, 0)
        total_agents = sum(agent_counts.values())

        # Count in-flight calls
        call_stmt = select(Call.call_state, func.count(Call.id)).where(
            Call.call_state.in_([CallState.INITIATED, CallState.RINGING, CallState.CONNECTED])
        ).group_by(Call.call_state)
        call_counts = dict((await db.execute(call_stmt)).all())

        initiated_calls = call_counts.get(CallState.INITIATED, 0)
        ringing_calls = call_counts.get(CallState.RINGING, 0)
        connected_calls = call_counts.get(CallState.CONNECTED, 0)

        # In-flight calls without connected conversation
        in_flight_pending = reserved_agents + dialing_agents + initiated_calls + ringing_calls

        # Conservative safe capacity: available agents minus all pending reservations/setup calls
        safe_capacity = max(0, available_agents - in_flight_pending)

        return {
            "total_agents": total_agents,
            "available_agents": available_agents,
            "reserved_agents": reserved_agents,
            "dialing_agents": dialing_agents,
            "connected_agents": connected_agents,
            "initiated_calls": initiated_calls,
            "ringing_calls": ringing_calls,
            "connected_calls": connected_calls,
            "in_flight_pending": in_flight_pending,
            "safe_capacity": safe_capacity
        }

    @staticmethod
    async def evaluate_dial_request(
        db: AsyncSession,
        campaign_id: str,
        requested_calls: int,
        dialing_mode: DialingMode,
        provider_id: str = "PROVIDER_A",
        predictive_confidence: float = 1.0,
        historical_answer_rate: float = 0.5
    ) -> SafetyDecision:
        """
        Independently evaluate whether requested calls can safely proceed.
        Returns immutable SafetyDecision committed to the database.
        """
        # 1. Fetch capacity snapshot directly from the DB
        cap = await SafetyController.get_system_capacity_snapshot(db)

        # 2. Fetch provider health & circuit status
        provider = get_telecom_provider(provider_id)
        provider_health = provider.get_health()
        provider_health_score = provider_health.get("health_score", 1.0)
        circuit_state = provider_health.get("circuit_breaker", {}).get("state", "CLOSED")

        safe_capacity = cap["safe_capacity"]
        available_agents = cap["available_agents"]
        ringing_calls = cap["ringing_calls"]
        reserved_agents = cap["reserved_agents"]
        active_calls = cap["connected_calls"]

        decision_type: SafetyDecisionType
        approved_calls: int = 0
        rejected_calls: int = requested_calls
        reason: str = ""

        # Constraint 1: Provider Circuit Breaker / Outage
        if circuit_state == "OPEN" or provider_health_score < 0.2:
            decision_type = SafetyDecisionType.REJECT
            approved_calls = 0
            rejected_calls = requested_calls
            reason = f"Provider {provider_id} circuit breaker is {circuit_state} (health score: {provider_health_score}). Calls rejected for carrier protection."

        # Constraint 2: Zero or negative requested calls
        elif requested_calls <= 0:
            decision_type = SafetyDecisionType.REJECT
            approved_calls = 0
            rejected_calls = 0
            reason = "Pacing engine requested 0 dials."

        # Constraint 3: Zero available agent capacity
        elif available_agents == 0:
            decision_type = SafetyDecisionType.REJECT
            approved_calls = 0
            rejected_calls = requested_calls
            reason = f"Zero agents available ({cap['total_agents']} total, {active_calls} connected, {cap['in_flight_pending']} in-flight). Dialing forbidden."

        # Constraint 4: Predictive confidence low or high variance -> Fallback to Progressive
        elif dialing_mode == DialingMode.PREDICTIVE and (predictive_confidence < 0.4 or historical_answer_rate < 0.10):
            decision_type = SafetyDecisionType.FALLBACK_TO_PROGRESSIVE
            # In progressive fallback, strictly 1 call per available unreserved agent
            progressive_allowance = max(0, available_agents - cap["in_flight_pending"])
            approved_calls = min(requested_calls, progressive_allowance)
            rejected_calls = max(0, requested_calls - approved_calls)
            reason = f"Predictive confidence degraded (confidence: {predictive_confidence:.2f}, answer rate: {historical_answer_rate:.1%}). Automatically fallen back to Progressive mode."

        # Constraint 5: Full approval within safe capacity
        elif requested_calls <= safe_capacity:
            decision_type = SafetyDecisionType.APPROVE
            approved_calls = requested_calls
            rejected_calls = 0
            reason = f"Approved all {requested_calls} requested calls. Agent capacity ({available_agents}) safely accommodates in-flight ({cap['in_flight_pending']}) and new dials."

        # Constraint 6: Request exceeds safe capacity -> REDUCE to exact safe capacity
        elif safe_capacity > 0:
            decision_type = SafetyDecisionType.REDUCE
            approved_calls = safe_capacity
            rejected_calls = requested_calls - approved_calls
            reason = f"Requested {requested_calls} calls, but available agent capacity ({available_agents}) and pending in-flight calls ({cap['in_flight_pending']}) limit safe dialing to {safe_capacity}. Reduced by {rejected_calls}."

        # Constraint 7: Pending calls consume entire available headroom -> REJECT
        else:
            decision_type = SafetyDecisionType.REJECT
            approved_calls = 0
            rejected_calls = requested_calls
            reason = f"Rejected {requested_calls} calls. Existing pending calls ({cap['in_flight_pending']}: {reserved_agents} reserved, {ringing_calls} ringing) exhaust available capacity ({available_agents})."

        # 3. Create immutable audit record
        decision = SafetyDecision(
            campaign_id=campaign_id,
            decision=decision_type,
            requested_calls=requested_calls,
            approved_calls=approved_calls,
            rejected_calls=rejected_calls,
            available_agents=available_agents,
            reserved_agents=reserved_agents,
            ringing_calls=ringing_calls,
            active_calls=active_calls,
            provider_health_score=provider_health_score,
            reason=reason,
            capacity_snapshot=cap,
            provider_health_snapshot=provider_health
        )
        db.add(decision)
        await db.commit()
        await db.refresh(decision)

        # 4. Broadcast decision over WebSocket
        await ws_manager.broadcast("SAFETY_DECISION", decision.to_dict())

        return decision
