"""Author lens — extracts authors, affiliations, and interests."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...domain.distillate import AffiliationMention, AuthorMention
from .base import Lens


class _AuthorItem(BaseModel):
    name: str
    affiliation: str | None = None
    interests: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class AuthorResponse(BaseModel):
    authors: list[_AuthorItem] = Field(default_factory=list)


class AuthorLens(Lens[AuthorResponse, AuthorMention]):
    name = "author"

    @property
    def system_prompt(self) -> str:
        return (
            "You extract the authors of a source document. For each author, "
            "include their affiliation (if stated) and any explicit "
            "research interests or focus areas. Return only people who are "
            "explicitly named as authors or contributors of the source."
        )

    @property
    def response_model(self) -> type[AuthorResponse]:
        return AuthorResponse

    def project(
        self, response: AuthorResponse, chunk_ids: list[str]
    ) -> list[AuthorMention]:
        out: list[AuthorMention] = []
        for a in response.authors:
            affiliation = (
                AffiliationMention(name=a.affiliation, extraction_confidence=1.0) if a.affiliation else None
            )
            out.append(
                AuthorMention(
                    name=a.name,
                    affiliation=affiliation,
                    interests=a.interests,
                    extraction_confidence=1.0,
                )
            )
        return out
