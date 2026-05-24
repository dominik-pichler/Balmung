import pytest

from distillation.adapters.llm.fake import FakeLLMClient
from distillation.domain.distillate import LensOutput, TopicMention
from distillation.domain.document import Chunk
from distillation.pipeline.lenses.topic import TopicLens, TopicResponse, _TopicItem


@pytest.fixture
def chunks() -> list[Chunk]:
    return [
        Chunk(
            chunk_id=f"chunk-{i}",
            document_id="doc-1",
            index=i,
            text=text,
            start_char=0,
            end_char=len(text),
        )
        for i, text in enumerate(
            [
                "Machine Learning enables Knowledge Graphs.",
                "Retrieval Augmented Generation builds on embeddings.",
            ]
        )
    ]


async def test_lens_returns_empty_for_no_chunks(fake_llm: FakeLLMClient):
    lens = TopicLens(fake_llm)
    out = await lens.apply([])
    assert out == LensOutput(lens_name="topic", items=[])


async def test_lens_returns_items_with_provenance(
    fake_llm: FakeLLMClient, chunks: list[Chunk]
):
    fake_llm.set_response(
        TopicResponse,
        TopicResponse(
            topics=[
                _TopicItem(name="Knowledge Graphs", theme="AI"),
                _TopicItem(name="RAG", theme="AI"),
            ]
        ),
    )

    lens = TopicLens(fake_llm)
    out = await lens.apply(chunks)

    assert out.error is None
    assert out.lens_name == "topic"
    assert len(out.items) == 2
    assert all(isinstance(i, TopicMention) for i in out.items)
    # Provenance is stamped onto every item from the chunks we passed.
    chunk_ids = {c.chunk_id for c in chunks}
    for item in out.items:
        assert set(item.provenance_chunk_ids) == chunk_ids


async def test_lens_captures_llm_error_as_lens_error(
    fake_llm: FakeLLMClient, chunks: list[Chunk]
):
    class Boom(FakeLLMClient):
        async def structured(self, *, system, user, response_model):
            from distillation.ports.llm_client import LLMError

            raise LLMError("boom")

    lens = TopicLens(Boom())
    out = await lens.apply(chunks)
    assert out.items == []
    assert out.error == "boom"
