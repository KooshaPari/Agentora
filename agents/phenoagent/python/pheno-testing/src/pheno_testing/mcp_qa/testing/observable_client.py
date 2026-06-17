"""Observable MCP Client with Real-Time Progress Tracking.

Wraps an MCP client to track:
- Tool calls in progress
- Call durations
- Success/failure rates
- Updates progress displays in real-time

Usage in pytest:
    @pytest.mark.asyncio
    async def test_my_feature(mcp_client):
        result = await mcp_client.call_tool("my_tool", arg="value")
        assert result["success"]
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional


class ProgressObserver:
    """Interface for progress observers.

    Implement this to receive real-time updates from ObservableMCPClient.
    """

    def on_call_start(self, tool_name: str, arguments: Dict[str, Any], call_id: str):
        """
        Called when a tool call starts.
        """
        pass

    def on_call_complete(self, tool_name: str, duration_ms: float, success: bool, call_id: str):
        """
        Called when a tool call completes.
        """
        pass

    def on_call_error(self, tool_name: str, error: str, duration_ms: float, call_id: str):
        """
        Called when a tool call errors.
        """
        pass


class LiveProgressObserver(ProgressObserver):
    """Progress observer that updates a live progress display.

    Shows currently running tests in real-time.
    """

    def __init__(self, display=None):
        """Initialize with optional progress display.

        Args:
            display: Optional ComprehensiveProgressDisplay instance
        """
        self.display = display
        self._running_calls: Dict[str, float] = {}  # call_id -> start_time
        self._lock = asyncio.Lock()

    def on_call_start(self, tool_name: str, arguments: Dict[str, Any], call_id: str):
        """
        Track call start.
        """
        self._running_calls[call_id] = time.time()

        # Update display if available
        if self.display and hasattr(self.display, "start_test"):
            # Extract test name from call context if available
            test_name = arguments.get("_test_name", tool_name)
            self.display.start_test(test_name)

    def on_call_complete(self, tool_name: str, duration_ms: float, success: bool, call_id: str):
        """
        Track call completion.
        """
        if call_id in self._running_calls:
            del self._running_calls[call_id]

    def on_call_error(self, tool_name: str, error: str, duration_ms: float, call_id: str):
        """
        Track call error.
        """
        if call_id in self._running_calls:
            del self._running_calls[call_id]

    def get_running_calls(self) -> List[Dict[str, Any]]:
        """
        Get list of currently running calls with durations.
        """
        current_time = time.time()
        return [
            {"call_id": call_id, "duration": current_time - start_time}
            for call_id, start_time in self._running_calls.items()
        ]


class ObservableMCPClient:
    """MCP client wrapper that provides real-time observability.

    Tracks all tool calls and notifies observers with:
    - Call start events
    - Call completion events
    - Success/failure status
    - Call durations

    This enables:
    - Real-time progress displays showing running tests
    - Performance monitoring
    - Live test status updates

    Usage:
        # In conftest.py
        @pytest.fixture
        async def mcp_client(unified_runner):
            client = ObservableMCPClient(
                unified_runner.client,
                observer=LiveProgressObserver(display)
            )
            return client

        # In tests
        async def test_feature(mcp_client):
            # Progress display automatically updated!
            result = await mcp_client.call_tool("workspace_tool", operation="list")
            assert result["success"]
    """

    def __init__(
        self, base_client, observer: Optional[ProgressObserver] = None, verbose: bool = False
    ):
        """Initialize observable client.

        Args:
            base_client: Underlying MCP client (from fastmcp)
            observer: Optional ProgressObserver for real-time updates
            verbose: Enable verbose logging
        """
        self._base_client = base_client
        self._observer = observer
        self._verbose = verbose
        self._call_counter = 0
        self._stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_duration_ms": 0.0,
        }

    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a tool with observability.

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool result
        """
        arguments = arguments or {}
        self._call_counter += 1
        call_id = f"{tool_name}_{self._call_counter}"

        # Notify observer: call started
        if self._observer:
            self._observer.on_call_start(tool_name, arguments, call_id)

        start_time = time.perf_counter()
        error = None

        try:
            # Make the actual call
            result = await self._base_client.call_tool(tool_name, arguments=arguments)

            duration_ms = (time.perf_counter() - start_time) * 1000

            # Update stats
            self._stats["total_calls"] += 1
            self._stats["successful_calls"] += 1
            self._stats["total_duration_ms"] += duration_ms

            # Notify observer: call completed
            if self._observer:
                self._observer.on_call_complete(tool_name, duration_ms, True, call_id)

            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            error = str(e)

            # Update stats
            self._stats["total_calls"] += 1
            self._stats["failed_calls"] += 1
            self._stats["total_duration_ms"] += duration_ms

            # Notify observer: call errored
            if self._observer:
                self._observer.on_call_error(tool_name, error, duration_ms, call_id)

            raise

    async def list_tools(self):
        """
        List available tools.
        """
        return await self._base_client.list_tools()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get call statistics.
        """
        stats = self._stats.copy()
        if stats["total_calls"] > 0:
            stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_calls"]
            stats["success_rate"] = stats["successful_calls"] / stats["total_calls"]
        return stats

    @property
    def base_client(self):
        """
        Access underlying base client.
        """
        return self._base_client

    def attach_observer(self, observer: ProgressObserver):
        """
        Attach a new observer.
        """
        self._observer = observer

    def detach_observer(self):
        """
        Detach current observer.
        """
        self._observer = None


# Pytest fixture helper
def create_observable_client(base_client, progress_display=None):
    """Helper to create an observable client with optional progress display.

    Args:
        base_client: Base MCP client
        progress_display: Optional progress display instance

    Returns:
        ObservableMCPClient instance
    """
    observer = None
    if progress_display:
        observer = LiveProgressObserver(progress_display)

    return ObservableMCPClient(base_client, observer=observer)


# Context manager for scoped observation
@asynccontextmanager
async def observe_calls(client, observer: ProgressObserver):
    """Context manager to temporarily attach an observer.

    Usage:
        async with observe_calls(client, MyObserver()) as observed_client:
            await observed_client.call_tool("tool", arg="value")
    """
    old_observer = getattr(client, "_observer", None)
    client.attach_observer(observer)
    try:
        yield client
    finally:
        if old_observer:
            client.attach_observer(old_observer)
        else:
            client.detach_observer()
