"""Performance Integration Module for MCP.

MCP-specific performance optimization and monitoring. Adapted from zen-mcp-server for
use as a reusable SDK component.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

# Use pydevkit for tracing
from pheno.dev.tracing import correlation_context

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """
    Central coordinator for MCP performance optimization features.
    """

    def __init__(self):
        self._initialized = False
        self._optimization_history: list[dict[str, Any]] = []
        self._performance_metrics: dict[str, Any] = defaultdict(dict)
        self._resource_usage: dict[str, Any] = {}

        logger.info("PerformanceOptimizer initialized for MCP")

    async def initialize_system(self) -> dict[str, Any]:
        """
        Initialize the MCP performance optimization system.
        """
        if self._initialized:
            return {"status": "already_initialized", "timestamp": datetime.now().isoformat()}

        initialization_results = {}

        with correlation_context("mcp_performance_system_init") as correlation_id:
            logger.info(
                f"Initializing MCP performance optimization system "
                f"(correlation_id: {correlation_id})",
            )

            # Initialize performance monitoring
            try:
                initialization_results["performance_monitoring"] = "initialized"
            except Exception as e:
                logger.exception(f"Failed to initialize performance monitoring: {e}")
                initialization_results["performance_monitoring"] = f"failed: {e}"

            # Perform initial system check
            try:
                import psutil

                process = psutil.Process()
                memory_info = process.memory_info()

                initialization_results["initial_system_check"] = {
                    "memory_rss_mb": memory_info.rss / 1024 / 1024,
                    "cpu_percent": process.cpu_percent(interval=0.1),
                }
            except Exception as e:
                logger.exception(f"Failed initial system check: {e}")
                initialization_results["initial_system_check"] = f"failed: {e}"

            self._initialized = True

            result = {
                "status": "initialized",
                "timestamp": datetime.now().isoformat(),
                "correlation_id": correlation_id,
                "components": initialization_results,
                "system_ready": True,
            }

            self._optimization_history.append(
                {"action": "system_initialization", "timestamp": datetime.now(), "result": result},
            )

            logger.info("MCP performance optimization system fully initialized")
            return result

    async def perform_comprehensive_optimization(self) -> dict[str, Any]:
        """
        Perform comprehensive MCP system optimization.
        """
        with correlation_context("mcp_comprehensive_optimization") as correlation_id:
            logger.info(
                f"Starting comprehensive MCP optimization (correlation_id: {correlation_id})",
            )

            optimization_results = {
                "timestamp": datetime.now().isoformat(),
                "correlation_id": correlation_id,
                "optimizations": {},
            }

            start_time = time.time()

            # 1. Memory optimization
            try:
                import gc

                gc.collect()

                optimization_results["optimizations"]["memory"] = {
                    "status": "success",
                    "garbage_collected": True,
                }
            except Exception as e:
                optimization_results["optimizations"]["memory"] = {
                    "status": "failed",
                    "error": str(e),
                }

            # 2. Resource usage check
            try:
                import psutil

                process = psutil.Process()

                optimization_results["optimizations"]["resource_check"] = {
                    "status": "success",
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "num_threads": process.num_threads(),
                }
            except Exception as e:
                optimization_results["optimizations"]["resource_check"] = {
                    "status": "failed",
                    "error": str(e),
                }

            total_time = time.time() - start_time
            optimization_results["total_time_seconds"] = total_time

            # Calculate overall success
            successful_optimizations = sum(
                1
                for opt in optimization_results["optimizations"].values()
                if opt.get("status") == "success"
            )
            total_optimizations = len(optimization_results["optimizations"])

            optimization_results["success_rate"] = (
                successful_optimizations / total_optimizations if total_optimizations > 0 else 0
            )
            optimization_results["overall_status"] = (
                "success" if successful_optimizations == total_optimizations else "partial"
            )

            self._optimization_history.append(
                {
                    "action": "comprehensive_optimization",
                    "timestamp": datetime.now(),
                    "result": optimization_results,
                },
            )

            logger.info(
                f"Comprehensive optimization completed in {total_time:.2f}s: "
                f"{successful_optimizations}/{total_optimizations} successful",
            )

            return optimization_results

    def get_performance_summary(self) -> dict[str, Any]:
        """
        Get comprehensive MCP performance summary.
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "system_initialized": self._initialized,
            "components": {},
        }

        # System metrics
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()

            summary["components"]["system_metrics"] = {
                "status": "active",
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_rss_mb": memory_info.rss / 1024 / 1024,
                "memory_vms_mb": memory_info.vms / 1024 / 1024,
                "num_threads": process.num_threads(),
            }
        except Exception as e:
            summary["components"]["system_metrics"] = {"status": "error", "error": str(e)}

        # Performance metrics
        summary["performance_metrics"] = self._performance_metrics

        # Overall health
        healthy_components = sum(
            1 for comp in summary["components"].values() if comp.get("status") == "active"
        )
        total_components = len(summary["components"])

        summary["overall_health"] = {
            "healthy_components": healthy_components,
            "total_components": total_components,
            "health_percentage": (
                (healthy_components / total_components * 100) if total_components > 0 else 0
            ),
            "status": "healthy" if healthy_components == total_components else "degraded",
        }

        summary["optimization_history_count"] = len(self._optimization_history)

        return summary

    def record_metric(
        self, metric_type: str, metric_name: str, value: Any, metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Record a performance metric.
        """
        if metric_type not in self._performance_metrics:
            self._performance_metrics[metric_type] = {}

        self._performance_metrics[metric_type][metric_name] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

    def get_optimization_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent optimization history.
        """
        return self._optimization_history[-limit:]


# Global performance optimizer instance
_performance_optimizer: PerformanceOptimizer | None = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """
    Get the global MCP performance optimizer instance.
    """
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer


# Convenience functions for common operations
async def initialize_performance_system() -> dict[str, Any]:
    """
    Initialize the complete MCP performance optimization system.
    """
    optimizer = get_performance_optimizer()
    return await optimizer.initialize_system()


async def optimize_system_performance() -> dict[str, Any]:
    """
    Perform comprehensive MCP system optimization.
    """
    optimizer = get_performance_optimizer()
    return await optimizer.perform_comprehensive_optimization()


def get_system_performance_summary() -> dict[str, Any]:
    """
    Get comprehensive MCP performance summary.
    """
    optimizer = get_performance_optimizer()
    return optimizer.get_performance_summary()
