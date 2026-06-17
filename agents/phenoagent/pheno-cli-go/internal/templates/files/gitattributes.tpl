# Auto detect text files and perform LF normalization
* text=auto

# Force Unix line endings for these files
*.sh text eol=lf
*.bash text eol=lf
*.zsh text eol=lf

# Scripts
*.awk text
*.sed text

# Documentation
*.md text
*.txt text
*.rst text
*.adoc text

# Config files
*.yml text
*.yaml text
*.toml text
*.json text
*.xml text
*.properties text

# Scripts
Makefile text eol=lf
Dockerfile text eol=lf

# Git files
.gitattributes text
.gitignore text

# Go files - let git handle line endings
*.go text

# Rust files
*.rs text

# Python files
*.py text

# TypeScript/JavaScript
*.ts text
*.js text
*.jsx text
*.tsx text

# Binary files - do not normalize
{{if eq .Language "go"}}
# Exclude go binaries
{{end}}
{{if eq .Language "rust"}}
*.rlib binary
{{end}}
{{if eq .Language "typescript"}}
*.wasm binary
{{end}}

# Images
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.ico binary
*.svg binary

# Fonts
*.ttf binary
*.otf binary
*.woff binary
*.woff2 binary

# Archives
*.zip binary
*.tar binary
*.gz binary
*.bz2 binary
*.xz binary

# Certificates
*.pem binary
*.crt binary
*.key binary
