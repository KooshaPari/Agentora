"""
Fallback Server - Lightweight HTTP server for error/loading pages

Serves custom error pages and loading screens when upstream services are unavailable.
Provides better UX during downtime, startup, or maintenance periods.
"""

import asyncio
import logging
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

from aiohttp import web

try:
    from aiohttp import web

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    web = None


logger = logging.getLogger(__name__)


class FallbackServer:
    """Lightweight HTTP server for serving error and loading pages.

    Features:
    - Serves 503 Service Unavailable pages
    - Serves custom loading screens with auto-refresh
    - Serves maintenance mode pages
    - Template variable substitution
    - Minimal resource usage
    """

    def __init__(self, port: int = 9000, templates_dir: Path | None = None):
        """Initialize fallback server.

        Args:
            port: Port to run the server on (default: 9000)
            templates_dir: Directory containing HTML templates (default: kinfra/templates/error_pages)
        """
        if not HAS_AIOHTTP:
            raise ImportError(
                "aiohttp is required for FallbackServer. Install with: pip install aiohttp",
            )

        self.port = port
        self.templates_dir = templates_dir or (Path(__file__).parent / "templates" / "error_pages")
        self.app = web.Application()
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

        # Current page configuration
        self.current_page = "loading"
        self.page_config: dict[str, any] = {
            "service_name": "Service",
            "refresh_interval": 5,
            "message": None,
            "status_message": "Service is starting up...",
            "port": "-",
            "pid": "-",
            "uptime": "0s",
            "health_status": "Starting",
            "state": "starting",
            "logs": [],
            "steps": [],
        }

        # Service status tracking (updated by ServiceManager)
        self.service_status: dict[str, dict[str, any]] = {}

        # Service manager reference (for actions)
        self.service_manager = None

        # Setup routes
        self.app.router.add_get("/kinfra", self._handle_dashboard)
        self.app.router.add_get("/__status__", self._handle_status_api)
        self.app.router.add_post("/__action__/restart/{service}", self._handle_restart)
        self.app.router.add_post("/__action__/stop/{service}", self._handle_stop)
        self.app.router.add_get("/__logs__/{service}", self._handle_logs)
        self.app.router.add_get("/{path:.*}", self._handle_request)

        logger.info(f"FallbackServer initialized on port {port}")

    async def start(self):
        """
        Start the fallback server.
        """
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "127.0.0.1", self.port)
            await self.site.start()
            logger.info(f"Fallback server started on http://127.0.0.1:{self.port}")
        except Exception as e:
            logger.exception(f"Failed to start fallback server: {e}")
            raise

    async def stop(self):
        """
        Stop the fallback server.
        """
        if self.site:
            await self.site.stop()
            logger.info("Fallback server site stopped")

        if self.runner:
            await self.runner.cleanup()
            logger.info("Fallback server runner cleaned up")

    async def _handle_request(self, request: "web.Request") -> "web.Response":
        """
        Handle incoming HTTP requests.
        """
        # Get template content
        template_content = self._load_template(self.current_page)

        if template_content is None:
            # Fallback to inline error page if template not found
            template_content = self._get_inline_error_page()

        # Substitute variables
        rendered_content = self._render_template(template_content, self.page_config)

        return web.Response(
            text=rendered_content,
            content_type="text/html",
            status=(
                HTTPStatus.SERVICE_UNAVAILABLE if self.current_page != "loading" else HTTPStatus.OK
            ),
        )

    def _load_template(self, page_type: str) -> str | None:
        """
        Load HTML template from disk.
        """
        template_path = self.templates_dir / f"{page_type}.html"

        if not template_path.exists():
            logger.warning(f"Template not found: {template_path}")
            return None

        try:
            return template_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.exception(f"Failed to load template {template_path}: {e}")
            return None

    async def _handle_dashboard(self, request: "web.Request") -> "web.Response":
        """
        Handle KInfra dashboard request.
        """
        dashboard_template = self._load_template("dashboard")

        if dashboard_template is None:
            # Fallback to simple dashboard
            dashboard_template = "<html><body><h1>KInfra Dashboard</h1><pre id='status'></pre><script>setInterval(async()=>{const r=await fetch('/__status__');document.getElementById('status').textContent=JSON.stringify(await r.json(),null,2)},2000)</script></body></html>"

        # Render with current config
        rendered = self._render_template(dashboard_template, self.page_config)

        return web.Response(text=rendered, content_type="text/html")

    async def _handle_status_api(self, request: "web.Request") -> "web.Response":
        """
        Handle status API requests for JavaScript polling.
        """
        import json

        status_data = {
            "service_name": self.page_config.get("service_name", "Service"),
            "status_message": self.page_config.get("status_message", "Starting..."),
            "port": self.page_config.get("port", "-"),
            "pid": self.page_config.get("pid", "-"),
            "uptime": self.page_config.get("uptime", "0s"),
            "health_status": self.page_config.get("health_status", "Starting"),
            "state": self.page_config.get("state", "starting"),
            "timestamp": datetime.now().isoformat(),
            "services": self.service_status,
        }

        return web.Response(text=json.dumps(status_data), content_type="application/json")

    async def _handle_restart(self, request: "web.Request") -> "web.Response":
        """
        Handle service restart action.
        """
        import json

        service_name = request.match_info.get("service")

        if not self.service_manager:
            return web.Response(
                text=json.dumps({"success": False, "error": "Service manager not configured"}),
                content_type="application/json",
            )

        try:
            # Trigger restart via service manager
            success = await self.service_manager.reload_service(service_name)

            return web.Response(
                text=json.dumps({"success": success, "service": service_name}),
                content_type="application/json",
            )
        except Exception as e:
            return web.Response(
                text=json.dumps({"success": False, "error": str(e)}),
                content_type="application/json",
                status=500,
            )

    async def _handle_stop(self, request: "web.Request") -> "web.Response":
        """
        Handle service stop action.
        """
        import json

        service_name = request.match_info.get("service")

        if not self.service_manager:
            return web.Response(
                text=json.dumps({"success": False, "error": "Service manager not configured"}),
                content_type="application/json",
            )

        try:
            success = await self.service_manager.stop_service(service_name)

            return web.Response(
                text=json.dumps({"success": success, "service": service_name}),
                content_type="application/json",
            )
        except Exception as e:
            return web.Response(
                text=json.dumps({"success": False, "error": str(e)}),
                content_type="application/json",
                status=500,
            )

    async def _handle_logs(self, request: "web.Request") -> "web.Response":
        """
        Handle logs view for a service.
        """

        service_name = request.match_info.get("service")
        service_data = self.service_status.get(service_name, {})
        logs = service_data.get("logs", [])

        # Simple HTML logs view
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{service_name} - Logs</title>
    <style>
        body {{
            font-family: monospace;
            background: #1A1D24;
            color: #D1D3D9;
            padding: 20px;
        }}
        .log-line {{ margin-bottom: 8px; }}
        .timestamp {{ color: #5D5F66; }}
        .level-info {{ color: #5A8DEE; }}
        .level-warn {{ color: #F59E0B; }}
        .level-error {{ color: #EF4444; }}
    </style>
</head>
<body>
    <h2>{service_name} Logs</h2>
    <div id="logs">
        {''.join([f'<div class="log-line"><span class="timestamp">{log.get("timestamp", "")}</span> <span class="level-{log.get("level", "info")}">[{log.get("level", "INFO").upper()}]</span> {log.get("message", log.get("text", ""))}</div>' for log in logs])}
    </div>
    <script>
        setInterval(async () => {{
            const r = await fetch('/__status__');
            const data = await r.json();
            const serviceLogs = data.services['{service_name}']?.logs || [];
            document.getElementById('logs').innerHTML = serviceLogs.map(log =>
                `<div class="log-line"><span class="timestamp">${{log.timestamp}}</span> <span class="level-${{log.level || 'info'}}">${{(log.level || 'INFO').toUpperCase()}}</span> ${{log.message || log.text}}</div>`
            ).join('');
        }}, 1000);
    </script>
</body>
</html>"""

        return web.Response(text=html, content_type="text/html")

    def _render_template(self, template: str, config: dict[str, any]) -> str:
        """Render template with variable substitution.

        Supports all variables in config dict.
        """
        rendered = template

        # Basic substitutions
        rendered = rendered.replace("{{service_name}}", str(config.get("service_name", "Service")))
        rendered = rendered.replace("{{refresh_interval}}", str(config.get("refresh_interval", 5)))
        rendered = rendered.replace("{{message}}", str(config.get("message") or ""))
        rendered = rendered.replace("{{timestamp}}", datetime.now().isoformat())

        # Status information
        rendered = rendered.replace(
            "{{status_message}}", str(config.get("status_message", "Service is starting up...")),
        )
        rendered = rendered.replace("{{port}}", str(config.get("port", "-")))
        rendered = rendered.replace("{{pid}}", str(config.get("pid", "-")))
        rendered = rendered.replace("{{uptime}}", str(config.get("uptime", "0s")))
        rendered = rendered.replace(
            "{{health_status}}", str(config.get("health_status", "Starting")),
        )
        return rendered.replace("{{state}}", str(config.get("state", "starting")))

        # Note: Complex structures like steps/logs handled by JavaScript templating
        # For now, simplified HTML-only rendering


    def _get_inline_error_page(self) -> str:
        """
        Get inline HTML error page as fallback.
        """
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="{{refresh_interval}}">
    <title>{{service_name}} - Service Unavailable</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            text-align: center;
            max-width: 600px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 60px 40px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        .spinner {
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 60px;
            height: 60px;
            animation: spin 1s linear infinite;
            margin: 0 auto 30px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        h1 { font-size: 2.5em; margin-bottom: 20px; font-weight: 700; }
        p { font-size: 1.2em; opacity: 0.9; line-height: 1.6; margin-bottom: 15px; }
        .meta { font-size: 0.9em; opacity: 0.7; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="spinner"></div>
        <h1>{{service_name}}</h1>
        <p>Service is currently starting up...</p>
        <p>This page will automatically refresh in {{refresh_interval}} seconds.</p>
        <div class="meta">Powered by KInfra</div>
    </div>
</body>
</html>"""

    def set_page(
        self,
        page_type: str = "loading",
        service_name: str = "Service",
        refresh_interval: int = 5,
        message: str | None = None,
    ):
        """Configure the current error/loading page.

        Args:
            page_type: Type of page ("loading", "503", "maintenance")
            service_name: Name of the service
            refresh_interval: Auto-refresh interval in seconds
            message: Optional custom message
        """
        self.current_page = page_type
        self.page_config.update(
            {"service_name": service_name, "refresh_interval": refresh_interval, "message": message},
        )
        logger.debug(f"Fallback page configured: {page_type} for {service_name}")

    def update_service_status(
        self,
        service_name: str,
        status_message: str | None = None,
        port: int | None = None,
        pid: int | None = None,
        uptime: str | None = None,
        health_status: str | None = None,
        state: str | None = None,
        logs: list | None = None,
        steps: list | None = None,
    ):
        """Update real-time status for a service.

        Args:
            service_name: Service name
            status_message: Current status message (e.g., "Building dependencies...")
            port: Service port
            pid: Process ID
            uptime: Service uptime
            health_status: Health check status
            state: Service state (starting, running, error, stopped)
            logs: Recent log lines
            steps: List of startup steps with status
        """
        status_data = {}

        if status_message:
            status_data["status_message"] = status_message
        if port is not None:
            status_data["port"] = str(port)
        if pid is not None:
            status_data["pid"] = str(pid)
        if uptime:
            status_data["uptime"] = uptime
        if health_status:
            status_data["health_status"] = health_status
        if state:
            status_data["state"] = state
        if logs:
            status_data["logs"] = logs
        if steps:
            status_data["steps"] = steps

        self.service_status[service_name] = status_data
        self.page_config.update(status_data)

        logger.debug(f"Updated status for {service_name}: {state or 'unknown'}")


# Convenience function for standalone usage
async def run_fallback_server(
    port: int = 9000,
    page_type: str = "loading",
    service_name: str = "Service",
    refresh_interval: int = 5,
):
    """Run fallback server standalone.

    Example:
        >>> await run_fallback_server(port=9000, page_type="loading", service_name="BytePort")
    """
    server = FallbackServer(port=port)
    server.set_page(
        page_type=page_type, service_name=service_name, refresh_interval=refresh_interval,
    )

    await server.start()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down fallback server...")
        await server.stop()
