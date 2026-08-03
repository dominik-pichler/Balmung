"""Ollama ``LLMClient`` adapter using instructor for structured output.

Uses the instructor library to get reliable structured (pydantic) output from
local Ollama models. The OpenAI-compatible API exposed by Ollama is used under
the hood.

Requires: pip install instructor openai
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ...ports.llm_client import LLMClient, LLMError

TModel = TypeVar("TModel", bound=BaseModel)


class OllamaLLMClient(LLMClient):
    """LLM adapter for local Ollama models via instructor.

    NOTE: This module imports ``instructor`` and ``openai`` lazily so the rest
    of the codebase does not require these packages to be installed.
    """

    def __init__(
        self,
        *,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434/v1",
        max_tokens: int = 2048,
        max_attempts: int = 3,
    ) -> None:
        try:
            import instructor
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "Install 'instructor' and 'openai' packages to use OllamaLLMClient: "
                "pip install instructor openai"
            ) from exc

        # Ollama exposes an OpenAI-compatible API at /v1
        openai_client = AsyncOpenAI(
            base_url=base_url,
            api_key="ollama",  # Ollama doesn't require a real key
        )
        self._raw_client = openai_client
        self._client = instructor.from_openai(openai_client)
        self._model = model
        self._max_tokens = max_tokens
        self._max_attempts = max_attempts

    async def structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[TModel],
    ) -> TModel:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((LLMError, ValidationError)),
            reraise=True,
        ):
            with attempt:
                try:
                    result = await self._client.chat.completions.create(
                        model=self._model,
                        max_tokens=self._max_tokens,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        response_model=response_model,
                    )
                    return result
                except ValidationError:
                    raise
                except Exception as exc:
                    raise LLMError(f"Ollama call failed: {exc}") from exc

        raise LLMError("Exhausted retries without a valid response")

    async def chat(self, *, system: str, user: str) -> str:
        try:
            response = await self._raw_client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMError(f"Ollama chat call failed: {exc}") from exc
