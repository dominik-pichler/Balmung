"""EvidenceLens — extracts Level 2 (epistemik) supporting entities.

Covers the paper-scoped entities that sit alongside claims: evidence,
experiments, and scopes. Claims themselves are handled by :class:`ClaimLens`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...domain.distillate import (
    EvidenceMention,
    ExperimentMention,
    ExtractedEntity,
    ScopeMention,
)
from ...domain.ontology import (
    DataRegime,
    DatasetContaminationRisk,
    EvidenceDirection,
    EvidenceType,
    ExperimentType,
    ReplicationStatus,
)
from .base import Lens, parse_enum


class _EvidenceItem(BaseModel):
    name: str
    type: str | None = None  # supporting | refuting
    effect_size: float | None = None
    significance: float | None = None
    direction: str | None = None  # positive | negative | neutral
    claim: str | None = None  # label of the Claim this evidence bears on
    confidence: float = 0.6


class _ExperimentItem(BaseModel):
    name: str
    experiment_type: str | None = None
    sample_size: int | None = None
    has_baseline: bool | None = None
    replication_status: str | None = None
    leakage_risk: str | None = None
    technologies: list[str] = Field(default_factory=list)  # PRODUCED_BY targets
    datasets: list[str] = Field(default_factory=list)  # EVALUATED_ON targets
    metrics: list[str] = Field(default_factory=list)  # MEASURED_BY targets
    confidence: float = 0.6


class _ScopeItem(BaseModel):
    name: str
    data_domain: str | None = None
    language: str | None = None
    scale: str | None = None
    data_regime: str | None = None
    hardware: str | None = None
    time_window: str | None = None
    confidence: float = 0.6


class EvidenceResponse(BaseModel):
    evidence: list[_EvidenceItem] = Field(default_factory=list)
    experiments: list[_ExperimentItem] = Field(default_factory=list)
    scopes: list[_ScopeItem] = Field(default_factory=list)


class EvidenceLens(Lens[EvidenceResponse, ExtractedEntity]):
    """Extracts evidence, experiments, and scopes from a source."""

    name = "evidence"

    @property
    def system_prompt(self) -> str:
        return (
            "You extract the EVIDENTIAL basis of a source's claims:\n"
            "- evidence: specific supporting or refuting data points (type is "
            "'supporting' or 'refuting'; direction is positive/negative/neutral; "
            "include effect_size / significance if reported). Set 'claim' to the "
            "label or text of the Claim this evidence bears on, using the same "
            "wording the claim is given elsewhere, so it links.\n"
            "- experiments: the experimental setups that produced evidence "
            "(experiment_type, sample_size, whether there was a baseline, "
            "replication status). For each experiment also list: 'technologies' "
            "(the technologies it runs/produces), 'datasets' (datasets it "
            "evaluates on), and 'metrics' (metrics it measures) — using the same "
            "short names those entities are given elsewhere.\n"
            "- scopes: the operational boundaries a result holds under (data "
            "domain, language, scale, hardware, time window)\n\n"
            "Use consistent, short names so references match. Omit fields you "
            "cannot determine. Provide a 'confidence' in [0,1] (never 1.0 unless "
            "verbatim)."
        )

    @property
    def response_model(self) -> type[EvidenceResponse]:
        return EvidenceResponse

    def project(
        self, response: EvidenceResponse, chunk_ids: list[str]
    ) -> list[ExtractedEntity]:
        out: list[ExtractedEntity] = []
        out.extend(
            EvidenceMention(
                name=e.name,
                type=parse_enum(EvidenceType, e.type),
                effect_size=e.effect_size,
                significance=e.significance,
                direction=parse_enum(EvidenceDirection, e.direction),
                claim=e.claim,
                extraction_confidence=e.confidence,
            )
            for e in response.evidence
        )
        out.extend(
            ExperimentMention(
                name=x.name,
                experiment_type=parse_enum(ExperimentType, x.experiment_type),
                sample_size=x.sample_size,
                has_baseline=x.has_baseline,
                replication_status=parse_enum(ReplicationStatus, x.replication_status),
                leakage_risk=parse_enum(DatasetContaminationRisk, x.leakage_risk),
                technologies=x.technologies,
                datasets=x.datasets,
                metrics=x.metrics,
                extraction_confidence=x.confidence,
            )
            for x in response.experiments
        )
        out.extend(
            ScopeMention(
                name=s.name,
                data_domain=s.data_domain,
                language=s.language,
                scale=s.scale,
                data_regime=parse_enum(DataRegime, s.data_regime),
                hardware=s.hardware,
                time_window=s.time_window,
                extraction_confidence=s.confidence,
            )
            for s in response.scopes
        )
        return out
