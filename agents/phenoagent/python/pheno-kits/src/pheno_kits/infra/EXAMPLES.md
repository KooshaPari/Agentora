# Infra Kit Usage Examples

## Basic Port Allocation

### Simple Port Allocation
```python
from pheno.kits.infra import KInfra

kinfra = KInfra()

# Allocate port
port = kinfra.allocate_port(
    service_name="my-api",
    preferred_port=8000
)

print(f"Allocated port: {port}")

# Check if port is free
if kinfra.is_port_free(8001):
    print("Port 8001 is available")

# Release port when done
kinfra.release_port(service_name="my-api")
```

### Port Registry
```python
from pheno.kits.infra import PortRegistry, ServiceInfo

registry = PortRegistry()

# Register service
registry.register(
    ServiceInfo(
        name="api-server",
        port=8000,
        pid=12345,
        started_at="2025-10-16T10:00:00"
    )
)

# Get service info
service = registry.get_service("api-server")
print(f"API running on port {service.port}")

# List all services
for service in registry.list_services():
    print(f"{service.name}: {service.port}")

# Deregister service
registry.deregister("api-server")
```

### Smart Port Allocator
```python
from pheno.kits.infra import SmartPortAllocator

allocator = SmartPortAllocator(
    port_range=(8000, 9000),
    persistence_path="~/.kinfra/ports"
)

# Allocate with conflict resolution
port = allocator.allocate(
    service_name="my-service",
    preferred_port=8000
)

# Port is persisted across restarts
# Next run will try to use same port
```

## Tunnel Management

### Create Tunnel
```python
from pheno.kits.infra import TunnelManager

tunnel_mgr = TunnelManager()

# Create cloudflared tunnel
tunnel = await tunnel_mgr.create_tunnel(
    port=8000,
    tunnel_type="cloudflared",
    subdomain="my-api"
)

print(f"Tunnel URL: {tunnel.public_url}")
print(f"Status: {tunnel.status}")

# Get tunnel info
info = tunnel_mgr.get_tunnel("my-api")

# Stop tunnel
await tunnel_mgr.stop_tunnel("my-api")
```

### Tunnel Health Monitoring
```python
from pheno.kits.infra import TunnelManager, check_tunnel_health

tunnel_mgr = TunnelManager()

# Create tunnel
tunnel = await tunnel_mgr.create_tunnel(
    port=8000,
    tunnel_type="cloudflared"
)

# Monitor health
health = await check_tunnel_health(
    url=tunnel.public_url,
    timeout=5
)

if health.healthy:
    print("Tunnel is healthy")
else:
    print(f"Tunnel unhealthy: {health.error}")
    # Restart tunnel
    await tunnel_mgr.restart_tunnel(tunnel.name)
```

### Multiple Tunnels
```python
from pheno.kits.infra import TunnelManager

tunnel_mgr = TunnelManager()

# API tunnel
api_tunnel = await tunnel_mgr.create_tunnel(
    port=8000,
    tunnel_type="cloudflared",
    subdomain="api"
)

# Webhook tunnel
webhook_tunnel = await tunnel_mgr.create_tunnel(
    port=8001,
    tunnel_type="ngrok",
    subdomain="webhooks"
)

# List all tunnels
for tunnel in tunnel_mgr.list_tunnels():
    print(f"{tunnel.name}: {tunnel.public_url}")
```

## Service Orchestration

### Service Manager
```python
from pheno.kits.infra import ServiceManager, ServiceConfig

manager = ServiceManager()

# Define service
config = ServiceConfig(
    name="api-server",
    command=["python", "app.py"],
    port=8000,
    env_vars={
        "DATABASE_URL": "postgresql://...",
        "PORT": "8000"
    },
    health_check={
        "type": "http",
        "path": "/health",
        "interval": 5
    }
)

# Start service
await manager.start_service(config)

# Check status
status = manager.get_status("api-server")
print(f"Status: {status}")

# Stop service
await manager.stop_service("api-server")
```

### Service Orchestrator
```python
from pheno.kits.infra import ServiceOrchestrator, OrchestratorConfig, KInfra

orchestrator = ServiceOrchestrator(
    config=OrchestratorConfig(
        project_name="my-project",
        port_range=(8000, 9000)
    ),
    infra=KInfra()
)

# Register services
orchestrator.register_service(
    name="database",
    command=["docker", "run", "-p", "5432:5432", "postgres"],
    dependencies=[]
)

orchestrator.register_service(
    name="api",
    command=["python", "api.py"],
    dependencies=["database"]
)

orchestrator.register_service(
    name="worker",
    command=["python", "worker.py"],
    dependencies=["database", "api"]
)

# Start all services in dependency order
await orchestrator.start_all()

# Stop all services
await orchestrator.stop_all()
```

## Resource Management

### Resource Adapters
```python
from pheno.kits.infra import ResourceManager
from pheno.kits.infra.adapters import DatabaseAdapter, CacheAdapter

resource_mgr = ResourceManager()

# Register database resource
db_adapter = DatabaseAdapter(
    host="localhost",
    port=5432,
    name="postgres"
)
resource_mgr.register_resource("database", db_adapter)

# Register cache resource
cache_adapter = CacheAdapter(
    host="localhost",
    port=6379,
    name="redis"
)
resource_mgr.register_resource("cache", cache_adapter)

# Start resources
await resource_mgr.start_resource("database")
await resource_mgr.start_resource("cache")

# Get resource status
status = resource_mgr.get_status("database")
print(f"Database status: {status}")

# Stop resources
await resource_mgr.stop_all()
```

### Custom Resource Adapter
```python
from pheno.kits.infra.adapters import ResourceAdapter

class QueueAdapter(ResourceAdapter):
    async def start(self):
        """Start queue service."""
        # Start RabbitMQ, SQS, etc.
        pass

    async def stop(self):
        """Stop queue service."""
        pass

    async def health_check(self) -> bool:
        """Check if queue is healthy."""
        # Check queue health
        return True

# Use custom adapter
queue = QueueAdapter(name="rabbitmq")
resource_mgr.register_resource("queue", queue)
```

## Proxy Server

### Smart Proxy
```python
from pheno.kits.infra import SmartProxyServer, UpstreamConfig

# Define upstreams
upstreams = [
    UpstreamConfig(
        name="primary",
        url="http://localhost:8000",
        weight=80
    ),
    UpstreamConfig(
        name="secondary",
        url="http://localhost:8001",
        weight=20
    )
]

# Create proxy
proxy = SmartProxyServer(
    port=80,
    upstreams=upstreams,
    health_check_interval=5
)

# Start proxy
await proxy.start()

# Proxy automatically:
# - Load balances across upstreams
# - Monitors upstream health
# - Fails over to healthy upstreams
# - Retries failed requests

# Stop proxy
await proxy.stop()
```

### Run Smart Proxy
```python
from pheno.kits.infra import run_smart_proxy

# Quick start proxy
await run_smart_proxy(
    port=80,
    upstreams=["http://localhost:8000", "http://localhost:8001"],
    health_check_path="/health"
)
```

## Fallback Server

### Start Fallback Server
```python
from pheno.kits.infra import FallbackServer

fallback = FallbackServer(
    port=8000,
    message="Service temporarily unavailable",
    status_code=503
)

# Start fallback server
await fallback.start()

# Useful during:
# - Deployments
# - Maintenance windows
# - Service failures

# Stop fallback
await fallback.stop()
```

### Custom Fallback Pages
```python
from pheno.kits.infra import FallbackServer

fallback = FallbackServer(
    port=8000,
    html_template="""
    <!DOCTYPE html>
    <html>
    <head><title>Maintenance</title></head>
    <body>
        <h1>We'll be back soon!</h1>
        <p>Scheduled maintenance in progress.</p>
    </body>
    </html>
    """
)

await fallback.start()
```

## Health Checks

### HTTP Health Check
```python
from pheno.kits.infra import check_http_health

health = await check_http_health(
    url="http://localhost:8000/health",
    expected_status=200,
    timeout=5
)

if health.healthy:
    print("Service is healthy")
```

### TCP Health Check
```python
from pheno.kits.infra import check_tcp_health

health = await check_tcp_health(
    host="localhost",
    port=5432,
    timeout=3
)

if health.healthy:
    print("Database is reachable")
```

## Process Management

### Process Utilities
```python
from pheno.kits.infra import (
    is_port_free,
    get_port_occupant,
    kill_processes_on_port,
    terminate_process
)

# Check if port is free
if is_port_free(8000):
    print("Port 8000 is available")

# Find what's using a port
occupant = get_port_occupant(8000)
if occupant:
    print(f"Port 8000 used by PID {occupant['pid']}: {occupant['name']}")

# Kill processes on port
killed = kill_processes_on_port(8000)
print(f"Killed {killed} processes")

# Terminate specific process
terminate_process(12345)
```

### Cleanup Orphaned Processes
```python
from pheno.kits.infra import cleanup_orphaned_processes

# Clean up processes that are no longer tracked
cleanup_orphaned_processes(
    project_name="my-project",
    max_age_hours=24
)
```

## DNS Utilities

### DNS-Safe Slugs
```python
from pheno.kits.infra import dns_safe_slug

# Convert to DNS-safe format
slug = dns_safe_slug("My API Service!")
print(slug)  # "my-api-service"

# Use for subdomains
subdomain = dns_safe_slug("User Auth Service")
url = f"https://{subdomain}.example.com"
```

## Complete Infrastructure Setup

```python
from pheno.kits.infra import (
    KInfra,
    ServiceOrchestrator,
    OrchestratorConfig,
    TunnelManager,
    SmartProxyServer,
    UpstreamConfig
)

async def setup_infrastructure():
    # 1. Initialize core infrastructure
    kinfra = KInfra()

    # 2. Setup orchestrator
    orchestrator = ServiceOrchestrator(
        config=OrchestratorConfig(
            project_name="my-app",
            port_range=(8000, 9000)
        ),
        infra=kinfra
    )

    # 3. Register services
    orchestrator.register_service(
        name="database",
        command=["docker", "run", "-p", "5432:5432", "postgres"],
        dependencies=[]
    )

    orchestrator.register_service(
        name="api",
        command=["python", "api.py"],
        dependencies=["database"]
    )

    # 4. Start services
    await orchestrator.start_all()

    # 5. Get allocated ports
    api_port = kinfra.get_service_port("api")

    # 6. Create tunnel for API
    tunnel_mgr = TunnelManager()
    tunnel = await tunnel_mgr.create_tunnel(
        port=api_port,
        tunnel_type="cloudflared",
        subdomain="api"
    )

    print(f"API accessible at: {tunnel.public_url}")

    # 7. Setup proxy (optional)
    proxy = SmartProxyServer(
        port=80,
        upstreams=[
            UpstreamConfig(
                name="api",
                url=f"http://localhost:{api_port}",
                weight=100
            )
        ]
    )
    await proxy.start()

    return {
        "orchestrator": orchestrator,
        "tunnel": tunnel,
        "proxy": proxy
    }

# Run setup
infrastructure = await setup_infrastructure()

# Cleanup on shutdown
await infrastructure["orchestrator"].stop_all()
await infrastructure["proxy"].stop()
```

## Development vs Production

### Development Setup
```python
from pheno.kits.infra import KInfra, ServiceManager

async def setup_dev():
    kinfra = KInfra()

    # Use fixed ports for development
    api_port = 8000
    db_port = 5432

    # Start services without tunnels
    service_mgr = ServiceManager()
    await service_mgr.start_service(
        name="api",
        command=["python", "api.py"],
        port=api_port
    )

    print(f"Dev API: http://localhost:{api_port}")
```

### Production Setup
```python
from pheno.kits.infra import ServiceOrchestrator, TunnelManager

async def setup_prod():
    # Dynamic port allocation
    orchestrator = ServiceOrchestrator(...)
    await orchestrator.start_all()

    # Public tunnels
    tunnel_mgr = TunnelManager()
    tunnel = await tunnel_mgr.create_tunnel(...)

    # Health monitoring
    # Load balancing
    # Failover
    pass
```

## Middleware Helpers

```python
from pheno.kits.infra import middleware_helpers

# Use built-in middleware patterns
app.use(middleware_helpers.cors())
app.use(middleware_helpers.request_id())
app.use(middleware_helpers.logging())
app.use(middleware_helpers.error_handler())
```

## Best Practices

1. **Port Management**:
   - Always use port registry
   - Release ports when done
   - Use port ranges to avoid conflicts

2. **Tunnel Management**:
   - Monitor tunnel health
   - Handle tunnel failures gracefully
   - Use appropriate tunnel type for use case

3. **Service Orchestration**:
   - Define service dependencies
   - Implement health checks
   - Handle startup failures

4. **Resource Management**:
   - Use resource adapters for external services
   - Cleanup resources on shutdown
   - Monitor resource health

5. **Process Management**:
   - Track process PIDs
   - Cleanup orphaned processes
   - Handle process crashes

6. **Production Readiness**:
   - Use smart proxy for load balancing
   - Implement fallback servers
   - Setup monitoring and alerts
   - Use tunnels for secure access

7. **Development**:
   - Use fixed ports for local dev
   - Skip tunnels for local testing
   - Use lightweight health checks
