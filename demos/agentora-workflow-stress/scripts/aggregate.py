#!/usr/bin/env python3
"""Agentora workflow-stress aggregator.

Reads artifacts/runs.jsonl, aggregates per-worker latency + approval-gate
counters, writes artifacts/metrics.json + assets/dashboard/metrics.json,
and (--watch) serves the GUI dashboard on http://127.0.0.1:9000/.
"""
import argparse
import json
import pathlib
import statistics
import sys
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_RUNS = ROOT / "artifacts" / "runs.jsonl"
DEFAULT_OUT = ROOT / "artifacts" / "metrics.json"
DASHBOARD_METRICS = ROOT / "assets" / "dashboard" / "metrics.json"
DASHBOARD_FILE = ROOT / "assets" / "dashboard" / "index.html"


def quantile(sorted_vals, q):
    if not sorted_vals:
        return 0
    return sorted_vals[min(int(q * len(sorted_vals)), len(sorted_vals) - 1)]


def aggregate(path: pathlib.Path) -> dict:
    runs = []
    if path.exists():
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    runs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    n = len(runs)
    if n == 0:
        return {
            "completed_runs": 0,
            "throughput_per_s": 0.0,
            "lat_ms": {"avg": 0, "p50": 0, "p99": 0, "max": 0, "min": 0},
            "approval_gate": {"total_routes": 0, "approval_required": 0, "approval_rate": 0.0},
            "by_worker": {},
            "ts_ms": int(time.time() * 1000),
        }
    lats = sorted(r["lat_ms"] for r in runs)
    total_routes = sum(r["total_routes"] for r in runs)
    approval_required = sum(r["approval_routes"] for r in runs)
    by_worker = defaultdict(lambda: {"runs": 0, "lat_sum": 0, "approval_routes": 0, "total_routes": 0})
    for r in runs:
        w = str(r["worker"])
        by_worker[w]["runs"] += 1
        by_worker[w]["lat_sum"] += r["lat_ms"]
        by_worker[w]["approval_routes"] += r["approval_routes"]
        by_worker[w]["total_routes"] += r["total_routes"]
    by_worker_out = {k: {"runs": v["runs"], "avg_lat_ms": round(v["lat_sum"] / max(v["runs"], 1), 2),
                         "approval_routes": v["approval_routes"], "total_routes": v["total_routes"]}
                      for k, v in by_worker.items()}
    mtime_ms = int(path.stat().st_mtime * 1000) if path.exists() else int(time.time() * 1000)
    now_ms = int(time.time() * 1000)
    elapsed_s = max(1, (now_ms - mtime_ms) / 1000.0)
    return {
        "completed_runs": n,
        "throughput_per_s": round(n / elapsed_s, 2),
        "lat_ms": {
            "avg": int(statistics.mean(lats)),
            "p50": int(quantile(lats, 0.50)),
            "p99": int(quantile(lats, 0.99)),
            "max": int(max(lats)),
            "min": int(min(lats)),
        },
        "approval_gate": {
            "total_routes": total_routes,
            "approval_required": approval_required,
            "approval_rate": round(approval_required / max(1, total_routes), 4),
        },
        "by_worker": by_worker_out,
        "ts_ms": now_ms,
    }


def write_metrics(m, out: pathlib.Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        json.dump(m, f, indent=2)


def serve_dashboard(port: int, dashboard: pathlib.Path, metrics: pathlib.Path):
    if not dashboard.exists():
        print(f"dashboard not found: {dashboard}", file=sys.stderr)
        return

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/metrics.json"):
                m = aggregate(metrics) if metrics.exists() else {"completed_runs": 0}
                body = json.dumps(m).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(body)
            else:
                with dashboard.open("rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, *_):
            return

    print(f"[agentora-workflow-stress] dashboard: http://127.0.0.1:{port}/", flush=True)
    HTTPServer(("127.0.0.1", port), H).serve_forever()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", action="store_true")
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--runs", type=pathlib.Path, default=DEFAULT_RUNS)
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    a = ap.parse_args()

    if a.watch:
        write_metrics(aggregate(a.runs), a.out)
        write_metrics(aggregate(a.runs), DASHBOARD_METRICS)
        import threading
        def poll():
            while True:
                time.sleep(1)
                m = aggregate(a.runs)
                write_metrics(m, a.out)
                write_metrics(m, DASHBOARD_METRICS)
        threading.Thread(target=poll, daemon=True).start()
        serve_dashboard(a.port, DASHBOARD_FILE, a.out)
    else:
        m = aggregate(a.runs)
        write_metrics(m, a.out)
        print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()
