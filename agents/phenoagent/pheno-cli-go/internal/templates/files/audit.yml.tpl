name: Audit
on:
  push:
    branches: [main]
  schedule: [{cron: "0 3 * * *"}]
  workflow_dispatch:
permissions:
  contents: read
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run audit
        run: echo "Audit placeholder"
