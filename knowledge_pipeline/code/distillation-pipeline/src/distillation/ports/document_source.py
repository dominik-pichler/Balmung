"""Port: where source documents come from."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from ..domain.document import SourceDocument


class DocumentSource(ABC):
    """Pulls raw documents into the pipeline.

    Implementations decide whether they yield from a local directory, an
    object store, a queue, or a polling API. The pipeline doesn't care.
    """

    @abstractmethod
    def stream(self) -> AsyncIterator[SourceDocument]:
        """Yield documents one at a time.

        Must be an async iterator so backpressure works naturally across
        slow IO (S3, HTTP) without blocking the event loop.
        """
        raise NotImplementedError
