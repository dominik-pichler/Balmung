"""Port: storage for documents that failed processing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..domain.document import SourceDocument


class DeadLetterStore(ABC):
    """Persists failed documents alongside their error context for triage."""

    @abstractmethod
    async def record(
        self,
        document: SourceDocument,
        *,
        stage: str,
        error: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Persist one failure record."""
        raise NotImplementedError
