"""
Templating utilities for fallback server pages.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

from ..templates import get_inline_error_page

logger = logging.getLogger(__name__)


class TemplateManager:
    """
    Load and render HTML templates for fallback server responses.
    """

    def __init__(self, templates_dir: Path | None = None):
        self._templates_dir = templates_dir or (
            Path(__file__).resolve().parent.parent / "templates" / "error_pages"
        )

    def load(self, page_type: str) -> str:
        """
        Return the template contents for the requested page.
        """
        template_path = self._templates_dir / f"{page_type}.html"
        if not template_path.exists():
            logger.warning("Template not found: %s", template_path)
            return get_inline_error_page()

        try:
            return template_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.exception("Failed to load template %s: %s", template_path, exc)
            return get_inline_error_page()

    def render(self, template: str, config: dict[str, Any]) -> str:
        """
        Render a plain template with fallback placeholders.
        """
        rendered = template
        replacements = {
            "{{service_name}}": str(config.get("service_name", "Service")),
            "{{refresh_interval}}": str(config.get("refresh_interval", 5)),
            "{{message}}": str(config.get("message") or ""),
            "{{timestamp}}": datetime.now().isoformat(),
            "{{status_message}}": str(config.get("status_message", "Service is starting up...")),
            "{{port}}": str(config.get("port", "-")),
            "{{pid}}": str(config.get("pid", "-")),
            "{{uptime}}": str(config.get("uptime", "0s")),
            "{{health_status}}": str(config.get("health_status", "Starting")),
            "{{state}}": str(config.get("state", "starting")),
            "{{last_output}}": str(config.get("last_output", "")),
        }
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)

        if "{{steps_html}}" in rendered:
            rendered = rendered.replace("{{steps_html}}", self._render_steps(config.get("steps")))

        return rendered

    @staticmethod
    def _render_steps(steps: Any) -> str:
        if not isinstance(steps, Iterable):
            return ""

        items = []
        for step in steps:
            if isinstance(step, dict):
                text = str(step.get("text", ""))
                status = step.get("status", "")
            else:
                text = str(step)
                status = ""
            icon = "⏳" if status == "active" else "○"
            items.append(
                f'<div class="step"><div class="step-icon {status}">{icon}</div>'
                f'<div class="step-text {status}">{text}</div></div>',
            )

        if not items:
            return ""
        return '<div class="steps">' + "".join(items) + "</div>"


__all__ = ["TemplateManager"]
