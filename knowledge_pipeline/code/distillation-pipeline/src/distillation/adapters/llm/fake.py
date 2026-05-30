"""Fake ``LLMClient`` for tests and offline local runs.

Behavior is rule-based: it inspects the ``response_model`` class name and
synthesizes a minimally valid instance using simple heuristics on the user
prompt. This is intentionally crude — the goal is "the pipeline runs
end-to-end without network" not "the extraction is good."

For tests, callers can register canned responses via ``set_response`` keyed
by ``response_model.__name__``.
"""

from __future__ import annotations

import re
from typing import Any, TypeVar

from pydantic import BaseModel

from ...ports.llm_client import LLMClient

TModel = TypeVar("TModel", bound=BaseModel)


class FakeLLMClient(LLMClient):
    """Deterministic, offline LLM stand-in."""

    def __init__(self) -> None:
        self._canned: dict[str, BaseModel] = {}
        self.calls: list[tuple[str, str, type[BaseModel]]] = []

    def set_response(self, response_model: type[BaseModel], value: BaseModel) -> None:
        """Pre-register a canned response for a given response model."""
        self._canned[response_model.__name__] = value

    async def structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[TModel],
    ) -> TModel:
        self.calls.append((system, user, response_model))
        canned = self._canned.get(response_model.__name__)
        if canned is not None:
            # Validate the canned value matches the requested model.
            return response_model.model_validate(canned.model_dump())
        return _synthesize(response_model, user)

    async def chat(self, *, system: str, user: str) -> str:
        return f"[FakeLLMClient] system={system!r:.40} user={user!r:.40}"


# --- heuristic synthesis -------------------------------------------------

_CAPITALIZED_PHRASE = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\b")


def _synthesize(model: type[TModel], user: str) -> TModel:
    """Build a minimal valid instance of ``model``.

    We look at the model's field schema and provide:
      * lists of items → up to 3 ``ExtractedEntity``-shaped dicts with
        capitalized phrases from the prompt as names.
      * strings → empty.
      * floats → 0.5.
      * other → field default.
    """
    candidates = list(dict.fromkeys(_CAPITALIZED_PHRASE.findall(user)))[:3]
    if not candidates:
        candidates = ["Unknown"]

    payload: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        annotation = field.annotation
        ann_str = str(annotation)

        if "list" in ann_str.lower():
            # Build entity-shaped dicts. The lens response models all have a
            # single list field whose item type has a ``name`` attribute, so
            # this minimal shape validates.
            payload[name] = [{"name": c} for c in candidates]
        elif annotation is str:
            payload[name] = ""
        elif annotation is float:
            payload[name] = 0.5
        elif annotation is int:
            payload[name] = 0
        else:
            payload[name] = field.default if field.default is not None else None

    return model.model_validate(payload)
