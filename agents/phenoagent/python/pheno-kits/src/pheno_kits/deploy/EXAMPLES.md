# Deploy Kit Usage Examples

## Vercel Deployment

### Basic Deployment
```python
from pheno.kits.deploy import VercelClient

vercel = VercelClient(token="your-vercel-token")

# Deploy project
deployment = await vercel.deploy(
    project="my-app",
    path="./dist",
    production=True
)

print(f"Deployed to: {deployment.url}")
print(f"Status: {deployment.state}")
```

### With Environment Variables
```python
deployment = await vercel.deploy(
    project="my-app",
    path="./dist",
    env_vars={
        "DATABASE_URL": "postgresql://...",
        "API_KEY": "secret-key",
        "NODE_ENV": "production"
    }
)
```

### Deploy from Git
```python
deployment = await vercel.deploy(
    project="my-app",
    git_url="https://github.com/user/repo",
    branch="main",
    production=True
)
```

## Fly.io Deployment

### Deploy Container
```python
from pheno.kits.deploy import FlyClient

fly = FlyClient(token="your-fly-token")

# Deploy app
deployment = await fly.deploy(
    app_name="my-app",
    dockerfile_path="./Dockerfile",
    region="sea"  # Seattle
)

# Scale app
await fly.scale(
    app_name="my-app",
    instances=3
)
```

## Local Service Management

### Start Local Service
```python
from pheno.kits.deploy import (
    LocalServiceManager,
    LocalProcessConfig,
    ReadyProbe
)

# Configure service
config = LocalProcessConfig(
    name="api-server",
    command=["python", "app.py"],
    port=8000,
    env_vars={
        "DATABASE_URL": "sqlite:///local.db",
        "DEBUG": "true"
    },
    ready_probe=ReadyProbe(
        type="http",
        path="/health",
        timeout=30,
        interval=1
    )
)

# Start service
manager = LocalServiceManager(config)
await manager.start()

# Service is ready when probe succeeds
print(f"Service running on port {manager.port}")

# Stop service
await manager.stop()
```

### Multiple Services
```python
from pheno.kits.deploy import LocalServiceManager

services = []

# Start API
api_config = LocalProcessConfig(
    name="api",
    command=["python", "api.py"],
    port=8000,
    ready_probe=ReadyProbe(type="http", path="/health")
)
api = LocalServiceManager(api_config)
await api.start()
services.append(api)

# Start Worker
worker_config = LocalProcessConfig(
    name="worker",
    command=["python", "worker.py"],
    ready_probe=ReadyProbe(type="tcp", port=6379)
)
worker = LocalServiceManager(worker_config)
await worker.start()
services.append(worker)

# Stop all
for service in services:
    await service.stop()
```

## Health Checks

### HTTP Health Check
```python
from pheno.kits.deploy import HTTPHealthCheck

check = HTTPHealthCheck(
    url="http://localhost:8000/health",
    expected_status=200,
    timeout=5
)

result = await check.run()
if result.healthy:
    print("Service is healthy")
else:
    print(f"Service unhealthy: {result.error}")
```

### TCP Health Check
```python
from pheno.kits.deploy import TCPHealthCheck

check = TCPHealthCheck(
    host="localhost",
    port=5432,
    timeout=3
)

result = await check.run()
```

### Custom Health Check
```python
from pheno.kits.deploy import HealthCheck, HealthCheckResult

class RedisHealthCheck(HealthCheck):
    async def run(self) -> HealthCheckResult:
        try:
            import redis
            r = redis.Redis(host=self.host, port=self.port)
            r.ping()
            return HealthCheckResult(healthy=True)
        except Exception as e:
            return HealthCheckResult(
                healthy=False,
                error=str(e)
            )
```

## Deployment Hooks

### Pre-Deploy Hook
```python
from pheno.kits.deploy import PreDeployHook

class DatabaseMigrationHook(PreDeployHook):
    async def execute(self, context):
        print("Running database migrations...")
        # Run migrations
        await run_migrations()
        print("Migrations complete")
```

### Post-Deploy Hook
```python
from pheno.kits.deploy import PostDeployHook

class CacheClearHook(PostDeployHook):
    async def execute(self, context):
        print("Clearing cache...")
        await clear_cache()
        print("Cache cleared")
```

### Hook Registry
```python
from pheno.kits.deploy import HookRegistry

registry = HookRegistry()

# Register hooks
registry.register_pre_deploy(DatabaseMigrationHook())
registry.register_post_deploy(CacheClearHook())

# Run all pre-deploy hooks
await registry.run_pre_deploy_hooks(context)

# Deploy...

# Run all post-deploy hooks
await registry.run_post_deploy_hooks(context)
```

## Build Configuration

### Auto-detect Package Manager
```python
from pheno.kits.deploy import PackageDetector

detector = PackageDetector(project_path="./my-app")

# Detect package manager
pkg_manager = detector.detect()
print(f"Using: {pkg_manager}")  # npm, yarn, pnpm, etc.

# Get build command
build_cmd = detector.get_build_command()
print(f"Build: {build_cmd}")  # npm run build

# Get install command
install_cmd = detector.get_install_command()
print(f"Install: {install_cmd}")  # npm install
```

### Deployment Configuration
```python
from pheno.kits.deploy import DeployConfig

config = DeployConfig.from_file("./deploy.yaml")

# Or create programmatically
config = DeployConfig(
    name="my-app",
    build_command="npm run build",
    output_directory="dist",
    install_command="npm install",
    framework="nextjs",
    node_version="18"
)

# Save configuration
config.save("./deploy.yaml")
```

## Platform Detection

### Detect Current Platform
```python
from pheno.kits.deploy import PlatformDetector

detector = PlatformDetector()

# Detect platform
platform = detector.detect()
print(f"Running on: {platform.name}")  # vercel, fly, local, etc.

# Platform-specific info
if platform.is_vercel:
    print(f"Deployment URL: {platform.deployment_url}")
    print(f"Environment: {platform.environment}")
elif platform.is_local:
    print("Running locally")
```

### Platform-Specific Logic
```python
detector = PlatformDetector()

if detector.is_production():
    # Use production database
    db_url = os.getenv("PROD_DATABASE_URL")
else:
    # Use local database
    db_url = "sqlite:///local.db"
```

## Environment Management

### Environment Variables
```python
from pheno.kits.deploy import EnvironmentManager

env_mgr = EnvironmentManager()

# Set variables
env_mgr.set("DATABASE_URL", "postgresql://...")
env_mgr.set("API_KEY", "secret", encrypted=True)

# Get variables
db_url = env_mgr.get("DATABASE_URL")

# Load from file
env_mgr.load_from_file(".env")

# Export for deployment
env_dict = env_mgr.export()
```

## Package Vendoring

### Vendor Dependencies
```python
from pheno.kits.deploy import PhenoVendor, PackageInfo

vendor = PhenoVendor(
    source_dir="./src",
    vendor_dir="./vendor"
)

# Vendor specific packages
packages = [
    PackageInfo(name="pheno-sdk", version="0.1.0"),
    PackageInfo(name="custom-lib", path="./local-lib")
]

vendor.vendor_packages(packages)

# Generate vendor manifest
vendor.generate_manifest()
```

## Build Hook Generation

### Generate Vercel Build Hook
```python
from pheno.kits.deploy import BuildHookGenerator

generator = BuildHookGenerator()

# Generate hook
hook = generator.generate_vercel_hook(
    project_id="my-project",
    production=True
)

print(f"Build hook URL: {hook.url}")

# Trigger build via hook
import requests
requests.post(hook.url)
```

## Deployment Validation

### Validate Deployment
```python
from pheno.kits.deploy import DeploymentValidator

validator = DeploymentValidator()

# Validate deployment
result = await validator.validate(
    url="https://my-app.vercel.app",
    checks=[
        {"type": "http", "path": "/health", "expected_status": 200},
        {"type": "http", "path": "/api", "expected_status": 200},
        {"type": "ssl", "min_days_valid": 30}
    ]
)

if result.passed:
    print("Deployment validated successfully")
else:
    print(f"Validation failed: {result.errors}")
```

## NVMS (Node Version Manager Script)

### Parse NVMS File
```python
from pheno.kits.deploy import NVMSParser

parser = NVMSParser()

# Parse .nvmrc or package.json
version = parser.parse_file(".nvmrc")
print(f"Node version: {version}")

# Or parse from package.json
version = parser.parse_package_json("package.json")
```

## Complete Deployment Pipeline

```python
from pheno.kits.deploy import (
    VercelClient,
    PackageDetector,
    HookRegistry,
    DeploymentValidator
)

async def deploy_app():
    # 1. Detect configuration
    detector = PackageDetector("./my-app")
    pkg_manager = detector.detect()

    # 2. Run pre-deploy hooks
    hooks = HookRegistry()
    hooks.register_pre_deploy(DatabaseMigrationHook())
    await hooks.run_pre_deploy_hooks({})

    # 3. Deploy
    vercel = VercelClient(token=os.getenv("VERCEL_TOKEN"))
    deployment = await vercel.deploy(
        project="my-app",
        path="./my-app",
        production=True
    )

    # 4. Validate deployment
    validator = DeploymentValidator()
    result = await validator.validate(
        url=deployment.url,
        checks=[
            {"type": "http", "path": "/health"},
            {"type": "ssl"}
        ]
    )

    # 5. Run post-deploy hooks
    await hooks.run_post_deploy_hooks({"deployment": deployment})

    print(f"Deployment complete: {deployment.url}")

# Run
await deploy_app()
```

## Startup Management

### Manage Service Startup
```python
from pheno.kits.deploy import StartupManager, StartupConfig

startup = StartupManager(
    config=StartupConfig(
        services=[
            {"name": "database", "priority": 1},
            {"name": "cache", "priority": 2},
            {"name": "api", "priority": 3}
        ],
        timeout=60
    )
)

# Start all services in order
await startup.start_all()

# Or start specific service
await startup.start_service("api")
```

## Best Practices

1. **Use Health Checks**: Always validate service readiness
2. **Implement Hooks**: Automate pre/post deployment tasks
3. **Validate Deployments**: Confirm deployments are working
4. **Handle Errors Gracefully**: Wrap deploy calls in try/except
5. **Use Environment Management**: Centralize env var handling
6. **Auto-detect Configuration**: Use platform detection
7. **Version Lock Dependencies**: Use NVMS for Node version
8. **Local Testing First**: Test with LocalServiceManager before cloud
