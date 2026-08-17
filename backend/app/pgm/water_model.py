"""
Water Infrastructure PGM Builder.

Constructs the Bayesian network for the water infrastructure scenario.
This function returns a fully-populated PGMGraph ready for simulation.

Graph structure (causal, approximately):

  rainfall ──────────────────────────────────────────────────┐
       │                                                       │
       ▼                                                       ▼
  water_availability ─────────────────────────────► storage_level
       │                                                       │
       ▼                                                       │
  pump_requirement                                             │
       │                                                       │
       ▼                                                       │
  electricity_reliability ──────► pump_availability            │
                                         │                     │
                                         ▼                     ▼
                                   distribution_capacity ◄─────┘
                                         │
                                         ▼
  household_demand ──────────────► water_access (target)

"""

from __future__ import annotations

from app.domain.models import EvidenceStatus, NodeType
from app.pgm.graph import NodeDistribution, PGMEdge, PGMGraph, PGMNode


def build_water_infrastructure_model(
    run_id: str,
    evidence_overrides: dict[str, dict] | None = None,
) -> PGMGraph:
    """
    Build the water infrastructure PGM.

    Args:
        run_id: The associated run ID.
        evidence_overrides: Optional dict mapping node_name → {param: value}
                            to apply updated evidence without rebuilding the whole model.
    Returns:
        A validated PGMGraph ready for simulation.
    """
    graph = PGMGraph(run_id=run_id, name="Water Infrastructure Decision Model")
    overrides = evidence_overrides or {}

    # -----------------------------------------------------------------------
    # Layer 1 — Environmental / exogenous inputs
    # -----------------------------------------------------------------------

    rainfall = PGMNode(
        name="rainfall",
        display_name="Rainfall",
        description=(
            "Annual rainfall affecting natural water availability. "
            "Higher rainfall reduces pump demand and increases storage."
        ),
        node_type=NodeType.CONTINUOUS,
        unit="mm/year",
        distribution=NodeDistribution(
            type="normal",
            mean=_override(overrides, "rainfall", "mean", 650.0),
            std=_override(overrides, "rainfall", "std", 120.0),
        ),
        confidence=_override(overrides, "rainfall", "confidence", 0.60),
        evidence_source="regional climate estimates",
        evidence_status=EvidenceStatus.ASSUMPTION,
    )

    electricity_reliability = PGMNode(
        name="electricity_reliability",
        display_name="Electricity Reliability",
        description=(
            "Fraction of time the electricity grid is operational. "
            "Critical for conventional electric pumps; solar avoids this dependency."
        ),
        node_type=NodeType.CONTINUOUS,
        unit="fraction (0–1)",
        distribution=NodeDistribution(
            type="beta",
            alpha=_override(overrides, "electricity_reliability", "alpha", 3.0),
            beta=_override(overrides, "electricity_reliability", "beta", 2.0),
        ),
        confidence=_override(overrides, "electricity_reliability", "confidence", 0.45),
        evidence_source="assumption — dominant uncertainty",
        evidence_status=EvidenceStatus.ASSUMPTION,
        intervention_overrides={
            "solar_pumping": {"alpha": 9.0, "beta": 1.0},  # Solar removes grid dependency
            "combined_strategy": {"alpha": 8.0, "beta": 1.5},
        },
    )

    household_demand = PGMNode(
        name="household_demand",
        display_name="Household Water Demand",
        description=(
            "Per-household daily water demand. Increases with population "
            "and seasonal factors."
        ),
        node_type=NodeType.CONTINUOUS,
        unit="liters/day/household",
        distribution=NodeDistribution(
            type="normal",
            mean=_override(overrides, "household_demand", "mean", 150.0),
            std=_override(overrides, "household_demand", "std", 30.0),
        ),
        confidence=_override(overrides, "household_demand", "confidence", 0.70),
        evidence_source="WHO guidelines + local assumption",
        evidence_status=EvidenceStatus.ASSUMPTION,
    )

    # -----------------------------------------------------------------------
    # Layer 2 — Infrastructure state
    # -----------------------------------------------------------------------

    water_availability = PGMNode(
        name="water_availability",
        display_name="Water Availability",
        description=(
            "Volume of water available from all sources (groundwater, "
            "surface water, rainfall-fed reservoirs) as a fraction of demand."
        ),
        node_type=NodeType.CONTINUOUS,
        unit="fraction of demand (0–2+)",
        distribution=NodeDistribution(
            type="normal",
            mean=_override(overrides, "water_availability", "mean", 0.75),
            std=_override(overrides, "water_availability", "std", 0.18),
        ),
        confidence=_override(overrides, "water_availability", "confidence", 0.55),
        evidence_source="derived from rainfall + groundwater estimates",
        evidence_status=EvidenceStatus.INFERRED,
        intervention_overrides={
            "pump_expansion": {"mean": 0.88, "std": 0.15},
            "storage_expansion": {"mean": 0.85, "std": 0.12},
            "combined_strategy": {"mean": 0.93, "std": 0.10},
        },
    )

    storage_level = PGMNode(
        name="storage_level",
        display_name="Storage Capacity",
        description=(
            "Current storage capacity as a fraction of community peak demand. "
            "Higher storage buffers supply variability."
        ),
        node_type=NodeType.CONTINUOUS,
        unit="days of storage",
        distribution=NodeDistribution(
            type="normal",
            mean=_override(overrides, "storage_level", "mean", 1.2),
            std=_override(overrides, "storage_level", "std", 0.5),
        ),
        confidence=_override(overrides, "storage_level", "confidence", 0.65),
        evidence_source="infrastructure survey estimates",
        evidence_status=EvidenceStatus.ASSUMPTION,
        intervention_overrides={
            "storage_expansion": {"mean": 3.5, "std": 0.6},
            "combined_strategy": {"mean": 3.0, "std": 0.5},
        },
    )

    pump_availability = PGMNode(
        name="pump_availability",
        display_name="Pump Availability",
        description=(
            "Fraction of time pumps are operational, affected by electricity "
            "reliability, maintenance quality, and equipment age."
        ),
        node_type=NodeType.CONTINUOUS,
        unit="fraction (0–1)",
        distribution=NodeDistribution(
            type="beta",
            alpha=_override(overrides, "pump_availability", "alpha", 4.0),
            beta=_override(overrides, "pump_availability", "beta", 2.0),
        ),
        confidence=_override(overrides, "pump_availability", "confidence", 0.50),
        evidence_source="derived from electricity_reliability",
        evidence_status=EvidenceStatus.INFERRED,
        intervention_overrides={
            "pump_expansion": {"alpha": 6.0, "beta": 2.0},
            "solar_pumping": {"alpha": 8.0, "beta": 1.5},
            "combined_strategy": {"alpha": 8.0, "beta": 1.2},
        },
    )

    # -----------------------------------------------------------------------
    # Layer 3 — Derived capacity
    # -----------------------------------------------------------------------

    distribution_capacity = PGMNode(
        name="distribution_capacity",
        display_name="Distribution Capacity",
        description=(
            "The effective fraction of water supply that reaches households. "
            "Combines pump availability, storage, pipe network quality, "
            "and water availability."
        ),
        node_type=NodeType.CONTINUOUS,
        unit="fraction of demand satisfied (0–1)",
        distribution=NodeDistribution(
            type="beta",
            alpha=_override(overrides, "distribution_capacity", "alpha", 3.5),
            beta=_override(overrides, "distribution_capacity", "beta", 2.0),
        ),
        confidence=_override(overrides, "distribution_capacity", "confidence", 0.55),
        evidence_source="derived from pump_availability + storage_level + water_availability",
        evidence_status=EvidenceStatus.INFERRED,
        intervention_overrides={
            "pump_expansion": {"alpha": 5.5, "beta": 2.0},
            "storage_expansion": {"alpha": 5.0, "beta": 2.0},
            "solar_pumping": {"alpha": 6.5, "beta": 1.8},
            "distribution_improvements": {"alpha": 7.0, "beta": 1.5},
            "combined_strategy": {"alpha": 7.5, "beta": 1.2},
        },
    )

    # -----------------------------------------------------------------------
    # Layer 4 — Target outcome
    # -----------------------------------------------------------------------

    water_access = PGMNode(
        name="water_access",
        display_name="Household Water Access",
        description=(
            "Fraction of households with reliable water access (>= 80% of "
            "daily requirement met on >= 80% of days). This is the primary "
            "optimization target."
        ),
        node_type=NodeType.CONTINUOUS,
        unit="fraction of households (0–1)",
        distribution=NodeDistribution(
            type="beta",
            alpha=_override(overrides, "water_access", "alpha", 3.0),
            beta=_override(overrides, "water_access", "beta", 3.5),
        ),
        confidence=_override(overrides, "water_access", "confidence", 0.50),
        evidence_source="derived from distribution_capacity + household_demand",
        evidence_status=EvidenceStatus.INFERRED,
        intervention_overrides={
            "pump_expansion": {"alpha": 5.0, "beta": 3.0},
            "storage_expansion": {"alpha": 4.5, "beta": 3.0},
            "solar_pumping": {"alpha": 5.5, "beta": 2.5},
            "distribution_improvements": {"alpha": 5.0, "beta": 2.5},
            "combined_strategy": {"alpha": 7.0, "beta": 2.0},
        },
    )

    # -----------------------------------------------------------------------
    # Add nodes in topological order (roots first)
    # -----------------------------------------------------------------------
    graph.add_node(rainfall)
    graph.add_node(electricity_reliability)
    graph.add_node(household_demand)
    graph.add_node(water_availability)
    graph.add_node(storage_level)
    graph.add_node(pump_availability)
    graph.add_node(distribution_capacity)
    graph.add_node(water_access)

    # -----------------------------------------------------------------------
    # Add edges (causal links)
    # -----------------------------------------------------------------------
    graph.add_edge(PGMEdge(
        parent="rainfall",
        child="water_availability",
        relationship="Higher rainfall increases available water",
        strength=0.70,
        direction="positive",
    ))
    graph.add_edge(PGMEdge(
        parent="rainfall",
        child="storage_level",
        relationship="Rainfall partially replenishes storage",
        strength=0.45,
        direction="positive",
    ))
    graph.add_edge(PGMEdge(
        parent="electricity_reliability",
        child="pump_availability",
        relationship="Grid reliability directly limits electric pump uptime",
        strength=0.80,
        direction="positive",
    ))
    graph.add_edge(PGMEdge(
        parent="water_availability",
        child="distribution_capacity",
        relationship="Source water must be available before distribution is possible",
        strength=0.65,
        direction="positive",
    ))
    graph.add_edge(PGMEdge(
        parent="storage_level",
        child="distribution_capacity",
        relationship="Higher storage buffers supply gaps and reduces shortage frequency",
        strength=0.55,
        direction="positive",
    ))
    graph.add_edge(PGMEdge(
        parent="pump_availability",
        child="distribution_capacity",
        relationship="Pumps are needed to move water; downtime reduces delivered volume",
        strength=0.75,
        direction="positive",
    ))
    graph.add_edge(PGMEdge(
        parent="distribution_capacity",
        child="water_access",
        relationship="Effective distribution capacity determines household access",
        strength=0.85,
        direction="positive",
    ))
    graph.add_edge(PGMEdge(
        parent="household_demand",
        child="water_access",
        relationship="Higher demand is harder to satisfy with fixed capacity",
        strength=0.50,
        direction="negative",
    ))

    return graph


def _override(
    overrides: dict[str, dict],
    node_name: str,
    param: str,
    default: float,
) -> float:
    """Return overridden value if present, otherwise default."""
    return overrides.get(node_name, {}).get(param, default)
