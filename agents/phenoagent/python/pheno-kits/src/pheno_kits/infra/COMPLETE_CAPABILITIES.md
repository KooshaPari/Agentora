# KInfra Complete Capabilities Reference

Everything KInfra can manage and orchestrate.

## 1. Local Infrastructure Resources

### Docker Containers (DockerAdapter)
- ✅ PostgreSQL - `resources.postgres()`
- ✅ Redis - `resources.redis()`
- ✅ NATS - `resources.nats()`
- ✅ MongoDB - `resources.mongodb()`
- ✅ MySQL - `resources.mysql()`
- ✅ Elasticsearch - `resources.custom_docker(image="elasticsearch:8")`
- ✅ RabbitMQ - `resources.custom_docker(image="rabbitmq:3")`
- ✅ Kafka - `resources.custom_docker(image="confluentinc/cp-kafka")`
- ✅ **Any Docker image** - `resources.custom_docker()`

### System Services (SystemDaemonAdapter)
- ✅ nginx (systemd/launchd)
- ✅ PostgreSQL (system-installed)
- ✅ Redis (system-installed)
- ✅ Any systemd service
- ✅ Any launchd service

### CLI Tools (CommandAdapter)
- ✅ cloudflared tunnels
- ✅ kubectl (Kubernetes)
- ✅ Custom scripts
- ✅ Background processes
- ✅ Any CLI-based tool

## 2. Cloud/Remote Resources

### Supabase (SupabaseAdapter - SDK + CLI)
- ✅ Pause/restore projects
- ✅ Check project status
- ✅ Get connection strings
- ✅ Manage branches
- ✅ Native SDK: `supabase-management-py`
- ✅ Fallback: `supabase` CLI

### Vercel (VercelAdapter - SDK + CLI)
- ✅ Deploy projects
- ✅ Promote deployments
- ✅ Cancel deployments
- ✅ Get deployment URLs
- ✅ Native SDK: `vercel-python`
- ✅ Fallback: `vercel` CLI

### Neon (NeonAdapter - API + CLI)
- ✅ Start/suspend computes
- ✅ Manage branches
- ✅ Get connection strings
- ✅ Native: Neon HTTP API (`httpx`)
- ✅ Fallback: `neonctl` CLI

### Render.com (APIAdapter)
- ✅ Suspend/resume services
- ✅ Via REST API

### Railway (APIAdapter)
- ✅ Deploy/redeploy services
- ✅ Via GraphQL API

### Kubernetes (CommandAdapter)
- ✅ Scale deployments
- ✅ Via `kubectl` CLI

### Generic API (APIAdapter)
- ✅ Any HTTP/REST API
- ✅ Multiple auth types (Bearer, API Key, Basic, Custom)
- ✅ Configurable endpoints

## 3. Service Management

### Service Orchestration
- ✅ Multi-service lifecycle
- ✅ Dependency-ordered startup/shutdown
- ✅ Parallel or sequential startup
- ✅ Automatic restart on failure
- ✅ State persistence
- ✅ Signal handling (SIGINT, SIGTERM)

### Process Management
- ✅ Start/stop processes
- ✅ Environment variable management
- ✅ Working directory control
- ✅ stdout/stderr capture
- ✅ PID tracking
- ✅ Graceful shutdown

### Port Management
- ✅ Consistent ports across runs
- ✅ Automatic conflict resolution
- ✅ Port persistence (registry)
- ✅ Stale process cleanup
- ✅ Port reclamation

### Tunnel Management
- ✅ Cloudflare tunnel automation
- ✅ Path-based routing
- ✅ Health monitoring
- ✅ Automatic config updates
- ✅ DNS setup

### Health Monitoring
- ✅ TCP health checks
- ✅ HTTP health checks
- ✅ Custom command checks
- ✅ Docker health checks
- ✅ Continuous monitoring
- ✅ Auto-restart on unhealthy

### Fallback/Error Pages
- ✅ Professional loading pages
- ✅ 503 error pages
- ✅ Maintenance pages
- ✅ Auto-refresh
- ✅ Smart reverse proxy
- ✅ Health-aware routing

### File Watching (Optional)
- ✅ Auto-reload on file changes
- ✅ Configurable paths/patterns
- ✅ Debouncing
- ✅ Requires `watchdog` package

## 4. Deployment Patterns

### Pattern 1: Local Development
```python
# All local Docker
manager.resource_manager.add_resource_adapter(
    resource_from_dict("postgres", resources.postgres(port=5432))
)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("redis", resources.redis(port=6379))
)
```

### Pattern 2: Cloud Development
```python
# All cloud (no Docker!)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("db", resources.neon_database(...))
)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("frontend", resources.vercel_deployment(...))
)
```

### Pattern 3: Hybrid
```python
# Mix local + cloud
resources_config = {
    "redis-local": resources.redis(port=6379),        # Fast local cache
    "db-cloud": resources.supabase_project(...),      # Cloud database
    "frontend-cloud": resources.vercel_deployment(...) # Cloud frontend
}
```

### Pattern 4: Multi-Cloud
```python
# Resources from different providers
{
    "supabase-db": resources.supabase_project(...),
    "neon-analytics": resources.neon_database(...),
    "vercel-frontend": resources.vercel_deployment(...),
    "render-worker": resources.render_service(...),
    "k8s-api": resources.kubernetes_deployment(...)
}
```

## 5. Real-World Use Cases

### zen-mcp-server
```python
# Local NATS + Cloud Supabase
manager.resource_manager.add_resource_adapter(
    resource_from_dict("nats", resources.nats(port=4222, enable_jetstream=True))
)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("supabase", resources.supabase_project(
        project_id="zen-db",
        access_token=os.getenv("SUPABASE_TOKEN")
    ))
)
# Auto-pauses Supabase when not in use → save money!
```

### BytePort
```python
# Optional metadata database
if args.with_db:
    manager.resource_manager.add_resource_adapter(
        resource_from_dict("metadata", resources.postgres(port=5433))
    )
```

### atoms-mcp
```python
# Development cache
manager.resource_manager.add_resource_adapter(
    resource_from_dict("cache", resources.redis(port=6379))
)
```

## 6. Extension Points

### Custom Adapter
```python
from kinfra.adapters.base import ResourceAdapter

class MyAdapter(ResourceAdapter):
    async def start(self) -> bool: ...
    async def stop(self) -> bool: ...
    async def is_running(self) -> bool: ...
    async def check_health(self) -> bool: ...
```

### Custom Template
```python
def my_custom_resource(**kwargs):
    return {
        "type": "docker",  # or "api", "command", etc.
        "image": "my-image",
        **kwargs
    }
```

### Plugin Architecture
```python
# Register custom adapter
ResourceFactory.register_adapter("my_type", MyAdapter)

# Now usable
resource = resource_from_dict("foo", {"type": "my_type", ...})
```

## 7. Feature Matrix

| Feature | Local | Cloud | API | CLI |
|---------|-------|-------|-----|-----|
| Docker containers | ✅ | - | - | ✅ |
| System daemons | ✅ | - | - | ✅ |
| Supabase | - | ✅ | ✅ | ✅ |
| Vercel | - | ✅ | ✅ | ✅ |
| Neon | - | ✅ | ✅ | ✅ |
| Render | - | ✅ | ✅ | - |
| Railway | - | ✅ | ✅ | - |
| Kubernetes | - | ✅ | - | ✅ |
| Generic API | - | ✅ | ✅ | - |
| Health monitoring | ✅ | ✅ | ✅ | ✅ |
| Auto-restart | ✅ | ✅ | ✅ | ✅ |
| Tunnels | ✅ | ✅ | ✅ | ✅ |
| Fallback pages | ✅ | ✅ | ✅ | ✅ |

## 8. Dependencies

### Core (No External Deps)
- Standard library only
- Works out of the box

### Optional
- `psutil` - Process management (highly recommended)
- `aiohttp` - Async HTTP (for API adapters, proxy, fallback)
- `watchdog` - File watching for auto-reload
- `pyyaml` - YAML config files
- `httpx` - Neon API (alternative to aiohttp)
- `supabase-management-py` - Supabase native SDK
- `vercel-python` - Vercel native SDK

### Install Options
```bash
# Minimal (core only)
pip install kinfra

# With cloud providers
pip install kinfra[cloud]  # aiohttp, httpx

# Full
pip install kinfra[full]   # All optional deps
```

## 9. Complete Feature List

**Infrastructure:**
- [x] Port allocation with persistence
- [x] Process lifecycle management
- [x] Docker container management
- [x] System daemon management (systemd/launchd)
- [x] CLI tool management
- [x] Cloud API resource management
- [x] Cloudflare tunnel automation
- [x] Health monitoring (TCP, HTTP, custom)
- [x] Auto-restart on failure
- [x] Graceful shutdown
- [x] Signal handling

**UX/Developer Experience:**
- [x] Professional error pages
- [x] Loading screens with auto-refresh
- [x] Maintenance mode pages
- [x] Health-aware reverse proxy
- [x] Automatic fallback routing
- [x] File watching & auto-reload
- [x] Colored console output (Rich)
- [x] Progress indicators

**Configuration:**
- [x] Python dict configs
- [x] YAML file support
- [x] JSON file support
- [x] Environment variables
- [x] Template system
- [x] Config cascade (root + service)

**Cloud Providers:**
- [x] Supabase (native SDK + CLI)
- [x] Vercel (native SDK + CLI)
- [x] Neon (API + CLI)
- [x] Render (API)
- [x] Railway (API)
- [x] AWS (API/boto3 ready)
- [x] GCP (API ready)
- [x] Kubernetes (kubectl)
- [x] Generic HTTP API

**Extensibility:**
- [x] Adapter pattern for new resource types
- [x] Template system for common configs
- [x] Factory pattern for creation
- [x] Plugin architecture (custom adapters)
- [x] No core modification needed for new types

## 10. Code Reduction Statistics

**Before KInfra:**
- Custom Docker code: ~100-200 lines per project
- Custom process management: ~150 lines per project
- Custom health checks: ~50 lines per project
- Custom tunnel code: ~100 lines per project
- Total: ~400-500 lines per project

**After KInfra:**
- Resource definition: 1-3 lines per resource
- Service definition: 5-10 lines per service
- Orchestration: 10-20 lines total
- Total: ~30-50 lines per project

**Result: 90%+ infrastructure code reduction!**

## 11. Supported Platforms

- ✅ macOS (tested)
- ✅ Linux (tested)
- ✅ Windows (partial - Docker/process management work)
- ✅ Cloud/remote (platform-independent)

## Summary

**KInfra manages everything from a single interface:**
- Local Docker containers
- System services
- CLI tools
- Cloud databases (Supabase, Neon)
- Cloud deployments (Vercel, Render, Railway)
- Kubernetes workloads
- Any HTTP API

**With automatic:**
- Health monitoring
- Auto-restart
- Error pages
- Tunnels
- Port management
- Cleanup

**All in 1-3 lines of code per resource!**
