"""
Port management utilities.
"""

from __future__ import annotations

import socket
import subprocess


class PortManager:
    """
    Manage port allocation and availability.
    """

    @staticmethod
    def is_port_available(port: int) -> bool:
        """Check if a port is available.

        Args:
            port: Port number to check

        Returns:
            True if port is available
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("", port))
                return True
            except OSError:
                return False

    @staticmethod
    def find_free_port(start: int = 8000, end: int = 9000) -> int | None:
        """Find a free port in range.

        Args:
            start: Start of port range
            end: End of port range

        Returns:
            Free port number or None if none available
        """
        for port in range(start, end):
            if PortManager.is_port_available(port):
                return port
        return None

    @staticmethod
    def get_process_on_port(port: int) -> str | None:
        """Get process using a port.

        Args:
            port: Port number

        Returns:
            Process information or None
        """
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-sTCP:LISTEN"], check=False, capture_output=True, text=True,
            )
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    return lines[1].split()[0]
        except FileNotFoundError:
            pass

        return None

    @staticmethod
    def kill_process_on_port(port: int) -> bool:
        """Kill process using a port.

        Args:
            port: Port number

        Returns:
            True if killed successfully
        """
        try:
            result = subprocess.run(["lsof", "-ti", f":{port}"], check=False, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    subprocess.run(["kill", "-9", pid], check=False)
                return True
        except Exception:
            pass

        return False
