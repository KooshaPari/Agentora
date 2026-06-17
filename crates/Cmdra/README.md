# clikit - Universal CLI Framework

> Universal CLI framework with hexagonal architecture and plugin support.

## Overview

clikit is a general-purpose CLI framework designed for building robust, extensible command-line applications using hexagonal architecture principles.

## Features

- **Hexagonal Architecture**: Clean separation of domain logic from infrastructure
- **Plugin System**: Extensible command and output adapters
- **Multiple Input Sources**: Support for stdin, files, and environment variables
- **Structured Output**: JSON, YAML, TOML, and custom formatters
- **Built-in Utilities**: Common CLI patterns out of the box

## Architecture

```
clikit/
├── src/
│   ├── domain/           # Pure domain (no external deps)
│   │   ├── entities/     # Command, Option, Argument
│   │   ├── value_objects/# Input, Output, Result
│   │   ├── services/    # Domain services
│   │   └── ports/       # Domain interfaces
│   │
│   ├── application/      # Use cases
│   │   ├── commands/    # Command handlers
│   │   ├── queries/    # Query handlers
│   │   └── services/   # Application services
│   │
│   ├── adapters/        # Implementations
│   │   ├── primary/    # Driving adapters
│   │   │   ├── cli/    # CLI input parser
│   │   │   └── api/    # API input
│   │   └── secondary/  # Driven adapters
│   │       ├── config/ # Configuration
│   │       └── logging/# Logging
│   │
│   └── infrastructure/  # Cross-cutting
│
├── plugins/            # Plugin system
├── templates/          # CLI templates
└── examples/          # Example projects
```

## xDD Methodologies Applied

| Category | Methodology |
|----------|-------------|
| Development | TDD, BDD, DDD, ATDD, SDD |
| Design | SOLID, DRY, KISS, YAGNI |
| Architecture | Clean, Hexagonal, Onion |
| Quality | Property-Based Testing, Mutation Testing |
| Process | CI/CD, GitOps, Agile |

## Installation

```bash
cargo add clikit
```

## Quick Start

```rust
use clikit::prelude::*;
use clikit::domain::entities::{Command, Argument};
use clikit::application::commands::Handler;

struct HelloHandler;

impl Handler for HelloHandler {
    fn handle(&self, ctx: &Context) -> Result<Output, Error> {
        let name = ctx.get::<String>("name").unwrap_or("World".into());
        Ok(Output::text(format!("Hello, {}!", name)))
    }
}

fn main() {
    let app = Command::new("hello")
        .argument(Argument::new("name").optional())
        .handler(HelloHandler);

    CliKit::new(app).run();
}
```

## Documentation

- [API Documentation](https://docs.rs/clikit)
- [Book](https://clikit.dev/book)
- [Examples](./examples/)

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

MIT OR Apache-2.0
