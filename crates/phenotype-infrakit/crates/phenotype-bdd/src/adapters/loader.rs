use crate::BddError;

pub struct FileLoader;

impl std::fmt::Debug for FileLoader {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("FileLoader").finish()
    }
}

impl FileLoader {
    pub fn new() -> Self {
        Self
    }

    pub fn load_feature(&self, path: &str) -> Result<String, BddError> {
        std::fs::read_to_string(path).map_err(BddError::IoError)
    }

    pub fn load_features_in_dir(&self, dir: &str) -> Result<Vec<(String, String)>, BddError> {
        let entries = std::fs::read_dir(dir).map_err(BddError::IoError)?;
        let mut features = Vec::new();

        for entry in entries {
            let entry = entry.map_err(BddError::IoError)?;
            let path = entry.path();
            if path.extension().is_some_and(|e| e == "feature") {
                let content = std::fs::read_to_string(&path).map_err(BddError::IoError)?;
                let name = path.to_string_lossy().to_string();
                features.push((name, content));
            }
        }

        features.sort_by(|a, b| a.0.cmp(&b.0));
        Ok(features)
    }
}

impl Default for FileLoader {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    // Traces to: FR-BDD-050 - Load feature file
    #[test]
    fn test_load_feature_file() {
        let dir = std::env::temp_dir().join("bdd-loader-test");
        let _ = std::fs::create_dir_all(&dir);
        let path = dir.join("test.feature");
        {
            let mut f = std::fs::File::create(&path).unwrap();
            write!(f, "Feature: Loader Test").unwrap();
        }

        let loader = FileLoader::new();
        let content = loader.load_feature(path.to_str().unwrap()).unwrap();
        assert_eq!(content, "Feature: Loader Test");
        let _ = std::fs::remove_dir_all(&dir);
    }

    // Traces to: FR-BDD-051 - Load nonexistent file returns error
    #[test]
    fn test_load_nonexistent() {
        let loader = FileLoader::new();
        let result = loader.load_feature("/nonexistent/path.feature");
        assert!(matches!(result, Err(BddError::IoError(_))));
    }

    // Traces to: FR-BDD-052 - Load features from directory
    #[test]
    fn test_load_features_in_dir() {
        let dir = std::env::temp_dir().join("bdd-loader-dir-test");
        let _ = std::fs::create_dir_all(&dir);

        for name in &["b.feature", "a.feature"] {
            let mut f = std::fs::File::create(dir.join(name)).unwrap();
            write!(f, "Feature: {}", name).unwrap();
        }

        let loader = FileLoader::new();
        let features = loader.load_features_in_dir(dir.to_str().unwrap()).unwrap();
        assert_eq!(features.len(), 2);
        let _ = std::fs::remove_dir_all(&dir);
    }
}
