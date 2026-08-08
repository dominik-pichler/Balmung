"""ProvenanceWriter — writes Level 3 (persistent provenance) nodes.

Writes ``Paper``, ``Author``, ``Organization``, ``Venue``, ``FundingSource``
via MERGE on ``node_id``.

These nodes are persistent across papers: same ORCID or canonical name
→ same ``node_id`` → MERGE ON MATCH ON CREATE.

Author-Matching priority:
  1. ORCID (unique, machine-readable)
  2. Normalized name + affiliation (fallback for older papers without ORCID)

This is critical for Independence-Detection: wrong Author matching
breaks the entire bias analysis later.
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
from ..domain.ids import canonicalize, deterministic_id


class ProvenanceWriter:
    """Produces persistent (MERGE'd) provenance nodes and edges."""

    def __init__(self) -> None:
        self._author_orcid_map: dict[str, GraphNode] = {}
        self._author_name_map: dict[str, GraphNode] = {}

    # --- public API -----------------------------------------------------

    def write_papers(
        self, entities: Iterable[PaperMention],
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for paper in entities:
            n, e = self._write_paper(paper)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    def write_authors(
        self,
        entities: Iterable[AuthorMention],
        paper_id: str,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for author in entities:
            n, e = self._write_author(author, paper_id)
            nodes.append(n)
            edges.extend(e)
        return nodes, edges

    def write_organizations(
        self, entities: Iterable[OrganizationMention],
    ) -> list[GraphNode]:
        return [self._write_organization(org) for org in entities]

    def write_venues(
        self, entities: Iterable[VenueMention],
    ) -> list[GraphNode]:
        return [self._write_venue(v) for v in entities]

    def write_funding_sources(
        self, entities: Iterable[FundingSourceMention],
    ) -> list[GraphNode]:
        return [self._write_funding(fs) for fs in entities]

    # --- Paper (from the ingested document) -----------------------------

    def write_document_paper(
        self, document: SourceDocument, paper_id: str
    ) -> GraphNode:
        """Build the ``Paper`` node representing the ingested document.

        The node id is the ``document_id`` so that per-paper edges
        (``MAKES_CLAIM``, ``AUTHORED_BY``) anchor to the same node.
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

    def _paper_id(self, paper: PaperMention) -> str:
        """Paper ID: prefer DOI from metadata, otherwise sha256(title[:50])."""
        # The PaperMention may carry a ``name`` that is the DOI, or we
        # derive from title. The caller is responsible for setting
        # name=DOI when a DOI is available.
        return deterministic_id("paper", canonicalize(paper.name))

    def _write_paper(
        self, paper: PaperMention
    ) -> tuple[GraphNode, list[GraphEdge]]:
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        node_id = self._paper_id(paper)

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
            node_id=node_id,
            type=GraphNodeType.PAPER,
            name=paper.name,
            properties=props,
        )
        nodes.append(node)

        return node, edges

    # --- Author (with ORCID matching) ---------------------------------

    def _author_id(self, author: AuthorMention) -> str:
        """Author ID: prefer ORCID, fallback to (name + affiliation).

        This is the most critical matching logic for Independence-Detection:
        - If ORCID is available → use it directly (most precise).
        - Otherwise → sha256(normalized_name + "|" + normalized_affiliation).
        """
        if author.orcid:
            return deterministic_id("author", canonicalize(author.orcid))
        # Fallback: name + affiliation. Affiliation helps disambiguate
        # "John Smith" from different institutions.
        affiliation = (
            canonicalize(author.affiliation.name) if author.affiliation else ""
        )
        return deterministic_id(
            "author", canonicalize(author.name), affiliation
        )

    def _write_author(
        self, author: AuthorMention, paper_id: str
    ) -> tuple[GraphNode, list[GraphEdge]]:
        edges: list[GraphEdge] = []

        node_id = self._author_id(author)

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
            node_id=node_id,
            type=GraphNodeType.AUTHOR,
            name=author.name,
            properties=props,
        )

        # Paper → Author: AUTHORED_BY
        edges.append(
            GraphEdge(
                source_node_id=paper_id,
                target_node_id=node_id,
                type=GraphEdgeType.AUTHORED_BY,
                extraction_confidence=author.extraction_confidence,
            )
        )

        return node, edges

    # --- Organization -----------------------------------------------

    def _organization_id(self, org: OrganizationMention) -> str:
        return deterministic_id("org", canonicalize(org.name))

    def _write_organization(
        self, org: OrganizationMention
    ) -> GraphNode:
        props: dict = {
            "extraction_confidence": org.extraction_confidence,
        }
        if org.org_type is not None:
            props["type"] = org.org_type.value
        return GraphNode(
            node_id=self._organization_id(org),
            type=GraphNodeType.ORGANIZATION,
            name=org.name,
            properties=props,
        )

    # --- Venue ----------------------------------------------------------

    def _venue_id(self, venue: VenueMention) -> str:
        return deterministic_id("venue", canonicalize(venue.name))

    def _write_venue(
        self, venue: VenueMention
    ) -> GraphNode:
        props: dict = {
            "extraction_confidence": venue.extraction_confidence,
        }
        if venue.tier is not None:
            props["tier"] = venue.tier.value
        if venue.peer_reviewed is not None:
            props["peer_reviewed"] = venue.peer_reviewed
        return GraphNode(
            node_id=self._venue_id(venue),
            type=GraphNodeType.VENUE,
            name=venue.name,
            properties=props,
        )

    # --- FundingSource -----------------------------------------------

    def _funding_id(self, fs: FundingSourceMention) -> str:
        return deterministic_id("funding", canonicalize(fs.name))

    def _write_funding(
        self, fs: FundingSourceMention
    ) -> GraphNode:
        props: dict = {
            "extraction_confidence": fs.extraction_confidence,
        }
        if fs.funding_type is not None:
            props["type"] = fs.funding_type.value
        props["potential_coi"] = fs.potential_coi
        return GraphNode(
            node_id=self._funding_id(fs),
            type=GraphNodeType.FUNDING_SOURCE,
            name=fs.name,
            properties=props,
        )
