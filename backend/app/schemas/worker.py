from pydantic import BaseModel
from typing import Optional, List
from app.models.enums import WorkerStatus

class WorkerResponse(BaseModel):
    id: str
    worker_name: str
    status: WorkerStatus
    active_job_id: Optional[str] = None
    jobs_processed: int
    jobs_failed: int
    jobs_recovered: int
    last_heartbeat: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

class WorkerActionRequest(BaseModel):
    action: str # "start", "stop", "crash", "recover"
