"""
Performance assertions for MCP testing.
"""


def assert_response_time(duration: float, max_seconds: float):
    """
    Assert response time is within limit.
    """
    assert duration <= max_seconds, f"Response time {duration:.2f}s exceeds limit {max_seconds}s"


def assert_memory_usage(memory_mb: float, max_mb: float):
    """
    Assert memory usage is within limit.
    """
    assert memory_mb <= max_mb, f"Memory usage {memory_mb:.2f}MB exceeds limit {max_mb}MB"


def assert_throughput(requests_per_second: float, min_rps: float):
    """
    Assert throughput meets minimum.
    """
    assert (
        requests_per_second >= min_rps
    ), f"Throughput {requests_per_second:.2f} RPS below minimum {min_rps} RPS"
