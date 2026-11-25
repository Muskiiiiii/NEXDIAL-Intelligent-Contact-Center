from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List

from app.core.database import get_db
from app.models.call import Call
from app.models.borrower import Borrower
from app.models.agent import Agent
from app.models.enums import CallState
from app.schemas.call import CallResponse, CallListResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/calls", tags=["Calls"])

@router.get("", response_model=CallListResponse)
async def list_calls(
    state: Optional[CallState] = None,
    campaign_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(
            Call,
            Borrower.name.label("borrower_name"),
            Borrower.phone_number.label("borrower_phone"),
            Agent.name.label("agent_name")
        )
        .join(Borrower, Call.borrower_id == Borrower.id, isouter=True)
        .join(Agent, Call.agent_id == Agent.id, isouter=True)
    )
    count_query = select(func.count(Call.id))

    if state:
        query = query.where(Call.call_state == state)
        count_query = count_query.where(Call.call_state == state)
    if campaign_id:
        query = query.where(Call.campaign_id == campaign_id)
        count_query = count_query.where(Call.campaign_id == campaign_id)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Call.created_at.desc()).offset(skip).limit(limit)
    rows = (await db.execute(query)).all()

    calls = []
    for call, b_name, b_phone, a_name in rows:
        d = call.to_dict()
        d["borrower_name"] = b_name
        d["borrower_phone"] = b_phone
        d["agent_name"] = a_name
        calls.append(CallResponse.model_validate(d))

    # Aggregates
    tot_active_stmt = select(func.count(Call.id)).where(Call.call_state.in_([CallState.INITIATED, CallState.RINGING, CallState.CONNECTED]))
    tot_comp_stmt = select(func.count(Call.id)).where(Call.call_state == CallState.COMPLETED)
    tot_fail_stmt = select(func.count(Call.id)).where(Call.call_state == CallState.FAILED)

    active_cnt = (await db.execute(tot_active_stmt)).scalar() or 0
    comp_cnt = (await db.execute(tot_comp_stmt)).scalar() or 0
    fail_cnt = (await db.execute(tot_fail_stmt)).scalar() or 0

    return CallListResponse(
        calls=calls,
        total=total,
        active_count=active_cnt,
        completed_count=comp_cnt,
        failed_count=fail_cnt
    )

@router.get("/live", response_model=List[CallResponse])
async def get_live_operations_calls(limit: int = 25, db: AsyncSession = Depends(get_db)):
    rows = await AnalyticsService.get_live_operations_table(db, limit)
    return [CallResponse.model_validate(r) for r in rows]

@router.get("/{call_id}", response_model=CallResponse)
async def get_call(call_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            Call,
            Borrower.name.label("borrower_name"),
            Borrower.phone_number.label("borrower_phone"),
            Agent.name.label("agent_name")
        )
        .join(Borrower, Call.borrower_id == Borrower.id, isouter=True)
        .join(Agent, Call.agent_id == Agent.id, isouter=True)
        .where(Call.id == call_id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Call not found")
    call, b_name, b_phone, a_name = row
    d = call.to_dict()
    d["borrower_name"] = b_name
    d["borrower_phone"] = b_phone
    d["agent_name"] = a_name
    return CallResponse.model_validate(d)
