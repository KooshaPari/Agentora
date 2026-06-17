"""
NPM deployment pipeline implementation.
"""

from __future__ import annotations

import asyncio
import json

from ..base import BaseDeployment, DeploymentStage


class NPMDeployment(BaseDeployment):
    """Deployment pipeline for publishing JavaScript/TypeScript packages to NPM.

    Handles dependency installation, test execution, building, and publishing with
    optional dry-run support.
    """

    def _init_stages(self) -> None:
        """Define the stages executed for an NPM deployment.

        Each stage weight represents its contribution to overall progress and can be
        tuned to reflect expected execution time.
        """
        self.stages = [
            DeploymentStage("validate", "Validate package.json", 0.5),
            DeploymentStage("install", "Install dependencies", 1.0),
            DeploymentStage("test", "Run tests", 1.5),
            DeploymentStage("build", "Build package", 1.0),
            DeploymentStage("publish", "Publish to NPM", 1.0),
        ]

    async def _execute_stage(self, stage: DeploymentStage) -> bool:
        """Dispatch execution of the current NPM deployment stage.

        Args:
            stage: Stage metadata describing the current pipeline step.

        Returns:
            ``True`` when the stage succeeds, otherwise ``False``.
        """
        try:
            if stage.name == "validate":
                return await self._validate_package_json(stage)
            if stage.name == "install":
                return await self._npm_install(stage)
            if stage.name == "test":
                return await self._npm_test(stage)
            if stage.name == "build":
                return await self._npm_build(stage)
            if stage.name == "publish":
                return await self._npm_publish(stage)
            return False
        except Exception as e:
            stage.add_log(f"Error: {e}")
            return False

    async def _validate_package_json(self, stage: DeploymentStage) -> bool:
        """Validate that ``package.json`` exists and includes required fields.

        Args:
            stage: Stage metadata used for logging output.

        Returns:
            ``True`` when validation passes.
        """
        stage.add_log("Validating package.json...")

        package_json = self.project_path / "package.json"
        if not package_json.exists():
            stage.add_log("❌ package.json not found")
            return False

        try:
            with open(package_json) as f:
                data = json.load(f)

            required_fields = ["name", "version"]
            missing = [field for field in required_fields if field not in data]

            if missing:
                stage.add_log(f"❌ Missing required fields: {missing}")
                return False

            stage.add_log("✅ package.json validated")
            return True
        except json.JSONDecodeError:
            stage.add_log("❌ Invalid JSON in package.json")
            return False

    async def _npm_install(self, stage: DeploymentStage) -> bool:
        """Install dependencies using ``npm install``.

        Args:
            stage: Stage metadata used for logging output.

        Returns:
            ``True`` when installation succeeds.
        """
        stage.add_log("Installing dependencies...")

        try:
            result = await asyncio.create_subprocess_exec(
                "npm",
                "install",
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await result.communicate()

            if result.returncode == 0:
                stage.add_log("✅ Dependencies installed")
                return True
            stage.add_log(f"❌ Install failed: {stderr.decode()}")
            return False
        except FileNotFoundError:
            stage.add_log("❌ npm not found")
            return False

    async def _npm_test(self, stage: DeploymentStage) -> bool:
        """Execute the ``npm test`` script if defined.

        Args:
            stage: Stage metadata used for logging output.

        Returns:
            ``True`` when tests pass or are skipped; ``False`` otherwise.
        """
        stage.add_log("Running tests...")

        try:
            result = await asyncio.create_subprocess_exec(
                "npm",
                "test",
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await result.communicate()

            if result.returncode == 0:
                stage.add_log("✅ Tests passed")
                return True
            stage.add_log(f"⚠️  Tests failed: {stderr.decode()}")
            return not self.config.get("fail_on_test_failure", False)
        except FileNotFoundError:
            stage.add_log("⚠️  npm not found, skipping tests")
            return True

    async def _npm_build(self, stage: DeploymentStage) -> bool:
        """Execute the ``npm run build`` script to produce artifacts.

        Args:
            stage: Stage metadata used for logging output.

        Returns:
            ``True`` when the build succeeds.
        """
        stage.add_log("Building package...")

        package_json = self.project_path / "package.json"
        try:
            with open(package_json) as f:
                data = json.load(f)

            if "build" in data.get("scripts", {}):
                result = await asyncio.create_subprocess_exec(
                    "npm",
                    "run",
                    "build",
                    cwd=self.project_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _stdout, stderr = await result.communicate()

                if result.returncode == 0:
                    stage.add_log("✅ Build successful")
                    return True
                stage.add_log(f"❌ Build failed: {stderr.decode()}")
                return False
            stage.add_log("⚠️  No build script found, skipping")
            return True
        except Exception:
            stage.add_log("⚠️  Skipping build")
            return True

    async def _npm_publish(self, stage: DeploymentStage) -> bool:
        """Publish the package to the NPM registry using ``npm publish``.

        Args:
            stage: Stage metadata used for logging output.

        Returns:
            ``True`` when publishing succeeds.
        """
        stage.add_log("Publishing to NPM...")

        try:
            cmd = ["npm", "publish"]
            if self.config.get("dry_run", False):
                cmd.append("--dry-run")

            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await result.communicate()

            if result.returncode == 0:
                stage.add_log("✅ Published successfully")
                return True
            stage.add_log(f"❌ Publish failed: {stderr.decode()}")
            return False
        except FileNotFoundError:
            stage.add_log("❌ npm not found")
            return False


__all__ = ["NPMDeployment"]
