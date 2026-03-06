from abc import ABC, abstractmethod
from typing import List
from synapse_like.core.models import Device, Profile

class DeviceProvider(ABC):
    """
    Abstract interface for providing and managing hardware devices.
    Any specific hardware integration (like OpenRazer) must implement this.
    """

    @abstractmethod
    def list_devices(self) -> List[Device]:
        """Returns a list of all detected and supported devices."""
        pass

    @abstractmethod
    def apply_profile(self, profile: Profile) -> None:
        """Applies a given profile configuration to the relevant connected devices."""
        pass

    @abstractmethod
    def persist_profile(self, profile_name: str, payload: dict) -> str:
        """Attempts to persist a profile directly to compatible hardware."""
        pass
