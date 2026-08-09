"""Claude reasoning agent - structured JSON only, validated via Pydantic."""

from __future__ import annotations

import json
import logging
from typing import Optional

import anthropic
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.models.finding import AgentReasoning, DetectionFinding, ProposedAction, Severity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Quorom, an AWS cost and reliability reasoning agent.
You receive a detected finding about an EC2 instance or Lambda function.
Return ONLY valid JSON matching this schema (no markdown, no prose outside JSON):
{
  "explanation": "string - why this finding matters",
  "severity": "low|medium|high",
  "proposed_action": "resize_ec2|stop_idle_ec2|no_action",
  "proposed_params": {},
  "confidence": 0.0-1.0,
  "estimated_monthly_savings_usd": number,
  "blast_radius": "string - what could go wrong if the action is wrong"
}

Rules:
- proposed_action must be one of the enum values exactly.
- For idle EC2 prefer stop_idle_ec2 with {"target_state": "stopped"}.
- For oversized EC2 prefer resize_ec2 with {"target_instance_type": "<smaller type>"}.
- For Lambda idle or unclear cases use no_action (Day 1 has no Lambda execute path).
- Never invent AWS API calls. Never request credentials.
- Be conservative: if unsure, use no_action and lower confidence.
"""


class ReasoningAgent:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self._client: Optional[anthropic.Anthropic] = None
        if self.settings.anthropic_api_key:
            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    def reason(self, finding: DetectionFinding) -> AgentReasoning:
        if self.settings.quorom_mode == "mock" or not self._client:
            return self._mock_reason(finding)

        user_payload = {
            "resource_id": finding.resource_id,
            "resource_type": finding.resource_type.value,
            "resource_name": finding.resource_name,
            "flag_type": finding.flag_type.value,
            "detection_confidence": finding.confidence,
            "metric_summary": finding.metric_summary.model_dump(),
            "resource_metadata": finding.resource_metadata,
        }
        raw = self._call_claude(json.dumps(user_payload, indent=2))
        try:
            return self._parse(raw)
        except (ValidationError, json.JSONDecodeError) as first_err:
            logger.warning("Malformed agent JSON, retrying once: %s", first_err)
            raw_retry = self._call_claude(
                json.dumps(user_payload, indent=2)
                + "\n\nYour previous reply was invalid. Return ONLY valid JSON."
            )
            try:
                return self._parse(raw_retry)
            except (ValidationError, json.JSONDecodeError) as second_err:
                logger.error("Agent JSON failed after retry: %s", second_err)
                return AgentReasoning(
                    explanation="Agent output failed validation; defaulting to no_action.",
                    severity=Severity.LOW,
                    proposed_action=ProposedAction.NO_ACTION,
                    proposed_params={},
                    confidence=0.0,
                    estimated_monthly_savings_usd=0.0,
                    blast_radius="none - no action proposed",
                )

    def _call_claude(self, user_content: str) -> str:
        assert self._client is not None
        message = self._client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        parts = []
        for block in message.content:
            if hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts).strip()

    def _parse(self, raw: str) -> AgentReasoning:
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        return AgentReasoning.model_validate(data)

    def _mock_reason(self, finding: DetectionFinding) -> AgentReasoning:
        """Deterministic reasoning for local demo without Claude keys."""
        meta = finding.resource_metadata
        if finding.flag_type.value == "idle" and finding.resource_type.value == "ec2":
            itype = meta.get("instance_type", "unknown")
            return AgentReasoning(
                explanation=(
                    f"{finding.resource_name} ({itype}) averaged "
                    f"{finding.metric_summary.avg_cpu_pct}% CPU over "
                    f"{finding.metric_summary.lookback_days} days. "
                    "It looks abandoned staging capacity; stopping it is low-risk."
                ),
                severity=Severity.MEDIUM,
                proposed_action=ProposedAction.STOP_IDLE_EC2,
                proposed_params={"target_state": "stopped"},
                confidence=0.91,
                estimated_monthly_savings_usd=112.0,
                blast_radius="Jobs scheduled on this host would fail until restarted.",
            )
        if finding.flag_type.value == "oversized" and finding.resource_type.value == "ec2":
            itype = meta.get("instance_type", "c5.2xlarge")
            return AgentReasoning(
                explanation=(
                    f"{finding.resource_name} runs on {itype} but peak CPU was only "
                    f"{finding.metric_summary.peak_cpu_pct}%. A smaller type should "
                    "cover observed load with headroom."
                ),
                severity=Severity.LOW,
                proposed_action=ProposedAction.RESIZE_EC2,
                proposed_params={"target_instance_type": "c5.large", "current_instance_type": itype},
                confidence=0.84,
                estimated_monthly_savings_usd=68.0,
                blast_radius="Brief stop/start required; traffic spikes above prior peak could throttle.",
            )
        if finding.flag_type.value == "idle" and finding.resource_type.value == "lambda":
            return AgentReasoning(
                explanation=(
                    f"Lambda {finding.resource_name} averages "
                    f"{finding.metric_summary.avg_invocations_per_day} invocations/day. "
                    "Likely unused; Day 1 proposes no_action pending approval workflow."
                ),
                severity=Severity.LOW,
                proposed_action=ProposedAction.NO_ACTION,
                proposed_params={"suggestion": "review_and_delete"},
                confidence=0.78,
                estimated_monthly_savings_usd=4.0,
                blast_radius="Deleting without checking EventBridge/S3 triggers could break a nightly job.",
            )
        return AgentReasoning(
            explanation="Signal does not clearly warrant remediation.",
            severity=Severity.LOW,
            proposed_action=ProposedAction.NO_ACTION,
            proposed_params={},
            confidence=0.5,
            estimated_monthly_savings_usd=0.0,
            blast_radius="none",
        )
