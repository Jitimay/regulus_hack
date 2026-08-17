# Regulus — Probabilistic Graphical Model

## Purpose

The PGM is the mathematical core of Regulus. It represents the causal structure of the water infrastructure system as a Bayesian network (directed acyclic graph), enabling probabilistic inference and sensitivity analysis.

---

## Graph structure

```
rainfall ─────────────────────────────────────────┐
    │                                               │
    ▼                                               ▼
water_availability ──────────────────────► storage_level
    │                                               │
    └──────────────────┐                            │
                       ▼                            │
electricity_reliability ──► pump_availability       │
                                   │                │
                                   ▼                ▼
                            distribution_capacity ◄─┘
                                   │
                     household_demand
                           │       │
                           └──────►▼
                              water_access  ← TARGET
```

---

## Nodes

| Node | Type | Unit | Role |
|---|---|---|---|
| `rainfall` | Continuous | mm/year | Exogenous — drives water availability and storage |
| `electricity_reliability` | Continuous | fraction (0–1) | **Dominant uncertainty** — drives pump availability |
| `household_demand` | Continuous | L/day/household | Exogenous — increases pressure on distribution |
| `water_availability` | Continuous | fraction of demand | Derived — combines rainfall + groundwater sources |
| `storage_level` | Continuous | days of storage | Infrastructure — buffers supply variability |
| `pump_availability` | Continuous | fraction (0–1) | Derived — depends heavily on electricity reliability |
| `distribution_capacity` | Continuous | fraction of demand satisfied | Aggregated — combines pump, storage, water availability |
| `water_access` | Continuous | fraction of households | **Target outcome** |

---

## Distributions

Each node has a parameterized probability distribution:

- **Normal** — used for continuous variables with symmetric uncertainty (rainfall, water_availability, household_demand)
- **Beta** — used for bounded fractions [0,1] (electricity_reliability, pump_availability, distribution_capacity, water_access)

### Beta distribution interpretation

For Beta(α, β):
- Mean = α / (α + β)
- Higher α+β = more concentrated (higher confidence)
- Example: electricity_reliability with α=3, β=2 → mean=0.60, moderate uncertainty

---

## Evidence → distribution update

When new evidence arrives (via the Research Agent), the Simulation Agent translates it into distribution parameter updates using the **method of moments**:

For a Beta distribution:
```
κ (concentration) = 3.0 + confidence × 8.0   # range: 3–11
α = mean_estimate × κ
β = (1 - mean_estimate) × κ
```

Higher confidence evidence produces higher κ (tighter distribution).

---

## Intervention modifiers

Each node stores intervention-specific distribution overrides. When a scenario is simulated, the relevant overrides replace the baseline parameters:

```python
# Example: solar_pumping eliminates electricity dependency for pump_availability
"solar_pumping": {"alpha": 8.0, "beta": 1.5}   # mean ≈ 0.84, high confidence
```

Interventions that directly address a node's bottleneck produce the largest improvements.

---

## Simulation methodology

### Monte Carlo propagation

The simulation runs N samples (default: 500 in dev, 2000 in demo mode) through the DAG in topological order:

```
For each sample i in 1..N:
  For each node in topological_order:
    sample_own = draw from node.distribution (with intervention override)
    if node has parents:
      parent_influence = weighted average of parent samples
                         (weighted by edge.strength, signed by edge.direction)
      blend_weight = min(0.5, total_edge_strength / 2.0)
      node_sample[i] = (1 - blend_weight) × sample_own
                     + blend_weight × parent_influence
    else:
      node_sample[i] = sample_own
```

This approach:
- Is computationally tractable (no CPT enumeration required)
- Respects causal structure via topological ordering
- Allows edge strength and direction to modulate parent influence
- Is fully reproducible with a fixed seed

### Outcome computation

For `water_access` samples across N runs:
- **Mean** — expected access improvement
- **Median** — typical outcome
- **P10, P25, P75, P90** — uncertainty bands
- **Robustness** = P(outcome ≥ 0.60) — fraction of runs meeting the target

---

## Sensitivity analysis

### Methodology

Two complementary approaches are combined:

**1. One-at-a-time (OAT) perturbation**

For each node, the simulation reruns with that node's distribution mean increased by 10%. The sensitivity score is the absolute change in `water_access` mean, normalized to [0,1]:

```
sensitivity(node) = |mean(perturbed) - mean(baseline)| / 0.10
```

**2. Spearman rank correlation**

Computed between each node's sample array and the final `water_access` sample array. Used to determine direction (positive/negative relationship) and validate OAT results.

**3. Variance contribution**

Estimated as the squared normalized sensitivity score, normalized to sum to 1.0:

```
variance_contribution(node) = score²  / Σ(score²)
```

### Materiality threshold

A dominant variable is **material** if its sensitivity score ≥ 0.35. This threshold triggers the autonomous re-research loop in the Orchestrator.

### Expected result for the demo scenario

`electricity_reliability` typically ranks highest because:
- It has low initial confidence (0.45–0.55)
- It has a high-strength edge to `pump_availability` (0.80)
- `pump_availability` has a high-strength edge to `distribution_capacity` (0.75)
- `distribution_capacity` has the strongest edge to `water_access` (0.85)

---

## Reproducibility

All simulations use a seeded `numpy.random.RandomState`. The default seed is 42 for the initial simulation and 43 for sensitivity. Re-research loops use incremented seeds (42+loop, 43+loop) to maintain independence while remaining reproducible.

---

## Assumptions and limitations

- The causal graph structure is a model, not a ground truth. Real water systems are more complex.
- All demo data is synthetic. Real deployment would require validated local parameters.
- The simulation propagation method is an approximation of full Bayesian inference — it does not compute exact posterior distributions.
- Sensitivity scores are relative within a run, not absolute physical quantities.
- The model does not capture inter-community dynamics, seasonal variation, or implementation timeline effects.
