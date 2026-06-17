package taskrunner

// Reference mise.toml configurations per language ecosystem.
// These serve as canonical templates for pheno-cli repo bootstrap and as
// validation baselines for ValidateMiseConfig.

const MiseTomlGo = `[tools]
go = "1.24"

[tasks.format]
run = "gofmt -w ."
description = "Format Go source files"

[tasks.lint]
run = "golangci-lint run ./..."
description = "Run golangci-lint static analysis"

[tasks.test]
run = "go test ./..."
description = "Run Go test suite"

[tasks.build]
run = "go build ./..."
description = "Build Go binaries"

[tasks.audit]
run = "govulncheck ./..."
description = "Scan for known Go vulnerabilities"
`

const MiseTomlRust = `[tools]
rust = "stable"

[tasks.format]
run = "cargo fmt --all"
description = "Format Rust source files"

[tasks.lint]
run = "cargo clippy --all-targets --all-features -- -D warnings"
description = "Run Clippy linter"

[tasks.test]
run = "cargo test --all"
description = "Run Rust test suite"

[tasks.build]
run = "cargo build --release"
description = "Build Rust release artifact"

[tasks.audit]
run = "cargo audit"
description = "Scan for known Rust vulnerabilities"
`

const MiseTomlPython = `[tools]
python = "3.12"

[tasks.format]
run = "ruff format ."
description = "Format Python source files"

[tasks.lint]
run = "ruff check ."
description = "Run ruff linter"

[tasks.test]
run = "pytest"
description = "Run Python test suite"

[tasks.build]
run = "python -m build"
description = "Build Python distribution"

[tasks.audit]
run = "pip-audit"
description = "Scan for known Python vulnerabilities"
`

const MiseTomlTypeScript = `[tools]
node = "22"

[tasks.format]
run = "prettier --write ."
description = "Format TypeScript/JavaScript source files"

[tasks.lint]
run = "eslint ."
description = "Run ESLint static analysis"

[tasks.test]
run = "vitest run"
description = "Run TypeScript test suite"

[tasks.build]
run = "tsc --noEmit && esbuild --bundle src/index.ts --outdir=dist"
description = "Type-check and bundle TypeScript"

[tasks.audit]
run = "npm audit --audit-level=moderate"
description = "Scan for known npm vulnerabilities"
`

// ReferenceByLanguage maps language identifiers to their reference mise.toml content.
var ReferenceByLanguage = map[string]string{
	"go":         MiseTomlGo,
	"rust":       MiseTomlRust,
	"python":     MiseTomlPython,
	"typescript": MiseTomlTypeScript,
}
