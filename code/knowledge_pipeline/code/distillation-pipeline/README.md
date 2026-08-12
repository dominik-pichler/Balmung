# Distillation Pipeline

Document → Distillate → Knowledge Graph ingestion pipeline. It reads research
papers and builds a **four-layer knowledge graph** (Domain · Epistemik ·
Provenanz · Assessment) via a preprocess → six-lens distillation → synthesis →
graph-persistence flow.

> **New here?** Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the
> high-level picture, then [`docs/PIPELINE.md`](docs/PIPELINE.md) for the deep
> reference.

## What it does

Given a document (PDF, Markdown, HTML, plain text), the pipeline:

1. **Preprocesses** it — format-specific text extraction, NFKC normalization,
   sliding-window chunking with deterministic IDs and character offsets.
2. **Distills** it through **six parallel lenses**, each calling an LLM with a
   typed (pydantic) response schema:
   | Lens | Extracts | Feeds ontology layer |
   |---|---|---|
   | `domain` | technologies, problems, capabilities, metrics, datasets, limitations | L1 Domain |
   | `assumption` | implicit assumptions | L1 Domain |
   | `claim` | claims (+ what they're `about` and `assume`) | L2 Epistemik |
   | `evidence` | evidence, experiments, scopes | L2 Epistemik |
   | `author` | authors + affiliations | L3 Provenanz |
   | `provenance` | cited papers, organizations, venues, funding | L3 Provenanz |
3. **Synthesizes** the lens outputs — merges, deduplicates by canonical name,
   routes each entity type to its writer.
4. **Persists** to a graph store as nodes and edges, with an
   `extraction_confidence ∈ [0,1]` on every edge.

Per-lens failures are captured (not fatal); whole-document failures are
dead-lettered with the stage + error, and the pipeline keeps going.

## The ontology (what lands in the graph)

Ingestion writes **three** of the four layers; the fourth (Assessment) is left
for a separate downstream engine.

| Layer | Write semantics | Node types |
|---|---|---|
| **L1 Domain** | persistent, **MERGE**'d across papers | Technology, Problem, Capability, Metric, Dataset, Assumption, Limitation |
| **L2 Epistemik** | per-paper, paper-scoped id (MERGE = idempotent re-ingest, never merges across papers) | Claim, Evidence, Experiment, Scope |
| **L3 Provenanz** | persistent, **MERGE**'d | Paper, Author, Venue, Organization, FundingSource |
| **L4 Assessment** | *not produced by ingestion* | (reserved) |

Edges: `MAKES_CLAIM`, `ABOUT`, `ADDRESSES`, `CONCERNS`, `HOLDS_UNDER`,
`ASSUMES`, `SUPPORTED_BY`, `REFUTED_BY`, `PRODUCED_BY`, `EVALUATED_ON`,
`MEASURED_BY`, `AUTHORED_BY`, `AFFILIATED_WITH`, `CITES`, `FUNDED_BY`. Only
*within-document* edges are produced at ingest; corpus-level edges are a
separate job. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full
edge map.

## Layout

```
src/distillation/
  domain/        # Pure data types (ontology, distillate, ids) — no I/O
  ports/         # Abstract interfaces (DocumentSource, LLMClient, GraphRepository, …)
  adapters/      # Concrete implementations behind each port (fake/anthropic/omlx, in_memory/neo4j, …)
  pipeline/      # Stages, the six lenses, orchestrator, DI context
  mapping/       # Distillate → graph nodes/edges (three writers + EdgeLinker)
  cli.py         # Typer entrypoint (the only place concrete adapters are wired)
docs/            # ARCHITECTURE.md, PIPELINE.md, MANUAL_GRAPH_EDITING.md, REFACTOR_PLAN.md
schema/          # Neo4j constraints + ontology CSV
tests/unit/      # deterministic pytest suite (fake LLM)
tests/eval/      # lens quality regression vs a real LLM (skipped by default)
examples/        # sample input documents
```

Dependency direction is strict: `domain` depends on nothing else, `ports` on
`domain`, `adapters`/`pipeline` on `ports` + `domain`, and `cli.py` is the only
thing that wires concrete adapters.

## Setup

Python 3.11+.

```bash
pip install -e .[dev]      # or: uv sync
cp .env.example .env
```

Defaults run **fully offline**: `FakeLLMClient` produces deterministic stubs,
`InMemoryGraphRepository` keeps the graph in RAM — no API keys needed. Swap in
real services via `.env`:

```ini
# LLM: fake | anthropic | omlx
DISTILL_LLM_PROVIDER=omlx
DISTILL_LLM_MODEL=Qwen3.6-35B-A3B-4bit
DISTILL_OMLX_BASE_URL=http://localhost:8000/v1
OMLX_API_KEY=...

# Graph: in_memory | neo4j   (secrets use conventional names, no DISTILL_ prefix)
DISTILL_GRAPH_BACKEND=neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
```

For a real Neo4j run, apply the ontology constraints once:

```bash
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f schema/neo4j_constraints.cypher
```

## Run

```bash
distill ingest examples/full_ontology_paper.txt
```

Structured logs at every stage plus a final summary (fake + in-memory yields
49 nodes / 21 edges for the full-ontology example):

```
Ingested 1 document(s). Graph now has 49 node(s), 21 edge(s).
  - 73715cfa2ef0d25b: +49 nodes / +21 edges
```

Multiple files in one invocation work too: `distill ingest a.pdf b.md c.txt`.

## Knowledge-graph chat

Query the graph in plain English. Retrieval embeds the question, takes the
top-k most similar nodes, expands one hop, and sends only that subgraph to the
LLM.

```bash
distill chat "Which problems does SparseFormer address?"
distill chat --top-k 10                 # interactive REPL, wider seed
```

Needs a real embedder (`DISTILL_EMBEDDER_PROVIDER=omlx`); the fake embedder
returns random vectors.

## Export / backup

```bash
distill export                          # → export/graph_snapshot.json
distill export --output backups/db.json
```

## Tests

```bash
pytest                                  # 44 deterministic unit tests (fake LLM)
```

Covers deterministic IDs, chunker offsets, lens base behavior, writer
MERGE/paper-scoping semantics, edge linking (incl. the `ASSUMES` no-cross-product
regression) and dangling-edge filtering, Neo4j write semantics (incl. `name`
persistence), one-hop retrieval, and end-to-end orchestration (success,
idempotency, dead-letter).

### Lens quality regression (real LLM)

`tests/eval/` scores each lens against a real model over a fixture paper with a
known gold standard — entity **recall** and edge-driving **reference-field
coverage**. Use it to compare models or prompt changes. Skipped by default
(needs a real provider):

```bash
DISTILL_LLM_PROVIDER=omlx pytest tests/eval -m eval -s
# strict mode also gates on reference-field coverage:
DISTILL_EVAL_STRICT=1 DISTILL_LLM_PROVIDER=omlx pytest tests/eval -m eval -s
```

A per-model JSON scorecard is written to `tests/eval/reports/` so runs are
comparable over time.

## Fixing under-extraction by hand

Local models often leave edges unformed (they extract the entities but not the
reference fields that link them). [`docs/MANUAL_GRAPH_EDITING.md`](docs/MANUAL_GRAPH_EDITING.md)
is a cookbook of Cypher recipes for patching the graph without breaking
re-ingest idempotency.

## Determinism and idempotency

- Node IDs: `sha256(tenant_id || node_type || [paper_id] || canonical_name)[:16]`.
  Same canonical entity → same id across runs and papers. L2 nodes fold in
  `paper_id` so they never merge across papers.
- Chunk IDs: `sha256(document_id || "chunk" || index)[:16]`.
- `document_id` includes the content hash — a content change is a new version.
- Re-ingesting an unchanged document is a graph no-op.

## Extension points

Ports-and-adapters; common extensions are drop-ins, all wired in `cli.py`:

- **Document source** — implement `ports.document_source.DocumentSource` (S3, Kafka, …).
- **Format parser** — implement `ports.document_parser.DocumentParser`, register in the `ParserRegistry`.
- **LLM backend** — implement `ports.llm_client.LLMClient.structured` (bring your own retry / structured-output).
- **Graph store** — implement `ports.graph_repository.GraphRepository` (upserts must be idempotent on id).
- **Embedder** — implement `ports.embedder.Embedder` (used by chat retrieval).
- **Cross-corpus edges** — a separate job over the persisted graph, not part of ingest.
