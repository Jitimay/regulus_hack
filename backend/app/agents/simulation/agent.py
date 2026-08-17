"""
Model/Simulation Agent.

Translates evidence into PGM configuration, runs Monte Carlo simulation,
and interprets results. All numerical computation is delegated to the
PGM engine — this agent only orchestrates configuration and interpretation.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.prompts import SIMULATION_AGENT_SYSTEM_PROMPT
from app.domain.decisions import RunResult, SensitivityResult
from app.domain.evidence import ResearchFindings
from app.domain.models import InterventionType
from app.domain.scenarios import Scenario, ScenarioSet
from app.infrastructure.gemini import GeminiClient
from app.pgm.graph import PGMGraph
from app.pgm.sensitivity import run_sensitivity_analysis
from app.pgm.simulation import SimulationConfig, rank_scenarios, run_scenario_simulation
from app.pgm.water_model import build_water_infrastructure_model

logger = logging.getLogger(__name__)


class SimulationAgent:
    def __init__(
        self,
        gemini: GeminiClient,
        simulation_count: int = 500,
    ) -> None:
        self._gemini = gemini
        self._simulation_count = simulation_count

    def build_model(
        self,
        run_id: str,
        findings: ResearchFindings,
        prior_overrides: dict[str, dict] | None = None,
    ) -> PGMGraph:
        """
        Build a PGMGraph from research findings.

        Maps evidence items to node distribution overrides, applying
        updated confidence and parameter values from the research findings.
        """
        overrides: dict[str, dict] = dict(prior_overrides or {})

        # Apply evidence to node parameters
        for item in findings.items:
            if not item.variable_name:
                continue

            node = item.variable_name
            if node not in overrides:
                overrides[node] = {}

            # Update confidence from evidence
            overrides[node]["confidence"] = item.confidence

            # Map specific values to distribution parameters
            if item.value is not None and item.unit:
                self._apply_evidence_value(overrides, node, item)

        graph = build_water_infrastructure_model(run_id=run_id, evidence_overrides=overrides)
        errors = graph.validate()
        if errors:
            logger.error("PGM validation errors: %s", errors)
            raise ValueError(f"PGM validation failed: {errors}")

        return graph

    def _apply_evidence_value(
        self,
        overrides: dict[str, dict],
        node: str,
        item: Any,
    ) -> None:
        """Map an evidence value to the appropriate node distribution parameter."""
        value = float(item.value)

        if node == "electricity_reliability":
            # Map fraction [0,1] to Beta alpha parameter (higher confidence → higher alpha)
            if 0.0 < value <= 1.0:
                # Use method of moments: alpha = mean * kappa, beta = (1-mean) * kappa
                # kappa (concentration) scales with evidence confidence
                kappa = 3.0 + item.confidence * 8.0  # 3–11 range
                overrides[node]["alpha"] = round(value * kappa, 2)
                overrides[node]["beta"] = round((1.0 - value) * kappa, 2)

        elif node == "rainfall":
            overrides[node]["mean"] = value
            # Uncertainty is roughly 15% of mean if confidence is medium
            std_factor = 0.20 - item.confidence * 0.10  # lower confidence → higher std
            overrides[node]["std"] = round(value * std_factor, 1)

        elif node == "pump_availability":
            if 0.0 < value <= 1.0:
                kappa = 3.0 + item.confidence * 7.0
                overrides[node]["alpha"] = round(value * kappa, 2)
                overrides[node]["beta"] = round((1.0 - value) * kappa, 2)

        elif node == "water_availability":
            if value <= 2.0:  # Fraction form
                overrides[node]["mean"] = min(value, 1.0)

        elif node == "storage_level":
            overrides[node]["mean"] = value  # Days of storage

    def build_scenarios(self, run_id: str, interventions: list[str]) -> ScenarioSet:
        """
        Build the scenario set from the requested interventions.

        Maps InterventionType values to Scenario objects with appropriate
        cost allocations for a $50,000 budget.
        """
        budget = 50_000.0
        scenario_configs = {
            "pump_expansion": {
                "name": "Pump Expansion",
                "description": "Expand pumping capacity with additional electric pumps and upgraded infrastructure.",
                "cost": budget,
            },
            "storage_expansion": {
                "name": "Storage Expansion",
                "description": "Increase community water storage capacity with new tanks and reservoirs.",
                "cost": budget,
            },
            "solar_pumping": {
                "name": "Solar-Powered Pumping",
                "description": "Replace grid-dependent pumps with solar-powered systems, eliminating electricity reliability dependency.",
                "cost": budget,
            },
            "distribution_improvements": {
                "name": "Distribution Network Improvements",
                "description": "Upgrade pipes, connections, and distribution infrastructure to reduce losses.",
                "cost": budget,
            },
            "combined_strategy": {
                "name": "Combined Strategy",
                "description": "Balanced investment in solar pumping and storage expansion for maximum robustness.",
                "cost": budget,
            },
        }

        scenarios: list[Scenario] = []
        for intervention_str in interventions:
            config = scenario_configs.get(intervention_str, {
                "name": intervention_str.replace("_", " ").title(),
                "description": f"Custom intervention: {intervention_str}",
                "cost": budget,
            })
            try:
                itype = InterventionType(intervention_str)
            except ValueError:
                itype = InterventionType.CUSTOM

            scenarios.append(Scenario(
                run_id=run_id,
                name=config["name"],
                description=config["description"],
                intervention_type=itype,
                cost_usd=config["cost"],
            ))

        scenario_set = ScenarioSet(run_id=run_id, scenarios=scenarios)
        return scenario_set

    async def run_simulation(
        self,
        graph: PGMGraph,
        scenario_set: ScenarioSet,
        seed: int | None = 42,
    ) -> list[Any]:
        """
        Execute Monte Carlo simulation for all scenarios.

        Returns ranked ScenarioResult list.
        """
        config = SimulationConfig(
            n_samples=self._simulation_count,
            seed=seed,
        )

        results = []
        for scenario in scenario_set.scenarios:
            logger.info(
                "simulating scenario=%s intervention=%s",
                scenario.name,
                scenario.intervention_type.value,
            )
            result = run_scenario_simulation(graph, scenario, config)
            results.append(result)

        ranked = rank_scenarios(results)
        logger.info(
            "simulation_complete scenarios=%d top=%s robustness=%.2f",
            len(ranked),
            ranked[0].scenario_name if ranked else "none",
            ranked[0].robustness if ranked else 0.0,
        )
        return ranked

    async def run_sensitivity(
        self,
        graph: PGMGraph,
        seed: int | None = 42,
    ) -> SensitivityResult:
        """Run sensitivity analysis on the current model."""
        return run_sensitivity_analysis(
            graph,
            n_samples=min(self._simulation_count, 300),
            seed=seed,
        )
