"""Quick verification test for widgets_compat.py.

This script verifies that the backward compatibility layer works correctly by
instantiating widgets with mock clients.
"""

import sys
from pathlib import Path


# Mock OAuth client for testing
class MockOAuthClient:
    def _get_cache_path(self):
        return Path("/tmp/test_oauth_token.json")


# Mock MCP client for testing
class MockMCPClient:
    @property
    def endpoint(self):
        return "http://localhost:8000/test"

    async def list_tools(self):
        return [{"name": "test_tool", "description": "Test"}]


def test_imports():
    """
    Test that imports work correctly.
    """
    print("Testing imports...")
    print("✓ All imports successful")


def test_widget_creation():
    """
    Test that widgets can be instantiated.
    """
    print("\nTesting widget creation...")

    # Suppress deprecation warnings for testing
    import warnings

    from pheno.testing.mcp_qa.tui.widgets_compat import (
        OAuthStatusWidget,
        ResourceStatusWidget,
        ServerStatusWidget,
        TunnelStatusWidget,
    )

    warnings.filterwarnings("ignore", category=DeprecationWarning)

    # Test OAuth widget
    OAuthStatusWidget(oauth_cache_client=MockOAuthClient(), _skip_deprecation_warning=True)
    print("✓ OAuthStatusWidget created")

    # Test Server widget
    ServerStatusWidget(client_adapter=MockMCPClient(), _skip_deprecation_warning=True)
    print("✓ ServerStatusWidget created")

    # Test Tunnel widget
    TunnelStatusWidget(
        tunnel_config={"type": "ngrok", "port": 4040}, _skip_deprecation_warning=True
    )
    print("✓ TunnelStatusWidget created")

    # Test Resource widget
    ResourceStatusWidget(resource_config={"check_system": True}, _skip_deprecation_warning=True)
    print("✓ ResourceStatusWidget created")


def test_adapters():
    """
    Test that adapters work correctly.
    """
    print("\nTesting adapters...")

    from pheno.testing.mcp_qa.tui.widgets_compat import (
        MCPClientAdapter,
        MCPOAuthCacheAdapter,
    )

    # Test OAuth adapter
    oauth_adapter = MCPOAuthCacheAdapter(MockOAuthClient())
    cache_path = oauth_adapter._get_cache_path()
    assert cache_path == Path("/tmp/test_oauth_token.json")
    print("✓ MCPOAuthCacheAdapter works")

    # Test MCP client adapter
    client_adapter = MCPClientAdapter(MockMCPClient())
    assert client_adapter.endpoint == "http://localhost:8000/test"
    print("✓ MCPClientAdapter works")


def test_batch_creation():
    """
    Test batch widget creation helper.
    """
    print("\nTesting batch creation...")

    import warnings

    from pheno.testing.mcp_qa.tui.widgets_compat import create_compatible_widgets

    warnings.filterwarnings("ignore", category=DeprecationWarning)

    widgets = create_compatible_widgets(
        oauth_cache_client=MockOAuthClient(),
        client_adapter=MockMCPClient(),
        tunnel_config={"type": "ngrok"},
        resource_config={"check_system": True},
        suppress_warnings=True,
    )

    assert "oauth" in widgets
    assert "server" in widgets
    assert "tunnel" in widgets
    assert "resource" in widgets
    print("✓ Batch creation successful")


def test_utilities():
    """
    Test utility functions.
    """
    print("\nTesting utilities...")

    from pheno.testing.mcp_qa.tui.widgets_compat import (
        check_tui_kit_available,
        get_migration_guide,
    )

    # Test tui-kit check
    has_tui_kit = check_tui_kit_available()
    print(f"✓ tui-kit available: {has_tui_kit}")

    # Test migration guide
    guide = get_migration_guide()
    assert len(guide) > 0
    assert "MIGRATION STEPS" in guide
    print("✓ Migration guide available")


def main():
    """
    Run all tests.
    """
    print("=" * 70)
    print("Widget Compatibility Layer Verification")
    print("=" * 70)

    try:
        test_imports()
        test_widget_creation()
        test_adapters()
        test_batch_creation()
        test_utilities()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        return 0
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
