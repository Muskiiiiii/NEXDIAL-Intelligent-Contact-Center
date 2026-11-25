from pydantic import BaseModel
from typing import Optional, List
from app.models.enums import CallState, CallOutcome

class CallResponse(BaseModel):
    id: str
    campaign_id: str
    borrower_id: str
    agent_id: Optional[str] = None
    worker_id: Optional[str] = None
    job_id: Optional[str] = None
    provider_id: str
    provider_call_id: Optional[str] = None
    call_state: CallState
    outcome: CallOutcome
    ring_time_seconds: float
    talk_time_seconds: float
    total_duration_seconds: float
    initiated_at: Optional[str] = None
    ringing_at: Optional[str] = None
    answered_at: Optional[str] = None
    connected_at: Optional[str] = None
    ended_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None

    # Enrichment fields for UI
    borrower_name: Optional[str] = None
    borrower_phone: Optional[str] = None
    agent_name: Optional[str] = None

    class Config:
        from_attributes = True

class CallListResponse(BaseModel):
    calls: List[CallResponse]
    total: int
    active_count: int
    completed_count: int
    failed_count: int
