"""
WebSocket communication for real-time collaboration.
"""

import asyncio
import time
from typing import Callable, List, Optional, Set

import websockets

from .models import TestEvent

try:
    from websockets.asyncio.client import ClientConnection as WebSocketClientProtocol
    from websockets.asyncio.server import ServerConnection as WebSocketServerProtocol
except ImportError:
    try:
        from websockets.legacy.client import WebSocketClientProtocol
        from websockets.legacy.server import WebSocketServerProtocol
    except ImportError:
        from websockets.client import WebSocketClientProtocol
        from websockets.server import WebSocketServerProtocol


class WebSocketBroadcaster:
    """
    Broadcast test events to team members via WebSocket.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.running = False
        self.message_handlers: List[Callable] = []

    async def start_server(self):
        """
        Start WebSocket server.
        """
        self.server = await websockets.serve(self._handle_client, self.host, self.port)
        self.running = True
        print(f"WebSocket server started on {self.host}:{self.port}")

    async def stop_server(self):
        """
        Stop WebSocket server.
        """
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients], return_exceptions=True
            )
        self.clients.clear()
        print("WebSocket server stopped")

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """
        Handle new client connection.
        """
        self.clients.add(websocket)
        print(f"Client connected. Total clients: {len(self.clients)}")

        try:
            async for message in websocket:
                for handler in self.message_handlers:
                    try:
                        await handler(message, websocket)
                    except Exception as e:
                        print(f"Handler error: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
            print(f"Client disconnected. Total clients: {len(self.clients)}")

    async def broadcast(self, event: TestEvent):
        """
        Broadcast event to all connected clients.
        """
        if not self.clients:
            return

        message = event.to_json()
        await asyncio.gather(
            *[self._send_to_client(client, message) for client in self.clients],
            return_exceptions=True,
        )

    async def _send_to_client(self, client: WebSocketServerProtocol, message: str):
        """
        Send message to a single client.
        """
        try:
            await client.send(message)
        except websockets.exceptions.ConnectionClosed:
            self.clients.discard(client)
        except Exception as e:
            print(f"Error sending to client: {e}")

    def add_message_handler(self, handler: Callable):
        """
        Add a message handler.
        """
        self.message_handlers.append(handler)

    async def broadcast_test_start(self, test_name: str, endpoint: str, user: str):
        """
        Broadcast test start event.
        """
        event = TestEvent(
            event_type="started",
            test_name=test_name,
            endpoint=endpoint,
            user=user,
            timestamp=time.time(),
            data={},
        )
        await self.broadcast(event)

    async def broadcast_test_complete(
        self,
        test_name: str,
        endpoint: str,
        user: str,
        success: bool,
        duration: float,
        details: dict,
    ):
        """
        Broadcast test completion event.
        """
        event = TestEvent(
            event_type="completed" if success else "failed",
            test_name=test_name,
            endpoint=endpoint,
            user=user,
            timestamp=time.time(),
            data={"success": success, "duration": duration, "details": details},
        )
        await self.broadcast(event)


class WebSocketClient:
    """
    WebSocket client for receiving broadcasts.
    """

    def __init__(self, uri: str):
        self.uri = uri
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connected = False
        self.message_handlers: List[Callable] = []

    async def connect(self):
        """
        Connect to WebSocket server.
        """
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print(f"Connected to {self.uri}")
        except Exception as e:
            print(f"Connection failed: {e}")
            raise

    async def disconnect(self):
        """
        Disconnect from WebSocket server.
        """
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("Disconnected from server")

    async def listen(self):
        """
        Listen for messages from server.
        """
        if not self.websocket:
            raise RuntimeError("Not connected")

        try:
            async for message in self.websocket:
                event = TestEvent.from_json(message)
                for handler in self.message_handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        print(f"Handler error: {e}")
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            print("Connection closed by server")

    def add_message_handler(self, handler: Callable):
        """
        Add a message handler.
        """
        self.message_handlers.append(handler)
