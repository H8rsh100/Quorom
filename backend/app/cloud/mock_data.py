"""Seeded demo resources for QUOROM_MODE=mock (no AWS credentials required)."""

from __future__ import annotations

from app.cloud.aws import ManagedResource
from app.models.finding import MetricSummary


def mock_managed_resources() -> list[ManagedResource]:
    return [
        ManagedResource(
            resource_id="i-0idlecafe01",
            resource_type="ec2",
            resource_name="staging-batch-worker",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-0idlecafe01",
            region="us-east-1",
            metadata={
                "instance_type": "m5.xlarge",
                "state": "running",
                "tags": {"quorom:managed": "true", "Name": "staging-batch-worker", "env": "staging"},
            },
        ),
        ManagedResource(
            resource_id="i-0oversize99",
            resource_type="ec2",
            resource_name="dev-api-box",
            resource_arn="arn:aws:ec2:us-east-1:123456789012:instance/i-0oversize99",
            region="us-east-1",
            metadata={
                "instance_type": "c5.2xlarge",
                "state": "running",
                "tags": {"quorom:managed": "true", "Name": "dev-api-box", "env": "dev"},
            },
        ),
        ManagedResource(
            resource_id="quorom-nightly-report",
            resource_type="lambda",
            resource_name="quorom-nightly-report",
            resource_arn="arn:aws:lambda:us-east-1:123456789012:function:quorom-nightly-report",
            region="us-east-1",
            metadata={
                "runtime": "python3.12",
                "memory_mb": 1024,
                "timeout": 60,
                "tags": {"quorom:managed": "true", "env": "staging"},
            },
        ),
        ManagedResource(
            resource_id="quorom-healthy-api",
            resource_type="lambda",
            resource_name="quorom-healthy-api",
            resource_arn="arn:aws:lambda:us-east-1:123456789012:function:quorom-healthy-api",
            region="us-east-1",
            metadata={
                "runtime": "nodejs20.x",
                "memory_mb": 256,
                "timeout": 10,
                "tags": {"quorom:managed": "true", "env": "prod-sandbox"},
            },
        ),
    ]


def mock_metrics_for(resource: ManagedResource) -> MetricSummary:
    """Deterministic metrics that exercise idle / oversized / healthy paths."""
    lookback = 7
    if resource.resource_id == "i-0idlecafe01":
        return MetricSummary(
            lookback_days=lookback,
            avg_cpu_pct=1.2,
            peak_cpu_pct=3.4,
            notes="mock idle EC2",
        )
    if resource.resource_id == "i-0oversize99":
        return MetricSummary(
            lookback_days=lookback,
            avg_cpu_pct=8.5,
            peak_cpu_pct=14.0,
            notes="mock oversized EC2",
        )
    if resource.resource_id == "quorom-nightly-report":
        return MetricSummary(
            lookback_days=lookback,
            avg_invocations_per_day=0.3,
            avg_duration_ms=420.0,
            notes="mock idle Lambda",
        )
    return MetricSummary(
        lookback_days=lookback,
        avg_invocations_per_day=4200.0,
        avg_duration_ms=85.0,
        notes="mock healthy Lambda",
    )
