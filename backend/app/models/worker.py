from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
import uuid
from app.core.database import Base
from app.models.enums import WorkerStatus

class Worker(Base):
    __tablename__ = "workers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_name = Column(String(100), nullable=False, unique=True)
    status = Column(SQLEnum(WorkerStatus), default=WorkerStatus.IDLE, nullable=False, index=True)
    active_job_id = Column(String(36), nullable=True)
    jobs_processed = Column(Integer, default=0, nullable=False)
    jobs_failed = Column(Integer, default=0, nullable=False)
    jobs_recovered = Column(Integer, default=0, nullable=False)
    last_heartbeat = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "worker_name": self.worker_name,
            "status": self.status.value if isinstance(self.status, WorkerStatus) else self.status,
            "active_job_id": self.active_job_id,
            "jobs_processed": self.jobs_processed,
            "jobs_failed": self.jobs_failed,
            "jobs_recovered": self.jobs_recovered,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
