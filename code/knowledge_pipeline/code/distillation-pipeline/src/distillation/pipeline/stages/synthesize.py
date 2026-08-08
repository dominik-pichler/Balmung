"""Synthesis stage — merges lens outputs into a single ``Distillate``.

Responsibilities (per the architecture diagram):
  * **Merge**: combine the lens outputs into one ``Distillate``. Items are
    routed to the right field by their *entity type*, so a single multi-entity
    lens (e.g. ``DomainLens``) can feed several fields.
  * **Deduplicate**: within a single document, collapse entities sharing a
    canonical name. Cross-document semantic dedup is left to a separate
    process that runs on the persisted graph (out of scope for ingestion).

Claims are the one exception to name-dedup: distinct claims can share a short
label, so they are kept as-is here and deduplicated at the node level by their
paper-scoped claim id.
"""

from __future__ import annotations

import structlog

from ...domain.distillate import (
    AffiliationMention,
    AssumptionMention,
    AuthorMention,
    CapabilityMention,
    ClaimMention,
    DatasetMention,
    Distillate,
    EvidenceMention,
    ExperimentMention,
    ExtractedEntity,
    FundingSourceMention,
    LensOutput,
    LimitationMention,
    MetricMention,
    OrganizationMention,
    PaperMention,
    ProblemMention,
    ScopeMention,
    TechnologyMention,
    VenueMention,
)
from .preprocess import PreprocessedDocument

log = structlog.get_logger(__name__)


# Entity type → Distillate field. Routing by type (not lens name) lets a single
# multi-entity lens contribute to several fields. Claims are handled separately
# (never name-deduped).
_TYPE_TO_FIELD: dict[type[ExtractedEntity], str] = {
    TechnologyMention: "technologies",
    ProblemMention: "problems",
    CapabilityMention: "capabilities",
    MetricMention: "metrics",
    DatasetMention: "datasets",
    AssumptionMention: "assumptions",
    LimitationMention: "limitations",
    EvidenceMention: "evidence",
    ExperimentMention: "experiments",
    ScopeMention: "scopes",
    PaperMention: "papers",
    AuthorMention: "authors",
    AffiliationMention: "affiliations",
    OrganizationMention: "organizations",
    VenueMention: "venues",
    FundingSourceMention: "funding_sources",
}


class SynthesizeStage:
    """Combines lens outputs into a ``Distillate`` with deduplicated entities."""

    async def run(
        self,
        preprocessed: PreprocessedDocument,
        lens_outputs: list[LensOutput],
    ) -> Distillate:
        buckets: dict[str, list[ExtractedEntity]] = {
            field: [] for field in _TYPE_TO_FIELD.values()
        }
        # Claims are paper-scoped and never merged by name (distinct claims can
        # share a short label). They are deduped at the node level by claim id.
        claims: list[ClaimMention] = []

        for lo in lens_outputs:
            for item in lo.items:
                if isinstance(item, ClaimMention):
                    claims.append(item)
                    continue
                field = _TYPE_TO_FIELD.get(type(item))
                if field is None:
                    log.warning(
                        "synthesize.unknown_entity",
                        lens=lo.lens_name,
                        entity_type=type(item).__name__,
                    )
                    continue
                buckets[field].append(item)

        # Dedup each bucket by canonical_name. Provenance and (where present)
        # nested/list fields are merged.
        deduped = {field: _dedupe(items) for field, items in buckets.items()}

        distillate = Distillate(
            paper_id=preprocessed.document_id,
            chunk_ids=[c.chunk_id for c in preprocessed.chunks],
            claims=claims,
            **deduped,  # type: ignore[arg-type]
        )
        log.info(
            "synthesize.completed",
            document_id=distillate.paper_id,
            **{field: len(items) for field, items in deduped.items() if items},
            claims=len(claims),
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
