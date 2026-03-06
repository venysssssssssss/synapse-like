from abc import ABC, abstractmethod
from typing import List

from synapse_like.core.models import (
    DeviceCapabilities,
    DeviceType,
    LightingCapabilities,
    MacroCapabilities,
)

class CapabilityExtractor(ABC):
    @abstractmethod
    def extract(self, dev) -> DeviceCapabilities:
        pass

    def _lighting_modes(self, dev) -> List[str]:
        modes = []
        for candidate in ("static", "breathing", "spectrum"):
            if dev.has(candidate):
                modes.append(candidate)
        return modes or ["static"]

    def _device_id(self, dev) -> str:
        vid = getattr(dev, "usb_vid", None)
        pid = getattr(dev, "usb_pid", None)
        if vid and pid:
            return f"usb:{vid:04x}:{pid:04x}"
        product = getattr(dev, "product_id", None)
        if product:
            return f"usb:{product}"
        return getattr(dev, "serial", "unknown")

    def _extract_base_capabilities(self, dev, dev_type: DeviceType) -> DeviceCapabilities:
        lighting = None
        if dev.has("lighting"):
            lighting = LightingCapabilities(
                modes=self._lighting_modes(dev),
                brightness=dev.has("brightness"),
            )

        return DeviceCapabilities(
            device_id=self._device_id(dev),
            type=dev_type,
            lighting=lighting,
            dpi=dev.has("dpi"),
            polling_rate=dev.has("polling_rate"),
            macros=MacroCapabilities(supported=dev.has("macro")),
        )


class KeyboardCapabilityExtractor(CapabilityExtractor):
    def extract(self, dev) -> DeviceCapabilities:
        # Podes injetar mais lógica específica de teclado aqui (N-key rollover, etc)
        return self._extract_base_capabilities(dev, DeviceType.KEYBOARD)


class MouseCapabilityExtractor(CapabilityExtractor):
    def extract(self, dev) -> DeviceCapabilities:
        # Lógica de extração de features exclusivas de mouses no openrazer
        return self._extract_base_capabilities(dev, DeviceType.MOUSE)


class HeadsetCapabilityExtractor(CapabilityExtractor):
    def extract(self, dev) -> DeviceCapabilities:
        return self._extract_base_capabilities(dev, DeviceType.HEADSET)


class UnknownDeviceExtractor(CapabilityExtractor):
    def extract(self, dev) -> DeviceCapabilities:
        return self._extract_base_capabilities(dev, DeviceType.UNKNOWN)


def get_extractor(dev) -> CapabilityExtractor:
    dev_type = getattr(dev, "type", None)
    if dev_type == "keyboard":
        return KeyboardCapabilityExtractor()
    elif dev_type == "mouse":
        return MouseCapabilityExtractor()
    elif dev_type == "headset":
        return HeadsetCapabilityExtractor()
    return UnknownDeviceExtractor()
