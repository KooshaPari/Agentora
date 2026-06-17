"""
Port allocation utilities.
"""

from __future__ import annotations

import socket

from .options import DefaultLogger, Logger


def allocate_free_port(preferred: int | None = None, logger: Logger | None = None) -> int:
    """Find an available port with smart fallback logic.

    Mirrors legacy behavior from kinfra_networking.allocate_free_port.
    """
    if logger is None:
        logger = DefaultLogger()

    def try_bind(port: int) -> int | None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if port == 0:
                sock.bind(("", 0))
                actual = sock.getsockname()[1]
            else:
                sock.bind(("", port))
                actual = port
            sock.close()
            return actual
        except OSError:
            return None

    if preferred and preferred > 0:
        actual_port = try_bind(preferred)
        if actual_port:
            logger.info(f"Port allocation: using preferred port {actual_port}")
            return actual_port
        logger.warn(f"Port allocation: preferred port {preferred} unavailable, falling back")

    picked = try_bind(0)
    if picked:
        logger.info(f"Port allocation: OS assigned port {picked}")
        return picked

    raise RuntimeError("Failed to allocate a free port")
