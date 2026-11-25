from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from app.core.database import get_db
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/overview")
async def get_analytics_overview(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    overview = await AnalyticsService.get_overview_kpis(db)
    time_series = await AnalyticsService.get_time_series_data(db, points=12)
    overview["time_series"] = time_series
    return overview

@router.get("/timeseries")
async def get_timeseries(
    points: int = Query(12, ge=6, le=60),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    return await AnalyticsService.get_time_series_data(db, points)
