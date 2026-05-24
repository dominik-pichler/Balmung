"""Port: LLM with structured (typed) output.

The lenses don't want a free-text completion API; they want "give me an
instance of this pydantic model." This port enforces that shape so the
lenses stay declarative.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


class LLMClient(ABC):
    """Returns a typed pydantic model from a prompt.

    Concrete adapters are responsible for:
      * Constructing the structured-output request (e.g. tool use, JSON mode).
      * Validating the response against ``response_model``.
      * Retrying on transient failures (the adapter, not the lens, owns this).
    """

    @abstractmethod
    async def structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[TModel],
    ) -> TModel:
        """Issue a structured-output completion.

        Raises:
            LLMError: when the model returns invalid output after retries.
        """
        raise NotImplementedError


class LLMError(RuntimeError):
    """Raised when an LLM call cannot be completed within retry budget."""
