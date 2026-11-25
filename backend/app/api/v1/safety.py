from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.safety import SafetyDecision
from app.models.enums import DialingMode
from app.schemas.safety import SafetyCapacityStatus, SafetyDecisionResponse
from app.services.safety_controller import SafetyController
from app.services.telecom import get_telecom_provider

router = APIRouter(prefix="/safety", tags=["Safety Controller"])

@router.get("/capacity", response_model=SafetyCapacityStatus)
async def get_safety_capacity(db: AsyncSession = Depends(get_db)):
    cap = await SafetyController.get_system_capacity_snapshot(db)
    provider_a = get_telecom_provider("PROVIDER_A")
    health = provider_a.get_health()
    cb = health.get("circuit_breaker", {})

    constraints = []
    if cap["available_agents"] == 0:
        constraints.append("ZERO_AVAILABLE_AGENTS: Dialing restricted until agents become available.")
    if cap["in_flight_pending"] > 0:
        constraints.append(f"IN_FLIGHT_CALLS: {cap['in_flight_pending']} reservations/setup calls currently pending.")
    if cb.get("state") != "CLOSED":
        constraints.append(f"CIRCUIT_BREAKER_{cb.get('state')}: Provider protection active.")

    is_safe = cap["safe_capacity"] > 0 and cb.get("state") == "CLOSED"

    return SafetyCapacityStatus(
        available_agents=cap["available_agents"],
        reserved_agents=cap["reserved_agents"],
        dialing_calls=cap["dialing_agents"],
        ringing_calls=cap["ringing_calls"],
        active_connected_calls=cap["connected_calls"],
        safe_dialing_capacity=cap["safe_capacity"],
        provider_health_score=health.get("health_score", 1.0),
        circuit_status=cb.get("state", "CLOSED"),
        is_safe=is_safe,
        constraints=constraints
    )

@router.get("/decisions", response_model=List[SafetyDecisionResponse])
async def list_safety_decisions(
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SafetyDecision).order_by(SafetyDecision.created_at.desc()).limit(limit)
    decisions = list((await db.execute(stmt)).scalars().all())
    return [SafetyDecisionResponse.model_validate(d.to_dict()) for d in decisions]

@router.post("/evaluate", response_model=SafetyDecisionResponse)
async def dry_run_evaluate_safety(
    campaign_id: str,
    requested_calls: int,
    dialing_mode: DialingMode = DialingMode.PROGRESSIVE,
    db: AsyncSession = Depends(get_db)
):
    decision = await SafetyController.evaluate_dial_request(
        db=db,
        campaign_id=campaign_id,
        requested_calls=requested_calls,
        dialing_mode=dialing_mode
    )
    return SafetyDecisionResponse.model_validate(decision.to_dict())
