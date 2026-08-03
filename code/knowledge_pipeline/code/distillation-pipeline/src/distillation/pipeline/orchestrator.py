"""Pipeline orchestrator.

Drives the four stages — preprocess, distill, synthesize, persist — for each
document streamed by the ``DocumentSource``. Per-document failures are
dead-lettered with stage context; the loop keeps going.

Concurrency: documents are processed serially by default. To process N
documents in parallel, wrap ``ingest_one`` in ``asyncio.gather`` from the
caller — the pipeline itself is fully reentrant given separate
``PipelineContext`` instances.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from ..domain.document import SourceDocument
from ..ports.document_source import DocumentSource
from .context import PipelineContext

log = structlog.get_logger(__name__)


@dataclass(slots=True)
class IngestionResult:
    document_id: str
    nodes_written: int
    edges_written: int
    failed_lenses: list[str]


class IngestionPipeline:
    def __init__(self, context: PipelineContext) -> None:
        self._ctx = context

    async def ingest_one(self, document: SourceDocument) -> IngestionResult | None:
        """Run all four stages for a single document.

        Returns ``None`` if the document was dead-lettered before completion.
        """
        clear_contextvars()
        bind_contextvars(
            document_id=document.document_id,
            tenant_id=document.metadata.tenant_id,
            source_id=document.metadata.source_id,
        )

        try:
            preprocessed = await self._ctx.preprocess.run(document)
        except Exception as exc:
            await self._fail(document, stage="preprocess", error=exc)
            return None

        try:
            lens_outputs = await self._ctx.distill.run(preprocessed)
        except Exception as exc:
            await self._fail(document, stage="distill", error=exc)
            return None

        try:
            distillate = await self._ctx.synthesize.run(preprocessed, lens_outputs)
        except Exception as exc:
            await self._fail(document, stage="synthesize", error=exc)
            return None

        try:
            nodes_written, edges_written = await self._ctx.persist.run(
                document, distillate
            )
        except Exception as exc:
            await self._fail(document, stage="persist", error=exc)
            return None

        failed_lenses = [lo.lens_name for lo in lens_outputs if lo.error]
        log.info(
            "ingest.completed",
            nodes=nodes_written,
            edges=edges_written,
            failed_lenses=failed_lenses,
        )
        return IngestionResult(
            document_id=document.document_id,
            nodes_written=nodes_written,
            edges_written=edges_written,
            failed_lenses=failed_lenses,
        )

    async def ingest_all(self, source: DocumentSource) -> list[IngestionResult]:
        results: list[IngestionResult] = []
        async for document in source.stream():
            outcome = await self.ingest_one(document)
            if outcome is not None:
                results.append(outcome)
        return results

    async def _fail(
        self,
        document: SourceDocument,
        *,
        stage: str,
        error: BaseException,
    ) -> None:
        log.error("ingest.failed", stage=stage, error=str(error), exc_info=error)
        await self._ctx.dead_letter.record(
            document, stage=stage, error=str(error)
        )
