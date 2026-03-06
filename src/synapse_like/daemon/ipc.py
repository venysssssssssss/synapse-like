from __future__ import annotations

from pathlib import Path

SOCKET_PATH = Path("/tmp/synapse-like-daemon.sock")
DAEMON_ADDRESS = str(SOCKET_PATH)
DAEMON_AUTHKEY = b"synapse-like-daemon"

__all__ = ["DAEMON_ADDRESS", "DAEMON_AUTHKEY", "SOCKET_PATH"]
