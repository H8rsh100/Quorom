"""Unit tests for deterministic detection rules."""

from app.cloud.aws import ManagedResource
from app.core.detector import Detector
from app.models.finding import FlagType, MetricSummary


def _ec2(resource_id: str = "i-test", instance_type: str = "m5.large") -> ManagedResource:
    return ManagedResource(
        resource_id=resource_id,
        resource_type="ec2",
        resource_name="test",
        resource_arn=f"arn:aws:ec2:us-east-1:1:instance/{resource_id}",
        region="us-east-1",
        metadata={"instance_type": instance_type},
    )


def test_idle_ec2_flagged():
    detector = Detector()
    finding = detector.evaluate(
        _ec2(),
        MetricSummary(lookback_days=7, avg_cpu_pct=1.0, peak_cpu_pct=2.0),
    )
    assert finding is not None
    assert finding.flag_type == FlagType.IDLE


def test_oversized_ec2_flagged():
    detector = Detector()
    finding = detector.evaluate(
        _ec2(instance_type="c5.2xlarge"),
        MetricSummary(lookback_days=7, avg_cpu_pct=8.0, peak_cpu_pct=15.0),
    )
    assert finding is not None
    assert finding.flag_type == FlagType.OVERSIZED


def test_healthy_ec2_not_flagged():
    detector = Detector()
    finding = detector.evaluate(
        _ec2(),
        MetricSummary(lookback_days=7, avg_cpu_pct=45.0, peak_cpu_pct=78.0),
    )
    assert finding is None


def test_idle_lambda_flagged():
    detector = Detector()
    resource = ManagedResource(
        resource_id="fn-idle",
        resource_type="lambda",
        resource_name="fn-idle",
        resource_arn="arn:aws:lambda:us-east-1:1:function:fn-idle",
        region="us-east-1",
        metadata={"memory_mb": 128},
    )
    finding = detector.evaluate(
        resource,
        MetricSummary(lookback_days=7, avg_invocations_per_day=0.2, avg_duration_ms=100.0),
    )
    assert finding is not None
    assert finding.flag_type == FlagType.IDLE
