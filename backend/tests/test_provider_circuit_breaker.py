import pytest
import time
from app.services.telecom.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException

def test_circuit_breaker_trips_to_open_after_threshold():
    cb = CircuitBreaker("Test-Carrier", failure_threshold=3, recovery_time_seconds=1.0)
    assert cb.state.value == "CLOSED"
    assert cb.can_execute() is True

    # 1st failure
    cb.record_failure()
    assert cb.state.value == "CLOSED"

    # 2nd failure
    cb.record_failure()
    assert cb.state.value == "CLOSED"

    # 3rd consecutive failure -> trips to OPEN!
    cb.record_failure()
    assert cb.state.value == "OPEN"
    assert cb.can_execute() is False

def test_circuit_breaker_half_open_recovery():
    cb = CircuitBreaker("Test-Carrier-Rec", failure_threshold=2, recovery_time_seconds=0.1)
    cb.record_failure()
    cb.record_failure()
    assert cb.state.value == "OPEN"

    # Wait for recovery timeout
    time.sleep(0.12)
    # can_execute transitions to HALF_OPEN
    assert cb.can_execute() is True
    assert cb.state.value == "HALF_OPEN"

    # Successful trial call resets to CLOSED
    cb.record_success()
    assert cb.state.value == "CLOSED"
    assert cb.consecutive_failures == 0
