from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional, Tuple
import datetime

from app.models.campaign import Campaign
from app.models.borrower import Borrower
from app.models.enums import CampaignStatus, DialingMode, BorrowerStatus
from app.models.audit import AuditLog
from app.core.websocket_manager import ws_manager

class CampaignService:
    @staticmethod
    async def create_campaign(
        db: AsyncSession,
        name: str,
        dialing_mode: DialingMode = DialingMode.PROGRESSIVE,
        priority: int = 1,
        max_attempts: int = 3,
        retry_interval_seconds: int = 300,
        target_abandon_rate: float = 0.03,
        pacing_ratio: float = 1.0
    ) -> Campaign:
        campaign = Campaign(
            name=name,
            dialing_mode=dialing_mode,
            status=CampaignStatus.DRAFT,
            priority=priority,
            max_attempts=max_attempts,
            retry_interval_seconds=retry_interval_seconds,
            target_abandon_rate=target_abandon_rate,
            pacing_ratio=pacing_ratio
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)

        audit = AuditLog(
            event_type="CAMPAIGN_CREATED",
            entity_type="Campaign",
            entity_id=campaign.id,
            message=f"Campaign '{campaign.name}' created in {dialing_mode.value} mode",
            metadata_json={"dialing_mode": dialing_mode.value}
        )
        db.add(audit)
        await db.commit()

        await ws_manager.broadcast("CAMPAIGN_CREATED", campaign.to_dict())
        return campaign

    @staticmethod
    async def get_campaign(db: AsyncSession, campaign_id: str) -> Optional[Campaign]:
        stmt = select(Campaign).where(Campaign.id == campaign_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_campaigns(db: AsyncSession, skip: int = 0, limit: int = 50) -> Tuple[List[Campaign], int]:
        count_stmt = select(func.count(Campaign.id))
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = select(Campaign).order_by(Campaign.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        campaigns = list(result.scalars().all())

        # Update borrower counts
        for camp in campaigns:
            tot_b_stmt = select(func.count(Borrower.id)).where(Borrower.campaign_id == camp.id)
            comp_b_stmt = select(func.count(Borrower.id)).where(Borrower.campaign_id == camp.id, Borrower.status == BorrowerStatus.COMPLETED)
            camp.total_borrowers = (await db.execute(tot_b_stmt)).scalar() or 0
            camp.completed_borrowers = (await db.execute(comp_b_stmt)).scalar() or 0

        return campaigns, total

    @staticmethod
    async def update_campaign_status(
        db: AsyncSession,
        campaign_id: str,
        new_status: CampaignStatus
    ) -> Campaign:
        campaign = await CampaignService.get_campaign(db, campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        old_status = campaign.status
        campaign.status = new_status
        db.add(campaign)

        audit = AuditLog(
            event_type="CAMPAIGN_STATUS_CHANGED",
            entity_type="Campaign",
            entity_id=campaign.id,
            message=f"Campaign '{campaign.name}' status changed from {old_status.value} to {new_status.value}",
            metadata_json={"old_status": old_status.value, "new_status": new_status.value}
        )
        db.add(audit)
        await db.commit()
        await db.refresh(campaign)

        await ws_manager.broadcast("CAMPAIGN_UPDATED", campaign.to_dict())
        return campaign
