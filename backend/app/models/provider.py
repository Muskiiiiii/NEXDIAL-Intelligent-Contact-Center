from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Enum as SQLEnum, Text, JSON
from sqlalchemy.sql import func
import uuid
from app.core.database import Base
from app.models.enums import CircuitState, ProviderStatus, CallState

class ProviderMetric(Base):
    __tablename__ = "providers"

    id = Column(String(50), primary_key=True) # "PROVIDER_A", "PROVIDER_B"
    name = Column(String(100), nullable=False)
    status = Column(SQLEnum(ProviderStatus), default=ProviderStatus.ACTIVE, nullable=False)
    circuit_state = Column(SQLEnum(CircuitState), default=CircuitState.CLOSED, nullable=False)

    total_calls_sent = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    timeout_count = Column(Integer, default=0, nullable=False)
    consecutive_failures = Column(Integer, default=0, nullable=False)

    avg_latency_ms = Column(Float, default=120.0, nullable=False)
    last_failure_at = Column(DateTime(timezone=True), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    circuit_opened_at = Column(DateTime(timezone=True), nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, ProviderStatus) else self.status,
            "circuit_state": self.circuit_state.value if isinstance(self.circuit_state, CircuitState) else self.circuit_state,
            "total_calls_sent": self.total_calls_sent,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "timeout_count": self.timeout_count,
            "consecutive_failures": self.consecutive_failures,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "last_failure_at": self.last_failure_at.isoformat() if self.last_failure_at else None,
            "last_success_at": self.last_success_at.isoformat() if self.last_success_at else None,
            "circuit_opened_at": self.circuit_opened_at.isoformat() if self.circuit_opened_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class ProviderEvent(Base):
    __tablename__ = "provider_events"

    id = Column(String(64), primary_key=True) # Unique event ID (UUID or provider sequence)
    provider_id = Column(String(50), nullable=False, index=True)
    call_id = Column(String(36), nullable=False, index=True)
    event_type = Column(SQLEnum(CallState), nullable=False, index=True)
    sequence_number = Column(Integer, default=1, nullable=False)
    payload = Column(JSON, nullable=True)
    is_processed = Column(Boolean, default=False, nullable=False)
    is_duplicate = Column(Boolean, default=False, nullable=False)
    is_out_of_order = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "provider_id": self.provider_id,
            "call_id": self.call_id,
            "event_type": self.event_type.value if isinstance(self.event_type, CallState) else self.event_type,
            "sequence_number": self.sequence_number,
            "payload": self.payload,
            "is_processed": self.is_processed,
            "is_duplicate": self.is_duplicate,
            "is_out_of_order": self.is_out_of_order,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
