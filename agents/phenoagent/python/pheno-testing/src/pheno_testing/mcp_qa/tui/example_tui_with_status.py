"""
Example: Using TUI Dashboard with Status Monitoring

This example demonstrates how to launch the enhanced TUI dashboard
with comprehensive status monitoring widgets including:
- OAuth token status with expiry countdown
- MCP server connection status with latency
- Tunnel status (ngrok/cloudflare/custom)
- Resource monitoring (DB, Redis, API limits, memory)
"""

from .oauth_cache import CachedOAuthClient
from .tui import run_tui_dashboard


def run_enhanced_dashboard_example():
    """
    Example of running TUI dashboard with full status monitoring.
    """
    # Configuration
    mcp_endpoint = "https://mcp.atoms.tech/api/mcp"
    test_modules = ["tests.comprehensive.test_entity"]

    # Initialize OAuth cache client for token monitoring
    oauth_client = CachedOAuthClient(
        mcp_url=mcp_endpoint,
        client_name="Atoms MCP Test Suite",
    )

    # Tunnel configuration (optional - for local development)
    tunnel_config = {
        "type": "ngrok",  # or "cloudflare", "custom"
        # "url": "https://custom-tunnel.example.com",  # for custom tunnels
    }

    # Resource monitoring configuration (optional)
    resource_config = {
        # Enable database monitoring
        "check_db": True,
        "db_config": {
            "host": "localhost",
            "port": 5432,
            # Add more DB config as needed
        },
        # Enable Redis monitoring
        "check_redis": False,
        "redis_config": {
            "host": "localhost",
            "port": 6379,
        },
        # Enable API rate limit monitoring
        "check_api_limits": True,
        # Enable memory usage monitoring (always on if psutil available)
    }

    # Launch TUI with status monitoring
    print("🚀 Starting Atoms MCP Test Dashboard with Status Monitoring")
    print("\nStatus Monitoring Features:")
    print("  - OAuth token status with expiry countdown")
    print("  - MCP server connection status with latency")
    print("  - Tunnel status (ngrok/cloudflare/custom)")
    print("  - Resource monitoring (DB, Redis, API limits, memory)")
    print("\nKeyboard Shortcuts:")
    print("  - Ctrl+H: Manual health check (refresh all status)")
    print("  - O: Clear OAuth cache")
    print("  - H or ?: Show full help with all shortcuts")
    print("\nStatus widgets auto-refresh every 5 seconds.\n")

    run_tui_dashboard(
        endpoint=mcp_endpoint,
        test_modules=test_modules,
        # Phase 2: Live reload
        enable_live_reload=True,
        watch_paths=["tools/", "tests/"],
        # Phase 5: WebSocket team collaboration
        enable_websocket=False,
        websocket_host="localhost",
        websocket_port=8765,
        # Status monitoring
        oauth_cache_client=oauth_client,
        tunnel_config=tunnel_config,
        resource_config=resource_config,
    )


def run_minimal_dashboard_example():
    """Example of running TUI dashboard with minimal status monitoring.

    Just OAuth and Server status - no tunnel or resource monitoring.
    """
    mcp_endpoint = "https://mcp.atoms.tech/api/mcp"
    test_modules = ["tests.comprehensive.test_entity"]

    # Initialize OAuth client
    oauth_client = CachedOAuthClient(mcp_url=mcp_endpoint)

    print("🚀 Starting Minimal TUI Dashboard")
    print("   Status: OAuth + Server only\n")

    run_tui_dashboard(
        endpoint=mcp_endpoint,
        test_modules=test_modules,
        oauth_cache_client=oauth_client,
        # No tunnel_config or resource_config - widgets will show "not configured"
    )


def run_local_dev_dashboard_example():
    """
    Example for local development with ngrok tunnel monitoring.
    """
    mcp_endpoint = "http://localhost:8000"  # Local MCP server
    test_modules = ["tests.comprehensive.test_entity"]

    # No OAuth needed for local development
    oauth_client = None

    # Configure ngrok tunnel monitoring
    tunnel_config = {
        "type": "ngrok",
        # ngrok API will be automatically checked at http://localhost:4040/api/tunnels
    }

    # Monitor memory during development
    resource_config = {
        "check_api_limits": False,  # Not applicable for local
    }

    print("🚀 Starting Local Development Dashboard")
    print("   - No OAuth monitoring")
    print("   - ngrok tunnel monitoring enabled")
    print("   - Memory usage tracking\n")

    run_tui_dashboard(
        endpoint=mcp_endpoint,
        test_modules=test_modules,
        oauth_cache_client=oauth_client,
        tunnel_config=tunnel_config,
        resource_config=resource_config,
        enable_live_reload=True,
        watch_paths=["tools/", "src/", "tests/"],
    )


if __name__ == "__main__":
    # Choose which example to run:

    # Full featured with all status monitoring
    run_enhanced_dashboard_example()

    # Or minimal version
    # run_minimal_dashboard_example()

    # Or local development version
    # run_local_dev_dashboard_example()
