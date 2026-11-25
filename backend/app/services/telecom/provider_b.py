import asyncio
import random
import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.telecom.interface import TelecomProvider
from app.services.telecom.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from app.models.enums import CallState

class ProviderB(TelecomProvider):
    """
    Mock Telecom Provider B:
    Budget / Secondary tier — slower setup (250-700ms), 15% failures/timeouts,
    configurable autonomous out-of-order & duplicate webhook event tendencies.
    """
    def __init__(self):
        self._name = "PROVIDER_B"
        self.circuit_breaker = CircuitBreaker(self._name, failure_threshold=4, recovery_time_seconds=12.0)
        self.avg_latency_ms = 450.0
        self.outage_mode = False
        self.simulate_duplicates = False
        self.simulate_out_of_order = False
        self.active_calls: Dict[str, Dict[str, Any]] = {}

        # Autonomous anomaly generation settings (F4 requirement)
        self.autonomous_anomalies_enabled: bool = False
        self.duplicate_event_probability: float = 0.20
        self.out_of_order_probability: float = 0.15
        self.random_seed: Optional[int] = None
        self._rng = random.Random()

    @property
    def name(self) -> str:
        return self._name

    async def initiate_call(self, call_id: str, to_number: str) -> Dict[str, Any]:
        if self.outage_mode:
            self.circuit_breaker.record_failure()
            raise RuntimeError("Provider B simulated outage: upstream timeout / gateway unavailable")

        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenException(f"Circuit Breaker for {self._name} is OPEN. Calls rejected.")

        # Slower setup (250ms - 750ms)
        latency = random.uniform(0.25, 0.75)
        await asyncio.sleep(latency)
        self.avg_latency_ms = (self.avg_latency_ms * 0.85) + (latency * 1000 * 0.15)

        # 15% failure/timeout rate
        if random.random() < 0.15:
            self.circuit_breaker.record_failure()
            raise TimeoutError(f"Provider B timeout during carrier handshake for call {call_id}")

        self.circuit_breaker.record_success()
        provider_call_id = f"PB-{uuid.uuid4().hex[:8]}"

        payload = {
            "event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "provider_id": self._name,
            "call_id": call_id,
            "provider_call_id": provider_call_id,
            "to_number": to_number,
            "state": "INITIATED",
            "latency_ms": round(latency * 1000, 1),
            "flag_duplicate": self.simulate_duplicates,
            "flag_out_of_order": self.simulate_out_of_order
        }
        self.active_calls[call_id] = {
            "provider_call_id": provider_call_id,
            "state": "INITIATED",
            "to_number": to_number
        }
        return payload

    async def hangup_call(self, call_id: str) -> Dict[str, Any]:
        await asyncio.sleep(0.08)
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
                "error": "Provider B unreachable (outage / circuit open)"
            }

        # If provider_call_id is None and not in active_calls, it never reached carrier
        if not provider_call_id and call_id not in self.active_calls:
            return {
                "status": "NOT_FOUND",
                "initiated": False,
                "error": "Call never initiated with Provider B"
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

    def configure_anomalies(
        self,
        enabled: bool = True,
        duplicate_probability: float = 0.20,
        out_of_order_probability: float = 0.15,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Configure autonomous anomaly generation for Provider B.
        Allows setting probabilities and optional deterministic seed for reproducible testing.
        """
        self.autonomous_anomalies_enabled = enabled
        self.duplicate_event_probability = max(0.0, min(1.0, duplicate_probability))
        self.out_of_order_probability = max(0.0, min(1.0, out_of_order_probability))
        self.random_seed = seed
        if seed is not None:
            self._rng = random.Random(seed)
        else:
            self._rng = random.Random()

        return {
            "provider_id": self._name,
            "autonomous_anomalies_enabled": self.autonomous_anomalies_enabled,
            "duplicate_event_probability": self.duplicate_event_probability,
            "out_of_order_probability": self.out_of_order_probability,
            "seed": self.random_seed
        }

    async def maybe_generate_autonomous_anomalies(
        self,
        db: AsyncSession,
        call_id: str,
        primary_event_id: str,
        current_state: CallState
    ) -> List[Dict[str, Any]]:
        """
        Autonomously generate duplicate and out-of-order webhook events
        if autonomous anomalies are enabled.
        Does NOT bypass EventProcessor — routes directly to EventProcessor to verify
        idempotency and monotonic hierarchy protection.
        """
        if not self.autonomous_anomalies_enabled:
            return []

        from app.services.telecom.event_processor import EventProcessor

        results = []
        rng = getattr(self, "_rng", random)

        # 1. Autonomous duplicate event anomaly
        if rng.random() < self.duplicate_event_probability:
            dup_res = await EventProcessor.process_provider_event(
                db=db,
                event_id=primary_event_id,
                provider_id=self._name,
                call_id=call_id,
                event_type=current_state
            )
            results.append({
                "anomaly_type": "AUTONOMOUS_DUPLICATE",
                "event_id": primary_event_id,
                "result": dup_res
            })

        # 2. Autonomous out-of-order event anomaly
        if rng.random() < self.out_of_order_probability:
            earlier_state: Optional[CallState] = None
            if current_state in (CallState.CONNECTED, CallState.ANSWERED):
                earlier_state = CallState.RINGING
            elif current_state == CallState.COMPLETED:
                earlier_state = CallState.ANSWERED

            if earlier_state:
                ooo_event_id = f"ooo-auto-{uuid.uuid4().hex[:8]}"
                ooo_res = await EventProcessor.process_provider_event(
                    db=db,
                    event_id=ooo_event_id,
                    provider_id=self._name,
                    call_id=call_id,
                    event_type=earlier_state
                )
                results.append({
                    "anomaly_type": "AUTONOMOUS_OUT_OF_ORDER",
                    "event_id": ooo_event_id,
                    "target_state": earlier_state.value,
                    "result": ooo_res
                })

        return results

    def get_health(self) -> Dict[str, Any]:
        cb_status = self.circuit_breaker.get_status()
        health_score = 1.0 - cb_status["failure_rate"]
        if self.outage_mode or cb_status["state"] == "OPEN":
            health_score = 0.0
        elif cb_status["state"] == "HALF_OPEN":
            health_score = 0.4

        return {
            "provider_id": self._name,
            "status": "OFFLINE" if health_score == 0 else ("DEGRADED" if health_score < 0.75 else "ACTIVE"),
            "health_score": round(max(0.0, health_score), 2),
            "circuit_breaker": cb_status,
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "outage_mode": self.outage_mode,
            "simulate_duplicates": self.simulate_duplicates,
            "simulate_out_of_order": self.simulate_out_of_order,
            "autonomous_anomalies": {
                "enabled": self.autonomous_anomalies_enabled,
                "duplicate_probability": self.duplicate_event_probability,
                "out_of_order_probability": self.out_of_order_probability,
                "seed": self.random_seed
            }
        }
