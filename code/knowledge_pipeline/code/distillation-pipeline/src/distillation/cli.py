"""Typer-based CLI entrypoint.

Wires concrete adapters onto the abstract ports based on ``Settings`` and
runs the pipeline against a list of local files. The CLI is the only place
that knows about specific adapter implementations — keeping the rest of the
codebase implementation-agnostic.

Run ``distill ingest path/to/doc.txt`` after installing the package.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import structlog
import typer

from .adapters.chunkers.sliding_window import SlidingWindowChunker
from .adapters.dead_letter.filesystem import FilesystemDeadLetterStore
from .adapters.embedders.fake import FakeEmbedder
from .adapters.graph.in_memory import InMemoryGraphRepository
from .adapters.llm.fake import FakeLLMClient
from .adapters.parsers.markdown import MarkdownParser
from .adapters.parsers.plaintext import PlainTextParser
from .adapters.sources.local_file import LocalFileSource
from .config import Settings, get_settings
from .logging_setup import configure_logging
from .mapping.graph_mapper import GraphMapper
from .pipeline.context import PipelineContext
from .pipeline.lenses.assumption import AssumptionLens
from .pipeline.lenses.author import AuthorLens
from .pipeline.lenses.conclusion import ConclusionLens
from .pipeline.lenses.methodology import MethodologyLens
from .pipeline.lenses.theory import TheoryLens
from .pipeline.lenses.topic import TopicLens
from .pipeline.orchestrator import IngestionPipeline
from .pipeline.stages.distill import DistillStage
from .pipeline.stages.persist import PersistStage
from .pipeline.stages.preprocess import PreprocessStage
from .pipeline.stages.synthesize import SynthesizeStage
from .ports.document_parser import ParserRegistry
from .ports.embedder import Embedder
from .ports.graph_repository import GraphRepository
from .ports.llm_client import LLMClient
from .retrieval import GraphRetriever

app = typer.Typer(
    help="Document → Distillate → Knowledge Graph pipeline",
    # Force subcommand mode so `distill ingest ...` is the invocation,
    # even when there is currently only one command registered.
    no_args_is_help=True,
)
log = structlog.get_logger(__name__)


def _build_llm(settings: Settings) -> LLMClient:
    if settings.llm_provider == "anthropic":
        from .adapters.llm.anthropic import AnthropicLLMClient

        return AnthropicLLMClient(
            api_key=settings.anthropic_api_key, model=settings.llm_model
        )
    if settings.llm_provider == "ollama":
        from .adapters.llm.ollama import OllamaLLMClient

        return OllamaLLMClient(
            model=settings.llm_model, base_url=settings.ollama_base_url
        )
    return FakeLLMClient()


def _build_embedder(settings: Settings) -> Embedder:
    if settings.embedder_provider == "ollama":
        from .adapters.embedders.ollama import OllamaEmbedder

        return OllamaEmbedder(
            model=settings.embedder_model,
            base_url=settings.ollama_base_url,
        )
    return FakeEmbedder()


def _build_graph_repo(settings: Settings) -> GraphRepository:
    if settings.graph_backend == "neo4j":
        from .adapters.graph.neo4j import Neo4jGraphRepository

        return Neo4jGraphRepository(
            uri=settings.neo4j_uri,
            user=settings.neo4j_user,
            password=settings.neo4j_password,
        )
    return InMemoryGraphRepository()


def _build_context(settings: Settings) -> PipelineContext:
    llm = _build_llm(settings)

    parsers = ParserRegistry([PlainTextParser(), MarkdownParser()])
    # PDF parser registered lazily — only if pypdf is installed.
    try:
        from .adapters.parsers.pdf import PdfParser

        parsers = ParserRegistry(
            [PlainTextParser(), MarkdownParser(), PdfParser()]
        )
    except ImportError:  # pragma: no cover
        log.warning("pdf_parser.unavailable")

    chunker = SlidingWindowChunker(
        max_tokens=settings.chunk_token_size,
        overlap_tokens=settings.chunk_token_overlap,
    )
    lenses = [
        TopicLens(llm),
        AuthorLens(llm),
        AssumptionLens(llm),
        TheoryLens(llm),
        ConclusionLens(llm),
        MethodologyLens(llm),
    ]
    graph_repo = _build_graph_repo(settings)
    mapper = GraphMapper(tenant_id=settings.tenant_id)
    dead_letter = FilesystemDeadLetterStore(settings.dead_letter_dir)

    return PipelineContext(
        preprocess=PreprocessStage(parsers, chunker),
        distill=DistillStage(lenses, max_concurrency=settings.llm_max_concurrency),
        synthesize=SynthesizeStage(),
        persist=PersistStage(mapper, graph_repo),
        graph_repository=graph_repo,
        dead_letter=dead_letter,
    )


@app.command()
def ingest(
    paths: list[Path] = typer.Argument(..., help="Files to ingest"),
) -> None:
    """Ingest one or more documents and print a summary."""
    settings = get_settings()
    configure_logging(settings.log_level)

    async def _run() -> None:
        context = _build_context(settings)
        source = LocalFileSource(paths=list(paths), tenant_id=settings.tenant_id)
        pipeline = IngestionPipeline(context)
        results = await pipeline.ingest_all(source)

        total_nodes = await context.graph_repository.count_nodes()
        total_edges = await context.graph_repository.count_edges()
        try:
            typer.echo(
                f"Ingested {len(results)} document(s). "
                f"Graph now has {total_nodes} node(s), {total_edges} edge(s)."
            )
            for r in results:
                typer.echo(
                    f"  - {r.document_id}: "
                    f"+{r.nodes_written} nodes / +{r.edges_written} edges"
                    f"{' (failed lenses: ' + ','.join(r.failed_lenses) + ')' if r.failed_lenses else ''}"
                )
        finally:
            await context.graph_repository.close()

    asyncio.run(_run())


_GRAPH_SYSTEM_PROMPT = """\
You are a knowledge-graph assistant. The user has ingested documents into a \
knowledge graph. The subgraph below was retrieved by semantic similarity to \
the user's question — it contains the most relevant nodes and their direct \
neighbours (JSON format).

Node types: Source, Author, Affiliation, Topic, Theme, Assumption, Theory, \
Conclusion, Methodology.

Edge types (Source → entity): AUTHORED_BY, DISCUSSES, USES, BUILDS, CONCLUDES, \
ASSUMES. Edge types (cross-entity): IS_AT, HAS_INTEREST, BELONGS_TO, SUPPORTS, \
CONTRADICTS, UNDERLIES, APPLIES_TO, CITES.

Answer the user's question based solely on the subgraph data. Be concise. If \
the subgraph does not contain enough information, say so.

--- SUBGRAPH ---
{graph_json}
--- END SUBGRAPH ---
"""


@app.command()
def chat(
    prompt: str | None = typer.Argument(
        None, help="Question to ask. Omit for interactive REPL."
    ),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Seed nodes for retrieval."),
) -> None:
    """Query the knowledge graph in plain English via an LLM."""
    import json

    settings = get_settings()
    configure_logging(settings.log_level)

    repo = _build_graph_repo(settings)
    embedder = _build_embedder(settings)
    retriever = GraphRetriever(repo, embedder)
    llm = _build_llm(settings)

    async def _ask(question: str) -> str:
        nodes, edges = await retriever.retrieve(question, k=top_k)
        graph_json = json.dumps(
            {
                "nodes": [n.model_dump(mode="json") for n in nodes],
                "edges": [e.model_dump(mode="json") for e in edges],
            },
            ensure_ascii=False,
        )
        system = _GRAPH_SYSTEM_PROMPT.format(graph_json=graph_json)
        return await llm.chat(system=system, user=question)

    async def _close() -> None:
        await repo.close()

    if prompt:
        answer = asyncio.run(_ask(prompt))
        asyncio.run(_close())
        typer.echo(answer)
        return

    # Interactive REPL
    typer.echo("Knowledge graph chat (type 'exit' or Ctrl-C to quit)\n")
    try:
        while True:
            try:
                question = typer.prompt("You")
            except (KeyboardInterrupt, EOFError):
                break
            if question.strip().lower() in {"exit", "quit"}:
                break
            answer = asyncio.run(_ask(question))
            typer.echo(f"\nAssistant: {answer}\n")
    finally:
        asyncio.run(_close())


@app.command()
def export(
    output: Path = typer.Option(
        Path("export/graph_snapshot.json"),
        "--output",
        "-o",
        help="Destination JSON file",
    ),
) -> None:
    """Export every node and edge to a JSON snapshot for version control."""
    settings = get_settings()
    configure_logging(settings.log_level)

    async def _run() -> None:
        repo = _build_graph_repo(settings)
        try:
            nodes = await repo.all_nodes()
            edges = await repo.all_edges()
        finally:
            await repo.close()

        output.parent.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "nodes": [n.model_dump(mode="json") for n in nodes],
            "edges": [e.model_dump(mode="json") for e in edges],
        }
        output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))
        typer.echo(
            f"Exported {len(nodes)} node(s) and {len(edges)} edge(s) → {output}"
        )

    asyncio.run(_run())


@app.command()
def version() -> None:
    """Print the package version."""
    from importlib.metadata import PackageNotFoundError, version as _v

    try:
        typer.echo(_v("distillation-pipeline"))
    except PackageNotFoundError:
        typer.echo("0.1.0 (development)")


if __name__ == "__main__":
    app()
