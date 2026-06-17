"""
Pytest fixtures for TUI components.
"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def mock_cache_dir(tmp_path: Path) -> Path:
    cache_dir = tmp_path / ".oauth_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def valid_token_data() -> dict[str, Any]:
    return {
        "access_token": "test_access_token_valid_123",
        "token_type": "Bearer",
        "expires_at": time.time() + 3600,
        "refresh_token": "test_refresh_token_123",
        "scope": "read write",
    }


@pytest.fixture
def expired_token_data() -> dict[str, Any]:
    return {
        "access_token": "test_access_token_expired_456",
        "token_type": "Bearer",
        "expires_at": time.time() - 3600,
        "refresh_token": "test_refresh_token_456",
        "scope": "read write",
    }


@pytest.fixture
def expiring_soon_token_data() -> dict[str, Any]:
    return {
        "access_token": "test_access_token_expiring_789",
        "token_type": "Bearer",
        "expires_at": time.time() + 1800,
        "refresh_token": "test_refresh_token_789",
        "scope": "read write",
    }


@pytest.fixture
def mock_oauth_client(mock_cache_dir: Path):
    client = MagicMock()
    client._cache_dir = mock_cache_dir

    def get_cache_path() -> Path:
        return mock_cache_dir / "oauth_token.json"

    client._get_cache_path = get_cache_path

    def save_token(token_data: dict[str, Any]) -> None:
        cache_path = get_cache_path()
        with open(cache_path, "w") as handle:
            json.dump(token_data, handle)

    def load_token() -> dict[str, Any] | None:
        cache_path = get_cache_path()
        if not cache_path.exists():
            return None
        try:
            with open(cache_path) as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

    def clear_token() -> None:
        cache_path = get_cache_path()
        if cache_path.exists():
            cache_path.unlink()

    client.save_token = save_token
    client.load_token = load_token
    client.clear_token = clear_token
    return client


@pytest.fixture
def mock_oauth_client_with_valid_token(mock_oauth_client, valid_token_data):
    mock_oauth_client.save_token(valid_token_data)
    return mock_oauth_client


@pytest.fixture
def mock_oauth_client_with_expired_token(mock_oauth_client, expired_token_data):
    mock_oauth_client.save_token(expired_token_data)
    return mock_oauth_client


@pytest.fixture
def mock_oauth_client_with_expiring_token(mock_oauth_client, expiring_soon_token_data):
    mock_oauth_client.save_token(expiring_soon_token_data)
    return mock_oauth_client


@pytest.fixture
def mock_oauth_client_no_token(mock_oauth_client):
    mock_oauth_client.clear_token()
    return mock_oauth_client


@pytest.fixture
def mock_server_client():
    client = MagicMock()
    client.endpoint = "https://api.example.com/v1"
    client.connected = True
    client.latency_ms = 45.2

    async def health_check():
        if client.connected:
            return {"status": "healthy", "latency_ms": client.latency_ms}
        raise ConnectionError("Server unreachable")

    async def ping():
        if client.connected:
            return client.latency_ms
        raise TimeoutError("Ping timeout")

    client.health_check = health_check
    client.ping = ping
    return client


@pytest.fixture
def mock_progress_widget():
    widget = MagicMock()
    widget.tasks = {}

    def add_task(task_id: str, description: str, total: int = 1, category: str = ""):
        widget.tasks[task_id] = {
            "description": description,
            "total": total,
            "current": 0,
            "status": "pending",
            "category": category,
        }

    def update(task_id: str, **changes):
        if task_id in widget.tasks:
            widget.tasks[task_id].update(changes)

    def complete(task_id: str):
        if task_id in widget.tasks:
            widget.tasks[task_id]["status"] = "completed"
            widget.tasks[task_id]["current"] = widget.tasks[task_id]["total"]

    widget.add_task = add_task
    widget.update = update
    widget.complete = complete
    return widget


@pytest.fixture
def mock_metrics_tracker():
    tracker = MagicMock()
    tracker.api_calls = 0
    tracker.errors = 0
    tracker.latencies: list[float] = []

    def record_api_call(latency_ms: float) -> None:
        tracker.api_calls += 1
        tracker.latencies.append(latency_ms)

    def record_error() -> None:
        tracker.errors += 1

    def get_avg_latency() -> float:
        if not tracker.latencies:
            return 0.0
        return sum(tracker.latencies) / len(tracker.latencies)

    def get_error_rate() -> float:
        if tracker.api_calls == 0:
            return 0.0
        return (tracker.errors / tracker.api_calls) * 100

    tracker.record_api_call = record_api_call
    tracker.record_error = record_error
    tracker.get_avg_latency = get_avg_latency
    tracker.get_error_rate = get_error_rate
    return tracker


class MockTextualApp:
    def __init__(self) -> None:
        self.mounted_widgets: list[Any] = []
        self.unmounted_widgets: list[Any] = []

    async def mount(self, widget: Any) -> None:
        self.mounted_widgets.append(widget)
        if hasattr(widget, "on_mount"):
            await widget.on_mount()

    async def unmount(self, widget: Any) -> None:
        self.unmounted_widgets.append(widget)
        if hasattr(widget, "on_unmount"):
            await widget.on_unmount()


@pytest.fixture
def mock_textual_app():
    return MockTextualApp()


@pytest.fixture
def corrupt_token_file(mock_cache_dir: Path) -> Path:
    cache_file = mock_cache_dir / "oauth_token.json"
    with open(cache_file, "w") as handle:
        handle.write("{ invalid json content ][")
    return cache_file


@pytest.fixture
def token_without_expiry(mock_cache_dir: Path) -> Path:
    cache_file = mock_cache_dir / "oauth_token.json"
    token_data = {
        "access_token": "test_token_no_expiry",
        "token_type": "Bearer",
    }
    with open(cache_file, "w") as handle:
        json.dump(token_data, handle)
    return cache_file


def assert_widget_renders(widget) -> None:
    try:
        rendered = widget.render()
        assert rendered is not None
    except Exception as exc:  # pragma: no cover - defensive
        pytest.fail(f"Widget failed to render: {exc}")


__all__ = [
    "MockTextualApp",
    "assert_widget_renders",
    "corrupt_token_file",
    "expired_token_data",
    "expiring_soon_token_data",
    "mock_cache_dir",
    "mock_metrics_tracker",
    "mock_oauth_client",
    "mock_oauth_client_no_token",
    "mock_oauth_client_with_expired_token",
    "mock_oauth_client_with_expiring_token",
    "mock_oauth_client_with_valid_token",
    "mock_progress_widget",
    "mock_server_client",
    "mock_textual_app",
    "token_without_expiry",
    "valid_token_data",
]
