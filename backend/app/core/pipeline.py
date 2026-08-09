"""Scan pipeline: detect → reason → persist (read-only toward AWS)."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.reasoner import ReasoningAgent
from app.cloud.aws import AwsSandboxClient
from app.cloud.metrics import MetricsCollector
from app.cloud.mock_data import mock_managed_resources, mock_metrics_for
from app.config import Settings, get_settings
from app.core.detector import Detector
from app.models.finding import FindingRecord, FindingStatus

logger = logging.getLogger(__name__)


class ScanPipeline:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.detector = Detector(self.settings)
        self.agent = ReasoningAgent(self.settings)

    def run(self, db: Session) -> list[FindingRecord]:
        resources, metrics_fn = self._load_inventory()
        created: list[FindingRecord] = []

        for resource in resources:
            metrics = metrics_fn(resource)
            detection = self.detector.evaluate(resource, metrics)
            if detection is None:
                continue

            reasoning = self.agent.reason(detection)
            record = FindingRecord(
                resource_id=detection.resource_id,
                resource_arn=detection.resource_arn,
                resource_type=detection.resource_type.value,
                resource_name=detection.resource_name,
                region=detection.region,
                flag_type=detection.flag_type.value,
                detection_confidence=detection.confidence,
                metric_summary=detection.metric_summary.model_dump(),
                resource_metadata=detection.resource_metadata,
                explanation=reasoning.explanation,
                severity=reasoning.severity.value,
                proposed_action=reasoning.proposed_action.value,
                proposed_params=reasoning.proposed_params,
                agent_confidence=reasoning.confidence,
                estimated_monthly_savings_usd=reasoning.estimated_monthly_savings_usd,
                blast_radius=reasoning.blast_radius,
                status=FindingStatus.OPEN.value,
            )
            db.add(record)
            created.append(record)

        db.commit()
        for r in created:
            db.refresh(r)
        logger.info("Scan complete: %d findings persisted", len(created))
        return created

    def _load_inventory(self):
        if self.settings.quorom_mode == "mock":
            resources = mock_managed_resources()
            return resources, mock_metrics_for

        client = AwsSandboxClient(self.settings)
        collector = MetricsCollector(client, self.settings)
        resources = client.list_managed_resources()
        return resources, collector.collect
