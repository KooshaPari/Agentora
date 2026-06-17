package templates

import (
	"strings"
	"testing"
)

func TestRenderTemplate(t *testing.T) {
	languages := []string{"go", "rust", "python", "typescript"}

	for _, lang := range languages {
		t.Run(lang, func(t *testing.T) {
			ctx := TemplateContext{
				RepoName:    "test-repo",
				Language:    lang,
				Registry:    "npm",
				RiskProfile: "low",
			}

			// Test mise.toml template
			result, err := RenderTemplate("mise.toml", ctx)
			if err != nil {
				t.Fatalf("failed to render mise.toml for %s: %v", lang, err)
			}
			if len(result) == 0 {
				t.Fatal("rendered template is empty")
			}
			if !strings.Contains(result, "[tasks.") {
				t.Fatal("rendered template missing expected content")
			}

			// Test pre-commit.sh template
			result, err = RenderTemplate("pre-commit.sh", ctx)
			if err != nil {
				t.Fatalf("failed to render pre-commit.sh for %s: %v", lang, err)
			}
			if len(result) == 0 {
				t.Fatal("rendered template is empty")
			}
			if !strings.Contains(result, "Conventional commit") {
				t.Fatal("rendered template missing expected content")
			}

			// Test ci.yml template
			result, err = RenderTemplate("ci.yml", ctx)
			if err != nil {
				t.Fatalf("failed to render ci.yml for %s: %v", lang, err)
			}
			if len(result) == 0 {
				t.Fatal("rendered template is empty")
			}
			if !strings.Contains(result, "name: CI") {
				t.Fatal("rendered template missing CI workflow name")
			}
		})
	}
}

func TestRenderTemplate_InvalidName(t *testing.T) {
	ctx := TemplateContext{
		RepoName:    "test-repo",
		Language:    "go",
		Registry:    "npm",
		RiskProfile: "low",
	}

	_, err := RenderTemplate("nonexistent", ctx)
	if err == nil {
		t.Fatal("expected error for nonexistent template")
	}
}

func TestListTemplates(t *testing.T) {
	templates := ListTemplates()

	if len(templates) != 5 {
		t.Fatalf("expected 5 templates, got %d", len(templates))
	}

	expected := []string{
		"mise.toml",
		"pre-commit.sh",
		"pre-push.sh",
		"ci.yml",
		"release.yml",
	}

	for i, name := range expected {
		if templates[i] != name {
			t.Fatalf("expected template %s at index %d, got %s", name, i, templates[i])
		}
	}
}
