from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.sql import func
import uuid
from app.core.database import Base
from app.models.enums import BorrowerStatus

class Borrower(Base):
    __tablename__ = "borrowers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, index=True)
    priority = Column(Integer, default=1, nullable=False, index=True) # 1 = highest, 5 = lowest
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(SQLEnum(BorrowerStatus), default=BorrowerStatus.QUEUED, nullable=False, index=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    eligible_for_call = Column(Boolean, default=True, nullable=False) # Consent & DNC check
    last_attempted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone_number": self.phone_number,
            "priority": self.priority,
            "campaign_id": self.campaign_id,
            "status": self.status.value if isinstance(self.status, BorrowerStatus) else self.status,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "eligible_for_call": self.eligible_for_call,
            "last_attempted_at": self.last_attempted_at.isoformat() if self.last_attempted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
