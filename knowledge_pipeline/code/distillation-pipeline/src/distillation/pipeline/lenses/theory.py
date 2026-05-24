"""Theory lens — identifies theories the source builds or relies on."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...domain.distillate import TheoryMention
from .base import Lens


class _TheoryItem(BaseModel):
    name: str
    statement: str = ""
    confidence: float = 1.0


class TheoryResponse(BaseModel):
    theories: list[_TheoryItem] = Field(default_factory=list)


class TheoryLens(Lens[TheoryResponse, TheoryMention]):
    name = "theory"

    @property
    def system_prompt(self) -> str:
        return (
            "You extract THEORIES the source builds, develops, or extends. "
            "Each theory must have a short canonical name and a one- or "
            "two-sentence statement. Do not include conclusions or methods."
        )

    @property
    def response_model(self) -> type[TheoryResponse]:
        return TheoryResponse

    def project(
        self, response: TheoryResponse, chunk_ids: list[str]
    ) -> list[TheoryMention]:
        return [
            TheoryMention(
                name=t.name, statement=t.statement, confidence=t.confidence
            )
            for t in response.theories
        ]
