name: Release

on:
  push:
    branches: [main]
    paths-ignore:
      - 'docs/**'
      - '**.md'

permissions:
  contents: write
  packages: write

jobs:
  release:
    runs-on: ubuntu-latest
    if: contains(github.event.head_commit.message, 'release:') || contains(github.event.head_commit.message, 'chore(release)')
    outputs:
      version: ${{ '{' }}steps.version.outputs.version{{ '}' }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      {{if eq .Language "go"}}
      - name: Setup Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.22'

      - name: Build
        run: go build ./...

      - name: Test
        run: go test ./... -v -race

      - name: Determine version
        id: version
        run: |
          VERSION=$(git describe --tags --always --abbrev=7)
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      - name: Publish to Go proxy
        run: |
          # Go packages are published automatically via git tags
          git tag v${{ '{' }}steps.version.outputs.version{{ '}' }}
          git push origin v${{ '{' }}steps.version.outputs.version{{ '}' }}
      {{else if eq .Language "rust"}}
      - name: Setup Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Build
        run: cargo build --release

      - name: Test
        run: cargo test --release

      - name: Determine version
        id: version
        run: |
          VERSION=$(grep '^version' Cargo.toml | head -1 | cut -d'"' -f2)
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      - name: Publish to crates.io
        run: |
          cargo publish --token ${{ '{' }}secrets.CARGO_REGISTRY_TOKEN{{ '}' }}
      {{else if eq .Language "python"}}
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install build tools
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build
        run: python -m build

      - name: Determine version
        id: version
        run: |
          VERSION=$(grep '^version' pyproject.toml | cut -d'"' -f2)
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      - name: Publish to PyPI
        run: |
          twine upload dist/* -u __token__ -p ${{ '{' }}secrets.PYPI_API_TOKEN{{ '}' }}
      {{else if eq .Language "typescript"}}
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Test
        run: npm test

      - name: Determine version
        id: version
        run: |
          VERSION=$(jq -r '.version' package.json)
          echo "version=$VERSION" >> $GITHUB_OUTPUT

      - name: Publish to NPM
        run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ '{' }}secrets.NPM_TOKEN{{ '}' }}
      {{end}}

  promote:
    needs: release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Promote to staging
        uses: KooshaPari/phenotypeActions/promote@main
        with:
          version: ${{ '{' }}needs.release.outputs.version{{ '}' }}
          channel: beta
          registry: {{.Registry}}
