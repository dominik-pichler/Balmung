"""Distillation stage — fans out to the configured lenses in parallel.

Each lens runs concurrently via ``asyncio.gather`` (bounded by a semaphore).
Per-lens failures are captured in ``LensOutput.error`` and do not abort the
rest of the pipeline: this matches the ontology, where a missing dimension just
produces fewer nodes/edges rather than a catastrophic failure.
"""

from __future__ import annotations

import asyncio

import structlog

from ...domain.distillate import LensOutput
from ..lenses.base import Lens
from .preprocess import PreprocessedDocument

log = structlog.get_logger(__name__)


class DistillStage:
    """Applies all configured lenses to the preprocessed document."""

    def __init__(self, lenses: list[Lens], max_concurrency: int = 4) -> None:
        if not lenses:
            raise ValueError("At least one lens is required")
        self._lenses = lenses
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def run(self, preprocessed: PreprocessedDocument) -> list[LensOutput]:
        async def _bounded(lens: Lens) -> LensOutput:
            async with self._semaphore:
                return await lens.apply(preprocessed.chunks)

        outputs = await asyncio.gather(*[_bounded(lens) for lens in self._lenses])
        log.info(
            "distill.completed",
            document_id=preprocessed.document_id,
            lens_count=len(outputs),
            failed_lenses=[o.lens_name for o in outputs if o.error],
        )
        return list(outputs)
