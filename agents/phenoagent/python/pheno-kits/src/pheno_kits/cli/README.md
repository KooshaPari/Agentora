# CLI-Builder-Kit 🖥️

Simple CLI framework with commands and argument parsing.

## Quick Start

```python
from cli_builder import CLI

cli = CLI(name="mytool", description="My CLI tool")

@cli.command("greet", description="Greet someone", args=["name"])
async def greet(name: str):
    print(f"Hello, {name}!")

@cli.command("config", description="Show config")
async def config():
    print("Config settings...")

# Run
await cli.run()  # or cli.run(["greet", "Alice"])
```

## Features

- Command registration with decorators
- Automatic help generation
- Argument parsing
- Async support
