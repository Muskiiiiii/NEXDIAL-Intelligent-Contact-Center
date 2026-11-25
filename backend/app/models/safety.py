from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum, JSON, Text
from sqlalchemy.sql import func
import uuid
from app.core.database import Base
from app.models.enums import SafetyDecisionType

class SafetyDecision(Base):
    __tablename__ = "safety_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String(36), nullable=False, index=True)
    decision = Column(SQLEnum(SafetyDecisionType), nullable=False, index=True)

    requested_calls = Column(Integer, nullable=False)
    approved_calls = Column(Integer, nullable=False)
    rejected_calls = Column(Integer, nullable=False)

    available_agents = Column(Integer, nullable=False)
    reserved_agents = Column(Integer, nullable=False)
    ringing_calls = Column(Integer, nullable=False)
    active_calls = Column(Integer, nullable=False)

    provider_health_score = Column(Float, default=1.0, nullable=False)
    reason = Column(Text, nullable=False)
    capacity_snapshot = Column(JSON, nullable=True)
    provider_health_snapshot = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "decision": self.decision.value if isinstance(self.decision, SafetyDecisionType) else self.decision,
            "requested_calls": self.requested_calls,
            "approved_calls": self.approved_calls,
            "rejected_calls": self.rejected_calls,
            "available_agents": self.available_agents,
            "reserved_agents": self.reserved_agents,
            "ringing_calls": self.ringing_calls,
            "active_calls": self.active_calls,
            "provider_health_score": round(self.provider_health_score, 2),
            "reason": self.reason,
            "capacity_snapshot": self.capacity_snapshot,
            "provider_health_snapshot": self.provider_health_snapshot,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
