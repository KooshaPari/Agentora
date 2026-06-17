"""
Metrics Analyzer: Analyzes collected telemetry data

This module provides comprehensive analysis of telemetry data, including
performance analysis, usage patterns, error detection, and recommendations.
"""

import json
import logging
import sqlite3
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np


@dataclass
class AnalysisResult:
    """Represents an analysis result."""
    component: str
    analysis_type: str
    timestamp: str
    findings: list[dict[str, Any]]
    recommendations: list[str]
    severity: str
    confidence: float


@dataclass
class PerformanceAnalysis:
    """Represents performance analysis results."""
    component: str
    operation: str
    avg_duration: float
    p95_duration: float
    p99_duration: float
    success_rate: float
    error_rate: float
    trend: str
    recommendations: list[str]


@dataclass
class UsageAnalysis:
    """Represents usage analysis results."""
    project: str
    service: str
    total_usage: int
    peak_usage: int
    usage_pattern: str
    recommendations: list[str]


@dataclass
class HealthAnalysis:
    """Represents health analysis results."""
    component: str
    health_score: float
    issues: list[str]
    recommendations: list[str]
    trend: str


class MetricsAnalyzer:
    """Analyzes telemetry data and provides insights."""

    def __init__(self, db_path: str):
        """Initialize the metrics analyzer."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

    async def analyze_performance(self, component: str | None = None,
                                 hours: int = 24) -> list[PerformanceAnalysis]:
        """Analyze performance metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since = (datetime.now() - timedelta(hours=hours)).isoformat()

            # Build query
            query = """
                SELECT component, operation, duration, success, error_message
                FROM performance_metrics
                WHERE timestamp >= ?
            """
            params = [since]

            if component:
                query += " AND component = ?"
                params.append(component)

            query += " ORDER BY timestamp"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Group by component and operation
            grouped_data = defaultdict(list)
            for row in rows:
                comp, op, duration, success, error = row
                grouped_data[(comp, op)].append({
                    "duration": duration,
                    "success": success,
                    "error": error,
                })

            # Analyze each group
            analyses = []
            for (comp, op), data in grouped_data.items():
                durations = [d["duration"] for d in data]
                successes = [d["success"] for d in data]

                # Calculate statistics
                avg_duration = statistics.mean(durations)
                p95_duration = np.percentile(durations, 95)
                p99_duration = np.percentile(durations, 99)
                success_rate = sum(successes) / len(successes)
                error_rate = 1 - success_rate

                # Calculate trend
                if len(durations) >= 10:
                    recent_avg = statistics.mean(durations[-10:])
                    older_avg = statistics.mean(durations[:-10])
                    if recent_avg > older_avg * 1.1:
                        trend = "degrading"
                    elif recent_avg < older_avg * 0.9:
                        trend = "improving"
                    else:
                        trend = "stable"
                else:
                    trend = "insufficient_data"

                # Generate recommendations
                recommendations = []
                if avg_duration > 1.0:  # More than 1 second
                    recommendations.append("Consider optimizing operation performance")
                if success_rate < 0.95:  # Less than 95% success rate
                    recommendations.append("Investigate and fix error causes")
                if p95_duration > avg_duration * 2:  # High variance
                    recommendations.append("Investigate performance variance")
                if trend == "degrading":
                    recommendations.append("Performance is degrading, investigate recent changes")

                analysis = PerformanceAnalysis(
                    component=comp,
                    operation=op,
                    avg_duration=avg_duration,
                    p95_duration=p95_duration,
                    p99_duration=p99_duration,
                    success_rate=success_rate,
                    error_rate=error_rate,
                    trend=trend,
                    recommendations=recommendations,
                )

                analyses.append(analysis)

            conn.close()
            return analyses

        except Exception as e:
            self.logger.exception(f"Error analyzing performance: {e}")
            return []

    async def analyze_usage(self, project: str | None = None,
                           hours: int = 24) -> list[UsageAnalysis]:
        """Analyze usage patterns."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since = (datetime.now() - timedelta(hours=hours)).isoformat()

            # Build query
            query = """
                SELECT project, service, timestamp
                FROM usage_metrics
                WHERE timestamp >= ?
            """
            params = [since]

            if project:
                query += " AND project = ?"
                params.append(project)

            query += " ORDER BY timestamp"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Group by project and service
            grouped_data = defaultdict(list)
            for row in rows:
                proj, svc, timestamp = row
                grouped_data[(proj, svc)].append(timestamp)

            # Analyze each group
            analyses = []
            for (proj, svc), timestamps in grouped_data.items():
                total_usage = len(timestamps)

                # Calculate peak usage (usage in busiest hour)
                hourly_usage = defaultdict(int)
                for ts in timestamps:
                    hour = datetime.fromisoformat(ts).replace(minute=0, second=0, microsecond=0)
                    hourly_usage[hour.isoformat()] += 1

                peak_usage = max(hourly_usage.values()) if hourly_usage else 0

                # Determine usage pattern
                if peak_usage > total_usage * 0.3:
                    usage_pattern = "bursty"
                elif total_usage > 100:
                    usage_pattern = "high_volume"
                elif total_usage < 10:
                    usage_pattern = "low_volume"
                else:
                    usage_pattern = "moderate"

                # Generate recommendations
                recommendations = []
                if usage_pattern == "bursty":
                    recommendations.append("Consider implementing rate limiting")
                if total_usage > 1000:
                    recommendations.append("Consider horizontal scaling")
                if total_usage < 5:
                    recommendations.append("Consider if this service is needed")

                analysis = UsageAnalysis(
                    project=proj,
                    service=svc,
                    total_usage=total_usage,
                    peak_usage=peak_usage,
                    usage_pattern=usage_pattern,
                    recommendations=recommendations,
                )

                analyses.append(analysis)

            conn.close()
            return analyses

        except Exception as e:
            self.logger.exception(f"Error analyzing usage: {e}")
            return []

    async def analyze_health(self, component: str | None = None,
                            hours: int = 24) -> list[HealthAnalysis]:
        """Analyze health metrics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since = (datetime.now() - timedelta(hours=hours)).isoformat()

            # Build query
            query = """
                SELECT component, health_score, issues, recommendations, timestamp
                FROM health_metrics
                WHERE timestamp >= ?
            """
            params = [since]

            if component:
                query += " AND component = ?"
                params.append(component)

            query += " ORDER BY timestamp"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Group by component
            grouped_data = defaultdict(list)
            for row in rows:
                comp, score, issues, recs, timestamp = row
                grouped_data[comp].append({
                    "health_score": score,
                    "issues": json.loads(issues),
                    "recommendations": json.loads(recs),
                    "timestamp": timestamp,
                })

            # Analyze each component
            analyses = []
            for comp, data in grouped_data.items():
                scores = [d["health_score"] for d in data]
                avg_score = statistics.mean(scores)

                # Collect all issues and recommendations
                all_issues = []
                all_recommendations = []
                for d in data:
                    all_issues.extend(d["issues"])
                    all_recommendations.extend(d["recommendations"])

                # Count most common issues
                issue_counts = Counter(all_issues)
                common_issues = [issue for issue, count in issue_counts.most_common(5)]

                # Count most common recommendations
                rec_counts = Counter(all_recommendations)
                common_recommendations = [rec for rec, count in rec_counts.most_common(5)]

                # Calculate trend
                if len(scores) >= 5:
                    recent_avg = statistics.mean(scores[-5:])
                    older_avg = statistics.mean(scores[:-5])
                    if recent_avg > older_avg + 10:
                        trend = "improving"
                    elif recent_avg < older_avg - 10:
                        trend = "degrading"
                    else:
                        trend = "stable"
                else:
                    trend = "insufficient_data"

                analysis = HealthAnalysis(
                    component=comp,
                    health_score=avg_score,
                    issues=common_issues,
                    recommendations=common_recommendations,
                    trend=trend,
                )

                analyses.append(analysis)

            conn.close()
            return analyses

        except Exception as e:
            self.logger.exception(f"Error analyzing health: {e}")
            return []

    async def detect_anomalies(self, hours: int = 24) -> list[dict[str, Any]]:
        """Detect anomalies in telemetry data."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since = (datetime.now() - timedelta(hours=hours)).isoformat()

            anomalies = []

            # Detect performance anomalies
            cursor.execute("""
                SELECT component, operation, duration, timestamp
                FROM performance_metrics
                WHERE timestamp >= ?
                ORDER BY timestamp
            """, (since,))

            performance_data = cursor.fetchall()

            # Group by component and operation
            grouped_perf = defaultdict(list)
            for row in performance_data:
                comp, op, duration, timestamp = row
                grouped_perf[(comp, op)].append((duration, timestamp))

            for (comp, op), data in grouped_perf.items():
                if len(data) < 10:
                    continue

                durations = [d[0] for d in data]
                timestamps = [d[1] for d in data]

                # Use Z-score to detect outliers
                mean_duration = statistics.mean(durations)
                std_duration = statistics.stdev(durations)

                if std_duration > 0:
                    z_scores = [(d - mean_duration) / std_duration for d in durations]

                    # Find outliers (Z-score > 2)
                    for i, z_score in enumerate(z_scores):
                        if abs(z_score) > 2:
                            anomalies.append({
                                "type": "performance_anomaly",
                                "component": comp,
                                "operation": op,
                                "timestamp": timestamps[i],
                                "duration": durations[i],
                                "z_score": z_score,
                                "severity": "high" if abs(z_score) > 3 else "medium",
                            })

            # Detect error spikes
            cursor.execute("""
                SELECT component, operation, timestamp, success
                FROM performance_metrics
                WHERE timestamp >= ?
                ORDER BY timestamp
            """, (since,))

            error_data = cursor.fetchall()

            # Group by hour
            hourly_errors = defaultdict(lambda: defaultdict(int))
            for row in error_data:
                comp, op, timestamp, success = row
                hour = datetime.fromisoformat(timestamp).replace(minute=0, second=0, microsecond=0)
                hourly_errors[hour.isoformat()][(comp, op)] += 1 if not success else 0

            # Find error spikes
            for hour, errors in hourly_errors.items():
                total_errors = sum(errors.values())
                if total_errors > 10:  # Threshold for error spike
                    anomalies.append({
                        "type": "error_spike",
                        "timestamp": hour,
                        "total_errors": total_errors,
                        "component_errors": dict(errors),
                        "severity": "high" if total_errors > 50 else "medium",
                    })

            conn.close()
            return anomalies

        except Exception as e:
            self.logger.exception(f"Error detecting anomalies: {e}")
            return []

    async def generate_recommendations(self, hours: int = 24) -> list[dict[str, Any]]:
        """Generate recommendations based on analysis."""
        try:
            recommendations = []

            # Analyze performance
            perf_analyses = await self.analyze_performance(hours=hours)
            for analysis in perf_analyses:
                if analysis.recommendations:
                    recommendations.append({
                        "type": "performance",
                        "component": analysis.component,
                        "operation": analysis.operation,
                        "recommendations": analysis.recommendations,
                        "priority": "high" if analysis.success_rate < 0.9 else "medium",
                    })

            # Analyze usage
            usage_analyses = await self.analyze_usage(hours=hours)
            for analysis in usage_analyses:
                if analysis.recommendations:
                    recommendations.append({
                        "type": "usage",
                        "project": analysis.project,
                        "service": analysis.service,
                        "recommendations": analysis.recommendations,
                        "priority": "high" if analysis.usage_pattern == "bursty" else "medium",
                    })

            # Analyze health
            health_analyses = await self.analyze_health(hours=hours)
            for analysis in health_analyses:
                if analysis.health_score < 80:
                    recommendations.append({
                        "type": "health",
                        "component": analysis.component,
                        "recommendations": analysis.recommendations,
                        "priority": "high" if analysis.health_score < 60 else "medium",
                    })

            # Detect anomalies
            anomalies = await self.detect_anomalies(hours=hours)
            for anomaly in anomalies:
                if anomaly["severity"] == "high":
                    recommendations.append({
                        "type": "anomaly",
                        "component": anomaly.get("component", "unknown"),
                        "recommendations": [f"Investigate {anomaly['type']} at {anomaly['timestamp']}"],
                        "priority": "high",
                    })

            return recommendations

        except Exception as e:
            self.logger.exception(f"Error generating recommendations: {e}")
            return []

    async def get_dashboard_data(self, hours: int = 24) -> dict[str, Any]:
        """Get data for dashboard display."""
        try:
            # Get performance analysis
            perf_analyses = await self.analyze_performance(hours=hours)

            # Get usage analysis
            usage_analyses = await self.analyze_usage(hours=hours)

            # Get health analysis
            health_analyses = await self.analyze_health(hours=hours)

            # Get anomalies
            anomalies = await self.detect_anomalies(hours=hours)

            # Get recommendations
            recommendations = await self.generate_recommendations(hours=hours)

            # Calculate summary statistics
            total_operations = sum(analysis.total_usage for analysis in usage_analyses)
            avg_health_score = statistics.mean([analysis.health_score for analysis in health_analyses]) if health_analyses else 0
            high_priority_recommendations = [r for r in recommendations if r["priority"] == "high"]

            return {
                "summary": {
                    "total_operations": total_operations,
                    "avg_health_score": avg_health_score,
                    "high_priority_recommendations": len(high_priority_recommendations),
                    "anomalies_detected": len(anomalies),
                },
                "performance": [
                    {
                        "component": analysis.component,
                        "operation": analysis.operation,
                        "avg_duration": analysis.avg_duration,
                        "success_rate": analysis.success_rate,
                        "trend": analysis.trend,
                    }
                    for analysis in perf_analyses
                ],
                "usage": [
                    {
                        "project": analysis.project,
                        "service": analysis.service,
                        "total_usage": analysis.total_usage,
                        "peak_usage": analysis.peak_usage,
                        "pattern": analysis.usage_pattern,
                    }
                    for analysis in usage_analyses
                ],
                "health": [
                    {
                        "component": analysis.component,
                        "health_score": analysis.health_score,
                        "trend": analysis.trend,
                        "issues": analysis.issues,
                    }
                    for analysis in health_analyses
                ],
                "anomalies": anomalies,
                "recommendations": recommendations,
            }

        except Exception as e:
            self.logger.exception(f"Error getting dashboard data: {e}")
            return {"error": str(e)}
