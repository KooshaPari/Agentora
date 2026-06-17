# KInfra Dashboard - Always-Available Monitoring

The `/kinfra` path always returns a real-time monitoring dashboard.

## Access

```
https://byte.kooshapari.com/kinfra
http://localhost:9100/kinfra  (via proxy)
http://localhost:9000/kinfra  (direct to fallback server)
```

## Features

### 1. Real-Time Monitoring
- ✅ Live updates every 2 seconds (no page reload)
- ✅ Shows all managed services
- ✅ Color-coded status indicators
- ✅ Detailed metrics per service

### 2. Service Information
Each service shows:
- **Name** - Service identifier
- **Status** - Current state with visual indicator (🟢 Running, 🟡 Starting, 🔴 Error)
- **Port** - Allocated port
- **PID** - Process ID
- **Uptime** - How long service has been running
- **Health** - Health check status
- **Logs** - Recent log lines (last 10)

### 3. Action Buttons
Per-service actions:
- **🔄 Restart** - Restart the service
- **📄 View Logs** - Full log view in new tab
- **⏹ Stop** - Stop the service

Global actions:
- **🔄 Refresh All** - Force refresh all data

### 4. Statistics Bar
Shows at-a-glance metrics:
- Total services
- Running services (green)
- Starting services (yellow)
- Error services (red)

## API Endpoints

### GET `/kinfra`
Returns HTML dashboard with live updates.

### GET `/__status__`
Returns JSON with all service status.

```json
{
  "service_name": "API",
  "status_message": "Service is running",
  "port": "8000",
  "pid": "12345",
  "uptime": "5m 32s",
  "health_status": "Healthy",
  "state": "running",
  "timestamp": "2025-10-09T15:00:00",
  "services": {
    "api": {
      "status_message": "Service is running",
      "port": "8000",
      "pid": "12345",
      "uptime": "5m 32s",
      "health_status": "Healthy",
      "state": "running",
      "logs": [
        {
          "timestamp": "15:00:01",
          "level": "info",
          "message": "Server started on port 8000"
        }
      ]
    },
    "frontend": {
      "status_message": "Building...",
      "port": "8001",
      "pid": "12346",
      "state": "starting",
      "logs": [...]
    }
  }
}
```

### POST `/__action__/restart/{service}`
Restart a service.

**Response:**
```json
{
  "success": true,
  "service": "api"
}
```

### POST `/__action__/stop/{service}`
Stop a service.

**Response:**
```json
{
  "success": true,
  "service": "api"
}
```

### GET `/__logs__/{service}`
View full logs for a service in separate page.

## Usage

### Default (Auto-enabled)
```python
from kinfra import ServiceManager, KInfra

manager = ServiceManager(KInfra())

# Dashboard automatically available at /kinfra
# No configuration needed!
```

### Update Service Logs
```python
# ServiceManager automatically captures logs and sends to fallback server
# But you can also manually update:

if manager.fallback_server:
    manager.fallback_server.update_service_status(
        service_name="api",
        logs=[
            {
                "timestamp": "15:00:01",
                "level": "info",
                "message": "Server started successfully"
            },
            {
                "timestamp": "15:00:02",
                "level": "warn",
                "message": "Rate limit approaching"
            }
        ]
    )
```

## Routing Behavior

### When Services Healthy
```
User Request → Proxy (9100)
├─ /kinfra → Fallback (9000) → Dashboard
├─ /__status__ → Fallback (9000) → JSON
├─ /__action__/* → Fallback (9000) → Actions
├─ /api/* → API Service (8000)
└─ /* → Frontend (8001)
```

### When Services Unhealthy
```
User Request → Proxy (9100)
├─ /kinfra → Fallback (9000) → Dashboard (shows errors)
├─ /api/* → Fallback (9000) → Loading page
└─ /* → Fallback (9000) → Loading page
```

**`/kinfra` ALWAYS works** - even when all services are down!

## Dashboard Views

### All Services Healthy
```
🚀 KInfra Dashboard
Live • Updates every 2s                    🔄 Refresh All

┌─────────────────────────────────────────────────┐
│ 2 Total   2 Running   0 Starting   0 Errors    │
└─────────────────────────────────────────────────┘

┌─────────────────────┐ ┌─────────────────────┐
│ 🟢 API              │ │ 🟢 Frontend         │
│ Running             │ │ Running             │
│ Port: 8000          │ │ Port: 8001          │
│ PID: 12345          │ │ PID: 12346          │
│ Health: Healthy     │ │ Health: Healthy     │
│                     │ │                     │
│ [Logs: 5 lines]     │ │ [Logs: 3 lines]     │
│                     │ │                     │
│ [🔄 Restart] [📄]   │ │ [🔄 Restart] [📄]   │
└─────────────────────┘ └─────────────────────┘
```

### Service Starting
```
┌─────────────────────┐
│ 🟡 API              │
│ Building deps...    │
│ Port: 8000          │
│ PID: 12345          │
│ Health: Starting    │
│                     │
│ Recent Logs:        │
│ [INFO] npm install  │
│ [INFO] Downloading  │
│ [INFO] Building...  │
│                     │
│ [🔄 Restart] [📄]   │
└─────────────────────┘
```

### Service Error
```
┌─────────────────────┐
│ 🔴 API              │
│ Process crashed     │
│ Port: 8000          │
│ PID: - (stopped)    │
│ Health: Unhealthy   │
│                     │
│ Recent Logs:        │
│ [ERROR] EADDRINUSE  │
│ [ERROR] Exit code 1 │
│                     │
│ [🔄 Restart] [⏹]    │
└─────────────────────┘
```

## Integration Examples

### BytePort
```python
# Access dashboard at:
https://byte.kooshapari.com/kinfra

# Shows:
- API service status
- Frontend service status
- All with real-time logs
- Action buttons to restart services
```

### zen-mcp-server
```python
# Access dashboard at:
https://zen.kooshapari.com/kinfra

# Shows:
- zen-mcp service
- NATS container status
- Postgres container status
- All with health monitoring
```

## Logs Integration

### Automatic Log Capture
ServiceManager can automatically capture stdout/stderr:

```python
# In ServiceManager.start_service():
# Logs are captured from process stdout/stderr
# Sent to fallback_server.update_service_status()
```

### Manual Log Updates
```python
manager.fallback_server.update_service_status(
    service_name="api",
    logs=[
        {"timestamp": "15:00:01", "level": "info", "message": "Started"},
        {"timestamp": "15:00:02", "level": "warn", "message": "Slow query"}
    ]
)
```

### Log Levels
Supported levels with color coding:
- **INFO** - Blue (#5A8DEE)
- **WARN** - Yellow (#F59E0B)
- **ERROR** - Red (#EF4444)
- **DEBUG** - Gray (#9EA0A6)

## Security

### Action Authorization
Currently, actions are open (localhost only).

For production, add authentication:
```python
# In fallback_server.py _handle_restart()
auth_header = request.headers.get('Authorization')
if auth_header != f"Bearer {os.getenv('KINFRA_ADMIN_TOKEN')}":
    return web.Response(status=401)
```

### CORS
Dashboard is localhost-only by default (127.0.0.1).

For remote access:
```python
FallbackServer(
    port=9000,
    allow_remote=True,  # Listen on 0.0.0.0
    admin_token="your-secret-token"
)
```

## Customization

### Custom Dashboard Template
```python
# Place custom template at:
# ~/.kinfra/templates/dashboard.html

# Or specify directory:
FallbackServer(
    port=9000,
    templates_dir=Path("/custom/templates")
)
```

### Disable Actions
```python
# Don't connect service_manager
fallback_server.service_manager = None

# Action buttons will show "Not available"
```

## Benefits

✅ **Always Available** - `/kinfra` works even when all services down
✅ **Real-Time** - No page reload, updates every 2s
✅ **Actionable** - Restart/stop services from browser
✅ **Informative** - See actual logs in real-time
✅ **Professional** - Production-quality monitoring UI
✅ **Zero Config** - Works out of the box

## Comparison

### Before
- No monitoring dashboard
- Must check logs via CLI
- No way to restart from browser
- Connection errors when services down

### After
- Professional dashboard at `/kinfra`
- Live logs in browser
- One-click restart/stop
- Always accessible monitoring

**Like having Vercel/Railway dashboard for ANY infrastructure!**
