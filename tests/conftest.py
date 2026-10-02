"""Pytest configuration and network isolation fixtures.

Enforces zero live outbound network access during test runs.
"""

import os
import socket
import pytest

# Ensure background scheduler is always disabled during test sessions
os.environ["ENABLE_SCHEDULER"] = "false"


@pytest.fixture(autouse=True)
def block_external_sockets(monkeypatch):
    """Enforce strict network isolation: block all real outbound socket connections."""
    orig_connect = socket.socket.connect

    def guarded_connect(self, address):
        # Allow loopback/in-memory connections if local test server is used
        host = address[0] if isinstance(address, (tuple, list)) and len(address) > 0 else str(address)
        if host in ("127.0.0.1", "localhost", "::1"):
            return orig_connect(self, address)
        raise RuntimeError(
            f"Live network access blocked by test suite! Attempted connection to: {address}. "
            "All weather data and external APIs must be strictly mocked."
        )

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
