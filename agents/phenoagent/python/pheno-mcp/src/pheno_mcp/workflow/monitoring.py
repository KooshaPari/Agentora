"""Workflow Monitoring Integration for MCP.

This module provides MCP-specific workflow monitoring and observability.
Adapted from zen-mcp-server for use as a reusable SDK component.

Key Features:
- MCP workflow monitoring integration
- Health check endpoint registration
- Dashboard route integration
- Background monitoring startup
- Configuration management
- Graceful shutdown handling
"""

import asyncio
import contextlib
import logging
import time
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any

# Use pydevkit for tracing

logger = logging.getLogger(__name__)


class WorkflowMonitoringIntegration:
    """
    Main integration class for MCP workflow monitoring.
    """

    def __init__(
        self,
        workflow_engine: Any | None = None,
        distributed_executor: Any | None = None,
        observability_manager: Any | None = None,
        enable_background_monitoring: bool = True,
        monitoring_interval_seconds: int = 30,
        log_level: int = logging.INFO,
    ):
        """Initialize workflow monitoring integration.

        Args:
            workflow_engine: Workflow engine instance (optional)
            distributed_executor: Distributed workflow executor instance (optional)
            observability_manager: Custom observability manager (optional)
            enable_background_monitoring: Whether to start background monitoring
            monitoring_interval_seconds: Interval for background monitoring checks
            log_level: Logging level for workflow monitoring
        """
        self.workflow_engine = workflow_engine
        self.distributed_executor = distributed_executor
        self.enable_background_monitoring = enable_background_monitoring
        self.monitoring_interval_seconds = monitoring_interval_seconds
        self.log_level = log_level

        # Initialize observability manager
        self.observability = observability_manager

        # State tracking
        self.monitoring_started = False
        self.monitoring_task: asyncio.Task | None = None

        # Metrics storage
        self.workflow_metrics: dict[str, Any] = {}
        self.execution_history: list[dict[str, Any]] = []

        logger.setLevel(log_level)
        logger.info("Workflow monitoring integration initialized")

    async def start_monitoring(self):
        """
        Start background monitoring and observability.
        """
        if self.monitoring_started:
            logger.warning("Workflow monitoring already started")
            return

        try:
            if self.enable_background_monitoring:
                self.monitoring_task = asyncio.create_task(self._background_monitoring_loop())
                logger.info(
                    f"Started workflow monitoring with {self.monitoring_interval_seconds}s intervals",
                )

            self.monitoring_started = True

        except Exception as e:
            logger.exception(f"Failed to start workflow monitoring: {e}")
            raise

    async def stop_monitoring(self):
        """
        Stop background monitoring.
        """
        if not self.monitoring_started:
            return

        try:
            if self.monitoring_task:
                self.monitoring_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self.monitoring_task
                self.monitoring_task = None

            self.monitoring_started = False
            logger.info("Stopped workflow monitoring")

        except Exception as e:
            logger.exception(f"Error stopping workflow monitoring: {e}")

    async def _background_monitoring_loop(self):
        """
        Background monitoring loop.
        """
        while True:
            try:
                await asyncio.sleep(self.monitoring_interval_seconds)
                await self._collect_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in monitoring loop: {e}")

    async def _collect_metrics(self):
        """
        Collect workflow metrics.
        """
        try:
            if self.observability:
                metrics = await self.observability.collect_metrics()
                self.workflow_metrics.update(metrics)
        except Exception as e:
            logger.exception(f"Failed to collect metrics: {e}")

    def integrate_with_fastapi(self, app):
        """
        Integrate monitoring routes with FastAPI application.
        """
        try:
            # Add dashboard route
            @app.get("/dashboard/workflow")
            async def workflow_dashboard(workflow_id: str = ""):
                """
                Serve workflow monitoring dashboard.
                """
                from fastapi.responses import HTMLResponse

                dashboard_data = self.get_dashboard_data(workflow_id)
                html_content = self._generate_dashboard_html(dashboard_data)
                return HTMLResponse(content=html_content)

            # Add health check route
            @app.get("/health/workflow")
            async def workflow_health():
                """
                Workflow health check endpoint.
                """
                try:
                    health_status = await self.get_health_status()
                    overall_status = "healthy" if self.monitoring_started else "inactive"

                    return {
                        "status": overall_status,
                        "monitoring_active": self.monitoring_started,
                        "health": health_status,
                    }

                except Exception as e:
                    logger.exception(f"Workflow health check failed: {e}")
                    return {"status": "error", "error": str(e)}

            # Add metrics endpoint
            @app.get("/metrics/workflow")
            async def workflow_metrics():
                """
                Get workflow metrics.
                """
                return {
                    "timestamp": time.time(),
                    "metrics": self.workflow_metrics,
                    "execution_history": self.execution_history[-10:],  # Last 10
                }

            logger.info("Integrated workflow monitoring routes with FastAPI")

        except Exception as e:
            logger.exception(f"Failed to integrate with FastAPI: {e}")
            raise

    def get_monitoring_context(self, workflow_id: str, workflow_type: str = "") -> str:
        """
        Create monitoring context for workflow execution.
        """
        return f"{workflow_type}_{workflow_id}_{uuid.uuid4().hex[:8]}"

    def record_workflow_completion(
        self,
        span_id: str,
        workflow_id: str,
        workflow_type: str,
        duration_seconds: float,
        success: bool = True,
        **kwargs,
    ):
        """
        Record workflow completion with observability.
        """
        execution_record = {
            "span_id": span_id,
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "duration_seconds": duration_seconds,
            "success": success,
            "timestamp": time.time(),
            **kwargs,
        }

        self.execution_history.append(execution_record)

        # Update metrics
        if workflow_type not in self.workflow_metrics:
            self.workflow_metrics[workflow_type] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
            }

        metrics = self.workflow_metrics[workflow_type]
        metrics["total_executions"] += 1
        if success:
            metrics["successful_executions"] += 1
        else:
            metrics["failed_executions"] += 1
        metrics["total_duration"] += duration_seconds
        metrics["avg_duration"] = metrics["total_duration"] / metrics["total_executions"]

        logger.info(
            f"Recorded workflow completion: {workflow_type}/{workflow_id} "
            f"(success={success}, duration={duration_seconds:.2f}s)",
        )

    def get_dashboard_data(self, workflow_id: str = "") -> dict[str, Any]:
        """
        Get dashboard data for external use.
        """
        return {
            "workflow_id": workflow_id,
            "monitoring_active": self.monitoring_started,
            "metrics": self.workflow_metrics,
            "recent_executions": self.execution_history[-20:],
        }

    async def get_health_status(self) -> dict[str, Any]:
        """
        Get comprehensive health status.
        """
        try:
            return {
                "timestamp": time.time(),
                "monitoring_active": self.monitoring_started,
                "total_workflows": len(self.workflow_metrics),
                "total_executions": sum(
                    m.get("total_executions", 0) for m in self.workflow_metrics.values()
                ),
                "success_rate": self._calculate_overall_success_rate(),
            }

        except Exception as e:
            logger.exception(f"Failed to get health status: {e}")
            return {"error": str(e), "monitoring_active": self.monitoring_started}

    def _calculate_overall_success_rate(self) -> float:
        """
        Calculate overall success rate across all workflows.
        """
        total_executions = 0
        successful_executions = 0

        for metrics in self.workflow_metrics.values():
            total_executions += metrics.get("total_executions", 0)
            successful_executions += metrics.get("successful_executions", 0)

        if total_executions == 0:
            return 1.0

        return successful_executions / total_executions

    def _generate_dashboard_html(self, dashboard_data: dict[str, Any]) -> str:
        """
        Generate simple dashboard HTML.
        """
        metrics_html = ""
        for workflow_type, metrics in dashboard_data.get("metrics", {}).items():
            metrics_html += f"""
            <div class="metric-card">
                <h3>{workflow_type}</h3>
                <p>Total: {metrics.get('total_executions', 0)}</p>
                <p>Success: {metrics.get('successful_executions', 0)}</p>
                <p>Failed: {metrics.get('failed_executions', 0)}</p>
                <p>Avg Duration: {metrics.get('avg_duration', 0):.2f}s</p>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MCP Workflow Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metric-card {{
                    border: 1px solid #ddd;
                    padding: 15px;
                    margin: 10px;
                    border-radius: 5px;
                }}
                h1 {{ color: #333; }}
            </style>
        </head>
        <body>
            <h1>MCP Workflow Monitoring Dashboard</h1>
            <p>Monitoring Active: {dashboard_data.get('monitoring_active', False)}</p>
            <div class="metrics">
                {metrics_html}
            </div>
        </body>
        </html>
        """


# Global integration instance
_workflow_monitoring_integration: WorkflowMonitoringIntegration | None = None


def initialize_workflow_monitoring(
    workflow_engine: Any | None = None,
    distributed_executor: Any | None = None,
    **kwargs,
) -> WorkflowMonitoringIntegration:
    """
    Initialize the global workflow monitoring integration.
    """
    global _workflow_monitoring_integration

    if _workflow_monitoring_integration is None:
        _workflow_monitoring_integration = WorkflowMonitoringIntegration(
            workflow_engine=workflow_engine, distributed_executor=distributed_executor, **kwargs,
        )

    return _workflow_monitoring_integration


def get_workflow_monitoring() -> WorkflowMonitoringIntegration | None:
    """
    Get the global workflow monitoring integration instance.
    """
    return _workflow_monitoring_integration


async def start_workflow_monitoring():
    """
    Start workflow monitoring if initialized.
    """
    if _workflow_monitoring_integration:
        await _workflow_monitoring_integration.start_monitoring()
    else:
        logger.warning("Workflow monitoring not initialized")


async def stop_workflow_monitoring():
    """
    Stop workflow monitoring if running.
    """
    if _workflow_monitoring_integration:
        await _workflow_monitoring_integration.stop_monitoring()


def monitor_workflow_execution(workflow_type: str = ""):
    """
    Decorator to automatically monitor workflow execution.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            workflow_id = kwargs.get("workflow_id", str(uuid.uuid4()))

            # Start monitoring
            integration = get_workflow_monitoring()
            if integration:
                span_id = integration.get_monitoring_context(workflow_id, workflow_type)
                start_time = time.time()

                try:
                    result = await func(*args, **kwargs)

                    # Record success
                    duration = time.time() - start_time
                    integration.record_workflow_completion(
                        span_id=span_id,
                        workflow_id=workflow_id,
                        workflow_type=workflow_type,
                        duration_seconds=duration,
                        success=True,
                    )

                    return result

                except Exception as e:
                    # Record failure
                    duration = time.time() - start_time
                    integration.record_workflow_completion(
                        span_id=span_id,
                        workflow_id=workflow_id,
                        workflow_type=workflow_type,
                        duration_seconds=duration,
                        success=False,
                        error_message=str(e),
                    )
                    raise
            else:
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            workflow_id = kwargs.get("workflow_id", str(uuid.uuid4()))

            # Start monitoring
            integration = get_workflow_monitoring()
            if integration:
                span_id = integration.get_monitoring_context(workflow_id, workflow_type)
                start_time = time.time()

                try:
                    result = func(*args, **kwargs)

                    # Record success
                    duration = time.time() - start_time
                    integration.record_workflow_completion(
                        span_id=span_id,
                        workflow_id=workflow_id,
                        workflow_type=workflow_type,
                        duration_seconds=duration,
                        success=True,
                    )

                    return result

                except Exception as e:
                    # Record failure
                    duration = time.time() - start_time
                    integration.record_workflow_completion(
                        span_id=span_id,
                        workflow_id=workflow_id,
                        workflow_type=workflow_type,
                        duration_seconds=duration,
                        success=False,
                        error_message=str(e),
                    )
                    raise
            else:
                return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
