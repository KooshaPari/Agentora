"""
Status Pages - HTML template generation.

Provides HTML templates for status pages:
- Status dashboard
- Loading page
- Error page
- Maintenance page
"""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .status_pages_core import ProjectStatus


def generate_status_dashboard(project_status: "ProjectStatus") -> str:
    """Generate a status dashboard page."""
    services_html = ""
    for service in project_status.services.values():
        status_class = f"status-{service.status}"
        services_html += f"""
            <div class="service-item {status_class}">
                <div class="service-name">{service.service_name}</div>
                <div class="service-status">{service.status}</div>
                <div class="service-port">{service.host}:{service.port}</div>
                <div class="service-uptime">{_format_uptime(service.uptime)}</div>
            </div>
            """

    tunnels_html = ""
    for tunnel in project_status.tunnels.values():
        status_class = f"status-{tunnel.status}"
        tunnels_html += f"""
            <div class="tunnel-item {status_class}">
                <div class="tunnel-name">{tunnel.service_name}</div>
                <div class="tunnel-status">{tunnel.status}</div>
                <div class="tunnel-hostname">{tunnel.hostname}</div>
                <div class="tunnel-provider">{tunnel.provider}</div>
            </div>
            """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{project_status.project_name} - Status Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="30">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
            }}
            .project-name {{
                font-size: 2.5em;
                font-weight: 700;
                margin-bottom: 10px;
            }}
            .overall-status {{
                font-size: 1.2em;
                padding: 10px 20px;
                border-radius: 25px;
                display: inline-block;
                margin-bottom: 20px;
            }}
            .status-healthy {{ background: rgba(34, 197, 94, 0.3); border: 1px solid rgba(34, 197, 94, 0.5); }}
            .status-unhealthy {{ background: rgba(239, 68, 68, 0.3); border: 1px solid rgba(239, 68, 68, 0.5); }}
            .status-partial {{ background: rgba(245, 158, 11, 0.3); border: 1px solid rgba(245, 158, 11, 0.5); }}
            .status-maintenance {{ background: rgba(156, 163, 175, 0.3); border: 1px solid rgba(156, 163, 175, 0.5); }}
            .status-unknown {{ background: rgba(107, 114, 128, 0.3); border: 1px solid rgba(107, 114, 128, 0.5); }}
            .section {{
                margin-bottom: 40px;
            }}
            .section-title {{
                font-size: 1.5em;
                font-weight: 600;
                margin-bottom: 20px;
                border-bottom: 2px solid rgba(255, 255, 255, 0.3);
                padding-bottom: 10px;
            }}
            .service-item, .tunnel-item {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 15px;
                display: grid;
                grid-template-columns: 1fr auto auto auto;
                gap: 20px;
                align-items: center;
            }}
            .service-name, .tunnel-name {{
                font-weight: 600;
                font-size: 1.1em;
            }}
            .service-status, .tunnel-status {{
                padding: 5px 15px;
                border-radius: 15px;
                font-size: 0.9em;
                font-weight: 500;
            }}
            .status-running, .status-active {{ background: rgba(34, 197, 94, 0.3); color: #10b981; }}
            .status-starting {{ background: rgba(245, 158, 11, 0.3); color: #f59e0b; }}
            .status-stopping {{ background: rgba(245, 158, 11, 0.3); color: #f59e0b; }}
            .status-error, .status-inactive {{ background: rgba(239, 68, 68, 0.3); color: #ef4444; }}
            .status-unknown {{ background: rgba(107, 114, 128, 0.3); color: #6b7280; }}
            .service-port, .tunnel-hostname {{
                font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
                font-size: 0.9em;
                opacity: 0.8;
            }}
            .service-uptime, .tunnel-provider {{
                font-size: 0.9em;
                opacity: 0.7;
            }}
            .meta {{
                text-align: center;
                margin-top: 40px;
                font-size: 0.9em;
                opacity: 0.7;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="project-name">{project_status.project_name}</div>
                <div class="overall-status status-{project_status.overall_status}">
                    {project_status.overall_status.upper()}
                </div>
            </div>

            <div class="section">
                <div class="section-title">Services ({len(project_status.services)})</div>
                {services_html or '<div class="service-item">No services running</div>'}
            </div>

            <div class="section">
                <div class="section-title">Tunnels ({len(project_status.tunnels)})</div>
                {tunnels_html or '<div class="tunnel-item">No tunnels active</div>'}
            </div>

            <div class="meta">
                Last updated: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(project_status.last_updated))}
                <br>Auto-refresh: 30 seconds
            </div>
        </div>
    </body>
    </html>
    """


def generate_loading_page(project_status: "ProjectStatus") -> str:
    """Generate a loading page."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{project_status.project_name} - Starting Up</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="5">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                text-align: center;
                max-width: 600px;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 60px 40px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }}
            .spinner {{
                border: 4px solid rgba(255, 255, 255, 0.3);
                border-top: 4px solid white;
                border-radius: 50%;
                width: 60px;
                height: 60px;
                animation: spin 1s linear infinite;
                margin: 0 auto 30px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            h1 {{
                font-size: 2.5em;
                margin-bottom: 20px;
                font-weight: 700;
            }}
            p {{
                font-size: 1.2em;
                opacity: 0.9;
                line-height: 1.6;
                margin-bottom: 15px;
            }}
            .meta {{
                font-size: 0.9em;
                opacity: 0.7;
                margin-top: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="spinner"></div>
            <h1>{project_status.project_name}</h1>
            <p>Service is currently starting up...</p>
            <p>This page will automatically refresh in 5 seconds.</p>
            <div class="meta">Powered by KInfra</div>
        </div>
    </body>
    </html>
    """


def generate_error_page(
    message: str,
    project_status: "ProjectStatus | None" = None,
) -> str:
    """Generate an error page."""
    project_name = project_status.project_name if project_status else "Service"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{project_name} - Service Unavailable</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="10">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                text-align: center;
                max-width: 600px;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 60px 40px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }}
            .error-icon {{
                font-size: 4em;
                margin-bottom: 30px;
            }}
            h1 {{
                font-size: 2.5em;
                margin-bottom: 20px;
                font-weight: 700;
            }}
            p {{
                font-size: 1.2em;
                opacity: 0.9;
                line-height: 1.6;
                margin-bottom: 15px;
            }}
            .meta {{
                font-size: 0.9em;
                opacity: 0.7;
                margin-top: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-icon">!</div>
            <h1>{project_name}</h1>
            <p>{message}</p>
            <p>Please try again later.</p>
            <div class="meta">Powered by KInfra</div>
        </div>
    </body>
    </html>
    """


def generate_maintenance_page(project_status: "ProjectStatus") -> str:
    """Generate a maintenance page."""
    maintenance_message = project_status.metadata.get(
        "maintenance_message",
        "Service is under maintenance",
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{project_status.project_name} - Under Maintenance</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="30">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                text-align: center;
                max-width: 600px;
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 60px 40px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }}
            .maintenance-icon {{
                font-size: 4em;
                margin-bottom: 30px;
            }}
            h1 {{
                font-size: 2.5em;
                margin-bottom: 20px;
                font-weight: 700;
            }}
            p {{
                font-size: 1.2em;
                opacity: 0.9;
                line-height: 1.6;
                margin-bottom: 15px;
            }}
            .meta {{
                font-size: 0.9em;
                opacity: 0.7;
                margin-top: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="maintenance-icon">*</div>
            <h1>{project_status.project_name}</h1>
            <p>{maintenance_message}</p>
            <p>We'll be back soon!</p>
            <div class="meta">Powered by KInfra</div>
        </div>
    </body>
    </html>
    """


def _format_uptime(uptime: float) -> str:
    """Format uptime in a human-readable format."""
    if uptime < 60:
        return f"{int(uptime)}s"
    if uptime < 3600:
        return f"{int(uptime // 60)}m {int(uptime % 60)}s"
    hours = int(uptime // 3600)
    minutes = int((uptime % 3600) // 60)
    return f"{hours}h {minutes}m"
