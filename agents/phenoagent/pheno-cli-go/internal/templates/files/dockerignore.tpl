# Version control
.git
.gitignore
.svn

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Documentation
README.md
LICENSE
docs/
*.md

# Test files
test/
tests/
coverage/
*.test
*.spec

# Local config
.env
.env.local
*.local

# Build artifacts
{{if eq .Language "go"}}
# Exclude binaries
*.exe
go.work
{{end}}
{{if eq .Language "rust"}}
target/
**/*.rs.bk
Cargo.lock
{{end}}
{{if eq .Language "python"}}
build/
dist/
*.egg-info/
venv/
{{end}}
{{if eq .Language "typescript"}}
node_modules/
dist/
{{end}}

# Logs
*.log
logs/

# Temporary files
*.tmp
.tmp/
