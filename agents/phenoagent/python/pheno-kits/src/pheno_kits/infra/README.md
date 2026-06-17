# KInfra - Universal Infrastructure Management

Cross-platform infrastructure library for dynamic port allocation, service orchestration, and resource management.

## Features

✅ **Service Orchestration** - Multi-service lifecycle management with dependencies
✅ **Smart Port Allocation** - Consistent ports across runs with conflict resolution
✅ **Cloudflare Tunnels** - Automatic tunnel management with health monitoring
✅ **Resource Management** - Docker, systemd, CLI tools, cloud APIs (Supabase, Vercel, Neon)
✅ **Fallback Pages** - Professional error/loading pages like Cloudflare
✅ **Health Monitoring** - Automatic health checks and auto-restart
✅ **Native SDKs** - Use official SDKs when available, CLI as fallback

## Quick Start

```python
from kinfra import ServiceManager, ServiceConfig, KInfra
from kinfra.templates import resources
from kinfra.adapters import resource_from_dict

# Initialize
manager = ServiceManager(KInfra(domain="myapp.com"))

# Add Postgres (one line!)
pg = resource_from_dict("db", resources.postgres(port=5432))
manager.resource_manager.add_resource_adapter(pg)

# Add service
manager.add_service(ServiceConfig(
    name="api",
    command=["python", "api.py"],
    preferred_port=8000,
    enable_tunnel=True,
    enable_fallback=True  # Auto error pages!
))

# Start everything
await manager.start_all()
await manager.monitor()
```

## Architecture

```
KInfra (Unified API)
├── ServiceOrchestrator     → Multi-service management
│   └── ServiceManager      → Individual service lifecycle
│       ├── ResourceManager → Docker/daemon/API resources
│       │   └── Adapters    → docker, systemd, command, api, cloud/*
│       ├── FallbackServer  → Error/loading pages
│       └── ProxyServer     → Health-aware routing
├── PortRegistry           → Port persistence
├── SmartPortAllocator     → Intelligent allocation
└── TunnelManager          → Cloudflare tunnels
```

## Supported Resource Types

### Local Infrastructure
- **Docker** - Any container (Postgres, Redis, NATS, MongoDB, MySQL, custom)
- **systemd/launchd** - System daemons
- **CLI tools** - Any command-line tool
- **Custom processes** - Arbitrary processes

### Cloud Resources (with Native SDKs!)
- **Supabase** - Pause/restore projects (SDK + CLI)
- **Vercel** - Deploy/promote deployments (SDK + CLI)
- **Neon** - Serverless Postgres (API + CLI)
- **Render.com** - Suspend/resume services (API)
- **Railway** - Manage services (API)
- **Kubernetes** - Scale deployments (kubectl)
- **Any HTTP API** - Generic API adapter

## Usage Patterns

### 1. Docker Resources
```python
# Use template
pg = resource_from_dict("db", resources.postgres(port=5432, password="secret"))

# Or dict config
config = {
    "type": "docker",
    "image": "postgres:16",
    "ports": {5432: 5432},
    "environment": {"POSTGRES_PASSWORD": "secret"}
}
pg = resource_from_dict("db", config)
```

### 2. Cloud Resources (Supabase)
```python
# Native SDK with CLI fallback
supabase = resource_from_dict("cloud-db", resources.supabase_project(
    project_id="your-project-id",
    access_token=os.getenv("SUPABASE_TOKEN"),
    database_password="your-db-password"
))

# Auto-restores project on start, pauses on stop
```

### 3. Vercel Deployments
```python
vercel = resource_from_dict("frontend", resources.vercel_deployment(
    project_name="my-app",
    team_id="team_xxx",
    access_token=os.getenv("VERCEL_TOKEN"),
    target="production"
))

# Auto-deploys on start
```

### 4. Neon Serverless Postgres
```python
neon = resource_from_dict("serverless-db", resources.neon_database(
    project_id="neon-project-id",
    api_key=os.getenv("NEON_API_KEY"),
    branch_name="main"
))

# Auto-starts compute on demand
```

### 5. Mixed Local + Cloud
```python
# Local Redis cache
redis = resource_from_dict("cache", resources.redis(port=6379))

# Cloud Supabase database
supabase = resource_from_dict("db", resources.supabase_project(...))

# Both managed with same interface!
```

### 6. Services with Dependencies
```python
from kinfra import ServiceOrchestrator, OrchestratorConfig

orchestrator = ServiceOrchestrator(
    OrchestratorConfig(project_name="myapp"),
    KInfra()
)

# Add service with dependencies
orchestrator.add_service(api_service, depends_on=["postgres", "redis"])
orchestrator.add_service(frontend_service, depends_on=["api"])

# Auto-starts in correct order: postgres → redis → api → frontend
await orchestrator.start_all()
```

## Configuration Files

### YAML Configuration
```yaml
# myapp.yaml
resources:
  postgres:
    type: docker
    image: postgres:16
    ports:
      5432: 5432
    environment:
      POSTGRES_PASSWORD: secret

  supabase:
    type: supabase
    project_id: xxx
    access_token: ${SUPABASE_TOKEN}

  neon:
    type: neon
    project_id: yyy
    api_key: ${NEON_API_KEY}

services:
  api:
    command: [python, api.py]
    port: 8000
    depends_on: [postgres]
```

```python
# Load and use
import yaml
with open("myapp.yaml") as f:
    config = yaml.safe_load(f)

for name, resource_config in config["resources"].items():
    resource = resource_from_dict(name, resource_config)
    manager.resource_manager.add_resource_adapter(resource)
```

## Key Advantages

1. **Adapter Pattern** - Add new resource types without modifying core
2. **SDK + CLI Fallback** - Use native SDKs, gracefully fall back to CLI
3. **Config-Driven** - Define everything in YAML/JSON
4. **Auto-Management** - Start, stop, health, restart all automatic
5. **Mixed Environments** - Local Docker + Cloud APIs seamlessly
6. **Professional UX** - Error pages like Cloudflare
7. **Zero Boilerplate** - One line per resource

## Migration from Old Code

### Old Custom Infrastructure
```python
# 100+ lines of custom Docker/process management
def start_postgres():
    subprocess.run(["docker", "run", ...])  # Long command
    # Custom health check
    # Custom cleanup
```

### New KInfra
```python
# 1 line!
pg = resource_from_dict("db", resources.postgres(port=5432))
```

**Result:** 95%+ code reduction in application infrastructure code!

## Complete Examples

See:
- `examples/easy_resource_usage.py` - Basic patterns
- `examples/cloud_resources.py` - Cloud/API resources
- `examples/resource_management.py` - Advanced usage
- `services/byteport.py` - Real-world service definitions
- `RESOURCE_MANAGEMENT.md` - Detailed guide
- `API_RESOURCES.md` - Cloud resources guide
- `RESOURCE_TYPES.md` - All supported types

## Installation

```bash
# Core (no external dependencies)
pip install kinfra

# With cloud providers
pip install kinfra[supabase,vercel,neon]

# Full (all optional dependencies)
pip install kinfra[full]
```

## License

MIT
