"""Scenario domain models — intervention definitions and simulation configurations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import InterventionType, SimulationScenarioStatus, new_id, utcnow


class InterventionModifier(BaseModel):
    """How an intervention changes a specific node's parameters."""

    node_name: str
    parameter: str  # e.g. "mean", "probability", "capacity"
    absolute_change: float | None = None
    relative_change: float | None = None  # multiplicative factor
    new_value: float | None = None
    description: str = ""


class Scenario(BaseModel):
    """A single intervention scenario to be evaluated."""

    id: str = Field(default_factory=new_id)
    run_id: str
    name: str
    description: str
    intervention_type: InterventionType
    cost_usd: float
    modifiers: list[InterventionModifier] = Field(default_factory=list)
    status: SimulationScenarioStatus = SimulationScenarioStatus.PENDING
    created_at: datetime = Field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        return cls.model_validate(data)


class ScenarioSet(BaseModel):
    """The full set of scenarios for a run, including baseline."""

    run_id: str
    scenarios: list[Scenario] = Field(default_factory=list)
    baseline_scenario_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
