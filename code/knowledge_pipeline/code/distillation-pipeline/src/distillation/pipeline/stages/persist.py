"""Persistence stage: map the distillate to graph nodes/edges and write them.

Uses the three-layer writer architecture (``DomainWriter``, ``EpistemicWriter``,
``ProvenanceWriter``) that matches the current ontology in ``domain/ontology.py``.
"""

from __future__ import annotations

import structlog

from ...domain.distillate import Distillate
from ...domain.document import SourceDocument
from ...domain.graph import GraphEdge, GraphNode
from ...mapping.domain_writer import DomainWriter
from ...mapping.epistemic_writer import EpistemicWriter
from ...mapping.provenance_writer import ProvenanceWriter
from ...ports.graph_repository import GraphRepository

log = structlog.get_logger(__name__)


class PersistStage:
    def __init__(
        self,
        domain_writer: DomainWriter,
        epistemic_writer: EpistemicWriter,
        provenance_writer: ProvenanceWriter,
        repository: GraphRepository,
    ) -> None:
        self._domain = domain_writer
        self._epistemic = epistemic_writer
        self._provenance = provenance_writer
        self._repository = repository

    async def run(
        self, document: SourceDocument, distillate: Distillate
    ) -> tuple[int, int]:
        """Persist the distillate. Returns ``(node_count, edge_count)`` written."""
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        # Level 1: Domain (persistent, MERGE'd)
        nodes.extend(self._domain.write_technologies(distillate.technologies))
        nodes.extend(self._domain.write_problems(distillate.problems))
        nodes.extend(self._domain.write_capabilities(distillate.capabilities))
        nodes.extend(self._domain.write_metrics(distillate.metrics))
        nodes.extend(self._domain.write_datasets(distillate.datasets))
        nodes.extend(self._domain.write_assumptions(distillate.assumptions))
        nodes.extend(self._domain.write_limitations(distillate.limitations))

        # Level 2: Epistemik (paper-scoped, CREATE)
        for items in (
            self._epistemic.write_claims(
                distillate.claims,
                paper_id=distillate.paper_id,
                assumptions=distillate.assumptions,
            ),
            self._epistemic.write_evidence(distillate.evidence),
            self._epistemic.write_experiments(distillate.experiments),
            self._epistemic.write_scopes(distillate.scopes),
        ):
            item_nodes, item_edges = items
            nodes.extend(item_nodes)
            edges.extend(item_edges)

        # Level 3: Provenanz (persistent, MERGE'd)
        # The ingested document itself becomes the anchor Paper node, whose id
        # is the document_id that per-paper edges (MAKES_CLAIM, AUTHORED_BY)
        # point at.
        nodes.append(
            self._provenance.write_document_paper(document, distillate.paper_id)
        )
        extra_paper_nodes, extra_paper_edges = self._provenance.write_papers(
            distillate.papers
        )
        author_nodes, author_edges = self._provenance.write_authors(
            distillate.authors, paper_id=distillate.paper_id
        )
        nodes.extend(extra_paper_nodes)
        edges.extend(extra_paper_edges)
        nodes.extend(author_nodes)
        edges.extend(author_edges)
        nodes.extend(self._provenance.write_organizations(distillate.organizations))
        nodes.extend(self._provenance.write_venues(distillate.venues))
        nodes.extend(self._provenance.write_funding_sources(distillate.funding_sources))

        await self._repository.upsert_nodes(nodes)
        await self._repository.upsert_edges(edges)
        log.info(
            "persist.completed",
            document_id=document.document_id,
            nodes=len(nodes),
            edges=len(edges),
        )
        return len(nodes), len(edges)
