from __future__ import annotations

import logging
import shutil
import subprocess
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class WindowMonitor:
    """
    Polls the active X11 window and notifies listeners when WM_CLASS changes.
    """

    def __init__(self, interval: float = 1.0) -> None:
        self.interval = interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[str], None]] = None
        self._last_class = ""
        self._xprop_path = shutil.which("xprop")

    def start(self, callback: Callable[[str], None]) -> None:
        if self._running or self._xprop_path is None:
            return
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def current_window_class(self) -> str:
        if self._xprop_path is None:
            return ""
        try:
            active_window = subprocess.run(
                [self._xprop_path, "-root", "_NET_ACTIVE_WINDOW"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            if "window id #" not in active_window:
                return ""
            window_id = active_window.split("window id #", 1)[1].strip()
            wm_class = subprocess.run(
                [self._xprop_path, "-id", window_id, "WM_CLASS"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except Exception:
            return ""

        parts = [segment.strip().strip('"') for segment in wm_class.split(",") if '"' in segment]
        if not parts:
            return ""
        return parts[-1].casefold()

    def _loop(self) -> None:
        while self._running:
            current = self.current_window_class()
            if current and current != self._last_class:
                self._last_class = current
                if self._callback:
                    try:
                        self._callback(current)
                    except Exception as exc:
                        logger.warning("Window callback failed: %s", exc)
            time.sleep(self.interval)
