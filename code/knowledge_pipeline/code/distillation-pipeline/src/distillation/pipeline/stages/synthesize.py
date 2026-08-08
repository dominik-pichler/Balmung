"""Synthesis stage — merges lens outputs into a single ``Distillate``.

Responsibilities (per the architecture diagram):
  * **Merge**: combine the lens outputs.
  * **Deduplicate**: within a single document, collapse entities sharing a
    canonical name. Cross-document semantic dedup is left to a separate
    process that runs on the persisted graph (out of scope for ingestion).
"""

from __future__ import annotations

import structlog

from ...domain.distillate import (
    AssumptionMention,
    AuthorMention,
    ClaimMention,
    Distillate,
    ExtractedEntity,
    LensOutput,
)
from .preprocess import PreprocessedDocument

log = structlog.get_logger(__name__)


# Lenses whose outputs are deduplicated by canonical name within a document.
_LENS_TO_FIELD: dict[str, str] = {
    "author": "authors",
    "assumption": "assumptions",
}

_LENS_TO_TYPE: dict[str, type[ExtractedEntity]] = {
    "author": AuthorMention,
    "assumption": AssumptionMention,
    "claim": ClaimMention,
}


class SynthesizeStage:
    """Combines lens outputs into a ``Distillate`` with deduplicated entities."""

    async def run(
        self,
        preprocessed: PreprocessedDocument,
        lens_outputs: list[LensOutput],
    ) -> Distillate:
        bucket: dict[str, list[ExtractedEntity]] = {f: [] for f in _LENS_TO_FIELD.values()}
        # Claims are paper-scoped and never merged by name (distinct claims can
        # share a short label). They are deduped at the node level by claim id.
        claims: list[ClaimMention] = []

        for lo in lens_outputs:
            if lo.lens_name == "claim":
                claims.extend(c for c in lo.items if isinstance(c, ClaimMention))
                continue
            field = _LENS_TO_FIELD.get(lo.lens_name)
            if field is None:
                log.warning("synthesize.unknown_lens", lens=lo.lens_name)
                continue
            for item in lo.items:
                bucket[field].append(item)

        # Dedup each bucket by canonical_name. Provenance and (where present)
        # nested fields are merged.
        deduped: dict[str, list[ExtractedEntity]] = {}
        for field, items in bucket.items():
            deduped[field] = _dedupe(items)

        distillate = Distillate(
            paper_id=preprocessed.document_id,
            chunk_ids=[c.chunk_id for c in preprocessed.chunks],
            authors=deduped["authors"],  # type: ignore[arg-type]
            assumptions=deduped["assumptions"],  # type: ignore[arg-type]
            claims=claims,
        )
        log.info(
            "synthesize.completed",
            document_id=distillate.paper_id,
            authors=len(distillate.authors),
            assumptions=len(distillate.assumptions),
            claims=len(distillate.claims),
        )
        return distillate


def _dedupe(items: list[ExtractedEntity]) -> list[ExtractedEntity]:
    """Merge entities sharing a canonical name.

    Strategy: keep the highest-confidence representative, union provenance,
    union list-typed fields (interests), prefer non-empty scalar fields from
    the higher-confidence entry.
    """
    by_canonical: dict[str, ExtractedEntity] = {}
    for item in items:
        existing = by_canonical.get(item.canonical_name)
        if existing is None:
            by_canonical[item.canonical_name] = item
            continue
        by_canonical[item.canonical_name] = _merge_two(existing, item)
    return list(by_canonical.values())


def _merge_two(a: ExtractedEntity, b: ExtractedEntity) -> ExtractedEntity:
    primary, secondary = (
        (a, b) if a.extraction_confidence >= b.extraction_confidence else (b, a)
    )
    merged_provenance = list(
        dict.fromkeys([*primary.provenance_chunk_ids, *secondary.provenance_chunk_ids])
    )

    update: dict[str, object] = {
        "provenance_chunk_ids": merged_provenance,
        "extraction_confidence": max(a.extraction_confidence, b.extraction_confidence),
    }

    # Type-specific union logic.
    if isinstance(primary, AuthorMention) and isinstance(secondary, AuthorMention):
        union_interests = list(dict.fromkeys([*primary.interests, *secondary.interests]))
        update["interests"] = union_interests
        if primary.affiliation is None and secondary.affiliation is not None:
            update["affiliation"] = secondary.affiliation

    return primary.model_copy(update=update)
