"""Source document and chunk models.

These represent the *raw* and *preprocessed* artifacts that flow into the
distillation lenses. They are pure data containers; no business logic lives
here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field

from .ids import content_hash, deterministic_id


class DocumentFormat(str, Enum):
    """Supported source document formats."""

    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    TEXT = "text"
    DOCX = "docx"
    # Audio / video / code / slides are placeholders for future adapters.
    AUDIO = "audio"
    VIDEO = "video"
    CODE = "code"
    SLIDES = "slides"


class DocumentMetadata(BaseModel):
    """Metadata accompanying every source.

    ``tenant_id`` partitions data for multi-tenant deployments and feeds into
    deterministic ID generation. ``source_id`` is the caller-supplied stable
    identifier (e.g. an S3 key, a CMS document id). ``uri`` is the locator.
    """

    tenant_id: str
    source_id: str
    uri: str
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )
    extra: dict[str, str] = Field(default_factory=dict)


class SourceDocument(BaseModel):
    """A raw document picked up by a ``DocumentSource``.

    ``raw_bytes`` is the unparsed payload. ``format`` tells the parser stage
    which adapter to invoke. ``content_sha256`` is the full hash, used for
    idempotency.
    """

    metadata: DocumentMetadata
    format: DocumentFormat
    raw_bytes: bytes
    content_sha256: str = ""

    def model_post_init(self, _ctx: object) -> None:
        """Auto-compute the content hash if the caller didn't supply one."""
        if not self.content_sha256:
            self.content_sha256 = content_hash(self.raw_bytes)

    @property
    def document_id(self) -> str:
        """Deterministic per-tenant document identifier.

        Hash combines tenant + source_id + content hash so the same logical
        source with the same content is the same node, and a content update
        produces a fresh ID (i.e. document versions are distinct nodes).
        """
        return deterministic_id(
            self.metadata.tenant_id,
            "source",
            self.metadata.source_id,
            self.content_sha256,
        )


class Chunk(BaseModel):
    """One unit of text emitted by the chunker.

    Provenance is carried explicitly: ``document_id`` + ``index`` + character
    offsets are enough to reconstruct the original span for citation.
    """

    chunk_id: str
    document_id: str
    index: int
    text: str
    start_char: int
    end_char: int
    token_estimate: int | None = None
