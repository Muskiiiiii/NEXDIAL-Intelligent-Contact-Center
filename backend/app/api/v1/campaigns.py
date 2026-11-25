from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.models.enums import CampaignStatus
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse
from app.services.campaign_service import CampaignService

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])

@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    campaigns, _ = await CampaignService.get_all_campaigns(db, skip, limit)
    return [CampaignResponse.model_validate(c.to_dict()) for c in campaigns]

@router.post("", response_model=CampaignResponse)
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = await CampaignService.create_campaign(
        db=db,
        name=payload.name,
        dialing_mode=payload.dialing_mode,
        priority=payload.priority,
        max_attempts=payload.max_attempts,
        retry_interval_seconds=payload.retry_interval_seconds,
        target_abandon_rate=payload.target_abandon_rate,
        pacing_ratio=payload.pacing_ratio
    )
    return CampaignResponse.model_validate(campaign.to_dict())

@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    campaign = await CampaignService.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CampaignResponse.model_validate(campaign.to_dict())

@router.post("/{campaign_id}/start", response_model=CampaignResponse)
async def start_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    campaign = await CampaignService.update_campaign_status(db, campaign_id, CampaignStatus.RUNNING)
    return CampaignResponse.model_validate(campaign.to_dict())

@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
async def pause_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    campaign = await CampaignService.update_campaign_status(db, campaign_id, CampaignStatus.PAUSED)
    return CampaignResponse.model_validate(campaign.to_dict())

@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
async def resume_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    campaign = await CampaignService.update_campaign_status(db, campaign_id, CampaignStatus.RUNNING)
    return CampaignResponse.model_validate(campaign.to_dict())

@router.post("/{campaign_id}/stop", response_model=CampaignResponse)
async def stop_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    campaign = await CampaignService.update_campaign_status(db, campaign_id, CampaignStatus.STOPPED)
    return CampaignResponse.model_validate(campaign.to_dict())
