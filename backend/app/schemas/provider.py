from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.models.enums import CircuitState, ProviderStatus, CallState

class ProviderMetricResponse(BaseModel):
    id: str
    name: str
    status: ProviderStatus
    circuit_state: CircuitState
    total_calls_sent: int
    success_count: int
    failure_count: int
    timeout_count: int
    consecutive_failures: int
    avg_latency_ms: float
    last_failure_at: Optional[str] = None
    last_success_at: Optional[str] = None
    circuit_opened_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

class ProviderEventResponse(BaseModel):
    id: str
    provider_id: str
    call_id: str
    event_type: CallState
    sequence_number: int
    payload: Optional[Dict[str, Any]] = None
    is_processed: bool
    is_duplicate: bool
    is_out_of_order: bool
    processed_at: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
