"""
Quality analysis framework integration for zen-mcp-server and atoms_mcp-old.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from .config import get_config
from .export_import import export_quality_framework
from .manager import quality_manager


class QualityFrameworkIntegration:
    """
    Integration class for quality analysis framework.
    """

    def __init__(self, project_type: str = "pheno-sdk"):
        self.project_type = project_type
        self.config = get_config(project_type)
        self.manager = quality_manager
        self.manager.config = self.config

    def setup_for_project(self, project_path: str | Path) -> bool:
        """
        Setup quality framework for a specific project.
        """
        try:
            project_path = Path(project_path)

            # Create quality directory in project
            quality_dir = project_path / "quality"
            quality_dir.mkdir(exist_ok=True)

            # Copy framework files
            self._copy_framework_files(quality_dir)

            # Create project-specific configuration
            self._create_project_config(quality_dir)

            # Create integration scripts
            self._create_integration_scripts(quality_dir, project_path)

            return True
        except Exception as e:
            print(f"Error setting up quality framework: {e}")
            return False

    def _copy_framework_files(self, quality_dir: Path):
        """
        Copy framework files to project.
        """
        import shutil

        # Copy all quality framework files
        framework_dir = Path(__file__).parent
        for file_path in framework_dir.glob("*.py"):
            if file_path.name != "__init__.py":
                shutil.copy2(file_path, quality_dir / file_path.name)

        # Copy tools directory
        tools_dir = framework_dir / "tools"
        if tools_dir.exists():
            dst_tools_dir = quality_dir / "tools"
            shutil.copytree(tools_dir, dst_tools_dir, dirs_exist_ok=True)

    def _create_project_config(self, quality_dir: Path):
        """
        Create project-specific configuration.
        """
        config_file = quality_dir / "project_config.py"

        config_content = f'''"""
Project-specific quality analysis configuration for {self.project_type}
"""

from .config import create_custom_config

# Project-specific configuration
PROJECT_CONFIG = create_custom_config(
    '{self.project_type}',
    enabled_tools={self.config.enabled_tools},
    thresholds={self.config.thresholds},
    filters={self.config.filters},
    output_format='{self.config.output_format}',
    output_path='reports',
    parallel_analysis={self.config.parallel_analysis},
    max_workers={self.config.max_workers},
    timeout_seconds={self.config.timeout_seconds}
)

# Tool-specific configurations
TOOL_CONFIGS = {{
    'pattern_detector': {{
        'enabled_patterns': [
            'god_object', 'feature_envy', 'data_clump', 'shotgun_surgery',
            'divergent_change', 'parallel_inheritance', 'lazy_class',
            'inappropriate_intimacy', 'message_chain', 'middle_man'
        ],
        'thresholds': {{
            'god_object_methods': 15,
            'feature_envy_ratio': 2.0,
            'data_clump_params': 3
        }}
    }},
    'architectural_validator': {{
        'enabled_patterns': [
            'hexagonal_architecture', 'clean_architecture', 'solid_principles',
            'layered_architecture', 'domain_driven_design'
        ]
    }},
    'performance_detector': {{
        'enabled_patterns': [
            'n_plus_one_query', 'memory_leak', 'blocking_calls',
            'inefficient_loops', 'excessive_io'
        ],
        'thresholds': {{
            'max_loop_iterations': 1000,
            'max_nested_loops': 3,
            'max_memory_usage_mb': 100
        }}
    }},
    'security_scanner': {{
        'enabled_patterns': [
            'sql_injection', 'xss_vulnerability', 'insecure_deserialization',
            'authentication_bypass', 'authorization_flaw'
        ]
    }},
    'code_smell_detector': {{
        'enabled_patterns': [
            'long_method', 'large_class', 'duplicate_code', 'dead_code',
            'magic_number', 'deep_nesting', 'high_complexity'
        ],
        'thresholds': {{
            'long_method_lines': 50,
            'large_class_methods': 20,
            'cyclomatic_complexity': 10
        }}
    }},
    'integration_gates': {{
        'enabled_gates': [
            'api_contracts', 'data_flow_validation', 'error_handling',
            'logging_validation', 'security_validation'
        ]
    }}
}}
'''

        config_file.write_text(config_content)

    def _create_integration_scripts(self, quality_dir: Path, project_path: Path):
        """
        Create integration scripts for the project.
        """

        # Create main quality analysis script
        main_script = quality_dir / "analyze.py"
        main_script.write_text(self._get_main_analysis_script())
        main_script.chmod(0o755)

        # Create Makefile integration
        makefile_integration = quality_dir / "Makefile.integration"
        makefile_integration.write_text(self._get_makefile_integration())

        # Create CLI integration
        cli_integration = quality_dir / "cli_integration.py"
        cli_integration.write_text(self._get_cli_integration())

        # Create CI/CD integration
        ci_integration = quality_dir / "ci_integration.py"
        ci_integration.write_text(self._get_ci_integration())

    def _get_main_analysis_script(self) -> str:
        """
        Get main analysis script content.
        """
        return f'''#!/usr/bin/env python3
"""
Quality analysis script for {self.project_type}
"""

import sys
import argparse
from pathlib import Path

# Add quality framework to path
sys.path.insert(0, str(Path(__file__).parent))

from manager import quality_manager
from project_config import PROJECT_CONFIG, TOOL_CONFIGS

def main():
    parser = argparse.ArgumentParser(description='Quality Analysis for {self.project_type}')
    parser.add_argument('path', nargs='?', default='.', help='Path to analyze')
    parser.add_argument('--tools', nargs='+', help='Specific tools to run')
    parser.add_argument('--output', '-o', help='Output path for report')
    parser.add_argument('--format', choices=['json', 'html', 'markdown', 'csv'], default='json', help='Output format')
    parser.add_argument('--config', help='Configuration preset to use')
    parser.add_argument('--severity', choices=['low', 'medium', 'high', 'critical'], help='Filter by severity')
    parser.add_argument('--summary', action='store_true', help='Show summary only')

    args = parser.parse_args()

    # Setup configuration
    config = PROJECT_CONFIG
    if args.config:
        from config import get_config
        config = get_config(args.config)

    # Setup manager
    manager = quality_manager
    manager.config = config

    # Determine tools to run
    tools = args.tools or config.enabled_tools

    # Run analysis
    print(f"🔍 Running quality analysis on {args.path}...")
    print(f"Tools: {', '.join(tools)}")

    report = manager.analyze_project(
        project_path=args.path,
        enabled_tools=tools,
        output_path=args.output
    )

    # Generate summary
    summary = manager.generate_summary(report)

    if args.summary:
        # Show summary only
        print(f"\\n📊 Quality Analysis Summary")
        print(f"Project: {summary['project_name']}")
        print(f"Quality Score: {summary['quality_score']:.1f}/100")
        print(f"Total Issues: {summary['total_issues']}")
        print(f"Files Affected: {summary['files_affected']}")
        print(f"Analysis Duration: {summary['analysis_duration']:.2f}s")
        print(f"Quality Status: {summary['quality_status']}")

        if summary['recommendations']:
            print("\\n🔧 Recommendations:")
            for rec in summary['recommendations']:
                print(f"  {rec}")
    else:
        # Show detailed results
        print(f"\\n📊 Quality Analysis Results")
        print(f"Quality Score: {summary['quality_score']:.1f}/100")
        print(f"Total Issues: {summary['total_issues']}")

        print("\\nIssues by Severity:")
        for severity, count in summary['issues_by_severity'].items():
            print(f"  {severity}: {count}")

        print("\\nIssues by Tool:")
        for tool, count in summary['issues_by_tool'].items():
            print(f"  {tool}: {count}")

        # Filter by severity if requested
        if args.severity:
            filtered_issues = [issue for issue in report.issues if issue.severity.value == args.severity]
            print(f"\\n{args.severity.title()} Issues ({len(filtered_issues)}):")
            for issue in filtered_issues[:10]:  # Show first 10
                print(f"  {issue.type} in {issue.file}:{issue.line}")
                print(f"    {issue.message}")
                print(f"    Suggestion: {issue.suggestion}")
                print()

    return 0 if summary['quality_score'] >= 70 else 1

if __name__ == "__main__":
    sys.exit(main())
'''

    def _get_makefile_integration(self) -> str:
        """
        Get Makefile integration content.
        """
        return f"""# Quality Analysis Integration for {self.project_type}
# Add these targets to your Makefile

.PHONY: quality quality-full quality-report quality-clean

# Quality analysis targets
quality: ## Run basic quality analysis
\t@echo "🔍 Running quality analysis..."
\tpython quality/analyze.py . --summary

quality-full: ## Run comprehensive quality analysis
\t@echo "🔍 Running comprehensive quality analysis..."
\tpython quality/analyze.py . --output reports/quality_report.json

quality-report: ## Generate quality report in multiple formats
\t@echo "📊 Generating quality reports..."
\tpython quality/analyze.py . --output reports/quality_report.json --format json
\tpython quality/analyze.py . --output reports/quality_report.html --format html
\tpython quality/analyze.py . --output reports/quality_report.md --format markdown

quality-clean: ## Clean quality analysis reports
\t@echo "🧹 Cleaning quality reports..."
\trm -rf reports/quality_*

# Tool-specific targets
quality-patterns: ## Run pattern detection
\tpython quality/analyze.py . --tools pattern_detector --output reports/pattern_analysis.json

quality-architecture: ## Run architectural validation
\tpython quality/analyze.py . --tools architectural_validator --output reports/architectural_analysis.json

quality-performance: ## Run performance analysis
\tpython quality/analyze.py . --tools performance_detector --output reports/performance_analysis.json

quality-security: ## Run security analysis
\tpython quality/analyze.py . --tools security_scanner --output reports/security_analysis.json

quality-smells: ## Run code smell detection
\tpython quality/analyze.py . --tools code_smell_detector --output reports/smell_analysis.json

quality-gates: ## Run integration quality gates
\tpython quality/analyze.py . --tools integration_gates --output reports/integration_analysis.json

# CI/CD integration
quality-ci: ## Run quality analysis for CI/CD
\tpython quality/analyze.py . --config strict --output reports/ci_quality_report.json
\t@if [ $$(python quality/analyze.py . --config strict --summary | grep -o "Quality Score: [0-9]*" | grep -o "[0-9]*") -lt 80 ]; then \\
\t\techo "❌ Quality score below threshold"; \\
\t\texit 1; \\
\tfi
"""

    def _get_cli_integration(self) -> str:
        """
        Get CLI integration content.
        """
        return f'''"""
CLI integration for {self.project_type} quality analysis
"""

import argparse
import sys
from pathlib import Path

def add_quality_commands(parser):
    """Add quality analysis commands to CLI parser"""

    # Quality subparser
    quality_parser = parser.add_subparsers(dest='quality_command', help='Quality analysis commands')

    # Basic quality analysis
    quality_parser.add_parser('analyze', help='Run quality analysis')

    # Tool-specific commands
    quality_parser.add_parser('patterns', help='Run pattern detection')
    quality_parser.add_parser('architecture', help='Run architectural validation')
    quality_parser.add_parser('performance', help='Run performance analysis')
    quality_parser.add_parser('security', help='Run security analysis')
    quality_parser.add_parser('smells', help='Run code smell detection')
    quality_parser.add_parser('gates', help='Run integration quality gates')

    # Report commands
    quality_parser.add_parser('report', help='Generate quality report')
    quality_parser.add_parser('summary', help='Show quality summary')

def handle_quality_command(args):
    """Handle quality analysis commands"""
    quality_script = Path(__file__).parent / 'analyze.py'

    if args.quality_command == 'analyze':
        cmd = [str(quality_script), args.path or '.']
    elif args.quality_command == 'patterns':
        cmd = [str(quality_script), args.path or '.', '--tools', 'pattern_detector']
    elif args.quality_command == 'architecture':
        cmd = [str(quality_script), args.path or '.', '--tools', 'architectural_validator']
    elif args.quality_command == 'performance':
        cmd = [str(quality_script), args.path or '.', '--tools', 'performance_detector']
    elif args.quality_command == 'security':
        cmd = [str(quality_script), args.path or '.', '--tools', 'security_scanner']
    elif args.quality_command == 'smells':
        cmd = [str(quality_script), args.path or '.', '--tools', 'code_smell_detector']
    elif args.quality_command == 'gates':
        cmd = [str(quality_script), args.path or '.', '--tools', 'integration_gates']
    elif args.quality_command == 'report':
        cmd = [str(quality_script), args.path or '.', '--output', 'reports/quality_report.json']
    elif args.quality_command == 'summary':
        cmd = [str(quality_script), args.path or '.', '--summary']
    else:
        print(f"Unknown quality command: {args.quality_command}")
        return 1

    # Add additional arguments
    if hasattr(args, 'output') and args.output:
        cmd.extend(['--output', args.output])
    if hasattr(args, 'format') and args.format:
        cmd.extend(['--format', args.format])
    if hasattr(args, 'severity') and args.severity:
        cmd.extend(['--severity', args.severity])

    # Execute command
    import subprocess
    return subprocess.run(cmd).returncode

# Example integration in main CLI
def integrate_with_main_cli():
    """Example of how to integrate with main CLI"""
    parser = argparse.ArgumentParser(description='{self.project_type} CLI')
    parser.add_argument('command', help='Command to execute')
    parser.add_argument('path', nargs='?', default='.', help='Path to analyze')

    # Add quality commands
    add_quality_commands(parser)

    args = parser.parse_args()

    if args.command == 'quality':
        return handle_quality_command(args)
    else:
        # Handle other commands
        pass
'''

    def _get_ci_integration(self) -> str:
        """
        Get CI/CD integration content.
        """
        return f'''#!/usr/bin/env python3
"""
CI/CD integration for {self.project_type} quality analysis
"""

import sys
import os
from pathlib import Path

def run_quality_checks():
    """Run quality checks for CI/CD"""
    quality_script = Path(__file__).parent / 'analyze.py'

    print("🔍 Running quality analysis for CI/CD...")

    # Run quality analysis with strict configuration
    result = os.system(f"python {{quality_script}} . --config strict --output reports/ci_quality_report.json")

    if result != 0:
        print("❌ Quality analysis failed")
        return False

    # Check quality score threshold
    print("📊 Checking quality score threshold...")

    # This would typically parse the JSON report and check thresholds
    # For now, we'll use a simple approach
    try:
        import json
        with open('reports/ci_quality_report.json', 'r') as f:
            report = json.load(f)

        quality_score = report.get('metrics', {{}}).get('quality_score', 0)
        threshold = 80.0  # CI threshold

        if quality_score < threshold:
            print(f"❌ Quality score {{quality_score:.1f}} below threshold {{threshold}}")
            return False

        print(f"✅ Quality score {{quality_score:.1f}} meets threshold {{threshold}}")
        return True

    except Exception as e:
        print(f"❌ Error checking quality score: {{e}}")
        return False

def main():
    """Main CI/CD entry point"""
    success = run_quality_checks()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
'''


def integrate_quality_framework(
    project_path: str | Path, project_type: str = "pheno-sdk",
) -> bool:
    """
    Integrate quality framework into a project.
    """
    integration = QualityFrameworkIntegration(project_type)
    return integration.setup_for_project(project_path)


def export_framework_for_project(project_type: str, output_path: str | Path) -> bool:
    """
    Export framework specifically for a project type.
    """
    framework_path = Path(__file__).parent
    return export_quality_framework(framework_path, output_path)


# Example usage
if __name__ == "__main__":
    # Integrate with pheno-sdk
    integrate_quality_framework(".", "pheno-sdk")

    # Export framework for zen-mcp-server
    export_framework_for_project("zen-mcp", "./exports/zen-mcp-quality")

    # Export framework for atoms_mcp-old
    export_framework_for_project("atoms-mcp", "./exports/atoms-mcp-quality")
