from __future__ import annotations

import logging
import os
import threading
import time
from multiprocessing.connection import Listener
from pathlib import Path
from typing import Any, Dict, List, Optional

from synapse_like.daemon.ipc import DAEMON_ADDRESS, DAEMON_AUTHKEY, SOCKET_PATH
from synapse_like.remap.actions import Action
from synapse_like.remap.device_paths import expand_related_paths
from synapse_like.remap.mapper import InputMapper, MappingConfig
from synapse_like.remap.strategy import is_aux_pointer_only_mapping

logging.basicConfig(
    level=logging.INFO,
    format="[daemon] %(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class RemapDaemon:
    def __init__(self) -> None:
        self._running = True
        self._listener = self._build_listener()
        self._mappers: list[InputMapper] = []
        self._active_device: Optional[str] = None
        self._active_mappings: Dict[str, Action] = {}
        self._hotplug_thread = threading.Thread(target=self._monitor_hotplug, daemon=True)
        self._hotplug_thread.start()

    def _build_listener(self) -> Listener:
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        return Listener(DAEMON_ADDRESS, authkey=DAEMON_AUTHKEY, family="AF_UNIX")

    def run(self) -> None:
        logger.info("Daemon listening at %s", DAEMON_ADDRESS)
        while self._running:
            try:
                connection = self._listener.accept()
            except OSError:
                if not self._running:
                    break
                raise

            try:
                while self._running:
                    try:
                        payload = connection.recv()
                    except EOFError:
                        break
                    response = self._handle_message(payload if isinstance(payload, dict) else {})
                    connection.send(response)
            finally:
                connection.close()

        self._cleanup_socket()

    def _handle_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        command = str(payload.get("command", "")).upper()
        if command == "PING":
            return {"status": "ok", "payload": "pong"}
        if command == "STATUS":
            return {
                "status": "ok",
                "active_count": len(self._mappers),
                "device": self._active_device,
                "low_latency": is_aux_pointer_only_mapping(self._active_mappings),
            }
        if command == "GET_INPUT_STATE":
            return {"status": "ok", "active_keys": self._collect_active_keys()}
        if command == "STOP":
            return self._stop_all()
        if command == "APPLY":
            return self._apply_config(
                device=str(payload.get("device", "")),
                mappings=self._deserialize_mappings(payload.get("mappings", {})),
            )
        if command == "SHUTDOWN":
            response = self._stop_all()
            self._running = False
            try:
                self._listener.close()
            except Exception:
                pass
            return response
        return {"status": "error", "error": f"Unknown command: {command}"}

    def _apply_config(self, device: str, mappings: Dict[str, Action]) -> Dict[str, Any]:
        self._active_device = device
        self._active_mappings = dict(mappings)
        self._stop_all()

        failures: list[str] = []
        started_paths: list[str] = []
        low_latency = is_aux_pointer_only_mapping(mappings)
        paths = expand_related_paths(device)
        if not paths:
            return {"status": "error", "failures": ["Nenhum device encontrado"], "active_count": 0}

        for path in paths:
            use_fast_mode = low_latency and "-if" in path
            try:
                mapper = InputMapper(
                    MappingConfig(
                        device_path=path,
                        mappings=mappings,
                        grab=not use_fast_mode,
                        passthrough=not use_fast_mode,
                    )
                )
                mapper.start()
                self._mappers.append(mapper)
                started_paths.append(path)
            except Exception as exc:
                failures.append(f"{path}: {exc}")
                logger.error("Failed to start mapper for %s: %s", path, exc)

        return {
            "status": "ok",
            "active_count": len(self._mappers),
            "failures": failures,
            "low_latency": low_latency,
            "paths": started_paths,
        }

    def _stop_all(self) -> Dict[str, Any]:
        failures: list[str] = []
        while self._mappers:
            mapper = self._mappers.pop()
            try:
                mapper.stop()
            except Exception as exc:
                failures.append(str(exc))
        return {"status": "ok", "active_count": 0, "failures": failures}

    def _collect_active_keys(self) -> list[str]:
        keys: set[str] = set()
        for mapper in self._mappers:
            keys.update(mapper.active_keys)
        return sorted(keys)

    def _deserialize_mappings(self, raw_mappings: Any) -> Dict[str, Action]:
        if not isinstance(raw_mappings, dict):
            return {}
        return {
            str(code): Action.from_dict(payload)
            for code, payload in raw_mappings.items()
            if isinstance(payload, dict)
        }

    def _monitor_hotplug(self) -> None:
        try:
            import pyudev
        except ImportError:
            logger.info("pyudev not installed; daemon hotplug disabled")
            return

        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem="input")
        for device in iter(monitor.poll, None):
            if not self._running:
                return
            if device.action != "add" or not self._active_device or not self._active_mappings:
                continue
            time.sleep(0.8)
            logger.info("Hotplug detected; reapplying active configuration")
            self._apply_config(self._active_device, self._active_mappings)

    def _cleanup_socket(self) -> None:
        try:
            self._listener.close()
        except Exception:
            pass
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()


def main() -> None:
    daemon = RemapDaemon()
    try:
        daemon.run()
    finally:
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()


if __name__ == "__main__":
    main()
