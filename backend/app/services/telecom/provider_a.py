import asyncio
import random
import uuid
from typing import Dict, Any, Optional
from app.services.telecom.interface import TelecomProvider
from app.services.telecom.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException

class ProviderA(TelecomProvider):
    """
    Mock Telecom Provider A:
    Enterprise tier — fast call setup (40-120ms), high reliability (98%), minimal jitter.
    """
    def __init__(self):
        self._name = "PROVIDER_A"
        self.circuit_breaker = CircuitBreaker(self._name, failure_threshold=5, recovery_time_seconds=10.0)
        self.avg_latency_ms = 75.0
        self.outage_mode = False
        self.active_calls: Dict[str, Dict[str, Any]] = {}

    @property
    def name(self) -> str:
        return self._name

    async def initiate_call(self, call_id: str, to_number: str) -> Dict[str, Any]:
        if self.outage_mode:
            self.circuit_breaker.record_failure()
            raise RuntimeError("Provider A simulated outage: upstream 503 Service Unavailable")

        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenException(f"Circuit Breaker for {self._name} is OPEN. Calls rejected.")

        # Simulate fast network latency (40-120ms)
        latency = random.uniform(0.04, 0.12)
        await asyncio.sleep(latency)
        self.avg_latency_ms = (self.avg_latency_ms * 0.9) + (latency * 1000 * 0.1)

        # 98% reliability
        if random.random() < 0.02:
            self.circuit_breaker.record_failure()
            raise RuntimeError(f"Provider A call initiation failed (transient network glitch)")

        self.circuit_breaker.record_success()
        provider_call_id = f"PA-{uuid.uuid4().hex[:8]}"

        payload = {
            "event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "provider_id": self._name,
            "call_id": call_id,
            "provider_call_id": provider_call_id,
            "to_number": to_number,
            "state": "INITIATED",
            "latency_ms": round(latency * 1000, 1)
        }
        self.active_calls[call_id] = {
            "provider_call_id": provider_call_id,
            "state": "INITIATED",
            "to_number": to_number
        }
        return payload

    async def hangup_call(self, call_id: str) -> Dict[str, Any]:
        await asyncio.sleep(0.02)
        if call_id in self.active_calls:
            self.active_calls[call_id]["state"] = "COMPLETED"
        return {
            "event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "provider_id": self._name,
            "call_id": call_id,
            "state": "COMPLETED",
            "reason": "NORMAL_CLEARING"
        }

    async def query_call_status(self, call_id: str, provider_call_id: Optional[str] = None) -> Dict[str, Any]:
        if self.outage_mode or self.circuit_breaker.state == "OPEN":
            return {
                "status": "UNKNOWN",
                "initiated": False,
                "error": "Provider A unreachable (outage / circuit open)"
            }

        # If provider_call_id is None and not in active_calls, it never reached carrier
        if not provider_call_id and call_id not in self.active_calls:
            return {
                "status": "NOT_FOUND",
                "initiated": False,
                "error": "Call never initiated with Provider A"
            }

        call_info = self.active_calls.get(call_id)
        if call_info:
            current_state = call_info.get("state", "INITIATED")
            is_active = current_state in ("INITIATED", "RINGING", "ANSWERED", "CONNECTED")
            return {
                "status": "ACTIVE" if is_active else "COMPLETED",
                "call_state": current_state,
                "initiated": True,
                "provider_call_id": call_info.get("provider_call_id")
            }

        if provider_call_id:
            return {
                "status": "COMPLETED",
                "call_state": "COMPLETED",
                "initiated": True,
                "provider_call_id": provider_call_id
            }

        return {
            "status": "NOT_FOUND",
            "initiated": False
        }

    def get_health(self) -> Dict[str, Any]:
        cb_status = self.circuit_breaker.get_status()
        health_score = 1.0 - cb_status["failure_rate"]
        if self.outage_mode or cb_status["state"] == "OPEN":
            health_score = 0.0
        elif cb_status["state"] == "HALF_OPEN":
            health_score = 0.5

        return {
            "provider_id": self._name,
            "status": "OFFLINE" if health_score == 0 else ("DEGRADED" if health_score < 0.85 else "ACTIVE"),
            "health_score": round(max(0.0, health_score), 2),
            "circuit_breaker": cb_status,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "outage_mode": self.outage_mode
        }
