# KInfra Cloud & API Resource Management

Manage remote/cloud resources via HTTP APIs using the same interface as local resources.

## Supported Resource Types

### Local Resources (Existing)
- ✅ Docker containers
- ✅ systemd/launchd services
- ✅ Command-line tools

### Cloud/API Resources (New)
- ✅ Supabase projects
- ✅ Render.com services
- ✅ Vercel deployments
- ✅ Railway services
- ✅ AWS RDS instances
- ✅ Kubernetes deployments
- ✅ Any HTTP API

## Quick Start

```python
from kinfra import ServiceManager, KInfra
from kinfra.templates import resources
from kinfra.adapters import resource_from_dict

manager = ServiceManager(KInfra())

# Manage Supabase project via API
supabase = resource_from_dict("db", resources.supabase_project(
    project_id="your-project-id",
    access_token="sbp_..."
))

manager.resource_manager.add_resource_adapter(supabase)

# Auto-restores project before starting services
await manager.start_all()
```

## Cloud Resource Templates

### Supabase
```python
supabase = resources.supabase_project(
    project_id="abcdefghij",
    access_token=os.getenv("SUPABASE_TOKEN")
)
```

### Render.com
```python
render = resources.render_service(
    service_id="srv-123abc",
    api_key=os.getenv("RENDER_API_KEY")
)
```

### Vercel
```python
vercel = resources.vercel_deployment(
    deployment_id="dpl_123",
    team_id="team_456",
    access_token=os.getenv("VERCEL_TOKEN")
)
```

### Kubernetes
```python
k8s = resources.kubernetes_deployment(
    deployment_name="backend-api",
    namespace="production"
)
```

### Custom API
```python
custom = resources.custom_api(
    base_url="https://api.myservice.com",
    auth_token="Bearer xxx",
    start_endpoint="/v1/instances/start",
    stop_endpoint="/v1/instances/stop",
    health_endpoint="/v1/health"
)
```

## Mixed Local + Cloud

```python
from kinfra import ServiceManager, KInfra
from kinfra.templates import resources
from kinfra.adapters import resource_from_dict

manager = ServiceManager(KInfra())

# Local Docker resources
manager.resource_manager.add_resource_adapter(
    resource_from_dict("redis-cache", resources.redis(port=6379))
)

# Cloud database
manager.resource_manager.add_resource_adapter(
    resource_from_dict("supabase-db", resources.supabase_project(
        project_id="prod-db",
        access_token=os.getenv("SUPABASE_TOKEN")
    ))
)

# Cloud worker service
manager.resource_manager.add_resource_adapter(
    resource_from_dict("render-worker", resources.render_service(
        service_id="srv-worker",
        api_key=os.getenv("RENDER_KEY")
    ))
)

# Local API service
manager.add_service(ServiceConfig(
    name="api",
    command=["python", "api.py"],
    preferred_port=8000,
    env={
        "REDIS_URL": "redis://localhost:6379",
        "DATABASE_URL": "postgresql://...",  # From Supabase
    }
))

# Everything auto-starts in correct order!
await manager.start_all()
```

## Pure Dict Configuration (YAML/JSON friendly)

```python
import yaml

# Load from YAML
config = yaml.safe_load("""
resources:
  # Local Docker
  postgres:
    type: docker
    image: postgres:16
    ports:
      5432: 5432
    environment:
      POSTGRES_PASSWORD: secret

  # Cloud API
  supabase:
    type: api
    api_base_url: https://api.supabase.com/v1/projects/my-proj
    auth:
      type: bearer
      token: ${SUPABASE_TOKEN}
    start_endpoint: /restore
    stop_endpoint: /pause

  # Kubernetes
  k8s_backend:
    type: command
    start_command: [kubectl, scale, deployment, backend, --replicas=1]
    stop_command: [kubectl, scale, deployment, backend, --replicas=0]

  # Custom API
  my_service:
    type: api
    api_base_url: https://api.example.com
    auth:
      type: api_key
      api_key: ${API_KEY}
      header_name: X-API-Key
    start_endpoint: /v1/start
    health_endpoint: /v1/health
""")

# Create all resources from config
manager = ServiceManager(KInfra())
for name, resource_config in config["resources"].items():
    resource = resource_from_dict(name, resource_config)
    manager.resource_manager.add_resource_adapter(resource)

await manager.start_all()
```

## Authentication Support

### Bearer Token
```python
config = {
    "type": "api",
    "api_base_url": "https://api.service.com",
    "auth": {
        "type": "bearer",
        "token": "your-token-here"
    }
}
```

### API Key
```python
config = {
    "auth": {
        "type": "api_key",
        "api_key": "your-key",
        "header_name": "X-API-Key"  # Customizable
    }
}
```

### Basic Auth
```python
config = {
    "auth": {
        "type": "basic",
        "username": "user",
        "password": "pass"
    }
}
```

### Custom Headers
```python
config = {
    "auth": {
        "type": "custom",
        "headers": {
            "X-Custom-Auth": "value",
            "X-Another-Header": "value2"
        }
    }
}
```

## Real-World Use Cases

### 1. Development with Cloud DB
```python
# Use cloud Postgres for dev (pause when not in use to save money)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("dev-db", resources.supabase_project(
        project_id="dev-project",
        access_token=os.getenv("SUPABASE_TOKEN")
    ))
)
# Auto-restores when you start dev, pauses when you stop
```

### 2. Integration Testing with Real Services
```python
# Start staging deployments for integration tests
manager.resource_manager.add_resource_adapter(
    resource_from_dict("staging-api", resources.vercel_deployment(
        deployment_id="dpl_staging",
        access_token=os.getenv("VERCEL_TOKEN")
    ))
)
# Runs tests against real staging deployment
```

### 3. Multi-Region Deployments
```python
# Manage deployments across regions via API
for region in ["us-east-1", "eu-west-1", "ap-south-1"]:
    manager.resource_manager.add_resource_adapter(
        resource_from_dict(f"api-{region}", resources.custom_api(
            base_url=f"https://api.{region}.myservice.com",
            start_endpoint="/deploy",
            health_endpoint="/health"
        ))
    )
```

### 4. Hybrid Cloud Setup
```python
# Local dev resources
resources_config = {
    "redis": resources.redis(port=6379),
    "nats": resources.nats(port=4222),
}

# Production cloud resources
resources_config.update({
    "supabase": resources.supabase_project(...),
    "render-worker": resources.render_service(...),
    "k8s-api": resources.kubernetes_deployment(...)
})

# All managed uniformly!
for name, config in resources_config.items():
    manager.resource_manager.add_resource_adapter(
        resource_from_dict(name, config)
    )
```

## Key Benefits

✅ **Unified Interface** - Local Docker and Cloud API managed the same way
✅ **Automatic Lifecycle** - Start/stop/health monitoring automatic
✅ **Cost Optimization** - Pause cloud resources when not in use
✅ **Multi-Cloud** - Mix AWS, GCP, Vercel, Render, Supabase, etc.
✅ **YAML/JSON Config** - Define everything declaratively
✅ **Extensible** - Add any API-based resource easily

## Extending for New APIs

```python
from kinfra.adapters.api import APIAdapter

# Create adapter for your specific API
class MyServiceAdapter(APIAdapter):
    async def start(self) -> bool:
        # Custom start logic if needed
        return await super().start()

# Or just use dict config:
config = {
    "type": "api",
    "api_base_url": "https://api.myservice.com",
    "auth": {"type": "bearer", "token": "xxx"},
    "start_endpoint": "/custom/start",
    "health_endpoint": "/custom/health"
}

resource = resource_from_dict("myservice", config)
```

## Complete Example: zen-mcp-server with Cloud Resources

```python
# zen-mcp-server with local NATS + cloud Supabase
manager = ServiceManager(KInfra())

# Local NATS for real-time
manager.resource_manager.add_resource_adapter(
    resource_from_dict("nats", resources.nats(
        port=4222,
        enable_jetstream=True
    ))
)

# Cloud Supabase for data persistence
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
    env={
        "NATS_URL": "nats://localhost:4222",
        "DATABASE_URL": f"postgresql://..."  # From Supabase
    }
))

# Local + Cloud resources auto-managed!
await manager.start_all()
```
