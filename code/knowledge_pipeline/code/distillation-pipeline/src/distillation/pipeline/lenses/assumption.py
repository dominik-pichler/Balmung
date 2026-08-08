"""Assumption lens — surfaces implicit assumptions."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...domain.distillate import AssumptionMention
from .base import Lens


class _AssumptionItem(BaseModel):
    name: str
    statement: str = ""
    confidence: float = 1.0


class AssumptionResponse(BaseModel):
    assumptions: list[_AssumptionItem] = Field(default_factory=list)


class AssumptionLens(Lens[AssumptionResponse, AssumptionMention]):
    name = "assumption"

    @property
    def system_prompt(self) -> str:
        return (
            "You surface IMPLICIT assumptions made by the source — claims it "
            "takes for granted but does not argue for. For each, give a "
            "short name (3-7 words) and a one-sentence statement of the "
            "assumption."
        )

    @property
    def response_model(self) -> type[AssumptionResponse]:
        return AssumptionResponse

    def project(
        self, response: AssumptionResponse, chunk_ids: list[str]
    ) -> list[AssumptionMention]:
        return [
            AssumptionMention(
                name=a.name,
                statement=a.statement,
                extraction_confidence=a.confidence,
            )
            for a in response.assumptions
        ]
