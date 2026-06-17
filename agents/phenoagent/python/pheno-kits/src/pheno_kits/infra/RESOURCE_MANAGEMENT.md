# KInfra Resource Management

Automatic Docker container and system daemon management with health monitoring.

## Quick Start

```python
from kinfra import ServiceManager, KInfra
from kinfra.templates import resources
from kinfra.adapters import resource_from_dict

# Initialize
manager = ServiceManager(KInfra())

# Add Postgres (one-liner!)
pg = resource_from_dict("db", resources.postgres(port=5432, password="secret"))
manager.resource_manager.add_resource_adapter(pg)

# Auto-starts before services
await manager.start_all()
```

## Architecture

### Adapter Pattern
- **ResourceAdapter** - Base interface for any resource type
- **DockerAdapter** - Manages Docker containers
- **SystemDaemonAdapter** - Manages systemd/launchd services
- **CommandAdapter** - Manages CLI/API-based resources

### Templates
Pre-configured templates in `kinfra.templates.resources`:
- `postgres()` - PostgreSQL
- `nats()` - NATS with optional JetStream
- `redis()` - Redis with persistence
- `mongodb()` - MongoDB
- `mysql()` - MySQL
- `custom_docker()` - Generic Docker container
- `systemd_service()` - Systemd service
- `custom_command()` - CLI-based resource

## Usage Patterns

### Pattern 1: Use Templates (Easiest)

```python
from kinfra.templates import resources
from kinfra.adapters import resource_from_dict

# PostgreSQL
pg = resource_from_dict("postgres", resources.postgres(
    port=5432,
    password="mypass",
    database="mydb",
    data_dir=Path.home() / ".myapp" / "pgdata"
))

# NATS with JetStream
nats = resource_from_dict("nats", resources.nats(
    port=4222,
    enable_jetstream=True,
    data_dir=Path.home() / ".myapp" / "nats"
))

# Add to manager
manager.resource_manager.add_resource_adapter(pg)
manager.resource_manager.add_resource_adapter(nats)
```

### Pattern 2: Dictionary Config (Flexible)

```python
# Define as dict
config = {
    "type": "docker",
    "image": "postgres:16",
    "ports": {5432: 5432},
    "environment": {"POSTGRES_PASSWORD": "secret"},
    "health_check": {"type": "tcp", "port": 5432}
}

# Create resource
pg = resource_from_dict("postgres", config)
```

### Pattern 3: Custom Docker Container

```python
# Elasticsearch example
es = resource_from_dict("elasticsearch", resources.custom_docker(
    image="elasticsearch:8.11.0",
    ports={9200: 9200, 9300: 9300},
    environment={
        "discovery.type": "single-node",
        "ES_JAVA_OPTS": "-Xms2g -Xmx2g"
    },
    health_check_port=9200,
    health_check_type="http",
    health_check_path="/_cluster/health"
))
```

### Pattern 4: Command-Based Resources

```python
# Manage any CLI tool
cloudflared = resource_from_dict("tunnel", resources.custom_command(
    start_command=["cloudflared", "tunnel", "run", "my-tunnel"],
    stop_command=["pkill", "cloudflared"],
    health_check_port=8080
))
```

### Pattern 5: Systemd Services

```python
# Manage nginx via systemd
nginx = resource_from_dict("nginx", resources.systemd_service(
    service_name="nginx",
    health_check_port=80
))
```

## Complete Example: Service with Dependencies

```python
import asyncio
from pathlib import Path
from kinfra import ServiceManager, ServiceConfig, KInfra
from kinfra.templates import resources
from kinfra.adapters import resource_from_dict

async def run_my_app():
    manager = ServiceManager(KInfra())

    # Add dependencies (auto-managed!)
    for name, config in {
        "postgres": resources.postgres(port=5432, password="secret"),
        "redis": resources.redis(port=6379),
        "nats": resources.nats(port=4222, enable_jetstream=True)
    }.items():
        resource = resource_from_dict(name, config)
        manager.resource_manager.add_resource_adapter(resource)

    # Add your service
    manager.add_service(ServiceConfig(
        name="my-api",
        command=["python", "api.py"],
        preferred_port=8000,
        env={
            "DATABASE_URL": "postgresql://postgres:secret@localhost:5432/postgres",
            "REDIS_URL": "redis://localhost:6379",
            "NATS_URL": "nats://localhost:4222"
        }
    ))

    # Resources auto-start, health-monitored, and auto-restart!
    await manager.start_all()
    await manager.monitor()

if __name__ == "__main__":
    asyncio.run(run_my_app())
```

## Advanced: Custom Adapter

```python
from kinfra.adapters.base import ResourceAdapter

class MyCustomAdapter(ResourceAdapter):
    """Custom adapter for your specific use case."""

    async def start(self) -> bool:
        # Your custom start logic
        return True

    async def stop(self) -> bool:
        # Your custom stop logic
        return True

    async def is_running(self) -> bool:
        # Your custom status check
        return True

    async def check_health(self) -> bool:
        # Your custom health check
        return True

# Use it
adapter = MyCustomAdapter("my-resource", {"custom": "config"})
manager.resource_manager.add_resource_adapter(adapter)
```

## Key Benefits

1. **No Hardcoded Implementations** - All resources use same adapter pattern
2. **Easy Extension** - Add new resource types without modifying KInfra
3. **Template Library** - Common resources have templates
4. **Dict-Based** - Can load configs from YAML/JSON/TOML
5. **Auto-Management** - Health monitoring, restart, cleanup all automatic
6. **Zero Boilerplate** - One-line resource creation

## Migration from Old Code

### Before (Custom Implementation):
```python
# Had to implement custom Docker logic
def start_postgres():
    subprocess.run(["docker", "run", "-d", "postgres:16", ...])  # 50 lines
    # Custom health check logic
    # Custom cleanup logic
```

### After (KInfra):
```python
# One line!
pg = resource_from_dict("db", resources.postgres(port=5432))
```

## Real-World Examples

### zen-mcp-server
```python
# Start Postgres + NATS for zen-mcp-server
manager.resource_manager.add_resource_adapter(
    resource_from_dict("postgres", resources.postgres(port=5432, database="zen"))
)
manager.resource_manager.add_resource_adapter(
    resource_from_dict("nats", resources.nats(port=4222, enable_jetstream=True))
)
```

### BytePort (Optional Metadata DB)
```python
# Only if --with-db flag is used
if args.with_db:
    pg = resource_from_dict("metadata", resources.postgres(
        port=5433,
        database="byteport_metadata"
    ))
    manager.resource_manager.add_resource_adapter(pg)
```

### atoms-mcp (Development Cache)
```python
# Redis for caching during development
redis = resource_from_dict("cache", resources.redis(port=6379))
manager.resource_manager.add_resource_adapter(redis)
```
