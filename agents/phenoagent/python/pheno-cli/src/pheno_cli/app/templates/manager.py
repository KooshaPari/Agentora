"""
Template manager for project scaffolding.
"""

from pathlib import Path
from typing import Any


class TemplateManager:
    """
    Manages project templates for scaffolding.
    """

    def __init__(
        self,
        base_templates_dir: Path | None = None,
        context_templates_dir: Path | None = None,
        shared_templates_dir: Path | None = None,
        templates_dir: Path | None = None,  # Backward compatibility
    ):
        """Initialize with template directories.

        Args:
            base_templates_dir: Base templates directory
            context_templates_dir: Context-specific templates directory
            shared_templates_dir: Shared templates directory
            templates_dir: Legacy single templates directory for backward compatibility
        """
        if templates_dir:
            # Legacy single directory mode
            self.base_templates_dir = Path(templates_dir)
            self.context_templates_dir = None
            self.shared_templates_dir = None
        else:
            # Multi-directory context-aware mode
            self.base_templates_dir = Path(base_templates_dir) if base_templates_dir else None
            self.context_templates_dir = (
                Path(context_templates_dir) if context_templates_dir else None
            )
            self.shared_templates_dir = Path(shared_templates_dir) if shared_templates_dir else None

        # For backward compatibility
        self.templates_dir = self.base_templates_dir

    def list_templates(self) -> dict[str, str]:
        """
        List available project templates.
        """
        templates = {}

        # Add base templates
        base_templates = {
            "python-basic": "Basic Python project template",
            "api-gateway": "FastAPI-based API gateway service",
            "tui-app": "Terminal UI application using textual",
            "mcp-server": "MCP server with multiple model providers",
            "web-service": "Web service template",
            "cli-tool": "Command-line tool template",
            "data-processor": "Data processing toolkit",
            "monitor-service": "Monitoring and observability service",
            "auth-service": "Authentication service",
            "storage-service": "Storage management service",
            "workflow-engine": "Workflow orchestration engine",
        }
        templates.update(base_templates)

        # Add context-specific templates if available
        if self.context_templates_dir:
            context_templates = {
                "atoms-server": "Atoms FastMCP server template",
                "atoms-api": "Atoms API service template",
                "atoms-client": "Atoms client application template",
                "zen-server": "Zen multi-provider AI server template",
                "zen-api": "Zen AI API service template",
                "zen-client": "Zen AI client application template",
                "byteport-platform": "BytePort development platform template",
                "byteport-api": "BytePort API service template",
                "byteport-frontend": "BytePort frontend application template",
            }
            templates.update(context_templates)

        # Add shared templates if available
        if self.shared_templates_dir:
            shared_templates = {
                "docker-service": "Docker containerized service template",
                "k8s-deployment": "Kubernetes deployment template",
                "terraform-infra": "Terraform infrastructure template",
            }
            templates.update(shared_templates)

        return templates

    def generate_project(self, template_name: str, target_dir: Path, context: dict[str, Any]):
        """
        Generate a project from a template (legacy method).
        """
        return self.create_project(
            template_name, context["project_name"], target_dir.parent, context, dry_run=False,
        )

    def create_project(
        self,
        template: str,
        project_name: str,
        output_dir: Path,
        template_vars: dict[str, Any],
        dry_run: bool = False,
    ) -> list[Path]:
        """Create a project from template with context support.

        Returns:
            List of created files
        """
        target_dir = output_dir / project_name

        if not dry_run:
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)

        # For now, create a basic project structure
        # In a full implementation, this would use actual templates based on context

        return self._create_basic_structure(target_dir, template_vars, dry_run)

    def _create_basic_structure(
        self, target_dir: Path, context: dict[str, Any], dry_run: bool = False,
    ) -> list[Path]:
        """Create basic project structure.

        Returns:
            List of created files
        """
        created_files = []

        project_name = context.get("project_name", target_dir.name)
        project_description = context.get("project_description", "")
        context.get("author", "")
        license_type = context.get("license", "MIT")
        context.get("python_version", "3.10")

        # Get context-specific information
        project_context = context.get("context", "pheno")
        context_name = context.get("context_name", project_context)
        context_description = context.get("context_description", "")

        # Create package directory
        package_dir = target_dir / project_name.replace("-", "_")
        if not dry_run:
            package_dir.mkdir(exist_ok=True)

        # Create __init__.py
        init_file = package_dir / "__init__.py"
        init_content = f'"""\n{project_description or f"{context_name} project"}\n"""\n\n__version__ = "0.1.0"\n'
        if not dry_run:
            init_file.write_text(init_content)
        created_files.append(init_file)

        # Create basic module
        main_file = package_dir / "main.py"
        main_content = f'"""\nMain module for {project_name}.\n"""\n\n\ndef main():\n    """Main entry point."""\n    print("Hello from {project_name}!")\n\n\nif __name__ == "__main__":\n    main()\n'
        if not dry_run:
            main_file.write_text(main_content)
        created_files.append(main_file)

        # Create tests directory
        tests_dir = target_dir / "tests"
        if not dry_run:
            tests_dir.mkdir(exist_ok=True)

        tests_init_file = tests_dir / "__init__.py"
        if not dry_run:
            tests_init_file.write_text("")
        created_files.append(tests_init_file)

        test_main_file = tests_dir / "test_main.py"
        test_content = f'"""\nTests for {project_name}.\n"""\n\nfrom {package_dir.name} import main\n\n\ndef test_main():\n    """Test main function."""\n    # Basic test\n    assert True\n'
        if not dry_run:
            test_main_file.write_text(test_content)
        created_files.append(test_main_file)

        # Create README.md with context information
        readme_file = target_dir / "README.md"
        readme_content = f"""# {project_name}

{project_description or f"A {context_name} project"}

{context_description}

## Installation

```bash
pip install -e .
```

## Usage

```python
from {package_dir.name} import main

main()
```

## Development

```bash
# Setup development environment
{project_context} setup dev

# Run tests
{project_context} dev test

# Run linting
{project_context} dev lint
```

## License

{license_type}
"""
        if not dry_run:
            readme_file.write_text(readme_content)
        created_files.append(readme_file)

        return created_files

    def add_template(self, name: str, source: str, description: str | None = None):
        """
        Add a custom template.
        """
        # For now, just validate the name
        if not name.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Template name must be alphanumeric with hyphens/underscores")

        # In a full implementation, this would download/copy the template
        print(f"Template {name} would be added from {source}")
        return True
