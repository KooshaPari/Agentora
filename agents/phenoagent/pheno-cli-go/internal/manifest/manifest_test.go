package manifest

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadManifest(t *testing.T) {
	dir := t.TempDir()
	tomlContent := `
[[repos]]
name = "api"
language = "go"
registry = "go_proxy"
risk_profile = "low"
private = false
skip = false

[[repos]]
name = "frontend"
language = "typescript"
registry = "npm"
risk_profile = "medium"
private = true
skip = false
`
	manifestPath := filepath.Join(dir, "repos.toml")
	if err := os.WriteFile(manifestPath, []byte(tomlContent), 0644); err != nil {
		t.Fatalf("failed to write test manifest: %v", err)
	}

	m, err := LoadManifest(manifestPath)
	if err != nil {
		t.Fatalf("LoadManifest error: %v", err)
	}

	if len(m.Repos) != 2 {
		t.Fatalf("expected 2 repos, got %d", len(m.Repos))
	}
	if m.Repos[0].Name != "api" {
		t.Errorf("expected repos[0].Name=api, got %s", m.Repos[0].Name)
	}
	if m.Repos[1].Language != "typescript" {
		t.Errorf("expected repos[1].Language=typescript, got %s", m.Repos[1].Language)
	}
	if !m.Repos[1].Private {
		t.Errorf("expected repos[1].Private=true")
	}
}

func TestLoadManifest_NotFound(t *testing.T) {
	_, err := LoadManifest("/nonexistent/repos.toml")
	if err == nil {
		t.Fatal("expected error for missing file")
	}
}

func TestLoadManifest_Invalid(t *testing.T) {
	dir := t.TempDir()
	badPath := filepath.Join(dir, "repos.toml")
	if err := os.WriteFile(badPath, []byte("not valid toml [[["), 0644); err != nil {
		t.Fatalf("write: %v", err)
	}
	_, err := LoadManifest(badPath)
	if err == nil {
		t.Fatal("expected parse error")
	}
}

func TestGenerateManifest(t *testing.T) {
	dir := t.TempDir()

	// Create a Go repo
	goRepo := filepath.Join(dir, "my-service")
	if err := os.MkdirAll(goRepo, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(goRepo, "go.mod"), []byte("module example.com/my-service\ngo 1.21\n"), 0644); err != nil {
		t.Fatal(err)
	}

	// Create a TypeScript repo
	tsRepo := filepath.Join(dir, "my-frontend")
	if err := os.MkdirAll(tsRepo, 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(tsRepo, "package.json"), []byte(`{"name":"my-frontend"}`), 0644); err != nil {
		t.Fatal(err)
	}

	// Create a non-code dir (no manifest)
	emptyDir := filepath.Join(dir, "docs")
	if err := os.MkdirAll(emptyDir, 0755); err != nil {
		t.Fatal(err)
	}

	m, err := GenerateManifest(dir)
	if err != nil {
		t.Fatalf("GenerateManifest error: %v", err)
	}

	if len(m.Repos) != 2 {
		t.Fatalf("expected 2 repos, got %d: %+v", len(m.Repos), m.Repos)
	}

	found := map[string]string{}
	for _, r := range m.Repos {
		found[r.Name] = r.Language
	}
	if found["my-service"] != "go" {
		t.Errorf("expected my-service=go, got %s", found["my-service"])
	}
	if found["my-frontend"] != "typescript" {
		t.Errorf("expected my-frontend=typescript, got %s", found["my-frontend"])
	}
}

func TestGenerateManifest_EmptyDir(t *testing.T) {
	dir := t.TempDir()
	m, err := GenerateManifest(dir)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(m.Repos) != 0 {
		t.Errorf("expected 0 repos, got %d", len(m.Repos))
	}
}

func TestDetectLanguage(t *testing.T) {
	cases := []struct {
		file string
		lang string
	}{
		{"go.mod", "go"},
		{"Cargo.toml", "rust"},
		{"package.json", "typescript"},
		{"pyproject.toml", "python"},
	}
	for _, c := range cases {
		dir := t.TempDir()
		if err := os.WriteFile(filepath.Join(dir, c.file), []byte(""), 0644); err != nil {
			t.Fatal(err)
		}
		if got := detectLanguage(dir); got != c.lang {
			t.Errorf("file %s: expected %s, got %s", c.file, c.lang, got)
		}
	}
}
