import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.agent import Agent
from app.models.call import Call
from app.models.borrower import Borrower
from app.models.audit import AuditLog
from app.models.safety import SafetyDecision
from app.models.enums import AgentStatus, CallState, CallOutcome
from app.services.telecom import get_telecom_provider

class AnalyticsService:
    @staticmethod
    async def get_overview_kpis(db: AsyncSession) -> Dict[str, Any]:
        """
        Derive all real-time operational metrics directly from the database.
        """
        # 1. Agent metrics
        agent_counts_stmt = select(Agent.status, func.count(Agent.id)).group_by(Agent.status)
        agent_counts = dict((await db.execute(agent_counts_stmt)).all())

        total_agents = sum(agent_counts.values())
        available_agents = agent_counts.get(AgentStatus.AVAILABLE, 0)
        reserved_agents = agent_counts.get(AgentStatus.RESERVED, 0)
        dialing_agents = agent_counts.get(AgentStatus.DIALING, 0)
        connected_agents = agent_counts.get(AgentStatus.CONNECTED, 0)
        wrap_up_agents = agent_counts.get(AgentStatus.WRAP_UP, 0)
        paused_agents = agent_counts.get(AgentStatus.PAUSED, 0)
        offline_agents = agent_counts.get(AgentStatus.OFFLINE, 0)

        # 2. Call metrics
        call_state_counts_stmt = select(Call.call_state, func.count(Call.id)).group_by(Call.call_state)
        call_state_counts = dict((await db.execute(call_state_counts_stmt)).all())

        calls_initiated = sum(call_state_counts.values())
        active_calls = call_state_counts.get(CallState.INITIATED, 0) + call_state_counts.get(CallState.RINGING, 0) + call_state_counts.get(CallState.CONNECTED, 0)
        connected_calls = call_state_counts.get(CallState.CONNECTED, 0)
        completed_calls = call_state_counts.get(CallState.COMPLETED, 0)
        failed_calls = call_state_counts.get(CallState.FAILED, 0)

        # 3. Answer rate calculation
        answered_stmt = select(func.count(Call.id)).where(Call.answered_at.isnot(None))
        total_answered = (await db.execute(answered_stmt)).scalar() or 0
        total_finished = completed_calls + failed_calls
        answer_rate_pct = round((total_answered / max(1, total_finished)) * 100, 1)

        # 4. Agent utilization percentage
        # Busy agents = connected + dialing + wrap_up
        # Active pool = total - offline - paused
        active_agent_pool = max(1, total_agents - offline_agents - paused_agents)
        utilization_pct = round(((connected_agents + dialing_agents + wrap_up_agents) / active_agent_pool) * 100, 1)

        # 5. Average talk time
        avg_tt_stmt = select(func.avg(Call.talk_time_seconds)).where(Call.talk_time_seconds > 0)
        avg_talk_time = (await db.execute(avg_tt_stmt)).scalar() or 0.0

        # 6. Provider health
        provider_a = get_telecom_provider("PROVIDER_A")
        health_a = provider_a.get_health().get("health_score", 1.0) * 100

        # 7. Agent availability distribution
        agent_distribution = {
            "AVAILABLE": available_agents,
            "RESERVED": reserved_agents,
            "DIALING": dialing_agents,
            "CONNECTED": connected_agents,
            "WRAP_UP": wrap_up_agents,
            "PAUSED": paused_agents,
            "OFFLINE": offline_agents
        }

        # 8. Call outcome distribution
        outcome_counts_stmt = select(Call.outcome, func.count(Call.id)).group_by(Call.outcome)
        outcome_counts = dict((await db.execute(outcome_counts_stmt)).all())
        call_outcomes = {
            "SUCCESS": outcome_counts.get(CallOutcome.SUCCESS, 0),
            "BUSY": outcome_counts.get(CallOutcome.BUSY, 0),
            "UNANSWERED": outcome_counts.get(CallOutcome.UNANSWERED, 0),
            "FAILED": outcome_counts.get(CallOutcome.FAILED, 0),
            "ABANDONED": outcome_counts.get(CallOutcome.ABANDONED, 0),
            "CANCELLED": outcome_counts.get(CallOutcome.CANCELLED, 0),
        }

        # 9. Recent activity feed
        recent_logs_stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(15)
        recent_logs = list((await db.execute(recent_logs_stmt)).scalars().all())

        return {
            "kpis": {
                "total_agents": total_agents,
                "available_agents": available_agents,
                "reserved_agents": reserved_agents,
                "active_calls": active_calls,
                "connected_calls": connected_calls,
                "calls_initiated": calls_initiated,
                "agent_utilization_pct": utilization_pct,
                "answer_rate_pct": answer_rate_pct,
                "average_talk_time_sec": round(float(avg_talk_time), 1),
                "provider_health_pct": round(health_a, 1)
            },
            "agent_distribution": agent_distribution,
            "call_outcomes": call_outcomes,
            "recent_events": [log.to_dict() for log in recent_logs]
        }

    @staticmethod
    async def get_time_series_data(db: AsyncSession, points: int = 12) -> List[Dict[str, Any]]:
        """
        Generate time-series activity telemetry from actual call records.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        result = []
        for i in range(points - 1, -1, -1):
            bucket_time = now - datetime.timedelta(seconds=i * 10)
            time_label = bucket_time.strftime("%H:%M:%S")
            # Query call transitions in this window
            start_window = bucket_time - datetime.timedelta(seconds=10)

            stmt = select(
                func.count(Call.id).filter(Call.initiated_at >= start_window, Call.initiated_at < bucket_time).label("initiated"),
                func.count(Call.id).filter(Call.answered_at >= start_window, Call.answered_at < bucket_time).label("answered"),
                func.count(Call.id).filter(Call.connected_at >= start_window, Call.connected_at < bucket_time).label("connected"),
                func.count(Call.id).filter(Call.ended_at >= start_window, Call.ended_at < bucket_time, Call.call_state == CallState.COMPLETED).label("completed"),
                func.count(Call.id).filter(Call.ended_at >= start_window, Call.ended_at < bucket_time, Call.call_state == CallState.FAILED).label("failed"),
            )
            row = (await db.execute(stmt)).first()
            result.append({
                "timestamp": time_label,
                "initiated": row.initiated if row else 0,
                "answered": row.answered if row else 0,
                "connected": row.connected if row else 0,
                "completed": row.completed if row else 0,
                "failed": row.failed if row else 0,
            })
        return result

    @staticmethod
    async def get_live_operations_table(db: AsyncSession, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Enriched live operations call table.
        Columns: Call ID, Borrower, Agent, Provider, Call State, Duration, Timestamp.
        """
        stmt = (
            select(
                Call,
                Borrower.name.label("borrower_name"),
                Borrower.phone_number.label("borrower_phone"),
                Agent.name.label("agent_name")
            )
            .join(Borrower, Call.borrower_id == Borrower.id, isouter=True)
            .join(Agent, Call.agent_id == Agent.id, isouter=True)
            .order_by(Call.created_at.desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()

        results = []
        for call, b_name, b_phone, a_name in rows:
            data = call.to_dict()
            data["borrower_name"] = b_name or "Unknown Borrower"
            data["borrower_phone"] = b_phone or "N/A"
            data["agent_name"] = a_name or "Unassigned"
            results.append(data)
        return results
