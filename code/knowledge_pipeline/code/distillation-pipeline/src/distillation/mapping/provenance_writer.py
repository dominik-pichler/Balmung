"""ProvenanceWriter — writes Level 3 (persistent provenance) nodes.

Writes ``Paper``, ``Author``, ``Organization``, ``Venue``, ``FundingSource``
via MERGE on ``node_id``.

These nodes are persistent across papers: same ORCID or canonical name (for a
given tenant + node type) → same ``node_id`` → MERGE ON MATCH ON CREATE. Node
ids follow ``sha256(tenant || type || canonical_name)[:16]`` (see
:func:`distillation.domain.ids.node_id`) and deliberately omit the paper id.

Author-Matching priority:
  1. ORCID (unique, machine-readable)
  2. Normalized name + affiliation (fallback for older papers without ORCID)

This is critical for Independence-Detection: wrong Author matching breaks the
entire bias analysis later.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..domain.distillate import (
    AuthorMention,
    FundingSourceMention,
    OrganizationMention,
    PaperMention,
    VenueMention,
)
from ..domain.document import SourceDocument
from ..domain.graph import GraphEdge, GraphEdgeType, GraphNode, GraphNodeType
from ..domain.ids import node_id


class ProvenanceWriter:
    """Produces persistent (MERGE'd) provenance nodes and edges."""

    # --- public API -----------------------------------------------------

    def write_papers(
        self, entities: Iterable[PaperMention], tenant_id: str
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for paper in entities:
            n, e = self._write_paper(paper, tenant_id)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    def write_authors(
        self,
        entities: Iterable[AuthorMention],
        paper_id: str,
        tenant_id: str,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for author in entities:
            n, e = self._write_author(author, paper_id, tenant_id)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    def write_organizations(
        self, entities: Iterable[OrganizationMention], tenant_id: str
    ) -> list[GraphNode]:
        return [self._write_organization(org, tenant_id) for org in entities]

    def write_venues(
        self, entities: Iterable[VenueMention], tenant_id: str
    ) -> list[GraphNode]:
        return [self._write_venue(v, tenant_id) for v in entities]

    def write_funding_sources(
        self, entities: Iterable[FundingSourceMention], tenant_id: str
    ) -> list[GraphNode]:
        return [self._write_funding(fs, tenant_id) for fs in entities]

    # --- Paper (from the ingested document) -----------------------------

    def write_document_paper(
        self, document: SourceDocument, paper_id: str
    ) -> GraphNode:
        """Build the ``Paper`` node representing the ingested document.

        The node id is the ``document_id`` (already tenant + content scoped)
        so per-paper edges (``MAKES_CLAIM``, ``AUTHORED_BY``) anchor here.
        """
        meta = document.metadata
        props: dict = {
            "source_id": meta.source_id,
            "uri": meta.uri,
            "content_sha256": document.content_sha256,
            "tenant_id": meta.tenant_id,
            "format": document.format.value,
            "fetched_at": meta.fetched_at.isoformat(),
        }
        return GraphNode(
            node_id=paper_id,
            type=GraphNodeType.PAPER,
            name=meta.source_id,
            properties=props,
        )

    # --- Paper (from an explicit PaperMention) --------------------------

    def _paper_id(self, paper: PaperMention, tenant_id: str) -> str:
        """Paper id from its ``name`` (DOI where the caller set name=DOI)."""
        return node_id(tenant_id, GraphNodeType.PAPER, paper.name)

    def _write_paper(
        self, paper: PaperMention, tenant_id: str
    ) -> tuple[GraphNode, list[GraphEdge]]:
        props: dict = {
            "extraction_confidence": paper.extraction_confidence,
        }
        if paper.title is not None:
            props["title"] = paper.title
        if paper.year is not None:
            props["year"] = paper.year
        if paper.venue_tier is not None:
            props["venue_tier"] = paper.venue_tier.value
        if paper.peer_reviewed is not None:
            props["peer_reviewed"] = paper.peer_reviewed
        props["is_preprint"] = paper.is_preprint

        node = GraphNode(
            node_id=self._paper_id(paper, tenant_id),
            type=GraphNodeType.PAPER,
            name=paper.name,
            properties=props,
        )
        return node, []

    # --- Author (with ORCID matching) ---------------------------------

    def _author_id(self, author: AuthorMention, tenant_id: str) -> str:
        """Author id: prefer ORCID, fallback to (name + affiliation).

        The most critical matching logic for Independence-Detection:
        - ORCID available → use it directly (most precise).
        - Otherwise → name + affiliation (affiliation disambiguates namesakes).
        """
        if author.orcid:
            return node_id(tenant_id, GraphNodeType.AUTHOR, author.orcid)
        affiliation = author.affiliation.name if author.affiliation else ""
        return node_id(
            tenant_id, GraphNodeType.AUTHOR, author.name, affiliation
        )

    def _write_author(
        self, author: AuthorMention, paper_id: str, tenant_id: str
    ) -> tuple[GraphNode, list[GraphEdge]]:
        edges: list[GraphEdge] = []
        aid = self._author_id(author, tenant_id)

        props: dict = {
            "extraction_confidence": author.extraction_confidence,
        }
        if author.orcid is not None:
            props["orcid"] = author.orcid
        if author.affiliation is not None:
            props["affiliation"] = author.affiliation.name
        if author.interests:
            props["interests"] = author.interests
        if author.position is not None:
            props["author_position"] = author.position

        node = GraphNode(
            node_id=aid,
            type=GraphNodeType.AUTHOR,
            name=author.name,
            properties=props,
        )

        # Paper → Author: AUTHORED_BY
        edges.append(
            GraphEdge(
                source_node_id=paper_id,
                target_node_id=aid,
                type=GraphEdgeType.AUTHORED_BY,
                extraction_confidence=author.extraction_confidence,
            )
        )
        return node, edges

    # --- Organization -----------------------------------------------

    def _write_organization(
        self, org: OrganizationMention, tenant_id: str
    ) -> GraphNode:
        props: dict = {
            "extraction_confidence": org.extraction_confidence,
        }
        if org.org_type is not None:
            props["type"] = org.org_type.value
        return GraphNode(
            node_id=node_id(tenant_id, GraphNodeType.ORGANIZATION, org.name),
            type=GraphNodeType.ORGANIZATION,
            name=org.name,
            properties=props,
        )

    # --- Venue ----------------------------------------------------------

    def _write_venue(self, venue: VenueMention, tenant_id: str) -> GraphNode:
        props: dict = {
            "extraction_confidence": venue.extraction_confidence,
        }
        if venue.tier is not None:
            props["tier"] = venue.tier.value
        if venue.peer_reviewed is not None:
            props["peer_reviewed"] = venue.peer_reviewed
        return GraphNode(
            node_id=node_id(tenant_id, GraphNodeType.VENUE, venue.name),
            type=GraphNodeType.VENUE,
            name=venue.name,
            properties=props,
        )

    # --- FundingSource -----------------------------------------------

    def _write_funding(
        self, fs: FundingSourceMention, tenant_id: str
    ) -> GraphNode:
        props: dict = {
            "extraction_confidence": fs.extraction_confidence,
        }
        if fs.funding_type is not None:
            props["type"] = fs.funding_type.value
        props["potential_coi"] = fs.potential_coi
        return GraphNode(
            node_id=node_id(tenant_id, GraphNodeType.FUNDING_SOURCE, fs.name),
            type=GraphNodeType.FUNDING_SOURCE,
            name=fs.name,
            properties=props,
        )
