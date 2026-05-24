"""Deterministic fake embedder.

Uses hashing to produce stable vectors for a given input. Suitable for tests
and offline runs that need *some* embedding signal (e.g. dedup unit tests)
but no real semantic quality.
"""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Sequence

from ...ports.embedder import Embedder


class FakeEmbedder(Embedder):
    """Hash-derived embeddings — deterministic, no network."""

    def __init__(self, dimension: int = 32) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        # Expand the SHA-256 digest into ``dimension`` floats in [-1, 1].
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        out: list[float] = []
        i = 0
        while len(out) < self._dimension:
            if i + 4 > len(digest):
                # Re-hash to extend.
                digest = digest + hashlib.sha256(digest).digest()
            (val,) = struct.unpack_from(">I", digest, i)
            i += 4
            out.append((val / 0xFFFFFFFF) * 2.0 - 1.0)
        return out
