"""DomainLens — extracts Level 1 (persistent domain) entities.

One multi-entity lens covering the domain layer: technologies, problems,
capabilities, metrics, datasets, and limitations. Assumptions have their own
dedicated :class:`AssumptionLens` (they also drive the L2 ``ASSUMES`` edge).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...domain.distillate import (
    CapabilityMention,
    DatasetMention,
    ExtractedEntity,
    LimitationMention,
    MetricMention,
    ProblemMention,
    TechnologyMention,
)
from ...domain.ontology import (
    CapabilityType,
    DatasetContaminationRisk,
    LimitationSeverity,
    MetricDirection,
    TechnologyType,
)
from .base import Lens, parse_enum


class _TechItem(BaseModel):
    name: str
    type: str | None = None
    aliases: list[str] = Field(default_factory=list)
    confidence: float = 0.6


class _ProblemItem(BaseModel):
    name: str
    domain: str | None = None
    confidence: float = 0.6


class _CapabilityItem(BaseModel):
    name: str
    description: str = ""
    capability_type: str | None = None
    addresses: str | None = None  # name of a Problem this capability addresses
    confidence: float = 0.6


class _MetricItem(BaseModel):
    name: str
    unit: str | None = None
    direction: str | None = None
    confidence: float = 0.6


class _DatasetItem(BaseModel):
    name: str
    domain: str | None = None
    size: int | None = None
    contamination_risk: str | None = None
    confidence: float = 0.6


class _LimitationItem(BaseModel):
    name: str
    statement: str = ""
    severity: str | None = None
    concerns: str | None = None  # name of a Domain entity this limitation concerns
    confidence: float = 0.6


class DomainResponse(BaseModel):
    technologies: list[_TechItem] = Field(default_factory=list)
    problems: list[_ProblemItem] = Field(default_factory=list)
    capabilities: list[_CapabilityItem] = Field(default_factory=list)
    metrics: list[_MetricItem] = Field(default_factory=list)
    datasets: list[_DatasetItem] = Field(default_factory=list)
    limitations: list[_LimitationItem] = Field(default_factory=list)


class DomainLens(Lens[DomainResponse, ExtractedEntity]):
    """Extracts the persistent domain entities of a source."""

    name = "domain"

    @property
    def system_prompt(self) -> str:
        return (
            "You extract the DOMAIN entities of a source document — the "
            "persistent, cross-paper concepts. Extract:\n"
            "- technologies: models, algorithms, architectures, systems, tools\n"
            "- problems: research problems the work addresses\n"
            "- capabilities: what a technology can do (functional, performance, "
            "robustness, safety)\n"
            "- metrics: how performance is measured (with unit and whether "
            "higher_better or lower_better)\n"
            "- datasets: datasets used or introduced\n"
            "- limitations: constraints on a technology or result\n\n"
            "Give each a short name. Omit fields you cannot determine. Provide a "
            "'confidence' in [0,1] reflecting extraction certainty (never 1.0 "
            "unless verbatim)."
        )

    @property
    def response_model(self) -> type[DomainResponse]:
        return DomainResponse

    def project(
        self, response: DomainResponse, chunk_ids: list[str]
    ) -> list[ExtractedEntity]:
        out: list[ExtractedEntity] = []
        out.extend(
            TechnologyMention(
                name=t.name,
                type=parse_enum(TechnologyType, t.type),
                aliases=t.aliases,
                extraction_confidence=t.confidence,
            )
            for t in response.technologies
        )
        out.extend(
            ProblemMention(
                name=p.name, domain=p.domain, extraction_confidence=p.confidence
            )
            for p in response.problems
        )
        out.extend(
            CapabilityMention(
                name=c.name,
                description=c.description,
                capability_type=parse_enum(CapabilityType, c.capability_type),
                addresses=c.addresses,
                extraction_confidence=c.confidence,
            )
            for c in response.capabilities
        )
        out.extend(
            MetricMention(
                name=m.name,
                unit=m.unit,
                direction=parse_enum(MetricDirection, m.direction),
                extraction_confidence=m.confidence,
            )
            for m in response.metrics
        )
        out.extend(
            DatasetMention(
                name=d.name,
                domain=d.domain,
                size=d.size,
                contamination_risk=parse_enum(
                    DatasetContaminationRisk, d.contamination_risk
                ),
                extraction_confidence=d.confidence,
            )
            for d in response.datasets
        )
        out.extend(
            LimitationMention(
                name=limitation.name,
                statement=limitation.statement,
                severity=parse_enum(LimitationSeverity, limitation.severity),
                concerns=limitation.concerns,
                extraction_confidence=limitation.confidence,
            )
            for limitation in response.limitations
        )
        return out
