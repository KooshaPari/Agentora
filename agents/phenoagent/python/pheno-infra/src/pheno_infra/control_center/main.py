"""
Pheno Control Center - Main Integration Example.

Demonstrates the complete system integrating all ARU components:
- Project registry and configuration
- Unified monitor engine
- CLI bridge and command routing
- Multi-tenant infrastructure management
- Enhanced TUI monitoring

This serves as both an integration test and usage example.
"""

import asyncio
import logging
import sys
from pathlib import Path

from .cli_bridge import CLIBridge, CommandRouter
from .config import ProjectConfig, ProjectRegistry
from .engine import (
    ProcessInfo,
    ResourceInfo,
    ResourceState,
    ServiceState,
    UnifiedMonitorEngine,
)
from .enhanced_monitor import EnhancedMultiProjectMonitor
from .multi_tenant import MultiTenantManager
from .tui_monitor import run_enhanced_tui_monitor

logger = logging.getLogger(__name__)


class PhenoControlCenter:
    """Main Pheno Control Center orchestrator.

    Integrates all components to provide a unified control interface for managing
    multiple pheno-sdk projects.
    """

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize the control center.
        """
        self.config_dir = config_dir

        # Core components
        self.project_registry = ProjectRegistry(config_dir)
        self.monitor_engine = UnifiedMonitorEngine()
        self.cli_bridge = CLIBridge()
        self.command_router = CommandRouter(self.cli_bridge)

        # Multi-tenant manager
        config = self.project_registry.config
        self.multi_tenant_manager = MultiTenantManager(
            base_fallback_port=config.base_fallback_port,
            base_proxy_port=config.base_proxy_port,
            tunnel_domain="kooshapari.com",  # Could be made configurable
        )

        # Enhanced monitor
        self.enhanced_monitor = EnhancedMultiProjectMonitor(
            project_registry=self.project_registry,
            monitor_engine=self.monitor_engine,
            enable_rich=True,
        )

        logger.info("Pheno Control Center initialized")

    async def setup(self) -> None:
        """
        Setup the control center components.
        """
        logger.info("Setting up Pheno Control Center...")

        # Start monitor engine
        await self.monitor_engine.start_monitoring()

        # Register all projects with multi-tenant manager
        for project_name in self.project_registry.list_projects():
            project_config = self.project_registry.get_project(project_name)
            if project_config:
                # Register with multi-tenant manager
                self.multi_tenant_manager.register_project(project_config)

                # Register CLI context with command router
                working_dir = (
                    Path(project_config.working_directory)
                    if project_config.working_directory
                    else None
                )
                self.command_router.register_project_context(
                    project_name=project_name,
                    working_dir=working_dir,
                    env_vars=project_config.env_vars,
                    cli_prefix=project_config.cli_entry[:1] if project_config.cli_entry else [],
                )

                # Add some example processes and resources to the monitor
                await self._setup_project_monitoring(project_name, project_config)

        logger.info("Control center setup complete")

    async def _setup_project_monitoring(
        self, project_name: str, project_config: ProjectConfig,
    ) -> None:
        """
        Setup monitoring for a specific project.
        """
        # Register example process (would be real in actual usage)
        process_info = ProcessInfo(
            name=project_name,
            project=project_name,
            port=project_config.base_port,
            state=ServiceState.STOPPED,
            health_endpoint=project_config.health_endpoint,
        )
        self.monitor_engine.register_process(process_info)

        # Register example resources based on project
        if project_name == "atoms":
            # Example: Atoms might need a database
            db_resource = ResourceInfo(
                name="postgres",
                project=project_name,
                host="localhost",
                port=5432,
                state=ResourceState.UNKNOWN,
                required=False,
            )
            self.monitor_engine.register_resource(db_resource)

        elif project_name == "zen":
            # Example: Zen might need NATS and Redis
            nats_resource = ResourceInfo(
                name="nats",
                project=project_name,
                host="localhost",
                port=4222,
                state=ResourceState.UNKNOWN,
                required=False,
            )
            self.monitor_engine.register_resource(nats_resource)

            redis_resource = ResourceInfo(
                name="redis",
                project=project_name,
                host="localhost",
                port=6379,
                state=ResourceState.UNKNOWN,
                required=False,
            )
            self.monitor_engine.register_resource(redis_resource)

        # Register fallback resource
        fallback_port = self.multi_tenant_manager.get_project_fallback_port(project_name)
        if fallback_port:
            fallback_resource = ResourceInfo(
                name="fallback",
                project=project_name,
                host="localhost",
                port=fallback_port,
                state=ResourceState.UNKNOWN,
                required=False,
            )
            self.monitor_engine.register_resource(fallback_resource)

        # Register proxy resource
        proxy_port = self.multi_tenant_manager.get_project_proxy_port(project_name)
        if proxy_port:
            proxy_resource = ResourceInfo(
                name="proxy",
                project=project_name,
                host="localhost",
                port=proxy_port,
                state=ResourceState.UNKNOWN,
                required=False,
            )
            self.monitor_engine.register_resource(proxy_resource)

    async def run_tui_monitor(self) -> None:
        """
        Run the enhanced TUI monitor.
        """
        logger.info("Starting TUI monitor...")

        await run_enhanced_tui_monitor(
            project_registry=self.project_registry,
            monitor_engine=self.monitor_engine,
            cli_bridge=self.cli_bridge,
            command_router=self.command_router,
            prefer_textual=True,
        )

    async def run_simple_monitor(self) -> None:
        """
        Run the simple Rich-based monitor.
        """
        logger.info("Starting simple monitor...")

        try:
            await self.enhanced_monitor.run()
        except KeyboardInterrupt:
            logger.info("Monitor stopped by user")

    async def shutdown(self) -> None:
        """
        Shutdown the control center.
        """
        logger.info("Shutting down Pheno Control Center...")

        # Shutdown components
        await self.monitor_engine.stop_monitoring()
        await self.multi_tenant_manager.shutdown()
        self.cli_bridge.shutdown()

        logger.info("Control center shutdown complete")


def run_desktop_gui(config_dir: Path | None = None) -> int:
    """
    Run the desktop GUI application.
    """
    try:
        from .desktop.launcher import run_desktop_app

        return run_desktop_app(config_dir)
    except ImportError:
        print("Desktop GUI not available. PyQt6 is required for desktop mode.")
        print("Install with: pip install PyQt6")
        return 1


async def main():
    """
    Main entry point for the control center.
    """
    import argparse

    # Setup argument parser
    parser = argparse.ArgumentParser(
        description="Pheno Control Center - Multi-project orchestration system",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="tui",
        choices=["tui", "monitor", "desktop", "demo"],
        help="Mode to run: tui (interactive TUI), monitor (simple monitor), desktop (PyQt GUI), demo (demonstration)",
    )
    parser.add_argument("--config-dir", type=Path, help="Configuration directory path")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    mode = args.mode
    config_dir = args.config_dir

    # Handle desktop mode separately (runs Qt event loop)
    if mode == "desktop":
        exit_code = run_desktop_gui(config_dir)
        sys.exit(exit_code)

    # Handle demo mode
    if mode == "demo":
        await demo_control_center(config_dir)
        return

    # Initialize control center for async modes
    control_center = PhenoControlCenter(config_dir)

    try:
        # Setup
        await control_center.setup()

        # Run based on mode
        if mode == "tui":
            await control_center.run_tui_monitor()
        elif mode == "monitor":
            await control_center.run_simple_monitor()
        else:
            logger.error(f"Unknown mode: {mode}")
            return

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Control center error: {e}")
        raise
    finally:
        await control_center.shutdown()


async def demo_control_center(config_dir: Path | None = None):
    """Demo function showing the control center capabilities.

    This demonstrates:
    - Project registration
    - Multi-tenant infrastructure setup
    - Command routing and execution
    - Monitoring and status reporting
    """
    print("=== Pheno Control Center Demo ===")

    # Initialize
    control_center = PhenoControlCenter(config_dir)
    await control_center.setup()

    # Show registered projects
    projects = control_center.project_registry.list_projects()
    print(f"\nRegistered projects: {', '.join(projects)}")

    # Show multi-tenant status
    mt_status = control_center.multi_tenant_manager.get_global_status()
    print("\nMulti-tenant infrastructure:")
    print(f"  Fallback servers: {mt_status['infrastructure']['active_fallback_servers']}")
    print(f"  Proxy servers: {mt_status['infrastructure']['active_proxy_servers']}")
    print(f"  Total tunnels: {mt_status['infrastructure']['total_tunnels']}")

    # Show global monitoring status
    global_status = control_center.monitor_engine.get_global_status()
    print("\nGlobal status:")
    print(
        f"  Projects: {global_status['summary']['healthy_projects']}/{global_status['summary']['total_projects']} healthy",
    )
    print(
        f"  Processes: {global_status['summary']['running_processes']}/{global_status['summary']['total_processes']} running",
    )

    # Show per-project status
    for project_name in projects:
        project_status = control_center.monitor_engine.get_project_status(project_name)
        print(f"\n{project_name.upper()}:")
        print(f"  State: {project_status['overall_state']}")
        print(
            f"  Processes: {project_status['processes']['running']}/{project_status['processes']['total']}",
        )
        print(
            f"  Resources: {project_status['resources']['available']}/{project_status['resources']['total']}",
        )

    # Demo command routing
    print("\nTesting command routing:")

    # Test routing atoms command
    test_commands = ["atoms --help", "zen --version", "status", "help"]

    for cmd in test_commands:
        print(f"  Routing: '{cmd}'")
        suggestions = control_center.command_router.get_command_suggestions(cmd.split()[0])
        if suggestions:
            print(f"    Suggestions: {', '.join(suggestions[:3])}")

    print("\n=== Demo Complete ===")

    # Cleanup
    await control_center.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
