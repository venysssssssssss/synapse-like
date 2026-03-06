from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional

try:
    import pyudev
except ImportError:
    pyudev = None

from synapse_like.remap.device_paths import card_name, detect_razer_devices, path_kind

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DeviceInfo:
    path: str
    name: str
    kind: str
    vid: Optional[str] = None
    pid: Optional[str] = None


class DeviceManager:
    """
    Tracks input devices and exposes hotplug notifications.
    """

    def __init__(self) -> None:
        self._context = pyudev.Context() if pyudev else None
        self._devices: list[DeviceInfo] = []
        self._callbacks: list[Callable[[list[DeviceInfo]], None]] = []
        self._monitor_stop = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

    def scan(self) -> list[DeviceInfo]:
        self._devices = [self._build_info(path) for path in detect_razer_devices()]
        return list(self._devices)

    def get_primary_devices(self) -> list[DeviceInfo]:
        devices = self._devices or self.scan()
        primary = [
            device
            for device in devices
            if device.path.endswith("-event-kbd") or device.path.endswith("-event-mouse")
        ]
        return primary or devices[:4]

    def get_device_by_path(self, path: str) -> Optional[DeviceInfo]:
        for device in self._devices:
            if device.path == path:
                return device
        return None

    def subscribe(self, callback: Callable[[list[DeviceInfo]], None]) -> None:
        self._callbacks.append(callback)

    def start_monitoring(self) -> None:
        if self._monitor_thread is not None or pyudev is None:
            return
        self._monitor_stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        self._monitor_stop.set()
        self._monitor_thread = None

    def _monitor_loop(self) -> None:
        if self._context is None or pyudev is None:
            return
        monitor = pyudev.Monitor.from_netlink(self._context)
        monitor.filter_by(subsystem="input")
        for _device in iter(monitor.poll, None):
            if self._monitor_stop.is_set():
                return
            devices = self.scan()
            for callback in self._callbacks:
                try:
                    callback(devices)
                except Exception as exc:
                    logger.warning("Device hotplug callback failed: %s", exc)

    def _build_info(self, path: str) -> DeviceInfo:
        info = DeviceInfo(path=path, name=card_name(path), kind=path_kind(path))
        if self._context and os.path.exists(path):
            try:
                device = pyudev.Devices.from_device_file(self._context, path)
                info.vid = device.get("ID_VENDOR_ID")
                info.pid = device.get("ID_MODEL_ID")
            except Exception:
                pass
        return info
