"""ProvenanceLens — extracts Level 3 (provenance) context entities.

Covers the persistent identity/provenance metadata around a paper:
referenced papers, organizations, venues, and funding sources. Authors have
their own dedicated :class:`AuthorLens`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...domain.distillate import (
    ExtractedEntity,
    FundingSourceMention,
    OrganizationMention,
    PaperMention,
    VenueMention,
)
from ...domain.ontology import FundingType, OrganizationType, VenueTier
from .base import Lens, parse_enum


class _PaperItem(BaseModel):
    name: str  # DOI where available, else a short title label
    title: str | None = None
    year: int | None = None
    is_preprint: bool = False
    confidence: float = 0.6


class _OrgItem(BaseModel):
    name: str
    org_type: str | None = None
    confidence: float = 0.6


class _VenueItem(BaseModel):
    name: str
    tier: str | None = None
    peer_reviewed: bool | None = None
    confidence: float = 0.6


class _FundingItem(BaseModel):
    name: str
    funding_type: str | None = None
    confidence: float = 0.6


class ProvenanceResponse(BaseModel):
    papers: list[_PaperItem] = Field(default_factory=list)
    organizations: list[_OrgItem] = Field(default_factory=list)
    venues: list[_VenueItem] = Field(default_factory=list)
    funding_sources: list[_FundingItem] = Field(default_factory=list)


class ProvenanceLens(Lens[ProvenanceResponse, ExtractedEntity]):
    """Extracts referenced papers, organizations, venues, funding sources."""

    name = "provenance"

    @property
    def system_prompt(self) -> str:
        return (
            "You extract PROVENANCE metadata around a source document:\n"
            "- papers: other papers this one references/cites (name = DOI if "
            "given, else a short title label; include year, is_preprint)\n"
            "- organizations: institutions/companies mentioned as affiliations "
            "or actors (org_type: academic/industry/gov)\n"
            "- venues: the conference/journal (with tier and peer_reviewed)\n"
            "- funding_sources: grants or funders (funding_type: "
            "public/industry/mixed)\n\n"
            "Give each a short name. Omit fields you cannot determine. Provide a "
            "'confidence' in [0,1] (never 1.0 unless verbatim)."
        )

    @property
    def response_model(self) -> type[ProvenanceResponse]:
        return ProvenanceResponse

    def project(
        self, response: ProvenanceResponse, chunk_ids: list[str]
    ) -> list[ExtractedEntity]:
        out: list[ExtractedEntity] = []
        out.extend(
            PaperMention(
                name=p.name,
                title=p.title,
                year=p.year,
                is_preprint=p.is_preprint,
                extraction_confidence=p.confidence,
            )
            for p in response.papers
        )
        out.extend(
            OrganizationMention(
                name=o.name,
                org_type=parse_enum(OrganizationType, o.org_type),
                extraction_confidence=o.confidence,
            )
            for o in response.organizations
        )
        out.extend(
            VenueMention(
                name=v.name,
                tier=parse_enum(VenueTier, v.tier),
                peer_reviewed=v.peer_reviewed,
                extraction_confidence=v.confidence,
            )
            for v in response.venues
        )
        out.extend(
            FundingSourceMention(
                name=f.name,
                funding_type=parse_enum(FundingType, f.funding_type),
                extraction_confidence=f.confidence,
            )
            for f in response.funding_sources
        )
        return out
