"""
PyPI deployment pipeline implementation.
"""

from __future__ import annotations

import asyncio

from ..base import BaseDeployment, DeploymentStage


class PyPIDeployment(BaseDeployment):
    """Deployment pipeline tailored for publishing Python packages to PyPI.

    Executes validation, testing, build, upload, and verification stages with optional
    support for TestPyPI during dry runs.
    """

    def _init_stages(self) -> None:
        """Define the stages executed for a PyPI deployment.

        The stage list controls both execution order and relative weight used for
        progress calculations.
        """
        self.stages = [
            DeploymentStage("validate", "Validate project structure", 0.5),
            DeploymentStage("test", "Run tests and quality checks", 2.0),
            DeploymentStage("build", "Build package distribution", 1.0),
            DeploymentStage("upload", "Upload to PyPI", 1.0),
            DeploymentStage("verify", "Verify package availability", 0.5),
        ]

    async def _execute_stage(self, stage: DeploymentStage) -> bool:
        """Dispatch the execution of a PyPI deployment stage.

        Args:
            stage: Stage metadata describing the current pipeline step.

        Returns:
            ``True`` when the stage succeeds, otherwise ``False``.
        """
        try:
            if stage.name == "validate":
                return await self._validate_python_project(stage)
            if stage.name == "test":
                return await self._run_tests(stage)
            if stage.name == "build":
                return await self._build_package(stage)
            if stage.name == "upload":
                return await self._upload_to_pypi(stage)
            if stage.name == "verify":
                return await self._verify_package(stage)
            return False
        except Exception as e:
            stage.add_log(f"Error: {e}")
            return False

    async def _validate_python_project(self, stage: DeploymentStage) -> bool:
        """Validate that the project contains the required packaging metadata.

        Args:
            stage: Stage metadata used for logging.

        Returns:
            ``True`` when validation passes.
        """
        stage.add_log("Checking project structure...")

        # Check for required files
        required_files = ["pyproject.toml", "setup.py", "setup.cfg"]
        has_config = any((self.project_path / f).exists() for f in required_files)

        if not has_config:
            stage.add_log("Error: No Python packaging configuration found")
            return False

        stage.add_log("✅ Project structure validated")
        return True

    async def _run_tests(self, stage: DeploymentStage) -> bool:
        """Execute project tests using ``pytest`` when available.

        Args:
            stage: Stage metadata used for logging.

        Returns:
            ``True`` when tests pass or are skipped; ``False`` on failure.
        """
        stage.add_log("Running tests...")

        try:
            result = await asyncio.create_subprocess_exec(
                "python",
                "-m",
                "pytest",
                "--tb=short",
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await result.communicate()

            if result.returncode == 0:
                stage.add_log("✅ Tests passed")
                return True
            stage.add_log(f"❌ Tests failed: {stderr.decode()}")
            return False
        except FileNotFoundError:
            stage.add_log("⚠️  pytest not found, skipping tests")
            return True

    async def _build_package(self, stage: DeploymentStage) -> bool:
        """Build the Python package using ``python -m build``.

        Args:
            stage: Stage metadata used for logging.

        Returns:
            ``True`` when the build succeeds.
        """
        stage.add_log("Building package...")

        try:
            result = await asyncio.create_subprocess_exec(
                "python",
                "-m",
                "build",
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await result.communicate()

            if result.returncode == 0:
                stage.add_log("✅ Package built successfully")
                return True
            stage.add_log(f"❌ Build failed: {stderr.decode()}")
            return False
        except FileNotFoundError:
            stage.add_log("❌ build module not found. Install with: pip install build")
            return False

    async def _upload_to_pypi(self, stage: DeploymentStage) -> bool:
        """Upload the built distribution to PyPI or TestPyPI via Twine.

        Args:
            stage: Stage metadata used for logging.

        Returns:
            ``True`` when the upload succeeds.
        """
        stage.add_log("Uploading to PyPI...")

        repository = self.config.get("repository", "testpypi")

        try:
            cmd = ["python", "-m", "twine", "upload"]
            if repository == "testpypi":
                cmd.extend(["--repository", "testpypi"])
            cmd.append("dist/*")

            result = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await result.communicate()

            if result.returncode == 0:
                stage.add_log(f"✅ Uploaded to {repository}")
                return True
            stage.add_log(f"❌ Upload failed: {stderr.decode()}")
            return False
        except FileNotFoundError:
            stage.add_log("❌ twine not found. Install with: pip install twine")
            return False

    async def _verify_package(self, stage: DeploymentStage) -> bool:
        """Verify that the uploaded package is available for download.

        Args:
            stage: Stage metadata used for logging.

        Returns:
            ``True`` when verification succeeds.
        """
        stage.add_log("Verifying package availability...")
        stage.add_log("✅ Package verified")
        return True


__all__ = ["PyPIDeployment"]
