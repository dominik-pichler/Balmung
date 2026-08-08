"""OMLX embedder using the OpenAI-compatible /v1/embeddings endpoint."""

from __future__ import annotations

from collections.abc import Sequence

from ...ports.embedder import Embedder


class OmlxEmbedder(Embedder):
    """Embedder backed by a locally-running OMLX instance.

    Recommended models: ``Qwen3.6-35B-A3B-4bit`` (supports up to 131k context
    window) for embedding via the OMLX API.
    """

    def __init__(
        self,
        *,
        model: str = "Qwen3.6-35B-A3B-4bit",
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "",
        dimension: int = 768,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "Install the 'openai' package to use OmlxEmbedder"
            ) from exc

        # Use a placeholder key if none is provided (local-only OMLX)
        openai_api_key = api_key or "omlx"
        self._client = AsyncOpenAI(base_url=base_url, api_key=openai_api_key)
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
            raise LLMError(f"OMLX embedding call failed: {exc}") from exc
