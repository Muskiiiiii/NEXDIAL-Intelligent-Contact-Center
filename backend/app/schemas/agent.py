from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.enums import AgentStatus

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    status: AgentStatus = AgentStatus.OFFLINE

class AgentUpdateStatus(BaseModel):
    status: AgentStatus

class AgentResponse(BaseModel):
    id: str
    name: str
    status: AgentStatus
    current_call_id: Optional[str] = None
    total_calls: int = 0
    total_talk_time_seconds: float = 0.0
    average_talk_time: float = 0.0
    last_status_change: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

class AgentListResponse(BaseModel):
    agents: List[AgentResponse]
    total: int
    available_count: int
    reserved_count: int
    connected_count: int
    offline_count: int
