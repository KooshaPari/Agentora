name: Security Guard
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Security scan
        run: echo "Security guard placeholder"
