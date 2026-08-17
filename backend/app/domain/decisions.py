"""Decision domain models — simulation results, sensitivity, and recommendations."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import new_id, utcnow


class OutcomeDistribution(BaseModel):
    """Statistical summary of a scenario's outcome distribution."""

    mean: float
    median: float
    std: float
    p10: float  # 10th percentile (downside)
    p25: float
    p75: float
    p90: float  # 90th percentile (upside)
    min: float
    max: float
    prob_target: float  # P(outcome >= target)


class ScenarioResult(BaseModel):
    """Simulation result for a single scenario."""

    scenario_id: str
    scenario_name: str
    intervention_type: str
    cost_usd: float
    access_improvement: OutcomeDistribution  # Main outcome: household access improvement
    reliability_score: OutcomeDistribution  # Secondary: supply reliability
    robustness: float  # 0–1, fraction of Monte Carlo runs above target
    expected_households_served: float
    rank: int = 0  # Filled after comparison
    samples: list[float] = Field(default_factory=list)  # Raw MC samples (access improvement)


class SensitivityEntry(BaseModel):
    """Sensitivity of the outcome to a single variable."""

    variable_name: str
    node_description: str
    sensitivity_score: float  # 0–1, higher = more influential
    direction: str  # "positive" or "negative"
    uncertainty_contribution: float  # Fraction of total variance


class SensitivityResult(BaseModel):
    """Full sensitivity analysis result."""

    id: str = Field(default_factory=new_id)
    run_id: str
    scenario_id: str | None = None  # None = baseline
    entries: list[SensitivityEntry] = Field(default_factory=list)
    dominant_variable: str | None = None
    dominant_uncertainty_score: float = 0.0
    is_material: bool = False  # True if dominant uncertainty is above threshold
    created_at: datetime = Field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SensitivityResult":
        return cls.model_validate(data)


class AlternativeComparison(BaseModel):
    """Why an alternative was not recommended."""

    scenario_name: str
    reason: str
    key_weakness: str
    expected_impact: float


class Recommendation(BaseModel):
    """Final decision agent output."""

    id: str = Field(default_factory=new_id)
    run_id: str
    recommended_scenario_id: str
    recommended_scenario_name: str
    intervention_type: str
    expected_impact: float  # Mean access improvement (0–1)
    expected_households_served: float
    robustness: float  # 0–1
    confidence: float  # 0–1
    cost_usd: float
    summary: str
    reasoning: str
    key_risks: list[str] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)
    sensitive_variables: list[str] = Field(default_factory=list)
    evidence_items: list[str] = Field(default_factory=list)  # EvidenceItem IDs
    alternative_comparisons: list[AlternativeComparison] = Field(default_factory=list)
    conditions_for_change: list[str] = Field(default_factory=list)
    uncertainty_notes: str = ""
    research_loops_completed: int = 0
    created_at: datetime = Field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Recommendation":
        return cls.model_validate(data)


class RunResult(BaseModel):
    """Aggregated result document stored for a completed run."""

    id: str = Field(default_factory=new_id)
    run_id: str
    scenario_results: list[ScenarioResult] = Field(default_factory=list)
    sensitivity: SensitivityResult | None = None
    recommendation: Recommendation | None = None
    baseline_access_pct: float = 0.0  # Before any intervention
    research_loop_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunResult":
        return cls.model_validate(data)
