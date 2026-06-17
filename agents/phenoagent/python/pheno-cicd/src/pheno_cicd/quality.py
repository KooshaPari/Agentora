"""
Quality integration for CI/CD pipelines.
"""

import json
from typing import Any

from .core import CICDPipeline, ProjectType
from .ports import CICDQualityProvider


class QualityGateIntegrator(CICDQualityProvider):
    """
    Quality gate integrator for CI/CD pipelines.
    """

    def __init__(self):
        self.quality_configs = self._load_quality_configs()

    def _load_quality_configs(self) -> dict[ProjectType, dict[str, Any]]:
        """
        Load quality configurations for each project type.
        """
        configs = {}

        # Pheno-SDK quality configuration
        configs[ProjectType.PHENO_SDK] = {
            "quality_score_threshold": 80.0,
            "coverage_threshold": 65.0,
            "loc_threshold": 70000,
            "complexity_threshold": 10,
            "max_violations": 50,
            "max_warnings": 100,
            "max_errors": 10,
            "enabled_checks": [
                "pattern_detector",
                "architectural_validator",
                "performance_detector",
                "security_scanner",
                "code_smell_detector",
                "integration_gates",
                "atlas_health",
            ],
            "quality_gates": [
                "coverage_gate",
                "complexity_gate",
                "security_gate",
                "performance_gate",
                "maintainability_gate",
            ],
        }

        # Zen-MCP-Server quality configuration
        configs[ProjectType.ZEN_MCP_SERVER] = {
            "quality_score_threshold": 75.0,
            "coverage_threshold": 75.0,
            "loc_threshold": 50000,
            "complexity_threshold": 15,
            "max_violations": 75,
            "max_warnings": 150,
            "max_errors": 15,
            "enabled_checks": [
                "pattern_detector",
                "architectural_validator",
                "performance_detector",
                "security_scanner",
                "code_smell_detector",
                "integration_gates",
            ],
            "quality_gates": [
                "coverage_gate",
                "complexity_gate",
                "security_gate",
                "performance_gate",
            ],
        }

        # Atoms-MCP-Old quality configuration
        configs[ProjectType.ATOMS_MCP_OLD] = {
            "quality_score_threshold": 70.0,
            "coverage_threshold": 70.0,
            "loc_threshold": 8500,
            "complexity_threshold": 20,
            "max_violations": 100,
            "max_warnings": 200,
            "max_errors": 25,
            "enabled_checks": [
                "pattern_detector",
                "architectural_validator",
                "performance_detector",
                "security_scanner",
                "code_smell_detector",
                "integration_gates",
            ],
            "quality_gates": ["coverage_gate", "complexity_gate", "security_gate"],
        }

        return configs

    def integrate_quality_checks(self, pipeline: CICDPipeline) -> CICDPipeline:
        """
        Integrate quality checks into pipeline.
        """
        quality_config = self.get_quality_config(pipeline.config.project_type)

        # Add quality stage to GitHub Actions workflow
        if ".github/workflows/ci.yml" in pipeline.files:
            workflow_content = pipeline.get_file(".github/workflows/ci.yml")
            if workflow_content:
                updated_workflow = self._add_quality_stage_to_workflow(
                    workflow_content, quality_config,
                )
                pipeline.add_file(".github/workflows/ci.yml", updated_workflow)

        # Add quality stage to other workflows
        for workflow_file in pipeline.files:
            if workflow_file.startswith(".github/workflows/") and workflow_file.endswith(".yml"):
                if workflow_file != ".github/workflows/ci.yml":
                    workflow_content = pipeline.get_file(workflow_file)
                    if workflow_content and "quality" not in workflow_content.lower():
                        updated_workflow = self._add_quality_stage_to_workflow(
                            workflow_content, quality_config,
                        )
                        pipeline.add_file(workflow_file, updated_workflow)

        # Add quality targets to Makefile
        if "Makefile" in pipeline.files:
            makefile_content = pipeline.get_file("Makefile")
            if makefile_content:
                updated_makefile = self._add_quality_targets_to_makefile(
                    makefile_content, quality_config,
                )
                pipeline.add_file("Makefile", updated_makefile)

        # Create quality configuration file
        quality_config_file = self._create_quality_config_file(quality_config)
        pipeline.add_file(".github/quality-config.json", quality_config_file)

        return pipeline

    def get_quality_config(self, project_type: ProjectType) -> dict[str, Any]:
        """
        Get quality configuration for project type.
        """
        return self.quality_configs.get(project_type, {})

    def validate_quality_integration(self, pipeline: CICDPipeline) -> list[str]:
        """
        Validate quality integration.
        """
        errors = []

        # Check if quality stage exists in workflows
        has_quality_stage = False
        for workflow_file in pipeline.files:
            if workflow_file.startswith(".github/workflows/") and workflow_file.endswith(".yml"):
                workflow_content = pipeline.get_file(workflow_file)
                if workflow_content and "quality:" in workflow_content:
                    has_quality_stage = True
                    break

        if not has_quality_stage:
            errors.append("No quality stage found in workflows")

        # Check if quality targets exist in Makefile
        if "Makefile" in pipeline.files:
            makefile_content = pipeline.get_file("Makefile")
            if makefile_content and "quality:" not in makefile_content:
                errors.append("No quality targets found in Makefile")

        # Check if quality configuration file exists
        if ".github/quality-config.json" not in pipeline.files:
            errors.append("Quality configuration file not found")

        return errors

    def update_quality_thresholds(
        self, pipeline: CICDPipeline, thresholds: dict[str, Any],
    ) -> CICDPipeline:
        """
        Update quality thresholds in pipeline.
        """
        # Update quality configuration
        if ".github/quality-config.json" in pipeline.files:
            quality_config_content = pipeline.get_file(".github/quality-config.json")
            if quality_config_content:
                try:
                    quality_config = json.loads(quality_config_content)
                    quality_config.update(thresholds)
                    updated_config = json.dumps(quality_config, indent=2)
                    pipeline.add_file(".github/quality-config.json", updated_config)
                except json.JSONDecodeError:
                    pass

        # Update workflow files
        for workflow_file in pipeline.files:
            if workflow_file.startswith(".github/workflows/") and workflow_file.endswith(".yml"):
                workflow_content = pipeline.get_file(workflow_file)
                if workflow_content:
                    updated_workflow = self._update_thresholds_in_workflow(
                        workflow_content, thresholds,
                    )
                    pipeline.add_file(workflow_file, updated_workflow)

        return pipeline

    def _add_quality_stage_to_workflow(
        self, workflow_content: str, quality_config: dict[str, Any],
    ) -> str:
        """
        Add quality stage to GitHub Actions workflow.
        """
        quality_stage = f"""
  quality:
    name: Quality Gates
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ env.PYTHON_VERSION }}}}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install ../pheno-sdk

      - name: Run quality analysis
        run: |
          python -c "
          from pheno.quality.manager import quality_manager
          from pheno.quality.config import get_config

          config = get_config('{quality_config.get('project_type', 'pheno-sdk')}')
          manager = quality_manager
          manager.config = config

          report = manager.analyze_project('.')
          summary = manager.generate_summary(report)

          print(f'Quality Score: {{summary[\"quality_score\"]:.1f}}/100')
          print(f'Total Issues: {{summary[\"total_issues\"]}}')

          if summary['quality_score'] < {quality_config.get('quality_score_threshold', 70)}:
              print('❌ Quality score below threshold')
              exit(1)
          else:
              print('✅ Quality score meets threshold')
          "

      - name: Upload quality report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: quality-report
          path: reports/quality_report.json
"""

        # Insert quality stage before build stage
        if "build:" in workflow_content:
            workflow_content = workflow_content.replace("build:", quality_stage + "\n  build:")
        else:
            # Add at the end before the last job
            lines = workflow_content.split("\n")
            insert_index = len(lines)
            for i, line in enumerate(lines):
                if line.startswith("  ") and ":" in line and not line.startswith("    "):
                    insert_index = i
                    break
            lines.insert(insert_index, quality_stage)
            workflow_content = "\n".join(lines)

        return workflow_content

    def _add_quality_targets_to_makefile(
        self, makefile_content: str, quality_config: dict[str, Any],
    ) -> str:
        """
        Add quality targets to Makefile.
        """
        quality_targets = f"""
quality: ## Run quality analysis
\tpython -c "
\tfrom pheno.quality.manager import quality_manager
\tfrom pheno.quality.config import get_config
\t
\tconfig = get_config('{quality_config.get('project_type', 'pheno-sdk')}')
\tmanager = quality_manager
\tmanager.config = config
\t
\treport = manager.analyze_project('.')
\tsummary = manager.generate_summary(report)
\t
\tprint(f'Quality Score: {{summary[\"quality_score\"]:.1f}}/100')
\tprint(f'Total Issues: {{summary[\"total_issues\"]}}')
\t
\tif summary['quality_score'] < {quality_config.get('quality_score_threshold', 70)}:
\t    print('❌ Quality score below threshold')
\t    exit(1)
\telse:
\t    print('✅ Quality score meets threshold')
\t"

quality-report: ## Generate quality report
\tpython -c "
\tfrom pheno.quality.manager import quality_manager
\tfrom pheno.quality.config import get_config
\t
\tconfig = get_config('{quality_config.get('project_type', 'pheno-sdk')}')
\tmanager = quality_manager
\tmanager.config = config
\t
\treport = manager.analyze_project('.', output_path='reports/quality_report.json')
\tsummary = manager.generate_summary(report)
\t
\tprint(f'Quality Score: {{summary[\"quality_score\"]:.1f}}/100')
\tprint(f'Total Issues: {{summary[\"total_issues\"]}}')
\tprint('Quality report saved to reports/quality_report.json')
\t"

quality-ci: ## Run quality checks for CI
\tpython -c "
\tfrom pheno.quality.manager import quality_manager
\tfrom pheno.quality.config import get_config
\t
\tconfig = get_config('{quality_config.get('project_type', 'pheno-sdk')}')
\tmanager = quality_manager
\tmanager.config = config
\t
\treport = manager.analyze_project('.')
\tsummary = manager.generate_summary(report)
\t
\tif summary['quality_score'] < {quality_config.get('quality_score_threshold', 70)}:
\t    print(f'❌ Quality score {{summary[\"quality_score\"]:.1f}} below threshold {quality_config.get('quality_score_threshold', 70)}')
\t    exit(1)
\telse:
\t    print(f'✅ Quality score {{summary[\"quality_score\"]:.1f}} meets threshold')
\t"
"""

        # Add quality targets before the help target
        if "help:" in makefile_content:
            makefile_content = makefile_content.replace("help:", quality_targets + "\nhelp:")
        else:
            # Add at the end
            makefile_content += quality_targets

        return makefile_content

    def _create_quality_config_file(self, quality_config: dict[str, Any]) -> str:
        """
        Create quality configuration file.
        """
        return json.dumps(quality_config, indent=2)

    def _update_thresholds_in_workflow(
        self, workflow_content: str, thresholds: dict[str, Any],
    ) -> str:
        """
        Update quality thresholds in workflow.
        """
        for key, value in thresholds.items():
            if key in workflow_content:
                # Replace threshold values in workflow
                pattern = f"{key}.*?\\d+"
                replacement = f"{key}: {value}"
                import re

                workflow_content = re.sub(pattern, replacement, workflow_content)

        return workflow_content


class QualityCheckConfig:
    """
    Quality check configuration.
    """

    def __init__(self, project_type: ProjectType, thresholds: dict[str, Any]):
        self.project_type = project_type
        self.thresholds = thresholds
        self.enabled_checks = thresholds.get("enabled_checks", [])
        self.quality_gates = thresholds.get("quality_gates", [])

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "project_type": self.project_type.value,
            "thresholds": self.thresholds,
            "enabled_checks": self.enabled_checks,
            "quality_gates": self.quality_gates,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QualityCheckConfig":
        """
        Create from dictionary.
        """
        return cls(project_type=ProjectType(data["project_type"]), thresholds=data["thresholds"])
