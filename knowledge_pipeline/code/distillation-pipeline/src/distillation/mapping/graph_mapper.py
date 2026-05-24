"""Distillate → graph nodes/edges mapping.

This is the single place where ontology rules become graph operations.
Solid arrows from the ontology are produced here directly; dashed
cross-entity arrows that emerge across sources (``HAS_INTEREST``,
``BELONGS_TO``, etc.) are produced where they can be derived from the
single-document distillate (e.g. an author's stated interests → topics).
Truly corpus-emergent edges (``APPLIES_TO``, ``UNDERLIES``) are left for a
separate corpus-level job.
"""

from __future__ import annotations

from typing import Iterable

from ..domain.distillate import (
    ConclusionMention,
    Distillate,
)
from ..domain.document import SourceDocument
from ..domain.graph import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType
from ..domain.ids import canonicalize, deterministic_id


class GraphMapper:
    """Pure function-style mapper from ``Distillate`` to graph deltas."""

    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id

    # --- public ---------------------------------------------------------

    def map(
        self, document: SourceDocument, distillate: Distillate
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        source_node = self._source_node(document)
        nodes.append(source_node)

        nodes.extend(self._topic_nodes(distillate))
        nodes.extend(self._theme_nodes(distillate))
        nodes.extend(self._author_nodes(distillate))
        nodes.extend(self._affiliation_nodes(distillate))
        nodes.extend(self._assumption_nodes(distillate))
        nodes.extend(self._theory_nodes(distillate))
        nodes.extend(self._conclusion_nodes(distillate))
        nodes.extend(self._methodology_nodes(distillate))

        edges.extend(self._primary_edges(source_node, distillate))
        edges.extend(self._affiliation_edges(distillate))
        edges.extend(self._topic_theme_edges(distillate))
        edges.extend(self._author_interest_edges(distillate))
        edges.extend(self._conclusion_supports_theory_edges(distillate))

        return _dedupe_nodes(nodes), _dedupe_edges(edges)

    # --- node builders --------------------------------------------------

    def _source_node(self, document: SourceDocument) -> GraphNode:
        return GraphNode(
            node_id=document.document_id,
            type=GraphNodeType.SOURCE,
            name=document.metadata.source_id,
            properties={
                "uri": document.metadata.uri,
                "format": document.format.value,
                "content_sha256": document.content_sha256,
                "tenant_id": document.metadata.tenant_id,
                "fetched_at": document.metadata.fetched_at.isoformat(),
            },
        )

    def _topic_nodes(self, d: Distillate) -> list[GraphNode]:
        return [
            GraphNode(
                node_id=self._id(GraphNodeType.TOPIC, t.canonical_name),
                type=GraphNodeType.TOPIC,
                name=t.name,
                properties={"canonical_name": t.canonical_name},
            )
            for t in d.topics
        ]

    def _theme_nodes(self, d: Distillate) -> list[GraphNode]:
        themes = {canonicalize(t.theme): t.theme for t in d.topics if t.theme}
        return [
            GraphNode(
                node_id=self._id(GraphNodeType.THEME, canonical),
                type=GraphNodeType.THEME,
                name=display,
                properties={"canonical_name": canonical},
            )
            for canonical, display in themes.items()
        ]

    def _author_nodes(self, d: Distillate) -> list[GraphNode]:
        return [
            GraphNode(
                node_id=self._id(GraphNodeType.AUTHOR, a.canonical_name),
                type=GraphNodeType.AUTHOR,
                name=a.name,
                properties={
                    "canonical_name": a.canonical_name,
                    "interests": a.interests,
                },
            )
            for a in d.authors
        ]

    def _affiliation_nodes(self, d: Distillate) -> list[GraphNode]:
        out: list[GraphNode] = []
        for a in d.authors:
            if a.affiliation is None:
                continue
            canon = canonicalize(a.affiliation.name)
            out.append(
                GraphNode(
                    node_id=self._id(GraphNodeType.AFFILIATION, canon),
                    type=GraphNodeType.AFFILIATION,
                    name=a.affiliation.name,
                    properties={"canonical_name": canon},
                )
            )
        return out

    def _assumption_nodes(self, d: Distillate) -> list[GraphNode]:
        return [
            GraphNode(
                node_id=self._id(GraphNodeType.ASSUMPTION, a.canonical_name),
                type=GraphNodeType.ASSUMPTION,
                name=a.name,
                properties={
                    "canonical_name": a.canonical_name,
                    "statement": a.statement,
                },
            )
            for a in d.assumptions
        ]

    def _theory_nodes(self, d: Distillate) -> list[GraphNode]:
        return [
            GraphNode(
                node_id=self._id(GraphNodeType.THEORY, t.canonical_name),
                type=GraphNodeType.THEORY,
                name=t.name,
                properties={
                    "canonical_name": t.canonical_name,
                    "statement": t.statement,
                },
            )
            for t in d.theories
        ]

    def _conclusion_nodes(self, d: Distillate) -> list[GraphNode]:
        return [
            GraphNode(
                node_id=self._id(GraphNodeType.CONCLUSION, c.canonical_name),
                type=GraphNodeType.CONCLUSION,
                name=c.name,
                properties={
                    "canonical_name": c.canonical_name,
                    "statement": c.statement,
                },
            )
            for c in d.conclusions
        ]

    def _methodology_nodes(self, d: Distillate) -> list[GraphNode]:
        return [
            GraphNode(
                node_id=self._id(GraphNodeType.METHODOLOGY, m.canonical_name),
                type=GraphNodeType.METHODOLOGY,
                name=m.name,
                properties={
                    "canonical_name": m.canonical_name,
                    "description": m.description,
                },
            )
            for m in d.methodologies
        ]

    # --- edge builders --------------------------------------------------

    def _primary_edges(
        self, source: GraphNode, d: Distillate
    ) -> list[GraphEdge]:
        """All ``Source → entity`` solid arrows from the ontology."""
        edges: list[GraphEdge] = []

        for entity, edge_type, node_type in (
            *((t, GraphEdgeType.DISCUSSES, GraphNodeType.TOPIC) for t in d.topics),
            *((a, GraphEdgeType.AUTHORED_BY, GraphNodeType.AUTHOR) for a in d.authors),
            *((a, GraphEdgeType.ASSUMES, GraphNodeType.ASSUMPTION) for a in d.assumptions),
            *((t, GraphEdgeType.BUILDS, GraphNodeType.THEORY) for t in d.theories),
            *((c, GraphEdgeType.CONCLUDES, GraphNodeType.CONCLUSION) for c in d.conclusions),
            *((m, GraphEdgeType.USES, GraphNodeType.METHODOLOGY) for m in d.methodologies),
        ):
            edges.append(
                GraphEdge(
                    source_node_id=source.node_id,
                    target_node_id=self._id(node_type, entity.canonical_name),
                    type=edge_type,
                    provenance_chunk_ids=list(entity.provenance_chunk_ids),
                )
            )
        return edges

    def _affiliation_edges(self, d: Distillate) -> list[GraphEdge]:
        out: list[GraphEdge] = []
        for a in d.authors:
            if a.affiliation is None:
                continue
            out.append(
                GraphEdge(
                    source_node_id=self._id(GraphNodeType.AUTHOR, a.canonical_name),
                    target_node_id=self._id(
                        GraphNodeType.AFFILIATION, canonicalize(a.affiliation.name)
                    ),
                    type=GraphEdgeType.IS_AT,
                    provenance_chunk_ids=list(a.provenance_chunk_ids),
                )
            )
        return out

    def _topic_theme_edges(self, d: Distillate) -> list[GraphEdge]:
        out: list[GraphEdge] = []
        for t in d.topics:
            if not t.theme:
                continue
            out.append(
                GraphEdge(
                    source_node_id=self._id(GraphNodeType.TOPIC, t.canonical_name),
                    target_node_id=self._id(GraphNodeType.THEME, canonicalize(t.theme)),
                    type=GraphEdgeType.BELONGS_TO,
                    provenance_chunk_ids=list(t.provenance_chunk_ids),
                )
            )
        return out

    def _author_interest_edges(self, d: Distillate) -> list[GraphEdge]:
        topic_canonicals = {t.canonical_name for t in d.topics}
        out: list[GraphEdge] = []
        for a in d.authors:
            for interest in a.interests:
                canon = canonicalize(interest)
                # Only link to topics that exist as nodes in this distillate;
                # cross-document HAS_INTEREST links are produced by the
                # corpus-level cross-reference job (out of scope here).
                if canon not in topic_canonicals:
                    continue
                out.append(
                    GraphEdge(
                        source_node_id=self._id(GraphNodeType.AUTHOR, a.canonical_name),
                        target_node_id=self._id(GraphNodeType.TOPIC, canon),
                        type=GraphEdgeType.HAS_INTEREST,
                        provenance_chunk_ids=list(a.provenance_chunk_ids),
                    )
                )
        return out

    def _conclusion_supports_theory_edges(self, d: Distillate) -> list[GraphEdge]:
        theory_canonicals = {t.canonical_name for t in d.theories}
        out: list[GraphEdge] = []
        for c in d.conclusions:
            assert isinstance(c, ConclusionMention)
            for theory_name in c.supports_theories:
                canon = canonicalize(theory_name)
                if canon not in theory_canonicals:
                    continue
                out.append(
                    GraphEdge(
                        source_node_id=self._id(GraphNodeType.CONCLUSION, c.canonical_name),
                        target_node_id=self._id(GraphNodeType.THEORY, canon),
                        type=GraphEdgeType.SUPPORTS,
                        provenance_chunk_ids=list(c.provenance_chunk_ids),
                    )
                )
        return out

    # --- helpers --------------------------------------------------------

    def _id(self, node_type: GraphNodeType, canonical_name: str) -> str:
        return deterministic_id(
            self._tenant_id, node_type.value, canonical_name
        )


def _dedupe_nodes(nodes: Iterable[GraphNode]) -> list[GraphNode]:
    seen: dict[str, GraphNode] = {}
    for n in nodes:
        if n.node_id not in seen:
            seen[n.node_id] = n
    return list(seen.values())


def _dedupe_edges(edges: Iterable[GraphEdge]) -> list[GraphEdge]:
    seen: dict[tuple[str, str, str], GraphEdge] = {}
    for e in edges:
        seen[e.edge_key] = e
    return list(seen.values())
