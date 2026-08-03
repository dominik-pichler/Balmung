"""Ollama embedder using the OpenAI-compatible /v1/embeddings endpoint."""

from __future__ import annotations

from collections.abc import Sequence

from ...ports.embedder import Embedder


class OllamaEmbedder(Embedder):
    """Embedder backed by a locally-running Ollama instance.

    Recommended models: ``nomic-embed-text`` (768-dim),
    ``mxbai-embed-large`` (1024-dim).
    """

    def __init__(
        self,
        *,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434/v1",
        dimension: int = 768,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai' package to use OllamaEmbedder"
            ) from exc

        self._client = AsyncOpenAI(base_url=base_url, api_key="ollama")
        self._model = model
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=list(texts),
            )
            return [item.embedding for item in response.data]
        except Exception as exc:
            from ...ports.llm_client import LLMError
            raise LLMError(f"Ollama embedding call failed: {exc}") from exc
