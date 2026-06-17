"""
HTML template helpers for the fallback server.
"""

from __future__ import annotations


def get_inline_error_page() -> str:
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


def render_logs_html(service_name: str, logs: list[dict], follow: bool) -> str:
    # Pre-render lines server-side to avoid templating collisions
    lines = []
    for log in logs:
        ts = log.get("timestamp", "")
        level = log.get("level", "info")
        level_upper = (log.get("level", "INFO") or "INFO").upper()
        msg = log.get("message", log.get("text", ""))
        lines.append(
            f'<div class="log-line"><span class="timestamp">{ts}</span> '
            f'<span class="level-{level}">[{level_upper}]</span> '
            f'<span class="message">{msg}</span></div>',
        )
    logs_html = "".join(lines)

    base = """<!DOCTYPE html>
<html>
<head>
    <title>%%SERVICE_NAME%% - Logs</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            background: #0F1115;
            color: #D1D3D9;
            padding: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        h2 {
            color: #F5F6F8;
            font-weight: 600;
        }
        .controls {
            display: flex;
            gap: 8px;
        }
        .btn {
            padding: 8px 16px;
            background: rgba(90, 141, 238, 0.1);
            color: #5A8DEE;
            border: 1px solid rgba(90, 141, 238, 0.3);
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
        }
        .btn:hover {
            background: rgba(90, 141, 238, 0.15);
        }
        #logs {
            background: #1A1D24;
            border-radius: 8px;
            padding: 16px;
            max-height: 80vh;
            overflow-y: auto;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .log-line {
            margin-bottom: 6px;
            word-wrap: break-word;
            line-height: 1.5;
        }
        .timestamp { color: #5D5F66; }
        .level-info { color: #5A8DEE; font-weight: 600; }
        .level-warn { color: #F59E0B; font-weight: 600; }
        .level-error { color: #EF4444; font-weight: 600; }
        .level-debug { color: #9EA0A6; font-weight: 600; }
        .message { color: #D1D3D9; }
        .meta {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
            font-size: 0.85em;
            color: #5D5F66;
        }
    </style>
</head>
<body>
    <div class="header">
        <h2>%%SERVICE_NAME%% - Logs</h2>
        <div class="controls">
            <button class="btn" onclick="copyLogs()">Copy All</button>
            <button class="btn" onclick="clearLogs()">Clear</button>
            <button class="btn" onclick="window.location.href='/kinfra'">Dashboard</button>
        </div>
    </div>
    <div id="logs">
        %%LOGS_HTML%%
    </div>
    <div class="meta">
        <span id="logCount">%%LOG_COUNT%% lines</span> • Auto-refresh: <span id="refreshStatus">%%FOLLOW%%</span>
    </div>
    <script>
        let autoRefresh = %%FOLLOW_BOOL%%;
        async function updateLogs() {
            if (!autoRefresh) return;
            try {
                const r = await fetch('/__status__');
                const data = await r.json();
                const serviceLogs = data.services['%%SERVICE_NAME%%']?.logs || [];
                const logsDiv = document.getElementById('logs');
                logsDiv.innerHTML = serviceLogs.map(log => {
                    const timestamp = log.timestamp || '';
                    const level = log.level || 'info';
                    const levelUpper = (log.level || 'INFO').toUpperCase();
                    const message = log.message || log.text || '';
                    return `<div class=\"log-line\"><span class=\"timestamp\">${timestamp}</span> <span class=\"level-${level}\">[${levelUpper}]</span> <span class=\"message\">${message}</span></div>`;
                }).join('');
                document.getElementById('logCount').textContent = serviceLogs.length + ' lines';
                logsDiv.scrollTop = logsDiv.scrollHeight;
            } catch (error) {
                console.error('Failed to update logs:', error);
            }
        }
        async function copyLogs() {
            const logsText = document.getElementById('logs').innerText;
            try { await navigator.clipboard.writeText(logsText); alert('Logs copied to clipboard!'); }
            catch (err) { console.error('Failed to copy logs:', err); }
        }
        function clearLogs() {
            document.getElementById('logs').innerHTML = '<div style="color: #5D5F66; text-align: center; padding: 20px;">Logs cleared</div>';
        }
        if (autoRefresh) { setInterval(updateLogs, 1000); }
    </script>
</body>
</html>"""

    return (
        base.replace("%%SERVICE_NAME%%", service_name)
        .replace("%%LOGS_HTML%%", logs_html)
        .replace("%%LOG_COUNT%%", str(len(logs)))
        .replace("%%FOLLOW%%", "ON" if follow else "OFF")
        .replace("%%FOLLOW_BOOL%%", "true" if follow else "false")
    )
