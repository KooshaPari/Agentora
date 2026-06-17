"""
Metrics storage backends.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pheno.observability.runtime_metrics.models import MetricsRecord


class MetricsStorage(Protocol):
    """
    Protocol for persisting metrics records.
    """

    def write_records(self, records: Iterable[MetricsRecord]) -> None: ...


class NoOpMetricsStorage:
    """
    Fallback storage that discards metrics.
    """

    def write_records(self, records: Iterable[MetricsRecord]) -> None:
        return None


class SqliteMetricsStorage:
    """
    SQLite-backed storage for metrics records.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics_records (
                    request_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    task_complexity REAL,
                    task_risk TEXT,
                    model_used TEXT,
                    candidate_models TEXT,
                    input_tokens INTEGER,
                    input_characters INTEGER,
                    model_tier TEXT,
                    routing_policy TEXT,
                    selection_method TEXT,
                    response_tokens INTEGER,
                    response_characters INTEGER,
                    latency_ms REAL,
                    cost_in_usd REAL,
                    cost_out_usd REAL,
                    total_cost_usd REAL,
                    cascade_cost_usd REAL,
                    ttft_ms REAL,
                    throughput_tps REAL,
                    fallback_used INTEGER,
                    error_occurred INTEGER,
                    quality_score REAL,
                    human_feedback_score REAL,
                    was_successful INTEGER,
                    validation_passed INTEGER,
                    refinement_needed INTEGER,
                    chain_length INTEGER,
                    chain_position INTEGER,
                    user_id TEXT,
                    session_id TEXT,
                    metadata TEXT
                )
                """,
            )
            self._ensure_additional_columns(conn)

    def _ensure_additional_columns(self, conn: sqlite3.Connection) -> None:
        """
        Add newly introduced columns if the table was created previously.
        """

        required_columns = {
            "task_complexity": "REAL",
            "task_risk": "TEXT",
            "model_tier": "TEXT",
            "routing_policy": "TEXT",
            "selection_method": "TEXT",
            "cascade_cost_usd": "REAL",
            "ttft_ms": "REAL",
            "throughput_tps": "REAL",
            "validation_passed": "INTEGER",
            "refinement_needed": "INTEGER",
        }

        existing = {row[1] for row in conn.execute("PRAGMA table_info(metrics_records)").fetchall()}

        for column, column_type in required_columns.items():
            if column not in existing:
                try:
                    conn.execute(f"ALTER TABLE metrics_records ADD COLUMN {column} {column_type}")
                except sqlite3.OperationalError:
                    continue
        conn.commit()

    def write_records(self, records: Iterable[MetricsRecord]) -> None:
        rows = [
            (
                record.request_id,
                record.timestamp.isoformat(),
                record.task_type,
                record.task_complexity,
                record.task_risk,
                record.model_used,
                json.dumps(record.candidate_models),
                record.input_tokens,
                record.input_characters,
                record.model_tier,
                record.routing_policy,
                record.selection_method,
                record.response_tokens,
                record.response_characters,
                record.latency_ms,
                record.cost_in_usd,
                record.cost_out_usd,
                record.total_cost_usd,
                record.cascade_cost_usd,
                record.ttft_ms,
                record.throughput_tps,
                int(record.fallback_used),
                int(record.error_occurred),
                record.quality_score,
                record.human_feedback_score,
                int(record.was_successful),
                (
                    record.validation_passed
                    if record.validation_passed is None
                    else int(record.validation_passed)
                ),
                (
                    record.refinement_needed
                    if record.refinement_needed is None
                    else int(record.refinement_needed)
                ),
                record.chain_length,
                record.chain_position,
                record.user_id,
                record.session_id,
                json.dumps(record.metadata or {}),
            )
            for record in records
        ]

        if not rows:
            return

        with sqlite3.connect(self.database_path) as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO metrics_records (
                    request_id,
                    timestamp,
                    task_type,
                    task_complexity,
                    task_risk,
                    model_used,
                    candidate_models,
                    input_tokens,
                    input_characters,
                    model_tier,
                    routing_policy,
                    selection_method,
                    response_tokens,
                    response_characters,
                    latency_ms,
                    cost_in_usd,
                    cost_out_usd,
                    total_cost_usd,
                    cascade_cost_usd,
                    ttft_ms,
                    throughput_tps,
                    fallback_used,
                    error_occurred,
                    quality_score,
                    human_feedback_score,
                    was_successful,
                    validation_passed,
                    refinement_needed,
                    chain_length,
                    chain_position,
                    user_id,
                    session_id,
                    metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
