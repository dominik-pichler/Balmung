"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make src/ importable without installing the package.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from distillation.adapters.chunkers.sliding_window import SlidingWindowChunker  # noqa: E402
from distillation.adapters.graph.in_memory import InMemoryGraphRepository  # noqa: E402
from distillation.adapters.llm.fake import FakeLLMClient  # noqa: E402
from distillation.adapters.parsers.markdown import MarkdownParser  # noqa: E402
from distillation.adapters.parsers.plaintext import PlainTextParser  # noqa: E402
from distillation.domain.document import DocumentFormat, DocumentMetadata, SourceDocument  # noqa: E402
from distillation.mapping.domain_writer import DomainWriter  # noqa: E402
from distillation.mapping.epistemic_writer import EpistemicWriter  # noqa: E402
from distillation.mapping.provenance_writer import ProvenanceWriter  # noqa: E402
from distillation.pipeline.context import PipelineContext  # noqa: E402
from distillation.pipeline.lenses.assumption import AssumptionLens  # noqa: E402
from distillation.pipeline.lenses.author import AuthorLens  # noqa: E402
from distillation.pipeline.lenses.claim_lens import ClaimLens  # noqa: E402
from distillation.pipeline.stages.distill import DistillStage  # noqa: E402
from distillation.pipeline.stages.persist import PersistStage  # noqa: E402
from distillation.pipeline.stages.preprocess import PreprocessStage  # noqa: E402
from distillation.pipeline.stages.synthesize import SynthesizeStage  # noqa: E402
from distillation.ports.document_parser import ParserRegistry  # noqa: E402


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def in_memory_graph() -> InMemoryGraphRepository:
    return InMemoryGraphRepository()


@pytest.fixture
def sample_document() -> SourceDocument:
    body = (
        "By Alice Smith, MIT.\n\n"
        "We propose the Lens Theory and conclude that distillation supports it. "
        "Method: lens-based extraction.\n"
    ).encode("utf-8")
    return SourceDocument(
        metadata=DocumentMetadata(
            tenant_id="test", source_id="sample.txt", uri="file:///sample.txt"
        ),
        format=DocumentFormat.TEXT,
        raw_bytes=body,
    )


@pytest.fixture
def pipeline_context(
    fake_llm: FakeLLMClient,
    in_memory_graph: InMemoryGraphRepository,
    tmp_path,
) -> PipelineContext:
    from distillation.adapters.dead_letter.filesystem import FilesystemDeadLetterStore

    parsers = ParserRegistry([PlainTextParser(), MarkdownParser()])
    chunker = SlidingWindowChunker(max_tokens=200, overlap_tokens=20)
    lenses = [
        AuthorLens(fake_llm),
        AssumptionLens(fake_llm),
        ClaimLens(fake_llm),
    ]
    domain_writer = DomainWriter()
    epistemic_writer = EpistemicWriter(domain_writer)
    provenance_writer = ProvenanceWriter()
    return PipelineContext(
        preprocess=PreprocessStage(parsers, chunker),
        distill=DistillStage(lenses),
        synthesize=SynthesizeStage(),
        persist=PersistStage(domain_writer, epistemic_writer, provenance_writer, in_memory_graph),
        graph_repository=in_memory_graph,
        dead_letter=FilesystemDeadLetterStore(tmp_path / "dlq"),
    )
