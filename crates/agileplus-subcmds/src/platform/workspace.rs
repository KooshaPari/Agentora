//! Resolve the AgilePlus repo root and `process-compose.yml` so CLI commands work from any cwd.
//!
//! Set **`AGILEPLUS_ROOT`** to the repository root if you are outside the tree (optional).

use std::path::{Path, PathBuf};

use anyhow::{Result, anyhow};

/// Find a directory containing `process-compose.yml` by walking parents from `current_dir`.
pub(crate) fn find_agileplus_root_from_walk() -> Option<PathBuf> {
    let mut dir = std::env::current_dir().ok()?;
    loop {
        if dir.join("process-compose.yml").is_file() {
            return Some(dir);
        }
        dir = dir.parent()?.to_path_buf();
    }
}

/// Returns `(workdir, compose_file_path_for -f)` — both canonical for `process-compose`.
///
/// - If `config` is absolute, workdir is its parent.
/// - Otherwise resolves via **`AGILEPLUS_ROOT`** env or walking up from cwd to find `process-compose.yml`.
pub(crate) fn resolve_platform_compose(config: &str) -> Result<(PathBuf, PathBuf)> {
    let path = Path::new(config);
    if path.is_absolute() {
        let compose = path.to_path_buf();
        let meta = compose
            .metadata()
            .map_err(|e| anyhow!("compose file: {e}"))?;
        if !meta.is_file() {
            return Err(anyhow!(
                "compose file does not exist: {}",
                compose.display()
            ));
        }
        let workdir = compose
            .parent()
            .ok_or_else(|| anyhow!("invalid compose path"))?
            .to_path_buf();
        return Ok((workdir, compose));
    }

    let root = std::env::var("AGILEPLUS_ROOT")
        .ok()
        .map(PathBuf::from)
        .filter(|r| r.join(config).is_file())
        .or_else(find_agileplus_root_from_walk)
        .ok_or_else(|| {
            anyhow!(
                "Could not find AgilePlus repo root (looking for `{}`).\n\
                 cd into the AgilePlus clone, or set AGILEPLUS_ROOT to the repo root.",
                config
            )
        })?;

    let compose = root.join(config);
    if !compose.is_file() {
        return Err(anyhow!("compose file not found: {}", compose.display()));
    }
    let compose = compose
        .canonicalize()
        .map_err(|e| anyhow!("compose path: {e}"))?;
    let workdir = compose
        .parent()
        .ok_or_else(|| anyhow!("invalid compose path"))?
        .to_path_buf();
    Ok((workdir, compose))
}
