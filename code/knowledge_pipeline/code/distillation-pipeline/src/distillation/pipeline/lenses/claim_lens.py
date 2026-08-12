"""ClaimLens — extracts claims from documents.

Replaces the old ``ConclusionLens`` + ``hypothesis`` + ``confirmed`` model.
Claims are paper-scoped (CREATE), never MERGE'd across papers.

Each claim carries:
- ``text``: full claim statement
- ``claim_type``: capability|comparative|causal|limitation|existence
- ``polarity``: positive (supports) or negative (refutes)
- ``stated_confidence``: author's hedging (0.0–1.0)
- ``prior_implausibility``: base-rate of the claim being true (0.0–1.0)
- ``decay_immune``: true for formal proofs (immune to aging)
- ``extraction_confidence``: parser's confidence (from LLM logprobs or heuristic)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...domain.distillate import ClaimMention
from ...domain.ontology import ClaimType, Polarity
from .base import Lens


class _ClaimItem(BaseModel):
    """Raw extraction result for one claim."""

    name: str
    text: str = ""  # Full statement
    claim_type: str | None = None  # capability|comparative|...
    polarity: str | None = None  # positive|negative
    stated_confidence: float | None = None  # Author's hedging 0.0–1.0
    prior_implausibility: float | None = None  # Base-rate 0.0–1.0
    decay_immune: bool = False  # Formal proofs are decay_immune
    about: list[str] = Field(default_factory=list)  # Domain entities the claim is about
    assumes: list[str] = Field(default_factory=list)  # Assumptions the claim rests on
    extraction_confidence: float = 0.6  # Default parser confidence


class ClaimResponse(BaseModel):
    claims: list[_ClaimItem] = Field(default_factory=list)


class ClaimLens(
    Lens[ClaimResponse, ClaimMention]
):
    """Extracts claims with full epistemik metadata."""

    name = "claim"

    @property
    def system_prompt(self) -> str:
        return (
            "You extract CLAIMS made by the source — the substantive, testable "
            "assertions the authors argue for (a result, a comparison, a causal "
            "effect). Extract each distinct claim ONCE. Do NOT manufacture a "
            "separate claim for every sentence: a stand-alone capability, "
            "limitation, or assumption is captured by other extractors, so only "
            "emit it as a claim when the authors actually assert it as a finding. "
            "Aim for the paper's handful of headline claims, not a claim per line. "
            "For each claim, provide:\n\n"
            "1. ``name``: short label (3–7 words)\n"
            "2. ``text``: full claim statement\n"
            "3. ``claim_type``: one of {capability, comparative, causal, "
            "limitation, existence}\n"
            "4. ``polarity``: one of {positive, negative}\n"
            "   (positive = the claim supports something, "
            "negative = the claim identifies a limitation or failure)\n"
            "5. ``stated_confidence``: the author's own hedging, as a float "
            "0.0–1.0. Examples: 'may work' → 0.5, 'we demonstrate' → 0.9, "
            "'definitely works' → 1.0. If not clear, use 0.6.\n"
            "6. ``prior_implausibility``: a float 0.0–1.0 representing how "
            "plausible the claim is before reading this paper. "
            "'X is 2% faster than Y' → 0.1 (very plausible). "
            "'X solves AGI' → 0.8 (implausible a priori). "
            "'X is a novel architecture' → 0.3. "
            "If unclear, use 0.5.\n"
            "7. ``decay_immune``: true ONLY for formal proofs (mathematical "
            "theorems), false for everything else including empirical results.\n"
            "8. ``extraction_confidence``: YOUR confidence in the extraction, "
            "as a float 0.0–1.0. Use 0.8 for clear statements, 0.5 for "
            "implications. NEVER use 1.0 unless the text is verbatim.\n"
            "9. ``about``: the list of Domain entities this claim is about — "
            "the technologies, problems, capabilities, metrics, or datasets it "
            "concerns. Use the SAME short names those entities are given "
            "elsewhere in the text (e.g. 'SparseFormer', 'long-context "
            "reasoning'), so the claim links to them. Return [] if none apply.\n"
            "10. ``assumes``: the list of specific assumptions THIS claim rests "
            "on, by their short name/statement as stated in the text. Only list "
            "assumptions this particular claim actually depends on — do not list "
            "every assumption in the paper. Return [] if none apply."
        )

    @property
    def response_model(self) -> type[ClaimResponse]:
        return ClaimResponse

    def project(
        self, response: ClaimResponse, chunk_ids: list[str]
    ) -> list[ClaimMention]:
        return [
            ClaimMention(
                name=c.name,
                text=c.text or c.name,
                claim_type=(
                    ClaimType(c.claim_type)
                    if c.claim_type and c.claim_type in [ct.value for ct in ClaimType]
                    else None
                ),
                polarity=(
                    Polarity(c.polarity)
                    if c.polarity and c.polarity in [p.value for p in Polarity]
                    else None
                ),
                stated_confidence=c.stated_confidence,
                prior_implausibility=c.prior_implausibility,
                decay_immune=c.decay_immune,
                about=c.about,
                assumes=c.assumes,
                extraction_confidence=c.extraction_confidence,
            )
            for c in response.claims
        ]
