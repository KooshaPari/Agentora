# KInfra Resource Types - Complete Reference

All resource types manageable via KInfra with the same unified interface.

## Architecture

```
ResourceManager
    ↓
ResourceAdapter (ABC)
    ├── DockerAdapter      → Docker containers
    ├── SystemDaemonAdapter → systemd/launchd services
    ├── CommandAdapter     → CLI tools
    └── APIAdapter         → HTTP/REST APIs
```

**Everything extends `ResourceAdapter`** → Same interface for all resource types!

## Complete Resource Type Matrix

| Resource Type | Adapter | Template Function | Use Case |
|---------------|---------|-------------------|----------|
| **Local Infrastructure** |
| PostgreSQL (Docker) | `DockerAdapter` | `resources.postgres()` | Local database |
| NATS (Docker) | `DockerAdapter` | `resources.nats()` | Local message queue |
| Redis (Docker) | `DockerAdapter` | `resources.redis()` | Local cache |
| MongoDB (Docker) | `DockerAdapter` | `resources.mongodb()` | Local NoSQL |
| MySQL (Docker) | `DockerAdapter` | `resources.mysql()` | Local database |
| Custom Docker | `DockerAdapter` | `resources.custom_docker()` | Any container |
| **System Services** |
| nginx (systemd) | `SystemDaemonAdapter` | `resources.systemd_service()` | System daemon |
| PostgreSQL (system) | `SystemDaemonAdapter` | `resources.systemd_service()` | System-installed DB |
| **CLI Tools** |
| cloudflared | `CommandAdapter` | `resources.custom_command()` | Tunnel daemon |
| kubectl scale | `CommandAdapter` | `resources.kubernetes_deployment()` | K8s scaling |
| Custom script | `CommandAdapter` | `resources.custom_command()` | Any CLI tool |
| **Cloud Services** |
| Supabase | `APIAdapter` | `resources.supabase_project()` | Cloud Postgres |
| Render.com | `APIAdapter` | `resources.render_service()` | Cloud hosting |
| Vercel | `APIAdapter` | `resources.vercel_deployment()` | Cloud deployment |
| Railway | `APIAdapter` | `resources.railway_service()` | Cloud hosting |
| AWS RDS | `APIAdapter` | `resources.aws_rds_instance()` | Cloud database |
| Custom API | `APIAdapter` | `resources.custom_api()` | Any HTTP API |

## Usage Patterns

### Pattern 1: Template (Easiest)
```python
# Use pre-made template
pg = resource_from_dict("db", resources.postgres(port=5432, password="secret"))
```

### Pattern 2: Dict Config (YAML-friendly)
```python
# Define as dictionary
config = {
    "type": "docker",
    "image": "postgres:16",
    "ports": {5432: 5432},
    "environment": {"POSTGRES_PASSWORD": "secret"}
}
resource = resource_from_dict("db", config)
```

### Pattern 3: Custom Adapter (Maximum Control)
```python
# Extend ResourceAdapter for custom behavior
class MyAdapter(ResourceAdapter):
    async def start(self): ...
    async def stop(self): ...
    async def is_running(self): ...
    async def check_health(self): ...
```

## Complete Examples

### Example 1: Local Development
```python
# All local Docker resources
manager.resource_manager.add_resource_adapter(
    resource_from_dict("postgres", resources.postgres(port=5432))
)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("redis", resources.redis(port=6379))
)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("nats", resources.nats(port=4222, enable_jetstream=True))
)
```

### Example 2: Cloud Development
```python
# All cloud resources (no Docker needed!)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("db", resources.supabase_project(
        project_id="dev-db",
        access_token=os.getenv("SUPABASE_TOKEN")
    ))
)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("backend", resources.render_service(
        service_id="srv-backend",
        api_key=os.getenv("RENDER_KEY")
    ))
)
```

### Example 3: Hybrid (Local + Cloud)
```python
# Mix and match!
resources_config = {
    # Local for development speed
    "redis": resources.redis(port=6379),
    "nats": resources.nats(port=4222),

    # Cloud for data persistence
    "supabase": resources.supabase_project(
        project_id="prod-db",
        access_token=os.getenv("SUPABASE_TOKEN")
    ),

    # Cloud for workers
    "render-worker": resources.render_service(
        service_id="srv-worker",
        api_key=os.getenv("RENDER_KEY")
    )
}

# Add all with same interface
for name, config in resources_config.items():
    resource = resource_from_dict(name, config)
    manager.resource_manager.add_resource_adapter(resource)
```

### Example 4: YAML Configuration
```yaml
# resources.yaml
resources:
  # Docker
  postgres:
    type: docker
    image: postgres:16
    ports:
      5432: 5432
    environment:
      POSTGRES_PASSWORD: secret
    health_check:
      type: tcp
      port: 5432

  # API
  supabase:
    type: api
    api_base_url: https://api.supabase.com/v1/projects/my-proj
    auth:
      type: bearer
      token: ${SUPABASE_TOKEN}
    start_endpoint: /restore
    stop_endpoint: /pause
    health_endpoint: /health

  # CLI
  k8s_deployment:
    type: command
    start_command: [kubectl, scale, deployment, app, --replicas=1]
    stop_command: [kubectl, scale, deployment, app, --replicas=0]
```

```python
# Load and use
import yaml
with open("resources.yaml") as f:
    config = yaml.safe_load(f)

for name, resource_config in config["resources"].items():
    resource = resource_from_dict(name, resource_config)
    manager.resource_manager.add_resource_adapter(resource)
```

## Key Advantages

### 1. Unified Interface
```python
# Same code for local and cloud!
for resource in [local_postgres, cloud_supabase, k8s_deployment]:
    await resource.start()      # Works for all
    await resource.check_health()  # Works for all
    await resource.stop()       # Works for all
```

### 2. Config-Driven
```python
# Load from JSON/YAML/TOML
config = load_config("resources.yaml")
resources = ResourceFactory.create_many(config)
```

### 3. Easy Extension
```python
# Add new cloud provider in minutes
def my_cloud_service(instance_id, api_key):
    return api_resource(
        api_base_url=f"https://api.mycloud.com/v1/instances/{instance_id}",
        auth_type="api_key",
        api_key=api_key,
        start_endpoint="/start",
        health_endpoint="/health"
    )
```

### 4. Cost Optimization
```python
# Automatically pause expensive cloud resources when not in use
# Resume them when services start
await manager.start_all()  # Resumes cloud DBs
# ... do work ...
await manager.stop_all()   # Pauses cloud DBs → save $$
```

## zen-mcp-server Complete Example

```python
from kinfra import ServiceManager, ServiceConfig, KInfra
from kinfra.templates import resources
from kinfra.adapters import resource_from_dict

manager = ServiceManager(KInfra(domain="zen.kooshapari.com"))

# Local NATS for real-time messaging
manager.resource_manager.add_resource_adapter(
    resource_from_dict("nats", resources.nats(
        port=4222,
        enable_jetstream=True,
        data_dir=Path.home() / ".zen" / "nats"
    ))
)

# Cloud Supabase for PostgreSQL (pause when not in use!)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("supabase", resources.supabase_project(
        project_id="zen-db",
        access_token=os.getenv("SUPABASE_TOKEN")
    ))
)

# zen-mcp service
manager.add_service(ServiceConfig(
    name="zen-mcp",
    command=["python", "server.py"],
    preferred_port=50002,
    enable_tunnel=True,
    enable_fallback=True,
    env={
        "NATS_URL": "nats://localhost:4222",
        "DATABASE_URL": "postgresql://..."  # From Supabase
    }
))

# Everything auto-starts in correct order!
# Local resources start instantly, cloud resources resume, then service starts
await manager.start_all()
await manager.monitor()

# On stop, cloud resources auto-pause → $$$$ saved!
```

## Summary

**Before KInfra:**
- Custom Docker code for each project
- Custom API client code for each service
- Manual health checks
- Manual cleanup
- Hard to mix local + cloud

**After KInfra:**
- One line per resource (any type!)
- Automatic health monitoring
- Automatic cleanup
- Mix local + cloud seamlessly
- Load from YAML/JSON
