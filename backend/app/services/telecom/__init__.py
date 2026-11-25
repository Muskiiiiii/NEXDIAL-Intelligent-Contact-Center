from app.services.telecom.interface import TelecomProvider
from app.services.telecom.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from app.services.telecom.provider_a import ProviderA
from app.services.telecom.provider_b import ProviderB
from app.services.telecom.event_processor import EventProcessor

# Singleton provider instances
provider_a_instance = ProviderA()
provider_b_instance = ProviderB()

PROVIDER_REGISTRY = {
    "PROVIDER_A": provider_a_instance,
    "PROVIDER_B": provider_b_instance,
}

def get_telecom_provider(provider_id: str) -> TelecomProvider:
    provider = PROVIDER_REGISTRY.get(provider_id)
    if not provider:
        raise ValueError(f"Unknown telecom provider: {provider_id}")
    return provider

__all__ = [
    "TelecomProvider",
    "CircuitBreaker",
    "CircuitBreakerOpenException",
    "ProviderA",
    "ProviderB",
    "EventProcessor",
    "PROVIDER_REGISTRY",
    "get_telecom_provider",
]
