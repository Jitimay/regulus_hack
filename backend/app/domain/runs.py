"""Run domain model — represents a single Regulus analysis run."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import (
    AgentName,
    EventType,
    InterventionType,
    RunStatus,
    is_valid_transition,
    new_id,
    utcnow,
)


class Community(BaseModel):
    name: str
    population: int | None = None
    current_access_pct: float | None = None  # 0–1
    notes: str | None = None


class RunInput(BaseModel):
    """User-supplied decision problem."""

    decision_question: str
    context: str | None = None
    budget_usd: float
    communities: list[Community]
    objective: str
    interventions: list[InterventionType]
    custom_interventions: list[str] = Field(default_factory=list)
    demo_mode: bool = False


class Run(BaseModel):
    """A Regulus analysis run — the top-level document stored in Firestore."""

    id: str = Field(default_factory=new_id)
    status: RunStatus = RunStatus.CREATED
    input: RunInput
    research_loop_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    # References to related documents
    model_id: str | None = None
    result_id: str | None = None

    def transition(self, new_status: RunStatus) -> None:
        if not is_valid_transition(self.status, new_status):
            raise ValueError(
                f"Invalid state transition: {self.status} → {new_status}"
            )
        self.status = new_status
        self.updated_at = utcnow()
        if new_status == RunStatus.PLANNING and self.started_at is None:
            self.started_at = utcnow()
        if new_status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
            self.completed_at = utcnow()

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Run":
        return cls.model_validate(data)


class AgentEvent(BaseModel):
    """A structured event emitted by an agent during a run."""

    id: str = Field(default_factory=new_id)
    run_id: str
    timestamp: datetime = Field(default_factory=utcnow)
    agent: AgentName
    type: EventType
    message: str
    status: str = "info"  # info | success | warning | error
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentEvent":
        return cls.model_validate(data)
