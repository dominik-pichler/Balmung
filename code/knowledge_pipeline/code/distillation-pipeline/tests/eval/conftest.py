"""Fixtures for the lens evaluation suite.

The heavy work — one real LLM call per lens — happens **once** per session in
``lens_outputs`` (a plain sync fixture that drives the async lenses via
``asyncio.run``), so the per-lens tests are cheap sync assertions over cached
results. The whole suite auto-skips unless a real LLM provider is configured,
so it never runs (or costs money) in the default fake-backed CI.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from distillation.config import Settings, get_settings
from distillation.domain.distillate import LensOutput
from distillation.domain.document import Chunk
from distillation.pipeline.lenses import (
    AssumptionLens,
    AuthorLens,
    ClaimLens,
    DomainLens,
    EvidenceLens,
    ProvenanceLens,
)

from .harness import FIXTURE_PAPER

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()


@pytest.fixture(scope="session")
def lens_outputs(settings: Settings) -> dict[str, LensOutput]:
    """Run every lens once over the fixture paper against the real LLM.

    Skips the entire eval suite when no real provider is configured.
    Returns ``{lens_name: LensOutput}``; a lens that raises is captured as a
    ``LensOutput`` with ``error`` set, so its own test fails cleanly without
    taking down the others.
    """
    if settings.llm_provider == "fake":
        pytest.skip(
            "Lens eval needs a real LLM. Re-run with e.g. "
            "DISTILL_LLM_PROVIDER=omlx pytest tests/eval -m eval -s"
        )

    # Import here so a broken CLI import can't collect-error the whole suite.
    from distillation.cli import _build_llm

    llm = _build_llm(settings)
    text = FIXTURE_PAPER.read_text(encoding="utf-8")
    # One whole-document chunk: gives every lens full context — the fair,
    # reproducible baseline for measuring extraction capability.
    chunks = [
        Chunk(
            chunk_id="eval-0",
            document_id="eval-paper",
            index=0,
            text=text,
            start_char=0,
            end_char=len(text),
        )
    ]

    lenses = {
        "domain": DomainLens(llm),
        "assumption": AssumptionLens(llm),
        "claim": ClaimLens(llm),
        "evidence": EvidenceLens(llm),
        "author": AuthorLens(llm),
        "provenance": ProvenanceLens(llm),
    }

    async def run() -> dict[str, LensOutput]:
        out: dict[str, LensOutput] = {}
        for name, lens in lenses.items():
            try:
                out[name] = await lens.apply(chunks)
            except Exception as exc:  # noqa: BLE001 - eval must not abort mid-suite
                out[name] = LensOutput(lens_name=name, items=[], error=repr(exc))
        return out

    return asyncio.run(run())


@pytest.fixture(scope="session")
def scorecard(settings: Settings):
    """Accumulates per-lens scores and writes a comparable JSON report at teardown."""
    card: dict = {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "lenses": {},
    }
    yield card

    # --- teardown: pretty-print a summary + persist a JSON scorecard ---
    if not card["lenses"]:
        return
    print("\n\n" + "=" * 68)
    print(f"LENS EVAL — {card['provider']} / {card['model']}")
    print("=" * 68)
    print(f"{'lens':<12}{'recall':>8}   reference-field coverage")
    print("-" * 68)
    for name, sc in card["lenses"].items():
        if sc.get("error"):
            print(f"{name:<12}{'ERR':>8}   {sc['error'][:44]}")
            continue
        refs = sc.get("ref_coverage", {})
        ref_str = ", ".join(f"{k.split('.')[-1]}={v:.2f}" for k, v in refs.items())
        print(f"{name:<12}{sc['recall']:>8.2f}   {ref_str}")
    print("=" * 68)

    REPORTS_DIR.mkdir(exist_ok=True)
    safe_model = "".join(c if c.isalnum() else "-" for c in card["model"])
    out_path = REPORTS_DIR / f"{card['provider']}__{safe_model}.json"
    out_path.write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(f"scorecard written: {out_path}")
