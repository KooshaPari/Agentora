"""Artifact builders and build hook generation for deployment utilities.

Provides platform-specific build script and configuration file generation with vendored
package handling.
"""

from pathlib import Path


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

    def generate_dockerfile(self, platform: str = "auto") -> str:
        """Generate Dockerfile for specified platform.

        Args:
            platform: Target platform (auto = detect from project)

        Returns:
            Dockerfile content
        """
        if platform == "auto":
            # Auto-detect platform
            detector = PlatformDetector(self.project_root)
            platform = detector.detect()

        return self._generate_docker_content(platform)

    def _generate_docker_content(self, platform: str) -> str:
        """
        Generate Dockerfile content for platform.
        """
        docker_templates = {
            "vercel": """FROM python:3.10-alpine
WORKDIR /app
COPY . .
RUN pip install pheno-vendor
RUN pheno-vendor setup --no-validate
RUN pip install -r requirements-prod.txt
CMD ["python", "-m", "vercel", "dev"]
""",
            "docker": """FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install pheno-vendor
RUN pheno-vendor setup --no-validate
RUN pip install -r requirements-prod.txt
EXPOSE 8000
CMD ["python", "server.py"]
""",
            "lambda": """FROM python:3.10-alpine
WORKDIR /app
COPY . .
RUN pip install pheno-vendor
RUN pheno-vendor setup --no-validate
RUN pip install -r requirements-prod.txt
CMD ["python", "lambda_function.py"]
""",
        }

        return docker_templates.get(platform, self._generate_docker_content("docker"))

    def create_build_script(self, platform: str, output_path: Path | None = None) -> Path:
        """Create a build script file for the platform.

        Args:
            platform: Target platform
            output_path: Where to save the script (default: build_<platform>.sh)

        Returns:
            Path to the created script file
        """
        if output_path is None:
            output_path = self.project_root / f"build_{platform}.sh"

        content = self.generate(platform)

        with open(output_path, "w") as f:
            f.write(content)

        # Make executable on Unix systems
        import os

        if os.name != "nt":
            import stat

            current_permissions = output_path.stat().st_mode
            output_path.chmod(current_permissions | stat.S_IEXEC)

        return output_path


class ArtifactValidator:
    """Validate generated artifacts and deployment readiness.

    Ensures generated build scripts and configurations are valid.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    def validate_artifact(
        self, artifact_path: Path, artifact_type: str = "script",
    ) -> dict[str, any]:
        """Validate a specific artifact.

        Args:
            artifact_path: Path to the artifact file
            artifact_type: Type of artifact (script, config, dockerfile)

        Returns:
            Validation results dictionary
        """
        results = {
            "exists": artifact_path.exists(),
            "readable": False,
            "valid": False,
            "errors": [],
        }

        if artifact_path.exists():
            try:
                with open(artifact_path) as f:
                    content = f.read()
                    results["readable"] = True

                    # Basic validation based on artifact type
                    if artifact_type == "script":
                        results["valid"] = self._validate_script(content)
                    elif artifact_type == "dockerfile":
                        results["valid"] = self._validate_dockerfile(content)
                    else:
                        results["valid"] = True  # Generic validation

            except Exception as e:
                results["errors"].append(f"Failed to read artifact: {e}")

        return results

    def _validate_script(self, content: str) -> bool:
        """
        Validate shell script content.
        """
        # Basic validation - check for shebang and essential commands
        lines = content.strip().split("\n")
        return len(lines) > 1 and (lines[0].startswith("#!") or "pheno-vendor" in content)

    def _validate_dockerfile(self, content: str) -> bool:
        """
        Validate Dockerfile content.
        """
        # Basic validation - check for FROM instruction
        lines = content.strip().split("\n")
        return any(line.strip().startswith("FROM") for line in lines)


__all__ = [
    "ArtifactValidator",
    "BuildHookGenerator",
]
