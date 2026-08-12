"""Distillation lenses — LLM-powered per-dimension extractors.

Each concrete lens provides a ``system_prompt``, a Pydantic ``response_model``,
and a ``project`` method; the base :class:`Lens` owns chunk formatting, LLM
dispatch, and provenance stamping.

Six lenses, grouped by ontology level:
  * L1 domain: :class:`DomainLens`, :class:`AssumptionLens`
  * L2 epistemik: :class:`ClaimLens`, :class:`EvidenceLens`
  * L3 provenance: :class:`AuthorLens`, :class:`ProvenanceLens`
"""

from __future__ import annotations

from .assumption import AssumptionLens
from .author import AuthorLens
from .base import Lens
from .claim_lens import ClaimLens
from .domain_lens import DomainLens
from .evidence import EvidenceLens
from .provenance import ProvenanceLens

__all__ = [
    "AssumptionLens",
    "AuthorLens",
    "ClaimLens",
    "DomainLens",
    "EvidenceLens",
    "Lens",
    "ProvenanceLens",
]
