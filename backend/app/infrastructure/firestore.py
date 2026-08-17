"""
Firestore persistence layer.

Provides typed repository classes for every major domain document.
All repositories depend on a FirestoreClient abstraction so they can be
swapped for an in-memory mock in tests or local development.

Collections:
  runs/           — Run documents (top-level)
  events/         — AgentEvent documents
  models/         — PGM serialized graph
  scenarios/      — ScenarioSet documents
  results/        — RunResult documents
  evidence/       — EvidenceItem documents
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any

from app.domain.decisions import RunResult, SensitivityResult
from app.domain.evidence import EvidenceItem, ResearchFindings
from app.domain.runs import AgentEvent, Run
from app.domain.scenarios import ScenarioSet

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class RunRepository(ABC):
    @abstractmethod
    async def save(self, run: Run) -> None: ...

    @abstractmethod
    async def get(self, run_id: str) -> Run | None: ...

    @abstractmethod
    async def update_status(self, run_id: str, **fields: Any) -> None: ...


class EventRepository(ABC):
    @abstractmethod
    async def save(self, event: AgentEvent) -> None: ...

    @abstractmethod
    async def list_for_run(self, run_id: str) -> list[AgentEvent]: ...


class ModelRepository(ABC):
    @abstractmethod
    async def save(self, run_id: str, model_data: dict[str, Any]) -> None: ...

    @abstractmethod
    async def get(self, run_id: str) -> dict[str, Any] | None: ...


class ScenarioRepository(ABC):
    @abstractmethod
    async def save(self, scenario_set: ScenarioSet) -> None: ...

    @abstractmethod
    async def get(self, run_id: str) -> ScenarioSet | None: ...


class ResultRepository(ABC):
    @abstractmethod
    async def save(self, result: RunResult) -> None: ...

    @abstractmethod
    async def get(self, run_id: str) -> RunResult | None: ...


class EvidenceRepository(ABC):
    @abstractmethod
    async def save_many(self, items: list[EvidenceItem]) -> None: ...

    @abstractmethod
    async def list_for_run(self, run_id: str) -> list[EvidenceItem]: ...


# ---------------------------------------------------------------------------
# In-memory implementation (local dev / testing)
# ---------------------------------------------------------------------------


class InMemoryRunRepository(RunRepository):
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def save(self, run: Run) -> None:
        self._store[run.id] = run.to_dict()

    async def get(self, run_id: str) -> Run | None:
        data = self._store.get(run_id)
        return Run.from_dict(data) if data else None

    async def update_status(self, run_id: str, **fields: Any) -> None:
        if run_id in self._store:
            self._store[run_id].update(fields)


class InMemoryEventRepository(EventRepository):
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = defaultdict(list)

    async def save(self, event: AgentEvent) -> None:
        self._store[event.run_id].append(event.to_dict())

    async def list_for_run(self, run_id: str) -> list[AgentEvent]:
        return [AgentEvent.from_dict(d) for d in self._store.get(run_id, [])]


class InMemoryModelRepository(ModelRepository):
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def save(self, run_id: str, model_data: dict[str, Any]) -> None:
        self._store[run_id] = model_data

    async def get(self, run_id: str) -> dict[str, Any] | None:
        return self._store.get(run_id)


class InMemoryScenarioRepository(ScenarioRepository):
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def save(self, scenario_set: ScenarioSet) -> None:
        self._store[scenario_set.run_id] = scenario_set.to_dict()

    async def get(self, run_id: str) -> ScenarioSet | None:
        data = self._store.get(run_id)
        return ScenarioSet.model_validate(data) if data else None


class InMemoryResultRepository(ResultRepository):
    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def save(self, result: RunResult) -> None:
        self._store[result.run_id] = result.to_dict()

    async def get(self, run_id: str) -> RunResult | None:
        data = self._store.get(run_id)
        return RunResult.from_dict(data) if data else None


class InMemoryEvidenceRepository(EvidenceRepository):
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = defaultdict(list)

    async def save_many(self, items: list[EvidenceItem]) -> None:
        for item in items:
            self._store[item.run_id].append(item.to_dict())

    async def list_for_run(self, run_id: str) -> list[EvidenceItem]:
        return [EvidenceItem.from_dict(d) for d in self._store.get(run_id, [])]


# ---------------------------------------------------------------------------
# Firestore implementation (Google Cloud)
# ---------------------------------------------------------------------------


class FirestoreRunRepository(RunRepository):
    def __init__(self, db: Any) -> None:
        self._db = db

    async def save(self, run: Run) -> None:
        loop = asyncio.get_event_loop()
        ref = self._db.collection("runs").document(run.id)
        await loop.run_in_executor(None, ref.set, run.to_dict())

    async def get(self, run_id: str) -> Run | None:
        loop = asyncio.get_event_loop()
        ref = self._db.collection("runs").document(run_id)
        doc = await loop.run_in_executor(None, ref.get)
        if not doc.exists:
            return None
        return Run.from_dict(doc.to_dict())

    async def update_status(self, run_id: str, **fields: Any) -> None:
        loop = asyncio.get_event_loop()
        ref = self._db.collection("runs").document(run_id)
        await loop.run_in_executor(None, ref.update, fields)


class FirestoreEventRepository(EventRepository):
    def __init__(self, db: Any) -> None:
        self._db = db

    async def save(self, event: AgentEvent) -> None:
        loop = asyncio.get_event_loop()
        ref = self._db.collection("events").document(event.id)
        await loop.run_in_executor(None, ref.set, event.to_dict())

    async def list_for_run(self, run_id: str) -> list[AgentEvent]:
        loop = asyncio.get_event_loop()
        query = self._db.collection("events").where("run_id", "==", run_id).order_by("timestamp")

        def _fetch():
            return list(query.stream())

        docs = await loop.run_in_executor(None, _fetch)
        return [AgentEvent.from_dict(d.to_dict()) for d in docs]


class FirestoreModelRepository(ModelRepository):
    def __init__(self, db: Any) -> None:
        self._db = db

    async def save(self, run_id: str, model_data: dict[str, Any]) -> None:
        loop = asyncio.get_event_loop()
        ref = self._db.collection("models").document(run_id)
        await loop.run_in_executor(None, ref.set, {"run_id": run_id, **model_data})

    async def get(self, run_id: str) -> dict[str, Any] | None:
        loop = asyncio.get_event_loop()
        ref = self._db.collection("models").document(run_id)
        doc = await loop.run_in_executor(None, ref.get)
        return doc.to_dict() if doc.exists else None


class FirestoreScenarioRepository(ScenarioRepository):
    def __init__(self, db: Any) -> None:
        self._db = db

    async def save(self, scenario_set: ScenarioSet) -> None:
        loop = asyncio.get_event_loop()
        ref = self._db.collection("scenarios").document(scenario_set.run_id)
        await loop.run_in_executor(None, ref.set, scenario_set.to_dict())

    async def get(self, run_id: str) -> ScenarioSet | None:
        loop = asyncio.get_event_loop()
        ref = self._db.collection("scenarios").document(run_id)
        doc = await loop.run_in_executor(None, ref.get)
        if not doc.exists:
            return None
        return ScenarioSet.model_validate(doc.to_dict())


class FirestoreResultRepository(ResultRepository):
    def __init__(self, db: Any) -> None:
        self._db = db

    async def save(self, result: RunResult) -> None:
        loop = asyncio.get_event_loop()
        ref = self._db.collection("results").document(result.run_id)
        await loop.run_in_executor(None, ref.set, result.to_dict())

    async def get(self, run_id: str) -> RunResult | None:
        loop = asyncio.get_event_loop()
        ref = self._db.collection("results").document(run_id)
        doc = await loop.run_in_executor(None, ref.get)
        if not doc.exists:
            return None
        return RunResult.from_dict(doc.to_dict())


class FirestoreEvidenceRepository(EvidenceRepository):
    def __init__(self, db: Any) -> None:
        self._db = db

    async def save_many(self, items: list[EvidenceItem]) -> None:
        loop = asyncio.get_event_loop()
        batch = self._db.batch()
        for item in items:
            ref = self._db.collection("evidence").document(item.id)
            batch.set(ref, item.to_dict())
        await loop.run_in_executor(None, batch.commit)

    async def list_for_run(self, run_id: str) -> list[EvidenceItem]:
        loop = asyncio.get_event_loop()
        query = self._db.collection("evidence").where("run_id", "==", run_id)

        def _fetch():
            return list(query.stream())

        docs = await loop.run_in_executor(None, _fetch)
        return [EvidenceItem.from_dict(d.to_dict()) for d in docs]


# ---------------------------------------------------------------------------
# Repository bundle (injected into services)
# ---------------------------------------------------------------------------


class Repositories:
    """Aggregates all repositories into a single injectable object."""

    def __init__(
        self,
        runs: RunRepository,
        events: EventRepository,
        models: ModelRepository,
        scenarios: ScenarioRepository,
        results: ResultRepository,
        evidence: EvidenceRepository,
    ) -> None:
        self.runs = runs
        self.events = events
        self.models = models
        self.scenarios = scenarios
        self.results = results
        self.evidence = evidence


def create_in_memory_repositories() -> Repositories:
    """Create a fully in-memory repository set for local dev/testing."""
    return Repositories(
        runs=InMemoryRunRepository(),
        events=InMemoryEventRepository(),
        models=InMemoryModelRepository(),
        scenarios=InMemoryScenarioRepository(),
        results=InMemoryResultRepository(),
        evidence=InMemoryEvidenceRepository(),
    )


def create_firestore_repositories(project_id: str, database: str = "(default)") -> Repositories:
    """Create Firestore-backed repositories for production."""
    try:
        from google.cloud import firestore

        db = firestore.Client(project=project_id, database=database)
        return Repositories(
            runs=FirestoreRunRepository(db),
            events=FirestoreEventRepository(db),
            models=FirestoreModelRepository(db),
            scenarios=FirestoreScenarioRepository(db),
            results=FirestoreResultRepository(db),
            evidence=FirestoreEvidenceRepository(db),
        )
    except ImportError:
        logger.warning("google-cloud-firestore not installed; falling back to in-memory repositories")
        return create_in_memory_repositories()
