//! `agent-platform-app` — the binary entry point.
//!
//! Wires concrete adapters into the application graph and starts the chosen
//! inbound transport. Today this is a thin shell; transport-specific wiring
//! is added as adapters land.

use clap::Parser;
use tracing_subscriber::EnvFilter;

#[derive(Parser, Debug)]
#[command(name = "agent-platform", version, about = "Phenotype agent/MCP monorepo binary")]
struct Args {
    /// Transport to serve on. One of: mcp-stdio, http.
    #[arg(long, default_value = "mcp-stdio")]
    transport: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .init();

    let args = Args::parse();
    tracing::info!(transport = %args.transport, "agent-platform starting");

    // TODO(agent-platform): construct the application graph and call
    // `transport.serve().await`.

    Ok(())
}
