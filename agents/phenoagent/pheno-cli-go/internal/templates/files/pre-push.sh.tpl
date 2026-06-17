#!/bin/bash
# Pre-push hook: Enforce branch pattern and run checks

set -e

BRANCH=$(git rev-parse --abbrev-ref HEAD)

# Allowed patterns:
# - main (no checks)
# - main branch for release/* branches
# - feature/* or bugfix/* for feature branches
# - release/* or hotfix/* for release branches
RELEASE_PATTERN="^(release|hotfix)/"
FEATURE_PATTERN="^(feature|bugfix|docs)/"
MAIN_PATTERN="^main$"

if [[ $BRANCH =~ $RELEASE_PATTERN ]] || [[ $BRANCH =~ $FEATURE_PATTERN ]]; then
  echo "Running pre-push checks on branch: $BRANCH"

  # Run linting and tests
  echo "→ Running lint..."
  {{if eq .Language "go"}}
  if ! golangci-lint run; then
    echo "ERROR: Linting failed"
    exit 1
  fi
  {{else if eq .Language "rust"}}
  if ! cargo clippy -- -D warnings; then
    echo "ERROR: Clippy failed"
    exit 1
  fi
  {{else if eq .Language "python"}}
  if ! ruff check . || ! mypy .; then
    echo "ERROR: Linting failed"
    exit 1
  fi
  {{else if eq .Language "typescript"}}
  if ! npm run lint; then
    echo "ERROR: Linting failed"
    exit 1
  fi
  {{end}}

  echo "→ Running tests..."
  {{if eq .Language "go"}}
  if ! go test ./...; then
    echo "ERROR: Tests failed"
    exit 1
  fi
  {{else if eq .Language "rust"}}
  if ! cargo test; then
    echo "ERROR: Tests failed"
    exit 1
  fi
  {{else if eq .Language "python"}}
  if ! pytest; then
    echo "ERROR: Tests failed"
    exit 1
  fi
  {{else if eq .Language "typescript"}}
  if ! npm test; then
    echo "ERROR: Tests failed"
    exit 1
  fi
  {{end}}

  echo "✓ All checks passed"
elif [[ ! $BRANCH =~ $MAIN_PATTERN ]]; then
  echo "WARNING: Unrecognized branch pattern: $BRANCH"
  echo "Expected: main, feature/*, bugfix/*, docs/*, release/*, hotfix/*"
fi
