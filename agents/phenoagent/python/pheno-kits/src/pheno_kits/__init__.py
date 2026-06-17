"""
Pheno Kits: Production-grade toolkit collection for rapid development.

The kits package provides a collection of battle-tested, framework-agnostic
utilities extracted from real-world production applications. Each kit is
designed to be:

- Standalone: No dependencies between kits
- Generic: No application-specific logic
- Well-tested: Extracted from production codebases
- Documented: Comprehensive examples and guides

Available Kits:

1. DB Kit (pheno.kits.db)
   Universal database abstraction with support for:
   - Supabase, PostgreSQL, Neon
   - Connection pooling (sync/async)
   - Migrations, RLS, multi-tenancy
   - Realtime subscriptions, storage

2. Deploy Kit (pheno.kits.deploy)
   Deployment orchestration across platforms:
   - Vercel, Fly.io, local processes
   - Health checks, hooks
   - Environment management
   - Package vendoring

3. CLI Kit (pheno.kits.cli)
   Framework-agnostic CLI builder:
   - argparse, click, typer backends
   - Unified interface
   - Type validation
   - Command composition

4. Infra Kit (pheno.kits.infra)
   Infrastructure orchestration:
   - Dynamic port allocation
   - Tunnel management
   - Service lifecycle
   - Process management
   - Smart proxy, fallback servers

Usage:
    # Import individual kits
    from pheno.kits.db import Database, SupabaseAdapter
    from pheno.kits.deploy import VercelClient, LocalServiceManager
    from pheno.kits.cli import CLI, Command
    from pheno.kits.infra import KInfra, ServiceOrchestrator

    # Or import everything
    from pheno.kits import db, deploy, cli, infra
"""

# Import all kits as submodules with graceful fallback
import sys

# Try to import each kit, with fallback for missing dependencies
try:
    from . import db
except ImportError as e:
    print(f"Warning: DB kit import failed: {e}", file=sys.stderr)
    db = None

try:
    from . import deploy
except ImportError as e:
    print(f"Warning: Deploy kit import failed: {e}", file=sys.stderr)
    deploy = None

try:
    from . import cli
except ImportError as e:
    if "cli_builder" in str(e):
        print("ℹ️  CLI kit partially loaded (cli_builder optional dependency not available)", file=sys.stderr)
    else:
        print(f"Warning: CLI kit import failed: {e}", file=sys.stderr)
    cli = None

try:
    from . import infra
except ImportError as e:
    print(f"Warning: Infra kit import failed: {e}", file=sys.stderr)
    infra = None

# Ensure we have at least infra for KINFRA
if infra is None:
    raise ImportError("Infra kit import failed - cannot initialize KINFRA")

__version__ = "0.1.0"

# Only export successfully imported kits
__all__ = []
if db is not None:
    __all__.append("db")
if deploy is not None:
    __all__.append("deploy")
if cli is not None:
    __all__.append("cli")
if infra is not None:
    __all__.append("infra")

# Kit metadata (only include successfully imported kits)
KITS = {}

if db is not None:
    KITS["db"] = {
        "name": "DB Kit",
        "description": "Universal database abstraction with RLS and multi-tenancy",
        "version": db.__version__,
        "module_count": 31,
        "loc": 2681,
    }

if deploy is not None:
    KITS["deploy"] = {
        "name": "Deploy Kit",
        "description": "Deployment orchestration for cloud and local platforms",
        "version": deploy.__version__,
        "module_count": 23,
        "loc": 4772,
    }

if cli is not None:
    KITS["cli"] = {
        "name": "CLI Kit",
        "description": "Framework-agnostic CLI construction toolkit",
        "version": cli.__version__,
        "module_count": 9,
        "loc": 2022,
    }

if infra is not None:
    KITS["infra"] = {
        "name": "Infra Kit",
        "description": "Cross-platform infrastructure orchestration",
        "version": infra.__version__,
        "module_count": 34,
        "loc": 9279,
    }


def list_kits():
    """
    List all available kits with metadata.
    """
    print("Pheno Kits - Available Toolkits:\n")
    for kit_id, metadata in KITS.items():
        print(f"  {metadata['name']} (pheno.kits.{kit_id})")
        print(f"    {metadata['description']}")
        print(f"    Version: {metadata['version']}")
        print(f"    Modules: {metadata['module_count']}")
        print(f"    LOC: {metadata['loc']:,}")
        print()


def get_kit_info(kit_name: str) -> dict:
    """Get metadata for a specific kit.

    Args:
        kit_name: Name of the kit (e.g., 'db', 'deploy', 'cli', 'infra')

    Returns:
        Dictionary containing kit metadata

    Raises:
        KeyError: If kit not found
    """
    return KITS[kit_name]
