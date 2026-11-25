from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, or_
from typing import List, Optional, Tuple
import datetime

from app.models.borrower import Borrower
from app.models.enums import BorrowerStatus
from app.models.audit import AuditLog
from app.core.websocket_manager import ws_manager

VALID_BORROWER_TRANSITIONS = {
    BorrowerStatus.QUEUED: {BorrowerStatus.RESERVED, BorrowerStatus.CANCELLED},
    BorrowerStatus.RESERVED: {BorrowerStatus.DIALING, BorrowerStatus.QUEUED, BorrowerStatus.CANCELLED},
    BorrowerStatus.DIALING: {BorrowerStatus.CONNECTED, BorrowerStatus.COMPLETED, BorrowerStatus.FAILED, BorrowerStatus.QUEUED},
    BorrowerStatus.CONNECTED: {BorrowerStatus.COMPLETED},
    BorrowerStatus.FAILED: {BorrowerStatus.QUEUED, BorrowerStatus.CANCELLED},
    BorrowerStatus.COMPLETED: set(),
    BorrowerStatus.CANCELLED: {BorrowerStatus.QUEUED},
}

class BorrowerService:
    @staticmethod
    async def create_borrower(
        db: AsyncSession,
        name: str,
        phone_number: str,
        priority: int = 1,
        campaign_id: Optional[str] = None,
        eligible_for_call: bool = True
    ) -> Borrower:
        borrower = Borrower(
            name=name,
            phone_number=phone_number,
            priority=priority,
            campaign_id=campaign_id,
            eligible_for_call=eligible_for_call,
            status=BorrowerStatus.QUEUED
        )
        db.add(borrower)
        await db.commit()
        await db.refresh(borrower)
        await ws_manager.broadcast("BORROWER_CREATED", borrower.to_dict())
        return borrower

    @staticmethod
    async def bulk_create_borrowers(
        db: AsyncSession,
        borrowers_data: List[dict],
        campaign_id: Optional[str] = None
    ) -> int:
        created_count = 0
        for data in borrowers_data:
            # Check consent & DNC eligibility
            if not data.get("eligible_for_call", True):
                continue
            borrower = Borrower(
                name=data["name"],
                phone_number=data["phone_number"],
                priority=data.get("priority", 1),
                campaign_id=campaign_id or data.get("campaign_id"),
                eligible_for_call=True,
                status=BorrowerStatus.QUEUED
            )
            db.add(borrower)
            created_count += 1

        await db.commit()
        await ws_manager.broadcast("BORROWERS_IMPORTED", {"imported_count": created_count, "campaign_id": campaign_id})
        return created_count

    @staticmethod
    async def get_borrower(db: AsyncSession, borrower_id: str) -> Optional[Borrower]:
        stmt = select(Borrower).where(Borrower.id == borrower_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_borrowers(
        db: AsyncSession,
        campaign_id: Optional[str] = None,
        status: Optional[BorrowerStatus] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Borrower], int]:
        query = select(Borrower)
        count_query = select(func.count(Borrower.id))

        filters = []
        if campaign_id:
            filters.append(Borrower.campaign_id == campaign_id)
        if status:
            filters.append(Borrower.status == status)
        if search:
            filters.append(or_(
                Borrower.name.ilike(f"%{search}%"),
                Borrower.phone_number.ilike(f"%{search}%")
            ))

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total = (await db.execute(count_query)).scalar() or 0
        query = query.order_by(Borrower.priority.asc(), Borrower.created_at.asc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    @staticmethod
    async def reserve_borrower_atomic(db: AsyncSession, borrower_id: str) -> bool:
        """
        CRITICAL CONCURRENCY:
        Atomically reserve a borrower only if status is QUEUED and eligible for call.
        """
        stmt = (
            update(Borrower)
            .where(
                and_(
                    Borrower.id == borrower_id,
                    Borrower.status == BorrowerStatus.QUEUED,
                    Borrower.eligible_for_call == True
                )
            )
            .values(
                status=BorrowerStatus.RESERVED,
                last_attempted_at=func.now(),
                attempt_count=Borrower.attempt_count + 1
            )
        )
        result = await db.execute(stmt)
        await db.commit()

        acquired = (result.rowcount > 0)
        if acquired:
            borrower = await BorrowerService.get_borrower(db, borrower_id)
            if borrower:
                await ws_manager.broadcast("BORROWER_UPDATED", borrower.to_dict())
        return acquired

    @staticmethod
    async def reserve_eligible_borrowers_batch(
        db: AsyncSession,
        campaign_id: Optional[str] = None,
        limit: int = 1
    ) -> List[Borrower]:
        """
        Finds and atomically reserves up to `limit` eligible queued borrowers.
        """
        if limit <= 0:
            return []

        filters = [
            Borrower.status == BorrowerStatus.QUEUED,
            Borrower.eligible_for_call == True,
            Borrower.attempt_count < Borrower.max_attempts
        ]
        if campaign_id:
            filters.append(Borrower.campaign_id == campaign_id)

        candidates_stmt = (
            select(Borrower.id)
            .where(and_(*filters))
            .order_by(Borrower.priority.asc(), Borrower.created_at.asc())
            .limit(limit)
        )
        candidate_ids = (await db.execute(candidates_stmt)).scalars().all()

        reserved: List[Borrower] = []
        for bid in candidate_ids:
            acquired = await BorrowerService.reserve_borrower_atomic(db, bid)
            if acquired:
                borrower = await BorrowerService.get_borrower(db, bid)
                if borrower:
                    reserved.append(borrower)
        return reserved

    @staticmethod
    async def update_borrower_status(
        db: AsyncSession,
        borrower_id: str,
        new_status: BorrowerStatus,
        force: bool = False
    ) -> Borrower:
        borrower = await BorrowerService.get_borrower(db, borrower_id)
        if not borrower:
            raise ValueError(f"Borrower {borrower_id} not found")

        old_status = borrower.status
        if not force and new_status not in VALID_BORROWER_TRANSITIONS.get(old_status, set()):
            raise ValueError(f"Invalid borrower transition from {old_status.value} to {new_status.value}")

        borrower.status = new_status
        db.add(borrower)
        await db.commit()
        await db.refresh(borrower)
        await ws_manager.broadcast("BORROWER_UPDATED", borrower.to_dict())
        return borrower

    @staticmethod
    async def release_borrower(db: AsyncSession, borrower_id: str, retry_allowed: bool = True) -> bool:
        """
        Releases a borrower back to QUEUED or marks FAILED if max attempts reached.
        """
        borrower = await BorrowerService.get_borrower(db, borrower_id)
        if not borrower:
            return False

        if borrower.status in (BorrowerStatus.RESERVED, BorrowerStatus.DIALING):
            if retry_allowed and borrower.attempt_count < borrower.max_attempts:
                borrower.status = BorrowerStatus.QUEUED
            else:
                borrower.status = BorrowerStatus.FAILED

            db.add(borrower)
            await db.commit()
            await db.refresh(borrower)
            await ws_manager.broadcast("BORROWER_UPDATED", borrower.to_dict())
            return True
        return False
