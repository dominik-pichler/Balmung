"""Methodology lens — identifies methods used."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...domain.distillate import MethodologyMention
from .base import Lens


class _MethodItem(BaseModel):
    name: str
    description: str = ""
    confidence: float = 1.0


class MethodologyResponse(BaseModel):
    methodologies: list[_MethodItem] = Field(default_factory=list)


class MethodologyLens(Lens[MethodologyResponse, MethodologyMention]):
    name = "methodology"

    @property
    def system_prompt(self) -> str:
        return (
            "You extract the METHODOLOGIES used in the source — research "
            "methods, experimental designs, analytical techniques, or "
            "frameworks the source applies. Provide a short name and a "
            "one-sentence description."
        )

    @property
    def response_model(self) -> type[MethodologyResponse]:
        return MethodologyResponse

    def project(
        self, response: MethodologyResponse, chunk_ids: list[str]
    ) -> list[MethodologyMention]:
        return [
            MethodologyMention(
                name=m.name, description=m.description, confidence=m.confidence
            )
            for m in response.methodologies
        ]
