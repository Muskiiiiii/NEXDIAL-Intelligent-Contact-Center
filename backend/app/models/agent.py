from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
import uuid
from app.core.database import Base
from app.models.enums import AgentStatus

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    status = Column(SQLEnum(AgentStatus), default=AgentStatus.OFFLINE, nullable=False, index=True)
    current_call_id = Column(String(36), nullable=True)
    total_calls = Column(Integer, default=0, nullable=False)
    total_talk_time_seconds = Column(Float, default=0.0, nullable=False)
    average_talk_time = Column(Float, default=0.0, nullable=False)
    last_status_change = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "current_call_id": self.current_call_id,
            "total_calls": self.total_calls,
            "total_talk_time_seconds": round(self.total_talk_time_seconds, 2),
            "average_talk_time": round(self.average_talk_time, 2),
            "last_status_change": self.last_status_change.isoformat() if self.last_status_change else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
