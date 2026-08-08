"""In-memory graph repository.

Backed by two dicts: ``node_id → GraphNode`` and ``(src, type, tgt) → GraphEdge``.
Useful for tests and for running the pipeline locally without Neo4j.

Properties are merged on upsert so re-ingesting the same source augments
rather than overwrites node/edge state.
"""

from __future__ import annotations

from collections.abc import Iterable

from ...domain.graph import GraphEdge, GraphNode
from ...ports.graph_repository import GraphRepository


class InMemoryGraphRepository(GraphRepository):
    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: dict[tuple[str, str, str], GraphEdge] = {}

    async def upsert_nodes(self, nodes: Iterable[GraphNode]) -> None:
        for node in nodes:
            existing = self._nodes.get(node.node_id)
            if existing is None:
                self._nodes[node.node_id] = node
            else:
                # Merge properties: new values win on conflict.
                merged_props = {**existing.properties, **node.properties}
                self._nodes[node.node_id] = existing.model_copy(
                    update={"properties": merged_props, "name": node.name}
                )

    async def upsert_edges(self, edges: Iterable[GraphEdge]) -> None:
        for edge in edges:
            key = edge.edge_key
            existing = self._edges.get(key)
            if existing is None:
                self._edges[key] = edge
            else:
                merged_props = {**existing.properties, **edge.properties}
                merged_confidence = (
                    edge.extraction_confidence
                    if edge.extraction_confidence is not None
                    else existing.extraction_confidence
                )
                self._edges[key] = existing.model_copy(
                    update={
                        "properties": merged_props,
                        "extraction_confidence": merged_confidence,
                    }
                )

    async def count_nodes(self) -> int:
        return len(self._nodes)

    async def count_edges(self) -> int:
        return len(self._edges)

    async def all_nodes(self) -> list[GraphNode]:
        return list(self._nodes.values())

    async def all_edges(self) -> list[GraphEdge]:
        return list(self._edges.values())

    # --- test helpers ---------------------------------------------------

    def nodes(self) -> list[GraphNode]:
        return list(self._nodes.values())

    def edges(self) -> list[GraphEdge]:
        return list(self._edges.values())
