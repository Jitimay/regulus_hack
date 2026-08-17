"""
Probabilistic Graphical Model — graph representation.

Implements a DAG-based Bayesian network structure for the water
infrastructure decision problem. The graph is fully serializable so
the frontend can render it and the simulation engine can traverse it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from app.domain.models import EvidenceStatus, NodeType


@dataclass
class NodeDistribution:
    """Parameters of a node's probability distribution."""

    type: str  # "normal", "beta", "uniform", "bernoulli", "deterministic"
    # Normal
    mean: float | None = None
    std: float | None = None
    # Beta (0–1 outcomes)
    alpha: float | None = None
    beta: float | None = None
    # Uniform
    low: float | None = None
    high: float | None = None
    # Bernoulli / discrete
    probability: float | None = None
    # Conditional modifier (applied when parent is True/high)
    conditional_modifier: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NodeDistribution":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PGMNode:
    """A single node in the probabilistic graphical model."""

    name: str
    display_name: str
    description: str
    node_type: NodeType
    unit: str = ""

    # Distribution parameters (baseline)
    distribution: NodeDistribution = field(default_factory=lambda: NodeDistribution(type="normal", mean=0.5, std=0.1))

    # Uncertainty / confidence
    confidence: float = 0.5  # 0–1
    evidence_source: str = "assumption"
    evidence_status: EvidenceStatus = EvidenceStatus.ASSUMPTION

    # Intervention modifiers — key: intervention name, value: dict of distribution param overrides
    intervention_overrides: dict[str, dict[str, float]] = field(default_factory=dict)

    # Computed during simulation
    sensitivity_score: float | None = None

    def apply_intervention(self, intervention_name: str) -> NodeDistribution:
        """Return a modified distribution for this intervention."""
        override = self.intervention_overrides.get(intervention_name)
        if not override:
            return self.distribution

        base = NodeDistribution(**self.distribution.__dict__)
        for param, value in override.items():
            if hasattr(base, param):
                setattr(base, param, value)
        return base

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "node_type": self.node_type.value,
            "unit": self.unit,
            "distribution": self.distribution.to_dict(),
            "confidence": self.confidence,
            "evidence_source": self.evidence_source,
            "evidence_status": self.evidence_status.value,
            "intervention_overrides": self.intervention_overrides,
            "sensitivity_score": self.sensitivity_score,
        }


@dataclass
class PGMEdge:
    """A directed edge in the PGM representing a causal relationship."""

    parent: str
    child: str
    relationship: str  # Human-readable description of the causal link
    strength: float = 0.5  # 0–1, how strongly parent influences child
    direction: str = "positive"  # "positive" or "negative"

    def to_dict(self) -> dict[str, Any]:
        return {
            "parent": self.parent,
            "child": self.child,
            "relationship": self.relationship,
            "strength": self.strength,
            "direction": self.direction,
        }


class PGMGraph:
    """
    Probabilistic Graphical Model for infrastructure decision analysis.

    Wraps a NetworkX DiGraph with typed node/edge metadata and
    provides serialization for storage and frontend rendering.
    """

    def __init__(self, run_id: str, name: str = "Water Infrastructure PGM"):
        self.run_id = run_id
        self.name = name
        self._graph: nx.DiGraph = nx.DiGraph()
        self._nodes: dict[str, PGMNode] = {}
        self._edges: list[PGMEdge] = []

    def add_node(self, node: PGMNode) -> None:
        self._nodes[node.name] = node
        self._graph.add_node(node.name, **node.to_dict())

    def add_edge(self, edge: PGMEdge) -> None:
        if edge.parent not in self._nodes:
            raise ValueError(f"Parent node '{edge.parent}' not in graph")
        if edge.child not in self._nodes:
            raise ValueError(f"Child node '{edge.child}' not in graph")
        self._edges.append(edge)
        self._graph.add_edge(edge.parent, edge.child, **edge.to_dict())

    def get_node(self, name: str) -> PGMNode | None:
        return self._nodes.get(name)

    def get_parents(self, node_name: str) -> list[PGMNode]:
        return [self._nodes[p] for p in self._graph.predecessors(node_name) if p in self._nodes]

    def get_children(self, node_name: str) -> list[PGMNode]:
        return [self._nodes[c] for c in self._graph.successors(node_name) if c in self._nodes]

    def validate(self) -> list[str]:
        """Return list of validation errors (empty = valid)."""
        errors = []
        if not self._nodes:
            errors.append("Graph has no nodes")
        if not nx.is_directed_acyclic_graph(self._graph):
            errors.append("Graph contains cycles — not a valid DAG")
        # Check all edges reference valid nodes
        for edge in self._edges:
            if edge.parent not in self._nodes:
                errors.append(f"Edge references unknown parent: {edge.parent}")
            if edge.child not in self._nodes:
                errors.append(f"Edge references unknown child: {edge.child}")
        return errors

    def topological_order(self) -> list[str]:
        """Return node names in topological sort order (roots first)."""
        return list(nx.topological_sort(self._graph))

    @property
    def nodes(self) -> dict[str, PGMNode]:
        return self._nodes

    @property
    def edges(self) -> list[PGMEdge]:
        return self._edges

    def update_node_confidence(self, node_name: str, confidence: float, source: str) -> None:
        """Update a node's confidence based on new evidence."""
        if node_name in self._nodes:
            self._nodes[node_name].confidence = max(0.0, min(1.0, confidence))
            self._nodes[node_name].evidence_source = source
            self._nodes[node_name].evidence_status = EvidenceStatus.EXTERNAL

    def update_node_distribution(self, node_name: str, **params: float) -> None:
        """Update a node's distribution parameters based on new evidence."""
        if node_name in self._nodes:
            node = self._nodes[node_name]
            for param, value in params.items():
                if hasattr(node.distribution, param):
                    setattr(node.distribution, param, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "name": self.name,
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
