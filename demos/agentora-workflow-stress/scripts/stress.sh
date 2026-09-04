#!/usr/bin/env bash
# Agentora workflow stress driver.
# Spawns N concurrent workers, each invoking `tweetclaw_workflow` repeatedly
# for `duration_s`. Writes one JSON line per run to artifacts/runs.jsonl.
set -euo pipefail
N="${N:-8}"
DURATION_S="${duration_s:-15}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BIN="${REPO_ROOT}/target/release/examples/tweetclaw_workflow"
if [ ! -x "$BIN" ]; then
    echo "binary not built: $BIN"
    echo "build first: cargo build --release --example tweetclaw_workflow"
    exit 1
fi
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_JSONL="${HERE}/../artifacts/runs.jsonl"
mkdir -p "$(dirname "$OUT_JSONL")"
: > "$OUT_JSONL"
STOP_FILE="$(mktemp -u)"
( sleep "$DURATION_S"; touch "$STOP_FILE" ) &
for ((i=0;i<N;i++)); do
  (
    while [ ! -f "$STOP_FILE" ]; do
      t_start=$(date +%s%N)
      out=$("$BIN" 2>&1) || true
      t_end=$(date +%s%N)
      lat_ms=$(( (t_end - t_start) / 1000000 ))
      approval=$(echo "$out" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin)
    print(sum(1 for v in d.values() if isinstance(v,dict) and v.get("requires_approval")))
except: print(0)' 2>/dev/null || echo 0)
      total=$(echo "$out" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin)
    print(len([v for v in d.values() if isinstance(v,dict)]))
except: print(0)' 2>/dev/null || echo 0)
      printf '{"worker":%d,"lat_ms":%d,"approval_routes":%s,"total_routes":%s}\n' "$i" "$lat_ms" "$approval" "$total" >> "$OUT_JSONL"
    done
  ) &
done
wait
rm -f "$STOP_FILE"

echo "wrote $OUT_JSONL ($(wc -l < "$OUT_JSONL") runs)"
