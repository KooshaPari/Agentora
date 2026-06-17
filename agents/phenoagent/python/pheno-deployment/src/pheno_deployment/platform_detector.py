"""Platform detection and analysis for deployment utilities.

Provides automatic detection of deployment platforms based on project structure and
configuration files.
"""

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

    def get_supported_platforms(self) -> list[str]:
        """Get list of all supported platforms.

        Returns:
            List of platform names
        """
        return list(self.PLATFORM_SIGNATURES.keys())

    def has_platform_config(self, platform: str) -> bool:
        """Check if project has configuration for specific platform.

        Args:
            platform: Platform name to check

        Returns:
            True if configuration files exist
        """
        platform = platform.lower()
        if platform not in self.PLATFORM_SIGNATURES:
            return False

        signature = self.PLATFORM_SIGNATURES[platform]
        for file_pattern in signature["files"]:
            if (self.project_root / file_pattern).exists():
                return True

        return False

    def get_platform_files(self, platform: str) -> list[Path]:
        """Get existing configuration files for a platform.

        Args:
            platform: Platform name

        Returns:
            List of existing file paths
        """
        platform = platform.lower()
        if platform not in self.PLATFORM_SIGNATURES:
            return []

        signature = self.PLATFORM_SIGNATURES[platform]
        existing_files = []

        for file_pattern in signature["files"]:
            file_path = self.project_root / file_pattern
            if file_path.exists():
                existing_files.append(file_path)

        return existing_files


__all__ = [
    "PlatformDetector",
    "PlatformInfo",
]
