"""A failing lens must be captured (non-fatal) and reported, per the
'ontology over accuracy' failure philosophy."""

from distillation.adapters.chunkers.sliding_window import SlidingWindowChunker
from distillation.adapters.dead_letter.filesystem import FilesystemDeadLetterStore
from distillation.adapters.graph.in_memory import InMemoryGraphRepository
from distillation.adapters.llm.fake import FakeLLMClient
from distillation.adapters.parsers.plaintext import PlainTextParser
from distillation.domain.document import DocumentFormat, DocumentMetadata, SourceDocument
from distillation.mapping.domain_writer import DomainWriter
from distillation.mapping.epistemic_writer import EpistemicWriter
from distillation.mapping.provenance_writer import ProvenanceWriter
from distillation.pipeline.context import PipelineContext
from distillation.pipeline.lenses import AuthorLens, ClaimLens, DomainLens
from distillation.pipeline.orchestrator import IngestionPipeline
from distillation.pipeline.stages.distill import DistillStage
from distillation.pipeline.stages.persist import PersistStage
from distillation.pipeline.stages.preprocess import PreprocessStage
from distillation.pipeline.stages.synthesize import SynthesizeStage
from distillation.ports.document_parser import ParserRegistry
from distillation.ports.llm_client import LLMError


class _BoomLLM(FakeLLMClient):
    async def structured(self, *, system, user, response_model):  # type: ignore[override]
        raise LLMError("boom")


def _context(tmp_path) -> PipelineContext:
    good = FakeLLMClient()
    dw = DomainWriter()
    return PipelineContext(
        preprocess=PreprocessStage(
            ParserRegistry([PlainTextParser()]),
            SlidingWindowChunker(max_tokens=200, overlap_tokens=20),
        ),
        # DomainLens fails; the others succeed.
        distill=DistillStage(
            [DomainLens(_BoomLLM()), ClaimLens(good), AuthorLens(good)]
        ),
        synthesize=SynthesizeStage(),
        persist=PersistStage(dw, EpistemicWriter(dw), ProvenanceWriter(), InMemoryGraphRepository()),
        graph_repository=InMemoryGraphRepository(),
        dead_letter=FilesystemDeadLetterStore(tmp_path / "dlq"),
    )


async def test_failed_lens_is_non_fatal_and_reported(tmp_path):
    ctx = _context(tmp_path)
    doc = SourceDocument(
        metadata=DocumentMetadata(tenant_id="t", source_id="p.txt", uri="file:///p.txt"),
        format=DocumentFormat.TEXT,
        raw_bytes=b"By Alice Smith. We propose a Theory and conclude it works.",
    )
    result = await IngestionPipeline(ctx).ingest_one(doc)

    assert result is not None  # one lens failing does not abort the document
    assert "domain" in result.failed_lenses
    assert "claim" not in result.failed_lenses
    # The surviving lenses still produced nodes.
    assert result.nodes_written > 0
    # No dead-letter file: a per-lens failure is not a document failure.
    assert not list((tmp_path / "dlq").iterdir())
