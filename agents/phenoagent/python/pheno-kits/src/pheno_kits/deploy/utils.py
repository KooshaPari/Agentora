"""Deployment utilities.

Platform detection, build hook generation, and deployment validation.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PlatformInfo:
    """
    Information about a deployment platform.
    """

    name: str
    detected: bool
    config_files: list[str]
    confidence: float  # 0.0 to 1.0


class PlatformDetector:
    """Auto-detect deployment platform from project structure.

    Checks for platform-specific files and configurations.
    """

    PLATFORM_SIGNATURES = {
        "vercel": {
            "files": ["vercel.json", ".vercel"],
            "required": 1,
        },
        "docker": {
            "files": ["Dockerfile", "docker-compose.yml", ".dockerignore"],
            "required": 1,
        },
        "lambda": {
            "files": ["serverless.yml", "template.yaml", ".aws-sam"],
            "required": 1,
        },
        "railway": {
            "files": ["railway.json", "railway.toml"],
            "required": 1,
        },
        "heroku": {
            "files": ["Procfile", "app.json"],
            "required": 1,
        },
        "fly": {
            "files": ["fly.toml"],
            "required": 1,
        },
        "cloudflare": {
            "files": ["wrangler.toml"],
            "required": 1,
        },
    }

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    def detect(self) -> str:
        """Detect the most likely deployment platform.

        Returns:
            Platform name (default: "docker")
        """
        platforms = self.detect_all()

        if not platforms:
            return "docker"  # Default fallback

        # Return platform with highest confidence
        return max(platforms, key=lambda p: p.confidence).name

    def detect_all(self) -> list[PlatformInfo]:
        """Detect all potential deployment platforms.

        Returns:
            List of PlatformInfo sorted by confidence
        """
        results = []

        for platform_name, signature in self.PLATFORM_SIGNATURES.items():
            found_files = []
            required = signature["required"]

            for file_pattern in signature["files"]:
                file_path = self.project_root / file_pattern

                if file_path.exists():
                    found_files.append(file_pattern)

            detected = len(found_files) >= required
            confidence = len(found_files) / len(signature["files"])

            results.append(
                PlatformInfo(
                    name=platform_name,
                    detected=detected,
                    config_files=found_files,
                    confidence=confidence,
                ),
            )

        # Sort by confidence (descending)
        results.sort(key=lambda p: p.confidence, reverse=True)

        return results


class BuildHookGenerator:
    """Generate platform-specific build hooks and configurations.

    Creates scripts and config files that use vendored pheno-sdk packages.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    def generate(self, platform: str) -> str:
        """Generate build hooks for specified platform.

        Args:
            platform: Target platform name

        Returns:
            Build script/config content
        """
        generators = {
            "vercel": self._generate_vercel,
            "docker": self._generate_docker,
            "lambda": self._generate_lambda,
            "railway": self._generate_railway,
            "heroku": self._generate_heroku,
            "fly": self._generate_fly,
            "cloudflare": self._generate_cloudflare,
        }

        generator = generators.get(platform.lower(), self._generate_generic)
        return generator()

    def _generate_vercel(self) -> str:
        """
        Generate Vercel build configuration.
        """
        return """#!/bin/bash
# Vercel Build Hook
# Runs during Vercel deployment

set -e

echo "Installing pheno-vendor..."
pip install pheno-vendor

echo "Vendoring pheno-sdk packages..."
pheno-vendor setup --no-validate

echo "Installing production dependencies..."
pip install -r requirements-prod.txt

echo "Vercel build complete!"
"""

    def _generate_docker(self) -> str:
        """
        Generate Dockerfile with vendored packages.
        """
        return """FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    build-essential \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Install pheno-vendor
RUN pip install --no-cache-dir pheno-vendor

# Copy project files
COPY . /app/

# Vendor pheno-sdk packages
RUN pheno-vendor setup --no-validate

# Install production dependencies
RUN pip install --no-cache-dir -r requirements-prod.txt

# Set Python path
ENV PYTHONPATH=/app/pheno_vendor

# Run application
CMD ["python", "server.py"]
"""

    def _generate_lambda(self) -> str:
        """
        Generate AWS Lambda build script.
        """
        return """#!/bin/bash
# AWS Lambda Build Hook
# Creates deployment package with vendored dependencies

set -e

BUILD_DIR="lambda_build"
PACKAGE_DIR="$BUILD_DIR/package"

echo "Creating Lambda build directory..."
mkdir -p "$PACKAGE_DIR"

echo "Installing pheno-vendor..."
pip install pheno-vendor -t "$PACKAGE_DIR"

echo "Vendoring pheno-sdk packages..."
cd "$PACKAGE_DIR"
pheno-vendor setup --project-root "$(pwd)/../.." --no-validate
cd ../..

echo "Installing production dependencies..."
pip install -r requirements-prod.txt -t "$PACKAGE_DIR"

echo "Copying application code..."
cp -r !(lambda_build) "$PACKAGE_DIR/"

echo "Creating deployment package..."
cd "$PACKAGE_DIR"
zip -r ../deployment.zip .
cd ../..

echo "Lambda package ready: $BUILD_DIR/deployment.zip"
"""

    def _generate_railway(self) -> str:
        """
        Generate Railway build configuration.
        """
        return """#!/bin/bash
# Railway Build Hook

set -e

echo "Installing pheno-vendor..."
pip install pheno-vendor

echo "Vendoring pheno-sdk packages..."
pheno-vendor setup --no-validate

echo "Installing production dependencies..."
pip install -r requirements-prod.txt

echo "Railway build complete!"
"""

    def _generate_heroku(self) -> str:
        """
        Generate Heroku build script.
        """
        return """#!/bin/bash
# Heroku Build Hook
# Runs during Heroku deployment

set -e

echo "Installing pheno-vendor..."
pip install pheno-vendor

echo "Vendoring pheno-sdk packages..."
pheno-vendor setup --no-validate

echo "Installing production dependencies..."
pip install -r requirements-prod.txt

echo "Heroku build complete!"
"""

    def _generate_fly(self) -> str:
        """
        Generate Fly.io Dockerfile.
        """
        return """FROM python:3.10-slim

WORKDIR /app

# Install pheno-vendor
RUN pip install pheno-vendor

# Copy project
COPY . /app/

# Vendor packages
RUN pheno-vendor setup --no-validate

# Install dependencies
RUN pip install -r requirements-prod.txt

# Set Python path
ENV PYTHONPATH=/app/pheno_vendor

CMD ["python", "server.py"]
"""

    def _generate_cloudflare(self) -> str:
        """
        Generate Cloudflare Workers build script.
        """
        return """#!/bin/bash
# Cloudflare Workers Build Hook

set -e

echo "Installing pheno-vendor..."
pip install pheno-vendor

echo "Vendoring pheno-sdk packages..."
pheno-vendor setup --no-validate

echo "Installing production dependencies..."
pip install -r requirements-prod.txt

echo "Building for Cloudflare Workers..."
# Additional Cloudflare-specific build steps here

echo "Cloudflare build complete!"
"""

    def _generate_generic(self) -> str:
        """
        Generate generic build script.
        """
        return """#!/bin/bash
# Generic Build Hook
# Universal deployment preparation

set -e

echo "Installing pheno-vendor..."
pip install pheno-vendor

echo "Vendoring pheno-sdk packages..."
pheno-vendor setup --no-validate

echo "Installing production dependencies..."
pip install -r requirements-prod.txt

echo "Build complete!"
"""


class DeploymentValidator:
    """Validate deployment configuration and vendored packages.

    Ensures the project is ready for production deployment.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    def validate(self) -> tuple[bool, list[str]]:
        """Validate deployment readiness.

        Returns:
            Tuple of (success, errors)
        """
        errors = []

        # Check vendor directory
        vendor_dir = self.project_root / "pheno_vendor"
        if not vendor_dir.exists():
            errors.append("Vendor directory not found. Run 'pheno-vendor setup'")

        # Check production requirements
        req_prod = self.project_root / "requirements-prod.txt"
        if not req_prod.exists():
            errors.append("requirements-prod.txt not found. Run 'pheno-vendor setup'")

        # Check sitecustomize
        sitecustomize = self.project_root / "sitecustomize.py"
        if not sitecustomize.exists():
            errors.append("sitecustomize.py not found. Run 'pheno-vendor setup'")

        # Check for editable installs in production requirements
        if req_prod.exists():
            content = req_prod.read_text()
            if "-e" in content and "pheno-sdk" in content:
                errors.append("production requirements contains editable installs")

        # Check Python path configuration
        if vendor_dir.exists():
            init_file = vendor_dir / "__init__.py"
            if not init_file.exists():
                errors.append("Vendor directory missing __init__.py")

        success = len(errors) == 0
        return success, errors

    def check_imports(self) -> tuple[bool, list[str]]:
        """Test that vendored packages can be imported.

        Returns:
            Tuple of (success, errors)
        """
        errors = []

        try:
            # Run Python import test
            test_script = """
import sys
from pathlib import Path

vendor_path = Path.cwd() / "pheno_vendor"
sys.path.insert(0, str(vendor_path))

# Try importing common packages
test_packages = ["mcp_qa", "pydevkit", "adapter_kit"]

for pkg in test_packages:
    try:
        __import__(pkg)
        print(f"✓ {pkg}")
    except ImportError as e:
        print(f"✗ {pkg}: {e}")
        sys.exit(1)
"""

            result = subprocess.run(
                ["python", "-c", test_script],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                errors.append(f"Import test failed: {result.stderr}")

        except Exception as e:
            errors.append(f"Failed to run import test: {e}")

        success = len(errors) == 0
        return success, errors


class EnvironmentManager:
    """Manage environment-specific configurations.

    Handles environment variables and secrets for different platforms.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    def generate_env_template(self) -> str:
        """Generate .env.template with required variables.

        Returns:
            Template content
        """
        return """# Environment Variables Template
# Copy to .env and fill in your values

# Platform Configuration
DEPLOYMENT_PLATFORM=vercel

# Python Configuration
PYTHONPATH=pheno_vendor

# Application Settings
# Add your app-specific variables below
"""

    def validate_env(self, platform: str) -> tuple[bool, list[str]]:
        """Validate environment configuration for platform.

        Args:
            platform: Target platform

        Returns:
            Tuple of (success, missing_vars)
        """
        # Platform-specific required variables
        required_vars = {
            "vercel": ["PYTHONPATH"],
            "docker": ["PYTHONPATH"],
            "lambda": ["PYTHONPATH"],
            "railway": [],
            "heroku": [],
        }

        missing = []
        env_file = self.project_root / ".env"

        if not env_file.exists():
            return False, ["No .env file found"]

        content = env_file.read_text()
        required = required_vars.get(platform.lower(), [])

        for var in required:
            if var not in content:
                missing.append(var)

        success = len(missing) == 0
        return success, missing
