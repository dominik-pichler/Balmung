"""Anthropic ``LLMClient`` adapter using structured tool output.

The pattern: declare a single tool whose ``input_schema`` is the JSON schema
of the requested pydantic model and force the model to call it. The tool
input is then validated against the pydantic model.

Network retry policy lives here (tenacity), keeping the lens layer naive.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ...ports.llm_client import LLMClient, LLMError

TModel = TypeVar("TModel", bound=BaseModel)


class AnthropicLLMClient(LLMClient):
    """Real LLM adapter against Anthropic's Messages API.

    NOTE: This module imports the ``anthropic`` SDK lazily inside ``__init__``
    so the rest of the codebase (and the test suite) does not require the
    package to be installed.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_tokens: int = 2048,
        max_attempts: int = 3,
    ) -> None:
        if not api_key:
            raise ValueError("Anthropic API key is required")

        # TODO: replace lazy import with module-level import once the
        # dependency is unconditionally installed in your environment.
        try:
            import anthropic  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - dep guard
            raise ImportError(
                "Install the 'anthropic' package to use AnthropicLLMClient"
            ) from exc

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
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
        schema = response_model.model_json_schema()
        tool = {
            "name": "emit_response",
            "description": "Emit the structured response.",
            "input_schema": schema,
        }

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((LLMError, ValidationError)),
            reraise=True,
        ):
            with attempt:
                response = await self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system,
                    tools=[tool],
                    tool_choice={"type": "tool", "name": "emit_response"},
                    messages=[{"role": "user", "content": user}],
                )
                payload = _extract_tool_input(response)
                if payload is None:
                    raise LLMError("Model did not emit the expected tool call")
                return response_model.model_validate(payload)

        raise LLMError("Exhausted retries without a valid response")


def _extract_tool_input(response: Any) -> dict[str, Any] | None:
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", "") == "emit_response":
            return dict(block.input)
    return None
