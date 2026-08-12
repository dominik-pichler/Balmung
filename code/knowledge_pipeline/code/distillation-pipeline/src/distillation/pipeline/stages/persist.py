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
from ...mapping.edges import EdgeLinker
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
        self._linker = EdgeLinker(epistemic_writer, provenance_writer)

    async def run(
        self, document: SourceDocument, distillate: Distillate
    ) -> tuple[int, int]:
        """Persist the distillate. Returns ``(node_count, edge_count)`` written."""
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        tenant_id = document.metadata.tenant_id
        paper_id = distillate.paper_id

        # Level 1: Domain (persistent, MERGE'd)
        nodes.extend(self._domain.write_technologies(distillate.technologies, tenant_id))
        nodes.extend(self._domain.write_problems(distillate.problems, tenant_id))
        nodes.extend(self._domain.write_capabilities(distillate.capabilities, tenant_id))
        nodes.extend(self._domain.write_metrics(distillate.metrics, tenant_id))
        nodes.extend(self._domain.write_datasets(distillate.datasets, tenant_id))
        nodes.extend(self._domain.write_assumptions(distillate.assumptions, tenant_id))
        nodes.extend(self._domain.write_limitations(distillate.limitations, tenant_id))

        # Level 2: Epistemik (paper-scoped, CREATE)
        for items in (
            self._epistemic.write_claims(
                distillate.claims,
                paper_id=paper_id,
                tenant_id=tenant_id,
            ),
            self._epistemic.write_evidence(
                distillate.evidence, paper_id=paper_id, tenant_id=tenant_id
            ),
            self._epistemic.write_experiments(
                distillate.experiments, paper_id=paper_id, tenant_id=tenant_id
            ),
            self._epistemic.write_scopes(
                distillate.scopes, paper_id=paper_id, tenant_id=tenant_id
            ),
        ):
            item_nodes, item_edges = items
            nodes.extend(item_nodes)
            edges.extend(item_edges)

        # Level 3: Provenanz (persistent, MERGE'd)
        # The ingested document itself becomes the anchor Paper node, whose id
        # is the document_id that per-paper edges (MAKES_CLAIM, AUTHORED_BY)
        # point at.
        nodes.append(
            self._provenance.write_document_paper(document, paper_id)
        )
        extra_paper_nodes, extra_paper_edges = self._provenance.write_papers(
            distillate.papers, tenant_id
        )
        author_nodes, author_edges = self._provenance.write_authors(
            distillate.authors, paper_id=paper_id, tenant_id=tenant_id
        )
        nodes.extend(extra_paper_nodes)
        edges.extend(extra_paper_edges)
        nodes.extend(author_nodes)
        edges.extend(author_edges)
        nodes.extend(self._provenance.write_organizations(distillate.organizations, tenant_id))
        nodes.extend(self._provenance.write_venues(distillate.venues, tenant_id))
        nodes.extend(
            self._provenance.write_funding_sources(distillate.funding_sources, tenant_id)
        )

        # Relationship + remaining structural edges, resolved once every node
        # exists (endpoints filtered to emitted nodes → no dangling edges).
        edges.extend(
            self._linker.link(
                nodes, distillate, tenant_id=tenant_id, paper_id=paper_id
            )
        )

        await self._repository.upsert_nodes(nodes)
        await self._repository.upsert_edges(edges)
        log.info(
            "persist.completed",
            document_id=document.document_id,
            nodes=len(nodes),
            edges=len(edges),
        )
        return len(nodes), len(edges)
