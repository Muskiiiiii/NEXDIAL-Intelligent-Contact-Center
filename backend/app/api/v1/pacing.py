from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.database import get_db
from app.models.campaign import Campaign
from app.schemas.pacing import PacingCalculationResponse
from app.services.pacing_engine import PacingEngine

router = APIRouter(prefix="/pacing", tags=["Pacing Engine"])

@router.get("/status", response_model=PacingCalculationResponse)
async def get_pacing_status(
    campaign_id: Optional[str] = None,
    risk_factor: float = Query(0.15, ge=0.0, le=0.5),
    db: AsyncSession = Depends(get_db)
):
    if campaign_id:
        camp_stmt = select(Campaign).where(Campaign.id == campaign_id)
        campaign = (await db.execute(camp_stmt)).scalar_one_or_none()
    else:
        camp_stmt = select(Campaign).order_by(Campaign.created_at.desc()).limit(1)
        campaign = (await db.execute(camp_stmt)).scalar_one_or_none()

    if not campaign:
        raise HTTPException(status_code=404, detail="No active campaign found for pacing calculation")

    result = await PacingEngine.compute_dial_request(
        db=db,
        campaign=campaign,
        risk_factor=risk_factor
    )
    return PacingCalculationResponse.model_validate(result)
