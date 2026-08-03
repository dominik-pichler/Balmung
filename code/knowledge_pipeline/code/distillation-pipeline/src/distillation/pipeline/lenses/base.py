"""Base class for distillation lenses.

Every lens follows the same shape:

  1. Concatenate (a window of) chunks.
  2. Call the LLM with a lens-specific system prompt + a typed response
     model.
  3. Project the response into the appropriate ``ExtractedEntity`` subclass
     list, stamped with chunk provenance.

The base class owns step 1 and step 3 so the concrete lenses only ship the
prompt and the response shape.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import structlog
from pydantic import BaseModel

from ...domain.distillate import ExtractedEntity, LensOutput
from ...domain.document import Chunk
from ...ports.llm_client import LLMClient, LLMError

TResponse = TypeVar("TResponse", bound=BaseModel)
TEntity = TypeVar("TEntity", bound=ExtractedEntity)

log = structlog.get_logger(__name__)


class Lens(ABC, Generic[TResponse, TEntity]):
    """One distillation dimension over a document's chunks."""

    name: str

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    # --- to implement -----------------------------------------------------

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Lens-specific system prompt."""
        raise NotImplementedError

    @property
    @abstractmethod
    def response_model(self) -> type[TResponse]:
        """Pydantic model the LLM must return."""
        raise NotImplementedError

    @abstractmethod
    def project(
        self, response: TResponse, chunk_ids: list[str]
    ) -> list[TEntity]:
        """Convert the LLM response into the lens's entity list."""
        raise NotImplementedError

    # --- shared behavior --------------------------------------------------

    async def apply(self, chunks: list[Chunk]) -> LensOutput:
        """Run the lens against all chunks of a document.

        Failures are captured into ``LensOutput.error`` so one lens failure
        does not abort the entire distillate.
        """
        if not chunks:
            return LensOutput(lens_name=self.name, items=[])

        user_prompt = _format_chunks(chunks)
        chunk_ids = [c.chunk_id for c in chunks]

        try:
            response = await self._llm.structured(
                system=self.system_prompt,
                user=user_prompt,
                response_model=self.response_model,
            )
        except (LLMError, ValueError) as exc:
            log.warning(
                "lens.failed",
                lens=self.name,
                error=str(exc),
                chunk_count=len(chunks),
            )
            return LensOutput(lens_name=self.name, items=[], error=str(exc))

        items = self.project(response, chunk_ids)
        # Stamp provenance on every item that doesn't already carry it.
        for item in items:
            if not item.provenance_chunk_ids:
                item.provenance_chunk_ids = list(chunk_ids)

        log.info("lens.applied", lens=self.name, item_count=len(items))
        return LensOutput(lens_name=self.name, items=list(items))


def _format_chunks(chunks: list[Chunk]) -> str:
    """Render chunks for the LLM with explicit boundaries."""
    parts: list[str] = []
    for c in chunks:
        parts.append(f"[chunk index={c.index} id={c.chunk_id}]\n{c.text}")
    return "\n\n".join(parts)
