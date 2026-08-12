"""Distillate models — the output of the distillation lenses.

Each lens produces a typed slice of the distillate. Synthesis combines them
into a single ``Distillate`` instance, which is then mapped to graph nodes
and edges via three writers (domain, epistemic, provenance).

All extracted entities carry an explicit ``extraction_confidence`` field
in [0, 1]. This is required by the new ontology: every extraction-layer
node must carry it so the assessment engine can reason about extraction
uncertainty rather than trusting hallucinated values with full confidence.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field

from .ontology import (
    AssumptionType,
    CapabilityType,
    ClaimType,
    DataRegime,
    DatasetContaminationRisk,
    EvidenceDirection,
    EvidenceType,
    ExperimentType,
    FundingType,
    LimitationSeverity,
    MetricDirection,
    OrganizationType,
    Polarity,
    ReplicationStatus,
    TechnologyType,
    VenueTier,
)

# ====================================================================
# Base extraction entity
# ====================================================================


class ExtractedEntity(BaseModel):
    """Common base for entities extracted by lenses.

    ``extraction_confidence`` is REQUIRED and MUST NOT be hard-coded to 1.0.
    If the extraction model cannot produce a meaningful value, it should
    return a fallback derived from the extraction method (e.g. LLM logprobs,
    regex match quality, pattern completeness).
    """

    name: str
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    """Parser's self-reported confidence in [0, 1]."""
    provenance_chunk_ids: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]  # mypy can't stack computed_field over property
    @property
    def canonical_name(self) -> str:
        return self.name.strip().lower()


# ===
# Level 1: Domain entities (persistent, MERGE'd across papers)
# ====================================================================


class TechnologyMention(ExtractedEntity):
    """A technology mentioned in a source."""

    type: TechnologyType | None = None
    aliases: list[str] = Field(default_factory=list)
    first_described_in: str | None = None  # DOI of earliest known paper


class ProblemMention(ExtractedEntity):
    """A research problem addressed by the source."""

    domain: str | None = None


class CapabilityMention(ExtractedEntity):
    """A capability claimed for a technology."""

    description: str = ""
    capability_type: CapabilityType | None = None
    addresses: str | None = None  # name of a Problem this capability addresses


class MetricMention(ExtractedEntity):
    """A metric by which performance is measured."""

    unit: str | None = None
    direction: MetricDirection | None = None


class DatasetMention(ExtractedEntity):
    """A dataset used in the source."""

    domain: str | None = None
    size: int | None = None  # Nullable: not always reported
    contamination_risk: DatasetContaminationRisk | None = None


class AssumptionMention(ExtractedEntity):
    """An implicit assumption surfaced from the source."""

    statement: str = ""
    assumption_type: AssumptionType | None = None
    holds_under: str | None = None  # name of a Domain entity it holds under


class LimitationMention(ExtractedEntity):
    """A limitation on a technology or claim."""

    statement: str = ""
    severity: LimitationSeverity | None = None
    concerns: str | None = None  # name of a Domain entity this limitation concerns


# ====================================================================
# Level 2: Epistemik entities (reified, CREATE per paper)
# ====================================================================


class ClaimMention(ExtractedEntity):
    """A claim made by the source.

    Replaces the old ``hypothesis`` + ``confirmed`` / ``falsified`` model.
    Truth assessment is deferred to the Assessment Engine.
    """

    text: str = ""  # Full statement, not just a label
    claim_type: ClaimType | None = None
    polarity: Polarity | None = None  # positive = supports, negative = refutes
    stated_confidence: float | None = Field(
        default=None, ge=0.0, le=1.0
    )  # Author's hedging (e.g. "may" → 0.5)
    prior_implausibility: float | None = Field(
        default=None, ge=0.0, le=1.0
    )  # Base-rate: "X solves AGI" high, "X is 2% faster" low
    decay_immune: bool = False  # True for formal proofs
    about: list[str] = Field(default_factory=list)  # names of Domain entities (ABOUT)
    assumes: list[str] = Field(
        default_factory=list
    )  # names of Assumptions this claim rests on (ASSUMES)


class EvidenceMention(ExtractedEntity):
    """Evidence supporting or refuting a claim.

    Replaces ``confirmed``/``falsified`` as an edge-property.
    """

    type: EvidenceType | None = None
    effect_size: float | None = None  # Nullable: not always reported
    significance: float | None = None  # Nullable: not always reported
    direction: EvidenceDirection | None = None
    claim: str | None = None  # label of the Claim this evidence bears on


class ExperimentMention(ExtractedEntity):
    """An experiment that produced evidence."""

    experiment_type: ExperimentType | None = None
    sample_size: int | None = None  # Nullable: not always reported
    has_baseline: bool | None = None  # Nullable
    replication_status: ReplicationStatus | None = None
    leakage_risk: DatasetContaminationRisk | None = None
    preregistered: bool = False
    # Relationship references (resolved to PRODUCED_BY / EVALUATED_ON / MEASURED_BY):
    technologies: list[str] = Field(default_factory=list)  # Technology names
    datasets: list[str] = Field(default_factory=list)  # Dataset names
    metrics: list[str] = Field(default_factory=list)  # Metric names


class ScopeMention(ExtractedEntity):
    """The operational scope of a claim/experiment."""

    data_domain: str | None = None
    language: str | None = None
    scale: str | None = None
    data_regime: DataRegime | None = None
    hardware: str | None = None
    time_window: str | None = None


# ====================================================================
# Level 3: Provenanz entities (persistent, MERGE'd)
# ====================================================================


class PaperMention(ExtractedEntity):
    """A paper, identified by DOI where available."""

    title: str | None = None
    year: int | None = None
    venue_tier: VenueTier | None = None
    peer_reviewed: bool | None = None
    is_preprint: bool = False


class AuthorMention(ExtractedEntity):
    """An author of the source, with optional ORCID and affiliation."""

    orcid: str | None = None
    affiliation: AffiliationMention | None = None
    interests: list[str] = Field(default_factory=list)
    position: int | None = None  # Author position in the paper


class AffiliationMention(ExtractedEntity):
    """An organizational affiliation (e.g. university, company)."""

    org_type: OrganizationType | None = None


class OrganizationMention(ExtractedEntity):
    """An organization."""

    org_type: OrganizationType | None = None


class VenueMention(ExtractedEntity):
    """A conference/journal venue."""

    tier: VenueTier | None = None
    peer_reviewed: bool | None = None


class FundingSourceMention(ExtractedEntity):
    """A funding source for a paper."""

    funding_type: FundingType | None = None
    potential_coi: bool = False


# ====================================================================
# Combined distillate
# ====================================================================


class LensOutput(BaseModel):
    """Wrapper for any single lens's output, plus failure metadata."""

    lens_name: str
    items: list[ExtractedEntity] = Field(default_factory=list)
    error: str | None = None


class Distillate(BaseModel):
    """The synthesized distillate for one paper.

    Three logically separate lists, each feeding a different writer:
    - ``domain_entities`` → DomainWriter (persistent)
    - ``claims``, ``evidence``, ``experiments``, ``scopes`` → EpistemicWriter (per-paper)
    - ``papers``, ``authors``, ``organizations``, ``venues``, ``funding_sources`` → ProvenanceWriter (persistent)
    """

    paper_id: str
    chunk_ids: list[str]

    # Level 1: Domain
    technologies: list[TechnologyMention] = Field(default_factory=list)
    problems: list[ProblemMention] = Field(default_factory=list)
    capabilities: list[CapabilityMention] = Field(default_factory=list)
    metrics: list[MetricMention] = Field(default_factory=list)
    datasets: list[DatasetMention] = Field(default_factory=list)
    assumptions: list[AssumptionMention] = Field(default_factory=list)
    limitations: list[LimitationMention] = Field(default_factory=list)

    # Level 2: Epistemik
    claims: list[ClaimMention] = Field(default_factory=list)
    evidence: list[EvidenceMention] = Field(default_factory=list)
    experiments: list[ExperimentMention] = Field(default_factory=list)
    scopes: list[ScopeMention] = Field(default_factory=list)

    # Level 3: Provenanz
    papers: list[PaperMention] = Field(default_factory=list)
    authors: list[AuthorMention] = Field(default_factory=list)
    affiliations: list[AffiliationMention] = Field(default_factory=list)
    organizations: list[OrganizationMention] = Field(default_factory=list)
    venues: list[VenueMention] = Field(default_factory=list)
    funding_sources: list[FundingSourceMention] = Field(default_factory=list)
