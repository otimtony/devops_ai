from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

# Pydantic models
class IncidentInput(BaseModel):
    """Information supplied by a user who wants to investigate an incident."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    incident_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this investigation.",
    )

    description: str = Field(
        min_length=10,
        max_length=5_000,
        description="Description of the problem being investigated.",
    )

    log_sample: str = Field(
        min_length=1,
        max_length=20_000,
        description="A sample of application or infrastructure logs.",
    )

    environment: Literal[
        "development",
        "staging",
        "production",
        "unknown",
    ] = "unknown"

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class EvidenceItem(BaseModel):
    """A specific piece of evidence identified during investigation."""

    model_config = ConfigDict(extra="forbid")

    observation: str = Field(min_length=1, max_length=1_000)
    source: str = Field(min_length=1, max_length=500)
    evidence_type: Literal["fact", "inference"]


class IncidentReport(BaseModel):
    """Structured output that our agent workflow will produce."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str
    summary: str = Field(min_length=1, max_length=2_000)

    severity: Literal["critical", "high", "medium", "low", "unknown"]

    likely_causes: list[str] = Field(default_factory=list, max_length=10)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=50)

    recommended_actions: list[str] = Field(
        default_factory=list,
        max_length=15,
    )

    confidence: float = Field(ge=0.0, le=1.0)
    requires_human_approval: bool = True
    human_approval_status: Literal["pending", "approved", "rejected"] = "pending"
    human_approval_reason: str | None = Field(
        default=None,
        max_length=1_000,
        description="Optional justification for the user approval/rejection decision.",
    )