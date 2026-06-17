---
layout: doc
title: Hello World Story
---

# Hello World: Your First Cmdra Operation

<StoryHeader
    title="First Operation"
    duration="2"
    difficulty="beginner"
    :gif="'/gifs/cmdra-hello-world.gif'"
/>

## Objective

Execute your first Cmdra operation successfully.

## Prerequisites

- Rust/Node/Python installed
- Cmdra CLI installed

## Implementation

```rust
use cmdra::Client;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = Client::new().await?;
    let result = client.hello().await?;
    println!("Success: {}", result);
    Ok(())
}
```

## Expected Output

```
Success: Hello from Cmdra!
```

## Next Steps

- [Core Integration](./core-integration)
- [API Reference](../reference/api)
