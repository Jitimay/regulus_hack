"""
Background run worker.

Dequeues run jobs from Pub/Sub (or in-memory queue in dev mode),
assembles the agent graph, and delegates execution to the Orchestrator.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.decision.agent import DecisionAgent
from app.agents.orchestrator.agent import OrchestratorAgent
from app.agents.research.agent import ResearchAgent
from app.agents.simulation.agent import SimulationAgent
from app.domain.models import RunStatus
from app.domain.runs import Run
from app.infrastructure.firestore import Repositories
from app.infrastructure.gemini import GeminiClient

logger = logging.getLogger(__name__)


class RunWorker:
    """
    Processes run jobs from the job queue.

    Each job contains a run_id. The worker:
    1. Fetches the Run from the repository.
    2. Transitions to QUEUED.
    3. Hands off to the OrchestratorAgent.
    """

    def __init__(
        self,
        repositories: Repositories,
        gemini: GeminiClient,
        simulation_count: int = 500,
        use_mock_research: bool = True,
    ) -> None:
        self._repos = repositories
        self._gemini = gemini
        self._simulation_count = simulation_count
        self._use_mock_research = use_mock_research

    async def handle_job(self, payload: dict[str, Any]) -> None:
        """Process a single job payload."""
        run_id: str = payload.get("run_id", "")
        if not run_id:
            logger.error("Received job with no run_id: %s", payload)
            return

        logger.info("worker_job_started run_id=%s", run_id)

        run = await self._repos.runs.get(run_id)
        if run is None:
            logger.error("Run not found: %s", run_id)
            return

        if run.status == RunStatus.CANCELLED:
            logger.info("Skipping cancelled run: %s", run_id)
            return

        # Build agents
        research_agent = ResearchAgent(
            gemini=self._gemini,
            use_mock=self._use_mock_research,
        )
        simulation_agent = SimulationAgent(
            gemini=self._gemini,
            simulation_count=self._simulation_count,
        )
        decision_agent = DecisionAgent(gemini=self._gemini)
        orchestrator = OrchestratorAgent(
            gemini=self._gemini,
            research_agent=research_agent,
            simulation_agent=simulation_agent,
            decision_agent=decision_agent,
            repositories=self._repos,
        )

        try:
            await orchestrator.execute(run)
            logger.info("worker_job_completed run_id=%s", run_id)
        except Exception as e:
            logger.exception("worker_job_failed run_id=%s error=%s", run_id, e)
