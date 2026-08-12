# Balmung → Distillation Pipeline — Refactor Plan (Phase 0)

**Status:** Audit complete. **No source changed.** Awaiting review before Phase 1.

**Spec (source of truth):** `docs/PIPELINE.md` (copied from
`docs/knowledge_pipeline_structure_and_workflow.md`).

**Scope note.** The working tree already contains a near-complete
implementation of the target architecture under
`distillation-pipeline/src/distillation/`. The git history
("Add experimental refactoring and extension of the ontology") and the many
untracked files (`schema/`, `mapping/provenance_writer.py`, the OMLX adapters,
dead-letter records) confirm this is a *migration already in progress*, not a
greenfield build. This plan therefore audits the current package against the
spec and closes the remaining gaps. The legacy Balmung experiments in sibling
directories (`code/kants_knowledge_graph/`, `code/ER-NLP/`, `code/Q_and_A/`,
`code/reranking/`, `code/ismails_guide_to_fishing/`) are **out of scope** —
they are separate experiments, not inputs to be folded into this package.
Flag it if that assumption is wrong.

**Baseline quality gates (measured at audit time):**

| Gate | Result |
|------|--------|
| `pytest` | **21 passed** |
| `ruff check src tests` | **92 errors** (82 auto-fixable; mostly style) |
| `mypy src` | **4 errors** in 3 files |
| `distill ingest examples/sample_document.txt` (fake + in-memory) | **runs**: 10 nodes / 15 edges |

---

## 1. Module Map (current → target)

The layout already matches the spec almost exactly. Legend: **KEEP** = conforms,
**ALIGN** = keep but change behaviour to match spec, **FIX** = bug/quality fix,
**NEW** = create, **DEL** = delete.

### domain/  (target: pure data, no internal deps)
| Current file | Target | Action |
|---|---|---|
| `domain/distillate.py` | `domain/distillate.py` | KEEP; FIX `@computed_field`/`@property` mypy error; doc drift (mentions non-existent `domain_entities`) |
| `domain/document.py` | `domain/document.py` | KEEP (SourceDocument/Chunk/DocumentMetadata + document_id) |
| `domain/graph.py` | `domain/graph.py` | KEEP (re-exports GraphNode/Edge + enums from ontology) |
| `domain/ids.py` | `domain/ids.py` | ALIGN: add a single `node_id(tenant, type, canonical_name)` helper matching the spec formula (see Conflict C1) |
| `domain/ontology.py` | `domain/ontology.py` | KEEP (enums + GraphNode/GraphEdge). Note `COMPARED_TO` edge exists but is not in spec's edge table (harmless superset) |

### ports/  (target: interfaces, import only domain)
All seven ports exist and are clean ABCs. **KEEP all.**
`chunker`, `dead_letter_store`, `document_parser` (+ `ParserRegistry`),
`document_source`, `embedder`, `graph_repository`, `llm_client`.

### adapters/  (import ports + domain)
| Current | Action |
|---|---|
| `adapters/graph/in_memory.py` | KEEP (upsert-by-id, prop merge — idempotent) |
| `adapters/graph/neo4j.py` | FIX: `legacy_upsert_nodes/edges` are broken (missing `query` arg — mypy errors) → **DEL** legacy methods. ALIGN: L2 CREATE idempotency (Conflict C3) |
| `adapters/llm/fake.py` | KEEP (deterministic `.structured()` + `.chat()`) |
| `adapters/llm/anthropic.py` | KEEP (tool-use structured output, tenacity retry). Consider model-id default review |
| `adapters/llm/omlx.py` | KEEP (instructor / OpenAI-compatible) |
| `adapters/parsers/plaintext.py`, `markdown.py`, `pdf.py` | KEEP (pdf lazy-imported) |
| `adapters/chunkers/sliding_window.py` | KEEP (offset invariant tested) |
| `adapters/embedders/fake.py`, `omlx.py` | KEEP |
| `adapters/sources/local_file.py` | KEEP |
| `adapters/dead_letter/filesystem.py` | KEEP |

### pipeline/  (import ports + domain)
| Current | Action |
|---|---|
| `pipeline/context.py` | KEEP (DI container) |
| `pipeline/orchestrator.py` | KEEP (per-doc try/except per stage → dead-letter; continues) |
| `pipeline/stages/base.py` | KEEP (`Stage[TIn,TOut]` protocol) |
| `pipeline/stages/preprocess.py` | KEEP (parse + validate-nonempty + chunk) |
| `pipeline/stages/distill.py` | ALIGN docstring ("six lenses" → actual count); logic KEEP (asyncio.gather + semaphore + per-lens capture) |
| `pipeline/stages/synthesize.py` | ALIGN: only maps author/assumption/claim today → extend to whatever lens set we settle on (Open Question). DEL unused `_LENS_TO_TYPE` |
| `pipeline/stages/persist.py` | KEEP (already routes all 18 Distillate fields through the three writers) |
| `pipeline/lenses/base.py` | KEEP (`Lens[TResponse,TEntity]`, owns formatting + dispatch + provenance stamp) |
| `pipeline/lenses/author.py`, `assumption.py`, `claim_lens.py` | KEEP |
| `pipeline/lenses/__init__.py` | FIX: empty file |
| `pipeline/lenses/{new lenses}` | NEW — depends on Open Question resolution |

### mapping/  (import domain; writers)
| Current | Action |
|---|---|
| `mapping/domain_writer.py` | ALIGN node IDs to spec formula (Conflict C1). Otherwise KEEP |
| `mapping/epistemic_writer.py` | ALIGN node IDs (C1) incl. **paper-scoping** evidence/experiment/scope IDs (Conflict C2). GAP: emits no SUPPORTED_BY/REFUTED_BY/PRODUCED_BY/EVALUATED_ON/MEASURED_BY/ABOUT edges |
| `mapping/provenance_writer.py` | ALIGN node IDs (C1). GAP: emits no CITES/AFFILIATED_WITH/FUNDED_BY edges |

### top-level
| Current | Action |
|---|---|
| `cli.py` | KEEP (only place wiring concrete adapters — boundary holds). FIX lens-list typing (mypy). ALIGN lens registration to Open Question |
| `config.py` | KEEP (Settings, `DISTILL_` prefix, secrets unprefixed, fake+in_memory defaults) |
| `retrieval.py` | KEEP (embed nodes, cosine top-k, one-hop expansion) |
| `logging_setup.py` | KEEP |

### docs / schema / examples
| Current | Action |
|---|---|
| `docs/PIPELINE.md` | NEW (created this phase — copy of spec) |
| `docs/REFACTOR_PLAN.md` | NEW (this file) |
| `schema/neo4j_constraints.cypher`, `schema/ontology_nodes.csv` | KEEP (comments in German; leave as-is unless asked) |
| `examples/*.txt` | KEEP |

**Nothing is slated for deletion except:** the broken `legacy_upsert_*` methods
in `neo4j.py`, the unused `_LENS_TO_TYPE` dict in `synthesize.py`, and the empty
`lenses/__init__.py` (fill, don't delete).

---

## 2. Gap List (spec components missing or incomplete)

- **G1 — Lens coverage.** Spec's overview/diagram say **6 lenses**; only its
  table (and the code) define **3** (Author, Assumption, Claim). The
  `Distillate` carries **18** entity types. Today only `authors`,
  `assumptions`, `claims` are ever populated; the other 15 lists are always
  empty, so most of the (already-built) writer code is dead at runtime. → see
  Open Question §4.
- **G2 — Level-2 internal edges.** `EpistemicWriter` creates Evidence /
  Experiment / Scope **nodes** but no `SUPPORTED_BY`, `REFUTED_BY`,
  `PRODUCED_BY`, `EVALUATED_ON`, `MEASURED_BY`, `ABOUT` edges. Only
  `MAKES_CLAIM` and `ASSUMES` are produced.
- **G3 — Domain & provenance edges.** No `ADDRESSES`, `CONCERNS`,
  `HOLDS_UNDER` (L1) and no `CITES`, `AFFILIATED_WITH`, `FUNDED_BY` (L3).
  (`AUTHORED_BY` **is** produced.) All are gated on G1 (need the source
  entities first).
- **G4 — Tests.** Missing dedicated tests for: writer MERGE-vs-CREATE
  semantics, deterministic-ID formula, per-lens error capture at the
  *pipeline* level (lens-level is covered), dead-lettering (partly covered),
  one-hop retrieval. `retrieval.py`, `neo4j.py`, `synthesize.py` have no unit
  tests.
- **G5 — `distill export`/`chat`/`version`** exist but are untested.

---

## 3. Conflict List (current behaviour vs spec — spec wins, but flag first)

**C1 — Node-ID formula (HIGH — changes graph output).**
Spec: `node_id = sha256(tenant_id || node_type || canonical_name)[:16]`.
Reality: every writer uses ad-hoc forms with **no `tenant_id`** and
**inconsistent type keys**:
- Domain: `deterministic_id(canonicalize(name))` — name only.
- Provenance: `deterministic_id("author"|"org"|"paper"|..., canonical)` — string
  literal prefix, still no tenant.
- Claim: `deterministic_id(paper_id, text_slice)`.

Consequences: (a) a `Technology` and a `Problem` with the same canonical name
collide to the **same node_id** (cross-type collision); (b) IDs are not
tenant-partitioned despite multi-tenant `tenant_id` plumbing.
**Proposed resolution:** add `ids.node_id(tenant_id, node_type, canonical_name)`
and route **all** writers through it. **This changes every node ID** (and the
`export/graph_snapshot.json`). Must be an isolated, called-out commit.

**C2 — L2 evidence/experiment/scope IDs are not paper-scoped (HIGH).**
`_evidence_id/_experiment_id/_scope_id` hash only `canonicalize(name)`, with no
`paper_id`. Two papers with an Evidence node of the same name → same node_id →
merged. This **violates the spec's "L2 CREATE, never merged across papers."**
(Only `_claim_id` correctly includes `paper_id`.)
**Proposed resolution:** fold `paper_id` into the L2 node_id for evidence,
experiment, scope (as claim already does). Ties into C1 and C3.

**C3 — Neo4j L2 CREATE breaks re-ingest idempotency (HIGH).**
`create_epistemic_nodes()` uses `CREATE (n:Label {id:...})` with **no
uniqueness constraint** on Claim/Evidence/Experiment/Scope. Re-ingesting the
same paper creates **duplicate** L2 nodes. The spec asserts both "L2 = CREATE"
**and** "re-ingesting an unchanged document is a graph no-op." These conflict
for Neo4j. (In-memory hides this: it upserts by `node_id`, so
`test_ingest_one_is_idempotent` passes on the fake backend only.)
**Proposed resolution (needs your call):** the deterministic, paper-scoped L2
IDs from C2 make CREATE safely idempotent if we either (a) `MERGE` on the
paper-scoped id (keeps "never merged *across papers*" because the id is
paper-unique) or (b) delete-then-CREATE the paper's L2 nodes on re-ingest.
Recommend (a): least surprising, preserves the no-op guarantee. This is a
**semantic change to graph output on re-ingest** — flagged.

**C4 — "6 lenses" vs 3 (MED).** Doc-level inconsistency inside the spec itself
(overview/diagram say 6; table defines 3). See Open Question §4.

**C5 — `extraction_confidence` on edges is `Optional` (LOW).**
Spec: "carried on every edge." `GraphEdge.extraction_confidence: float | None`
and the model permits `None`. Producers currently set it on the edges they
emit. **Proposed resolution:** keep the field optional at the model level but
have writers always populate it (assert non-None in a test), rather than making
the field required (which would break the retrieval/JSON round-trip for legacy
data).

**C6 — Ingest example counts (LOW).** Spec example claims "19 nodes / 18
edges"; the sample yields 10/15 with 3 lenses. Cosmetic; will re-baseline once
G1 is resolved.

**C7 — mypy: `@computed_field` over `@property` (LOW).** `distillate.py:58`.
Pydantic-idiomatic but mypy `prop-decorator`. Resolve via mypy config
(`plugins = pydantic.mypy`) or restructure the accessor.

---

## 4. Open Question — Lens ↔ Distillate reconciliation

The `Distillate` has 18 entity types; only 3 lenses populate 3 of them.
Options:

- **(a) One lens per entity type** (~14+ lenses). Maximal parallelism and
  single-responsibility prompts, but 14 LLM calls/document (cost, latency) and
  lots of prompt boilerplate.
- **(b) Few multi-entity lenses grouped by ontology level** (my
  recommendation). Three-to-four lenses whose response models emit several
  related entity types each — aligning lenses with the three writer levels the
  code already has:
  - **DomainLens** → technologies, problems, capabilities, metrics, datasets,
    limitations (feeds `DomainWriter`).
  - **ClaimLens** (exists) → claims (+ evidence, experiments, scopes, or split
    into an **EvidenceLens** for L2) (feeds `EpistemicWriter`).
  - **ProvenanceLens** → paper, authors, affiliations, organizations, venues,
    funding sources (feeds `ProvenanceWriter`); **AuthorLens** already covers
    the author slice and can be subsumed or kept.
  - Keep **AssumptionLens** as-is (feeds L1 assumptions + L2 `ASSUMES`).
  This keeps LLM calls to ~4/doc, matches the three-writer structure, and lets
  us light up the currently-dead writer paths and the G2/G3 edges.
- **(c) Match what Balmung already does** = the current 3 lenses only. Lowest
  effort; leaves 15 Distillate fields and most of the ontology permanently
  empty. Only sensible if the near-term goal is authors/assumptions/claims.

**Recommendation: (b).** It aligns lenses with the existing three-level writer
architecture, unlocks the already-built (but unused) writer code, and keeps
cost bounded. **I will not implement Phase 3 lenses until you pick (a)/(b)/(c).**
Whatever you choose, no lens/entity type will be invented that isn't already in
the `Distillate`/ontology (per the constraints).

---

## 5. Phase-by-Phase Commit Plan

Each phase = one commit on branch `refactor/distillation-pipeline`, with
`ruff` + `mypy` + `pytest` green before commit. Because the scaffold already
exists, phases are **alignment/fix** passes, not rewrites — diffs are small.

| Phase | Content | Rough diff |
|---|---|---|
| **0** | This plan + `docs/PIPELINE.md`. **(this commit — docs only)** | +2 files |
| **1 — Quality gate zero-out** | `ruff --fix` + manual style; fix 4 mypy errors (computed_field, cli lens typing, delete broken neo4j legacy methods); fill empty `lenses/__init__.py`; drop dead `_LENS_TO_TYPE`. **No behaviour change; no ID change.** | ~15 files, small |
| **2 — Node-ID alignment (C1/C2)** | Add `ids.node_id(tenant,type,canonical)`; route all writers through it; paper-scope L2 evidence/experiment/scope IDs. Update `export/graph_snapshot.json` if committed. **Changes graph output — isolated commit, needs sign-off.** | 3 writers + ids + tests |
| **3 — Lenses & synthesize (Open Question)** | Implement chosen lens set; extend `SynthesizeStage` mapping + dedup for new fields; register in `cli.py`; fix distill docstring. Gated on §4 decision. | new lens files + synth + cli |
| **4 — Writer edges (G2/G3) + L2 idempotency (C3)** | Emit the missing L1/L2/L3 edges from the new entities; MERGE-on-paper-scoped-id for Neo4j L2. Enforce edge `extraction_confidence` (C5). | 3 writers + neo4j |
| **5 — CLI/config/retrieval polish** | Confirm `ingest/chat/export/version`; retrieval one-hop tests; any config tweaks. Mostly tests + docs. | small |
| **6 — Tests & gates** | Add G4/G5 tests (writer MERGE/CREATE, deterministic IDs, per-lens capture at pipeline level, dead-letter, one-hop retrieval, Neo4j-idempotency via a fake driver). Re-baseline ingest counts. | +test files |

Phases 2, 3, 4 each change graph output or idempotency and will be flagged
again at execution time before the diff lands.

---

## 6. Risk List (anything that could silently change graph output or break idempotency)

1. **Node-ID reformatting (C1)** — rewrites *every* node_id. Any persisted
   Neo4j graph or committed `graph_snapshot.json` becomes incompatible. Do it
   once, in isolation, with a before/after count + snapshot diff.
2. **L2 paper-scoping (C2)** — changes evidence/experiment/scope IDs; currently
   cross-paper-mergeable nodes will split. Correct per spec, but changes counts.
3. **Neo4j L2 CREATE → MERGE (C3)** — changes re-ingest semantics on the real
   backend from "duplicates" to "no-op." Intended, but it is a behaviour change;
   verify with a fake/mock Neo4j driver test (no live DB per constraints).
4. **New lenses (G1)** — will substantially increase node/edge counts and
   change the shape of every ingested graph. Re-baseline all count assertions.
5. **`ruff --fix` sweep** — auto-fixes could touch files broadly; keep it in its
   own commit so behaviour-affecting changes aren't hidden in a formatting diff.
   Restrict formatting to files already being edited elsewhere where possible.
6. **`extraction_confidence` enforcement (C5)** — if a writer path forgets it,
   downstream assessment silently loses signal; cover with a test asserting
   every produced edge has a value in [0,1].
7. **`computed_field canonical_name`** is used as the dedup key in synthesize
   and (indirectly) shapes IDs — do not alter its normalization without
   re-checking dedup and ID stability together.
8. **`document_id` formula is correct and must not change** — it already
   includes `tenant_id + source_id + content_sha256`; the C1 work must leave it
   untouched (only *node* IDs change).

---

## 7. Definition-of-Done tracking (from the task)

Final state after Phases 1–6 (branch `refactor/distillation-pipeline`):

| DoD item | Status |
|---|---|
| `REFACTOR_PLAN.md` reflects final state | ✅ (this file) |
| `distill ingest` runs on fake+in-memory, prints counts | ✅ (49 nodes / 21 edges) |
| Re-ingest is a verified no-op | ✅ in-memory (test) + Neo4j MERGE (fake-driver test, C3) |
| Node/Chunk/Document ID formulas match spec | ✅ (node IDs via `ids.node_id`, C1/C2) |
| L1/L3 MERGE, L2 paper-scoped; every edge has `extraction_confidence∈[0,1]` | ✅ (C3, C5) |
| Concrete adapters imported only in `cli.py`; deps direction holds | ✅ |
| No cross-document edges during ingestion | ✅ (linker is within-document only; seam noted) |
| `ruff`, `mypy`, `pytest` all pass | ✅ (ruff clean / mypy clean / 41 passed) |
| Each phase its own commit | ✅ |

### What each phase delivered
- **P1** quality-gate zero-out (ruff/mypy clean; deleted broken Neo4j legacy
  methods; no behaviour change).
- **P2** node-ID formula alignment (C1 + C2) — tenant/type partitioning,
  paper-scoped L2 ids.
- **P3** six multi-entity lenses (strategy b) + type-routed synthesis.
- **P4** relationship + structural edges (`mapping/edges.py`), Neo4j L2
  MERGE-idempotency (C3), edge `extraction_confidence` enforced (C5).
- **P5** CLI/config/retrieval verified conformant; no source change required
  (verification landed as the retrieval test in P6).
- **P6** test suite (21 → 41): node-ID formula, writer MERGE/paper-scoping,
  edge linking + dangling filter, one-hop retrieval, Neo4j MERGE semantics,
  pipeline-level per-lens error capture.

### Remaining seams / out of scope (by design)
- Cross-document / corpus edges (APPLIES_TO, UNDERLIES, corpus
  SUPPORTS/CONTRADICTS) — separate job over the persisted graph.
- Relationship edges only materialise when extraction supplies the reference
  fields; `FakeLLMClient` leaves them empty (verified via canned responses in
  tests), so a fake ingest shows the structural edges only.
- `AuthorLens`/`AffiliationMention` still stamp `extraction_confidence=1.0`
  literally (pre-existing; not in this refactor's scope).

---

**Decisions (locked in review, 2026-08-08):**
1. Open Question §4 — **(b) few multi-entity lenses** grouped by ontology level.
2. C1/C2/C3 graph-output changes — **all approved** (node-ID reformat,
   paper-scoped L2 IDs, Neo4j L2 CREATE→MERGE-on-paper-scoped-id).
3. Legacy sibling directories — **out of scope**.
