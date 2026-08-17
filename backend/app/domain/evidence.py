"""Evidence domain model — structured research findings with provenance."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import ConfidenceLevel, EvidenceStatus, new_id, utcnow


class EvidenceItem(BaseModel):
    """A single evidence claim with full provenance tracking."""

    id: str = Field(default_factory=new_id)
    run_id: str
    claim: str
    value: Any | None = None  # Numeric/structured value when applicable
    unit: str | None = None
    variable_name: str | None = None  # Maps to a PGM node name
    source: str
    source_url: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    status: EvidenceStatus = EvidenceStatus.ASSUMPTION
    retrieved_at: datetime = Field(default_factory=utcnow)
    research_loop: int = 0  # Which research loop produced this
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceItem":
        return cls.model_validate(data)


class ResearchFindings(BaseModel):
    """Aggregated output of a research phase."""

    run_id: str
    research_loop: int
    query: str
    items: list[EvidenceItem] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    assumption_count: int = 0
    summary: str = ""
    completed_at: datetime = Field(default_factory=utcnow)

    def compute_counts(self) -> None:
        self.high_confidence_count = sum(
            1 for i in self.items if i.confidence_level == ConfidenceLevel.HIGH
        )
        self.medium_confidence_count = sum(
            1 for i in self.items if i.confidence_level == ConfidenceLevel.MEDIUM
        )
        self.low_confidence_count = sum(
            1 for i in self.items if i.confidence_level == ConfidenceLevel.LOW
        )
        self.assumption_count = sum(
            1 for i in self.items if i.status == EvidenceStatus.ASSUMPTION
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
