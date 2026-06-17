"""
Project utilities that integrate with our existing CI/CD setup.
"""

import importlib.util
from pathlib import Path


def load_setup_project_module(templates_dir: Path):
    """
    Dynamically load the setup_project.py module.
    """
    setup_script = templates_dir / "setup_project.py"

    if not setup_script.exists():
        raise FileNotFoundError(f"setup_project.py not found in {templates_dir}")

    # Load the module dynamically
    spec = importlib.util.spec_from_file_location("setup_project", setup_script)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load setup_project.py from {setup_script}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module.ProjectSetup


class ProjectSetup:
    """
    Wrapper for our existing ProjectSetup class.
    """

    def __init__(self, templates_dir: Path):
        """
        Initialize with templates directory.
        """
        self.templates_dir = templates_dir

        # Load the ProjectSetup class from our existing setup_project.py
        try:
            ProjectSetupClass = load_setup_project_module(templates_dir)
            self.setup = ProjectSetupClass(templates_dir)
        except Exception as e:
            raise ImportError(f"Failed to load ProjectSetup: {e}")

    def setup_full_project(
        self,
        project_name: str,
        project_dir: Path,
        project_version: str = "0.1.0",
        project_description: str = "",
        keywords: str = "",
    ) -> bool:
        """
        Setup complete standardized CI/CD for a project.
        """
        return self.setup.setup_full_project(
            project_name=project_name,
            project_dir=project_dir,
            project_version=project_version,
            project_description=project_description,
            keywords=keywords,
        )

    def copy_template(
        self, template_path: Path, target_path: Path, replace_placeholders: bool = True,
    ) -> bool:
        """
        Copy a template file to target location.
        """
        return self.setup.copy_template(template_path, target_path, replace_placeholders)

    def set_replacements(
        self,
        project_name: str,
        project_version: str = "0.1.0",
        project_description: str = "",
        keywords: str = "",
    ):
        """
        Set template replacement variables.
        """
        self.setup.set_replacements(project_name, project_version, project_description, keywords)
