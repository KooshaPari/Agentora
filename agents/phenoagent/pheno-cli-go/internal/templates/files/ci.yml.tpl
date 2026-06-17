name: CI

on:
  push:
    branches: [main, feature/*, bugfix/*, docs/*, release/*, hotfix/*]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    {{if eq .Language "go"}}
    strategy:
      matrix:
        go-version: ['1.21', '1.22']
    {{else if eq .Language "rust"}}
    strategy:
      matrix:
        rust-version: ['1.70', 'stable']
    {{else if eq .Language "python"}}
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']
    {{else if eq .Language "typescript"}}
    strategy:
      matrix:
        node-version: ['18', '20', '22']
    {{end}}
    steps:
      - uses: actions/checkout@v4

      {{if eq .Language "go"}}
      - name: Setup Go
        uses: actions/setup-go@v4
        with:
          go-version: ${{ '{' }}matrix.go-version{{ '}' }}

      - name: Download dependencies
        run: go mod download

      - name: Build
        run: go build ./...

      - name: Run tests
        run: go test ./... -v -race -coverprofile=coverage.out

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.out
      {{else if eq .Language "rust"}}
      - name: Setup Rust
        uses: dtolnay/rust-toolchain@master
        with:
          toolchain: ${{ '{' }}matrix.rust-version{{ '}' }}

      - name: Build
        run: cargo build --verbose

      - name: Run tests
        run: cargo test --verbose

      - name: Run clippy
        run: cargo clippy -- -D warnings
      {{else if eq .Language "python"}}
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ '{' }}matrix.python-version{{ '}' }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Lint
        run: |
          ruff check .
          mypy .

      - name: Run tests
        run: pytest -v --cov=.
      {{else if eq .Language "typescript"}}
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: ${{ '{' }}matrix.node-version{{ '}' }}

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Lint
        run: npm run lint

      - name: Run tests
        run: npm test -- --coverage
      {{end}}

  phenotype-validate:
    runs-on: ubuntu-latest
    uses: KooshaPari/phenotypeActions/.github/workflows/validate-governance.yml@main
