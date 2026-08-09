"""CloudWatch metric pulls for managed EC2 and Lambda resources."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any, Optional

from botocore.exceptions import BotoCoreError, ClientError

from app.cloud.aws import AwsSandboxClient, ManagedResource
from app.config import Settings, get_settings
from app.models.finding import MetricSummary


def _avg(datapoints: list[dict[str, Any]], stat: str = "Average") -> Optional[float]:
    vals = [dp[stat] for dp in datapoints if stat in dp]
    return mean(vals) if vals else None


def _max(datapoints: list[dict[str, Any]], stat: str = "Maximum") -> Optional[float]:
    vals = [dp[stat] for dp in datapoints if stat in dp]
    return max(vals) if vals else None


class MetricsCollector:
    """Read-only CloudWatch collector for Quorom-managed resources."""

    def __init__(
        self,
        client: Optional[AwsSandboxClient] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or AwsSandboxClient(self.settings)

    def collect(self, resource: ManagedResource) -> MetricSummary:
        if resource.resource_type == "ec2":
            return self._ec2_metrics(resource)
        if resource.resource_type == "lambda":
            return self._lambda_metrics(resource)
        return MetricSummary(lookback_days=self.settings.lookback_days, notes="unknown resource type")

    def _window(self) -> tuple[datetime, datetime]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=self.settings.lookback_days)
        return start, end

    def _ec2_metrics(self, resource: ManagedResource) -> MetricSummary:
        start, end = self._window()
        try:
            cw = self.client._cloudwatch()
            resp = cw.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName="CPUUtilization",
                Dimensions=[{"Name": "InstanceId", "Value": resource.resource_id}],
                StartTime=start,
                EndTime=end,
                Period=3600,
                Statistics=["Average", "Maximum"],
            )
            points = resp.get("Datapoints", [])
            avg_cpu = _avg(points, "Average")
            peak_cpu = _max(points, "Maximum")
            notes = "no datapoints" if not points else ""
            return MetricSummary(
                lookback_days=self.settings.lookback_days,
                avg_cpu_pct=round(avg_cpu, 2) if avg_cpu is not None else None,
                peak_cpu_pct=round(peak_cpu, 2) if peak_cpu is not None else None,
                notes=notes,
            )
        except (ClientError, BotoCoreError) as exc:
            return MetricSummary(
                lookback_days=self.settings.lookback_days,
                notes=f"metric fetch failed: {exc}",
            )

    def _lambda_metrics(self, resource: ManagedResource) -> MetricSummary:
        start, end = self._window()
        days = max(self.settings.lookback_days, 1)
        try:
            cw = self.client._cloudwatch()
            inv = cw.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Invocations",
                Dimensions=[{"Name": "FunctionName", "Value": resource.resource_id}],
                StartTime=start,
                EndTime=end,
                Period=86400,
                Statistics=["Sum"],
            )
            dur = cw.get_metric_statistics(
                Namespace="AWS/Lambda",
                MetricName="Duration",
                Dimensions=[{"Name": "FunctionName", "Value": resource.resource_id}],
                StartTime=start,
                EndTime=end,
                Period=86400,
                Statistics=["Average"],
            )
            inv_points = inv.get("Datapoints", [])
            dur_points = dur.get("Datapoints", [])
            total_inv = sum(dp.get("Sum", 0) for dp in inv_points)
            avg_inv_per_day = total_inv / days
            avg_duration = _avg(dur_points, "Average")
            notes = "no datapoints" if not inv_points and not dur_points else ""
            return MetricSummary(
                lookback_days=self.settings.lookback_days,
                avg_invocations_per_day=round(avg_inv_per_day, 2),
                avg_duration_ms=round(avg_duration, 2) if avg_duration is not None else None,
                notes=notes,
            )
        except (ClientError, BotoCoreError) as exc:
            return MetricSummary(
                lookback_days=self.settings.lookback_days,
                notes=f"metric fetch failed: {exc}",
            )
