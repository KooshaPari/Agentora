"""
Phenotype Shim - Python client for phenotype-daemon

Thin wrapper (~60 lines) that communicates with phenotype-daemon
via Unix sockets using msgpack-rpc. Much faster than stdio MCP.
"""

import socket
import struct
import subprocess
import os
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

try:
    import msgpack
except ImportError:
    raise ImportError("msgpack required: pip install msgpack")


@dataclass
class SkillManifest:
    """Skill manifest definition"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    runtime: str = "wasm"
    entry_point: str = ""
    dependencies: List[Dict[str, Any]] = None
    permissions: List[Dict[str, str]] = None
    priority: str = "normal"
    metadata: Dict[str, str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.permissions is None:
            self.permissions = []
        if self.metadata is None:
            self.metadata = {}


class PhenotypeClient:
    """Phenotype client - auto-spawns daemon if needed"""

    def __init__(self, socket_path: str = "/tmp/phenotype.sock"):
        self.socket_path = socket_path
        self._daemon_proc: Optional[subprocess.Popen] = None

    def _ensure_daemon(self) -> None:
        """Ensure daemon is running"""
        if os.path.exists(self.socket_path):
            # Verify daemon is responsive
            try:
                self.ping()
                return
            except Exception:
                # Stale socket, remove it
                os.unlink(self.socket_path)

        # Spawn daemon
        daemon_path = self._find_daemon()
        self._daemon_proc = subprocess.Popen(
            [daemon_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait for socket
        for _ in range(50):
            time.sleep(0.1)
            if os.path.exists(self.socket_path):
                return

        raise RuntimeError("Daemon failed to start")

    def _find_daemon(self) -> str:
        """Find daemon binary"""
        candidates = [
            Path(__file__).parent / "bin" / "phenotype-daemon",
            Path(__file__).parent.parent.parent / "phenotype-daemon",
            Path.home() / ".cargo" / "bin" / "phenotype-daemon",
            "phenotype-daemon",
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        return "phenotype-daemon"  # Hope it's in PATH

    def _rpc(self, method: str, params: Dict[str, Any]) -> Any:
        """Make RPC call"""
        self._ensure_daemon()

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path)

        try:
            # Send request
            request = {"method": method, "params": params}
            encoded = msgpack.packb(request, use_bin_type=True)
            sock.sendall(struct.pack(">I", len(encoded)))
            sock.sendall(encoded)

            # Receive response
            length_data = sock.recv(4)
            if not length_data:
                raise ConnectionError("Daemon closed connection")

            length = struct.unpack(">I", length_data)[0]
            response_data = b""
            while len(response_data) < length:
                chunk = sock.recv(length - len(response_data))
                if not chunk:
                    raise ConnectionError("Connection closed unexpectedly")
                response_data += chunk

            response = msgpack.unpackb(response_data, raw=False)

            if response.get("result") == "error":
                raise RuntimeError(response.get("message", "RPC error"))

            return response.get("data")
        finally:
            sock.close()

    # === Public API ===

    def ping(self) -> str:
        """Ping daemon"""
        return self._rpc("ping", {})

    def register_skill(self, manifest: SkillManifest) -> str:
        """Register a skill"""
        result = self._rpc("skill.register", {"manifest": manifest.__dict__})
        return result["id"]

    def get_skill(self, skill_id: str) -> Optional[SkillManifest]:
        """Get skill by ID"""
        try:
            data = self._rpc("skill.get", {"id": skill_id})
            return SkillManifest(**data)
        except RuntimeError:
            return None

    def list_skills(self) -> List[str]:
        """List all skills"""
        return self._rpc("skill.list", {})

    def unregister_skill(self, skill_id: str) -> bool:
        """Unregister a skill"""
        self._rpc("skill.unregister", {"id": skill_id})
        return True

    def skill_exists(self, skill_id: str) -> bool:
        """Check if skill exists"""
        return self._rpc("skill.exists", {"id": skill_id})

    def resolve_dependencies(self, skill_ids: List[str]) -> List[str]:
        """Resolve dependencies"""
        result = self._rpc("resolve", {"skill_ids": skill_ids})
        return result.get("resolved", [])

    def check_circular(self, skill_ids: List[str]) -> bool:
        """Check for circular dependencies"""
        try:
            result = self._rpc("check_circular", {"skill_ids": skill_ids})
            return result.get("circular", False)
        except RuntimeError:
            return True  # Error indicates circular

    def version(self) -> Dict[str, Any]:
        """Get daemon version"""
        return self._rpc("version", {})

    def close(self) -> None:
        """Close client and cleanup"""
        if self._daemon_proc:
            self._daemon_proc.terminate()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Convenience function
def create_client(socket_path: Optional[str] = None) -> PhenotypeClient:
    """Create and verify client connection"""
    client = PhenotypeClient(socket_path)
    client.ping()
    return client
