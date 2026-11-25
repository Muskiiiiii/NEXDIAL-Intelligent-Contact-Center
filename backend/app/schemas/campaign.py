from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.enums import CampaignStatus, DialingMode

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    dialing_mode: DialingMode = DialingMode.PROGRESSIVE
    priority: int = Field(default=1, ge=1, le=5)
    max_attempts: int = Field(default=3, ge=1, le=10)
    retry_interval_seconds: int = Field(default=300, ge=30, le=3600)
    target_abandon_rate: float = Field(default=0.03, ge=0.001, le=0.20)
    pacing_ratio: float = Field(default=1.0, ge=0.5, le=5.0)

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    dialing_mode: Optional[DialingMode] = None
    status: Optional[CampaignStatus] = None
    priority: Optional[int] = None
    max_attempts: Optional[int] = None
    retry_interval_seconds: Optional[int] = None
    target_abandon_rate: Optional[float] = None
    pacing_ratio: Optional[float] = None

class CampaignResponse(BaseModel):
    id: str
    name: str
    dialing_mode: DialingMode
    status: CampaignStatus
    priority: int
    total_borrowers: int
    completed_borrowers: int
    assigned_agents: int
    max_attempts: int
    retry_interval_seconds: int
    target_abandon_rate: float
    pacing_ratio: float
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True
