"""Distillation lenses — LLM-powered per-dimension extractors.

Each concrete lens provides a ``system_prompt``, a Pydantic ``response_model``,
and a ``project`` method; the base :class:`Lens` owns chunk formatting, LLM
dispatch, and provenance stamping.
"""

from __future__ import annotations

from .assumption import AssumptionLens
from .author import AuthorLens
from .base import Lens
from .claim_lens import ClaimLens

__all__ = [
    "AssumptionLens",
    "AuthorLens",
    "ClaimLens",
    "Lens",
]
