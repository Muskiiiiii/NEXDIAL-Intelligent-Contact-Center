from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from app.core.database import get_db
from app.schemas.worker import WorkerResponse
from app.services.worker_pool import WorkerPool

router = APIRouter(prefix="/workers", tags=["Workers"])

@router.get("", response_model=List[WorkerResponse])
async def list_workers(db: AsyncSession = Depends(get_db)):
    workers = await WorkerPool.get_all_workers(db)
    return [WorkerResponse.model_validate(w.to_dict()) for w in workers]

@router.post("/{worker_name}/crash")
async def crash_worker(worker_name: str, db: AsyncSession = Depends(get_db)):
    try:
        return await WorkerPool.simulate_worker_crash(db, worker_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/{worker_name}/recover")
async def recover_worker(worker_name: str, db: AsyncSession = Depends(get_db)):
    try:
        return await WorkerPool.recover_worker_and_reconcile(db, worker_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
