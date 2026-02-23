import logging
from typing import List

from synapse_like.core.models import (
    Device,
    DeviceType,
    DeviceCapabilities,
    LightingCapabilities,
    MacroCapabilities,
)

try:
    from openrazer.client import DeviceManager

    OPENRAZER_AVAILABLE = True
except ImportError:
    OPENRAZER_AVAILABLE = False
    # Keep import quiet for GUI-only usage; CLI commands already report availability.
    logging.getLogger(__name__).debug("OpenRazer python bindings not found. Running in mock mode.")


class OpenRazerAdapter:
    def __init__(self):
        if OPENRAZER_AVAILABLE:
            self.device_manager = DeviceManager()
        else:
            self.device_manager = None

    def list_devices(self) -> List[Device]:
        """
        Return connected devices with extracted capabilities.
        When OpenRazer bindings are missing, returns an empty list.
        """
        if not OPENRAZER_AVAILABLE:
            return []

        devices: List[Device] = []
        for dev in self.device_manager.devices:
            capabilities = self._extract_capabilities(dev)
            devices.append(
                Device(
                    name=dev.name,
                    serial=getattr(dev, "serial", None),
                    capabilities=capabilities,
                )
            )
        return devices

    def _extract_capabilities(self, dev) -> DeviceCapabilities:
        """Translate OpenRazer device into stable capability object."""
        dev_type = DeviceType.UNKNOWN
        if getattr(dev, "type", None) == "keyboard":
            dev_type = DeviceType.KEYBOARD
        elif getattr(dev, "type", None) == "mouse":
            dev_type = DeviceType.MOUSE

        lighting = None
        if dev.has("lighting"):
            lighting = LightingCapabilities(
                modes=self._lighting_modes(dev),
                brightness=dev.has("brightness"),
            )

        device_id = self._device_id(dev)

        return DeviceCapabilities(
            device_id=device_id,
            type=dev_type,
            lighting=lighting,
            dpi=dev.has("dpi"),
            polling_rate=dev.has("polling_rate"),
            macros=MacroCapabilities(supported=dev.has("macro")),
        )

    def _lighting_modes(self, dev) -> List[str]:
        """Best-effort discovery of lighting modes."""
        modes = []
        for candidate in ("static", "breathing", "spectrum"):
            if dev.has(candidate):
                modes.append(candidate)
        # Fallback to common defaults
        return modes or ["static"]

    def _device_id(self, dev) -> str:
        """Compose stable device_id like usb:1532:011a."""
        vid = getattr(dev, "usb_vid", None)
        pid = getattr(dev, "usb_pid", None)
        if vid and pid:
            return f"usb:{vid:04x}:{pid:04x}"
        product = getattr(dev, "product_id", None)
        if product:
            return f"usb:{product}"
        return getattr(dev, "serial", "unknown")

    def apply_profile(self, profile):
        """
        Apply a profile to all connected devices.
        Real hardware commands are no-ops when OpenRazer is unavailable.
        """
        devices = self.list_devices()
        if not devices:
            logging.info("No devices available to apply profile.")
            return

        for dev in devices:
            settings = profile.settings.get(dev.capabilities.device_id)
            if not settings:
                continue
            if dev.capabilities.lighting and settings.get("lighting"):
                self._apply_lighting(dev, settings["lighting"])
            if dev.capabilities.dpi and settings.get("dpi"):
                self._apply_dpi(dev, settings["dpi"])
            if dev.capabilities.polling_rate and settings.get("polling_rate"):
                self._apply_polling(dev, settings["polling_rate"])

    def _apply_lighting(self, dev, cfg):
        if not OPENRAZER_AVAILABLE:
            logging.info("Mock apply lighting: %s -> %s", dev.name, cfg)
            return
        try:
            if "brightness" in cfg and dev.has("brightness"):
                dev.brightness = int(cfg["brightness"])
            if "mode" in cfg and hasattr(dev, "set_effect"):
                dev.set_effect(cfg["mode"])
        except Exception as exc:
            logging.error("Failed to apply lighting to %s: %s", dev.name, exc)

    def _apply_dpi(self, dev, value: int):
        if not OPENRAZER_AVAILABLE:
            logging.info("Mock apply DPI: %s -> %s", dev.name, value)
            return
        try:
            if dev.has("dpi"):
                dev.dpi = int(value)
        except Exception as exc:
            logging.error("Failed to set DPI on %s: %s", dev.name, exc)

    def _apply_polling(self, dev, value: int):
        if not OPENRAZER_AVAILABLE:
            logging.info("Mock apply polling: %s -> %s", dev.name, value)
            return
        try:
            if dev.has("polling_rate"):
                dev.polling_rate = int(value)
        except Exception as exc:
            logging.error("Failed to set polling on %s: %s", dev.name, exc)
