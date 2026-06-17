package hooks

import (
	"os"
	"path/filepath"
	"testing"
)

func makeGitDir(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	gitHooks := filepath.Join(dir, ".git", "hooks")
	if err := os.MkdirAll(gitHooks, 0o755); err != nil {
		t.Fatalf("setup git dir: %v", err)
	}
	return dir
}

func TestInstallHooks(t *testing.T) {
	repoPath := makeGitDir(t)

	if err := InstallHooks(repoPath, false); err != nil {
		t.Fatalf("InstallHooks: %v", err)
	}

	hooksDir := filepath.Join(repoPath, ".git", "hooks")
	for _, name := range hookNames {
		path := filepath.Join(hooksDir, name)
		info, err := os.Stat(path)
		if err != nil {
			t.Errorf("hook %q not found: %v", name, err)
			continue
		}
		if info.Mode()&0o111 == 0 {
			t.Errorf("hook %q is not executable (mode %o)", name, info.Mode())
		}
	}
}

func TestInstallHooksIdempotent(t *testing.T) {
	repoPath := makeGitDir(t)

	if err := InstallHooks(repoPath, false); err != nil {
		t.Fatalf("first InstallHooks: %v", err)
	}

	// Write a sentinel to one hook to verify it is NOT overwritten
	sentinel := filepath.Join(repoPath, ".git", "hooks", "commit-msg")
	original, err := os.ReadFile(sentinel)
	if err != nil {
		t.Fatalf("read hook: %v", err)
	}
	if err := os.WriteFile(sentinel, append(original, []byte("# sentinel\n")...), 0o755); err != nil {
		t.Fatalf("write sentinel: %v", err)
	}

	// Second install without force should skip existing hooks
	if err := InstallHooks(repoPath, false); err != nil {
		t.Fatalf("second InstallHooks: %v", err)
	}

	after, err := os.ReadFile(sentinel)
	if err != nil {
		t.Fatalf("read after: %v", err)
	}
	if string(after) != string(original)+"# sentinel\n" {
		t.Error("existing hook was overwritten on second install (expected idempotent skip)")
	}
}

func TestUninstallHooks(t *testing.T) {
	repoPath := makeGitDir(t)

	if err := InstallHooks(repoPath, false); err != nil {
		t.Fatalf("InstallHooks: %v", err)
	}
	if !IsInstalled(repoPath) {
		t.Fatal("IsInstalled should be true after install")
	}

	if err := UninstallHooks(repoPath); err != nil {
		t.Fatalf("UninstallHooks: %v", err)
	}
	if IsInstalled(repoPath) {
		t.Error("IsInstalled should be false after uninstall")
	}

	hooksDir := filepath.Join(repoPath, ".git", "hooks")
	for _, name := range hookNames {
		path := filepath.Join(hooksDir, name)
		if _, err := os.Stat(path); !os.IsNotExist(err) {
			t.Errorf("hook %q still exists after uninstall", name)
		}
	}
}
