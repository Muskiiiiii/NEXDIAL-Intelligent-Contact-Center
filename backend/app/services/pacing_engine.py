import math
import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.call import Call
from app.models.agent import Agent
from app.models.borrower import Borrower
from app.models.campaign import Campaign
from app.models.enums import DialingMode, CallState, CallOutcome, AgentStatus, BorrowerStatus
from app.services.safety_controller import SafetyController
from app.services.telecom import get_telecom_provider

class PacingEngine:
    """
    STATISTICAL PREDICTIVE & PROGRESSIVE PACING ENGINE
    Computes optimal outbound dial requests based on real-time operational metrics.
    NEVER directly initiates calls — always passes requests to the Safety Controller.
    """

    DEFAULT_SETUP_WINDOW_SEC: float = 10.0
    MIN_SETUP_WINDOW_SEC: float = 2.0
    MAX_SETUP_WINDOW_SEC: float = 30.0
    STALE_TELEMETRY_WINDOW_SEC: float = 300.0  # 5 minutes

    @staticmethod
    async def get_dynamic_setup_latency(
        db: AsyncSession,
        provider_id: str = "PROVIDER_A",
        campaign_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dynamically calculate expected call setup latency combining:
        1. Live provider carrier handshake telemetry (avg_latency_ms).
        2. Rolling average ring time from recent database call measurements.
        3. Safe bounds and fallback handling for missing, stale, or insufficient data.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        stale_cutoff = now - datetime.timedelta(seconds=PacingEngine.STALE_TELEMETRY_WINDOW_SEC)

        # 1. Carrier handshake latency from provider telemetry
        provider = get_telecom_provider(provider_id)
        carrier_handshake_ms = 0.0
        is_provider_healthy = False

        if provider:
            health = provider.get_health()
            cb_state = health.get("circuit_breaker", {}).get("state", "CLOSED")
            if health.get("status") != "OFFLINE" and cb_state != "OPEN":
                carrier_handshake_ms = float(health.get("avg_latency_ms", 0.0))
                is_provider_healthy = True

        carrier_handshake_sec = carrier_handshake_ms / 1000.0

        # 2. Recent call setup (ring time) measurements from DB
        recent_calls_stmt = (
            select(Call.ring_time_seconds, Call.created_at)
            .where(
                Call.ring_time_seconds > 0,
                Call.call_state.in_([CallState.ANSWERED, CallState.CONNECTED, CallState.COMPLETED])
            )
            .order_by(Call.created_at.desc())
            .limit(20)
        )
        if campaign_id:
            recent_calls_stmt = recent_calls_stmt.where(Call.campaign_id == campaign_id)

        rows = (await db.execute(recent_calls_stmt)).all()

        fresh_samples = []
        stale_samples = []
        for r_sec, c_at in rows:
            if c_at:
                c_dt = c_at if c_at.tzinfo else c_at.replace(tzinfo=datetime.timezone.utc)
                if c_dt >= stale_cutoff:
                    fresh_samples.append(r_sec)
                else:
                    stale_samples.append(r_sec)
            else:
                stale_samples.append(r_sec)

        sample_size = len(fresh_samples)
        telemetry_source: str
        is_fallback: bool
        raw_setup_sec: float

        if sample_size >= 3:
            measured_ring = sum(fresh_samples) / sample_size
            raw_setup_sec = carrier_handshake_sec + measured_ring
            telemetry_source = "DYNAMIC_PROVIDER_AND_DB"
            is_fallback = False
        elif sample_size > 0:
            measured_ring = sum(fresh_samples) / sample_size
            sample_setup = carrier_handshake_sec + measured_ring
            weight = sample_size / 3.0
            raw_setup_sec = (weight * sample_setup) + ((1.0 - weight) * PacingEngine.DEFAULT_SETUP_WINDOW_SEC)
            telemetry_source = "BLENDED_INSUFFICIENT_TELEMETRY"
            is_fallback = True
        elif len(stale_samples) > 0:
            measured_ring = sum(stale_samples) / len(stale_samples)
            raw_setup_sec = 0.5 * (carrier_handshake_sec + measured_ring) + 0.5 * PacingEngine.DEFAULT_SETUP_WINDOW_SEC
            telemetry_source = "STALE_TELEMETRY_FALLBACK"
            is_fallback = True
        else:
            if is_provider_healthy and carrier_handshake_sec > 0:
                raw_setup_sec = carrier_handshake_sec + (PacingEngine.DEFAULT_SETUP_WINDOW_SEC - 0.5)
            else:
                raw_setup_sec = PacingEngine.DEFAULT_SETUP_WINDOW_SEC
            telemetry_source = "MISSING_TELEMETRY_DEFAULT"
            is_fallback = True

        clamped_setup_sec = max(
            PacingEngine.MIN_SETUP_WINDOW_SEC,
            min(PacingEngine.MAX_SETUP_WINDOW_SEC, raw_setup_sec)
        )

        return {
            "setup_window_sec": round(clamped_setup_sec, 2),
            "raw_setup_sec": round(raw_setup_sec, 2),
            "carrier_handshake_ms": round(carrier_handshake_ms, 1),
            "carrier_handshake_sec": round(carrier_handshake_sec, 2),
            "sample_size": sample_size,
            "telemetry_source": telemetry_source,
            "is_fallback": is_fallback,
            "clamped": clamped_setup_sec != raw_setup_sec
        }

    @staticmethod
    async def calculate_historical_metrics(db: AsyncSession, campaign_id: Optional[str] = None) -> Dict[str, float]:
        """
        Derive true operational statistics from historical database call records.
        """
        # Answer rate calculation
        total_calls_stmt = select(func.count(Call.id)).where(Call.call_state.in_([CallState.COMPLETED, CallState.FAILED, CallState.CANCELLED]))
        answered_calls_stmt = select(func.count(Call.id)).where(Call.answered_at.isnot(None))

        avg_talk_time_stmt = select(func.avg(Call.talk_time_seconds)).where(Call.talk_time_seconds > 0)
        avg_ring_time_stmt = select(func.avg(Call.ring_time_seconds)).where(Call.ring_time_seconds > 0)

        if campaign_id:
            total_calls_stmt = total_calls_stmt.where(Call.campaign_id == campaign_id)
            answered_calls_stmt = answered_calls_stmt.where(Call.campaign_id == campaign_id)
            avg_talk_time_stmt = avg_talk_time_stmt.where(Call.campaign_id == campaign_id)
            avg_ring_time_stmt = avg_ring_time_stmt.where(Call.campaign_id == campaign_id)

        total_completed = (await db.execute(total_calls_stmt)).scalar() or 0
        total_answered = (await db.execute(answered_calls_stmt)).scalar() or 0
        avg_talk_time = (await db.execute(avg_talk_time_stmt)).scalar() or 60.0
        avg_ring_time = (await db.execute(avg_ring_time_stmt)).scalar() or 8.0

        if total_completed > 0:
            raw_answer_rate = total_answered / total_completed
        else:
            raw_answer_rate = 0.45 # Reasonable initial prior

        # Bayesian smoothed answer rate (prior of 40% with weight of 10 calls)
        prior_weight = 10
        prior_rate = 0.40
        smoothed_answer_rate = ((total_completed * raw_answer_rate) + (prior_weight * prior_rate)) / (total_completed + prior_weight)

        return {
            "total_calls_completed": total_completed,
            "raw_answer_rate": round(raw_answer_rate, 3),
            "smoothed_answer_rate": round(max(0.05, min(0.95, smoothed_answer_rate)), 3),
            "avg_talk_time": round(float(avg_talk_time), 1),
            "avg_ring_time": round(float(avg_ring_time), 1)
        }

    @staticmethod
    async def compute_dial_request(
        db: AsyncSession,
        campaign: Campaign,
        provider_id: str = "PROVIDER_A",
        risk_factor: float = 0.15
    ) -> Dict[str, Any]:
        """
        Evaluate dial requirements for a campaign based on mode (Progressive or Predictive).
        Produces calculation details, explanation, and requested count for the Safety Controller.
        """
        # 1. System state snapshot
        cap = await SafetyController.get_system_capacity_snapshot(db)
        hist = await PacingEngine.calculate_historical_metrics(db, campaign.id)

        # 2. Eligible queued borrowers count
        queued_stmt = select(func.count(Borrower.id)).where(
            Borrower.campaign_id == campaign.id,
            Borrower.status == BorrowerStatus.QUEUED,
            Borrower.eligible_for_call == True,
            Borrower.attempt_count < Borrower.max_attempts
        )
        eligible_borrowers = (await db.execute(queued_stmt)).scalar() or 0

        available_agents = cap["available_agents"]
        reserved_agents = cap["reserved_agents"]
        ringing_calls = cap["ringing_calls"]
        connected_calls = cap["connected_calls"]
        in_flight = cap["in_flight_pending"]

        if campaign.dialing_mode == DialingMode.PROGRESSIVE:
            # PROGRESSIVE DIALING:
            # 1 available agent -> at most 1 outbound call.
            # Never exceed available agents minus in-flight calls.
            progressive_allowance = max(0, available_agents - in_flight)
            requested_count = min(progressive_allowance, eligible_borrowers)

            explanation = (
                f"Progressive Dialing (1:1 ratio): {available_agents} available agents, "
                f"{in_flight} in-flight. Requested {requested_count} calls for {eligible_borrowers} queued borrowers."
            )

            return {
                "campaign_id": campaign.id,
                "dialing_mode": DialingMode.PROGRESSIVE,
                "available_agents": available_agents,
                "reserved_agents": reserved_agents,
                "connected_calls": connected_calls,
                "ringing_calls": ringing_calls,
                "historical_answer_rate": hist["raw_answer_rate"],
                "smoothed_answer_rate": hist["smoothed_answer_rate"],
                "expected_near_term_releases": 0.0,
                "risk_factor": 0.0,
                "safety_buffer": 0.0,
                "eligible_borrowers": eligible_borrowers,
                "requested_dial_count": requested_count,
                "formula_explanation": explanation,
                "calculation_details": {
                    "mode": "PROGRESSIVE",
                    "safe_headroom": progressive_allowance,
                    "target_ratio": 1.0
                }
            }

        else:
            # PREDICTIVE DIALING:
            # Statistical pacing model
            smoothed_answer_rate = hist["smoothed_answer_rate"]
            avg_talk_time = hist["avg_talk_time"]

            # Dynamic setup latency calculation (B7 requirement)
            latency_info = await PacingEngine.get_dynamic_setup_latency(
                db=db,
                provider_id=provider_id,
                campaign_id=campaign.id
            )
            setup_window_sec = latency_info["setup_window_sec"]

            # Expected near-term agent releases:
            # Proportion of active connected calls expected to complete during dynamic setup window
            expected_releases = connected_calls * min(1.0, (setup_window_sec / max(10.0, avg_talk_time)))

            # Total agents expected to be available when new dials connect
            expected_available_agents = available_agents + expected_releases

            # Ringing calls predicted to answer
            predicted_answers_from_ringing = ringing_calls * smoothed_answer_rate

            # Net agents needing an answered call
            net_agent_capacity = max(0.0, expected_available_agents - predicted_answers_from_ringing)

            # Raw calls required to produce net_agent_capacity answers
            raw_dials_needed = net_agent_capacity / max(0.05, smoothed_answer_rate)

            # Apply configurable risk factor and safety buffer
            buffered_dials = raw_dials_needed * (1.0 - risk_factor)

            # Upper bound: Maximum dial multiplier (e.g., 2.5x available agents) to avoid wild overdialing
            max_pacing_limit = max(0, int(available_agents * 2.5))
            safe_requested = min(int(buffered_dials), max_pacing_limit)
            requested_count = min(max(0, safe_requested), eligible_borrowers)

            predicted_answers = round(requested_count * smoothed_answer_rate, 2)

            explanation = (
                f"Predictive Pacing: Answer rate estimated at {smoothed_answer_rate:.1%}. "
                f"Setup latency dynamically estimated at {setup_window_sec:.1f}s ({latency_info['telemetry_source']}). "
                f"Available agents: {available_agents}, expected near-term releases: {expected_releases:.1f}. "
                f"Ringing calls ({ringing_calls}) predicted to yield {predicted_answers_from_ringing:.1f} answers. "
                f"Risk factor: {risk_factor:.0%}. Generated dial request of {requested_count} calls."
            )

            return {
                "campaign_id": campaign.id,
                "dialing_mode": DialingMode.PREDICTIVE,
                "available_agents": available_agents,
                "reserved_agents": reserved_agents,
                "connected_calls": connected_calls,
                "ringing_calls": ringing_calls,
                "historical_answer_rate": hist["raw_answer_rate"],
                "smoothed_answer_rate": smoothed_answer_rate,
                "setup_window_sec": setup_window_sec,
                "setup_latency_telemetry": latency_info,
                "expected_near_term_releases": round(expected_releases, 2),
                "risk_factor": risk_factor,
                "safety_buffer": round(raw_dials_needed * risk_factor, 2),
                "eligible_borrowers": eligible_borrowers,
                "requested_dial_count": requested_count,
                "predicted_answers": predicted_answers,
                "formula_explanation": explanation,
                "calculation_details": {
                    "setup_window_sec": setup_window_sec,
                    "latency_telemetry": latency_info,
                    "expected_available_agents": round(expected_available_agents, 2),
                    "predicted_answers_from_ringing": round(predicted_answers_from_ringing, 2),
                    "raw_dials_needed": round(raw_dials_needed, 2),
                    "max_pacing_limit": max_pacing_limit,
                    "applied_clamp": requested_count < int(buffered_dials)
                }
            }
