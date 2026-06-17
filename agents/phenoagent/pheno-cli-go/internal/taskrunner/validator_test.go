package taskrunner

import (
	"os"
	"path/filepath"
	"testing"
)

func writeTempMiseToml(t *testing.T, content string) string {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "mise.toml")
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("writing temp mise.toml: %v", err)
	}
	return path
}

func TestValidateMiseConfig_AllRequired(t *testing.T) {
	content := `
[tasks.lint]
run = "golangci-lint run ./..."

[tasks.test]
run = "go test ./..."

[tasks.build]
run = "go build ./..."

[tasks.format]
run = "gofmt -w ."
`
	path := writeTempMiseToml(t, content)
	issues, err := ValidateMiseConfig(path)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if HasErrors(issues) {
		t.Errorf("expected no errors, got: %v", issues)
	}
}

func TestValidateMiseConfig_MissingRequired(t *testing.T) {
	// Missing "lint" and "format"
	content := `
[tasks.test]
run = "go test ./..."

[tasks.build]
run = "go build ./..."
`
	path := writeTempMiseToml(t, content)
	issues, err := ValidateMiseConfig(path)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !HasErrors(issues) {
		t.Fatal("expected errors for missing required tasks")
	}

	missing := map[string]bool{}
	for _, issue := range issues {
		if issue.Severity == SeverityError {
			missing[issue.Task] = true
		}
	}
	for _, required := range []string{"lint", "format"} {
		if !missing[required] {
			t.Errorf("expected error for missing task %q", required)
		}
	}
}

func TestValidateMiseConfig_EmptyRunCommand(t *testing.T) {
	content := `
[tasks.lint]
run = ""

[tasks.test]
run = "go test ./..."

[tasks.build]
run = "go build ./..."

[tasks.format]
run = "gofmt -w ."
`
	path := writeTempMiseToml(t, content)
	issues, err := ValidateMiseConfig(path)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !HasErrors(issues) {
		t.Fatal("expected error for empty run command")
	}

	found := false
	for _, issue := range issues {
		if issue.Task == "lint" && issue.Severity == SeverityError {
			found = true
		}
	}
	if !found {
		t.Error("expected error issue for task 'lint' with empty run")
	}
}

func TestValidateMiseConfig_ShorthandTasks(t *testing.T) {
	// Shorthand: tasks defined as plain strings
	content := `
[tasks]
lint = "golangci-lint run ./..."
test = "go test ./..."
build = "go build ./..."
format = "gofmt -w ."
audit = "govulncheck ./..."
`
	path := writeTempMiseToml(t, content)
	issues, err := ValidateMiseConfig(path)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if HasErrors(issues) {
		t.Errorf("expected no errors for shorthand tasks, got: %v", issues)
	}
}

func TestValidateMiseConfig_OptionalTasksWarn(t *testing.T) {
	// Only required tasks; all optional ones should produce warnings
	content := `
[tasks.lint]
run = "golangci-lint run ./..."

[tasks.test]
run = "go test ./..."

[tasks.build]
run = "go build ./..."

[tasks.format]
run = "gofmt -w ."
`
	path := writeTempMiseToml(t, content)
	issues, err := ValidateMiseConfig(path)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	warnTasks := map[string]bool{}
	for _, issue := range issues {
		if issue.Severity == SeverityWarning {
			warnTasks[issue.Task] = true
		}
	}
	for _, opt := range OptionalTasks {
		if !warnTasks[opt] {
			t.Errorf("expected warning for missing optional task %q", opt)
		}
	}
}

func TestValidateMiseConfig_FileNotFound(t *testing.T) {
	_, err := ValidateMiseConfig("/nonexistent/mise.toml")
	if err == nil {
		t.Fatal("expected error for missing file")
	}
}

func TestValidateMiseConfig_InvalidTOML(t *testing.T) {
	content := `this is not valid toml ][[[`
	path := writeTempMiseToml(t, content)
	_, err := ValidateMiseConfig(path)
	if err == nil {
		t.Fatal("expected error for invalid TOML")
	}
}

func TestHasErrors(t *testing.T) {
	tests := []struct {
		name   string
		issues []Issue
		want   bool
	}{
		{"empty", nil, false},
		{"only warnings", []Issue{{Severity: SeverityWarning, Task: "audit"}}, false},
		{"has error", []Issue{{Severity: SeverityError, Task: "lint"}}, true},
		{"mixed", []Issue{
			{Severity: SeverityWarning, Task: "audit"},
			{Severity: SeverityError, Task: "lint"},
		}, true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := HasErrors(tt.issues); got != tt.want {
				t.Errorf("HasErrors() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestReferenceByLanguage(t *testing.T) {
	for lang, content := range ReferenceByLanguage {
		t.Run(lang, func(t *testing.T) {
			path := writeTempMiseToml(t, content)
			issues, err := ValidateMiseConfig(path)
			if err != nil {
				t.Fatalf("language %q reference config parse error: %v", lang, err)
			}
			if HasErrors(issues) {
				t.Errorf("language %q reference config has validation errors: %v", lang, issues)
			}
		})
	}
}
