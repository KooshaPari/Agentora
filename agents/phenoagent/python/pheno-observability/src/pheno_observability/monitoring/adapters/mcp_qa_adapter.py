"""MCP QA Monitoring Adapter.

Bridges existing MCP QA monitoring components with the unified monitoring layer.
Provides compatibility for MCP QA observability, metrics, and testing components.
"""

from __future__ import annotations

import time
from typing import Any

from pheno.observability.logging import get_logger
from pheno.observability.monitoring.core import MonitoringProvider
from pheno.observability.monitoring.events import EventEmitter
from pheno.observability.monitoring.health import HealthStatus
from pheno.observability.monitoring.metrics import MetricsCollector

logger = get_logger(__name__)


class MCPQAMonitoringAdapter(MonitoringProvider):
    """Adapter for MCP QA monitoring components.

    Bridges existing MCP QA monitoring with the unified monitoring layer.
    """

    def __init__(
        self,
        observable_client: Any | None = None,
        metrics_collector: Any | None = None,
        health_checks: list[Any] | None = None,
        test_runner: Any | None = None,
    ):
        """Initialize MCP QA monitoring adapter.

        Args:
            observable_client: ObservableMCPClient instance
            metrics_collector: MCP QA metrics collector
            health_checks: List of health check components
            test_runner: Test runner instance
        """
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # MCP QA components
        self.observable_client = observable_client
        self.mcp_metrics_collector = metrics_collector
        self.health_checks = health_checks or []
        self.test_runner = test_runner

        # Adapter state
        self._started = False
        self._metrics_collector = MetricsCollector()
        self._event_emitter = EventEmitter()

        # Health tracking
        self._last_health_check = time.time()
        self._health_status = HealthStatus.HEALTHY

    async def start(self) -> None:
        """
        Start the MCP QA monitoring adapter.
        """
        if self._started:
            self.logger.warning("MCP QA monitoring adapter already started")
            return

        self.logger.info("Starting MCP QA monitoring adapter")

        try:
            # Start observable client
            if self.observable_client and hasattr(self.observable_client, "start"):
                await self.observable_client.start()
                self.logger.info("Started observable client")

            # Start MCP metrics collector
            if self.mcp_metrics_collector and hasattr(self.mcp_metrics_collector, "start"):
                await self.mcp_metrics_collector.start()
                self.logger.info("Started MCP metrics collector")

            # Start health checks
            for health_check in self.health_checks:
                if hasattr(health_check, "start"):
                    await health_check.start()
                    self.logger.debug(f"Started health check: {health_check.__class__.__name__}")

            # Start test runner
            if self.test_runner and hasattr(self.test_runner, "start"):
                await self.test_runner.start()
                self.logger.info("Started test runner")

            # Start metrics collection
            await self._metrics_collector.start()

            # Start event emission
            await self._event_emitter.start()

            self._started = True
            self.logger.info("MCP QA monitoring adapter started successfully")

        except Exception as e:
            self.logger.exception(f"Failed to start MCP QA monitoring adapter: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """
        Stop the MCP QA monitoring adapter.
        """
        if not self._started:
            return

        self.logger.info("Stopping MCP QA monitoring adapter")

        try:
            # Stop observable client
            if self.observable_client and hasattr(self.observable_client, "stop"):
                await self.observable_client.stop()
                self.logger.info("Stopped observable client")

            # Stop MCP metrics collector
            if self.mcp_metrics_collector and hasattr(self.mcp_metrics_collector, "stop"):
                await self.mcp_metrics_collector.stop()
                self.logger.info("Stopped MCP metrics collector")

            # Stop health checks
            for health_check in self.health_checks:
                if hasattr(health_check, "stop"):
                    await health_check.stop()
                    self.logger.debug(f"Stopped health check: {health_check.__class__.__name__}")

            # Stop test runner
            if self.test_runner and hasattr(self.test_runner, "stop"):
                await self.test_runner.stop()
                self.logger.info("Stopped test runner")

            # Stop metrics collection
            await self._metrics_collector.stop()

            # Stop event emission
            await self._event_emitter.stop()

            self._started = False
            self.logger.info("MCP QA monitoring adapter stopped")

        except Exception as e:
            self.logger.exception(f"Error stopping MCP QA monitoring adapter: {e}")

    async def collect_metrics(self) -> dict[str, Any]:
        """
        Collect metrics from MCP QA components.
        """
        metrics = {}

        try:
            # Collect observable client metrics
            if self.observable_client and hasattr(self.observable_client, "get_metrics"):
                client_metrics = await self.observable_client.get_metrics()
                metrics.update(client_metrics)

            # Collect MCP metrics
            if self.mcp_metrics_collector and hasattr(self.mcp_metrics_collector, "get_metrics"):
                mcp_metrics = await self.mcp_metrics_collector.get_metrics()
                metrics.update(mcp_metrics)

            # Collect test runner metrics
            if self.test_runner and hasattr(self.test_runner, "get_metrics"):
                test_metrics = await self.test_runner.get_metrics()
                metrics.update(test_metrics)

            # Add adapter metrics
            metrics.update(
                {
                    "mcp_qa_adapter_started": self._started,
                    "mcp_qa_adapter_uptime": time.time() - self._last_health_check,
                    "health_checks_count": len(self.health_checks),
                },
            )

            # Record metrics
            self._metrics_collector.gauge("mcp_qa_health_checks_count", len(self.health_checks))
            self._metrics_collector.gauge(
                "mcp_qa_adapter_uptime", time.time() - self._last_health_check,
            )

        except Exception as e:
            self.logger.exception(f"Error collecting MCP QA metrics: {e}")
            metrics["error"] = str(e)

        return metrics

    async def process_events(self) -> list[dict[str, Any]]:
        """
        Process events from MCP QA components.
        """
        events = []

        try:
            # Process observable client events
            if self.observable_client and hasattr(self.observable_client, "get_events"):
                client_events = await self.observable_client.get_events()
                events.extend(client_events)

            # Process test runner events
            if self.test_runner and hasattr(self.test_runner, "get_events"):
                test_events = await self.test_runner.get_events()
                events.extend(test_events)

            # Emit adapter events
            if self._started:
                self._event_emitter.emit(
                    "mcp_qa_adapter_status",
                    {"status": "running", "health_checks": len(self.health_checks)},
                    source="mcp_qa_adapter",
                    severity="info",
                )

        except Exception as e:
            self.logger.exception(f"Error processing MCP QA events: {e}")
            events.append(
                {
                    "type": "error",
                    "source": "mcp_qa_adapter",
                    "message": str(e),
                    "timestamp": time.time(),
                },
            )

        return events

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on MCP QA components.
        """
        health = {
            "healthy": True,
            "adapter_started": self._started,
            "components": {},
            "timestamp": time.time(),
        }

        try:
            # Check observable client health
            if self.observable_client:
                if hasattr(self.observable_client, "health_check"):
                    client_health = await self.observable_client.health_check()
                    health["components"]["observable_client"] = client_health
                    if not client_health.get("healthy", True):
                        health["healthy"] = False
                else:
                    health["components"]["observable_client"] = {
                        "healthy": True,
                        "status": "no_health_check",
                    }

            # Check MCP metrics collector health
            if self.mcp_metrics_collector:
                if hasattr(self.mcp_metrics_collector, "health_check"):
                    metrics_health = await self.mcp_metrics_collector.health_check()
                    health["components"]["mcp_metrics_collector"] = metrics_health
                    if not metrics_health.get("healthy", True):
                        health["healthy"] = False
                else:
                    health["components"]["mcp_metrics_collector"] = {
                        "healthy": True,
                        "status": "no_health_check",
                    }

            # Check health checks
            for i, health_check in enumerate(self.health_checks):
                check_name = f"health_check_{i}_{health_check.__class__.__name__}"
                if hasattr(health_check, "health_check"):
                    check_health = await health_check.health_check()
                    health["components"][check_name] = check_health
                    if not check_health.get("healthy", True):
                        health["healthy"] = False
                else:
                    health["components"][check_name] = {
                        "healthy": True,
                        "status": "no_health_check",
                    }

            # Check test runner health
            if self.test_runner:
                if hasattr(self.test_runner, "health_check"):
                    test_health = await self.test_runner.health_check()
                    health["components"]["test_runner"] = test_health
                    if not test_health.get("healthy", True):
                        health["healthy"] = False
                else:
                    health["components"]["test_runner"] = {
                        "healthy": True,
                        "status": "no_health_check",
                    }

            # Update health status
            self._health_status = (
                HealthStatus.HEALTHY if health["healthy"] else HealthStatus.UNHEALTHY
            )
            self._last_health_check = time.time()

        except Exception as e:
            self.logger.exception(f"Error in MCP QA health check: {e}")
            health["healthy"] = False
            health["error"] = str(e)
            self._health_status = HealthStatus.UNHEALTHY

        return health

    def get_metrics_collector(self) -> MetricsCollector:
        """
        Get the metrics collector.
        """
        return self._metrics_collector

    def get_event_emitter(self) -> EventEmitter:
        """
        Get the event emitter.
        """
        return self._event_emitter

    def add_health_check(self, health_check: Any) -> None:
        """
        Add a health check component.
        """
        if health_check not in self.health_checks:
            self.health_checks.append(health_check)
            self.logger.info(f"Added health check: {health_check.__class__.__name__}")

    def remove_health_check(self, health_check: Any) -> None:
        """
        Remove a health check component.
        """
        if health_check in self.health_checks:
            self.health_checks.remove(health_check)
            self.logger.info(f"Removed health check: {health_check.__class__.__name__}")

    async def run_tests(self) -> dict[str, Any]:
        """
        Run MCP QA tests.
        """
        if not self.test_runner:
            return {"error": "No test runner available"}

        try:
            if hasattr(self.test_runner, "run_tests"):
                return await self.test_runner.run_tests()
            return {"error": "Test runner does not support run_tests method"}
        except Exception as e:
            self.logger.exception(f"Error running MCP QA tests: {e}")
            return {"error": str(e)}
