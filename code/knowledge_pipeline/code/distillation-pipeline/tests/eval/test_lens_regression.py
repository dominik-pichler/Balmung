"""Per-lens regression gates against a real LLM.

Run:  DISTILL_LLM_PROVIDER=omlx pytest tests/eval -m eval -s
Strict (also gate on edge-driving reference fields):
      DISTILL_EVAL_STRICT=1 DISTILL_LLM_PROVIDER=omlx pytest tests/eval -m eval -s

Each test:
  * asserts entity **recall** >= the lens's ``MIN_RECALL`` threshold, and
  * records **reference-field coverage** (the fields that drive relationship
    edges) into the shared scorecard, asserting it only when strict mode is on.

Skipped entirely under the default fake LLM (see ``lens_outputs``).
"""

from __future__ import annotations

import pytest

from distillation.domain.distillate import LensOutput

from .harness import MAX_CLAIMS, MIN_RECALL, MIN_REF_COVERAGE, score_lens

pytestmark = pytest.mark.eval


def _record_and_gate(scorecard: dict, lens: str, out: LensOutput) -> None:
    """Score one lens, stash it in the scorecard, and apply the gates."""
    sc = score_lens(lens, out.items, out.error)
    scorecard["lenses"][lens] = sc.as_dict()

    assert out.error is None, f"{lens} lens raised against the real LLM: {out.error}"

    # Entity recall — the hard regression gate.
    assert sc.recall >= MIN_RECALL[lens], (
        f"{lens}: recall {sc.recall:.2f} < {MIN_RECALL[lens]:.2f}. "
        f"misses={ {g: m for g, m in sc.missed.items() if m} }"
    )

    # Reference-field coverage — report-only by default; hard gate under
    # DISTILL_EVAL_STRICT=1 (raise these once the prompts request the fields).
    for field_name, cov in sc.ref_coverage.items():
        assert cov >= MIN_REF_COVERAGE, (
            f"{lens}: reference field '{field_name}' coverage {cov:.2f} "
            f"< {MIN_REF_COVERAGE:.2f} (strict mode)"
        )


def test_domain_lens(lens_outputs: dict[str, LensOutput], scorecard: dict) -> None:
    _record_and_gate(scorecard, "domain", lens_outputs["domain"])


def test_assumption_lens(lens_outputs: dict[str, LensOutput], scorecard: dict) -> None:
    _record_and_gate(scorecard, "assumption", lens_outputs["assumption"])


def test_claim_lens(lens_outputs: dict[str, LensOutput], scorecard: dict) -> None:
    out = lens_outputs["claim"]
    _record_and_gate(scorecard, "claim", out)
    # Over-extraction guard: claims should not swallow every capability/limitation.
    n_claims = len(out.items)
    assert n_claims <= MAX_CLAIMS, (
        f"claim lens over-extracted: {n_claims} claims (> {MAX_CLAIMS}). "
        "The prompt likely invites capabilities/limitations to be re-labeled as claims."
    )


def test_evidence_lens(lens_outputs: dict[str, LensOutput], scorecard: dict) -> None:
    _record_and_gate(scorecard, "evidence", lens_outputs["evidence"])


def test_author_lens(lens_outputs: dict[str, LensOutput], scorecard: dict) -> None:
    _record_and_gate(scorecard, "author", lens_outputs["author"])


def test_provenance_lens(lens_outputs: dict[str, LensOutput], scorecard: dict) -> None:
    _record_and_gate(scorecard, "provenance", lens_outputs["provenance"])
