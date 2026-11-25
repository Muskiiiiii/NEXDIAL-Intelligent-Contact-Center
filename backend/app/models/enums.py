from enum import Enum

class AgentStatus(str, Enum):
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    DIALING = "DIALING"
    CONNECTED = "CONNECTED"
    WRAP_UP = "WRAP_UP"
    PAUSED = "PAUSED"

class BorrowerStatus(str, Enum):
    QUEUED = "QUEUED"
    RESERVED = "RESERVED"
    DIALING = "DIALING"
    CONNECTED = "CONNECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class DialingMode(str, Enum):
    PROGRESSIVE = "PROGRESSIVE"
    PREDICTIVE = "PREDICTIVE"

class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    COMPLETED = "COMPLETED"

class CallState(str, Enum):
    INITIATED = "INITIATED"
    RINGING = "RINGING"
    ANSWERED = "ANSWERED"
    CONNECTED = "CONNECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class CallOutcome(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    BUSY = "BUSY"
    UNANSWERED = "UNANSWERED"
    FAILED = "FAILED"
    ABANDONED = "ABANDONED"
    CANCELLED = "CANCELLED"
    WORKER_CRASH_ORPHANED = "WORKER_CRASH_ORPHANED"

class SafetyDecisionType(str, Enum):
    APPROVE = "APPROVE"
    REDUCE = "REDUCE"
    REJECT = "REJECT"
    FALLBACK_TO_PROGRESSIVE = "FALLBACK_TO_PROGRESSIVE"

class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class ProviderStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"

class WorkerStatus(str, Enum):
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    STOPPED = "STOPPED"
    CRASHED = "CRASHED"
