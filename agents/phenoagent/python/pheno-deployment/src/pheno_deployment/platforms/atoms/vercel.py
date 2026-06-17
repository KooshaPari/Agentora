"""Vercel Platform Implementation.

Platform-specific implementation for Vercel deployments. Can be moved to pheno-
sdk/deploy-kit/platforms/vercel.py

This implements the abstract DeploymentProvider for Vercel.
"""

import subprocess
from pathlib import Path
from typing import Any

from ...base.deployment import (
    DeploymentConfig,
    DeploymentEnvironment,
    DeploymentProvider,
    DeploymentResult,
    DeploymentStatus,
)


class VercelDeploymentProvider(DeploymentProvider):
    """
    Vercel-specific deployment implementation.
    """

    def __init__(self, config: DeploymentConfig, logger=None):
        super().__init__(config, logger)
        self.deployment_url: str | None = None
        self.deployment_id: str | None = None

    def validate_config(self) -> bool:
        """
        Validate Vercel deployment configuration.
        """
        # Check project root exists
        if not self.config.project_root.exists():
            self.log_error(f"Project root not found: {self.config.project_root}")
            return False

        # Check env file if specified
        if self.config.env_file and not self.config.env_file.exists():
            self.log_error(f"Environment file not found: {self.config.env_file}")
            return False

        return True

    def check_prerequisites(self) -> bool:
        """
        Check if Vercel CLI is installed and user is authenticated.
        """
        try:
            # Check CLI installed
            result = subprocess.run(
                ["vercel", "--version"], capture_output=True, text=True, check=True,
            )
            self.log_info(f"Vercel CLI version: {result.stdout.strip()}")

            # Could add auth check here
            # vercel whoami

            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log_error("Vercel CLI not found or not installed")
            return False

    def deploy(self) -> DeploymentResult:
        """
        Execute Vercel deployment.
        """
        # Validate first
        if not self.validate_config():
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                environment=self.config.environment,
                error_message="Configuration validation failed",
            )

        # Check prerequisites
        if not self.check_prerequisites():
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                environment=self.config.environment,
                error_message="Prerequisites check failed",
            )

        # Build deployment command
        cmd = ["vercel", "--yes"]

        if self.config.environment == DeploymentEnvironment.PRODUCTION:
            cmd.insert(1, "--prod")

        self.log_info(f"Running deployment command: {' '.join(cmd)}")

        # Execute deployment
        try:
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                check=True,
                text=True,
                capture_output=True,  # Capture to parse URL
            )

            # Parse deployment URL from output
            # Vercel outputs: "✅  Preview: https://..."
            for line in result.stdout.split("\n"):
                if "Preview:" in line or "Production:" in line:
                    parts = line.split("https://")
                    if len(parts) > 1:
                        self.deployment_url = "https://" + parts[1].strip()
                        break

            self.log_info("Deployment completed successfully")

            return DeploymentResult(
                status=DeploymentStatus.SUCCESS,
                environment=self.config.environment,
                url=self.deployment_url or self.config.domain,
                deployment_id=self.deployment_id,
                metadata={"output": result.stdout},
            )

        except subprocess.CalledProcessError as e:
            self.log_error(f"Deployment failed: {e}")
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                environment=self.config.environment,
                error_message=str(e),
                metadata={"stderr": e.stderr if hasattr(e, "stderr") else None},
            )

    def rollback(self, deployment_id: str) -> DeploymentResult:
        """
        Rollback to a previous Vercel deployment.
        """
        cmd = ["vercel", "rollback", deployment_id, "--yes"]

        try:
            result = subprocess.run(
                cmd, cwd=self.config.project_root, check=True, text=True, capture_output=True,
            )

            self.log_info(f"Rolled back to deployment: {deployment_id}")

            return DeploymentResult(
                status=DeploymentStatus.ROLLED_BACK,
                environment=self.config.environment,
                deployment_id=deployment_id,
                metadata={"output": result.stdout},
            )

        except subprocess.CalledProcessError as e:
            self.log_error(f"Rollback failed: {e}")
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                environment=self.config.environment,
                error_message=f"Rollback failed: {e}",
            )

    def get_deployment_url(self) -> str | None:
        """
        Get the URL of the deployed application.
        """
        if self.deployment_url:
            return self.deployment_url

        # Fallback to configured domain
        if self.config.domain:
            return f"https://{self.config.domain}"

        return None

    def get_deployments(self, limit: int = 10) -> list:
        """
        Get list of recent deployments.
        """
        cmd = ["vercel", "ls", "--json"]

        try:
            result = subprocess.run(
                cmd, cwd=self.config.project_root, check=True, text=True, capture_output=True,
            )

            import json

            deployments = json.loads(result.stdout)
            return deployments[:limit]

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            self.log_error(f"Failed to get deployments: {e}")
            return []

    def get_logs(self, deployment_id: str | None = None) -> str:
        """
        Get deployment logs.
        """
        cmd = ["vercel", "logs"]
        if deployment_id:
            cmd.append(deployment_id)

        try:
            result = subprocess.run(
                cmd, cwd=self.config.project_root, check=True, text=True, capture_output=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.log_error(f"Failed to get logs: {e}")
            return ""


class VercelConfigProvider:
    """
    Vercel-specific configuration management.
    """

    @staticmethod
    def get_environment_domain(environment: DeploymentEnvironment) -> str | None:
        """Get default domain for environment.

        This is platform-specific and should be overridden by application.
        """
        # This would be overridden in atoms-specific implementation
        return None

    @staticmethod
    def get_environment_file(environment: DeploymentEnvironment, project_root: Path) -> Path | None:
        """
        Get environment file path for environment.
        """
        env_files = {
            DeploymentEnvironment.PREVIEW: ".env.preview",
            DeploymentEnvironment.PRODUCTION: ".env.production",
            DeploymentEnvironment.STAGING: ".env.staging",
        }

        env_file = env_files.get(environment)
        if env_file:
            path = project_root / env_file
            return path if path.exists() else None

        return None

    @staticmethod
    def create_vercel_config(
        project_root: Path,
        build_command: str | None = None,
        install_command: str | None = None,
        env_vars: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Create vercel.json configuration.
        """
        config = {
            "version": 2,
        }

        if build_command:
            config["buildCommand"] = build_command

        if install_command:
            config["installCommand"] = install_command

        if env_vars:
            config["env"] = env_vars

        return config
