"""
Project creation and scaffolding commands.
"""

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from ..core import PhenoContext
from ..templates import TemplateManager
from ..utils.exceptions import PhenoError
from ..utils.git import init_git_repo

console = Console()


def _get_context_integrations(ctx: PhenoContext) -> dict:
    """
    Get context-specific integration configuration.
    """
    integrations = {}

    if ctx.context_config and ctx.context_config.integrations:
        for name, config in ctx.context_config.integrations.items():
            if config.get("enabled", False):
                integrations[f"enable_{name}"] = True
                integrations[f"{name}_config"] = config

    return integrations


def _show_context_next_steps(ctx: PhenoContext, project_name: str):
    """
    Show context-specific next steps.
    """
    console.print(f"\n[bold]Next steps for {ctx.current_context} project:[/bold]")
    console.print(f"  cd {project_name}")

    if ctx.current_context == "atoms":
        console.print("  python -m venv venv")
        console.print("  source venv/bin/activate")
        console.print("  pip install -e .")
        console.print("  atoms setup auth --provider=authkit")
        console.print("  atoms dev server")

    elif ctx.current_context == "zen":
        console.print("  python -m venv venv")
        console.print("  source venv/bin/activate")
        console.print("  pip install -e .")
        console.print("  zen setup providers --openai")
        console.print("  zen dev server")

    elif ctx.current_context == "byteport":
        console.print("  npm install")
        console.print("  byteport setup platform")
        console.print("  byteport dev start")

    else:
        console.print("  python -m venv venv")
        console.print("  source venv/bin/activate")
        console.print("  pip install -e .")
        console.print("  pheno setup dev")


def project(
    ctx: PhenoContext,
    name: str,
    template: str | None,
    directory: Path | None,
    description: str | None,
    author: str | None,
    license: str | None,
    python_version: str | None,
    interactive: bool,
    force: bool,
):
    """
    Create a new project.
    """

    # Determine context-specific project creation
    context_name = ctx.current_context
    context_info = ctx.get_context_info()

    console.print(f"[bold green]🚀 Creating new {context_name} project: {name}[/bold green]")
    console.print(f"[bold]Context:[/bold] {context_info.get('display_name', context_name)}")

    # Initialize template manager with context-aware paths
    template_manager = TemplateManager(
        base_templates_dir=ctx.templates_dir,
        context_templates_dir=ctx.context_templates_dir,
        shared_templates_dir=ctx.shared_templates_dir,
    )

    # Determine template with context defaults
    if not template:
        # Use context-specific default template
        if ctx.context_config and ctx.context_config.default_template:
            template = ctx.context_config.default_template
        else:
            template = ctx.config.templates.default

    if (interactive or not template) and not template:
        available_templates = template_manager.list_templates()
        console.print(f"\n[bold]Available templates for {context_name}:[/bold]")
        for i, (tmpl_name, tmpl_desc) in enumerate(available_templates.items(), 1):
            console.print(f"  {i}. [cyan]{tmpl_name}[/cyan] - {tmpl_desc}")

        # Get default template for context
        default_template = template or (
            ctx.context_config.default_template
            if ctx.context_config
            else ctx.config.templates.default
        )

        template_choice = Prompt.ask(
            f"\nSelect template for {context_name} project",
            choices=list(available_templates.keys()),
            default=default_template,
        )
        template = template_choice

    # Determine target directory
    if not directory:
        directory = Path.cwd() / name

    # Check if directory exists
    if directory.exists() and not force:
        if interactive:
            if not Confirm.ask(f"Directory {directory} exists. Continue anyway?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                return
        else:
            raise PhenoError(
                f"Directory {directory} already exists. Use --force to overwrite.",
                hint="Use --force to overwrite or choose a different name",
            )

    # Interactive prompts for missing information
    if interactive:
        if not description:
            description = Prompt.ask("Project description", default="")

        if not author:
            author = Prompt.ask("Author", default=ctx.config.default_author)

        if not license:
            license = Prompt.ask("License", default=ctx.config.default_license)

        if not python_version:
            python_version = Prompt.ask(
                "Minimum Python version", default=ctx.config.dev.default_python_version,
            )

    # Set defaults
    description = description or f"A new pheno-sdk project: {name}"
    author = author or ctx.config.default_author
    license = license or ctx.config.default_license
    python_version = python_version or ctx.config.dev.default_python_version

    # Create project context with context-specific variables
    project_context = {
        "project_name": name,
        "project_description": description,
        "author": author,
        "license": license,
        "python_version": python_version,
        "context": ctx.current_context,
        "context_name": context_info.get("display_name", ctx.current_context),
        "context_description": context_info.get("description", ""),
        # Add context-specific integrations
        **_get_context_integrations(ctx),
    }

    try:
        # Generate project from template
        console.print(f"\n[bold]📁 Creating project directory: {directory}[/bold]")
        template_manager.generate_project(template, directory, project_context)

        # Initialize git repository if enabled
        if ctx.config.dev.auto_setup_git:
            console.print("\n[bold]🔧 Initializing git repository[/bold]")
            init_git_repo(directory)

        # Success message
        console.print(
            f"\n[bold green]✅ {context_name.title()} project '{name}' created successfully![/bold green]",
        )
        console.print(f"\n[bold]📍 Location:[/bold] {directory}")

        # Show context-specific next steps
        _show_context_next_steps(ctx, name)

    except Exception as e:
        raise PhenoError(f"Failed to create project: {e}")


def template(ctx: PhenoContext, name: str, source: str, description: str | None):
    """
    Add a custom project template.
    """

    console.print(f"[bold green]📄 Adding custom template: {name}[/bold green]")

    template_manager = TemplateManager(ctx.templates_dir)

    try:
        template_manager.add_template(name, source, description)
        console.print(f"[bold green]✅ Template '{name}' added successfully![/bold green]")

        # Update configuration
        ctx.config.templates.sources[name] = source
        from ..core.config import save_config

        save_config(ctx.config)

    except Exception as e:
        raise PhenoError(f"Failed to add template: {e}")


def list_templates(ctx: PhenoContext):
    """
    List available project templates.
    """

    template_manager = TemplateManager(ctx.templates_dir)
    templates = template_manager.list_templates()

    console.print("\n[bold]Available Project Templates:[/bold]")
    console.print("=" * 50)

    for name, description in templates.items():
        is_default = " [dim](default)[/dim]" if name == ctx.config.templates.default else ""
        console.print(f"[cyan]{name}[/cyan]{is_default}")
        console.print(f"  {description}")
        console.print()

    if not templates:
        console.print("[yellow]No templates found[/yellow]")
        console.print(
            "Add templates with: [cyan]pheno create template <name> --source <path>[/cyan]",
        )
