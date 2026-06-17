# ADR-001: Hexagonal Architecture for clikit

## Status
Accepted

## Context
We need to build a CLI framework that is:
- Testable without external dependencies
- Extensible via plugins
- Maintainable over time
- Usable across multiple use cases

## Decision
We will use hexagonal (ports & adapters) architecture with the following layers:

1. **Domain** - Pure business logic with zero external dependencies
   - Entities (Command, Argument, Option, Flag)
   - Value Objects (Input, Output, Context)
   - Ports (interfaces)
   - Services

2. **Application** - Use cases orchestrating domain logic
   - Commands (write operations)
   - Queries (read operations)
   - Services

3. **Adapters** - Implementations of ports
   - Primary (driving): CLI parser
   - Secondary (driven): Config, Logging

4. **Infrastructure** - Cross-cutting concerns
   - Error handling
   - Logging
   - Tracing

## Consequences

### Positive
- Domain logic is completely testable
- Easy to swap adapters (e.g., different CLI parsers)
- Clear boundaries between layers
- Plugins can access domain without coupling to infrastructure

### Negative
- More abstraction than a simple CLI tool
- Initial setup is more complex
- Developers need to understand the architecture

## References
- Alistair Cockburn: Hexagonal Architecture
- Robert C. Martin: Clean Architecture
