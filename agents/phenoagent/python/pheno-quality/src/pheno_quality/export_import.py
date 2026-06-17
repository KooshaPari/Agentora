"""
Quality analysis framework export/import functionality.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import CONFIG_REGISTRY


class QualityFrameworkExporter:
    """
    Export quality analysis framework for use in other projects.
    """

    def __init__(self, framework_path: str | Path):
        self.framework_path = Path(framework_path)

    def export_framework(
        self,
        output_path: str | Path,
        include_tools: bool = True,
        include_configs: bool = True,
        include_examples: bool = True,
    ) -> bool:
        """
        Export the quality analysis framework.
        """
        try:
            output_path = Path(output_path)
            output_path.mkdir(parents=True, exist_ok=True)

            # Export core framework
            self._export_core_framework(output_path)

            # Export tools if requested
            if include_tools:
                self._export_tools(output_path)

            # Export configurations if requested
            if include_configs:
                self._export_configurations(output_path)

            # Export examples if requested
            if include_examples:
                self._export_examples(output_path)

            # Create package manifest
            self._create_manifest(output_path)

            return True
        except Exception as e:
            print(f"Error exporting framework: {e}")
            return False

    def _export_core_framework(self, output_path: Path):
        """
        Export core framework files.
        """
        core_files = [
            "core.py",
            "plugins.py",
            "exporters.py",
            "importers.py",
            "registry.py",
            "utils.py",
            "manager.py",
            "config.py",
        ]

        for file_name in core_files:
            src_file = self.framework_path / "quality" / file_name
            if src_file.exists():
                dst_file = output_path / "quality" / file_name
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                dst_file.write_text(src_file.read_text())

    def _export_tools(self, output_path: Path):
        """
        Export quality analysis tools.
        """
        tools_dir = self.framework_path / "quality" / "tools"
        if tools_dir.exists():
            dst_tools_dir = output_path / "quality" / "tools"
            dst_tools_dir.mkdir(parents=True, exist_ok=True)

            # Copy all tool files
            for tool_file in tools_dir.glob("*.py"):
                if tool_file.name != "__init__.py":
                    dst_file = dst_tools_dir / tool_file.name
                    dst_file.write_text(tool_file.read_text())

            # Copy __init__.py
            init_file = tools_dir / "__init__.py"
            if init_file.exists():
                dst_init = dst_tools_dir / "__init__.py"
                dst_init.write_text(init_file.read_text())

    def _export_configurations(self, output_path: Path):
        """
        Export configuration presets.
        """
        configs_dir = output_path / "configs"
        configs_dir.mkdir(exist_ok=True)

        for config_name, config in CONFIG_REGISTRY.items():
            config_file = configs_dir / f"{config_name}.json"
            config_file.write_text(json.dumps(config.to_dict(), indent=2))

    def _export_examples(self, output_path: Path):
        """
        Export usage examples.
        """
        examples_dir = output_path / "examples"
        examples_dir.mkdir(exist_ok=True)

        # Create basic usage example
        basic_example = examples_dir / "basic_usage.py"
        basic_example.write_text(self._get_basic_usage_example())

        # Create advanced usage example
        advanced_example = examples_dir / "advanced_usage.py"
        advanced_example.write_text(self._get_advanced_usage_example())

        # Create configuration example
        config_example = examples_dir / "custom_config.py"
        config_example.write_text(self._get_config_example())

    def _create_manifest(self, output_path: Path):
        """
        Create package manifest.
        """
        manifest = {
            "name": "pheno-quality-framework",
            "version": "1.0.0",
            "description": "Comprehensive quality analysis framework for Python projects",
            "author": "ATOMS-PHENO Team",
            "created": datetime.now().isoformat(),
            "components": {
                "core": [
                    "core.py",
                    "plugins.py",
                    "exporters.py",
                    "importers.py",
                    "registry.py",
                    "utils.py",
                    "manager.py",
                    "config.py",
                ],
                "tools": [
                    "pattern_detector.py",
                    "architectural_validator.py",
                    "performance_detector.py",
                    "security_scanner.py",
                    "code_smell_detector.py",
                    "integration_gates.py",
                    "atlas_health.py",
                ],
                "configs": list(CONFIG_REGISTRY.keys()),
                "examples": ["basic_usage.py", "advanced_usage.py", "custom_config.py"],
            },
            "requirements": [
                "ast",
                "pathlib",
                "typing",
                "dataclasses",
                "enum",
                "json",
                "time",
                "datetime",
                "concurrent.futures",
                "re",
                "hashlib",
                "uuid",
                "zipfile",
            ],
        }

        manifest_file = output_path / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2))

    def _get_basic_usage_example(self) -> str:
        """
        Get basic usage example.
        """
        return '''#!/usr/bin/env python3
"""
Basic usage example for Pheno Quality Framework
"""

from quality.manager import quality_manager
from quality.config import get_config

def main():
    # Create a quality analysis manager
    manager = quality_manager

    # Analyze a project
    report = manager.analyze_project(
        project_path='./src',
        enabled_tools=['pattern_detector', 'code_smell_detector'],
        output_path='./reports/quality_report.json'
    )

    # Print summary
    summary = manager.generate_summary(report)
    print(f"Quality Score: {summary['quality_score']:.1f}/100")
    print(f"Total Issues: {summary['total_issues']}")
    print(f"Files Affected: {summary['files_affected']}")

    # Print recommendations
    for recommendation in summary['recommendations']:
        print(f"  {recommendation}")

if __name__ == "__main__":
    main()
'''

    def _get_advanced_usage_example(self) -> str:
        """
        Get advanced usage example.
        """
        return '''#!/usr/bin/env python3
"""
Advanced usage example for Pheno Quality Framework
"""

from quality.manager import quality_manager
from quality.config import create_custom_config
from quality.core import QualityConfig

def main():
    # Create custom configuration
    config = create_custom_config(
        'pheno-sdk',
        enabled_tools=['pattern_detector', 'architectural_validator', 'performance_detector'],
        thresholds={
            'max_violations': 25,
            'quality_score_threshold': 85.0
        },
        parallel_analysis=True,
        max_workers=8
    )

    # Create manager with custom config
    manager = quality_manager
    manager.config = config

    # Analyze project
    report = manager.analyze_project(
        project_path='./src',
        output_path='./reports/advanced_quality_report.json'
    )

    # Export in multiple formats
    manager.export_report(report, './reports/quality_report.html')
    manager.export_report(report, './reports/quality_report.md')
    manager.export_report(report, './reports/quality_report.csv')

    # Get detailed metrics
    print("Detailed Analysis Results:")
    print(f"  Quality Score: {report.metrics.quality_score:.1f}/100")
    print(f"  Analysis Duration: {report.metrics.analysis_duration:.2f}s")

    print("\\nIssues by Severity:")
    for severity, count in report.metrics.issues_by_severity.items():
        print(f"  {severity}: {count}")

    print("\\nIssues by Tool:")
    for tool, count in report.metrics.issues_by_tool.items():
        print(f"  {tool}: {count}")

    # Get high-priority issues
    high_issues = report.get_issues_by_severity('high')
    if high_issues:
        print(f"\\nHigh Priority Issues ({len(high_issues)}):")
        for issue in high_issues[:5]:  # Show first 5
            print(f"  {issue.type} in {issue.file}:{issue.line}")
            print(f"    {issue.message}")

if __name__ == "__main__":
    main()
'''

    def _get_config_example(self) -> str:
        """
        Get configuration example.
        """
        return '''#!/usr/bin/env python3
"""
Configuration example for Pheno Quality Framework
"""

from quality.config import create_custom_config, get_config, list_configs
from quality.core import QualityConfig

def main():
    # List available configurations
    print("Available configurations:")
    for config_name in list_configs():
        print(f"  - {config_name}")

    # Get a specific configuration
    config = get_config('pheno-sdk')
    print(f"\\nPheno-SDK config thresholds: {config.thresholds}")

    # Create custom configuration
    custom_config = create_custom_config(
        'default',
        enabled_tools=['pattern_detector', 'security_scanner'],
        thresholds={
            'max_violations': 50,
            'quality_score_threshold': 75.0,
            'long_method_lines': 30,
            'max_nested_loops': 2
        },
        filters={
            'severity': ['high', 'critical'],
            'exclude_patterns': ['test_*', '*_test.py']
        },
        parallel_analysis=True,
        max_workers=4
    )

    print(f"\\nCustom config: {custom_config.to_dict()}")

    # Create configuration from scratch
    scratch_config = QualityConfig(
        enabled_tools=['pattern_detector'],
        thresholds={'max_violations': 100},
        output_format='json',
        parallel_analysis=False
    )

    print(f"\\nScratch config: {scratch_config.to_dict()}")

if __name__ == "__main__":
    main()
'''


class QualityFrameworkImporter:
    """
    Import quality analysis framework from exported package.
    """

    def __init__(self, package_path: str | Path):
        self.package_path = Path(package_path)

    def import_framework(self, target_path: str | Path) -> bool:
        """
        Import the quality analysis framework.
        """
        try:
            target_path = Path(target_path)
            target_path.mkdir(parents=True, exist_ok=True)

            # Read manifest
            manifest_file = self.package_path / "manifest.json"
            if not manifest_file.exists():
                print("Error: No manifest.json found in package")
                return False

            manifest = json.loads(manifest_file.read_text())

            # Copy framework files
            self._copy_framework_files(target_path)

            # Install requirements if needed
            self._install_requirements(manifest.get("requirements", []))

            # Create integration files
            self._create_integration_files(target_path, manifest)

            return True
        except Exception as e:
            print(f"Error importing framework: {e}")
            return False

    def _copy_framework_files(self, target_path: Path):
        """
        Copy framework files to target location.
        """
        # Copy quality directory
        if (self.package_path / "quality").exists():
            import shutil

            shutil.copytree(
                self.package_path / "quality", target_path / "quality", dirs_exist_ok=True,
            )

        # Copy configs
        if (self.package_path / "configs").exists():
            import shutil

            shutil.copytree(
                self.package_path / "configs", target_path / "configs", dirs_exist_ok=True,
            )

        # Copy examples
        if (self.package_path / "examples").exists():
            import shutil

            shutil.copytree(
                self.package_path / "examples", target_path / "examples", dirs_exist_ok=True,
            )

    def _install_requirements(self, requirements: list[str]):
        """
        Install Python requirements.
        """
        # This would typically use pip or similar
        print(f"Requirements to install: {requirements}")
        print("Please install these requirements manually or use pip install -r requirements.txt")

    def _create_integration_files(self, target_path: Path, manifest: dict[str, Any]):
        """
        Create integration files for the target project.
        """
        # Create __init__.py for quality module
        init_file = target_path / "quality" / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""Quality analysis framework"""\n')

        # Create setup script
        setup_script = target_path / "setup_quality.py"
        setup_script.write_text(self._get_setup_script())

        # Create usage guide
        usage_guide = target_path / "QUALITY_USAGE.md"
        usage_guide.write_text(self._get_usage_guide(manifest))

    def _get_setup_script(self) -> str:
        """
        Get setup script content.
        """
        return '''#!/usr/bin/env python3
"""
Setup script for Pheno Quality Framework
"""

import sys
from pathlib import Path

def setup_quality_framework():
    """Setup the quality analysis framework"""
    print("Setting up Pheno Quality Framework...")

    # Add quality module to Python path
    quality_path = Path(__file__).parent / 'quality'
    if str(quality_path) not in sys.path:
        sys.path.insert(0, str(quality_path))

    print("✅ Quality framework setup complete!")
    print("\\nUsage:")
    print("  from quality.manager import quality_manager")
    print("  report = quality_manager.analyze_project('./src')")
    print("  print(f'Quality Score: {report.metrics.quality_score:.1f}/100')")

if __name__ == "__main__":
    setup_quality_framework()
'''

    def _get_usage_guide(self, manifest: dict[str, Any]) -> str:
        """
        Get usage guide content.
        """
        return f"""# Pheno Quality Framework Usage Guide

## Overview
{manifest.get('description', 'Comprehensive quality analysis framework for Python projects')}

## Quick Start

### Basic Usage
```python
from quality.manager import quality_manager

# Analyze a project
report = quality_manager.analyze_project('./src')
print(f'Quality Score: {{report.metrics.quality_score:.1f}}/100')
```

### Advanced Usage
```python
from quality.config import create_custom_config
from quality.manager import quality_manager

# Create custom configuration
config = create_custom_config(
    'pheno-sdk',
    enabled_tools=['pattern_detector', 'security_scanner'],
    thresholds={{'max_violations': 50}}
)

# Analyze with custom config
manager = quality_manager
manager.config = config
report = manager.analyze_project('./src', output_path='./reports/quality.json')
```

## Available Tools
{chr(10).join(f'- {tool}' for tool in manifest.get('components', {}).get('tools', []))}

## Available Configurations
{chr(10).join(f'- {config}' for config in manifest.get('components', {}).get('configs', []))}

## Examples
See the `examples/` directory for detailed usage examples.

## Requirements
{chr(10).join(f'- {req}' for req in manifest.get('requirements', []))}
"""


def export_quality_framework(
    framework_path: str | Path, output_path: str | Path,
) -> bool:
    """
    Export quality analysis framework.
    """
    exporter = QualityFrameworkExporter(framework_path)
    return exporter.export_framework(output_path)


def import_quality_framework(package_path: str | Path, target_path: str | Path) -> bool:
    """
    Import quality analysis framework.
    """
    importer = QualityFrameworkImporter(package_path)
    return importer.import_framework(target_path)
