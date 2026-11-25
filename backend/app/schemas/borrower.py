from pydantic import BaseModel, Field
from typing import Optional, List
from app.models.enums import BorrowerStatus

class BorrowerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., min_length=5, max_length=20)
    priority: int = Field(default=1, ge=1, le=5)
    campaign_id: Optional[str] = None
    eligible_for_call: bool = True

class BorrowerImportItem(BaseModel):
    name: str
    phone_number: str
    priority: int = 1
    eligible_for_call: bool = True

class BorrowerResponse(BaseModel):
    id: str
    name: str
    phone_number: str
    priority: int
    campaign_id: Optional[str] = None
    status: BorrowerStatus
    attempt_count: int
    max_attempts: int
    eligible_for_call: bool
    last_attempted_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

class BorrowerListResponse(BaseModel):
    borrowers: List[BorrowerResponse]
    total: int
    queued_count: int
    connected_count: int
    completed_count: int
    failed_count: int
