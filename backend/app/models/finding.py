from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ResourceType(str, Enum):
    EC2 = "ec2"
    LAMBDA = "lambda"


class FlagType(str, Enum):
    IDLE = "idle"
    OVERSIZED = "oversized"


class ProposedAction(str, Enum):
    RESIZE_EC2 = "resize_ec2"
    STOP_IDLE_EC2 = "stop_idle_ec2"
    NO_ACTION = "no_action"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FindingStatus(str, Enum):
    OPEN = "open"
    REJECTED = "rejected"
    APPROVED = "approved"
    EXECUTED = "executed"


# --- SQLAlchemy ---


class FindingRecord(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_id: Mapped[str] = mapped_column(String(256), index=True)
    resource_arn: Mapped[str] = mapped_column(String(512), default="")
    resource_type: Mapped[str] = mapped_column(String(32))
    resource_name: Mapped[str] = mapped_column(String(256), default="")
    region: Mapped[str] = mapped_column(String(64), default="us-east-1")
    flag_type: Mapped[str] = mapped_column(String(32))
    detection_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    metric_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    resource_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Reasoning agent output
    explanation: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default=Severity.LOW.value)
    proposed_action: Mapped[str] = mapped_column(String(32), default=ProposedAction.NO_ACTION.value)
    proposed_params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    agent_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_monthly_savings_usd: Mapped[float] = mapped_column(Float, default=0.0)
    blast_radius: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[str] = mapped_column(String(32), default=FindingStatus.OPEN.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


# --- Pydantic (API + agent contracts) ---


class MetricSummary(BaseModel):
    lookback_days: int
    avg_cpu_pct: Optional[float] = None
    peak_cpu_pct: Optional[float] = None
    avg_invocations_per_day: Optional[float] = None
    avg_duration_ms: Optional[float] = None
    notes: str = ""


class DetectionFinding(BaseModel):
    """Output of the deterministic detector (pre-LLM)."""

    resource_id: str
    resource_arn: str = ""
    resource_type: ResourceType
    resource_name: str = ""
    region: str = "us-east-1"
    flag_type: FlagType
    confidence: float = Field(ge=0.0, le=1.0)
    metric_summary: MetricSummary
    resource_metadata: dict[str, Any] = Field(default_factory=dict)


class AgentReasoning(BaseModel):
    """Strict schema the LLM must return. Validated before persist."""

    explanation: str
    severity: Severity
    proposed_action: ProposedAction
    proposed_params: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    estimated_monthly_savings_usd: float = Field(ge=0.0, default=0.0)
    blast_radius: str = ""


class FindingOut(BaseModel):
    id: int
    resource_id: str
    resource_arn: str
    resource_type: str
    resource_name: str
    region: str
    flag_type: str
    detection_confidence: float
    metric_summary: dict[str, Any]
    resource_metadata: dict[str, Any]
    explanation: str
    severity: str
    proposed_action: str
    proposed_params: dict[str, Any]
    agent_confidence: float
    estimated_monthly_savings_usd: float
    blast_radius: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
