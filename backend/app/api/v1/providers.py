from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.provider import ProviderEvent
from app.schemas.provider import ProviderEventResponse
from app.services.telecom import PROVIDER_REGISTRY, get_telecom_provider

router = APIRouter(prefix="/providers", tags=["Telecom Providers"])

@router.get("")
async def list_providers() -> List[Dict[str, Any]]:
    results = []
    for pid, provider in PROVIDER_REGISTRY.items():
        results.append(provider.get_health())
    return results

@router.get("/events", response_model=List[ProviderEventResponse])
async def list_provider_events(
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ProviderEvent).order_by(ProviderEvent.created_at.desc()).limit(limit)
    events = list((await db.execute(stmt)).scalars().all())
    return [ProviderEventResponse.model_validate(e.to_dict()) for e in events]

@router.post("/{provider_id}/reset-circuit")
async def reset_provider_circuit(provider_id: str):
    provider = get_telecom_provider(provider_id)
    provider.circuit_breaker.state = "CLOSED"
    provider.circuit_breaker.consecutive_failures = 0
    provider.outage_mode = False
    return {"status": "SUCCESS", "message": f"Circuit breaker for {provider_id} reset to CLOSED"}

@router.post("/{provider_id}/configure-anomalies")
async def configure_provider_anomalies(provider_id: str, payload: Dict[str, Any]):
    provider = get_telecom_provider(provider_id)
    if not hasattr(provider, "configure_anomalies"):
        raise HTTPException(status_code=400, detail=f"Provider {provider_id} does not support autonomous anomaly configuration")

    config_res = provider.configure_anomalies(
        enabled=payload.get("enabled", True),
        duplicate_probability=float(payload.get("duplicate_probability", 0.20)),
        out_of_order_probability=float(payload.get("out_of_order_probability", 0.15)),
        seed=payload.get("seed")
    )
    return {"status": "SUCCESS", "message": f"Anomalies configured for {provider_id}", "config": config_res}
