"""Port: text embeddings for dedup and retrieval."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence


class Embedder(ABC):
    """Returns dense vector representations for one or more texts."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Output vector dimensionality."""
        raise NotImplementedError

    @abstractmethod
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding per input, in the same order."""
        raise NotImplementedError
