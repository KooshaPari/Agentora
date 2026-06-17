package hooks

import (
	"embed"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
)

//go:embed scripts/*
var hookScripts embed.FS

// hookNames lists the hook scripts to install.
var hookNames = []string{"commit-msg", "pre-commit", "pre-push"}

// InstallHooks copies hook scripts into <repoPath>/.git/hooks/ and marks them executable.
// If a hook already exists and force is false, that hook is skipped with a warning.
func InstallHooks(repoPath string, force bool) error {
	hooksDir := filepath.Join(repoPath, ".git", "hooks")
	if err := os.MkdirAll(hooksDir, 0o755); err != nil {
		return fmt.Errorf("create hooks dir: %w", err)
	}

	for _, name := range hookNames {
		dest := filepath.Join(hooksDir, name)

		if !force {
			if _, err := os.Stat(dest); err == nil {
				fmt.Printf("WARNING: hook %q already exists, skipping (use --force to overwrite)\n", name)
				continue
			}
		}

		src, err := hookScripts.Open(filepath.Join("scripts", name))
		if err != nil {
			return fmt.Errorf("open embedded hook %q: %w", name, err)
		}
		data, err := io.ReadAll(src)
		src.Close()
		if err != nil {
			return fmt.Errorf("read embedded hook %q: %w", name, err)
		}

		if err := os.WriteFile(dest, data, 0o755); err != nil {
			return fmt.Errorf("write hook %q: %w", name, err)
		}
		fmt.Printf("Installed hook: %s\n", dest)
	}
	return nil
}

// UninstallHooks removes hook scripts installed by InstallHooks.
func UninstallHooks(repoPath string) error {
	hooksDir := filepath.Join(repoPath, ".git", "hooks")
	for _, name := range hookNames {
		dest := filepath.Join(hooksDir, name)
		if err := os.Remove(dest); err != nil && !os.IsNotExist(err) {
			return fmt.Errorf("remove hook %q: %w", name, err)
		}
	}
	return nil
}

// IsInstalled returns true if all hooks are present in <repoPath>/.git/hooks/.
func IsInstalled(repoPath string) bool {
	hooksDir := filepath.Join(repoPath, ".git", "hooks")
	for _, name := range hookNames {
		if _, err := os.Stat(filepath.Join(hooksDir, name)); err != nil {
			return false
		}
	}
	return true
}

// ensure embed.FS satisfies fs.FS at compile time
var _ fs.FS = hookScripts
