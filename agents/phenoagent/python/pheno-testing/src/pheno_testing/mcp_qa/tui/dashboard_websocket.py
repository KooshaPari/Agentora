"""WebSocket broadcasting support for team visibility (Phase 5).

Provides WebSocket server for broadcasting test results to team members.
"""

import asyncio
import json
from typing import Any, Dict, List, Set

try:
    import websockets

    try:
        from websockets.asyncio.server import ServerConnection as WebSocketServerProtocol
    except ImportError:
        try:
            from websockets.legacy.server import WebSocketServerProtocol
        except ImportError:
            from websockets.server import WebSocketServerProtocol

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    WebSocketServerProtocol = object

import logging

logger = logging.getLogger("pheno.testing.mcp_qa.tui")


class WebSocketBroadcaster:
    """WebSocket server for broadcasting test results to team members (Phase 5)."""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        self.clients: Set[WebSocketServerProtocol] = set()
        self.running = False

    async def start(self) -> None:
        """Start WebSocket server."""
        if not HAS_WEBSOCKETS:
            logger.warning("WebSocket support not available. Install with: pip install websockets")
            return

        try:
            self.server = await websockets.serve(self.handler, self.host, self.port)
            self.running = True
            logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            self.running = False

    async def stop(self) -> None:
        """Stop WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.running = False
            logger.info("WebSocket server stopped")

    async def handler(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """Handle WebSocket connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected: {websocket.remote_address}")

        try:
            async for message in websocket:
                await websocket.send(message)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.clients.remove(websocket)
            logger.info(f"Client disconnected: {websocket.remote_address}")

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        if not self.clients:
            return

        message_json = json.dumps(message)
        await asyncio.gather(
            *[client.send(message_json) for client in self.clients], return_exceptions=True
        )

    def get_connected_users(self) -> List[Dict[str, Any]]:
        """Get list of connected users."""
        return [
            {"name": f"User-{i + 1}", "status": "Connected", "address": str(c.remote_address)}
            for i, c in enumerate(self.clients)
        ]


__all__ = [
    "WebSocketBroadcaster",
    "HAS_WEBSOCKETS",
]
