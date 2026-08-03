"""Topic lens — mines what the source is about."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...domain.distillate import TopicMention
from .base import Lens


class _TopicItem(BaseModel):
    name: str
    theme: str | None = None
    confidence: float = 1.0


class TopicResponse(BaseModel):
    topics: list[_TopicItem] = Field(default_factory=list)


class TopicLens(Lens[TopicResponse, TopicMention]):
    name = "topic"

    @property
    def system_prompt(self) -> str:
        return (
            "You extract the topics discussed in a source document. "
            "Return concise topic labels (1-4 words) and, where you can, a "
            "broader theme they belong to. Avoid duplicates."
        )

    @property
    def response_model(self) -> type[TopicResponse]:
        return TopicResponse

    def project(
        self, response: TopicResponse, chunk_ids: list[str]
    ) -> list[TopicMention]:
        return [
            TopicMention(name=t.name, theme=t.theme, confidence=t.confidence)
            for t in response.topics
        ]
