"""Conclusion lens — extracts conclusions derived in the source."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...domain.distillate import ConclusionMention
from .base import Lens


class _ConclusionItem(BaseModel):
    name: str
    statement: str = ""
    supports_theories: list[str] = Field(default_factory=list)
    confidence: float = 1.0


class ConclusionResponse(BaseModel):
    conclusions: list[_ConclusionItem] = Field(default_factory=list)


class ConclusionLens(Lens[ConclusionResponse, ConclusionMention]):
    name = "conclusion"

    @property
    def system_prompt(self) -> str:
        return (
            "You extract CONCLUSIONS the source derives — the takeaways it "
            "argues for. For each conclusion, give a short label, a single "
            "sentence stating the conclusion, and (optionally) the names of "
            "any theories this conclusion supports."
        )

    @property
    def response_model(self) -> type[ConclusionResponse]:
        return ConclusionResponse

    def project(
        self, response: ConclusionResponse, chunk_ids: list[str]
    ) -> list[ConclusionMention]:
        return [
            ConclusionMention(
                name=c.name,
                statement=c.statement,
                supports_theories=c.supports_theories,
                confidence=c.confidence,
            )
            for c in response.conclusions
        ]
