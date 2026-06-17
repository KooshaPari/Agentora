"""
HTML helpers for WildcardStatusHandler.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..status_page import StatusPageGenerator


def generate_routes_table_html(routes: list[dict[str, str]]) -> str:
    if not routes:
        return '<p style="color: #666;">No routes configured</p>'
    html = '<table class="routes-table">'
    html += "<thead><tr><th>Method</th><th>Path</th><th>Description</th></tr></thead>"
    html += "<tbody>"
    for route in routes:
        method = route.get("method", "GET").upper()
        path = route.get("path", "/")
        description = route.get("description", "-")
        html += f'<tr><td><span class="method method-{method}">{method}</span></td><td><code>{path}</code></td><td>{description}</td></tr>'
    html += "</tbody></table>"
    return html


def generate_404_html(
    status_generator: StatusPageGenerator,
    requested_path: str,
    requested_method: str,
    routes: list[dict[str, str]],
    suggestions: list[dict[str, str]],
) -> str:
    suggestions_html = ""
    if suggestions:
        suggestions_html = '<div class="suggestions-section">'
        suggestions_html += '<h3>Did you mean?</h3><ul class="suggestions-list">'
        for suggestion in suggestions[:3]:
            method = suggestion.get("method", "GET")
            path = suggestion.get("path", "/")
            desc = suggestion.get("description")
            suggestions_html += f'<li><a href="{path}"><span class="method method-{method}">{method}</span><span class="path">{path}</span></a>'
            if desc:
                suggestions_html += f'<span class="desc">{desc}</span>'
            suggestions_html += "</li>"
        suggestions_html += "</ul></div>"

    routes_html = generate_routes_table_html(routes)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{status_generator.service_name} - Route Not Found</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #333; min-height: 100vh; padding: 40px 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .error-card {{ background: white; border-radius: 16px; padding: 50px 40px; margin-bottom: 30px; box-shadow: 0 8px 32px rgba(0,0,0,.1); text-align: center; }}
        .error-icon {{ font-size: 100px; margin-bottom: 20px; animation: float 3s ease-in-out infinite; }}
        @keyframes float {{ 0%, 100% {{ transform: translateY(0px); }} 50% {{ transform: translateY(-20px); }} }}
        h1 {{ font-size: 4em; color: #667eea; margin-bottom: 10px; }}
        h2 {{ font-size: 1.8em; color: #333; margin-bottom: 20px; }}
        .requested-route {{ display: inline-flex; align-items: center; gap: 10px; background: #f8f9fa; padding: 12px 24px; border-radius: 8px; margin: 20px 0; font-family: monospace; }}
        .method {{ padding: 4px 12px; border-radius: 6px; font-size: .85em; font-weight: 600; font-family: monospace; }}
        .method-GET {{ background: #10b981; color: white; }} .method-POST {{ background: #3b82f6; color: white; }} .method-PUT {{ background: #f59e0b; color: white; }} .method-DELETE {{ background: #ef4444; color: white; }} .method-PATCH {{ background: #8b5cf6; color: white; }}
        .path {{ font-weight: 600; color: #333; }}
        .message {{ color: #666; font-size: 1.1em; margin: 20px 0; line-height: 1.6; }}
        .suggestions-section {{ margin: 30px 0; padding: 20px; background: #f0f4ff; border-radius: 12px; text-align: left; }}
        .suggestions-section h3 {{ color: #667eea; margin-bottom: 15px; font-size: 1.2em; }}
        .suggestions-list {{ list-style: none; }}
        .suggestions-list li {{ margin: 10px 0; }}
        .suggestions-list a {{ display: inline-flex; align-items: center; gap: 10px; padding: 10px 15px; background: white; border-radius: 8px; text-decoration: none; color: #333; transition: all .3s; }}
        .suggestions-list a:hover {{ background: #667eea; color: white; transform: translateX(5px); }}
        .suggestions-list a:hover .method {{ background: white; color: #667eea; }}
        .suggestions-list .desc {{ font-size: .9em; color: #666; margin-left: 10px; }}
        .section {{ background: white; border-radius: 16px; padding: 30px; margin-bottom: 30px; box-shadow: 0 8px 32px rgba(0,0,0,.1); }}
        .section h3 {{ font-size: 1.5em; color: #333; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #f0f0f0; }}
        .routes-table {{ width: 100%; border-collapse: collapse; }}
        .routes-table th {{ text-align: left; padding: 12px; background: #f8f9fa; font-weight: 600; color: #333; }}
        .routes-table td {{ padding: 12px; border-top: 1px solid #e5e7eb; }}
        .routes-table tr:hover {{ background: #f8f9fa; }}
        .actions {{ display: flex; gap: 15px; justify-content: center; margin-top: 30px; flex-wrap: wrap; }}
        .btn {{ padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 8px; text-decoration: none; font-weight: 500; transition: all .3s; cursor: pointer; }}
        .btn:hover {{ background: #5568d3; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102,126,234,.4); }}
        .btn-secondary {{ background: #6b7280; }}
        .btn-secondary:hover {{ background: #4b5563; }}
        .footer {{ text-align: center; color: white; margin-top: 40px; opacity: .9; }}
        .footer a {{ color: white; text-decoration: none; font-weight: 500; }}
        .footer a:hover {{ text-decoration: underline; }}
        @media (max-width: 768px) {{ .routes-table {{ font-size: .9em; }} .error-icon {{ font-size: 60px; }} h1 {{ font-size: 2.5em; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="error-card">
            <div class="error-icon">🔍</div>
            <h1>404</h1>
            <h2>Route Not Found</h2>
            <div class="requested-route">
                <span class="method method-{requested_method}">{requested_method}</span>
                <span class="path">{requested_path}</span>
            </div>
            <p class="message">The route you're looking for doesn't exist on this server. Check the available routes below or return to the home page.</p>
            {suggestions_html}
            <div class="actions">
                <a href="/" class="btn">🏠 Home</a>
                <a href="/kinfra" class="btn">📊 Dashboard</a>
                <a href="/__status__" class="btn btn-secondary">💚 Status API</a>
            </div>
        </div>
        <div class="section"><h3>📍 Available Routes</h3>{routes_html}</div>
        <div class="footer"><p>Powered by <a href="https://github.com/phenoflow/kinfra" target="_blank">KInfra</a></p></div>
    </div>
</body>
</html>"""
