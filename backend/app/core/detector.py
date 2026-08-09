"""Deterministic detection rules. LLM reasons about actions; this flags signals."""

from __future__ import annotations

from typing import Optional

from app.cloud.aws import ManagedResource
from app.config import Settings, get_settings
from app.models.finding import DetectionFinding, FlagType, MetricSummary, ResourceType


class Detector:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def evaluate(
        self,
        resource: ManagedResource,
        metrics: MetricSummary,
    ) -> Optional[DetectionFinding]:
        if resource.resource_type == "ec2":
            return self._evaluate_ec2(resource, metrics)
        if resource.resource_type == "lambda":
            return self._evaluate_lambda(resource, metrics)
        return None

    def _base(
        self,
        resource: ManagedResource,
        metrics: MetricSummary,
        flag_type: FlagType,
        confidence: float,
    ) -> DetectionFinding:
        return DetectionFinding(
            resource_id=resource.resource_id,
            resource_arn=resource.resource_arn,
            resource_type=ResourceType(resource.resource_type),
            resource_name=resource.resource_name,
            region=resource.region,
            flag_type=flag_type,
            confidence=confidence,
            metric_summary=metrics,
            resource_metadata=resource.metadata,
        )

    def _evaluate_ec2(
        self,
        resource: ManagedResource,
        metrics: MetricSummary,
    ) -> Optional[DetectionFinding]:
        avg = metrics.avg_cpu_pct
        peak = metrics.peak_cpu_pct
        if avg is None:
            return None

        idle_threshold = self.settings.idle_cpu_threshold_pct
        oversize_peak = self.settings.oversize_cpu_peak_pct

        # Idle: consistently near-zero CPU
        if avg < idle_threshold and (peak is None or peak < idle_threshold * 2):
            conf = min(1.0, (idle_threshold - avg) / idle_threshold + 0.4)
            return self._base(resource, metrics, FlagType.IDLE, round(conf, 2))

        # Oversized: running but peak well below what the instance class warrants
        if peak is not None and peak < oversize_peak and avg < oversize_peak:
            conf = min(1.0, (oversize_peak - peak) / oversize_peak + 0.3)
            return self._base(resource, metrics, FlagType.OVERSIZED, round(conf, 2))

        return None

    def _evaluate_lambda(
        self,
        resource: ManagedResource,
        metrics: MetricSummary,
    ) -> Optional[DetectionFinding]:
        inv = metrics.avg_invocations_per_day
        if inv is None:
            return None

        # Idle Lambda: fewer than 1 invocation/day on average
        if inv < 1.0:
            conf = min(1.0, 0.5 + (1.0 - inv) * 0.4)
            return self._base(resource, metrics, FlagType.IDLE, round(conf, 2))

        # Oversized memory: high memory config with short duration and low traffic
        memory = resource.metadata.get("memory_mb")
        duration = metrics.avg_duration_ms
        if (
            isinstance(memory, int)
            and memory >= 1024
            and duration is not None
            and duration < 500
            and inv < 100
        ):
            conf = 0.65
            return self._base(resource, metrics, FlagType.OVERSIZED, conf)

        return None
