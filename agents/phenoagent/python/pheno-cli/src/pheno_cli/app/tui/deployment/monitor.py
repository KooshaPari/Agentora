"""
Textual deployment monitor widget.
"""

from __future__ import annotations

try:
    from rich.panel import Panel
    from textual.widgets import Static

    HAS_TEXTUAL = True
except ImportError:  # pragma: no cover - textual is optional at runtime
    HAS_TEXTUAL = False
    Panel = object  # type: ignore
    Static = object  # type: ignore

from .base import BaseDeployment, DeploymentStatus


class DeploymentMonitor(Static if HAS_TEXTUAL else object):
    """Textual widget that renders real-time deployment status.

    When Textual is unavailable, the class degrades to a lightweight shim so the rest of
    the application can still import it.
    """

    def __init__(self, deployment: BaseDeployment, **kwargs):
        """Initialize the monitor and subscribe to deployment updates.

        Args:
            deployment: Deployment pipeline instance to observe.
            **kwargs: Forwarded to :class:`textual.widgets.Static` when Rich is available.
        """
        if HAS_TEXTUAL:
            super().__init__(**kwargs)
        self.deployment = deployment
        self.deployment.add_callback(self._on_deployment_update)

        if HAS_TEXTUAL:
            self.set_timer(0.5, self.refresh)  # Refresh every 500ms

    def _on_deployment_update(self, deployment: BaseDeployment) -> None:
        """Handle deployment progress updates from the pipeline.

        Args:
            deployment: Deployment pipeline instance emitting the update.
        """
        if HAS_TEXTUAL:
            self.refresh()

    def render(self):  # type: ignore[override]
        """Render the deployment status panel when Textual is available.

        Returns:
            Rich ``Panel`` containing progress information, or a fallback string
            when Textual is not installed.
        """
        if not HAS_TEXTUAL:
            return "Textual not available"

        # Overall progress
        progress = self.deployment.get_overall_progress()
        current_stage = self.deployment.get_current_stage()

        status_icons = {
            DeploymentStatus.IDLE: "⭕",
            DeploymentStatus.PREPARING: "🔄",
            DeploymentStatus.BUILDING: "🔨",
            DeploymentStatus.TESTING: "🧪",
            DeploymentStatus.PACKAGING: "📦",
            DeploymentStatus.UPLOADING: "⬆️",
            DeploymentStatus.INSTALLING: "💾",
            DeploymentStatus.COMPLETE: "✅",
            DeploymentStatus.FAILED: "❌",
            DeploymentStatus.CANCELLED: "🚫",
        }

        icon = status_icons.get(self.deployment.overall_status, "❓")

        # Build content
        content = f"[bold]{icon} Deployment Status: {self.deployment.overall_status.value.title()}[/bold]\n"
        content += f"Progress: [blue]{'▓' * int(progress / 10)}{'░' * (10 - int(progress / 10))}[/blue] {progress:.1f}%\n"

        if current_stage:
            content += f"Current: [cyan]{current_stage.description}[/cyan]\n"

        all_logs = []
        for stage in self.deployment.stages:
            all_logs.extend([f"[{stage.name}] {log}" for log in stage.logs[-2:]])

        if all_logs:
            content += "\n[bold]Recent Activity:[/bold]\n"
            content += "\n".join(all_logs[-5:])

        return Panel(content, title="Deployment Monitor", border_style="blue")


__all__ = ["HAS_TEXTUAL", "DeploymentMonitor"]
