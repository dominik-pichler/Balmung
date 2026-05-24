"""Graph node and edge models — the ontology types from the diagram.

Node and edge types are enumerated so the graph repository can validate
inputs and so consumers (e.g. Cypher generation) can switch on a closed set.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class GraphNodeType(str, Enum):
    """The ontology's node labels."""

    SOURCE = "Source"
    AUTHOR = "Author"
    AFFILIATION = "Affiliation"
    TOPIC = "Topic"
    THEME = "Theme"
    ASSUMPTION = "Assumption"
    THEORY = "Theory"
    CONCLUSION = "Conclusion"
    METHODOLOGY = "Methodology"


class GraphEdgeType(str, Enum):
    """The ontology's edge labels.

    Solid arrows (Source → extracted entity):
        AUTHORED_BY, DISCUSSES, CITES, USES, BUILDS, CONCLUDES, ASSUMES, IS_AT

    Dashed arrows (cross-entity, emergent):
        HAS_INTEREST, BELONGS_TO, APPLIES_TO, SUPPORTS, CONTRADICTS, UNDERLIES
    """

    # Primary (per-source)
    AUTHORED_BY = "AUTHORED_BY"
    DISCUSSES = "DISCUSSES"
    CITES = "CITES"
    USES = "USES"
    BUILDS = "BUILDS"
    CONCLUDES = "CONCLUDES"
    ASSUMES = "ASSUMES"
    IS_AT = "IS_AT"

    # Cross-entity (corpus-level)
    HAS_INTEREST = "HAS_INTEREST"
    BELONGS_TO = "BELONGS_TO"
    APPLIES_TO = "APPLIES_TO"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    UNDERLIES = "UNDERLIES"


class GraphNode(BaseModel):
    """A node in the knowledge graph.

    ``node_id`` is deterministic so re-ingests upsert cleanly. ``properties``
    is a flat dict of primitive JSON-serializable values — Neo4j friendly.
    """

    node_id: str
    type: GraphNodeType
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge in the knowledge graph.

    Provenance points back to the chunks that produced the edge, satisfying
    the design preference for end-to-end provenance tracking.
    """

    source_node_id: str
    target_node_id: str
    type: GraphEdgeType
    properties: dict[str, Any] = Field(default_factory=dict)
    provenance_chunk_ids: list[str] = Field(default_factory=list)

    @property
    def edge_key(self) -> tuple[str, str, str]:
        """Tuple key suitable for dedup/upsert in any backend."""
        return (self.source_node_id, self.type.value, self.target_node_id)
