from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.sql import func
import uuid
from app.core.database import Base
from app.models.enums import CallState, CallOutcome

class Call(Base):
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String(36), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    borrower_id = Column(String(36), ForeignKey("borrowers.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    worker_id = Column(String(36), ForeignKey("workers.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id = Column(String(36), nullable=True, index=True)
    provider_id = Column(String(50), nullable=False, default="PROVIDER_A")
    provider_call_id = Column(String(100), nullable=True, index=True)

    call_state = Column(SQLEnum(CallState), default=CallState.INITIATED, nullable=False, index=True)
    outcome = Column(SQLEnum(CallOutcome), default=CallOutcome.PENDING, nullable=False, index=True)

    ring_time_seconds = Column(Float, default=0.0, nullable=False)
    talk_time_seconds = Column(Float, default=0.0, nullable=False)
    total_duration_seconds = Column(Float, default=0.0, nullable=False)

    initiated_at = Column(DateTime(timezone=True), server_default=func.now())
    ringing_at = Column(DateTime(timezone=True), nullable=True)
    answered_at = Column(DateTime(timezone=True), nullable=True)
    connected_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "borrower_id": self.borrower_id,
            "agent_id": self.agent_id,
            "worker_id": self.worker_id,
            "job_id": self.job_id,
            "provider_id": self.provider_id,
            "provider_call_id": self.provider_call_id,
            "call_state": self.call_state.value if isinstance(self.call_state, CallState) else self.call_state,
            "outcome": self.outcome.value if isinstance(self.outcome, CallOutcome) else self.outcome,
            "ring_time_seconds": round(self.ring_time_seconds, 2),
            "talk_time_seconds": round(self.talk_time_seconds, 2),
            "total_duration_seconds": round(self.total_duration_seconds, 2),
            "initiated_at": self.initiated_at.isoformat() if self.initiated_at else None,
            "ringing_at": self.ringing_at.isoformat() if self.ringing_at else None,
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
