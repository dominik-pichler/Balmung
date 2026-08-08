"""Deterministic ID generation.

All node and chunk IDs are derived from their content + tenant. This makes
upserts idempotent: re-ingesting the same source produces the same IDs and
overwrites nothing semantically new.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from .ontology import GraphNodeType

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


def node_id(
    tenant_id: str,
    node_type: GraphNodeType,
    *name_parts: str,
    paper_id: str | None = None,
) -> str:
    """Deterministic node id per the ontology.

    Formula: ``sha256(tenant_id || node_type || [paper_id] || canonical_name...)[:16]``.

    Including ``tenant_id`` partitions nodes per tenant, and including
    ``node_type`` prevents two different labels that share a canonical name
    (e.g. a ``Technology`` and a ``Problem`` both called "attention") from
    colliding onto the same id.

    ``paper_id`` is supplied only for **Level 2 (Epistemik)** nodes
    (Claim, Evidence, Experiment, Scope). Those are paper-scoped and must
    never merge across papers, so their id folds in the anchoring paper.
    Level 1 / Level 3 nodes omit it, so the same canonical entity merges
    across papers.

    ``name_parts`` are each canonicalized (NFKC + lowercase + whitespace
    collapse); ``tenant_id``, ``node_type`` and ``paper_id`` are used as-is.
    """
    parts: list[str] = [tenant_id, node_type.value]
    if paper_id is not None:
        parts.append(paper_id)
    parts.extend(canonicalize(p) for p in name_parts)
    return deterministic_id(*parts)
