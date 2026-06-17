package plugin

import (
	"context"
	"sync"
)

type Metadata struct {
	Name        string
	Version     string
	Description string
	Author      string
	Tags        []string
}

type TemplateFile struct {
	Path    string
	Content string
}

type Plugin interface {
	Metadata() Metadata
	Init(ctx context.Context, cfg map[string]interface{}) error
	Templates() []TemplateFile
	Execute(ctx context.Context, args []string) error
}

type Registry struct {
	mu      sync.RWMutex
	plugins map[string]Plugin
}

var globalRegistry = NewRegistry()

func Global() *Registry {
	return globalRegistry
}

func NewRegistry() *Registry {
	return &Registry{plugins: make(map[string]Plugin)}
}

func (r *Registry) Register(p Plugin) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	m := p.Metadata()
	if _, ok := r.plugins[m.Name]; ok {
		return nil
	}
	r.plugins[m.Name] = p
	return nil
}

func (r *Registry) List() []Plugin {
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]Plugin, 0, len(r.plugins))
	for _, p := range r.plugins {
		out = append(out, p)
	}
	return out
}

func (r *Registry) Get(name string) (Plugin, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	p, ok := r.plugins[name]
	return p, ok
}

func init() {
	globalRegistry.Register(&SAST{})
	globalRegistry.Register(&Dependabot{})
	globalRegistry.Register(&Coverage{})
	globalRegistry.Register(&Codeowners{})
	globalRegistry.Register(&IssueTemplates{})
	globalRegistry.Register(&PRTemplates{})
}

type SAST struct{}

func (p *SAST) Metadata() Metadata {
	return Metadata{Name: "sast", Version: "1.0.0", Description: "Static Application Security Testing", Author: "Phenotype Org"}
}
func (p *SAST) Init(context.Context, map[string]interface{}) error { return nil }
func (p *SAST) Templates() []TemplateFile {
	return []TemplateFile{{Path: ".github/workflows/sast.yml", Content: sastWorkflow}}
}
func (p *SAST) Execute(context.Context, []string) error { return nil }

const sastWorkflow = `name: SAST
on: [pull_request, push]
jobs:
  semgrep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: returntocorp/semgrep-action@v1
`

type Dependabot struct{}

func (p *Dependabot) Metadata() Metadata {
	return Metadata{Name: "dependabot", Version: "1.0.0", Description: "Automated dependency updates", Author: "Phenotype Org"}
}
func (p *Dependabot) Init(context.Context, map[string]interface{}) error { return nil }
func (p *Dependabot) Templates() []TemplateFile {
	return []TemplateFile{{Path: ".github/dependabot.yml", Content: dependabotYML}}
}
func (p *Dependabot) Execute(context.Context, []string) error { return nil }

const dependabotYML = `version: 2
updates:
  - package-ecosystem: gomod
    directory: /
    schedule: {interval: weekly}
  - package-ecosystem: github-actions
    directory: /
    schedule: {interval: weekly}
`

type Coverage struct{}

func (p *Coverage) Metadata() Metadata {
	return Metadata{Name: "coverage", Version: "1.0.0", Description: "Code coverage tracking", Author: "Phenotype Org"}
}
func (p *Coverage) Init(context.Context, map[string]interface{}) error { return nil }
func (p *Coverage) Templates() []TemplateFile {
	return []TemplateFile{{Path: ".github/workflows/coverage.yml", Content: coverageWorkflow}}
}
func (p *Coverage) Execute(context.Context, []string) error { return nil }

const coverageWorkflow = `name: Coverage
on: [push, pull_request]
jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: go test ./... -coverprofile=coverage.out
      - uses: codecov/codecov-action@v4
`

type Codeowners struct{}

func (p *Codeowners) Metadata() Metadata {
	return Metadata{Name: "codeowners", Version: "1.0.0", Description: "GitHub CODEOWNERS", Author: "Phenotype Org"}
}
func (p *Codeowners) Init(context.Context, map[string]interface{}) error { return nil }
func (p *Codeowners) Templates() []TemplateFile {
	return []TemplateFile{{Path: ".github/CODEOWNERS", Content: codeownersContent}}
}
func (p *Codeowners) Execute(context.Context, []string) error { return nil }

const codeownersContent = `* @phenotype/owners
`

type IssueTemplates struct{}

func (p *IssueTemplates) Metadata() Metadata {
	return Metadata{Name: "issue-templates", Version: "1.0.0", Description: "GitHub issue templates", Author: "Phenotype Org"}
}
func (p *IssueTemplates) Init(context.Context, map[string]interface{}) error { return nil }
func (p *IssueTemplates) Templates() []TemplateFile {
	return []TemplateFile{
		{Path: ".github/ISSUE_TEMPLATE/bug_report.yml", Content: bugReportYML},
		{Path: ".github/ISSUE_TEMPLATE/feature_request.yml", Content: featureRequestYML},
	}
}
func (p *IssueTemplates) Execute(context.Context, []string) error { return nil }

const bugReportYML = `name: Bug Report
description: Create a report to help us improve
labels: [bug]
body:
  - type: markdown
    attributes:
      value: |
        ## Bug Description
        [Describe the bug]
`

const featureRequestYML = `name: Feature Request
description: Suggest an idea for this project
labels: [enhancement]
body:
  - type: markdown
    attributes:
      value: |
        ## Feature Description
        [Describe the feature]
`

type PRTemplates struct{}

func (p *PRTemplates) Metadata() Metadata {
	return Metadata{Name: "pr-templates", Version: "1.0.0", Description: "Pull request templates", Author: "Phenotype Org"}
}
func (p *PRTemplates) Init(context.Context, map[string]interface{}) error { return nil }
func (p *PRTemplates) Templates() []TemplateFile {
	return []TemplateFile{{Path: ".github/PULL_REQUEST_TEMPLATE.md", Content: prTemplate}}
}
func (p *PRTemplates) Execute(context.Context, []string) error { return nil }

const prTemplate = `## Description
[Describe your changes]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated
`
