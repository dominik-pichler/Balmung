"""Deterministic ID generation.

All node and chunk IDs are derived from their content + tenant. This makes
upserts idempotent: re-ingesting the same source produces the same IDs and
overwrites nothing semantically new.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")


def canonicalize(text: str) -> str:
    """Normalize a string for use in deterministic IDs.

    Steps:
      1. NFKC unicode normalization (compatibility decomposition + recomposition).
      2. Lowercase.
      3. Strip and collapse internal whitespace.

    Two inputs producing the same canonical form are considered the same entity
    for ID purposes. Semantic dedup (e.g. "ML" ≈ "machine learning") happens
    elsewhere via embeddings.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.strip().lower()
    return _WHITESPACE_RE.sub(" ", text)


def deterministic_id(*parts: str, length: int = 16) -> str:
    """SHA-256 of the joined parts, truncated to ``length`` hex chars.

    Empty / None parts are tolerated. The separator (``|``) is chosen so it
    cannot appear inside a canonicalized name (which uses only collapsed
    whitespace and the input's own characters).
    """
    joined = "|".join(p or "" for p in parts)
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return digest[:length]


def content_hash(content: bytes | str) -> str:
    """Full SHA-256 of raw content, hex-encoded.

    Used for source-document identity and idempotency checks.
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()
