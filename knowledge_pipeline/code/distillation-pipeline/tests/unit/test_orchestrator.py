from distillation.adapters.graph.in_memory import InMemoryGraphRepository
from distillation.adapters.sources.local_file import LocalFileSource
from distillation.domain.document import SourceDocument
from distillation.pipeline.context import PipelineContext
from distillation.pipeline.orchestrator import IngestionPipeline


async def test_ingest_one_produces_nodes_and_edges(
    pipeline_context: PipelineContext, sample_document: SourceDocument
):
    pipeline = IngestionPipeline(pipeline_context)
    result = await pipeline.ingest_one(sample_document)

    assert result is not None
    assert result.document_id == sample_document.document_id
    assert result.nodes_written > 0
    assert result.edges_written > 0


async def test_ingest_one_is_idempotent(
    pipeline_context: PipelineContext, sample_document: SourceDocument
):
    pipeline = IngestionPipeline(pipeline_context)
    await pipeline.ingest_one(sample_document)
    nodes_after_first = await pipeline_context.graph_repository.count_nodes()
    edges_after_first = await pipeline_context.graph_repository.count_edges()

    await pipeline.ingest_one(sample_document)
    assert await pipeline_context.graph_repository.count_nodes() == nodes_after_first
    assert await pipeline_context.graph_repository.count_edges() == edges_after_first


async def test_ingest_one_dead_letters_on_empty_text(
    pipeline_context: PipelineContext, tmp_path
):
    # An empty file fails the preprocess stage and is dead-lettered.
    empty = tmp_path / "empty.txt"
    empty.write_text("")
    source = LocalFileSource(paths=[empty], tenant_id="test")
    pipeline = IngestionPipeline(pipeline_context)

    results = await pipeline.ingest_all(source)
    assert results == []
    # DLQ directory has one file
    dlq_files = list((tmp_path / "dlq").iterdir())
    assert len(dlq_files) == 1
    assert "preprocess" in dlq_files[0].name


async def test_pipeline_writes_through_local_file_source(
    pipeline_context: PipelineContext, tmp_path
):
    f = tmp_path / "doc.txt"
    f.write_text("By Alice Smith, MIT. We build a Theory and conclude X.")
    source = LocalFileSource(paths=[f], tenant_id="test")
    pipeline = IngestionPipeline(pipeline_context)

    results = await pipeline.ingest_all(source)
    assert len(results) == 1
    assert isinstance(pipeline_context.graph_repository, InMemoryGraphRepository)
