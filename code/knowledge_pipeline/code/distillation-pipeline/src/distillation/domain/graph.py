"""Graph node and edge models — re-exported from the new ontology.

The old distillation pipeline had its own GraphNodeType/GraphEdgeType
enums and GraphNode/GraphEdge models. All definitions have been moved
to ``domain/ontology.py`` as part of the ontology migration.

This module re-exports everything so existing imports continue to work.
New code should import directly from ``domain.ontology``.
"""

from __future__ import annotations

from .ontology import (
    # Enums
    AssumptionType,
    CapabilityType,
    ClaimType,
    DataRegime,
    DatasetContaminationRisk,
    EvidenceDirection,
    EvidenceType,
    ExperimentType,
    GraphEdgeType,
    GraphNodeType,
    LimitationSeverity,
    MetricDirection,
    OrganizationType,
    Polarity,
    ReplicationStatus,
    TechnologyType,
    VenueTier,
    # Models
    GraphEdge,
    GraphNode,
)

__all__ = [
    "GraphNodeType",
    "GraphEdgeType",
    "GraphNode",
    "GraphEdge",
    "AssumptionType",
    "CapabilityType",
    "ClaimType",
    "DataRegime",
    "DatasetContaminationRisk",
    "EvidenceDirection",
    "EvidenceType",
    "ExperimentType",
    "LimitationSeverity",
    "MetricDirection",
    "OrganizationType",
    "Polarity",
    "ReplicationStatus",
    "TechnologyType",
    "VenueTier",
]
