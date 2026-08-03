"""Distillate models — the output of the distillation lenses.

Each lens produces a typed slice of the distillate. Synthesis combines them
into a single ``Distillate`` instance, which is then mapped to graph nodes
and edges.

All extracted entities carry an explicit ``provenance`` field listing the
chunk IDs they were derived from. This keeps the ontology's "Source →
extracted entity" arrow honest end-to-end.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    """Common base for entities extracted by lenses.

    ``name`` is the surface form. ``canonical_name`` is the cleaned form used
    for ID derivation and dedup. ``confidence`` is the lens's self-reported
    confidence in [0, 1].
    """

    name: str
    canonical_name: str = ""
    confidence: float = 1.0
    provenance_chunk_ids: list[str] = Field(default_factory=list)

    def model_post_init(self, _ctx: object) -> None:
        if not self.canonical_name:
            # Default canonicalization happens here; the synthesis stage may
            # overwrite this if it merges semantically similar mentions.
            self.canonical_name = self.name.strip().lower()


# --- Per-lens output models -------------------------------------------------


class TopicMention(ExtractedEntity):
    """A topic mined from the source."""

    theme: Optional[str] = None  # Optional theme grouping (cross-source link).


class AffiliationMention(ExtractedEntity):
    """An organization an author is affiliated with."""


class AuthorMention(ExtractedEntity):
    """An author of the source, with optional affiliation + interests."""

    affiliation: Optional[AffiliationMention] = None
    interests: list[str] = Field(default_factory=list)


class AssumptionMention(ExtractedEntity):
    """An implicit assumption surfaced from the source."""

    statement: str = ""  # Optional long form, distinct from short name.


class TheoryMention(ExtractedEntity):
    """A theory the source builds or relies on."""

    statement: str = ""


class ConclusionMention(ExtractedEntity):
    """A conclusion derived in the source."""

    statement: str = ""
    supports_theories: list[str] = Field(default_factory=list)
    """Canonical names of theories this conclusion supports (within-doc link)."""


class MethodologyMention(ExtractedEntity):
    """A methodology used by the source."""

    description: str = ""


# --- Combined distillate ---------------------------------------------------


class LensOutput(BaseModel):
    """Wrapper for any single lens's output, plus failure metadata.

    Lenses always return a ``LensOutput``; an empty ``items`` list with a
    non-empty ``error`` indicates a recoverable failure that should not
    block the rest of the pipeline.
    """

    lens_name: str
    items: list[ExtractedEntity] = Field(default_factory=list)
    error: Optional[str] = None


class Distillate(BaseModel):
    """The synthesized distillate ``D_i`` for one source.

    Mirrors the six lens dimensions from the architecture diagram, plus the
    originating document ID and the chunk IDs that produced it.
    """

    document_id: str
    chunk_ids: list[str]

    topics: list[TopicMention] = Field(default_factory=list)
    authors: list[AuthorMention] = Field(default_factory=list)
    assumptions: list[AssumptionMention] = Field(default_factory=list)
    theories: list[TheoryMention] = Field(default_factory=list)
    conclusions: list[ConclusionMention] = Field(default_factory=list)
    methodologies: list[MethodologyMention] = Field(default_factory=list)
