"""
HTML helpers for StatusPageGenerator.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _get_status_color(status: str) -> str:
    status_colors = {
        "healthy": "#10b981",
        "degraded": "#f59e0b",
        "down": "#ef4444",
        "starting": "#3b82f6",
        "maintenance": "#8b5cf6",
    }
    return status_colors.get((status or "").lower(), "#6b7280")


def _get_status_icon(status: str) -> str:
    status_icons = {
        "healthy": "✓",
        "degraded": "⚠",
        "down": "✗",
        "starting": "⟳",
        "maintenance": "🔧",
    }
    return status_icons.get((status or "").lower(), "○")


def _get_environment_badge(environment: str) -> str:
    env_colors = {
        "production": "background: #10b981; color: white;",
        "staging": "background: #f59e0b; color: white;",
        "development": "background: #3b82f6; color: white;",
        "dev": "background: #3b82f6; color: white;",
        "local": "background: #6b7280; color: white;",
    }
    color = env_colors.get((environment or "").lower(), "background: #667eea; color: white;")
    return f".env-badge {{ {color} }}"


def _format_bytes(bytes_value: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def generate_routes_html(routes: list[dict[str, str]]) -> str:
    if not routes:
        return '<p style="color: #666;">No routes configured</p>'
    parts: list[str] = []
    for route in routes:
        method = route.get("method", "GET").upper()
        path = route.get("path", "/")
        description = route.get("description", "No description available")
        parts.append(
            f"""<div class="route-card"><div class="route-header"><span class="route-method method-{method}">{method}</span><span class="route-path">{path}</span></div><div class="route-description">{description}</div></div>""",
        )
    return "\n".join(parts)


def generate_health_checks_html(checks: dict[str, Any]) -> str:
    if not checks:
        return '<p style="color: #666;">No health checks configured</p>'
    parts: list[str] = []
    for name, check_data in checks.items():
        if isinstance(check_data, dict):
            status = check_data.get("status", "unknown")
            message = check_data.get("message", "")
        else:
            status = "healthy" if check_data else "unhealthy"
            message = str(check_data)
        status_class = "healthy" if status in ["healthy", "ok", True] else "unhealthy"
        status_text = "✓ Healthy" if status_class == "healthy" else "✗ Unhealthy"
        parts.append(
            f"""<div class="health-check"><span class="health-check-name">{name}</span><div class="health-check-status {status_class}"><span>{status_text}</span>{f'<span style="opacity: 0.7;">({message})</span>' if message else ''}</div></div>""",
        )
    return "\n".join(parts)


def generate_metrics_html(metrics: dict[str, Any]) -> str:
    if not metrics:
        return ""
    parts: list[str] = ['<div class="metrics-grid">']
    for key, value in metrics.items():
        label = key.replace("_", " ").title()
        if isinstance(value, (int, float)):
            if key.endswith(("_ms", "_time")):
                formatted_value = f"{value}ms"
            elif key.endswith(("_bytes", "_size")):
                formatted_value = _format_bytes(float(value))
            else:
                formatted_value = str(value)
        else:
            formatted_value = str(value)
        parts.append(
            f"""<div class="metric-card"><div class="metric-value">{formatted_value}</div><div class="metric-label">{label}</div></div>""",
        )
    parts.append("</div>")
    return "\n".join(parts)


def generate_links_html(docs_url: str | None, support_url: str | None) -> str:
    links: list[dict[str, str]] = []
    if docs_url:
        links.append(
            {
                "icon": "📚",
                "title": "API Documentation",
                "description": "View API reference and guides",
                "url": docs_url,
            },
        )
    if support_url:
        links.append(
            {
                "icon": "💬",
                "title": "Support",
                "description": "Get help and support",
                "url": support_url,
            },
        )
    links.append(
        {
            "icon": "📊",
            "title": "KInfra Dashboard",
            "description": "View infrastructure dashboard",
            "url": "/kinfra",
        },
    )
    links.append(
        {
            "icon": "💚",
            "title": "Health Check",
            "description": "API health endpoint",
            "url": "/health",
        },
    )
    if not links:
        return ""
    parts: list[str] = ['<div class="links-grid">']
    for link in links:
        parts.append(
            f"""<a href="{link['url']}" class="link-card" target="_blank"><div class="link-icon">{link['icon']}</div><div class="link-content"><h3>{link['title']}</h3><p>{link['description']}</p></div></a>""",
        )
    parts.append("</div>")
    return "\n".join(parts)


def build_status_page_html(
    service_name: str,
    version: str,
    description: str,
    domain: str,
    routes_html: str,
    health_html: str,
    metrics_html: str,
    links_html: str,
    status: str,
    environment: str,
    uptime: str | None,
) -> str:
    status_color = _get_status_color(status)
    status_icon = _get_status_icon(status)
    env_badge = _get_environment_badge(environment)
    return f"""<!DOCTYPE html>
<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <title>{service_name} - Status</title>\n    <style>\n        * {{ margin: 0; padding: 0; box-sizing: border-box; }}\n        body {{ font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #333; min-height: 100vh; padding: 40px 20px; }}\n        .container {{ max-width: 1200px; margin: 0 auto; }}\n        .header {{ background: white; border-radius: 16px; padding: 40px; margin-bottom: 30px; box-shadow: 0 8px 32px rgba(0,0,0,.1); }}\n        .header-top {{ display: flex; justify-content: space-between; align-items: start; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }}\n        .service-info h1 {{ font-size: 2.5em; color: #667eea; margin-bottom: 10px; }}\n        .service-info .version {{ display: inline-block; background: #f0f0f0; padding: 4px 12px; border-radius: 12px; font-size: .85em; color: #666; margin-left: 10px; }}\n        .service-info .description {{ color: #666; font-size: 1.1em; margin-top: 10px; line-height: 1.6; }}\n        .status-badge {{ display: flex; align-items: center; gap: 10px; padding: 12px 24px; border-radius: 12px; background: {status_color}; color: white; font-weight: 600; font-size: 1.1em; }}\n        .status-icon {{ font-size: 1.5em; }}\n        .badges {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 20px; }}\n        .badge {{ padding: 6px 16px; border-radius: 8px; font-size: .9em; font-weight: 500; }}\n        {env_badge}\n        .section {{ background: white; border-radius: 16px; padding: 30px; margin-bottom: 30px; box-shadow: 0 8px 32px rgba(0,0,0,.1); }}\n        .section h2 {{ font-size: 1.8em; color: #333; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #f0f0f0; }}\n        .routes-grid {{ display: grid; gap: 15px; }}\n        .route-card {{ background: #f8f9fa; padding: 20px; border-radius: 12px; border-left: 4px solid #667eea; transition: all .3s; }}\n        .route-card:hover {{ transform: translateX(5px); box-shadow: 0 4px 12px rgba(0,0,0,.1); }}\n        .route-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }}\n        .route-method {{ padding: 4px 12px; border-radius: 6px; font-size: .85em; font-weight: 600; font-family: monospace; }}\n        .method-GET {{ background: #10b981; color: white; }} .method-POST {{ background: #3b82f6; color: white; }} .method-PUT {{ background: #f59e0b; color: white; }} .method-DELETE {{ background: #ef4444; color: white; }} .method-PATCH {{ background: #8b5cf6; color: white; }}\n        .route-path {{ font-family: monospace; font-size: 1.1em; color: #333; font-weight: 500; }}\n        .route-description {{ color: #666; font-size: .95em; line-height: 1.5; }}\n        .health-checks {{ display: grid; gap: 15px; }}\n        .health-check {{ display: flex; justify-content: space-between; align-items: center; padding: 15px 20px; background: #f8f9fa; border-radius: 10px; }}\n        .health-check-name {{ font-weight: 500; color: #333; }}\n        .health-check-status {{ display: flex; align-items: center; gap: 8px; font-size: .9em; }}\n        .health-check-status.healthy {{ color: #10b981; }} .health-check-status.unhealthy {{ color: #ef4444; }}\n        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}\n        .metric-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 12px; text-align: center; }}\n        .metric-value {{ font-size: 2em; font-weight: 700; margin-bottom: 5px; }}\n        .metric-label {{ font-size: .9em; opacity: .9; }}\n        .links-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}\n        .link-card {{ display: flex; align-items: center; gap: 15px; padding: 20px; background: #f8f9fa; border-radius: 12px; text-decoration: none; color: #333; transition: all .3s; }}\n        .link-card:hover {{ background: #667eea; color: white; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102,126,234,.4); }}\n        .link-icon {{ font-size: 2em; }}\n        .link-content h3 {{ font-size: 1.1em; margin-bottom: 5px; }}\n        .link-content p {{ font-size: .9em; opacity: .8; }}\n        .footer {{ text-align: center; color: white; margin-top: 40px; opacity: .9; }}\n        .footer a {{ color: white; text-decoration: none; font-weight: 500; }}\n        .footer a:hover {{ text-decoration: underline; }}\n        .timestamp {{ font-size: .9em; color: white; opacity: .8; margin-top: 10px; }}\n        @media (max-width: 768px) {{ .header-top {{ flex-direction: column; }} .metrics-grid {{ grid-template-columns: 1fr; }} }}\n    </style>\n</head>\n<body>\n    <div class=\"container\">\n        <div class=\"header\">\n            <div class=\"header-top\">\n                <div class=\"service-info\">\n                    <h1>{service_name}<span class=\"version\">v{version}</span></h1>\n                    <p class=\"description\">{description or 'Service Status Dashboard'}</p>\n                </div>\n                <div class=\"status-badge\"><span class=\"status-icon\">{status_icon}</span><span>{(status or 'unknown').upper()}</span></div>\n            </div>\n            <div class=\"badges\"><span class=\"badge env-badge\">{(environment or '').upper()}</span>{f'<span class="badge" style="background: #10b981; color: white;">Uptime: {uptime}</span>' if uptime else ''}<span class=\"badge\" style=\"background: #667eea; color: white;\">{domain}</span></div>\n        </div>\n        {f'<div class="section"><h2>📊 Metrics</h2>{metrics_html}</div>' if metrics_html else ''}\n        <div class=\"section\"><h2>🛣️ Available Routes</h2><div class=\"routes-grid\">{routes_html}</div></div>\n        <div class=\"section\"><h2>💚 Health Checks</h2><div class=\"health-checks\">{health_html}</div></div>\n        {f'<div class="section"><h2>🔗 Quick Links</h2>{links_html}</div>' if links_html else ''}\n        <div class=\"footer\"><p>Powered by <a href=\"https://github.com/phenoflow/kinfra\" target=\"_blank\">KInfra</a></p><p class=\"timestamp\">Last updated: {datetime.now().isoformat()}</p></div>\n    </div>\n</body>\n</html>"""
