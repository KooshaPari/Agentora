# CLI Kit Usage Examples

## Basic CLI with Typer Backend

### Simple Command
```python
from pheno.kits.cli import CLI

cli = CLI(backend="typer")

@cli.command()
def hello(name: str):
    """Say hello to someone."""
    print(f"Hello, {name}!")

if __name__ == "__main__":
    cli.run()
```

```bash
$ python app.py hello John
Hello, John!
```

## Multiple Commands

```python
from pheno.kits.cli import CLI

cli = CLI(backend="typer", name="myapp", version="1.0.0")

@cli.command()
def init(project: str):
    """Initialize a new project."""
    print(f"Initializing project: {project}")

@cli.command()
def build(release: bool = False):
    """Build the project."""
    mode = "release" if release else "debug"
    print(f"Building in {mode} mode...")

@cli.command()
def deploy(env: str = "staging"):
    """Deploy to environment."""
    print(f"Deploying to {env}...")

if __name__ == "__main__":
    cli.run()
```

```bash
$ python app.py init my-project
Initializing project: my-project

$ python app.py build --release
Building in release mode...

$ python app.py deploy --env production
Deploying to production...
```

## Backend Switching

### Use Click Backend
```python
from pheno.kits.cli import CLI

cli = CLI(backend="click")

@cli.command()
def hello(name: str):
    """Say hello."""
    print(f"Hello, {name}!")

cli.run()
```

### Use Argparse Backend
```python
from pheno.kits.cli import CLI

cli = CLI(backend="argparse")

@cli.command()
def hello(name: str):
    """Say hello."""
    print(f"Hello, {name}!")

cli.run()
```

### Switch Backend Programmatically
```python
import os
from pheno.kits.cli import CLI

# Use typer in production, argparse in CI
backend = "typer" if os.getenv("ENV") == "prod" else "argparse"
cli = CLI(backend=backend)

@cli.command()
def deploy():
    """Deploy application."""
    print("Deploying...")

cli.run()
```

## Command Groups

```python
from pheno.kits.cli import CLI

cli = CLI(backend="typer")

# Database commands
@cli.group("db")
def db_group():
    """Database operations."""
    pass

@db_group.command("migrate")
def db_migrate():
    """Run database migrations."""
    print("Running migrations...")

@db_group.command("seed")
def db_seed():
    """Seed database with data."""
    print("Seeding database...")

# User commands
@cli.group("user")
def user_group():
    """User management."""
    pass

@user_group.command("create")
def user_create(email: str):
    """Create a new user."""
    print(f"Creating user: {email}")

@user_group.command("list")
def user_list():
    """List all users."""
    print("Listing users...")

if __name__ == "__main__":
    cli.run()
```

```bash
$ python app.py db migrate
Running migrations...

$ python app.py user create john@example.com
Creating user: john@example.com
```

## Type Validation

### Basic Types
```python
from pheno.kits.cli import CLI

cli = CLI(backend="typer")

@cli.command()
def process(
    count: int,
    rate: float,
    enabled: bool = True
):
    """Process with typed arguments."""
    print(f"Count: {count} (type: {type(count).__name__})")
    print(f"Rate: {rate} (type: {type(rate).__name__})")
    print(f"Enabled: {enabled} (type: {type(enabled).__name__})")

cli.run()
```

```bash
$ python app.py process 10 0.5 --enabled
Count: 10 (type: int)
Rate: 0.5 (type: float)
Enabled: True (type: bool)
```

### Complex Types
```python
from typing import List, Optional
from pheno.kits.cli import CLI

cli = CLI(backend="typer")

@cli.command()
def deploy(
    services: List[str],
    env: Optional[str] = None,
    tags: List[str] = []
):
    """Deploy services."""
    print(f"Services: {services}")
    print(f"Environment: {env}")
    print(f"Tags: {tags}")

cli.run()
```

```bash
$ python app.py deploy api worker --env prod --tags v1.0 stable
Services: ['api', 'worker']
Environment: prod
Tags: ['v1.0', 'stable']
```

## Options and Flags

### Options with Defaults
```python
from pheno.kits.cli import CLI

cli = CLI(backend="typer")

@cli.command()
def build(
    target: str = "release",
    optimize: bool = True,
    threads: int = 4
):
    """Build project with options."""
    print(f"Target: {target}")
    print(f"Optimize: {optimize}")
    print(f"Threads: {threads}")

cli.run()
```

### Required Options
```python
from pheno.kits.cli import CLI

cli = CLI(backend="typer")

@cli.command()
def connect(
    host: str,  # Required
    port: int = 5432,  # Optional with default
    password: str = None  # Optional
):
    """Connect to database."""
    print(f"Connecting to {host}:{port}")
    if password:
        print("Using password authentication")

cli.run()
```

## Help Text and Documentation

### Command Help
```python
from pheno.kits.cli import CLI

cli = CLI(backend="typer")

@cli.command()
def deploy(
    env: str = "staging",
    force: bool = False
):
    """
    Deploy application to environment.

    Args:
        env: Target environment (staging, production)
        force: Force deployment even with warnings
    """
    print(f"Deploying to {env}")

cli.run()
```

```bash
$ python app.py deploy --help
Usage: app.py deploy [OPTIONS]

  Deploy application to environment.

  Args:
      env: Target environment (staging, production)
      force: Force deployment even with warnings

Options:
  --env TEXT      [default: staging]
  --force         [default: False]
  --help          Show this message and exit.
```

## Decorators

### Using Core Decorators
```python
from pheno.kits.cli import CLI, command, argument, option

cli = CLI(backend="typer")

@command(cli)
@argument("name", help="Project name")
@option("--template", default="basic", help="Project template")
def init(name: str, template: str):
    """Initialize new project."""
    print(f"Creating {template} project: {name}")

cli.run()
```

## Advanced Usage

### Command Definition
```python
from pheno.kits.cli import CLI, CommandDefinition, ArgumentDefinition

cli = CLI(backend="typer")

# Define command programmatically
cmd_def = CommandDefinition(
    name="deploy",
    description="Deploy application",
    arguments=[
        ArgumentDefinition(
            name="service",
            type=str,
            required=True,
            help="Service to deploy"
        ),
        ArgumentDefinition(
            name="env",
            type=str,
            default="staging",
            help="Target environment"
        )
    ]
)

# Register command
cli.register_command(cmd_def)

cli.run()
```

### CLI Builder
```python
from pheno.kits.cli import CLIBuilder

builder = CLIBuilder()
builder.set_name("myapp")
builder.set_version("1.0.0")
builder.set_backend("typer")

# Add commands
builder.add_command(
    name="init",
    handler=lambda name: print(f"Initializing {name}"),
    description="Initialize project"
)

builder.add_command(
    name="build",
    handler=lambda: print("Building..."),
    description="Build project"
)

# Build and run
cli = builder.build()
cli.run()
```

## Error Handling

```python
from pheno.kits.cli import CLI

cli = CLI(backend="typer")

@cli.command()
def connect(host: str):
    """Connect to server."""
    try:
        # Connection logic
        print(f"Connecting to {host}...")
        if not host.startswith("https://"):
            raise ValueError("Host must use HTTPS")
        print("Connected!")
    except ValueError as e:
        print(f"Error: {e}")
        raise SystemExit(1)

cli.run()
```

## Context and State

```python
from pheno.kits.cli import CLI

cli = CLI(backend="typer")

# Shared context
context = {"verbose": False}

@cli.command()
def config(verbose: bool = False):
    """Configure application."""
    context["verbose"] = verbose
    print(f"Verbose mode: {verbose}")

@cli.command()
def deploy():
    """Deploy application."""
    if context.get("verbose"):
        print("Detailed deployment logs...")
    print("Deploying...")

cli.run()
```

## Custom Backend

```python
from pheno.kits.cli import CLI
from pheno.kits.cli.backends import register_backend

# Register custom backend
class CustomBackend:
    def __init__(self, cli):
        self.cli = cli

    def run(self, args=None):
        # Custom implementation
        print("Running custom backend...")

register_backend("custom", CustomBackend)

# Use custom backend
cli = CLI(backend="custom")
cli.run()
```

## Real-World Example

### Database CLI
```python
from pheno.kits.cli import CLI
from typing import Optional

cli = CLI(backend="typer", name="dbctl", version="1.0.0")

@cli.group("db")
def db():
    """Database operations."""
    pass

@db.command("init")
def db_init(driver: str = "postgresql"):
    """Initialize database."""
    print(f"Initializing {driver} database...")

@db.command("migrate")
def db_migrate(
    target: Optional[str] = None,
    rollback: bool = False
):
    """Run migrations."""
    if rollback:
        print(f"Rolling back to: {target or 'previous'}")
    else:
        print(f"Migrating to: {target or 'latest'}")

@db.command("seed")
def db_seed(clean: bool = False):
    """Seed database with data."""
    if clean:
        print("Cleaning existing data...")
    print("Seeding database...")

@cli.group("user")
def user():
    """User management."""
    pass

@user.command("create")
def user_create(
    email: str,
    admin: bool = False
):
    """Create new user."""
    role = "admin" if admin else "user"
    print(f"Creating {role}: {email}")

@user.command("list")
def user_list(limit: int = 10):
    """List users."""
    print(f"Listing {limit} users...")

@user.command("delete")
def user_delete(email: str, force: bool = False):
    """Delete user."""
    if not force:
        confirm = input(f"Delete {email}? (y/n): ")
        if confirm.lower() != "y":
            print("Cancelled")
            return
    print(f"Deleting user: {email}")

if __name__ == "__main__":
    cli.run()
```

```bash
$ python dbctl.py db init --driver mysql
Initializing mysql database...

$ python dbctl.py db migrate --rollback --target v1.0
Rolling back to: v1.0

$ python dbctl.py user create admin@example.com --admin
Creating admin: admin@example.com

$ python dbctl.py user list --limit 5
Listing 5 users...
```

## Best Practices

1. **Type Hints**: Always use type hints for automatic validation
2. **Help Text**: Write clear docstrings for commands
3. **Defaults**: Provide sensible defaults for options
4. **Groups**: Organize related commands into groups
5. **Error Handling**: Handle errors gracefully with try/except
6. **Backend Choice**:
   - Use `typer` for modern type-hint based CLIs
   - Use `click` for decorator-heavy CLIs
   - Use `argparse` for minimal dependencies
7. **Testing**: Test CLI commands independently of the runner
8. **Context**: Use context for shared state between commands
