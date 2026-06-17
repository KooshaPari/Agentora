"""Example usage of the optimizations module for MCP test suites.

This demonstrates how to integrate the optimization features into your tests.
"""

import asyncio

from framework.optimizations import (
    OptimizationFlags,
    OptimizedMCPClient,
    create_optimized_client,
)


async def example_basic_usage():
    """
    Basic usage with default optimizations.
    """
    # Create client with all optimizations enabled by default
    client = create_optimized_client("http://localhost:8080")

    try:
        # Initialize the client (creates connection pool, etc.)
        await client.initialize()

        # Make optimized requests
        result = await client.call_tool("get_entity", {"entity_id": "123"})
        print(f"Result: {result}")

        # Get optimization statistics
        stats = client.get_stats()
        print(f"Performance stats: {stats}")

    finally:
        # Clean up
        await client.close()


async def example_custom_flags():
    """
    Custom optimization configuration.
    """
    # Create custom flags
    flags = OptimizationFlags(
        enable_connection_pooling=True,
        enable_batch_requests=True,
        enable_response_caching=True,
        pool_min_size=8,  # Larger pool for high-load tests
        pool_max_size=40,
        batch_size=20,  # Larger batches
        cache_max_entries=2000,
        cache_ttl_seconds=120,
        worker_multiplier=3,  # More workers
    )

    client = OptimizedMCPClient("http://localhost:8080", flags=flags)

    try:
        await client.initialize()

        # Run multiple requests in parallel (will be batched automatically)
        tasks = [client.call_tool("get_entity", {"entity_id": str(i)}) for i in range(100)]
        results = await asyncio.gather(*tasks)

        print(f"Processed {len(results)} requests")
        print(f"Stats: {client.get_stats()}")

    finally:
        await client.close()


async def example_from_environment():
    """
    Configure optimizations from environment variables.
    """
    # Set environment variables before running:
    # export MCP_ENABLE_POOLING=true
    # export MCP_POOL_MIN_SIZE=8
    # export MCP_POOL_MAX_SIZE=40
    # export MCP_ENABLE_CACHING=true
    # export MCP_CACHE_TTL=120

    flags = OptimizationFlags.from_env()
    client = OptimizedMCPClient("http://localhost:8080", flags=flags)

    try:
        await client.initialize()

        # Your test code here
        result = await client.call_tool("list_entities", {})
        print(f"Result: {result}")

    finally:
        await client.close()


async def example_selective_optimizations():
    """
    Enable only specific optimizations.
    """
    # Only enable connection pooling and caching, disable batching
    flags = OptimizationFlags(
        enable_connection_pooling=True,
        enable_batch_requests=False,  # Disabled
        enable_response_caching=True,
        enable_concurrency_optimization=False,  # Disabled
        enable_network_optimization=True,
    )

    client = OptimizedMCPClient("http://localhost:8080", flags=flags)

    try:
        await client.initialize()

        # Make requests
        result = await client.call_tool("get_entity", {"entity_id": "123"})
        print(f"Result: {result}")

    finally:
        await client.close()


async def example_no_caching_for_writes():
    """
    Demonstrate selective caching for read vs write operations.
    """
    client = create_optimized_client("http://localhost:8080")

    try:
        await client.initialize()

        # Read operation - will be cached
        _ = await client.call_tool("get_entity", {"entity_id": "123"}, use_cache=True)
        _ = await client.call_tool("get_entity", {"entity_id": "123"}, use_cache=True)
        # Second call will hit cache

        # Write operation - no caching
        await client.call_tool("create_entity", {"name": "test"}, use_cache=False)

        # Check cache stats
        stats = client.get_stats()
        print(f"Cache stats: {stats['cache']}")

    finally:
        await client.close()


async def example_pytest_fixture():
    """
    Example pytest fixture for tests.
    """
    # This would go in conftest.py
    import pytest

    @pytest.fixture
    async def optimized_client():
        """
        Provide an optimized MCP client for tests.
        """
        client = create_optimized_client("http://localhost:8080")
        await client.initialize()

        yield client

        # Print stats after test
        stats = client.get_stats()
        print(f"\nTest optimization stats: {stats}")

        await client.close()

    # Usage in tests:
    # async def test_something(optimized_client):
    #     result = await optimized_client.call_tool("get_entity", {"entity_id": "123"})
    #     assert result is not None


async def example_performance_comparison():
    """
    Compare performance with and without optimizations.
    """
    import time

    # Without optimizations
    flags_disabled = OptimizationFlags(
        enable_connection_pooling=False,
        enable_batch_requests=False,
        enable_response_caching=False,
    )

    # With optimizations
    flags_enabled = OptimizationFlags()

    async def run_test_suite(client, num_requests=100):
        await client.initialize()
        tasks = [
            client.call_tool("get_entity", {"entity_id": str(i % 10)}) for i in range(num_requests)
        ]
        await asyncio.gather(*tasks)

    # Test without optimizations
    client_disabled = OptimizedMCPClient("http://localhost:8080", flags=flags_disabled)
    start = time.time()
    await run_test_suite(client_disabled)
    time_disabled = time.time() - start
    await client_disabled.close()

    # Test with optimizations
    client_enabled = OptimizedMCPClient("http://localhost:8080", flags=flags_enabled)
    start = time.time()
    await run_test_suite(client_enabled)
    time_enabled = time.time() - start
    stats = client_enabled.get_stats()
    await client_enabled.close()

    print(f"Without optimizations: {time_disabled:.2f}s")
    print(f"With optimizations: {time_enabled:.2f}s")
    print(f"Speedup: {time_disabled / time_enabled:.2f}x")
    print(f"Stats: {stats}")


if __name__ == "__main__":
    # Run examples
    print("=== Basic Usage ===")
    asyncio.run(example_basic_usage())

    print("\n=== Custom Flags ===")
    asyncio.run(example_custom_flags())

    print("\n=== Selective Optimizations ===")
    asyncio.run(example_selective_optimizations())

    print("\n=== No Caching for Writes ===")
    asyncio.run(example_no_caching_for_writes())

    print("\n=== Performance Comparison ===")
    asyncio.run(example_performance_comparison())
