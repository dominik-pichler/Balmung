# Distillation Pipeline

Document → Distillate → Knowledge Graph ingestion pipeline. Implements the architecture in the two design diagrams: a preprocessing → six-lens distillation → synthesis → graph-persistence flow whose output conforms to the Source / Author / Topic / Theory / Conclusion / Methodology / Assumption ontology.

## What it does

Given a document (PDF, Markdown, HTML, plain text, …), the pipeline:

1. **Preprocesses** it: format-specific text extraction, unicode normalization, chunking with deterministic IDs and character offsets.
2. **Distills** it through six parallel lenses, each calling an LLM with a typed (pydantic) response schema:
   - Topic — what the document is about
   - Author — authors, affiliations, stated interests
   - Implicit Assumption — what the document takes for granted
   - Theory — theories the document builds
   - Conclusion — takeaways the document derives
   - Methodology — methods the document uses
3. **Synthesizes** the lens outputs: merges, deduplicates by canonical name, normalizes within-document cross-references.
4. **Persists** the result to a graph store as nodes (`Source`, `Author`, `Topic`, …) and edges (`AUTHORED_BY`, `DISCUSSES`, `BUILDS`, …) with chunk-level provenance on every edge.

Failed documents are dead-lettered with the stage and error captured; the pipeline keeps going.

## Layout

```
src/distillation/
  domain/        # Pure data types (no I/O)
  ports/         # Abstract interfaces (DocumentSource, LLMClient, GraphRepository, …)
  adapters/      # Concrete implementations behind each port
  pipeline/      # Stages, lenses, orchestrator, DI context
  mapping/       # Distillate → graph nodes/edges
  cli.py         # Typer entrypoint
tests/unit/      # pytest suite
examples/        # Sample input document
```

Dependency direction is strict: `domain` depends on nothing else in the project, `ports` depends only on `domain`, `adapters` and `pipeline` depend on `ports` + `domain`, and `cli` is the only thing that wires concrete adapters together.

## Setup

Python 3.11+.

```bash
pip install -e .[dev]
cp .env.example .env
```

Defaults run fully offline: `FakeLLMClient` produces deterministic stub responses, `InMemoryGraphRepository` keeps the graph in RAM, no API keys required. Swap to real services by editing `.env`:

```ini
DISTILL_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

DISTILL_GRAPH_BACKEND=neo4j
DISTILL_NEO4J_URI=bolt://localhost:7687
DISTILL_NEO4J_USER=neo4j
DISTILL_NEO4J_PASSWORD=...
```

### Ollama (local, recommended for M5)

Install [Ollama](https://ollama.com) and pull the required models:

```bash
# LLM — general-purpose Q&A and graph reasoning
ollama pull qwen2.5:14b

# Embeddings — used for semantic retrieval in `distill chat`
ollama pull nomic-embed-text
```

Then set in `.env`:

```ini
DISTILL_LLM_PROVIDER=ollama
DISTILL_LLM_MODEL=qwen2.5:14b

DISTILL_EMBEDDER_PROVIDER=ollama
DISTILL_EMBEDDER_MODEL=nomic-embed-text

DISTILL_OLLAMA_BASE_URL=http://localhost:11434/v1
```

**Model notes for M5:**

| Model | RAM (4-bit) | Best for |
|---|---|---|
| `qwen2.5:14b` | ~8 GB | Graph Q&A, structured-data reasoning — recommended |
| `llama3.1:8b` | ~5 GB | Faster / lighter alternative |
| `nomic-embed-text` | ~270 MB | Semantic retrieval (embeddings) |

`qwen3-coder` is optimised for code generation and is not well-suited for knowledge-graph Q&A. `qwen2.5:14b` is the general-purpose variant of the same family and performs significantly better on this task.

## Run

```bash
distill ingest examples/sample_document.txt
```

You should see structured logs at every stage and a final summary:

```
Ingested 1 document(s). Graph now has 19 node(s), 18 edge(s).
  - 662ddf11862045a7: +19 nodes / +18 edges
```

Multiple files in one invocation work too:

```bash
distill ingest doc1.pdf doc2.md doc3.txt
```

## Knowledge graph chat

Query the graph in plain English. The retrieval layer embeds your question, finds the top-k most semantically similar nodes, expands one hop to include their direct neighbours, and sends only that subgraph to the LLM as context.

```bash
# Single question
distill chat "What assumptions are made about X?"

# Interactive REPL
distill chat

# Widen retrieval seed (default: 5)
distill chat --top-k 10 "Who are the authors and what are their interests?"
```

Requires `DISTILL_EMBEDDER_PROVIDER=ollama` (or another real embedder) — the fake embedder produces random vectors that do not reflect semantic similarity.

## Export / backup

Snapshot every node and edge to a JSON file suitable for version control or backup:

```bash
distill export                          # → export/graph_snapshot.json
distill export --output backups/db.json # custom path
```

Commit `export/` to git to version your graph alongside your code.

## Tests

```bash
pytest
```

25 unit tests covering deterministic IDs, chunker offset fidelity, the lens base behavior (including LLM-failure handling), the graph mapper's node/edge coverage and idempotency, in-memory graph upsert semantics, and end-to-end orchestrator runs (success, idempotency, dead-letter on empty input).

## Extension points

The architecture is ports-and-adapters; the common extensions are drop-ins:

- **New document source**: implement `ports.document_source.DocumentSource`. Examples: `S3Source`, `KafkaSource`, `HttpPollingSource`. Register it in `cli.py`.
- **New format parser**: implement `ports.document_parser.DocumentParser`, declare `supported_formats`, register it in the `ParserRegistry` in `cli._build_context`.
- **New LLM backend**: implement `ports.llm_client.LLMClient.structured`. Bring your own retry / structured-output strategy.
- **Graph store**: implement `ports.graph_repository.GraphRepository`. Upserts must be idempotent on `node_id` and `(source_id, type, target_id)`.
- **Embeddings**: `ports.embedder.Embedder` is defined; the synthesis stage currently does name-based dedup, but a semantic-dedup variant would consume embeddings from this port.
- **Cross-corpus edges**: dashed-arrow edges that "emerge across sources" (`APPLIES_TO`, `UNDERLIES`, cross-document `SUPPORTS`/`CONTRADICTS` between theories) are intentionally not produced by the ingestion pipeline. They are corpus-level computations; add a separate job that reads from `GraphRepository` and writes new edges back.

## Determinism and idempotency

- Node IDs are `sha256(tenant_id || node_type || canonical_name)[:16]`. The same canonical entity produces the same `node_id` across runs and across documents.
- Chunk IDs are `sha256(document_id || "chunk" || index)[:16]`. The same chunk in the same document is always the same chunk.
- Source `document_id` includes the content hash, so a content change produces a new source node (i.e. versions are distinct).
- Re-ingesting an unchanged document is a graph-no-op (upsert on the same IDs).

The orchestrator test `test_ingest_one_is_idempotent` pins this behavior.

## Open items / TODO

- **PDF OCR**: scanned PDFs produce empty text and fail in preprocess. Add a parser variant that calls an OCR service.
- **Cross-corpus job**: see "Extension points" above. The graph mapper produces the within-document cross-entity edges (`BELONGS_TO`, `HAS_INTEREST` to topics present in the same doc, `SUPPORTS` between conclusions and theories in the same doc). True cross-document inference is unwritten.
- **Additional embedder backends**: `OllamaEmbedder` is implemented; an `AnthropicEmbedder` (or other hosted provider) would follow the same pattern.
- **OpenTelemetry**: structured logs are wired; tracing is not. The orchestrator's `bind_contextvars` call is where you'd add span creation.
- **`AnthropicLLMClient`**: uses tool-use to enforce structured output. Untested end-to-end (the suite uses `FakeLLMClient`); verify against your Anthropic SDK version before relying on it.
