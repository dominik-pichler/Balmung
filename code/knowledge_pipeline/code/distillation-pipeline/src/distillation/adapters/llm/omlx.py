"""OMLX ``LLMClient`` adapter using instructor for structured output.

Uses the instructor library to get reliable structured (pydantic) output from
a locally-running OMLX instance. The OpenAI-compatible API exposed by OMLX
is used under the hood.

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


class OmlxLLMClient(LLMClient):
    """LLM adapter for local OMLX instances via instructor.

    NOTE: This module imports ``instructor`` and ``openai`` lazily so the rest
    of the codebase does not require these packages to be installed.
    """

    def __init__(
        self,
        *,
        model: str = "Qwen3.6-35B-A3B-4bit",
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "",
        max_tokens: int = 32000,
        max_attempts: int = 3,
    ) -> None:
        try:
            import instructor
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "Install 'instructor' and 'openai' packages to use OmlxLLMClient: "
                "pip install instructor openai"
            ) from exc

        # OMLX exposes an OpenAI-compatible API at /v1
        # Use a placeholder key if none is provided (local-only OMLX)
        openai_api_key = api_key or "omlx"
        openai_client = AsyncOpenAI(
            base_url=base_url,
            api_key=openai_api_key,
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
                    raise LLMError(f"OMLX call failed: {exc}") from exc

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
            raise LLMError(f"OMLX chat call failed: {exc}") from exc
