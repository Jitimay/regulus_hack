"""Core domain enums, base types, and shared value objects for Regulus."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RunStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    PLANNING = "planning"
    RESEARCHING = "researching"
    MODELING = "modeling"
    SIMULATING = "simulating"
    ANALYZING = "analyzing"
    RESEARCHING_AGAIN = "researching_again"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Valid state transitions
VALID_TRANSITIONS: dict[RunStatus, list[RunStatus]] = {
    RunStatus.CREATED: [RunStatus.QUEUED, RunStatus.CANCELLED],
    RunStatus.QUEUED: [RunStatus.PLANNING, RunStatus.FAILED, RunStatus.CANCELLED],
    RunStatus.PLANNING: [RunStatus.RESEARCHING, RunStatus.FAILED, RunStatus.CANCELLED],
    RunStatus.RESEARCHING: [RunStatus.MODELING, RunStatus.FAILED, RunStatus.CANCELLED],
    RunStatus.MODELING: [RunStatus.SIMULATING, RunStatus.FAILED, RunStatus.CANCELLED],
    RunStatus.SIMULATING: [RunStatus.ANALYZING, RunStatus.FAILED, RunStatus.CANCELLED],
    RunStatus.ANALYZING: [
        RunStatus.RESEARCHING_AGAIN,
        RunStatus.FINALIZING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    ],
    RunStatus.RESEARCHING_AGAIN: [
        RunStatus.MODELING,
        RunStatus.FINALIZING,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    ],
    RunStatus.FINALIZING: [RunStatus.COMPLETED, RunStatus.FAILED],
    RunStatus.COMPLETED: [],
    RunStatus.FAILED: [],
    RunStatus.CANCELLED: [],
}


def is_valid_transition(current: RunStatus, next_: RunStatus) -> bool:
    return next_ in VALID_TRANSITIONS.get(current, [])


class AgentName(str, Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCH = "research_agent"
    SIMULATION = "simulation_agent"
    DECISION = "decision_agent"
    SYSTEM = "system"


class EventType(str, Enum):
    # Lifecycle
    RUN_CREATED = "run_created"
    RUN_QUEUED = "run_queued"
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"
    # Orchestrator
    PROBLEM_ANALYZED = "problem_analyzed"
    PLANNING_COMPLETED = "planning_completed"
    UNCERTAINTY_DETECTED = "uncertainty_detected"
    ADDITIONAL_RESEARCH_REQUESTED = "additional_research_requested"
    LOOP_COMPLETED = "loop_completed"
    # Research
    RESEARCH_STARTED = "research_started"
    EVIDENCE_COLLECTED = "evidence_collected"
    RESEARCH_COMPLETED = "research_completed"
    RESEARCH_FAILED = "research_failed"
    # Modeling
    MODEL_BUILDING_STARTED = "model_building_started"
    MODEL_VALIDATED = "model_validated"
    MODEL_UPDATED = "model_updated"
    MODEL_FAILED = "model_failed"
    # Simulation
    SIMULATION_STARTED = "simulation_started"
    SIMULATION_COMPLETED = "simulation_completed"
    SENSITIVITY_COMPLETED = "sensitivity_completed"
    SIMULATION_FAILED = "simulation_failed"
    # Decision
    DECISION_STARTED = "decision_started"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    DECISION_FAILED = "decision_failed"
    # Generic
    STATUS_UPDATE = "status_update"
    ERROR = "error"


class EvidenceStatus(str, Enum):
    EXTERNAL = "external_evidence"
    ASSUMPTION = "assumption"
    INFERRED = "inferred"
    COMPUTED = "computed"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

    @classmethod
    def from_float(cls, value: float) -> "ConfidenceLevel":
        if value >= 0.75:
            return cls.HIGH
        if value >= 0.50:
            return cls.MEDIUM
        if value >= 0.25:
            return cls.LOW
        return cls.UNKNOWN


class InterventionType(str, Enum):
    PUMP_EXPANSION = "pump_expansion"
    STORAGE_EXPANSION = "storage_expansion"
    SOLAR_PUMPING = "solar_pumping"
    DISTRIBUTION_IMPROVEMENTS = "distribution_improvements"
    COMBINED_STRATEGY = "combined_strategy"
    CUSTOM = "custom"


class NodeType(str, Enum):
    CONTINUOUS = "continuous"
    DISCRETE = "discrete"
    BINARY = "binary"
    DETERMINISTIC = "deterministic"


class SimulationScenarioStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Shared metadata
# ---------------------------------------------------------------------------


class Provenance:
    """Tracks where a piece of evidence came from."""

    def __init__(
        self,
        source: str,
        source_url: str | None = None,
        retrieved_at: datetime | None = None,
        confidence: float = 0.5,
        status: EvidenceStatus = EvidenceStatus.ASSUMPTION,
    ):
        self.source = source
        self.source_url = source_url
        self.retrieved_at = retrieved_at or utcnow()
        self.confidence = confidence
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at.isoformat(),
            "confidence": self.confidence,
            "status": self.status.value,
        }
