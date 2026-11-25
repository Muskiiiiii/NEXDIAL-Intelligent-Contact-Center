import time
from typing import Dict, Any
from app.models.enums import CircuitState

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_time_seconds: float = 10.0,
        half_open_max_trials: int = 2
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_time_seconds = recovery_time_seconds
        self.half_open_max_trials = half_open_max_trials

        self.state: CircuitState = CircuitState.CLOSED
        self.consecutive_failures: int = 0
        self.total_calls: int = 0
        self.total_failures: int = 0
        self.total_successes: int = 0
        self.last_failure_time: float = 0.0
        self.last_state_change: float = time.time()
        self.half_open_trials: int = 0

    def can_execute(self) -> bool:
        now = time.time()
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout elapsed
            if (now - self.last_state_change) >= self.recovery_time_seconds:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                self.half_open_trials = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_trials < self.half_open_max_trials:
                self.half_open_trials += 1
                return True
            return False

        return False

    def record_success(self):
        self.total_calls += 1
        self.total_successes += 1
        self.consecutive_failures = 0

        if self.state == CircuitState.HALF_OPEN:
            # Recovery verified! Reset to CLOSED
            self.state = CircuitState.CLOSED
            self.last_state_change = time.time()
            self.half_open_trials = 0

    def record_failure(self):
        self.total_calls += 1
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Trial failed: trip back to OPEN
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif self.state == CircuitState.CLOSED:
            if self.consecutive_failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()

    def get_status(self) -> Dict[str, Any]:
        state_str = self.state.value if hasattr(self.state, "value") else str(self.state)
        return {
            "name": self.name,
            "state": state_str,
            "consecutive_failures": self.consecutive_failures,
            "failure_threshold": self.failure_threshold,
            "total_calls": self.total_calls,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "failure_rate": round(self.total_failures / max(1, self.total_calls), 3),
            "recovery_time_seconds": self.recovery_time_seconds,
            "seconds_since_state_change": round(time.time() - self.last_state_change, 1)
        }
