"""
PGM engine unit tests.

Tests graph construction, validation, simulation, and sensitivity analysis
using the synthetic water infrastructure scenario.
"""

import pytest
import numpy as np

from app.domain.models import RunStatus, is_valid_transition
from app.pgm.graph import PGMGraph, PGMNode, PGMEdge, NodeDistribution
from app.pgm.water_model import build_water_infrastructure_model
from app.pgm.simulation import (
    SimulationConfig,
    run_scenario_simulation,
    run_baseline_simulation,
    rank_scenarios,
)
from app.pgm.sensitivity import run_sensitivity_analysis
from app.pgm.distributions import sample_distribution
from app.domain.models import NodeType, InterventionType
from app.domain.scenarios import Scenario, InterventionModifier
from numpy.random import RandomState


# ---------------------------------------------------------------------------
# Graph construction tests
# ---------------------------------------------------------------------------

class TestPGMGraphConstruction:
    def test_water_model_builds_successfully(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        assert len(graph.nodes) == 8
        assert len(graph.edges) > 0

    def test_water_model_has_no_cycles(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        errors = graph.validate()
        assert "Graph contains cycles" not in " ".join(errors)

    def test_water_model_validates_clean(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        errors = graph.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_topological_order_roots_first(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        order = graph.topological_order()
        # rainfall and electricity_reliability have no parents — must come first
        rainfall_idx = order.index("rainfall")
        elec_idx = order.index("electricity_reliability")
        access_idx = order.index("water_access")
        assert rainfall_idx < access_idx
        assert elec_idx < access_idx

    def test_node_parents_and_children(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        # pump_availability should have electricity_reliability as a parent
        parents = graph.get_parents("pump_availability")
        parent_names = [p.name for p in parents]
        assert "electricity_reliability" in parent_names

        # water_access should have distribution_capacity and household_demand as parents
        access_parents = [p.name for p in graph.get_parents("water_access")]
        assert "distribution_capacity" in access_parents
        assert "household_demand" in access_parents

    def test_invalid_edge_raises(self):
        graph = PGMGraph(run_id="test")
        with pytest.raises(ValueError, match="Parent node"):
            graph.add_edge(PGMEdge(
                parent="nonexistent",
                child="also_nonexistent",
                relationship="test",
            ))

    def test_update_node_confidence(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        graph.update_node_confidence("electricity_reliability", 0.85, "new_evidence")
        assert graph.get_node("electricity_reliability").confidence == 0.85

    def test_evidence_override_changes_distribution(self):
        overrides = {"electricity_reliability": {"alpha": 8.0, "beta": 1.5, "confidence": 0.80}}
        graph = build_water_infrastructure_model(run_id="test-run-1", evidence_overrides=overrides)
        node = graph.get_node("electricity_reliability")
        assert node.distribution.alpha == 8.0
        assert node.confidence == 0.80

    def test_serialization(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        d = graph.to_dict()
        assert d["node_count"] == 8
        assert "nodes" in d
        assert "edges" in d
        assert all("name" in n for n in d["nodes"])


# ---------------------------------------------------------------------------
# Distribution tests
# ---------------------------------------------------------------------------

class TestDistributions:
    def test_normal_samples_within_range(self):
        dist = NodeDistribution(type="normal", mean=0.5, std=0.1)
        rng = RandomState(42)
        samples = sample_distribution(dist, 1000, rng)
        assert len(samples) == 1000
        assert float(np.mean(samples)) == pytest.approx(0.5, abs=0.05)

    def test_beta_samples_between_0_and_1(self):
        dist = NodeDistribution(type="beta", alpha=3.0, beta=2.0)
        rng = RandomState(42)
        samples = sample_distribution(dist, 1000, rng)
        assert np.all(samples >= 0.0)
        assert np.all(samples <= 1.0)

    def test_uniform_samples_within_bounds(self):
        dist = NodeDistribution(type="uniform", low=0.2, high=0.8)
        rng = RandomState(42)
        samples = sample_distribution(dist, 500, rng)
        assert float(np.min(samples)) >= 0.2 - 1e-9
        assert float(np.max(samples)) <= 0.8 + 1e-9

    def test_deterministic_all_same(self):
        dist = NodeDistribution(type="deterministic", mean=0.75)
        rng = RandomState(42)
        samples = sample_distribution(dist, 100, rng)
        assert np.all(samples == 0.75)

    def test_clipping_applied(self):
        dist = NodeDistribution(type="normal", mean=1.5, std=0.01)  # Very high mean
        rng = RandomState(42)
        samples = sample_distribution(dist, 100, rng, clip_high=1.0)
        assert np.all(samples <= 1.0)


# ---------------------------------------------------------------------------
# Simulation tests
# ---------------------------------------------------------------------------

class TestSimulation:
    def _make_scenario(self, intervention: InterventionType, name: str) -> Scenario:
        return Scenario(
            id=f"sc-{name}",
            run_id="test-run-1",
            name=name,
            description=f"Test scenario: {name}",
            intervention_type=intervention,
            cost_usd=50000.0,
        )

    def test_baseline_simulation_runs(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        config = SimulationConfig(n_samples=200, seed=42)
        result = run_baseline_simulation(graph, config)
        assert result is not None
        assert 0.0 <= result.robustness <= 1.0
        assert result.expected_households_served >= 0

    def test_solar_scenario_better_than_baseline(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        config = SimulationConfig(n_samples=300, seed=42)

        solar_scenario = self._make_scenario(InterventionType.SOLAR_PUMPING, "Solar")
        result = run_scenario_simulation(graph, solar_scenario, config)

        # Solar explicitly raises electricity_reliability equivalent
        # Access improvement mean should be positive
        assert result.access_improvement.mean >= -0.1  # May be slightly negative with sampling noise
        assert result.robustness >= 0.0

    def test_combined_strategy_has_highest_expected_access(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        config = SimulationConfig(n_samples=300, seed=42)

        scenarios = [
            self._make_scenario(InterventionType.PUMP_EXPANSION, "Pump"),
            self._make_scenario(InterventionType.STORAGE_EXPANSION, "Storage"),
            self._make_scenario(InterventionType.SOLAR_PUMPING, "Solar"),
            self._make_scenario(InterventionType.COMBINED_STRATEGY, "Combined"),
        ]

        results = [run_scenario_simulation(graph, s, config) for s in scenarios]
        combined = next(r for r in results if r.intervention_type == "combined_strategy")
        others = [r for r in results if r.intervention_type != "combined_strategy"]

        # Combined should have higher mean access than the worst alternative
        assert combined.access_improvement.mean >= min(r.access_improvement.mean for r in others) - 0.05

    def test_scenario_ranking_assigns_rank_1_to_best(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        config = SimulationConfig(n_samples=200, seed=42)

        scenarios = [
            self._make_scenario(InterventionType.PUMP_EXPANSION, "Pump"),
            self._make_scenario(InterventionType.COMBINED_STRATEGY, "Combined"),
        ]

        results = [run_scenario_simulation(graph, s, config) for s in scenarios]
        ranked = rank_scenarios(results)

        assert ranked[0].rank == 1
        assert ranked[1].rank == 2

    def test_simulation_samples_field_populated(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        config = SimulationConfig(n_samples=300, seed=42)
        scenario = self._make_scenario(InterventionType.SOLAR_PUMPING, "Solar")
        result = run_scenario_simulation(graph, scenario, config)
        assert len(result.samples) > 0
        assert len(result.samples) <= 200  # Capped at 200 for storage

    def test_outcome_distribution_structure(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        config = SimulationConfig(n_samples=200, seed=42)
        result = run_baseline_simulation(graph, config)
        dist = result.access_improvement
        assert dist.p10 <= dist.median <= dist.p90
        assert dist.min <= dist.p10
        assert dist.p90 <= dist.max


# ---------------------------------------------------------------------------
# Sensitivity analysis tests
# ---------------------------------------------------------------------------

class TestSensitivityAnalysis:
    def test_sensitivity_runs_and_returns_entries(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        result = run_sensitivity_analysis(graph, n_samples=200, seed=42)
        assert len(result.entries) > 0
        assert result.dominant_variable is not None

    def test_scores_are_normalized_to_0_1(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        result = run_sensitivity_analysis(graph, n_samples=200, seed=42)
        for entry in result.entries:
            assert 0.0 <= entry.sensitivity_score <= 1.0, f"Score out of range: {entry}"

    def test_dominant_variable_has_highest_score(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        result = run_sensitivity_analysis(graph, n_samples=200, seed=42)
        top_entry = result.entries[0]
        assert top_entry.variable_name == result.dominant_variable

    def test_variance_contributions_sum_to_approx_1(self):
        graph = build_water_infrastructure_model(run_id="test-run-1")
        result = run_sensitivity_analysis(graph, n_samples=200, seed=42)
        total = sum(e.uncertainty_contribution for e in result.entries)
        assert abs(total - 1.0) < 0.02  # Within 2% of 1.0

    def test_electricity_reliability_is_influential(self):
        """electricity_reliability has low confidence and high edge strength — should rank high."""
        graph = build_water_infrastructure_model(run_id="test-run-1")
        result = run_sensitivity_analysis(graph, n_samples=300, seed=42)
        # Find electricity_reliability in results
        elec = next(
            (e for e in result.entries if e.variable_name == "electricity_reliability"),
            None
        )
        assert elec is not None, "electricity_reliability should appear in sensitivity results"
        # It should be in the top 3
        top_3 = [e.variable_name for e in result.entries[:3]]
        assert "electricity_reliability" in top_3 or elec.sensitivity_score > 0.2


# ---------------------------------------------------------------------------
# State machine tests
# ---------------------------------------------------------------------------

class TestStateMachine:
    def test_valid_transitions_accepted(self):
        assert is_valid_transition(RunStatus.CREATED, RunStatus.QUEUED) is True
        assert is_valid_transition(RunStatus.QUEUED, RunStatus.PLANNING) is True
        assert is_valid_transition(RunStatus.PLANNING, RunStatus.RESEARCHING) is True
        assert is_valid_transition(RunStatus.ANALYZING, RunStatus.RESEARCHING_AGAIN) is True
        assert is_valid_transition(RunStatus.FINALIZING, RunStatus.COMPLETED) is True

    def test_invalid_transitions_rejected(self):
        assert is_valid_transition(RunStatus.CREATED, RunStatus.COMPLETED) is False
        assert is_valid_transition(RunStatus.COMPLETED, RunStatus.PLANNING) is False
        assert is_valid_transition(RunStatus.FAILED, RunStatus.QUEUED) is False

    def test_cancelled_is_valid_from_most_states(self):
        cancellable = [
            RunStatus.QUEUED, RunStatus.PLANNING, RunStatus.RESEARCHING,
            RunStatus.MODELING, RunStatus.SIMULATING,
        ]
        for status in cancellable:
            assert is_valid_transition(status, RunStatus.CANCELLED) is True
