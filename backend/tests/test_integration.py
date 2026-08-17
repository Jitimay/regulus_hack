"""
Integration test — full end-to-end workflow using in-memory repositories.

Tests the complete path:
  Create Run → Worker → Orchestrator → Research → PGM → Simulation
  → Sensitivity → [Re-research loop] → Decision → Results stored
"""

import asyncio
import pytest
import pytest_asyncio

from app.config import Settings
from app.agents.decision.agent import DecisionAgent
from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.research.agent import ResearchAgent
from app.agents.simulation.agent import SimulationAgent
from app.domain.models import InterventionType, RunStatus
from app.domain.runs import Community, Run, RunInput
from app.infrastructure.firestore import create_in_memory_repositories
from app.infrastructure.gemini import GeminiClient


@pytest.fixture
def repos():
    return create_in_memory_repositories()


@pytest.fixture
def gemini():
    # Always mock in tests
    return GeminiClient(model_name="gemini-2.0-flash-exp", mock_mode=True)


@pytest.fixture
def run_input():
    return RunInput(
        decision_question="How should we allocate $50,000 to improve reliable water access across three communities?",
        context="Maji Valley region with three communities: Kijani, Mtoni, Amani",
        budget_usd=50_000.0,
        communities=[
            Community(name="Kijani", population=6000),
            Community(name="Mtoni", population=4000),
            Community(name="Amani", population=3000),
        ],
        objective="Maximize reliable household water access while controlling downside risk",
        interventions=[
            InterventionType.PUMP_EXPANSION,
            InterventionType.STORAGE_EXPANSION,
            InterventionType.SOLAR_PUMPING,
            InterventionType.COMBINED_STRATEGY,
        ],
        demo_mode=True,
    )


@pytest.mark.asyncio
async def test_full_workflow(repos, gemini, run_input):
    """
    Full end-to-end workflow test.

    Verifies that a complete run executes, produces simulation results,
    runs the re-research loop, and generates a recommendation.
    """
    run = Run(input=run_input)
    run.transition(RunStatus.QUEUED)
    await repos.runs.save(run)

    # Build agents
    research_agent = ResearchAgent(gemini=gemini, use_mock=True)
    simulation_agent = SimulationAgent(gemini=gemini, simulation_count=200)
    decision_agent = DecisionAgent(gemini=gemini)
    orchestrator = OrchestratorAgent(
        gemini=gemini,
        research_agent=research_agent,
        simulation_agent=simulation_agent,
        decision_agent=decision_agent,
        repositories=repos,
    )

    await orchestrator.execute(run)

    # -----------------------------------------------------------------------
    # Verify run state
    # -----------------------------------------------------------------------
    stored_run = await repos.runs.get(run.id)
    assert stored_run is not None
    assert stored_run.status == RunStatus.COMPLETED, f"Expected COMPLETED, got {stored_run.status}"
    assert stored_run.error_message is None

    # -----------------------------------------------------------------------
    # Verify events were emitted
    # -----------------------------------------------------------------------
    events = await repos.events.list_for_run(run.id)
    assert len(events) >= 8, f"Expected at least 8 events, got {len(events)}"

    event_types = {e.type.value for e in events}
    assert "run_started" in event_types
    assert "planning_completed" in event_types
    assert "research_completed" in event_types
    assert "model_validated" in event_types
    assert "simulation_completed" in event_types
    assert "sensitivity_completed" in event_types
    assert "recommendation_generated" in event_types
    assert "run_completed" in event_types

    # -----------------------------------------------------------------------
    # Verify model was stored
    # -----------------------------------------------------------------------
    model_data = await repos.models.get(run.id)
    assert model_data is not None
    assert model_data["node_count"] == 8
    assert len(model_data["nodes"]) == 8

    # -----------------------------------------------------------------------
    # Verify scenarios were built
    # -----------------------------------------------------------------------
    scenario_set = await repos.scenarios.get(run.id)
    assert scenario_set is not None
    assert len(scenario_set.scenarios) == 4

    # -----------------------------------------------------------------------
    # Verify results
    # -----------------------------------------------------------------------
    result = await repos.results.get(run.id)
    assert result is not None
    assert len(result.scenario_results) == 4
    assert result.sensitivity is not None
    assert result.recommendation is not None

    # -----------------------------------------------------------------------
    # Verify recommendation quality
    # -----------------------------------------------------------------------
    rec = result.recommendation
    assert rec.recommended_scenario_name != ""
    assert 0.0 <= rec.confidence <= 1.0
    assert 0.0 <= rec.robustness <= 1.0
    assert len(rec.key_risks) >= 2
    assert len(rec.key_assumptions) >= 2
    assert len(rec.conditions_for_change) >= 2
    assert rec.expected_households_served > 0

    # -----------------------------------------------------------------------
    # Verify re-research loop ran
    # -----------------------------------------------------------------------
    # The sensitivity analysis should have detected electricity_reliability
    # as dominant, triggering at least one additional research loop
    assert result.research_loop_count >= 1

    # Evidence should include items from the follow-up loop
    evidence_items = await repos.evidence.list_for_run(run.id)
    assert len(evidence_items) >= 6

    # -----------------------------------------------------------------------
    # Verify scenario ranking
    # -----------------------------------------------------------------------
    ranks = [r.rank for r in result.scenario_results]
    assert 1 in ranks
    assert sorted(ranks) == list(range(1, len(ranks) + 1))

    print(f"\n=== Integration test passed ===")
    print(f"Run status: {stored_run.status.value}")
    print(f"Events emitted: {len(events)}")
    print(f"Research loops: {result.research_loop_count}")
    print(f"Recommended: {rec.recommended_scenario_name}")
    print(f"Confidence: {rec.confidence:.0%}")
    print(f"Robustness: {rec.robustness:.0%}")
    print(f"Expected households served: {rec.expected_households_served:,.0f}")


@pytest.mark.asyncio
async def test_run_creates_and_queues(repos):
    """Test that a run is saved with QUEUED status."""
    run_input = RunInput(
        decision_question="Test decision question",
        budget_usd=10_000.0,
        communities=[Community(name="TestCommunity")],
        objective="Test objective",
        interventions=[InterventionType.PUMP_EXPANSION],
    )
    run = Run(input=run_input)
    run.transition(RunStatus.QUEUED)
    await repos.runs.save(run)

    stored = await repos.runs.get(run.id)
    assert stored is not None
    assert stored.status == RunStatus.QUEUED
    assert stored.id == run.id


@pytest.mark.asyncio
async def test_event_ordering(repos):
    """Events should be retrievable per run."""
    from app.domain.models import AgentName, EventType
    from app.domain.runs import AgentEvent

    run_id = "test-event-run"
    for i, etype in enumerate([EventType.RUN_STARTED, EventType.PLANNING_COMPLETED]):
        event = AgentEvent(
            run_id=run_id,
            agent=AgentName.ORCHESTRATOR,
            type=etype,
            message=f"Event {i}",
        )
        await repos.events.save(event)

    events = await repos.events.list_for_run(run_id)
    assert len(events) == 2
    assert events[0].type == EventType.RUN_STARTED


@pytest.mark.asyncio
async def test_model_persistence(repos):
    """Model data can be saved and retrieved."""
    model_data = {"run_id": "r1", "node_count": 8, "nodes": [], "edges": []}
    await repos.models.save("r1", model_data)
    retrieved = await repos.models.get("r1")
    assert retrieved["node_count"] == 8


@pytest.mark.asyncio
async def test_result_round_trip(repos):
    """RunResult can be saved and retrieved intact."""
    from app.domain.decisions import RunResult
    result = RunResult(run_id="r1", research_loop_count=1)
    await repos.results.save(result)
    retrieved = await repos.results.get("r1")
    assert retrieved is not None
    assert retrieved.run_id == "r1"
