from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class TelecomProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def initiate_call(self, call_id: str, to_number: str) -> Dict[str, Any]:
        """
        Initiate outbound call through telecom provider.
        Returns initial event payload or raises an exception if provider fails.
        """
        pass

    @abstractmethod
    async def hangup_call(self, call_id: str) -> Dict[str, Any]:
        """Terminate an active call."""
        pass

    @abstractmethod
    def get_health(self) -> Dict[str, Any]:
        """Return provider latency, failure rate, and operational health metrics."""
        pass

    @abstractmethod
    async def query_call_status(self, call_id: str, provider_call_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Query carrier for current call status during recovery and reconciliation.
        Returns status dict:
          - status: "NOT_FOUND" | "ACTIVE" | "COMPLETED" | "FAILED" | "UNKNOWN"
          - call_state: CallState string representation if active or known
          - initiated: bool
        """
        pass
