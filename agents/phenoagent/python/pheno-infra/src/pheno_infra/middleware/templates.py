"""
Template rendering helper for KInfra middleware.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from aiohttp import web  # noqa: F401  # for typing parity
except Exception:
    pass


class TemplateRenderer:
    def __init__(self, templates_dir: Path):
        self.templates_dir = templates_dir
        self._template_cache: dict[str, str] = {}

    def load_template(self, template_name: str) -> str | None:
        if template_name in self._template_cache:
            return self._template_cache[template_name]
        template_path = self.templates_dir / f"{template_name}.html"
        if not template_path.exists():
            logger.warning("Template not found: %s", template_path)
            return None
        try:
            content = template_path.read_text(encoding="utf-8")
            self._template_cache[template_name] = content
            return content
        except Exception as e:
            logger.exception("Failed to load template %s: %s", template_path, e)
            return None

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        template = self.load_template(template_name)
        if template is None:
            return self._get_fallback_html(template_name, context)
        rendered = template
        for key, value in context.items():
            rendered = rendered.replace("{{" + str(key) + "}}", str(value))
        if "{{timestamp}}" in rendered:
            rendered = rendered.replace("{{timestamp}}", datetime.now().isoformat())
        return rendered

    def _get_fallback_html(self, template_name: str, context: dict[str, Any]) -> str:
        service_name = context.get("service_name", "Service")
        status_message = context.get("status_message", "Service unavailable")
        return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>{service_name} - {template_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; display: flex; align-items: center; justify-content: center;
            min-height: 100vh; margin: 0; padding: 20px;
        }}
        .container {{ text-align: center; max-width: 600px; background: rgba(255,255,255,.1);
            backdrop-filter: blur(10px); border-radius: 20px; padding: 60px 40px; }}
        h1 {{ font-size: 2.5em; margin-bottom: 20px; }} p {{ font-size: 1.2em; opacity: .9; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class=\"container\">
        <h1>{service_name}</h1>
        <p>{status_message}</p>
        <p style=\"font-size: .9em; opacity: .7; margin-top: 30px;\">Powered by KInfra</p>
    </div>
</body>
</html>"""
