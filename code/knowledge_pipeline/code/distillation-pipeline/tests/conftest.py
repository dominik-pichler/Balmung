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


from distillation.adapters.chunkers.sliding_window import SlidingWindowChunker
from distillation.adapters.graph.in_memory import InMemoryGraphRepository
from distillation.adapters.llm.fake import FakeLLMClient
from distillation.adapters.parsers.markdown import MarkdownParser
from distillation.adapters.parsers.plaintext import PlainTextParser
from distillation.domain.document import (
    DocumentFormat,
    DocumentMetadata,
    SourceDocument,
)
from distillation.mapping.domain_writer import DomainWriter
from distillation.mapping.epistemic_writer import EpistemicWriter
from distillation.mapping.provenance_writer import ProvenanceWriter
from distillation.pipeline.context import PipelineContext
from distillation.pipeline.lenses import (
    AssumptionLens,
    AuthorLens,
    ClaimLens,
    DomainLens,
    EvidenceLens,
    ProvenanceLens,
)
from distillation.pipeline.stages.distill import DistillStage
from distillation.pipeline.stages.persist import PersistStage
from distillation.pipeline.stages.preprocess import PreprocessStage
from distillation.pipeline.stages.synthesize import SynthesizeStage
from distillation.ports.document_parser import ParserRegistry


@pytest.fixture
def fake_llm() -> FakeLLMClient:
    return FakeLLMClient()


@pytest.fixture
def in_memory_graph() -> InMemoryGraphRepository:
    return InMemoryGraphRepository()


@pytest.fixture
def sample_document() -> SourceDocument:
    body = (
        b"By Alice Smith, MIT.\n\n"
        b"We propose the Lens Theory and conclude that distillation supports it. "
        b"Method: lens-based extraction.\n"
    )
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
        DomainLens(fake_llm),
        AssumptionLens(fake_llm),
        ClaimLens(fake_llm),
        EvidenceLens(fake_llm),
        AuthorLens(fake_llm),
        ProvenanceLens(fake_llm),
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
