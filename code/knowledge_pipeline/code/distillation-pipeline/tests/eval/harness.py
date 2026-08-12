"""Lens evaluation harness — gold standard + scoring.

This is a **model/prompt evaluation** suite, not a deterministic unit test. It
runs every lens against a *real* LLM over one fixture paper
(``examples/full_ontology_paper.txt``) whose expected extractions are known,
then scores each lens on two axes:

1. **Entity recall** — did the lens surface the entities the paper clearly
   states? (fuzzy, canonicalized substring / token-subset match)
2. **Reference-field coverage** — did the lens populate the fields that drive
   the ontology's relationship edges (``about``, ``addresses``, ``concerns``,
   ``holds_under``, experiment ``technologies``/``datasets``/``metrics``,
   evidence ``claim``, author ``affiliation``)? These are the fields whose
   absence leaves domain/claim nodes unconnected.

Use it to compare models or prompt revisions: change ``DISTILL_LLM_PROVIDER`` /
``DISTILL_LLM_MODEL`` (or edit a lens prompt) and re-run
``pytest tests/eval -m eval -s``. A JSON scorecard is written per model so runs
are comparable over time.

The fixture paper is written so that *every* entity type and *every* reference
field has an unambiguous ground truth — a perfect extractor scores 1.0 across
the board.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from distillation.domain.distillate import (
    AssumptionMention,
    AuthorMention,
    CapabilityMention,
    ClaimMention,
    DatasetMention,
    EvidenceMention,
    ExperimentMention,
    LimitationMention,
    MetricMention,
    ProblemMention,
    ScopeMention,
)
from distillation.domain.ids import canonicalize
from distillation.domain.ontology import EvidenceType

# The fixture paper (repo-root/examples/…). parents[2] == distillation-pipeline/.
FIXTURE_PAPER = (
    Path(__file__).resolve().parents[2] / "examples" / "full_ontology_paper.txt"
)


# ======================================================================
# Gold standard — what the fixture paper unambiguously contains
# ======================================================================
#
# Each value is a list of *key phrases*; a gold entity counts as "found" if any
# extracted item of the right type fuzzily contains it (see ``matches``).

GOLD: dict[str, dict[str, list[str]]] = {
    "domain": {
        "technologies": ["sparseformer", "flashretrieval"],
        "problems": ["long-context reasoning", "retrieval latency"],
        "capabilities": ["long-context accuracy", "low-latency retrieval"],
        "metrics": ["exact match", "p95 latency"],
        "datasets": ["longbench", "naturalquestions"],
        "limitations": ["quadratic memory", "index staleness"],
    },
    "assumption": {
        "assumptions": ["context window", "static"],
    },
    "claim": {
        "claims": ["outperforms", "reduces retrieval latency"],
    },
    "evidence": {
        "evidence": ["longbench", "latency", "cold-start"],
        "experiments": ["longbench", "latency benchmark"],
        "scopes": ["long-document"],
    },
    "author": {
        "authors": ["alice chen", "bob martinez", "carol zhang"],
    },
    "provenance": {
        "papers": ["attention", "dense passage retrieval"],
        "organizations": ["deepmind", "mit"],
        "venues": ["neurips"],
        "funding_sources": ["nsf", "darpa"],
    },
}

# Minimum entity recall each lens must hit (a real regression gate). Tuned to be
# achievable by a competent model; raise as extraction improves.
MIN_RECALL: dict[str, float] = {
    "domain": 0.6,
    "assumption": 0.4,
    "claim": 0.5,
    "evidence": 0.4,
    "author": 0.6,
    "provenance": 0.5,
}

# Reference-field coverage gate. These fields drive the relationship edges.
# The current lens PROMPTS do not request most of them, so coverage is ~0 today
# — hence the default gate is report-only (0.0). Set DISTILL_EVAL_STRICT=1 to
# turn coverage into a hard gate (0.5) once the prompts ask for these fields.
MIN_REF_COVERAGE: float = 0.5 if os.getenv("DISTILL_EVAL_STRICT") else 0.0

# A competent claim extractor should not explode assumptions/limitations into
# claims. The fixture has ~2 primary claims; flag gross over-extraction.
MAX_CLAIMS = 12


# ======================================================================
# Entity-type filters (Domain/Evidence lenses emit mixed lists)
# ======================================================================

_TYPE_FILTERS = {
    "technologies": lambda i: type(i).__name__ == "TechnologyMention",
    "problems": lambda i: isinstance(i, ProblemMention),
    "capabilities": lambda i: isinstance(i, CapabilityMention),
    "metrics": lambda i: isinstance(i, MetricMention),
    "datasets": lambda i: isinstance(i, DatasetMention),
    "limitations": lambda i: isinstance(i, LimitationMention),
    "assumptions": lambda i: isinstance(i, AssumptionMention),
    "claims": lambda i: isinstance(i, ClaimMention),
    "evidence": lambda i: isinstance(i, EvidenceMention),
    "experiments": lambda i: isinstance(i, ExperimentMention),
    "scopes": lambda i: isinstance(i, ScopeMention),
    "authors": lambda i: isinstance(i, AuthorMention),
    # provenance sub-types are matched by attribute presence to avoid importing
    # the four provenance mention classes here:
    "papers": lambda i: type(i).__name__ == "PaperMention",
    "organizations": lambda i: type(i).__name__ == "OrganizationMention",
    "venues": lambda i: type(i).__name__ == "VenueMention",
    "funding_sources": lambda i: type(i).__name__ == "FundingSourceMention",
}


def items_of(items: list, group: str) -> list:
    """Filter a lens's mixed output list down to one entity group."""
    pred = _TYPE_FILTERS[group]
    return [i for i in items if pred(i)]


# ======================================================================
# Matching + scoring
# ======================================================================


def _haystack(item: object) -> str:
    """All searchable text on an extracted item, canonicalized."""
    parts: list[str] = []
    for attr in ("name", "text", "statement", "description", "title"):
        v = getattr(item, attr, None)
        if isinstance(v, str) and v:
            parts.append(v)
    aliases = getattr(item, "aliases", None)
    if isinstance(aliases, list):
        parts.extend(str(a) for a in aliases)
    return canonicalize(" ".join(parts))


def matches(term: str, items: list) -> bool:
    """Fuzzy: gold ``term`` matches if any item contains it (substring) or all
    of its tokens appear in the item's searchable text."""
    t = canonicalize(term)
    toks = t.split()
    for it in items:
        hay = _haystack(it)
        if t and t in hay:
            return True
        if toks and all(tok in hay for tok in toks):
            return True
    return False


def recall(expected: list[str], items: list) -> tuple[float, list[str]]:
    """Fraction of gold phrases found, plus the list of misses."""
    if not expected:
        return 1.0, []
    missed = [e for e in expected if not matches(e, items)]
    return (len(expected) - len(missed)) / len(expected), missed


def field_coverage(items: list, field_name: str) -> float:
    """Fraction of items carrying a non-empty value for ``field_name``.

    Handles scalars (str/obj), lists, and ``None``/empty as "not covered".
    """
    if not items:
        return 0.0
    covered = 0
    for it in items:
        v = getattr(it, field_name, None)
        if v not in (None, "", [], (), {}):
            covered += 1
    return covered / len(items)


@dataclass
class LensScore:
    """Scorecard for a single lens run."""

    lens: str
    error: str | None = None
    recall: float = 0.0
    recall_by_group: dict[str, float] = field(default_factory=dict)
    missed: dict[str, list[str]] = field(default_factory=dict)
    ref_coverage: dict[str, float] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "lens": self.lens,
            "error": self.error,
            "recall": round(self.recall, 3),
            "recall_by_group": {k: round(v, 3) for k, v in self.recall_by_group.items()},
            "missed": self.missed,
            "ref_coverage": {k: round(v, 3) for k, v in self.ref_coverage.items()},
            "counts": self.counts,
        }


def score_lens(lens_name: str, items: list, error: str | None) -> LensScore:
    """Score one lens's output against the gold standard."""
    s = LensScore(lens=lens_name, error=error)
    if error:
        return s

    groups = GOLD[lens_name]
    per_group: dict[str, float] = {}
    total_found = 0
    total_expected = 0
    for group, expected in groups.items():
        group_items = items_of(items, group)
        r, missed = recall(expected, group_items)
        per_group[group] = r
        s.missed[group] = missed
        s.counts[group] = len(group_items)
        total_found += len(expected) - len(missed)
        total_expected += len(expected)

    s.recall_by_group = per_group
    s.recall = total_found / total_expected if total_expected else 1.0

    # Reference-field coverage — the edge-driving fields, per lens.
    if lens_name == "domain":
        s.ref_coverage["capability.addresses"] = field_coverage(
            items_of(items, "capabilities"), "addresses"
        )
        s.ref_coverage["limitation.concerns"] = field_coverage(
            items_of(items, "limitations"), "concerns"
        )
    elif lens_name == "assumption":
        s.ref_coverage["assumption.holds_under"] = field_coverage(items, "holds_under")
    elif lens_name == "claim":
        s.ref_coverage["claim.about"] = field_coverage(items, "about")
    elif lens_name == "evidence":
        exps = items_of(items, "experiments")
        evs = items_of(items, "evidence")
        s.ref_coverage["experiment.technologies"] = field_coverage(exps, "technologies")
        s.ref_coverage["experiment.datasets"] = field_coverage(exps, "datasets")
        s.ref_coverage["experiment.metrics"] = field_coverage(exps, "metrics")
        s.ref_coverage["evidence.claim"] = field_coverage(evs, "claim")
        s.ref_coverage["evidence.has_refuting"] = float(
            any(e.type == EvidenceType.refuting for e in evs)
        )
    elif lens_name == "author":
        s.ref_coverage["author.affiliation"] = field_coverage(items, "affiliation")

    return s
