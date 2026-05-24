"""Synthesis stage — merges lens outputs into a single ``Distillate``.

Responsibilities (per the architecture diagram):
  * **Merge**: combine the six lens outputs.
  * **Deduplicate**: within a single document, collapse entities sharing a
    canonical name. Cross-document semantic dedup is left to a separate
    process that runs on the persisted graph (out of scope for ingestion).
  * **Cross-reference**: within-document links such as
    ``Conclusion.supports_theories`` are normalized so downstream graph
    mapping can produce ``SUPPORTS`` edges.
"""

from __future__ import annotations

import structlog

from ...domain.distillate import (
    AssumptionMention,
    AuthorMention,
    ConclusionMention,
    Distillate,
    ExtractedEntity,
    LensOutput,
    MethodologyMention,
    TheoryMention,
    TopicMention,
)
from ...domain.ids import canonicalize
from .preprocess import PreprocessedDocument

log = structlog.get_logger(__name__)


_LENS_TO_FIELD: dict[str, str] = {
    "topic": "topics",
    "author": "authors",
    "assumption": "assumptions",
    "theory": "theories",
    "conclusion": "conclusions",
    "methodology": "methodologies",
}

_LENS_TO_TYPE: dict[str, type[ExtractedEntity]] = {
    "topic": TopicMention,
    "author": AuthorMention,
    "assumption": AssumptionMention,
    "theory": TheoryMention,
    "conclusion": ConclusionMention,
    "methodology": MethodologyMention,
}


class SynthesizeStage:
    """Combines lens outputs into a ``Distillate`` with deduplicated entities."""

    async def run(
        self,
        preprocessed: PreprocessedDocument,
        lens_outputs: list[LensOutput],
    ) -> Distillate:
        bucket: dict[str, list[ExtractedEntity]] = {f: [] for f in _LENS_TO_FIELD.values()}

        for lo in lens_outputs:
            field = _LENS_TO_FIELD.get(lo.lens_name)
            if field is None:
                log.warning("synthesize.unknown_lens", lens=lo.lens_name)
                continue
            for item in lo.items:
                bucket[field].append(_canonicalize_entity(item))

        # Dedup each bucket by canonical_name. Provenance and (where present)
        # nested fields are merged.
        deduped: dict[str, list[ExtractedEntity]] = {}
        for field, items in bucket.items():
            deduped[field] = _dedupe(items)

        # Normalize conclusion → theory references using canonical names of
        # theories actually present in this distillate.
        theory_canonicals = {t.canonical_name for t in deduped["theories"]}
        for c in deduped["conclusions"]:
            assert isinstance(c, ConclusionMention)
            c.supports_theories = [
                canonicalize(name)
                for name in c.supports_theories
                if canonicalize(name) in theory_canonicals
            ]

        distillate = Distillate(
            document_id=preprocessed.document_id,
            chunk_ids=[c.chunk_id for c in preprocessed.chunks],
            topics=deduped["topics"],  # type: ignore[arg-type]
            authors=deduped["authors"],  # type: ignore[arg-type]
            assumptions=deduped["assumptions"],  # type: ignore[arg-type]
            theories=deduped["theories"],  # type: ignore[arg-type]
            conclusions=deduped["conclusions"],  # type: ignore[arg-type]
            methodologies=deduped["methodologies"],  # type: ignore[arg-type]
        )
        log.info(
            "synthesize.completed",
            document_id=distillate.document_id,
            topics=len(distillate.topics),
            authors=len(distillate.authors),
            assumptions=len(distillate.assumptions),
            theories=len(distillate.theories),
            conclusions=len(distillate.conclusions),
            methodologies=len(distillate.methodologies),
        )
        return distillate


def _canonicalize_entity(item: ExtractedEntity) -> ExtractedEntity:
    item.canonical_name = canonicalize(item.name)
    return item


def _dedupe(items: list[ExtractedEntity]) -> list[ExtractedEntity]:
    """Merge entities sharing a canonical name.

    Strategy: keep the highest-confidence representative, union provenance,
    union list-typed fields (interests, supports_theories), prefer non-empty
    scalar fields from the higher-confidence entry.
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
    primary, secondary = (a, b) if a.confidence >= b.confidence else (b, a)
    merged_provenance = list(
        dict.fromkeys([*primary.provenance_chunk_ids, *secondary.provenance_chunk_ids])
    )

    update: dict[str, object] = {
        "provenance_chunk_ids": merged_provenance,
        "confidence": max(a.confidence, b.confidence),
    }

    # Type-specific union logic.
    if isinstance(primary, AuthorMention) and isinstance(secondary, AuthorMention):
        union_interests = list(dict.fromkeys([*primary.interests, *secondary.interests]))
        update["interests"] = union_interests
        if primary.affiliation is None and secondary.affiliation is not None:
            update["affiliation"] = secondary.affiliation
    if isinstance(primary, ConclusionMention) and isinstance(secondary, ConclusionMention):
        update["supports_theories"] = list(
            dict.fromkeys([*primary.supports_theories, *secondary.supports_theories])
        )

    return primary.model_copy(update=update)
