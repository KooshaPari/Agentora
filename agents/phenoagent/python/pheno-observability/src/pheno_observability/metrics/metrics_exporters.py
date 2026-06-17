"""Metric exporter backends for CloudWatch and Datadog.

This module provides backend adapters for exporting metrics to cloud monitoring services.
"""

from __future__ import annotations

from typing import Any

from pheno.observability.ports import MetricData, MetricType


class CloudWatchBackend:
    """AWS CloudWatch metrics backend adapter.

    Exports metrics to AWS CloudWatch using the PutMetricData API.
    """

    def __init__(
        self,
        namespace: str = "PhenoSDK",
        region: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ):
        """Initialize CloudWatch backend.

        Args:
            namespace: CloudWatch namespace
            region: AWS region
            aws_access_key_id: Optional AWS access key
            aws_secret_access_key: Optional AWS secret key
        """
        self.namespace = namespace
        self.region = region
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

    async def export(self, metrics: list[MetricData]) -> list[dict[str, Any]]:
        """Export metrics in CloudWatch format.

        Args:
            metrics: Metrics to export

        Returns:
            List of CloudWatch metric data dictionaries
        """
        metric_data = []

        for metric in metrics:
            cw_metric = {
                "MetricName": metric.name.replace(".", "/"),
                "Value": metric.value,
                "Timestamp": metric.timestamp,
                "Unit": metric.metadata.get("unit", "None"),
            }

            if metric.labels:
                cw_metric["Dimensions"] = [
                    {"Name": k, "Value": v} for k, v in metric.labels.items()
                ]

            metric_data.append(cw_metric)

        return metric_data

    async def push(self, metrics: list[MetricData]) -> bool:
        """Push metrics to CloudWatch.

        Args:
            metrics: Metrics to push

        Returns:
            True if successful
        """
        try:
            import boto3

            session_kwargs: dict[str, Any] = {"region_name": self.region}
            if self.aws_access_key_id and self.aws_secret_access_key:
                session_kwargs.update(
                    {
                        "aws_access_key_id": self.aws_access_key_id,
                        "aws_secret_access_key": self.aws_secret_access_key,
                    },
                )

            client = boto3.client("cloudwatch", **session_kwargs)
            metric_data = await self.export(metrics)

            for i in range(0, len(metric_data), 20):
                batch = metric_data[i : i + 20]
                client.put_metric_data(Namespace=self.namespace, MetricData=batch)

            return True
        except Exception:
            return False


class DatadogBackend:
    """Datadog metrics backend adapter.

    Exports metrics to Datadog using the Datadog API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        app_key: str | None = None,
        site: str = "datadoghq.com",
    ):
        """Initialize Datadog backend.

        Args:
            api_key: Datadog API key
            app_key: Datadog application key
            site: Datadog site (e.g., datadoghq.com, datadoghq.eu)
        """
        self.api_key = api_key
        self.app_key = app_key
        self.site = site

    async def export(self, metrics: list[MetricData]) -> dict[str, Any]:
        """Export metrics in Datadog format.

        Args:
            metrics: Metrics to export

        Returns:
            Datadog-formatted metrics dictionary
        """
        series = []

        for metric in metrics:
            dd_metric = {
                "metric": metric.name,
                "points": [[metric.timestamp, metric.value]],
                "type": "gauge" if metric.metric_type == MetricType.GAUGE else "count",
            }

            if metric.labels:
                dd_metric["tags"] = [f"{k}:{v}" for k, v in metric.labels.items()]

            series.append(dd_metric)

        return {"series": series}

    async def push(self, metrics: list[MetricData]) -> bool:
        """Push metrics to Datadog.

        Args:
            metrics: Metrics to push

        Returns:
            True if successful
        """
        if not self.api_key:
            return False

        try:
            import aiohttp

            data = await self.export(metrics)
            url = f"https://api.{self.site}/api/v1/series"

            headers = {
                "DD-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as resp:
                    return resp.status == 202
        except Exception:
            return False
