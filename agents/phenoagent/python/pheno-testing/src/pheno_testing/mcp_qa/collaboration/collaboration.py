"""
Phase 5: Collaboration Features
Real-time test coordination and team collaboration tools.
"""

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List, Optional, Set

import websockets

# Handle websockets import deprecation
try:
    # Try new asyncio implementation first (websockets >= 14.0)
    from websockets.asyncio.client import ClientConnection as WebSocketClientProtocol
    from websockets.asyncio.server import ServerConnection as WebSocketServerProtocol
except ImportError:
    try:
        # Fall back to legacy implementation
        from websockets.legacy.client import WebSocketClientProtocol
        from websockets.legacy.server import WebSocketServerProtocol
    except ImportError:
        # Very old versions
        from websockets.client import WebSocketClientProtocol
        from websockets.server import WebSocketServerProtocol


@dataclass
class TestEvent:
    """
    Test event for broadcasting.
    """

    event_type: str  # started, completed, failed, etc.
    test_name: str
    endpoint: str
    user: str
    timestamp: float
    data: Dict[str, Any]

    def to_json(self) -> str:
        """
        Convert to JSON string.
        """
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, json_str: str) -> "TestEvent":
        """
        Create from JSON string.
        """
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class PresenceInfo:
    """
    User presence information.
    """

    user: str
    endpoint: str
    test_name: Optional[str]
    status: str  # testing, idle, offline
    last_seen: float

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        return asdict(self)


@dataclass
class TestResult:
    """
    Test result for comparison.
    """

    test_name: str
    endpoint: str
    success: bool
    duration: float
    timestamp: float
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        return asdict(self)


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
        # Close all client connections
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
                # Process incoming messages
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
        # Send to all clients concurrently
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
        details: Dict[str, Any],
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


class MultiEndpointManager:
    """
    Run tests on multiple environments simultaneously.
    """

    def __init__(self):
        self.endpoints: Dict[str, Dict[str, Any]] = {}
        self.results: Dict[str, List[TestResult]] = {}

    def add_endpoint(self, name: str, config: Dict[str, Any]):
        """
        Add an endpoint configuration.
        """
        self.endpoints[name] = config
        self.results[name] = []

    def remove_endpoint(self, name: str):
        """
        Remove an endpoint.
        """
        self.endpoints.pop(name, None)
        self.results.pop(name, None)

    async def run_test_on_all(
        self, test_func: Callable, test_name: str, *args, **kwargs
    ) -> Dict[str, TestResult]:
        """
        Run a test on all configured endpoints.
        """
        tasks = []
        for endpoint_name, config in self.endpoints.items():
            task = self._run_on_endpoint(
                test_func, test_name, endpoint_name, config, *args, **kwargs
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Organize results by endpoint
        endpoint_results = {}
        for endpoint_name, result in zip(self.endpoints.keys(), results):
            if isinstance(result, Exception):
                # Handle exception
                result = TestResult(
                    test_name=test_name,
                    endpoint=endpoint_name,
                    success=False,
                    duration=0.0,
                    timestamp=time.time(),
                    details={"error": str(result)},
                )
            endpoint_results[endpoint_name] = result
            self.results[endpoint_name].append(result)

        return endpoint_results

    async def _run_on_endpoint(
        self,
        test_func: Callable,
        test_name: str,
        endpoint_name: str,
        config: Dict[str, Any],
        *args,
        **kwargs,
    ) -> TestResult:
        """
        Run test on a specific endpoint.
        """
        start_time = time.time()
        try:
            # Pass endpoint config to test function
            result = await test_func(*args, endpoint_config=config, **kwargs)
            duration = time.time() - start_time

            return TestResult(
                test_name=test_name,
                endpoint=endpoint_name,
                success=True,
                duration=duration,
                timestamp=time.time(),
                details={"result": result},
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                endpoint=endpoint_name,
                success=False,
                duration=duration,
                timestamp=time.time(),
                details={"error": str(e)},
            )

    def get_results(self, endpoint: Optional[str] = None) -> List[TestResult]:
        """
        Get test results for an endpoint or all endpoints.
        """
        if endpoint:
            return self.results.get(endpoint, [])
        # Return all results
        all_results = []
        for results in self.results.values():
            all_results.extend(results)
        return all_results

    def get_success_rate(self, endpoint: str) -> float:
        """
        Get success rate for an endpoint.
        """
        results = self.results.get(endpoint, [])
        if not results:
            return 0.0
        successful = sum(1 for r in results if r.success)
        return successful / len(results)


class TeamPresenceTracker:
    """
    Track who's testing what in real-time.
    """

    def __init__(self):
        self.presence: Dict[str, PresenceInfo] = {}
        self.timeout = 300  # 5 minutes timeout

    def update_presence(
        self, user: str, endpoint: str, test_name: Optional[str] = None, status: str = "testing"
    ):
        """
        Update user presence information.
        """
        self.presence[user] = PresenceInfo(
            user=user, endpoint=endpoint, test_name=test_name, status=status, last_seen=time.time()
        )

    def remove_presence(self, user: str):
        """
        Remove user presence.
        """
        self.presence.pop(user, None)

    def get_presence(self, user: str) -> Optional[PresenceInfo]:
        """
        Get presence information for a user.
        """
        return self.presence.get(user)

    def get_all_presence(self) -> List[PresenceInfo]:
        """
        Get all presence information.
        """
        # Clean up stale presence
        current_time = time.time()
        stale_users = [
            user
            for user, info in self.presence.items()
            if current_time - info.last_seen > self.timeout
        ]
        for user in stale_users:
            self.presence.pop(user)

        return list(self.presence.values())

    def who_is_testing(self, test_name: str) -> List[str]:
        """
        Get list of users currently testing a specific test.
        """
        return [
            info.user
            for info in self.presence.values()
            if info.test_name == test_name and info.status == "testing"
        ]

    def who_is_on_endpoint(self, endpoint: str) -> List[str]:
        """
        Get list of users on a specific endpoint.
        """
        return [info.user for info in self.presence.values() if info.endpoint == endpoint]


class ResultComparator:
    """
    Compare test results across endpoints.
    """

    def compare_results(self, results: Dict[str, TestResult]) -> Dict[str, Any]:
        """
        Compare results from different endpoints.
        """
        if not results:
            return {"status": "no_results"}

        # Check if all succeeded
        all_success = all(r.success for r in results.values())

        # Calculate statistics
        durations = [r.duration for r in results.values()]
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        # Find discrepancies
        discrepancies = []
        success_values = [r.success for r in results.values()]
        if not all(s == success_values[0] for s in success_values):
            discrepancies.append(
                {
                    "type": "success_mismatch",
                    "details": {endpoint: r.success for endpoint, r in results.items()},
                }
            )

        return {
            "status": "all_passed" if all_success else "some_failed",
            "total_endpoints": len(results),
            "successful_endpoints": sum(1 for r in results.values() if r.success),
            "statistics": {
                "avg_duration": avg_duration,
                "min_duration": min_duration,
                "max_duration": max_duration,
                "duration_variance": max_duration - min_duration,
            },
            "discrepancies": discrepancies,
            "results": {endpoint: result.to_dict() for endpoint, result in results.items()},
        }

    def find_performance_outliers(
        self, results: Dict[str, TestResult], threshold: float = 2.0
    ) -> List[str]:
        """
        Find endpoints with significantly different performance.
        """
        durations = [r.duration for r in results.values()]
        if not durations:
            return []

        avg_duration = sum(durations) / len(durations)
        outliers = []

        for endpoint, result in results.items():
            if result.duration > avg_duration * threshold:
                outliers.append(endpoint)

        return outliers

    def generate_comparison_report(self, results: Dict[str, TestResult]) -> str:
        """
        Generate a human-readable comparison report.
        """
        comparison = self.compare_results(results)

        report = "Test Comparison Report\n"
        report += f"{'=' * 50}\n\n"
        report += f"Status: {comparison['status']}\n"
        report += f"Endpoints: {comparison['successful_endpoints']}/{comparison['total_endpoints']} passed\n\n"

        stats = comparison["statistics"]
        report += "Performance Statistics:\n"
        report += f"  Average Duration: {stats['avg_duration']:.3f}s\n"
        report += f"  Fastest: {stats['min_duration']:.3f}s\n"
        report += f"  Slowest: {stats['max_duration']:.3f}s\n"
        report += f"  Variance: {stats['duration_variance']:.3f}s\n\n"

        if comparison["discrepancies"]:
            report += "Discrepancies Found:\n"
            for disc in comparison["discrepancies"]:
                report += f"  - {disc['type']}: {disc['details']}\n"

        return report


class SharedCache:
    """
    Distributed cache for team-wide test data.
    """

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self.ttl: Dict[str, float] = {}  # Time-to-live

    def _get_lock(self, key: str) -> asyncio.Lock:
        """
        Get or create lock for a key.
        """
        if key not in self.locks:
            self.locks[key] = asyncio.Lock()
        return self.locks[key]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set a value in the cache.
        """
        async with self._get_lock(key):
            self.cache[key] = {"value": value, "timestamp": time.time()}
            if ttl:
                self.ttl[key] = time.time() + ttl

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        """
        async with self._get_lock(key):
            # Check TTL
            if key in self.ttl and time.time() > self.ttl[key]:
                self.cache.pop(key, None)
                self.ttl.pop(key, None)
                return None

            entry = self.cache.get(key)
            return entry["value"] if entry else None

    async def delete(self, key: str):
        """
        Delete a value from the cache.
        """
        async with self._get_lock(key):
            self.cache.pop(key, None)
            self.ttl.pop(key, None)

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        """
        value = await self.get(key)
        return value is not None

    async def clear(self):
        """
        Clear all cache entries.
        """
        self.cache.clear()
        self.ttl.clear()

    async def get_all_keys(self) -> List[str]:
        """
        Get all cache keys.
        """
        current_time = time.time()
        # Remove expired keys
        expired = [k for k, exp in self.ttl.items() if current_time > exp]
        for key in expired:
            await self.delete(key)
        return list(self.cache.keys())

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        """
        return {
            "total_keys": len(self.cache),
            "with_ttl": len(self.ttl),
            "oldest_entry": min((e["timestamp"] for e in self.cache.values()), default=None),
        }


class TestCoordinator:
    """
    Prevent duplicate test runs across team.
    """

    def __init__(self, cache: SharedCache):
        self.cache = cache
        self.lock_prefix = "test_lock:"
        self.result_prefix = "test_result:"
        self.lock_timeout = 300  # 5 minutes

    def _get_test_key(self, test_name: str, endpoint: str) -> str:
        """
        Generate a unique key for a test.
        """
        combined = f"{test_name}:{endpoint}"
        return hashlib.md5(combined.encode()).hexdigest()

    async def acquire_test_lock(self, test_name: str, endpoint: str, user: str) -> bool:
        """
        Try to acquire a lock for running a test.
        """
        key = self._get_test_key(test_name, endpoint)
        lock_key = f"{self.lock_prefix}{key}"

        # Check if already locked
        existing_lock = await self.cache.get(lock_key)
        if existing_lock:
            # Check if lock is stale
            if time.time() - existing_lock["timestamp"] > self.lock_timeout:
                # Lock is stale, remove it
                await self.cache.delete(lock_key)
            else:
                # Lock is active
                return False

        # Acquire lock
        await self.cache.set(
            lock_key, {"user": user, "timestamp": time.time()}, ttl=self.lock_timeout
        )

        return True

    async def release_test_lock(self, test_name: str, endpoint: str):
        """
        Release a test lock.
        """
        key = self._get_test_key(test_name, endpoint)
        lock_key = f"{self.lock_prefix}{key}"
        await self.cache.delete(lock_key)

    async def get_test_lock_holder(self, test_name: str, endpoint: str) -> Optional[str]:
        """
        Get who holds the lock for a test.
        """
        key = self._get_test_key(test_name, endpoint)
        lock_key = f"{self.lock_prefix}{key}"
        lock_data = await self.cache.get(lock_key)
        return lock_data["user"] if lock_data else None

    async def store_test_result(self, test_name: str, endpoint: str, result: TestResult):
        """
        Store a test result for sharing.
        """
        key = self._get_test_key(test_name, endpoint)
        result_key = f"{self.result_prefix}{key}"
        await self.cache.set(result_key, result.to_dict(), ttl=3600)  # 1 hour TTL

    async def get_test_result(self, test_name: str, endpoint: str) -> Optional[TestResult]:
        """
        Get a cached test result.
        """
        key = self._get_test_key(test_name, endpoint)
        result_key = f"{self.result_prefix}{key}"
        result_data = await self.cache.get(result_key)
        if result_data:
            return TestResult(**result_data)
        return None

    async def is_test_running(self, test_name: str, endpoint: str) -> bool:
        """
        Check if a test is currently running.
        """
        holder = await self.get_test_lock_holder(test_name, endpoint)
        return holder is not None

    async def wait_for_test(
        self, test_name: str, endpoint: str, timeout: float = 300
    ) -> Optional[TestResult]:
        """
        Wait for a test to complete and return its result.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if test is still running
            if not await self.is_test_running(test_name, endpoint):
                # Test completed, try to get result
                result = await self.get_test_result(test_name, endpoint)
                if result:
                    return result

            # Wait a bit before checking again
            await asyncio.sleep(1)

        return None  # Timeout


# Example usage
async def example_usage():
    """
    Example of using collaboration features.
    """

    # 1. Start WebSocket broadcaster
    broadcaster = WebSocketBroadcaster()
    await broadcaster.start_server()

    # 2. Set up multi-endpoint manager
    manager = MultiEndpointManager()
    manager.add_endpoint("production", {"url": "https://api.prod.com"})
    manager.add_endpoint("staging", {"url": "https://api.staging.com"})

    # 3. Set up team presence tracker
    presence = TeamPresenceTracker()
    presence.update_presence("alice", "production", "test_login", "testing")
    presence.update_presence("bob", "staging", "test_signup", "testing")

    # 4. Set up shared cache and coordinator
    cache = SharedCache()
    coordinator = TestCoordinator(cache)

    # 5. Example test function
    async def example_test(endpoint_config):
        await asyncio.sleep(0.1)  # Simulate test work
        return {"status": "success"}

    # 6. Try to acquire lock and run test
    test_name = "test_login"
    endpoint = "production"
    user = "alice"

    if await coordinator.acquire_test_lock(test_name, endpoint, user):
        print(f"Lock acquired by {user}")

        # Broadcast test start
        await broadcaster.broadcast_test_start(test_name, endpoint, user)

        # Run test on all endpoints
        results = await manager.run_test_on_all(example_test, test_name)

        # Compare results
        comparator = ResultComparator()
        comparison = comparator.compare_results(results)
        print(f"\nComparison: {comparison}")

        # Store result
        for ep, result in results.items():
            await coordinator.store_test_result(test_name, ep, result)

        # Broadcast completion
        await broadcaster.broadcast_test_complete(test_name, endpoint, user, True, 0.1, {})

        # Release lock
        await coordinator.release_test_lock(test_name, endpoint)
    else:
        holder = await coordinator.get_test_lock_holder(test_name, endpoint)
        print(f"Test already running by {holder}")

    # Cleanup
    await broadcaster.stop_server()


if __name__ == "__main__":
    asyncio.run(example_usage())
