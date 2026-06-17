"""
Configuration management commands.
"""

from rich.console import Console
from rich.table import Table

from ..core import PhenoContext
from ..core.config import save_config
from ..utils.exceptions import PhenoError

console = Console()


def set_config(ctx: PhenoContext, key: str, value: str):
    """
    Set configuration value.
    """

    console.print(f"[bold green]🔧 Setting config: {key} = {value}[/bold green]")

    try:
        # Parse nested keys like "ui.theme"
        keys = key.split(".")
        config_obj = ctx.config

        # Navigate to the correct nested object
        for k in keys[:-1]:
            if hasattr(config_obj, k):
                config_obj = getattr(config_obj, k)
            else:
                raise PhenoError(f"Configuration key '{k}' not found")

        # Set the final value
        final_key = keys[-1]
        if hasattr(config_obj, final_key):
            # Convert value to appropriate type
            current_value = getattr(config_obj, final_key)
            if isinstance(current_value, bool):
                value = value.lower() in ("true", "1", "yes", "on")
            elif isinstance(current_value, int):
                value = int(value)

            setattr(config_obj, final_key, value)
            save_config(ctx.config)
            console.print(f"[green]✅ Configuration updated: {key} = {value}[/green]")
        else:
            raise PhenoError(f"Configuration key '{final_key}' not found")

    except Exception as e:
        raise PhenoError(f"Failed to set configuration: {e}")


def get_config(ctx: PhenoContext, key: str | None):
    """
    Get configuration value(s).
    """

    if key:
        # Get specific key
        try:
            keys = key.split(".")
            config_obj = ctx.config

            for k in keys:
                config_obj = getattr(config_obj, k)

            console.print(f"[cyan]{key}:[/cyan] {config_obj}")

        except AttributeError:
            raise PhenoError(f"Configuration key '{key}' not found")
    else:
        # Show all configuration
        config_dict = ctx.config.dict()

        table = Table(title="Pheno CLI Configuration")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        def add_nested_config(obj, prefix=""):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    add_nested_config(v, full_key)
                else:
                    table.add_row(full_key, str(v))

        add_nested_config(config_dict)
        console.print(table)


def reset_config(ctx: PhenoContext):
    """
    Reset configuration to defaults.
    """

    console.print("[bold yellow]⚠️  Resetting configuration to defaults...[/bold yellow]")

    from ..core.config import PhenoConfig

    ctx.config = PhenoConfig()  # Create new config with defaults
    save_config(ctx.config)

    console.print("[green]✅ Configuration reset to defaults[/green]")
