"""Dashboard Factory for Creating Test Dashboards.

Provides factory methods for easy dashboard creation.
"""

from typing import Any, Dict, Type

from ..base.dashboard_base import BaseDashboard


class DashboardFactory:
    """
    Factory for creating test dashboards with common configurations.
    """

    @staticmethod
    def create(
        dashboard_class: Type[BaseDashboard], title: str = "Test Dashboard", **config
    ) -> BaseDashboard:
        """Create a dashboard instance.

        Args:
            dashboard_class: Dashboard class to instantiate
            title: Dashboard title
            **config: Additional configuration

        Returns:
            BaseDashboard: Configured dashboard instance

        Example:
            from pheno.testing.mcp_qa.tui.factories import DashboardFactory
            from myproject.tui import MyDashboard

            dashboard = DashboardFactory.create(
                MyDashboard,
                title="My Test Suite",
                theme="dark"
            )
            dashboard.run()
        """
        dashboard = dashboard_class(**config)
        dashboard.title = title
        return dashboard

    @staticmethod
    def create_with_oauth(
        dashboard_class: Type[BaseDashboard], oauth_config: Dict[str, Any], **config
    ) -> BaseDashboard:
        """Create dashboard with OAuth monitoring.

        Args:
            dashboard_class: Dashboard class
            oauth_config: OAuth configuration
            **config: Additional config

        Returns:
            BaseDashboard: Dashboard with OAuth monitoring
        """
        config["oauth_config"] = oauth_config
        return DashboardFactory.create(dashboard_class, **config)

    @staticmethod
    def create_with_server_monitoring(
        dashboard_class: Type[BaseDashboard], server_config: Dict[str, Any], **config
    ) -> BaseDashboard:
        """Create dashboard with server monitoring.

        Args:
            dashboard_class: Dashboard class
            server_config: Server configuration (host, port, health_url)
            **config: Additional config

        Returns:
            BaseDashboard: Dashboard with server monitoring
        """
        config["server_config"] = server_config
        return DashboardFactory.create(dashboard_class, **config)
