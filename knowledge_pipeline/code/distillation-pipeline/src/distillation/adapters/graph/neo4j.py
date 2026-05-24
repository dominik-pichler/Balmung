"""Neo4j ``GraphRepository`` adapter.

Cypher patterns:
  * Node upsert: ``MERGE (n:<Label> {node_id: $id}) SET n += $props, n.name = $name``
  * Edge upsert: ``MATCH (s {node_id: $src}), (t {node_id: $tgt})
                  MERGE (s)-[r:<TYPE>]->(t)
                  SET r += $props,
                      r.provenance_chunk_ids =
                          coalesce(r.provenance_chunk_ids, []) + $provenance``

Edge type is parameterized via the type enum value; we interpolate it into
the Cypher string after asserting it is a known enum member, which is safe
because the enum is closed.
"""

from __future__ import annotations

from collections.abc import Iterable

from ...domain.graph import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType
from ...ports.graph_repository import GraphRepository


class Neo4jGraphRepository(GraphRepository):
    def __init__(
        self,
        *,
        uri: str,
        user: str,
        password: str,
        database: str = "neo4j",
    ) -> None:
        # Lazy import keeps non-Neo4j environments importable.
        try:
            from neo4j import AsyncGraphDatabase  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - dep guard
            raise ImportError(
                "Install the 'neo4j' package to use Neo4jGraphRepository"
            ) from exc

        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self._database = database

    async def upsert_nodes(self, nodes: Iterable[GraphNode]) -> None:
        node_list = list(nodes)
        if not node_list:
            return
        async with self._driver.session(database=self._database) as session:
            for node in node_list:
                # Label is closed-set so direct interpolation is safe.
                label = _validate_node_label(node.type)
                cypher = (
                    f"MERGE (n:{label} {{node_id: $node_id}}) "
                    f"SET n += $props, n.name = $name"
                )
                await session.run(
                    cypher,
                    node_id=node.node_id,
                    props=node.properties,
                    name=node.name,
                )

    async def upsert_edges(self, edges: Iterable[GraphEdge]) -> None:
        edge_list = list(edges)
        if not edge_list:
            return
        async with self._driver.session(database=self._database) as session:
            for edge in edge_list:
                rel_type = _validate_edge_type(edge.type)
                cypher = (
                    "MATCH (s {node_id: $src}), (t {node_id: $tgt}) "
                    f"MERGE (s)-[r:{rel_type}]->(t) "
                    "SET r += $props, "
                    "    r.provenance_chunk_ids = "
                    "        coalesce(r.provenance_chunk_ids, []) + $provenance"
                )
                await session.run(
                    cypher,
                    src=edge.source_node_id,
                    tgt=edge.target_node_id,
                    props=edge.properties,
                    provenance=edge.provenance_chunk_ids,
                )

    async def count_nodes(self) -> int:
        async with self._driver.session(database=self._database) as session:
            result = await session.run("MATCH (n) RETURN count(n) AS c")
            record = await result.single()
            return int(record["c"]) if record else 0

    async def count_edges(self) -> int:
        async with self._driver.session(database=self._database) as session:
            result = await session.run("MATCH ()-[r]->() RETURN count(r) AS c")
            record = await result.single()
            return int(record["c"]) if record else 0

    async def close(self) -> None:
        await self._driver.close()


def _validate_node_label(t: GraphNodeType) -> str:
    if not isinstance(t, GraphNodeType):
        raise TypeError(f"Unknown node label: {t!r}")
    return t.value


def _validate_edge_type(t: GraphEdgeType) -> str:
    if not isinstance(t, GraphEdgeType):
        raise TypeError(f"Unknown edge type: {t!r}")
    return t.value
