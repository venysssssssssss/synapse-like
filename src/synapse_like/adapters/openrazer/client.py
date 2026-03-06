import logging
from typing import Any, List

from synapse_like.core.models import Device, Profile
from synapse_like.core.device_provider import DeviceProvider
from synapse_like.adapters.openrazer.capabilities import get_extractor

try:
    from openrazer.client import DeviceManager

    OPENRAZER_AVAILABLE = True
except ImportError:
    OPENRAZER_AVAILABLE = False
    logging.getLogger(__name__).debug("OpenRazer python bindings not found. Running in mock mode.")


class OpenRazerAdapter(DeviceProvider):
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
            extractor = get_extractor(dev)
            capabilities = extractor.extract(dev)
            devices.append(
                Device(
                    name=dev.name,
                    serial=getattr(dev, "serial", None),
                    capabilities=capabilities,
                )
            )
        return devices

    def apply_profile(self, profile: Profile) -> None:
        """
        Apply a profile to all connected devices.
        Real hardware commands are no-ops when OpenRazer is unavailable.
        """
        devices = self.list_devices()
        if not devices:
            logging.info("No devices available to apply profile.")
            return

        for dev in devices:
            # dev is our Model, but we need the raw openrazer device to apply things.
            # We match them by serial. Alternatively, we could retrieve from device_manager directly.
            # We find the matching openrazer raw device via serial
            raw_dev = self._find_raw_device_by_serial(dev.serial)
            if not raw_dev:
                continue

            settings = profile.settings.get(dev.capabilities.device_id)
            if not settings:
                continue
            
            if dev.capabilities.lighting and settings.get("lighting"):
                self._apply_lighting(raw_dev, settings["lighting"])
            if dev.capabilities.dpi and settings.get("dpi"):
                self._apply_dpi(raw_dev, settings["dpi"])
            if dev.capabilities.polling_rate and settings.get("polling_rate"):
                self._apply_polling(raw_dev, settings["polling_rate"])

    def persist_profile(self, profile_name: str, payload: dict) -> str:
        """
        Best-effort persistence for devices that expose onboard profile APIs.
        The exact OpenRazer surface varies by hardware, so this probes common hooks.
        """
        if not OPENRAZER_AVAILABLE:
            return "OpenRazer indisponivel no ambiente atual."

        persisted = 0
        for raw_dev in self.device_manager.devices:
            if self._persist_on_device(raw_dev, profile_name, payload):
                persisted += 1

        if persisted == 0:
            return "Nenhum dispositivo conectado expôs API de persistência onboard."
        return f"Perfil persistido em {persisted} dispositivo(s) compatível(is)."

    def _find_raw_device_by_serial(self, serial):
        if not OPENRAZER_AVAILABLE:
            return None
        for dev in self.device_manager.devices:
            if getattr(dev, "serial", None) == serial:
                return dev
        return None

    def _apply_lighting(self, raw_dev, cfg):
        if not OPENRAZER_AVAILABLE:
            logging.info("Mock apply lighting: %s -> %s", raw_dev.name, cfg)
            return
        try:
            if "brightness" in cfg and raw_dev.has("brightness"):
                raw_dev.brightness = int(cfg["brightness"])
            if "mode" in cfg and hasattr(raw_dev, "set_effect"):
                raw_dev.set_effect(cfg["mode"])
        except Exception as exc:
            logging.error("Failed to apply lighting to %s: %s", raw_dev.name, exc)

    def _apply_dpi(self, raw_dev, value: int):
        if not OPENRAZER_AVAILABLE:
            logging.info("Mock apply DPI: %s -> %s", raw_dev.name, value)
            return
        try:
            if raw_dev.has("dpi"):
                raw_dev.dpi = int(value)
        except Exception as exc:
            logging.error("Failed to set DPI on %s: %s", raw_dev.name, exc)

    def _apply_polling(self, raw_dev, value: int):
        if not OPENRAZER_AVAILABLE:
            logging.info("Mock apply polling: %s -> %s", raw_dev.name, value)
            return
        try:
            if raw_dev.has("polling_rate"):
                raw_dev.polling_rate = int(value)
        except Exception as exc:
            logging.error("Failed to set polling on %s: %s", raw_dev.name, exc)

    def _persist_on_device(self, raw_dev: Any, profile_name: str, payload: dict) -> bool:
        candidate_calls = (
            ("save_profile", (profile_name, payload)),
            ("persist_profile", (profile_name, payload)),
            ("set_profile", (profile_name,)),
        )
        for attr_name, args in candidate_calls:
            method = getattr(raw_dev, attr_name, None)
            if not callable(method):
                continue
            try:
                method(*args)
                return True
            except Exception as exc:
                logging.error("Failed to persist profile on %s via %s: %s", raw_dev.name, attr_name, exc)
                return False
        return False
