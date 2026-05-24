"""Persistence stage: write nodes and edges to the graph repository."""

from __future__ import annotations

import structlog

from ...domain.distillate import Distillate
from ...domain.document import SourceDocument
from ...mapping.graph_mapper import GraphMapper
from ...ports.graph_repository import GraphRepository

log = structlog.get_logger(__name__)


class PersistStage:
    def __init__(self, mapper: GraphMapper, repository: GraphRepository) -> None:
        self._mapper = mapper
        self._repository = repository

    async def run(
        self, document: SourceDocument, distillate: Distillate
    ) -> tuple[int, int]:
        """Persist the distillate. Returns ``(node_count, edge_count)`` written."""
        nodes, edges = self._mapper.map(document, distillate)
        await self._repository.upsert_nodes(nodes)
        await self._repository.upsert_edges(edges)
        log.info(
            "persist.completed",
            document_id=document.document_id,
            nodes=len(nodes),
            edges=len(edges),
        )
        return len(nodes), len(edges)
