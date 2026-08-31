"""
Monte Carlo Simulation Engine.

Performs probabilistic scenario analysis by:
1. Sampling all uncertain nodes N times (Monte Carlo).
2. Propagating values through the causal graph.
3. Computing outcome distributions for each scenario.
4. Calculating robustness (P(outcome >= target)).

Key design decision:
- The simulation propagates parent samples to children using weighted
  combination, respecting edge strengths and directions.
- This is NOT a full Bayesian network inference (which would require
  specifying complete CPTs for every node pair). Instead, it uses a
  DAG-aware Monte Carlo approach that:
    a) Samples root nodes from their prior distributions.
    b) For non-root nodes, blends parent-influenced adjustments with
       the node's own distribution to model conditional dependencies.
    c) Applies intervention overrides to change node parameters.
  This approach is computationally tractable, understandable, and
  produces meaningful sensitivity analysis.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from numpy.random import RandomState

from app.domain.decisions import OutcomeDistribution, ScenarioResult
from app.domain.models import InterventionType
from app.domain.scenarios import Scenario
from app.pgm.distributions import compute_outcome_distribution, sample_distribution
from app.pgm.graph import PGMGraph


# Target: fraction of households with reliable access
OUTCOME_TARGET = 0.45  # Realistic for peri-urban Burundi context
TOTAL_HOUSEHOLDS = 4500  # Combined three-community estimate


@dataclass
class SimulationConfig:
    n_samples: int = 500
    seed: int | None = None
    outcome_target: float = OUTCOME_TARGET
    total_households: int = TOTAL_HOUSEHOLDS


def run_scenario_simulation(
    graph: PGMGraph,
    scenario: Scenario,
    config: SimulationConfig,
) -> ScenarioResult:
    """
    Run Monte Carlo simulation for a single scenario.

    Returns a ScenarioResult with full outcome distributions.
    """
    rng = RandomState(config.seed)
    n = config.n_samples
    intervention = scenario.intervention_type.value

    # Sample all nodes in topological order so parents are computed before children
    topo = graph.topological_order()
    node_samples: dict[str, np.ndarray] = {}

    for node_name in topo:
        node = graph.get_node(node_name)
        if node is None:
            continue

        # Get distribution (apply intervention override if applicable)
        dist = node.apply_intervention(intervention)

        # Sample the node's own distribution
        own_samples = sample_distribution(
            dist, n, rng, clip_low=0.0, clip_high=1.0 if dist.type in ("beta", "bernoulli") else None
        )

        # Blend parent influence into this node's samples
        parents = graph.get_parents(node_name)
        if parents:
            parent_influence = _compute_parent_influence(
                node_name, parents, node_samples, graph, n
            )
            edges = [e for e in graph.edges if e.child == node_name]
            total_strength = sum(e.strength for e in edges) or 1.0
            blend_weight = min(0.5, total_strength / 2.0)  # Max 50% parent influence

            node_samples[node_name] = (
                (1.0 - blend_weight) * own_samples
                + blend_weight * parent_influence
            )
            node_samples[node_name] = np.clip(node_samples[node_name], 0.0, 1.0)
        else:
            node_samples[node_name] = own_samples

    # Primary outcome: water_access
    access_samples = node_samples.get("water_access", np.zeros(n))
    access_stats = compute_outcome_distribution(access_samples)
    access_stats["prob_target"] = float(np.mean(access_samples >= config.outcome_target))

    # Secondary outcome: distribution_capacity (reliability proxy)
    reliability_samples = node_samples.get("distribution_capacity", np.zeros(n))
    reliability_stats = compute_outcome_distribution(reliability_samples)
    reliability_stats["prob_target"] = float(np.mean(reliability_samples >= 0.65))

    # Compute baseline (no intervention) for improvement delta
    baseline_access = _compute_baseline_access(graph, n, rng=RandomState(config.seed + 1 if config.seed else 99))
    improvement_samples = access_samples - baseline_access

    robustness = float(np.mean(access_samples >= config.outcome_target))
    expected_households = float(np.mean(access_samples) * config.total_households)

    return ScenarioResult(
        scenario_id=scenario.id,
        scenario_name=scenario.name,
        intervention_type=scenario.intervention_type.value,
        cost_usd=scenario.cost_usd,
        access_improvement=OutcomeDistribution(**{
            **compute_outcome_distribution(improvement_samples),
            "prob_target": float(np.mean(improvement_samples >= 0.05)),
        }),
        reliability_score=OutcomeDistribution(**reliability_stats),
        robustness=robustness,
        expected_households_served=expected_households,
        samples=list(access_samples[:200].tolist()),  # Store first 200 for frontend distribution chart
    )


def run_baseline_simulation(
    graph: PGMGraph,
    config: SimulationConfig,
) -> ScenarioResult:
    """Run simulation with no intervention applied."""
    from app.domain.scenarios import Scenario, InterventionModifier
    baseline_scenario = Scenario(
        id="baseline",
        run_id=graph.run_id,
        name="Baseline (No Intervention)",
        description="Current state without any investment",
        intervention_type=InterventionType.CUSTOM,
        cost_usd=0.0,
    )
    # Temporarily neutralize intervention overrides by using a non-matching key
    result = run_scenario_simulation(graph, baseline_scenario, config)
    return result


def _compute_baseline_access(graph: PGMGraph, n: int, rng: RandomState) -> np.ndarray:
    """
    Compute baseline water_access samples without any intervention.
    Used to compute improvement delta for scenario results.
    """
    topo = graph.topological_order()
    node_samples: dict[str, np.ndarray] = {}

    for node_name in topo:
        node = graph.get_node(node_name)
        if node is None:
            continue
        # No intervention — use base distribution
        dist = node.distribution
        own_samples = sample_distribution(
            dist, n, rng, clip_low=0.0, clip_high=1.0 if dist.type in ("beta", "bernoulli") else None
        )
        parents = graph.get_parents(node_name)
        if parents:
            parent_influence = _compute_parent_influence(
                node_name, parents, node_samples, graph, n
            )
            edges = [e for e in graph.edges if e.child == node_name]
            total_strength = sum(e.strength for e in edges) or 1.0
            blend_weight = min(0.5, total_strength / 2.0)
            blended = (1.0 - blend_weight) * own_samples + blend_weight * parent_influence
            node_samples[node_name] = np.clip(blended, 0.0, 1.0)
        else:
            node_samples[node_name] = own_samples

    return node_samples.get("water_access", np.full(n, 0.46))


def _compute_parent_influence(
    node_name: str,
    parents: list,
    node_samples: dict[str, np.ndarray],
    graph: PGMGraph,
    n: int,
) -> np.ndarray:
    """
    Compute parent-weighted influence on a child node.

    Uses edge strength and direction to blend parent samples into
    an influence signal for the child node.
    """
    influence = np.zeros(n)
    total_weight = 0.0

    for parent in parents:
        if parent.name not in node_samples:
            continue
        # Find the connecting edge
        edge = next(
            (e for e in graph.edges if e.parent == parent.name and e.child == node_name),
            None,
        )
        if edge is None:
            continue

        weight = edge.strength
        parent_vals = node_samples[parent.name]

        if edge.direction == "negative":
            # Negative relationship: high parent → lower child
            influence += weight * (1.0 - parent_vals)
        else:
            influence += weight * parent_vals

        total_weight += weight

    if total_weight > 0:
        influence /= total_weight

    return np.clip(influence, 0.0, 1.0)


def rank_scenarios(results: list[ScenarioResult]) -> list[ScenarioResult]:
    """
    Rank scenarios by a composite score that balances:
    - Expected access improvement (50% weight)
    - Robustness — P(outcome >= target) (30% weight)
    - Downside protection — 1 - P10 loss (20% weight)
    """
    if not results:
        return results

    for r in results:
        improvement_mean = r.access_improvement.mean
        robustness = r.robustness
        downside = max(0.0, r.access_improvement.p10)  # Positive p10 = no downside
        r._composite = 0.50 * improvement_mean + 0.30 * robustness + 0.20 * (downside + 0.5)

    ranked = sorted(results, key=lambda r: r._composite, reverse=True)
    for i, r in enumerate(ranked):
        r.rank = i + 1
        del r._composite
    return ranked
