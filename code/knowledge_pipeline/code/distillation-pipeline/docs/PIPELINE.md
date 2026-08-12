# Knowledge Pipeline — Structure & Workflow

> **Distillation Pipeline**: Document → Distillate → Knowledge Graph ingestion pipeline.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [Directory Layout](#directory-layout)
  - [Dependency Direction](#dependency-direction)
  - [Ports & Adapters Pattern](#ports--adapters-pattern)
- [Data Models](#data-models)
  - [Domain Objects](#domain-objects)
  - [Pipeline Artifacts](#pipeline-artifacts)
  - [Graph Representation](#graph-representation)
- [Pipeline Workflow](#pipeline-workflow)
  - [Stage 1: Preprocess](#stage-1-preprocess)
  - [Stage 2: Distill (Lens Parallelization)](#stage-2-distill-lens-parallelization)
  - [Stage 3: Synthesize](#stage-3-synthesize)
  - [Stage 4: Persist](#stage-4-persist)
- [Knowledge Graph Ontology](#knowledge-graph-ontology)
  - [Three-Level Node Hierarchy](#three-level-node-hierarchy)
  - [Edge Taxonomy](#edge-taxonomy)
- [Retrieval & Chat](#retrieval--chat)
- [CLI Commands](#cli-commands)
- [Configuration](#configuration)
- [Failure Handling](#failure-handling)
- [Extensibility](#extensibility)

---

## Overview

The knowledge pipeline ingests documents (PDF, Markdown, HTML, plain text) and produces a **knowledge graph** by:

1. **Preprocessing** — extract text, chunk with deterministic IDs
2. **Distilling** — apply 6 parallel LLM-powered lenses, each extracting a different knowledge dimension
3. **Synthesizing** — merge and deduplicate lens outputs into a single structured `Distillate`
4. **Persisting** — map the distillate to graph nodes and edges, write to a graph store

All LLM calls use **typed Pydantic response schemas** so the pipeline knows exactly what structure to expect. Per-lens failures are captured (not fatal); per-document failures are dead-lettered.

---

## Architecture

### Directory Layout

```
src/distillation/
├── domain/              # Pure data types (no I/O)
│   ├── distillate.py    # All extraction entity types, Distillate, LensOutput
│   ├── document.py      # SourceDocument, Chunk, DocumentMetadata
│   ├── graph.py         # GraphNode, GraphEdge, GraphNodeType, GraphEdgeType (re-exports)
│   ├── ids.py           # Deterministic ID generation (sha256-based)
│   └── ontology.py      # All enumeration types (ClaimType, Polarity, etc.)
│
├── ports/               # Abstract interfaces (no implementations)
│   ├── chunker.py
│   ├── dead_letter_store.py
│   ├── document_parser.py
│   ├── document_source.py
│   ├── embedder.py
│   ├── graph_repository.py
│   └── llm_client.py
│
├── adapters/            # Concrete implementations behind ports
│   ├── chunkers/sliding_window.py    # Token-based windowed chunking
│   ├── embedders/                    # FakeEmbedder, OmlxEmbedder
│   ├── graph/                        # InMemoryGraphRepository, Neo4jGraphRepository
│   ├── llm/                          # FakeLLMClient, AnthropicLLMClient, OmlxLLMClient
│   ├── parsers/                      # PlainTextParser, MarkdownParser, PdfParser
│   ├── sources/local_file.py         # LocalFileSource
│   └── dead_letter/filesystem.py     # FilesystemDeadLetterStore
│
├── pipeline/            # Stage logic
│   ├── context.py          # PipelineContext (DI container)
│   ├── orchestrator.py     # IngestionPipeline (drives stages)
│   ├── lenses/             # LLM-powered extraction lenses
│   │   ├── base.py         # Lens[TResponse, TEntity] — abstract base
│   │   ├── author.py       # AuthorLens — extracts authors, affiliations, interests
│   │   ├── assumption.py   # AssumptionLens — surfaces implicit assumptions
│   │   └── claim_lens.py   # ClaimLens — extracts claims with full epistemik metadata
│   └── stages/             # Pipeline stages
│       ├── base.py         # Stage[TIn, TOut] — protocol
│       ├── preprocess.py   # PreprocessStage: parse + chunk
│       ├── distill.py      # DistillStage: fan-out to lenses
│       ├── synthesize.py   # SynthesizeStage: merge + dedup
│       └── persist.py      # PersistStage: write to graph
│
├── mapping/             # Distillate → GraphNode/GraphEdge conversion
│   ├── domain_writer.py    # Level 1 writers (persistent, MERGE'd)
│   ├── epistemic_writer.py # Level 2 writers (per-paper, CREATE)
│   └── provenance_writer.py# Level 3 writers (persistent, MERGE'd)
│
├── cli.py              # Typer CLI: ingest, chat, export, version
├── config.py           # Settings (env-driven configuration)
├── logging_setup.py    # Structured logging setup
└── retrieval.py        # GraphRetriever (semantic retrieval + chat)
```

### Dependency Direction

```
domain  ←  (no internal deps)
  ↑
ports   ←  domain
  ↑
adapters ←  ports + domain
  ↑
pipeline ←  ports + domain
  ↑
mapping  ←  pipeline + domain
  ↑
cli.py   ←  everything (only place that wires concrete adapters)
```

The dependency direction is strict. The CLI is the **only** file that knows about concrete adapter implementations; everywhere else talks through ports.

### Ports & Adapters Pattern

**Ports** are abstract interfaces (Python `Protocol` or abstract base classes) that define what the pipeline needs:

| Port | Purpose |
|------|---------|
| `DocumentSource` | Streams `SourceDocument` objects from some origin (files, S3, API) |
| `DocumentParser` / `ParserRegistry` | Extracts text from raw bytes (Markdown, plain text, PDF) |
| `Chunker` | Splits text into overlapping `Chunk` objects |
| `LLMClient` | Calls an LLM, optionally with structured (Pydantic) output |
| `GraphRepository` | Upserts nodes/edges, queries by ID or all |
| `Embedder` | Embeds text to vectors for semantic search |
| `DeadLetterStore` | Records failed documents with stage and error |

**Adapters** are concrete implementations behind each port. For example, `LocalFileSource` implements `DocumentSource`, `SlidingWindowChunker` implements `Chunker`, and `InMemoryGraphRepository` implements `GraphRepository`.

This pattern means:
- Tests can swap in mock adapters without touching pipeline logic
- New backends (Neo4j, Ollama, Anthropic) are drop-ins
- The CLI is the single point of wiring configuration

---

## Data Models

### Domain Objects

**`SourceDocument`** — The raw input artifact:

```python
SourceDocument {
    metadata: DocumentMetadata {
        tenant_id: str
        source_id: str         # Caller-supplied stable ID
        uri: str
        fetched_at: datetime
        extra: dict[str, str]
    }
    format: DocumentFormat  # pdf, html, markdown, text, docx, ...
    raw_bytes: bytes
    content_sha256: str
}
```

The `document_id` is deterministically computed from `tenant_id | source_id | content_sha256`. Same content → same ID (idempotency). Content change → new ID (versioning).

**`Chunk`** — A text fragment emitted by the chunker:

```python
Chunk {
    chunk_id: str            # sha256(document_id | "chunk" | index)[:16]
    document_id: str
    index: int               # Position within document
    text: str
    start_char: int
    end_char: int
    token_estimate: int | None
}
```

### Pipeline Artifacts

**`PreprocessedDocument`** — Output of the PreprocessStage:

```python
PreprocessedDocument {
    document_id: str
    text: str                # Full extracted text
    chunks: list[Chunk]
}
```

**`LensOutput`** — Output of a single lens:

```python
LensOutput {
    lens_name: str
    items: list[ExtractedEntity]
    error: str | None        # Set when the LLM call fails
}
```

**`Distillate`** — The synthesized output (input to the PersistStage):

```python
Distillate {
    paper_id: str            # The document's ID
    chunk_ids: list[str]

    # Level 1: Domain (persistent, MERGE'd across papers)
    technologies: list[TechnologyMention]
    problems: list[ProblemMention]
    capabilities: list[CapabilityMention]
    metrics: list[MetricMention]
    datasets: list[DatasetMention]
    assumptions: list[AssumptionMention]
    limitations: list[LimitationMention]

    # Level 2: Epistemik (per-paper, CREATE)
    claims: list[ClaimMention]
    evidence: list[EvidenceMention]
    experiments: list[ExperimentMention]
    scopes: list[ScopeMention]

    # Level 3: Provenanz (persistent, MERGE'd)
    papers: list[PaperMention]
    authors: list[AuthorMention]
    affiliations: list[AffiliationMention]
    organizations: list[OrganizationMention]
    venues: list[VenueMention]
    funding_sources: list[FundingSourceMention]
}
```

### Graph Representation

**`GraphNode`** — A vertex in the knowledge graph:

```python
GraphNode {
    node_id: str             # Deterministic: sha256(tenant || type || canonical_name)[:16]
    type: GraphNodeType      # TECHNOLOGY, CLAIM, AUTHOR, etc.
    name: str
    properties: dict        # All extra attributes
}
```

**`GraphEdge`** — A directed edge between nodes:

```python
GraphEdge {
    source_node_id: str
    target_node_id: str
    type: GraphEdgeType      # MAKES_CLAIM, AUTHORED_BY, ASSUMES, etc.
    extraction_confidence: float  # 0.0–1.0, carried on every edge
}
```

Every extraction carries an `extraction_confidence` field (required by the ontology) so downstream assessment engines can reason about extraction quality.

---

## Pipeline Workflow

```
┌──────────────┐    ┌───────────────┐    ┌───────────────┐    ┌──────────────┐    ┌───────────────┐
│  Document     │    │  Preprocess   │    │    Distill    │    │  Synthesize  │    │   Persist     │
│  Source       │───▶│  (parse +     │───▶│  (6 lenses    │───▶│  (merge +    │───▶│  (write to    │
│  (raw bytes)  │    │   chunk)      │    │   parallel)   │    │   dedup)     │    │   graph)      │
└──────────────┘    └───────────────┘    └───────────────┘    └──────────────┘    └───────────────┘
                           │                       │                         │
                    PreprocessedDoc         list[LensOutput]            Distillate
```

### Stage 1: Preprocess

**Input:** `SourceDocument` (raw bytes + metadata)
**Output:** `PreprocessedDocument` (parsed text + list of chunks)

Steps:
1. **Parse** — The `ParserRegistry` dispatches based on `DocumentFormat`:
   - `PlainTextParser` → direct byte decode
   - `MarkdownParser` → strip markdown formatting
   - `PdfParser` → (optional, requires `pypdf`) extract text from PDF
2. **Validate** — Reject documents where the parser produces empty text
3. **Chunk** — The `SlidingWindowChunker` splits the text into overlapping chunks using token-based sliding windows (configurable `chunk_token_size` and `chunk_token_overlap`)

Each chunk gets a deterministic `chunk_id`, character offsets (`start_char`, `end_char`), and a token count estimate.

### Stage 2: Distill (Lens Parallelization)

**Input:** `PreprocessedDocument`
**Output:** `list[LensOutput]` (one per lens, plus optional per-lens errors)

The DistillStage fans out to all configured lenses **in parallel** via `asyncio.gather`. Per-lens failures are captured in `LensOutput.error` and **do not abort** the pipeline (ontology design: missing dimensions simply produce fewer nodes, not a catastrophic failure).

Each lens:
1. Concatenates (a window of) chunks
2. Calls the LLM with a lens-specific `system_prompt` + a typed `response_model` (Pydantic)
3. Projects the response into the lens's entity list, stamped with chunk provenance

#### Lenses

| Lens | Purpose | Key Fields Extracted |
|------|---------|---------------------|
| **AuthorLens** | Authors, affiliations, interests | `name`, `affiliation`, `interests`, `position`, `orcid` |
| **AssumptionLens** | Implicit assumptions | `name`, `statement`, `assumption_type` |
| **ClaimLens** | Claims with epistemik metadata | `text`, `claim_type`, `polarity`, `stated_confidence`, `prior_implausibility`, `decay_immune` |

Each lens has:
- A `system_prompt` property — the instructions to the LLM
- A `response_model` property — the Pydantic model the LLM must return (enforced structured output)
- A `project(response, chunk_ids)` method — converts the raw LLM response into typed entities

The base `Lens` class owns chunk formatting and LLM dispatch; concrete lenses only provide the prompt, response model, and projection logic.

### Stage 3: Synthesize

**Input:** `PreprocessedDocument` + `list[LensOutput]`
**Output:** `Distillate`

Responsibilities:
1. **Merge** — Combine lens outputs into a single `Distillate` by field (authors, assumptions, claims)
2. **Deduplicate** — Within a single document, collapse entities sharing a `canonical_name` (case-insensitive, stripped). Cross-document semantic dedup is a separate process (out of scope for ingestion).

The deduplication strategy:
- Keep the highest-confidence representative
- Union provenance chunk IDs (preserving order)
- Union list-typed fields (e.g., author interests)
- Prefer non-empty scalar fields from the higher-confidence entry

Claims are paper-scoped and deduplicated by claim ID (not name), because distinct claims can share a short label.

### Stage 4: Persist

**Input:** `SourceDocument` + `Distillate`
**Output:** `(node_count, edge_count)`

Uses a **three-layer writer architecture** matching the ontology:

#### Level 1: DomainWriter (Persistent, MERGE'd)
Writes persistent nodes that cross papers:
- `Technology`, `Problem`, `Capability`, `Metric`, `Dataset`, `Assumption`, `Limitation`

These use **MERGE** semantics: same `node_id` (based on canonical name) → update in place.

#### Level 2: EpistemicWriter (Per-Paper, CREATE)
Writes paper-scoped nodes:
- `Claim` — with full epistemik metadata (polarity, confidence, decay_immune)
- `Evidence` — supporting or refuting data
- `Experiment` — experimental setup metadata
- `Scope` — operational boundaries (data domain, hardware, time window)

These use **CREATE** semantics: never merged across papers. Each paper creates its own claim/evidence/experiment/scope nodes.

Claims are linked to domain anchors via `MAKES_CLAIM`, `SUPPORTED_BY`, `REFUTED_BY`, `ASSUMES` edges.

#### Level 3: ProvenanceWriter (Persistent, MERGE'd)
Writes provenance and identity nodes:
- `Paper` — the ingested document itself (anchor node)
- `Author`, `Affiliation` — author identity and institutional affiliation
- `Organization`, `Venue`, `FundingSource` — contextual metadata

The paper node (identified by `document_id`) becomes the anchor that per-paper edges (`MAKES_CLAIM`, `AUTHORED_BY`) point at.

---

## Knowledge Graph Ontology

### Three-Level Node Hierarchy

```
┌──────────────────────────────────────────────────────────────────────┐
│ Level 1: Domain  (persistent, MERGE'd across papers)                  │
│ Technology, Problem, Capability, Metric, Dataset, Assumption, Limitation │
├──────────────────────────────────────────────────────────────────────┤
│ Level 2: Epistemik (per-paper, CREATE)                               │
│ Claim, Evidence, Experiment, Scope                                   │
├──────────────────────────────────────────────────────────────────────┤
│ Level 3: Provenanz (persistent, MERGE'd)                             │
│ Paper, Author, Affiliation, Organization, Venue, FundingSource        │
└──────────────────────────────────────────────────────────────────────┘
```

### Edge Taxonomy

| Edge Type | Description | Level |
|-----------|-------------|-------|
| `MAKES_CLAIM` | Paper → Claim | 2 (per-paper) |
| `SUPPORTED_BY` | Claim → Evidence | 2 (per-paper) |
| `REFUTED_BY` | Claim → Evidence | 2 (per-paper) |
| `ASSUMES` | Claim → Assumption | 2 (per-paper) |
| `ABOUT` | Claim → Domain entity | 2 (per-paper) |
| `ADDRESSES` | Capability → Problem | 1 (domain) |
| `CONCERNS` | Limitation → Domain entity | 1 (domain) |
| `HOLDS_UNDER` | Assumption → Domain entity | 1 (domain) |
| `PRODUCED_BY` | Experiment → Technology | 1 (domain) |
| `EVALUATED_ON` | Experiment → Dataset | 1 (domain) |
| `MEASURED_BY` | Experiment → Metric | 1 (domain) |
| `CITES` | Paper → Paper | 3 (provenance) |
| `AUTHORED_BY` | Paper → Author | 3 (provenance) |
| `AFFILIATED_WITH` | Author → Organization | 3 (provenance) |
| `FUNDED_BY` | Paper → FundingSource | 3 (provenance) |

Cross-document edges (e.g., `APPLIES_TO`, `UNDERLIES`, corpus-level `SUPPORTS`/`CONTRADICTS`) are **intentionally not produced** by the ingestion pipeline. They are corpus-level computations that run as separate jobs reading from and writing back to the `GraphRepository`.

---

## Retrieval & Chat

The `GraphRetriever` enables querying the knowledge graph in plain English via an LLM.

**Retrieval strategy:**
1. Embed all nodes (text derived from `type + name + key properties`)
2. Embed the query
3. Rank nodes by cosine similarity, take top-k (default: 5)
4. **One-hop expansion** — include every edge touching a seed node, plus the neighbor nodes on the other end
5. Send only that subgraph to the LLM as context

**CLI:**

```bash
# Single question
distill chat "What assumptions are made about X?"

# Interactive REPL
distill chat

# Widen retrieval (default seed: 5 nodes)
distill chat --top-k 10 "Who are the authors and what are their interests?"
```

The retrieval query wraps the subgraph in a system prompt that describes node/edge types and instructs the LLM to answer based solely on the subgraph data.

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `distill ingest <path> [path...]` | Ingest one or more documents, print summary |
| `distill chat [question]` | Query knowledge graph via LLM (interactive or one-shot) |
| `distill export [-o path]` | Export all nodes/edges to JSON (version control, backup) |
| `distill version` | Print the package version |

### Ingest Command

```bash
distill ingest examples/sample_document.txt
# Output: "Ingested 1 document(s). Graph now has 19 node(s), 18 edge(s)."
#         "  - 662ddf11862045a7: +19 nodes / +18 edges"
```

### Export Command

```bash
distill export                          # → export/graph_snapshot.json
distill export --output backups/db.json # Custom destination
```

---

## Configuration

All runtime configuration is funneled through the `Settings` class (Pydantic `BaseSettings`):

```ini
# Pipeline behavior
DISTILL_TENANT_ID=default
DISTILL_LOG_LEVEL=INFO

# Chunking
DISTILL_CHUNK_TOKEN_SIZE=800
DISTILL_CHUNK_TOKEN_OVERLAP=100

# LLM (defaults to FakeLLMClient when empty)
DISTILL_LLM_PROVIDER=anthropic      # or "omlx", "fake"
DISTILL_LLM_MODEL=claude-sonnet-4-5
ANTHROPIC_API_KEY=sk-ant-...        # Read without DISTILL_ prefix

# Embeddings
DISTILL_EMBEDDER_PROVIDER=omlx      # or "fake"
DISTILL_EMBEDDER_MODEL=Qwen3.6-35B
OMLX_API_KEY=...

# Graph
DISTILL_GRAPH_BACKEND=neo4j         # or "in_memory"
DISTILL_NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# Dead letter
DISTILL_DEAD_LETTER_DIR=./dead_letter
```

Environment variables are prefixed with `DISTILL_` (except secrets, which use their conventional names to match SDK conventions). Settings are loaded from a `.env` file when present.

Providers:
- **LLM**: `FakeLLMClient` (deterministic stubs), `AnthropicLLMClient` (tool-use structured output), `OmlxLLMClient` (OpenAI-compatible API)
- **Embedder**: `FakeEmbedder` (random vectors), `OmlxEmbedder` (embedding API)
- **Graph**: `InMemoryGraphRepository` (RAM), `Neo4jGraphRepository` (persistent)

---

## Failure Handling

Failures at every level are captured and recorded:

| Failure Level | Handling |
|---------------|----------|
| **Single lens fails** | Captured in `LensOutput.error`; other lenses continue; failed lens name reported in `IngestionResult.failed_lenses` |
| **Whole document fails** (parse, chunk, or any stage) | Document is **dead-lettered** via `DeadLetterStore`; the pipeline continues processing remaining documents |

The dead-letter store records the `document`, the `stage` where failure occurred, and the `error` message. These are persisted to a configurable filesystem directory (`DISTILL_DEAD_LETTER_DIR`).

The design philosophy: **ontology over accuracy** — a missing dimension simply produces fewer nodes/edges rather than a catastrophic pipeline failure.

---

## Extensibility

The ports-and-adapters pattern makes common extensions drop-ins:

| Extension | What to Implement | Where to Register |
|-----------|-------------------|-------------------|
| **New document source** | `ports.document_source.DocumentSource` (e.g., S3Source, KafkaSource) | `cli.py` — `_build_context()` |
| **New format parser** | `ports.document_parser.DocumentParser` with `supported_formats` | `cli.py` — `ParserRegistry([...])` |
| **New LLM backend** | `ports.llm_client.LLMClient.structured()` (with retry/structured-output strategy) | `cli.py` — `_build_llm()` |
| **Graph store** | `ports.graph_repository.GraphRepository` (upserts must be idempotent) | `cli.py` — `_build_graph_repo()` |
| **Cross-corpus edges** | Separate job reading from `GraphRepository`, writing edges back | New CLI command or scheduled job |

The pipeline is fully reentrant: documents can be processed in parallel (`asyncio.gather`) with separate `PipelineContext` instances.

---

## Determinism & Idempotency

- **Node IDs**: `sha256(tenant_id || node_type || canonical_name)[:16]` — same canonical entity → same ID across runs and documents
- **Chunk IDs**: `sha256(document_id || "chunk" || index)[:16]` — same chunk in same document is always the same chunk
- **Document IDs**: include the `content_sha256`, so content changes produce new nodes (versioned, distinct)
- **Re-ingestion**: unchanged documents are a graph-no-op (upsert on the same IDs)

The test `test_ingest_one_is_idempotent` verifies this behavior.
