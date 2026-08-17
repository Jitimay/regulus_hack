"""
Orchestrator Agent — the autonomous workflow engine.

This is the central controller of Regulus. It coordinates the full
research → model → simulate → analyze → [re-research?] → decide loop.

Key agentic behavior:
  After the initial simulation and sensitivity analysis, the Orchestrator
  inspects whether the dominant uncertainty is MATERIAL (score >= threshold).
  If material, it triggers an additional research cycle, updates the PGM,
  reruns simulation, and re-evaluates. This loop can repeat up to
  MAX_RESEARCH_LOOPS times.

State is maintained explicitly in the OrchestratorState Pydantic model,
not in conversation history.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from app.agents.decision.agent import DecisionAgent
from app.agents.prompts import ORCHESTRATOR_SYSTEM_PROMPT
from app.agents.research.agent import ResearchAgent
from app.agents.simulation.agent import SimulationAgent
from app.domain.decisions import Recommendation, RunResult, SensitivityResult, ScenarioResult
from app.domain.evidence import ResearchFindings
from app.domain.models import AgentName, EventType, RunStatus, new_id, utcnow
from app.domain.runs import AgentEvent, Run, RunInput
from app.domain.scenarios import ScenarioSet
from app.infrastructure.firestore import Repositories
from app.infrastructure.gemini import GeminiClient
from app.pgm.graph import PGMGraph

logger = logging.getLogger(__name__)

MATERIALITY_THRESHOLD = 0.35  # Sensitivity score above which another loop is triggered
MAX_RESEARCH_LOOPS = 3


# ---------------------------------------------------------------------------
# Explicit workflow state
# ---------------------------------------------------------------------------


class ProblemDefinition(BaseModel):
    objective: str = ""
    constraints: list[str] = Field(default_factory=list)
    candidate_interventions: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    budget_usd: float = 0.0


class OrchestratorState(BaseModel):
    """Complete mutable state for one Orchestrator workflow execution."""

    run_id: str
    status: RunStatus = RunStatus.PLANNING
    problem: ProblemDefinition = Field(default_factory=ProblemDefinition)
    research_loops: int = 0
    all_findings: list[dict] = Field(default_factory=list)  # Serialized ResearchFindings
    model_built: bool = False
    simulation_complete: bool = False
    sensitivity_complete: bool = False
    dominant_variable: str | None = None
    dominant_score: float = 0.0
    additional_research_triggered: bool = False
    decision_complete: bool = False
    error: str | None = None


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class OrchestratorAgent:
    def __init__(
        self,
        gemini: GeminiClient,
        research_agent: ResearchAgent,
        simulation_agent: SimulationAgent,
        decision_agent: DecisionAgent,
        repositories: Repositories,
        max_research_loops: int = MAX_RESEARCH_LOOPS,
    ) -> None:
        self._gemini = gemini
        self._research = research_agent
        self._simulation = simulation_agent
        self._decision = decision_agent
        self._repos = repositories
        self._max_loops = max_research_loops

    async def execute(self, run: Run) -> None:
        """
        Execute the complete autonomous workflow for a run.

        This method is called by the background worker after a job is dequeued.
        It mutates run state and writes events to Firestore throughout.
        """
        state = OrchestratorState(run_id=run.id)
        all_findings: list[ResearchFindings] = []
        current_graph: PGMGraph | None = None
        scenario_results: list[ScenarioResult] = []
        sensitivity: SensitivityResult | None = None

        try:
            # ----------------------------------------------------------------
            # Step 1: Understand the problem
            # ----------------------------------------------------------------
            await self._transition(run, RunStatus.PLANNING)
            await self._emit(run.id, AgentName.ORCHESTRATOR, EventType.RUN_STARTED,
                             "Analyzing decision problem and identifying variables", "info")

            state.problem = await self._analyze_problem(run.input)
            await self._emit(
                run.id, AgentName.ORCHESTRATOR, EventType.PLANNING_COMPLETED,
                f"Problem analyzed. Objective: {state.problem.objective[:80]}",
                "success",
                metadata={"objective": state.problem.objective, "constraints": state.problem.constraints},
            )

            # ----------------------------------------------------------------
            # Step 2: Initial research
            # ----------------------------------------------------------------
            await self._transition(run, RunStatus.RESEARCHING)
            await self._emit(run.id, AgentName.RESEARCH, EventType.RESEARCH_STARTED,
                             "Gathering evidence for infrastructure variables", "info")

            t0 = time.time()
            findings = await self._research.gather_evidence(
                run_id=run.id,
                decision_question=run.input.decision_question,
                evidence_requirements=state.problem.evidence_requirements,
                research_loop=0,
            )
            all_findings.append(findings)

            await self._repos.evidence.save_many(findings.items)
            duration_ms = int((time.time() - t0) * 1000)
            await self._emit(
                run.id, AgentName.RESEARCH, EventType.RESEARCH_COMPLETED,
                f"Collected {len(findings.items)} evidence items "
                f"({findings.high_confidence_count} high, {findings.medium_confidence_count} medium, "
                f"{findings.assumption_count} assumptions)",
                "success",
                duration_ms=duration_ms,
                metadata={
                    "item_count": len(findings.items),
                    "high_confidence": findings.high_confidence_count,
                    "medium_confidence": findings.medium_confidence_count,
                    "assumptions": findings.assumption_count,
                    "missing": findings.missing_information,
                },
            )

            # ----------------------------------------------------------------
            # Step 3: Build initial PGM
            # ----------------------------------------------------------------
            await self._transition(run, RunStatus.MODELING)
            await self._emit(run.id, AgentName.SIMULATION, EventType.MODEL_BUILDING_STARTED,
                             "Constructing probabilistic graphical model", "info")

            current_graph = self._simulation.build_model(run.id, findings)
            model_data = current_graph.to_dict()
            await self._repos.models.save(run.id, model_data)
            await run_repo_update(self._repos, run, model_id=run.id)

            await self._emit(
                run.id, AgentName.SIMULATION, EventType.MODEL_VALIDATED,
                f"PGM constructed with {len(current_graph.nodes)} nodes and {len(current_graph.edges)} edges",
                "success",
                metadata={"node_count": len(current_graph.nodes), "edge_count": len(current_graph.edges)},
            )

            # Build scenario set
            scenario_set = self._simulation.build_scenarios(
                run.id,
                [i.value for i in run.input.interventions],
            )
            await self._repos.scenarios.save(scenario_set)

            # ----------------------------------------------------------------
            # Step 4: Initial simulation
            # ----------------------------------------------------------------
            await self._transition(run, RunStatus.SIMULATING)
            await self._emit(
                run.id, AgentName.SIMULATION, EventType.SIMULATION_STARTED,
                f"Running probabilistic scenario analysis ({self._simulation._simulation_count} samples)",
                "info",
            )

            t0 = time.time()
            scenario_results = await self._simulation.run_simulation(current_graph, scenario_set, seed=42)
            duration_ms = int((time.time() - t0) * 1000)

            top = next((r for r in scenario_results if r.rank == 1), scenario_results[0])
            await self._emit(
                run.id, AgentName.SIMULATION, EventType.SIMULATION_COMPLETED,
                f"Simulation complete. Tentative best: {top.scenario_name} "
                f"(impact +{top.access_improvement.mean:.1%}, robustness {top.robustness:.0%})",
                "success",
                duration_ms=duration_ms,
                metadata={
                    "scenarios": [
                        {"name": r.scenario_name, "rank": r.rank,
                         "impact_mean": round(r.access_improvement.mean, 3),
                         "robustness": round(r.robustness, 3)}
                        for r in scenario_results
                    ]
                },
            )

            # ----------------------------------------------------------------
            # Step 5: Sensitivity analysis
            # ----------------------------------------------------------------
            await self._transition(run, RunStatus.ANALYZING)
            t0 = time.time()
            sensitivity = await self._simulation.run_sensitivity(current_graph, seed=43)
            duration_ms = int((time.time() - t0) * 1000)

            await self._emit(
                run.id, AgentName.SIMULATION, EventType.SENSITIVITY_COMPLETED,
                f"Sensitivity analysis complete. Dominant variable: {sensitivity.dominant_variable} "
                f"(score: {sensitivity.dominant_uncertainty_score:.2f}, material: {sensitivity.is_material})",
                "success" if not sensitivity.is_material else "warning",
                duration_ms=duration_ms,
                metadata={
                    "dominant_variable": sensitivity.dominant_variable,
                    "dominant_score": round(sensitivity.dominant_uncertainty_score, 3),
                    "is_material": sensitivity.is_material,
                    "entries": [
                        {"variable": e.variable_name, "score": e.sensitivity_score}
                        for e in sensitivity.entries[:5]
                    ],
                },
            )

            # ----------------------------------------------------------------
            # Step 6: Autonomous uncertainty loop
            # ----------------------------------------------------------------
            loops_done = 1  # We've done 1 research pass already

            while (
                sensitivity.is_material
                and loops_done < self._max_loops
            ):
                dominant_var = sensitivity.dominant_variable
                loops_done += 1

                await self._emit(
                    run.id, AgentName.ORCHESTRATOR, EventType.UNCERTAINTY_DETECTED,
                    f"Material uncertainty detected in '{dominant_var}' (score {sensitivity.dominant_uncertainty_score:.2f} >= {MATERIALITY_THRESHOLD}). "
                    f"Initiating additional research (loop {loops_done}).",
                    "warning",
                    metadata={
                        "dominant_variable": dominant_var,
                        "score": sensitivity.dominant_uncertainty_score,
                        "loop": loops_done,
                    },
                )

                await self._emit(
                    run.id, AgentName.ORCHESTRATOR, EventType.ADDITIONAL_RESEARCH_REQUESTED,
                    f"Requesting targeted evidence on '{dominant_var}'",
                    "info",
                )

                # Re-research targeting the dominant uncertain variable
                await self._transition(run, RunStatus.RESEARCHING_AGAIN)
                t0 = time.time()
                follow_findings = await self._research.gather_evidence(
                    run_id=run.id,
                    decision_question=run.input.decision_question,
                    evidence_requirements=[
                        f"Updated evidence for: {dominant_var}",
                        f"Confidence improvement needed for: {dominant_var}",
                    ],
                    research_loop=loops_done - 1,
                    target_variable=dominant_var,
                )
                all_findings.append(follow_findings)
                await self._repos.evidence.save_many(follow_findings.items)
                duration_ms = int((time.time() - t0) * 1000)

                await self._emit(
                    run.id, AgentName.RESEARCH, EventType.EVIDENCE_COLLECTED,
                    f"Additional evidence collected: {len(follow_findings.items)} new items for '{dominant_var}'",
                    "success",
                    duration_ms=duration_ms,
                    metadata={
                        "target_variable": dominant_var,
                        "new_items": len(follow_findings.items),
                        "loop": loops_done,
                    },
                )

                # Rebuild model with accumulated evidence
                await self._transition(run, RunStatus.MODELING)
                # Merge all evidence into combined findings
                merged = _merge_findings(run.id, all_findings)
                current_graph = self._simulation.build_model(run.id, merged)
                model_data = current_graph.to_dict()
                model_data["research_loop"] = loops_done
                await self._repos.models.save(run.id, model_data)

                await self._emit(
                    run.id, AgentName.SIMULATION, EventType.MODEL_UPDATED,
                    f"PGM updated with new evidence (loop {loops_done})",
                    "success",
                    metadata={"loop": loops_done, "node_count": len(current_graph.nodes)},
                )

                # Re-run simulation
                await self._transition(run, RunStatus.SIMULATING)
                t0 = time.time()
                scenario_results = await self._simulation.run_simulation(
                    current_graph, scenario_set, seed=42 + loops_done
                )
                duration_ms = int((time.time() - t0) * 1000)

                top = next((r for r in scenario_results if r.rank == 1), scenario_results[0])
                await self._emit(
                    run.id, AgentName.SIMULATION, EventType.SIMULATION_COMPLETED,
                    f"Re-simulation complete (loop {loops_done}). Best: {top.scenario_name} "
                    f"(impact +{top.access_improvement.mean:.1%}, robustness {top.robustness:.0%})",
                    "success",
                    duration_ms=duration_ms,
                    metadata={
                        "loop": loops_done,
                        "scenarios": [
                            {"name": r.scenario_name, "rank": r.rank,
                             "impact_mean": round(r.access_improvement.mean, 3)}
                            for r in scenario_results
                        ],
                    },
                )

                # Re-run sensitivity to check if uncertainty has reduced
                await self._transition(run, RunStatus.ANALYZING)
                prev_score = sensitivity.dominant_uncertainty_score
                sensitivity = await self._simulation.run_sensitivity(
                    current_graph, seed=43 + loops_done
                )

                score_change = prev_score - sensitivity.dominant_uncertainty_score
                await self._emit(
                    run.id, AgentName.SIMULATION, EventType.SENSITIVITY_COMPLETED,
                    f"Updated sensitivity: {sensitivity.dominant_variable} score {sensitivity.dominant_uncertainty_score:.2f} "
                    f"(reduced by {score_change:.2f}). Material: {sensitivity.is_material}",
                    "success" if not sensitivity.is_material else "warning",
                    metadata={
                        "dominant_variable": sensitivity.dominant_variable,
                        "dominant_score": round(sensitivity.dominant_uncertainty_score, 3),
                        "score_reduction": round(score_change, 3),
                        "is_material": sensitivity.is_material,
                        "loop": loops_done,
                    },
                )

                await self._emit(
                    run.id, AgentName.ORCHESTRATOR, EventType.LOOP_COMPLETED,
                    f"Research loop {loops_done} complete. Uncertainty reduced by {score_change:.2f}.",
                    "success",
                    metadata={"loop": loops_done, "score_reduction": round(score_change, 3)},
                )

            run.research_loop_count = loops_done

            # ----------------------------------------------------------------
            # Step 7: Generate final recommendation
            # ----------------------------------------------------------------
            await self._transition(run, RunStatus.FINALIZING)
            await self._emit(run.id, AgentName.DECISION, EventType.DECISION_STARTED,
                             "Evaluating scenarios and generating recommendation", "info")

            recommendation = await self._decision.generate_recommendation(
                run_id=run.id,
                scenario_results=scenario_results,
                sensitivity=sensitivity,
                findings=all_findings,
                research_loop_count=loops_done,
            )

            # Assemble and store final result
            result = RunResult(
                run_id=run.id,
                scenario_results=scenario_results,
                sensitivity=sensitivity,
                recommendation=recommendation,
                research_loop_count=loops_done,
            )
            await self._repos.results.save(result)

            await self._emit(
                run.id, AgentName.DECISION, EventType.RECOMMENDATION_GENERATED,
                f"Recommendation: {recommendation.recommended_scenario_name} "
                f"(confidence {recommendation.confidence:.0%}, robustness {recommendation.robustness:.0%})",
                "success",
                metadata={
                    "recommended": recommendation.recommended_scenario_name,
                    "confidence": recommendation.confidence,
                    "robustness": recommendation.robustness,
                    "expected_impact": recommendation.expected_impact,
                },
            )

            # Mark run complete
            await self._transition(run, RunStatus.COMPLETED)
            run.result_id = result.id
            await self._repos.runs.save(run)

            await self._emit(run.id, AgentName.SYSTEM, EventType.RUN_COMPLETED,
                             f"Run completed in {loops_done} research loop(s).", "success",
                             metadata={"research_loops": loops_done})

        except Exception as exc:
            logger.exception("Orchestrator workflow failed for run %s: %s", run.id, exc)
            run.error_message = str(exc)
            if run.status not in (RunStatus.FAILED, RunStatus.CANCELLED):
                run.status = RunStatus.FAILED
                run.updated_at = utcnow()
            await self._repos.runs.save(run)
            await self._emit(
                run.id, AgentName.ORCHESTRATOR, EventType.RUN_FAILED,
                f"Run failed: {exc}",
                "error",
                metadata={"error": str(exc)},
            )

    async def _analyze_problem(self, run_input: RunInput) -> ProblemDefinition:
        """
        Use Gemini to decompose the user's problem into structured components.
        Falls back gracefully to inference from the RunInput if Gemini fails.
        """
        prompt = f"""
Analyze this infrastructure decision problem:

Decision question: {run_input.decision_question}
Context: {run_input.context or "Not provided"}
Budget: ${run_input.budget_usd:,.0f}
Communities: {[c.name for c in run_input.communities]}
Objective: {run_input.objective}
Candidate interventions: {[i.value for i in run_input.interventions]}

Return JSON:
{{
  "objective": "string — clear, measurable objective",
  "constraints": ["string"],
  "candidate_interventions": ["string"],
  "evidence_requirements": ["string — what information is needed"],
  "budget_usd": number
}}
"""
        try:
            raw = await self._gemini.generate_structured(prompt, ORCHESTRATOR_SYSTEM_PROMPT)
            return ProblemDefinition(
                objective=raw.get("objective", run_input.objective),
                constraints=raw.get("constraints", [f"Budget: ${run_input.budget_usd:,.0f}"]),
                candidate_interventions=raw.get(
                    "candidate_interventions", [i.value for i in run_input.interventions]
                ),
                evidence_requirements=raw.get(
                    "evidence_requirements",
                    ["Electricity reliability", "Rainfall patterns", "Population data"],
                ),
                budget_usd=run_input.budget_usd,
            )
        except Exception as e:
            logger.warning("Problem analysis via Gemini failed: %s — using defaults", e)
            return ProblemDefinition(
                objective=run_input.objective,
                constraints=[f"Budget: ${run_input.budget_usd:,.0f}"],
                candidate_interventions=[i.value for i in run_input.interventions],
                evidence_requirements=[
                    "Electricity grid reliability and outage frequency",
                    "Annual rainfall and seasonal variation",
                    "Population and household counts per community",
                    "Current pump infrastructure and maintenance status",
                    "Existing storage capacity",
                ],
                budget_usd=run_input.budget_usd,
            )

    async def _transition(self, run: Run, new_status: RunStatus) -> None:
        """Transition run status, handling invalid transitions gracefully."""
        from app.domain.models import is_valid_transition
        if not is_valid_transition(run.status, new_status):
            # Some transitions may already be set (e.g., MODELING after RESEARCHING_AGAIN)
            # Log but don't raise — let the workflow continue
            logger.debug(
                "Skipping invalid transition %s → %s for run %s",
                run.status, new_status, run.id
            )
            return
        run.transition(new_status)
        await self._repos.runs.update_status(
            run.id, status=new_status.value, updated_at=utcnow().isoformat()
        )

    async def _emit(
        self,
        run_id: str,
        agent: AgentName,
        event_type: EventType,
        message: str,
        status: str = "info",
        duration_ms: int | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Emit and persist an agent event."""
        event = AgentEvent(
            run_id=run_id,
            agent=agent,
            type=event_type,
            message=message,
            status=status,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
        await self._repos.events.save(event)
        logger.info(
            "agent_event run=%s agent=%s type=%s status=%s msg=%s",
            run_id, agent.value, event_type.value, status, message[:80],
        )


async def run_repo_update(repos: Repositories, run: Run, **fields: Any) -> None:
    """Update specific fields on a run document."""
    for key, val in fields.items():
        setattr(run, key, val)
    await repos.runs.save(run)


def _merge_findings(run_id: str, all_findings: list[ResearchFindings]) -> ResearchFindings:
    """
    Merge multiple research loops into a single findings object.

    Later evidence overrides earlier evidence for the same variable
    (more recent evidence is presumed more accurate).
    """
    from app.domain.evidence import ResearchFindings as RF

    # Deduplicate: keep the last evidence item per variable_name
    seen: dict[str, Any] = {}
    all_items = []
    for f in all_findings:
        for item in f.items:
            key = item.variable_name or item.claim[:30]
            seen[key] = item  # Later loop items overwrite earlier

    all_items = list(seen.values())

    merged = RF(
        run_id=run_id,
        research_loop=len(all_findings),
        query="Merged evidence from all research loops",
        items=all_items,
        summary=f"Merged {len(all_findings)} research loop(s), {len(all_items)} unique evidence items",
    )
    merged.compute_counts()
    return merged
