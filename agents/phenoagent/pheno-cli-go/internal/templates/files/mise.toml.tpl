[tasks.format]
description = "Format code"
{{if eq .Language "go"}}
run = "gofmt -w ."
{{else if eq .Language "rust"}}
run = "cargo fmt"
{{else if eq .Language "python"}}
run = "black . --line-length 100"
{{else if eq .Language "typescript"}}
run = "npx prettier --write ."
{{end}}

[tasks.lint]
description = "Lint code"
{{if eq .Language "go"}}
run = "golangci-lint run"
{{else if eq .Language "rust"}}
run = "cargo clippy -- -D warnings"
{{else if eq .Language "python"}}
run = "ruff check . && mypy ."
{{else if eq .Language "typescript"}}
run = "eslint ."
{{end}}

[tasks.test]
description = "Run tests"
{{if eq .Language "go"}}
run = "go test ./..."
{{else if eq .Language "rust"}}
run = "cargo test"
{{else if eq .Language "python"}}
run = "pytest"
{{else if eq .Language "typescript"}}
run = "npm test"
{{end}}

[tasks.build]
description = "Build project"
{{if eq .Language "go"}}
run = "go build ./..."
{{else if eq .Language "rust"}}
run = "cargo build --release"
{{else if eq .Language "python"}}
run = "python -m build"
{{else if eq .Language "typescript"}}
run = "npm run build"
{{end}}

[tasks.audit]
description = "Audit dependencies"
{{if eq .Language "go"}}
run = "go list -json -m all | nancy sleuth"
{{else if eq .Language "rust"}}
run = "cargo audit"
{{else if eq .Language "python"}}
run = "pip-audit"
{{else if eq .Language "typescript"}}
run = "npm audit"
{{end}}

[tasks.docs:build]
description = "Build documentation"
{{if eq .Language "go"}}
run = "go doc -all -html ./... > docs/api.html"
{{else if eq .Language "rust"}}
run = "cargo doc --no-deps --open"
{{else if eq .Language "python"}}
run = "sphinx-build -b html docs docs/_build"
{{else if eq .Language "typescript"}}
run = "typedoc --out docs"
{{end}}
