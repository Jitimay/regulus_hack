"""
Sensitivity Analysis Engine.

Determines which uncertain variables have the greatest influence on
the target outcome (water_access) using a variance-based approach.

Methodology:
  For each node, we compute a sensitivity score using a one-at-a-time
  (OAT) perturbation approach:
    1. Run the baseline simulation (nominal parameters).
    2. For each uncertain node, perturb its distribution upward by
       one standard deviation (or by a fixed fraction for beta params).
    3. Re-run the simulation.
    4. Sensitivity score = absolute difference in mean outcome / perturbation size.
    5. Normalize scores to [0,1].

  Additionally, we compute a Spearman rank correlation between each
  node's samples and the final water_access samples to identify
  directionality.

  Variance contribution is estimated as the fraction of total variance
  attributable to each variable using the squared sensitivity scores
  as proxy weights.

  This approach is computationally efficient and interpretable for a
  hackathon demo, while being more rigorous than simply picking random
  numbers.
"""

from __future__ import annotations

import numpy as np
from numpy.random import RandomState
from scipy import stats

from app.domain.decisions import SensitivityEntry, SensitivityResult
from app.pgm.distributions import sample_distribution
from app.pgm.graph import PGMGraph, NodeDistribution


def run_sensitivity_analysis(
    graph: PGMGraph,
    intervention: str = "baseline",
    n_samples: int = 500,
    seed: int | None = None,
    materiality_threshold: float = 0.35,
) -> SensitivityResult:
    """
    Compute sensitivity of water_access to each input variable.

    Args:
        graph: The PGM to analyze.
        intervention: Intervention name to use for overrides.
        n_samples: Monte Carlo samples per perturbation run.
        seed: RNG seed for reproducibility.
        materiality_threshold: Score above which uncertainty is "material".

    Returns:
        SensitivityResult with per-node scores and dominant variable.
    """
    rng_base = RandomState(seed or 42)

    # 1. Collect all node samples for baseline (no perturbation)
    base_samples = _simulate_graph(graph, intervention, n_samples, rng=RandomState(seed or 42))
    base_access = base_samples.get("water_access", np.zeros(n_samples))
    base_mean = float(np.mean(base_access))

    entries: list[SensitivityEntry] = []
    raw_scores: list[float] = []

    for node_name, node in graph.nodes.items():
        if node_name == "water_access":
            # Skip the target node itself
            continue

        # Compute Spearman correlation between this node's samples and access
        node_vals = base_samples.get(node_name, np.zeros(n_samples))
        if np.std(node_vals) < 1e-6:
            # Node has no variance — skip
            continue

        corr, _ = stats.spearmanr(node_vals, base_access)
        if np.isnan(corr):
            corr = 0.0

        # 2. Perturb the node upward by ~10% of its range
        perturbed_graph = _perturb_node(graph, node_name, factor=1.10)
        perturbed_samples = _simulate_graph(
            perturbed_graph, intervention, n_samples, rng=RandomState((seed or 42) + hash(node_name) % 1000)
        )
        perturbed_access = perturbed_samples.get("water_access", np.zeros(n_samples))
        perturbed_mean = float(np.mean(perturbed_access))

        sensitivity = abs(perturbed_mean - base_mean) / 0.10  # Normalized to per-unit perturbation
        raw_scores.append(sensitivity)

        direction = "positive" if corr >= 0 else "negative"
        entries.append(SensitivityEntry(
            variable_name=node_name,
            node_description=node.description[:80],
            sensitivity_score=sensitivity,  # Will normalize below
            direction=direction,
            uncertainty_contribution=0.0,  # Filled below
        ))

    # 3. Normalize scores to [0,1]
    if raw_scores:
        max_score = max(raw_scores) or 1.0
        for entry in entries:
            entry.sensitivity_score = round(entry.sensitivity_score / max_score, 3)

        # 4. Variance contribution — proportional to normalized score squared
        score_sq = [e.sensitivity_score ** 2 for e in entries]
        total_sq = sum(score_sq) or 1.0
        for entry, sq in zip(entries, score_sq):
            entry.uncertainty_contribution = round(sq / total_sq, 3)

    # Sort by sensitivity descending
    entries.sort(key=lambda e: e.sensitivity_score, reverse=True)

    dominant = entries[0] if entries else None
    dominant_score = dominant.sensitivity_score if dominant else 0.0

    return SensitivityResult(
        run_id=graph.run_id,
        entries=entries,
        dominant_variable=dominant.variable_name if dominant else None,
        dominant_uncertainty_score=dominant_score,
        is_material=dominant_score >= materiality_threshold,
    )


def _simulate_graph(
    graph: PGMGraph,
    intervention: str,
    n: int,
    rng: RandomState,
) -> dict[str, np.ndarray]:
    """Run a fast graph traversal simulation and return per-node samples."""
    from app.pgm.simulation import _compute_parent_influence  # avoid circular at module level

    topo = graph.topological_order()
    node_samples: dict[str, np.ndarray] = {}

    for node_name in topo:
        node = graph.get_node(node_name)
        if node is None:
            continue

        dist = node.apply_intervention(intervention)
        own_samples = sample_distribution(
            dist, n, rng,
            clip_low=0.0,
            clip_high=1.0 if dist.type in ("beta", "bernoulli") else None,
        )

        parents = graph.get_parents(node_name)
        if parents:
            parent_influence = _compute_parent_influence(
                node_name, parents, node_samples, graph, n
            )
            edges = [e for e in graph.edges if e.child == node_name]
            total_strength = sum(e.strength for e in edges) or 1.0
            blend_weight = min(0.5, total_strength / 2.0)
            blended = (1 - blend_weight) * own_samples + blend_weight * parent_influence
            node_samples[node_name] = np.clip(blended, 0.0, 1.0)
        else:
            node_samples[node_name] = own_samples

    return node_samples


def _perturb_node(graph: PGMGraph, node_name: str, factor: float = 1.10) -> PGMGraph:
    """
    Return a copy-like graph with the named node's distribution perturbed upward.

    We do not deep-copy the entire graph (expensive); instead we create a
    fresh graph that shares the same structure but with the target node modified.
    """
    import copy
    # Shallow copy with manual node duplication
    new_graph = PGMGraph(run_id=graph.run_id, name=graph.name)

    for name, node in graph.nodes.items():
        if name == node_name:
            # Perturb this node's distribution upward
            modified_node = copy.deepcopy(node)
            dist = modified_node.distribution
            if dist.type == "normal" and dist.mean is not None:
                dist.mean = min(dist.mean * factor, 1.0 if "fraction" in node.unit else dist.mean * factor)
            elif dist.type == "beta" and dist.alpha is not None:
                dist.alpha = dist.alpha * factor  # Higher alpha → higher mean
            elif dist.type == "uniform" and dist.high is not None:
                dist.high = dist.high * factor
            new_graph.add_node(modified_node)
        else:
            new_graph.add_node(node)

    for edge in graph.edges:
        new_graph.add_edge(edge)

    return new_graph
