# Binaries
{{if eq .Language "go"}}
*.exe
*.exe~
*.dll
*.so
*.dylib
{{end}}
{{if eq .Language "rust"}}
target/
Cargo.lock
**/*.rs.bk
*.pdb
{{end}}
{{if eq .Language "python"}}
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
{{end}}
{{if eq .Language "typescript"}}
node_modules/
dist/
build/
*.tsbuildinfo
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.lerna
.cache/
{{end}}

# Test coverage
*.coverage
*.coverag
cov_profile/
coverage/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~
.project
.settings/
{{if eq .Language "go"}}
# Go workspace
go.work
{{end}}

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Environment
.env
.env.local
.env.*.local

# Temporary files
*.tmp
*.temp
.tmp/

# VCS
.svn/
.hg/

# Dependency directories
vendor/
{{if eq .Language "python"}}
venv/
ENV/
env/
.venv/
{{end}}
