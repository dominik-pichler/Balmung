"""Port: splitting normalized text into chunks."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.document import Chunk


class Chunker(ABC):
    """Splits a normalized text into bounded chunks with provenance offsets."""

    @abstractmethod
    def chunk(self, document_id: str, text: str) -> list[Chunk]:
        """Return non-empty chunks.

        Each chunk must carry ``start_char`` / ``end_char`` offsets into the
        normalized text so callers can reconstruct the source span.
        """
        raise NotImplementedError
