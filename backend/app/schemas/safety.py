from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.models.enums import SafetyDecisionType

class SafetyCapacityStatus(BaseModel):
    available_agents: int
    reserved_agents: int
    dialing_calls: int
    ringing_calls: int
    active_connected_calls: int
    safe_dialing_capacity: int
    provider_health_score: float
    circuit_status: str
    is_safe: bool
    constraints: List[str]

class SafetyDecisionResponse(BaseModel):
    id: str
    campaign_id: str
    decision: SafetyDecisionType
    requested_calls: int
    approved_calls: int
    rejected_calls: int
    available_agents: int
    reserved_agents: int
    ringing_calls: int
    active_calls: int
    provider_health_score: float
    reason: str
    capacity_snapshot: Optional[Dict[str, Any]] = None
    provider_health_snapshot: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
