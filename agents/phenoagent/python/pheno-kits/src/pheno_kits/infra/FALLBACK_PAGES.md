# KInfra Fallback Pages - Professional Error Handling

Cloudflare-like error and loading pages with real-time status updates.

## Features

✅ **Professional Design** - Modern, responsive HTML/CSS matching BytePort aesthetic
✅ **Real-time Updates** - JavaScript polling for live status (no page reload!)
✅ **Detailed Status** - Shows port, PID, uptime, health, progress steps
✅ **State-Aware Routing** - Proxy routes to fallback when service is down
✅ **Auto-Recovery** - Automatically redirects when service becomes healthy
✅ **Multiple Templates** - Loading, 503, maintenance, live status pages

## Page Types

### 1. Loading Page (`loading.html`)
Shows when service is starting up.

**Displays:**
- Service name
- Current status message ("Building dependencies...", "Starting server...", etc.)
- Port & PID information
- Uptime counter
- Health status
- Progress steps with icons
- Auto-refresh countdown

**Updates shown:**
- "Allocating port" → ✓
- "Starting process" → ⏳ (active)
- "Configuring tunnel" → ○ (pending)
- "Health check" → ○ (pending)

### 2. Live Status Page (`live.html`)
Shows real-time updates via JavaScript (no full page refresh).

**Features:**
- Polls `/__status__` API every 2 seconds
- Updates all fields dynamically
- Auto-redirects when service ready
- No page flickering

### 3. 503 Error Page (`503.html`)
Shows when service is unavailable/crashed.

**Displays:**
- Error code (503)
- Service name
- Custom error message
- Auto-retry countdown
- Professional error design

### 4. Maintenance Page (`maintenance.html`)
Shows during scheduled maintenance.

**Displays:**
- Maintenance notification
- Expected duration
- Custom message
- Countdown timer

### 5. Multi-Service Status (`status.html`)
Shows status of all managed services.

**Displays:**
- Grid of service cards
- Each shows: name, status, port, health
- Color-coded status indicators
- Refreshes to show latest

## Status API

All fallback pages can poll `/__status__` for real-time updates:

```javascript
// GET /__status__
{
    "service_name": "API",
    "status_message": "Building dependencies...",
    "port": "8000",
    "pid": "12345",
    "uptime": "15s",
    "health_status": "Starting",
    "state": "starting",
    "timestamp": "2025-10-09T14:50:00",
    "services": {
        "api": { ... },
        "frontend": { ... }
    }
}
```

## Usage

### Basic (Auto-enabled)
```python
from kinfra import ServiceManager, ServiceConfig, KInfra

manager = ServiceManager(KInfra())

# Fallback enabled by default!
manager.add_service(ServiceConfig(
    name="api",
    command=["python", "api.py"],
    preferred_port=8000,
    enable_fallback=True,  # Default
    fallback_page="loading",  # or "live", "503", "maintenance"
    fallback_refresh_interval=5
))
```

### With Custom Status Messages
```python
manager.add_service(ServiceConfig(
    name="api",
    command=["go", "run", "main.go"],
    enable_fallback=True,
    fallback_page="live",  # Use live updates!
    fallback_message="Building Go binary and starting server...",
    fallback_refresh_interval=3
))
```

### Update Status Programmatically
```python
# During service startup
if manager.fallback_server:
    manager.fallback_server.update_service_status(
        service_name="api",
        status_message="Installing dependencies...",
        state="starting",
        steps=[
            {"text": "Port allocation", "status": "completed"},
            {"text": "Installing packages", "status": "active"},
            {"text": "Starting server", "status": "pending"}
        ]
    )

# Later...
    manager.fallback_server.update_service_status(
        service_name="api",
        status_message="Starting HTTP server...",
        steps=[
            {"text": "Port allocation", "status": "completed"},
            {"text": "Installing packages", "status": "completed"},
            {"text": "Starting server", "status": "active"}
        ]
    )
```

## Architecture Flow

```
User Request
    ↓
Cloudflare Tunnel
    ↓
Smart Proxy (9100) ← Monitors health every 5s
    ├─→ Upstream Healthy → Route to Service (8000)
    └─→ Upstream Unhealthy → Route to Fallback (9000)
                                    ↓
                            Fallback Server
                            - Shows status page
                            - Updates via /__status__ API
                            - Auto-refresh or JS polling
```

## Real-World Examples

### Example 1: Next.js App Starting
```
Status: "Installing npm dependencies..."
Steps:
  ✓ Port allocation (8001)
  ✓ Running npm install
  ⏳ Building Next.js app
  ○ Starting dev server
  ○ Health check
```

### Example 2: Go API Starting
```
Status: "Compiling Go binary..."
Steps:
  ✓ Port allocation (8000)
  ⏳ Running go build
  ○ Starting server
  ○ Database connection
  ○ Health check
```

### Example 3: Service Crashed
```
503 Service Unavailable

API is temporarily unavailable.

We're working on getting things back up and running.

Error: Process exited with code 1

🔄 Auto-retry in 5 seconds...
```

## Status Messages by Stage

### Starting
- "Allocating resources..."
- "Building dependencies..."
- "Compiling application..."
- "Starting server process..."
- "Establishing connections..."
- "Running health checks..."

### Running
- "Service is healthy"
- "All systems operational"

### Error
- "Service crashed unexpectedly"
- "Health check failed"
- "Process terminated"

### Maintenance
- "Scheduled maintenance in progress"
- "Upgrading to version X.Y.Z"

## Design Philosophy

**Like Cloudflare:**
- Professional, clean design
- Informative error messages
- Auto-recovery without user action
- Technical details visible but not overwhelming

**BytePort Aesthetic:**
- Dark theme (#0F1115 background)
- Blue accents (#5A8DEE)
- Glassmorphism effects
- Monospace fonts for technical data
- Smooth animations

## Template Customization

### Override Templates
```python
# Use custom template directory
server = FallbackServer(
    port=9000,
    templates_dir=Path("/custom/templates")
)
```

### Custom Variables
```python
# Templates support any variables
server.page_config.update({
    "custom_field": "value",
    "build_version": "1.2.3",
    "git_commit": "abc123"
})

# Use in template:
# {{custom_field}}
# {{build_version}}
# {{git_commit}}
```

### Inline Templates
```python
# Define template inline for full control
custom_template = """
<!DOCTYPE html>
<html>
<body>
    <h1>{{service_name}}</h1>
    <p>Status: {{status_message}}</p>
    <p>Custom: {{my_field}}</p>
</body>
</html>
"""
```

## Benefits

✅ **Better UX** - Users see informative pages instead of connection errors
✅ **Professional** - Production-quality error handling
✅ **Informative** - Shows what's actually happening
✅ **Auto-recovery** - Automatically routes back when healthy
✅ **Real-time** - Live updates without page reload
✅ **Customizable** - Templates, messages, intervals all configurable
✅ **Zero Config** - Works out of the box with sensible defaults

## Comparison

### Before (Generic Error)
```
ERR_CONNECTION_REFUSED
Unable to connect
```

### After (KInfra Fallback)
```
API Server

Service is starting up...

Port: 8000
PID: 12345
Uptime: 5s
Health: Starting

Progress:
✓ Allocating port
✓ Starting process
⏳ Building dependencies
○ Health check

🔄 Auto-refreshing in 3 seconds...

[Live updates - no flicker!]
```

**Professional, informative, and automatic!**
