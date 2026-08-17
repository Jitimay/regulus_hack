"""
Runs API routes.

Thin route handlers — all business logic is in service layer.
Routes:
  POST   /api/v1/runs
  GET    /api/v1/runs/{run_id}
  GET    /api/v1/runs/{run_id}/events
  GET    /api/v1/runs/{run_id}/model
  GET    /api/v1/runs/{run_id}/scenarios
  GET    /api/v1/runs/{run_id}/results
  POST   /api/v1/runs/{run_id}/cancel
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import PublisherDep, RepositoriesDep
from app.domain.models import InterventionType, RunStatus, utcnow
from app.domain.runs import Community, Run, RunInput

router = APIRouter(prefix="/runs", tags=["runs"])


# ---------------------------------------------------------------------------
# Request / response schemas (API layer — separate from domain models)
# ---------------------------------------------------------------------------


class CommunityIn(BaseModel):
    name: str
    population: int | None = None
    current_access_pct: float | None = None
    notes: str | None = None


class CreateRunRequest(BaseModel):
    decision_question: str = Field(min_length=10, max_length=1000)
    context: str | None = Field(default=None, max_length=2000)
    budget_usd: float = Field(gt=0, le=10_000_000)
    communities: list[CommunityIn] = Field(min_length=1)
    objective: str = Field(min_length=5, max_length=500)
    interventions: list[InterventionType] = Field(min_length=1)
    custom_interventions: list[str] = Field(default_factory=list)
    demo_mode: bool = False


class CreateRunResponse(BaseModel):
    run_id: str
    status: str
    created_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreateRunResponse)
async def create_run(
    body: CreateRunRequest,
    repos: RepositoriesDep,
    publisher: PublisherDep,
) -> CreateRunResponse:
    """
    Create a new analysis run and enqueue it for asynchronous processing.
    Returns immediately with run_id — client should poll for updates.
    """
    run_input = RunInput(
        decision_question=body.decision_question,
        context=body.context,
        budget_usd=body.budget_usd,
        communities=[
            Community(**c.model_dump()) for c in body.communities
        ],
        objective=body.objective,
        interventions=body.interventions,
        custom_interventions=body.custom_interventions,
        demo_mode=body.demo_mode,
    )

    run = Run(input=run_input)
    run.transition(RunStatus.QUEUED)
    await repos.runs.save(run)

    # Publish job — worker picks it up asynchronously
    await publisher.publish_run(run.id, {"demo_mode": body.demo_mode})

    return CreateRunResponse(
        run_id=run.id,
        status=run.status.value,
        created_at=run.created_at.isoformat(),
    )


@router.get("/{run_id}", response_model=dict)
async def get_run(run_id: str, repos: RepositoriesDep) -> Any:
    """Get run status and metadata."""
    run = await repos.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run.to_dict()


@router.get("/{run_id}/events", response_model=list)
async def get_run_events(run_id: str, repos: RepositoriesDep) -> Any:
    """Get all agent events for a run, ordered by timestamp."""
    run = await repos.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    events = await repos.events.list_for_run(run_id)
    return [e.to_dict() for e in events]


@router.get("/{run_id}/model", response_model=dict)
async def get_run_model(run_id: str, repos: RepositoriesDep) -> Any:
    """Get the PGM model definition for a run."""
    run = await repos.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    model = await repos.models.get(run_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not yet available")
    return model


@router.get("/{run_id}/scenarios", response_model=dict)
async def get_run_scenarios(run_id: str, repos: RepositoriesDep) -> Any:
    """Get scenarios for a run."""
    run = await repos.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    scenario_set = await repos.scenarios.get(run_id)
    if scenario_set is None:
        raise HTTPException(status_code=404, detail="Scenarios not yet available")
    return scenario_set.to_dict()


@router.get("/{run_id}/results", response_model=dict)
async def get_run_results(run_id: str, repos: RepositoriesDep) -> Any:
    """Get simulation results and recommendation for a completed run."""
    run = await repos.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    result = await repos.results.get(run_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Results not yet available — run may still be executing",
        )
    return result.to_dict()


@router.post("/{run_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_run(run_id: str, repos: RepositoriesDep) -> dict:
    """Request cancellation of a run."""
    run = await repos.runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    if run.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED):
        return {"run_id": run_id, "status": run.status.value, "message": "Run already terminal"}

    from app.domain.models import is_valid_transition

    if is_valid_transition(run.status, RunStatus.CANCELLED):
        run.transition(RunStatus.CANCELLED)
        await repos.runs.save(run)
        return {"run_id": run_id, "status": "cancelled", "message": "Cancellation requested"}

    raise HTTPException(
        status_code=409,
        detail=f"Cannot cancel run in status: {run.status.value}",
    )
