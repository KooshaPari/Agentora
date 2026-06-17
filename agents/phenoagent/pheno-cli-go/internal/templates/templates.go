package templates

import (
	"bytes"
	"embed"
	"fmt"
	"text/template"
)

//go:embed files/*
var TemplateFiles embed.FS

// TemplateContext holds the context variables for template rendering.
type TemplateContext struct {
	RepoName    string // Repository name
	Language    string // Programming language (go, rust, python, typescript)
	Registry    string // Package registry
	RiskProfile string // Risk profile (low, medium, high)
}

// RenderTemplate renders a template by name with the given context.
func RenderTemplate(name string, ctx TemplateContext) (string, error) {
	// Read the template file from the embedded FS
	data, err := TemplateFiles.ReadFile("files/" + name + ".tpl")
	if err != nil {
		return "", fmt.Errorf("failed to read template %s: %w", name, err)
	}

	// Parse and execute the template
	tmpl, err := template.New(name).Parse(string(data))
	if err != nil {
		return "", fmt.Errorf("failed to parse template %s: %w", name, err)
	}

	var buf bytes.Buffer
	if err := tmpl.Execute(&buf, ctx); err != nil {
		return "", fmt.Errorf("failed to render template %s: %w", name, err)
	}

	return buf.String(), nil
}

// ListTemplates returns the list of available template names.
func ListTemplates() []string {
	return []string{
		// Base configs
		"editorconfig",
		"gitignore",
		"gitattributes",
		"dockerignore",
		// Task runner
		"mise.toml",
		// Git hooks
		"pre-commit.sh",
		"pre-push.sh",
		// CI/CD
		"ci.yml",
		"release.yml",
		// Governance
		"ADR.md",
		"FR.md",
		"GOVERNANCE.md",
		"PRD.md",
		"SPEC.md",
		// BDD Testing
		"bdd-cargo-toml",
		"bdd-cucumber-json",
		"bdd-feature",
		"bdd-package-json",
		"bdd-steps-go",
		"bdd-steps-py",
		"bdd-steps-rs",
		"bdd-steps-ts",
		"bdd-test-go",
		// Go templates
		"go-entity",
		"go-handler",
		"go-main",
		"go-service",
		// Python templates
		"py-entity",
		"py-ports",
		"py-service",
		// Rust templates
		"rust-adapters-mod",
		"rust-application-mod",
		"rust-domain-mod",
		"rust-dto",
		"rust-entity",
		"rust-lib",
		"rust-ports",
		"rust-repository",
		"rust-service",
	}
}

// GetStaticCliffToml returns the static cliff.toml content.
func GetStaticCliffToml() string {
	return `# Configuration for git-cliff: https://git-cliff.org/
# Generates CHANGELOG from conventional commits

[changelog]
header = """
# Changelog

All notable changes to this project will be documented in this file.
"""

body = """
{%- for group, commits in commits | group_by(attribute="group") %}
## {{ group | replace(from="Features", to="✨ Features") | replace(from="Bug Fixes", to="🐛 Bug Fixes") | replace(from="Documentation", to="📚 Documentation") | replace(from="Performance", to="⚡ Performance") }}

{%- for commit in commits %}
- {% if commit.breaking %}**BREAKING** {% endif %}{{ commit.message | upper_first }} ([` + "`" + `{{ commit.id | truncate(length=7, end="") }}` + "`" + `]({{ commit.link }}))
  {%- if commit.body %}
  {{ commit.body | indent(prefix="  > ") }}
  {%- endif %}
{%- endfor %}
{%- endfor %}
"""

footer = """
---

**Release Date:** {{ now | date(format="%Y-%m-%d") }}
"""

trim = true

[git]
conventional_commits = true

commit_parsers = [
  {message = "^feat", group = "Features"},
  {message = "^fix", group = "Bug Fixes"},
  {message = "^doc", group = "Documentation"},
  {message = "^perf", group = "Performance"},
  {message = "^refactor", group = "Refactoring"},
  {message = "^test", group = "Testing"},
  {message = "^chore", skip = true},
  {message = "^ci", skip = true},
]

commit_filters = [
  {remove_if_matches = ".*skip.*changelog.*"},
]

tag_pattern = "v[0-9].*"
skip_tags = ""
sort_commits = "newest"
`
}
