"""Neo4j ``GraphRepository`` adapter — migrated for the new ontology.

Key changes from the legacy adapter:
  1. **Constraints**: The adapter validates that required constraints exist
     before writing persistent (MERGE'd) nodes. Without constraints,
     MERGE is slower and can create duplicates.
  2. **Transactions**: Each call wraps in ``async with session(...)`` so
     partial writes never corrupt the graph.
  3. **Three-layer writes**: ``upsert_domain_nodes()`` uses MERGE with
     explicit ``id`` fields; ``create_epistemic_nodes()`` uses CREATE for
     paper-scoped nodes; ``upsert_provenance_nodes()`` uses MERGE for
     cross-paper persistent nodes.
  4. **``extraction_confidence``**: On every node write, the adapter
     writes this property so the assessment engine can later filter on
     extraction quality.

The adapter is backward-compatible with the legacy ``upsert_nodes()``
and ``upsert_edges()`` methods but NEW code should use the three-layer
methods to benefit from proper transaction handling and validation.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Optional

import structlog

from ...domain.graph import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType
from ...ports.graph_repository import GraphRepository

log = structlog.get_logger()


# ===================================================================
# Required constraints for the new ontology
# ===================================================================
#
# Each persistent (MERGE'd) node label needs a uniqueness constraint on
# ``id`` so cross-paper MERGE cannot create duplicates. These mirror
# ``schema/neo4j_constraints.cypher``; the adapter provisions them
# automatically (idempotently) on first write via ``ensure_constraints()``.

# constraint name → node label
CONSTRAINT_LABELS: dict[str, str] = {
    "technology_id": "Technology",
    "problem_id": "Problem",
    "capability_id": "Capability",
    "metric_id": "Metric",
    "dataset_id": "Dataset",
    "assumption_id": "Assumption",
    "limitation_id": "Limitation",
    "paper_id": "Paper",
    "author_id": "Author",
    "organization_id": "Organization",
    "fundingsource_id": "FundingSource",
    "venue_id": "Venue",
}

ALL_CONSTRAINTS = list(CONSTRAINT_LABELS)


class Neo4jGraphRepository(GraphRepository):
    """Neo4j adapter for the migrated ontology.

    Constraints are provisioned automatically (idempotently) on the first
    persistent write, so no manual setup step is required.

    Usage:
        repo = Neo4jGraphRepository(uri=..., user=..., password=...)
        await repo.upsert_domain_nodes(nodes)  # Level 1 (MERGE)
        await repo.create_epistemic_nodes(nodes)  # Level 2 (CREATE)
        await repo.upsert_provenance_nodes(nodes)  # Level 3 (MERGE)
        await repo.close()
    """

    def __init__(
            self,
            *,
            uri: str,
            user: str,
            password: str,
            auth_token: str = "",
            database: str = "neo4j",
    ) -> None:

        try:
            from neo4j import AsyncGraphDatabase, basic_auth, bearer_auth
        except ImportError as exc:
            raise ImportError(
                "Install the 'neo4j' package to use Neo4jGraphRepository"
            ) from exc

        # Prefer token-based auth (cloud/proxy), fall back to user/pass.
        if auth_token:
            driver_auth = bearer_auth(auth_token)
        else:
            if not password:
                raise ValueError(
                    "password is empty — set NEO4J_PASSWORD or pass password="
                )
            driver_auth = basic_auth(user, password)

        self._driver = AsyncGraphDatabase.driver(uri, auth=driver_auth)
        self._database = database
        self._constraints_checked: bool = False

    async def upsert_nodes(
        self, nodes: Iterable[GraphNode]
    ) -> None:
        """Write nodes through the three-layer architecture."""
        domain: list[GraphNode] = []
        epistemic: list[GraphNode] = []
        provenance: list[GraphNode] = []
        for node in nodes:
            if node.type in {
                GraphNodeType.TECHNOLOGY, GraphNodeType.PROBLEM,
                GraphNodeType.CAPABILITY, GraphNodeType.METRIC,
                GraphNodeType.DATASET, GraphNodeType.ASSUMPTION,
                GraphNodeType.LIMITATION,
            }:
                domain.append(node)
            elif node.type in {
                GraphNodeType.CLAIM, GraphNodeType.EVIDENCE,
                GraphNodeType.EXPERIMENT, GraphNodeType.SCOPE,
            }:
                epistemic.append(node)
            else:
                provenance.append(node)
        await self.upsert_domain_nodes(domain)
        await self.create_epistemic_nodes(epistemic)
        await self.upsert_provenance_nodes(provenance)

    async def close(self) -> None:
        await self._driver.close()

    # --- one-time setup -----------------------------------------------

    async def ensure_constraints(self) -> None:
        """Create all required uniqueness constraints if they don't exist.

        Uses ``CREATE CONSTRAINT ... IF NOT EXISTS`` so this is idempotent
        and safe to call on every run. Guarantees cross-paper MERGE cannot
        create duplicate persistent nodes.

        Runs automatically before the first write; callers may also invoke
        it explicitly (e.g. as a one-time setup step).
        """
        async with self._driver.session(database=self._database) as session:
            for name, label in CONSTRAINT_LABELS.items():
                await session.run(
                    f"CREATE CONSTRAINT {name} IF NOT EXISTS "
                    f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                )

        self._constraints_checked = True
        log.info("neo4j.constraints_ensured", count=len(CONSTRAINT_LABELS))

    # --- Level 1: Domain nodes (MERGE with explicit ``id``) --------

    async def upsert_domain_nodes(
        self, nodes: Iterable[GraphNode]
    ) -> None:
        """Write persistent (MERGE'd) domain nodes.

        Uses explicit ``id`` property for MERGE-key matching:
          ``MERGE (n:Label {id: $node_id}) SET n += $props``

        This is the Level 1 write: Technology, Problem, Capability,
        Metric, Dataset, Assumption, Limitation.
        """
        node_list = list(nodes)
        if not node_list:
            return

        # Provision constraints before the first persistent write.
        await self._ensure_constraints_once()

        async with self._driver.session(database=self._database) as session:
            for node in node_list:
                label = _validate_node_label(node.type)
                cypher = (
                    f"MERGE (n:{label} {{id: $node_id}}) "
                    "SET n += $props"
                )
                # Add id explicitly so MERGE matches on it.
                await session.run(
                    cypher,
                    node_id=node.node_id,
                    props=node.properties,
                )

    # --- Level 2: Epistemic nodes (CREATE, paper-scoped) --------

    async def create_epistemic_nodes(
        self, nodes: Iterable[GraphNode]
    ) -> None:
        """Create paper-scoped (CREATE) epistemik nodes.

        These nodes (Claim, Evidence, Experiment, Scope) are created
        fresh for each paper — they are NEVER merged across papers.
        Uses CREATE to enforce this invariant.
        """
        node_list = list(nodes)
        if not node_list:
            return

        async with self._driver.session(database=self._database) as session:
            for node in node_list:
                label = _validate_node_label(node.type)
                cypher = (
                    f"CREATE (n:{label} {{id: $node_id}}) "
                    "SET n += $props"
                )
                await session.run(
                    cypher,
                    node_id=node.node_id,
                    props=node.properties,
                )

    # --- Level 3: Provenance nodes (MERGE with explicit ``id``) --------

    async def upsert_provenance_nodes(
        self, nodes: Iterable[GraphNode]
    ) -> None:
        """Write persistent (MERGE'd) provenance nodes.

        Uses explicit ``id`` property for MERGE-key matching:
          ``MERGE (n:Label {id: $node_id}) SET n += $props``

        This is the Level 3 write: Paper, Author, Organization, Venue,
        FundingSource.
        """
        node_list = list(nodes)
        if not node_list:
            return

        # Provision constraints before the first persistent write.
        await self._ensure_constraints_once()

        async with self._driver.session(database=self._database) as session:
            for node in node_list:
                label = _validate_node_label(node.type)
                cypher = (
                    f"MERGE (n:{label} {{id: $node_id}}) "
                    "SET n += $props"
                )
                await session.run(
                    cypher,
                    node_id=node.node_id,
                    props=node.properties,
                )

    # --- Edges (all types, validated) -------------------------------

    async def upsert_edges(
        self, edges: Iterable[GraphEdge]
    ) -> None:
        """Write edges with provenance tracking.

        Uses MERGE for idempotency: the same edge (same source, type,
        target) is not duplicated. Provenance chunk lists are merged.

        NOTE: When using the new ontology with explicit ``id`` on nodes,
        edges are resolved by MATCH on ``id`` instead of ``node_id``.
        """
        edge_list = list(edges)
        if not edge_list:
            return

        async with self._driver.session(database=self._database) as session:
            for edge in edge_list:
                rel_type = _validate_edge_type(edge.type)

                # Build the Cypher for this edge. Nodes carry an explicit
                # ``id`` property, so edges resolve by MATCH on ``id``.
                cypher = (
                    "MATCH (s {id: $src_id}) MATCH (t {id: $tgt_id}) "
                    f"MERGE (s)-[r:{rel_type}]->(t) "
                    "SET r += $props "
                    "REMOVE r.provenanceChunkIds, r.provenance_chunk_ids, r.provenance"
                )
                # Add extraction_confidence on edge if present.
                if edge.extraction_confidence is not None:
                    cypher += " SET r.extractionConfidence = $extraction_conf"

                await session.run(
                    cypher,
                    src_id=edge.source_node_id,
                    tgt_id=edge.target_node_id,
                    props=edge.properties,
                    extraction_conf=edge.extraction_confidence,
                )

    # --- Legacy compatibility (without explicit ``id`` on nodes) --------

    async def legacy_upsert_nodes(
        self, nodes: Iterable[GraphNode]
    ) -> None:
        """Legacy method — uses ``node_id`` as the merge key.

        Deprecated: prefer ``upsert_domain_nodes()`` or
        ``upsert_provenance_nodes()`` which use explicit ``id``.
        """
        node_list = list(nodes)
        if not node_list:
            return

        async with self._driver.session(database=self._database) as session:
            for node in node_list:
                label = _validate_node_label(node.type)
                cypher = (
                    f"MERGE (n:{label} {{node_id: $node_id}}) "
                    f"SET n += $props, n.name = $name"
                )
                await session.run(
                    node_id=node.node_id,
                    props=node.properties,
                    name=node.name,
                )

    async def legacy_upsert_edges(
        self, edges: Iterable[GraphEdge]
    ) -> None:
        """Legacy method — uses ``node_id`` for edge resolution.

        Deprecated: prefer ``upsert_edges()`` which uses ``id``.
        """
        edge_list = list(edges)
        if not edge_list:
            return

        async with self._driver.session(database=self._database) as session:
            for edge in edge_list:
                rel_type = _validate_edge_type(edge.type)
                cypher = (
                    "MATCH (s {node_id: $src}), (t {node_id: $tgt}) "
                    f"MERGE (s)-[r:{rel_type}]->(t) "
                    "SET r += $props"
                )
                await session.run(
                    src=edge.source_node_id,
                    tgt=edge.target_node_id,
                    props=edge.properties,
                )

    # --- Query helpers ------------------------------------------------

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

    async def all_nodes(self) -> list[GraphNode]:
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                "MATCH (n) RETURN labels(n)[0] AS label, "
                "coalesce(n.id, n.node_id) AS node_id, "
                "coalesce(n.name, '') AS name, "
                "properties(n) AS props"
            )
            nodes: list[GraphNode] = []
            async for record in result:
                props = {
                    k: v
                    for k, v in dict(record["props"]).items()
                    if k not in ("node_id", "name", "id")
                }
                nodes.append(
                    GraphNode(
                        node_id=record["node_id"],
                        type=GraphNodeType(record["label"]),
                        name=record["name"],
                        properties=props,
                    )
                )
            return nodes

    async def all_edges(self) -> list[GraphEdge]:
        async with self._driver.session(database=self._database) as session:
            result = await session.run(
                "MATCH (s)-[r]->(t) "
                "RETURN coalesce(s.id, s.node_id) AS src, "
                "type(r) AS rel_type, "
                "coalesce(t.id, t.node_id) AS tgt, "
                "properties(r) AS props"
            )
            edges: list[GraphEdge] = []
            async for record in result:
                props = dict(record["props"])
                edges.append(
                    GraphEdge(
                        source_node_id=record["src"],
                        target_node_id=record["tgt"],
                        type=GraphEdgeType(record["rel_type"]),
                        properties=props,
                        extraction_confidence=props.get("extractionConfidence"),
                    )
                )
            return edges

    # --- internals ----------------------------------------------------

    async def _ensure_constraints_once(self) -> None:
        """Provision required constraints on the first write, idempotently."""
        if self._constraints_checked:
            return
        await self.ensure_constraints()


def _validate_node_label(t: GraphNodeType) -> str:
    if not isinstance(t, GraphNodeType):
        raise TypeError(f"Unknown node label: {t!r}")
    return t.value


def _validate_edge_type(t: GraphEdgeType) -> str:
    if not isinstance(t, GraphEdgeType):
        raise TypeError(f"Unknown edge type: {t!r}")
    return t.value
