from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_db
from app.models.enums import BorrowerStatus
from app.schemas.borrower import BorrowerCreate, BorrowerImportItem, BorrowerResponse, BorrowerListResponse
from app.services.borrower_service import BorrowerService

router = APIRouter(prefix="/borrowers", tags=["Borrowers"])

@router.get("", response_model=BorrowerListResponse)
async def list_borrowers(
    campaign_id: Optional[str] = None,
    status: Optional[BorrowerStatus] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    borrowers, total = await BorrowerService.get_borrowers(db, campaign_id, status, search, skip, limit)

    # Summary counts
    all_b, _ = await BorrowerService.get_borrowers(db, campaign_id, None, None, 0, 1000)
    q_count = sum(1 for b in all_b if b.status == BorrowerStatus.QUEUED)
    conn_count = sum(1 for b in all_b if b.status == BorrowerStatus.CONNECTED)
    comp_count = sum(1 for b in all_b if b.status == BorrowerStatus.COMPLETED)
    fail_count = sum(1 for b in all_b if b.status == BorrowerStatus.FAILED)

    return BorrowerListResponse(
        borrowers=[BorrowerResponse.model_validate(b.to_dict()) for b in borrowers],
        total=total,
        queued_count=q_count,
        connected_count=conn_count,
        completed_count=comp_count,
        failed_count=fail_count
    )

@router.post("", response_model=BorrowerResponse)
async def create_borrower(payload: BorrowerCreate, db: AsyncSession = Depends(get_db)):
    borrower = await BorrowerService.create_borrower(
        db=db,
        name=payload.name,
        phone_number=payload.phone_number,
        priority=payload.priority,
        campaign_id=payload.campaign_id,
        eligible_for_call=payload.eligible_for_call
    )
    return BorrowerResponse.model_validate(borrower.to_dict())

@router.post("/import")
async def import_borrowers(
    items: List[BorrowerImportItem],
    campaign_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    data = [item.model_dump() for item in items]
    count = await BorrowerService.bulk_create_borrowers(db, data, campaign_id)
    return {"status": "SUCCESS", "imported_count": count}

@router.post("/{borrower_id}/retry", response_model=BorrowerResponse)
async def retry_borrower(borrower_id: str, db: AsyncSession = Depends(get_db)):
    borrower = await BorrowerService.get_borrower(db, borrower_id)
    if not borrower:
        raise HTTPException(status_code=404, detail="Borrower not found")

    if borrower.status == BorrowerStatus.FAILED:
        borrower = await BorrowerService.update_borrower_status(db, borrower_id, BorrowerStatus.QUEUED)
    return BorrowerResponse.model_validate(borrower.to_dict())
