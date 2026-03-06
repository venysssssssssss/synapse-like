from __future__ import annotations

import logging
import queue
import subprocess
import sys
import threading
import time
from multiprocessing.connection import Client
from typing import Any, Dict, Optional

from synapse_like.daemon.ipc import DAEMON_ADDRESS, DAEMON_AUTHKEY
from synapse_like.remap.actions import Action

logger = logging.getLogger(__name__)


class RemapService:
    """
    GUI-side client for the remap daemon.
    """

    def __init__(self) -> None:
        self.active_count = 0
        self.busy = False
        self.service_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self._thread: Optional[threading.Thread] = None

    def is_busy(self) -> bool:
        return self.busy

    def is_active(self) -> bool:
        return self.active_count > 0

    def apply_configuration(self, device_path: str, mappings: Dict[str, Action]) -> None:
        if self.busy:
            return
        self.busy = True
        self._thread = threading.Thread(
            target=self._apply_worker,
            args=(device_path, dict(mappings)),
            daemon=True,
        )
        self._thread.start()

    def stop_all(self) -> None:
        if self.busy:
            return
        self.busy = True
        self._thread = threading.Thread(target=self._stop_worker, daemon=True)
        self._thread.start()

    def shutdown_daemon(self) -> None:
        self._send_command({"command": "SHUTDOWN"})

    def get_input_state(self) -> list[str]:
        if not self.is_active():
            return []
        response = self._send_command({"command": "GET_INPUT_STATE"})
        return response.get("active_keys", [])

    def get_status(self) -> Dict[str, Any]:
        return self._send_command({"command": "STATUS"})

    def _apply_worker(self, device_path: str, mappings: Dict[str, Action]) -> None:
        response = self._send_command(
            {
                "command": "APPLY",
                "device": device_path,
                "mappings": {code: action.to_dict() for code, action in mappings.items()},
            }
        )
        self.active_count = int(response.get("active_count", 0))
        self.busy = False
        self.service_queue.put(
            {
                "kind": "apply_done",
                "active_count": self.active_count,
                "failures": response.get("failures", []),
                "low_latency": bool(response.get("low_latency", False)),
            }
        )

    def _stop_worker(self) -> None:
        response = self._send_command({"command": "STOP"})
        self.active_count = 0
        self.busy = False
        self.service_queue.put({"kind": "stop_done", "failures": response.get("failures", [])})

    def _send_command(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_daemon()
        try:
            with Client(DAEMON_ADDRESS, authkey=DAEMON_AUTHKEY, family="AF_UNIX") as connection:
                connection.send(payload)
                response = connection.recv()
                return response if isinstance(response, dict) else {"status": "error", "error": "Invalid daemon response"}
        except Exception as exc:
            logger.error("IPC error: %s", exc)
            self.busy = False
            return {"status": "error", "error": str(exc), "active_count": 0, "failures": [str(exc)]}

    def _ensure_daemon(self) -> None:
        try:
            with Client(DAEMON_ADDRESS, authkey=DAEMON_AUTHKEY, family="AF_UNIX") as connection:
                connection.send({"command": "PING"})
                connection.recv()
                return
        except Exception:
            pass

        logger.info("Daemon not running; starting background process")
        subprocess.Popen(
            [sys.executable, "-m", "synapse_like.daemon.process"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._wait_for_daemon()

    def _wait_for_daemon(self, timeout: float = 2.5) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with Client(DAEMON_ADDRESS, authkey=DAEMON_AUTHKEY, family="AF_UNIX") as connection:
                    connection.send({"command": "PING"})
                    connection.recv()
                    return
            except Exception:
                time.sleep(0.1)
