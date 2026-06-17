"""
Docker deployment pipeline implementation.
"""

from __future__ import annotations

import asyncio

from ..base import BaseDeployment, DeploymentStage


class DockerDeployment(BaseDeployment):
    """Deployment pipeline for building, testing, and publishing Docker images.

    Integrates with the local Docker CLI and supports tagging for custom registries.
    """

    def _init_stages(self) -> None:
        """Define the stages executed for a Docker image deployment.

        The stages cover validation, build, optional tests, tagging, and push, and their
        weights influence overall progress reporting.
        """
        self.stages = [
            DeploymentStage("validate", "Validate Dockerfile", 0.5),
            DeploymentStage("build", "Build Docker image", 2.0),
            DeploymentStage("test", "Test container", 1.0),
            DeploymentStage("tag", "Tag image for registry", 0.5),
            DeploymentStage("push", "Push to registry", 1.5),
        ]

    async def _execute_stage(self, stage: DeploymentStage) -> bool:
        """Dispatch execution of the current Docker deployment stage.

        Args:
            stage: Stage metadata describing the current pipeline step.

        Returns:
            ``True`` when the stage succeeds, otherwise ``False``.
        """
        try:
            if stage.name == "validate":
                return await self._validate_dockerfile(stage)
            if stage.name == "build":
                return await self._build_image(stage)
            if stage.name == "test":
                return await self._test_container(stage)
            if stage.name == "tag":
                return await self._tag_image(stage)
            if stage.name == "push":
                return await self._push_image(stage)
            return False
        except Exception as e:
            stage.add_log(f"Error: {e}")
            return False

    async def _validate_dockerfile(self, stage: DeploymentStage) -> bool:
        """Validate that a Dockerfile exists in the project root.

        Args:
            stage: Stage metadata used for logging output.

        Returns:
            ``True`` when the Dockerfile is found.
        """
        stage.add_log("Validating Dockerfile...")

        dockerfile = self.project_path / "Dockerfile"
        if not dockerfile.exists():
            stage.add_log("❌ Dockerfile not found")
            return False

        stage.add_log("✅ Dockerfile found")
        return True

    async def _build_image(self, stage: DeploymentStage) -> bool:
        """Build the Docker image using ``docker build``.

        Args:
            stage: Stage metadata used for logging output.

        Returns:
            ``True`` when the build succeeds.
        """
        stage.add_log("Building Docker image...")

        image_name = self.config.get("image_name", f"{self.project_path.name}:latest")

        try:
            result = await asyncio.create_subprocess_exec(
                "docker",
                "build",
                "-t",
                image_name,
                ".",
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await result.communicate()

            if result.returncode == 0:
                stage.add_log(f"✅ Image built: {image_name}")
                return True
            stage.add_log(f"❌ Build failed: {stderr.decode()}")
            return False
        except FileNotFoundError:
            stage.add_log("❌ Docker not found")
            return False

    async def _test_container(self, stage: DeploymentStage) -> bool:
        """Execute a smoke test container to validate the image.

        Args:
            stage: Stage metadata used for logging output.

        Returns:
            ``True`` when the test command succeeds.
        """
        stage.add_log("Testing container...")

        image_name = self.config.get("image_name", f"{self.project_path.name}:latest")

        try:
            result = await asyncio.create_subprocess_exec(
                "docker",
                "run",
                "--rm",
                image_name,
                "echo",
                "test",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await result.communicate()

            if result.returncode == 0:
                stage.add_log("✅ Container test passed")
                return True
            stage.add_log(f"❌ Container test failed: {stderr.decode()}")
            return False
        except FileNotFoundError:
            stage.add_log("❌ Docker not found")
            return False

    async def _tag_image(self, stage: DeploymentStage) -> bool:
        """Tag the Docker image with the configured registry prefix.

        Args:
            stage: Stage metadata used for logging output.

        Returns:
            ``True`` when tagging succeeds.
        """
        stage.add_log("Tagging image...")

        registry = self.config.get("registry", "docker.io")
        image_name = self.config.get("image_name", f"{self.project_path.name}:latest")
        full_tag = f"{registry}/{image_name}"

        try:
            result = await asyncio.create_subprocess_exec(
                "docker",
                "tag",
                image_name,
                full_tag,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await result.communicate()

            if result.returncode == 0:
                stage.add_log(f"✅ Tagged as: {full_tag}")
                return True
            stage.add_log("❌ Tagging failed")
            return False
        except FileNotFoundError:
            stage.add_log("❌ Docker not found")
            return False

    async def _push_image(self, stage: DeploymentStage) -> bool:
        """Push the Docker image to the target registry.

        Args:
            stage: Stage metadata used for logging output.

        Returns:
            ``True`` when the push succeeds.
        """
        stage.add_log("Pushing to registry...")

        registry = self.config.get("registry", "docker.io")
        image_name = self.config.get("image_name", f"{self.project_path.name}:latest")
        full_tag = f"{registry}/{image_name}"

        try:
            result = await asyncio.create_subprocess_exec(
                "docker",
                "push",
                full_tag,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await result.communicate()

            if result.returncode == 0:
                stage.add_log(f"✅ Pushed: {full_tag}")
                return True
            stage.add_log(f"❌ Push failed: {stderr.decode()}")
            return False
        except FileNotFoundError:
            stage.add_log("❌ Docker not found")
            return False


__all__ = ["DockerDeployment"]
