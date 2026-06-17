use std::path::PathBuf;

#[cfg(not(test))]
use std::process::Command;

/// Check whether `process-compose` is available in PATH.
pub(crate) fn find_process_compose() -> Option<PathBuf> {
    which_process_compose()
}

#[cfg(not(test))]
fn which_process_compose() -> Option<PathBuf> {
    // Try `which` / `where` via std
    let output = Command::new("which").arg("process-compose").output();
    if let Ok(out) = output {
        if out.status.success() {
            let path_str = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if !path_str.is_empty() {
                return Some(PathBuf::from(path_str));
            }
        }
    }
    // Fallback: check PATH entries manually
    if let Ok(path_env) = std::env::var("PATH") {
        for dir in path_env.split(':') {
            let candidate = std::path::Path::new(dir).join("process-compose");
            if candidate.exists() {
                return Some(candidate);
            }
        }
    }
    None
}

#[cfg(test)]
fn which_process_compose() -> Option<PathBuf> {
    // In tests, pretend process-compose is available so we can exercise code paths.
    Some(PathBuf::from("/usr/local/bin/process-compose"))
}
