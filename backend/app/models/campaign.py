from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
import uuid
from app.core.database import Base
from app.models.enums import CampaignStatus, DialingMode

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    dialing_mode = Column(SQLEnum(DialingMode), default=DialingMode.PROGRESSIVE, nullable=False)
    status = Column(SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)
    priority = Column(Integer, default=1, nullable=False)
    total_borrowers = Column(Integer, default=0, nullable=False)
    completed_borrowers = Column(Integer, default=0, nullable=False)
    assigned_agents = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    retry_interval_seconds = Column(Integer, default=300, nullable=False)
    target_abandon_rate = Column(Float, default=0.03, nullable=False) # e.g. 3% max abandon rate
    pacing_ratio = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "dialing_mode": self.dialing_mode.value if isinstance(self.dialing_mode, DialingMode) else self.dialing_mode,
            "status": self.status.value if isinstance(self.status, CampaignStatus) else self.status,
            "priority": self.priority,
            "total_borrowers": self.total_borrowers,
            "completed_borrowers": self.completed_borrowers,
            "assigned_agents": self.assigned_agents,
            "max_attempts": self.max_attempts,
            "retry_interval_seconds": self.retry_interval_seconds,
            "target_abandon_rate": self.target_abandon_rate,
            "pacing_ratio": self.pacing_ratio,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
