# deploy-kit

**Universal deployment toolkit for modern platforms, cloud infrastructure, and pheno-sdk vendoring.**

## Features

### 🚀 Deployment Abstractions
- **Local Process Management**: Run and monitor local services
- **NVMS Format**: Universal deployment configuration
- **Platform Clients**: Vercel, Fly.io, AWS, GCP, Azure support
- **Cloud Orchestration**: Docker, Kubernetes integration

### 📦 Pheno-SDK Vendoring (NEW)
- **Auto-Detection**: Automatically detect which pheno-sdk packages your project uses
- **CLI & API**: Use via `pheno-vendor` command or Python API
- **Multi-Platform**: Generate configs for Vercel, Docker, Lambda, Railway, etc.
- **Validation**: Built-in validation and import testing
- **Cross-Platform**: Python-based (works on Windows, macOS, Linux)

### 🔧 Build Tools
- **Platform Detection**: Auto-detect deployment platform
- **Hook Generation**: Generate platform-specific build hooks
- **Configuration**: Auto-generate deployment configs
- **Validation**: Deployment readiness checks

## Installation

```bash
# Install from source
cd ~/temp-PRODVERCEL/485/kush/pheno-sdk/deploy-kit
pip install -e .

# Or install with extras
pip install -e ".[full]"  # All platform support
pip install -e ".[vercel,docker]"  # Specific platforms
```

## Quick Start

### Pheno-SDK Vendoring

Replace custom vendoring scripts with the unified toolkit:

```bash
# In your project directory
cd /path/to/your/project

# Vendor packages (auto-detect)
pheno-vendor setup

# Output:
# ✓ Detected 8 used packages
# ✓ Vendored 8/8 packages
# ✓ Created requirements-prod.txt
# ✓ Created sitecustomize.py
# ✓ All packages validated!
```

What gets created:
```
your-project/
├── pheno_vendor/           # Vendored packages
├── requirements-prod.txt   # Production requirements
└── sitecustomize.py        # Python path setup
```

### Deployment Configuration

```bash
# Generate platform-specific configs
pheno-vendor generate-hooks --platform vercel
pheno-vendor generate-hooks --platform docker --output build.sh
```

### Python API

```python
from deploy_kit import PhenoVendor

# Vendor packages
vendor = PhenoVendor(project_root=".")
vendor.vendor_all(auto_detect=True, validate=True)

# Generate configs
from deploy_kit import DeployConfig
config = DeployConfig(project_root=".")
config.save_configs()  # Creates vercel.json, Dockerfile, etc.
```

## CLI Commands

### `pheno-vendor setup`
Vendor pheno-sdk packages for production deployment.

```bash
pheno-vendor setup                    # Auto-detect packages
pheno-vendor setup --no-auto-detect   # Vendor all packages
pheno-vendor setup --no-validate      # Skip validation
```

### `pheno-vendor validate`
Validate vendored packages.

```bash
pheno-vendor validate                 # Basic validation
pheno-vendor validate --test-imports  # Include import tests
```

### `pheno-vendor info`
Show project and package information.

```bash
pheno-vendor info
```

### `pheno-vendor clean`
Remove vendored packages directory.

```bash
pheno-vendor clean
```

### `pheno-vendor generate-hooks`
Generate platform-specific build hooks.

```bash
pheno-vendor generate-hooks --platform vercel
pheno-vendor generate-hooks --platform docker --output build.sh
```

## Platform Support

### Vercel
```json
// Auto-generated vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "server.py",
      "use": "@vercel/python"
    }
  ],
  "env": {
    "PYTHONPATH": "pheno_vendor"
  }
}
```

### Docker
```dockerfile
# Auto-generated Dockerfile
FROM python:3.10-slim
WORKDIR /app

RUN pip install pheno-vendor
COPY . /app/
RUN pheno-vendor setup --no-validate
RUN pip install -r requirements-prod.txt

ENV PYTHONPATH=/app/pheno_vendor
CMD ["python", "server.py"]
```

### AWS Lambda
```bash
# Auto-generated build script
pip install pheno-vendor -t package/
pheno-vendor setup --project-root package/
zip -r deployment.zip package/
```

## Migration from Custom Scripts

### Before (Shell Script)
```bash
./scripts/vendor-pheno-sdk.sh --clean --verify
```

### After (deploy-kit)
```bash
pheno-vendor setup
```

**Benefits:**
- ✓ Cross-platform (Python vs Bash)
- ✓ Auto-detection of packages
- ✓ Built-in validation
- ✓ Platform-specific configs
- ✓ Programmatic API

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed migration steps.

## Documentation

### Guides
- **[Vendoring Guide](VENDORING_GUIDE.md)**: Complete guide to pheno-sdk vendoring
- **[Migration Guide](MIGRATION_GUIDE.md)**: Migrate from custom scripts
- **[Examples](examples/)**: Code examples for common use cases

### Examples
- [vendor_example.py](examples/vendor_example.py): Basic vendoring
- [config_example.py](examples/config_example.py): Configuration generation
- [platform_detection_example.py](examples/platform_detection_example.py): Platform detection
- [complete_workflow_example.py](examples/complete_workflow_example.py): Full workflow

## API Reference

### PhenoVendor

Main class for vendoring pheno-sdk packages.

```python
from deploy_kit import PhenoVendor

vendor = PhenoVendor(
    project_root=Path.cwd(),
    pheno_sdk_root=None,  # Auto-detect
    vendor_dir="pheno_vendor"
)

# Detect used packages
used = vendor.detect_used_packages()

# Vendor packages
results = vendor.vendor_packages(
    packages=None,  # None = auto-detect
    auto_detect=True,
    clean=True
)

# Generate production files
vendor.generate_prod_requirements()
vendor.create_sitecustomize()
vendor.generate_manifest()

# Validate
validation = vendor.validate_vendored()
import_tests = vendor.test_imports()

# All-in-one
vendor.vendor_all(auto_detect=True, validate=True)
```

### DeployConfig

Configuration management for deployment platforms.

```python
from deploy_kit import DeployConfig

config = DeployConfig(project_root=".")

# Auto-detected properties
config.python_version  # "3.10"
config.entry_point     # "server.py"
config.pheno_packages  # Set of pheno-sdk packages
config.external_deps   # Set of external dependencies

# Generate platform configs
vercel_config = config.to_vercel_config()
dockerfile = config.to_docker_config()
lambda_config = config.to_lambda_config()
railway_config = config.to_railway_config()

# Save all configs
config.save_configs()  # Creates vercel.json, Dockerfile, etc.
```

### PlatformDetector

Auto-detect deployment platform.

```python
from deploy_kit import PlatformDetector

detector = PlatformDetector(project_root=".")

# Detect primary platform
platform = detector.detect()  # "vercel", "docker", etc.

# Get all detected platforms
platforms = detector.detect_all()
for p in platforms:
    print(f"{p.name}: {p.confidence:.0%}")
```

### BuildHookGenerator

Generate platform-specific build hooks.

```python
from deploy_kit import BuildHookGenerator

generator = BuildHookGenerator(project_root=".")

# Generate hooks for platform
hooks = generator.generate("vercel")
print(hooks)

# Save to file
(Path.cwd() / "build.sh").write_text(hooks)
```

### DeploymentValidator

Validate deployment readiness.

```python
from deploy_kit import DeploymentValidator

validator = DeploymentValidator(project_root=".")

# Validate configuration
success, errors = validator.validate()
if not success:
    for error in errors:
        print(f"Error: {error}")

# Test imports
success, errors = validator.check_imports()
```

## Use Cases

### 1. Production Deployment (Vercel)

```bash
# Setup
pheno-vendor setup

# Deploy
vercel deploy
```

### 2. Docker Containerization

```bash
# Generate Dockerfile
python -c "from deploy_kit import DeployConfig; \
           print(DeployConfig('.').to_docker_config())" > Dockerfile

# Build
docker build -t myapp .
docker run myapp
```

### 3. AWS Lambda Package

```bash
# Vendor and package
pheno-vendor setup
pip install -r requirements-prod.txt -t package/
cd package && zip -r ../deployment.zip .
```

### 4. CI/CD Integration

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
      - name: Vendor packages
        run: |
          pip install pheno-vendor
          pheno-vendor setup
      - name: Deploy
        run: vercel deploy --prod
```

### 5. Multi-Platform Build

```python
from deploy_kit import DeployConfig

config = DeployConfig(".")

# Generate for all platforms
config.save_configs()  # Creates vercel.json, Dockerfile, railway.json, etc.

# Or specific platform
vercel_json = config.to_vercel_config()
with open("vercel.json", "w") as f:
    json.dump(vercel_json, f, indent=2)
```

## Architecture

```
deploy-kit/
├── deploy_kit/
│   ├── vendor.py          # PhenoVendor - Vendoring engine
│   ├── config.py          # DeployConfig - Configuration management
│   ├── utils.py           # Platform detection, hooks, validation
│   ├── cli.py             # CLI interface (pheno-vendor)
│   ├── local/             # Local process management
│   ├── nvms/              # NVMS format support
│   ├── platforms/         # Platform clients (Vercel, Fly, etc.)
│   └── cloud/             # Cloud provider interfaces
├── examples/              # Usage examples
├── VENDORING_GUIDE.md    # Complete vendoring guide
├── MIGRATION_GUIDE.md    # Migration from custom scripts
└── README.md             # This file
```

## Requirements

- Python >= 3.10
- Dependencies:
  - `httpx` - HTTP client
  - `pydantic` - Data validation
  - `pyyaml` - YAML support
  - `rich` - Terminal UI
  - `click` - CLI framework

Optional dependencies:
- `boto3` - AWS support
- `docker` - Docker integration
- `kubernetes` - K8s support
- Platform-specific SDKs (see [pyproject.toml](pyproject.toml))

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/

# Format code
black deploy_kit/
ruff check deploy_kit/
```

## Troubleshooting

### Package Not Found
```bash
# Specify pheno-sdk location
export PHENO_SDK_ROOT=/path/to/pheno-sdk
pheno-vendor setup
```

### Import Errors
```bash
# Validate vendored packages
pheno-vendor validate --test-imports

# Check Python path
export PYTHONPATH=pheno_vendor
```

### Build Issues
```bash
# Skip validation for faster builds
pheno-vendor setup --no-validate

# Clean and retry
pheno-vendor clean
pheno-vendor setup
```

See [VENDORING_GUIDE.md](VENDORING_GUIDE.md#troubleshooting) for more solutions.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - See [LICENSE](LICENSE) for details

## Support

- **Documentation**: [VENDORING_GUIDE.md](VENDORING_GUIDE.md), [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
- **Examples**: [examples/](examples/)
- **Issues**: GitHub Issues
- **Help**: `pheno-vendor --help`

## Roadmap

- [ ] PyPI package publication
- [ ] More platform integrations (Cloudflare Workers, Netlify, etc.)
- [ ] Dependency optimization (tree-shaking)
- [ ] Cache optimization for CI/CD
- [ ] GUI for configuration
- [ ] Integration with deploy-kit's other features (NVMS, etc.)

---

**Made with ❤️ by the Pheno-SDK team**
