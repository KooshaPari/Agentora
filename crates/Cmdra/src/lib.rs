//! clikit - Universal CLI Framework
//!
//! A hexagonal architecture CLI framework for building robust, extensible
//! command-line applications.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod infrastructure;
pub mod plugins;

pub mod prelude {
    //! Re-exports commonly used types
    pub use crate::adapters::primary::cli::*;
    pub use crate::adapters::secondary::config::*;
    pub use crate::application::commands::DefaultHandler;
    pub use crate::application::queries::QueryHandler;
    pub use crate::domain::entities::{Argument, CliOption, Command, Flag};
    pub use crate::domain::events::*;
    pub use crate::domain::ports::{
        CliParser, CommandExecutor as CommandExecutorPort, CommandHandler as CommandHandlerPort,
        ConfigLoader, Logger, OutputFormatter, Persistence, Plugin, PluginLoader, Telemetry,
    };
    pub use crate::domain::services::{CommandRegistry, InputValidator};
    pub use crate::domain::value_objects::{
        ArgValue, Context, Input, Output, OutputContent, ParsedInput, Result,
    };
    pub use crate::infrastructure::{
        init_tracing, init_tracing_with_filter, SimpleLogger, TracingLogger,
    };
}

pub use application::commands::DefaultHandler;
pub use application::queries::QueryHandler;
pub use domain::entities::{Argument, CliOption, Command, Flag};
pub use domain::ports::{
    CliParser, CommandExecutor as CommandExecutorPort, CommandHandler as CommandHandlerPort,
    ConfigLoader, Logger, OutputFormatter, Persistence, Plugin, PluginLoader, Telemetry,
};
pub use domain::services::{CommandRegistry, InputValidator};
pub use domain::value_objects::{
    ArgValue, Context, Input, Output, OutputContent, ParsedInput, Result,
};
pub use infrastructure::{init_tracing, init_tracing_with_filter, SimpleLogger, TracingLogger};
