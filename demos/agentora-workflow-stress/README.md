# agentora-workflow-stress

GUI/visual stress-test demo for Agentora's substrate routing layer. Drives
the `tweetclaw_workflow` example binary under N concurrent workers and
serves a live dashboard at http://127.0.0.1:9000/.

## Build prerequisite

```bash
cd Agentora
cargo build --release --example tweetclaw_workflow
```

## Run

```bash
# terminal 1: stress driver (N=8 workers, duration_s=15)
N=8 duration_s=15 bash demos/agentora-workflow-stress/scripts/stress.sh

# terminal 2: aggregator + dashboard
python3 demos/agentora-workflow-stress/scripts/aggregate.py --watch --port 9000
```

Open http://127.0.0.1:9000/ while the demo runs.

## What it stresses

| Dimension | How |
|---|---|
| Concurrent agents | N parallel bash workers invoking the workflow binary |
| Routing latency | wall-clock per run, p50/p99 captured |
| Approval gate | routes with `requires_approval=true` counted across runs |
| Throughput | runs/sec derived from run log timestamps |

## Files

- `scripts/stress.sh` — N workers × duration_s
- `scripts/aggregate.py` — reads `artifacts/runs.jsonl`, writes `metrics.json`, serves dashboard
- `assets/dashboard/index.html` — GUI (embedded at runtime)
- `artifacts/runs.jsonl` — per-run telemetry
