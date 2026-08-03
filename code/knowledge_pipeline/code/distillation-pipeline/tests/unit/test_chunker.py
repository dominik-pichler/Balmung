import pytest

from distillation.adapters.chunkers.sliding_window import SlidingWindowChunker


def test_chunker_empty_text_returns_no_chunks():
    chunker = SlidingWindowChunker(max_tokens=100, overlap_tokens=10)
    assert chunker.chunk("doc-1", "   ") == []


def test_chunker_short_text_produces_one_chunk():
    chunker = SlidingWindowChunker(max_tokens=100, overlap_tokens=10)
    chunks = chunker.chunk("doc-1", "Hello world. This is a short paragraph.")
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].document_id == "doc-1"
    assert chunks[0].text.startswith("Hello world")


def test_chunker_splits_long_text_into_multiple_chunks():
    chunker = SlidingWindowChunker(max_tokens=20, overlap_tokens=2)  # ~80 chars
    paragraphs = ["This is paragraph " + str(i) + "." for i in range(20)]
    text = "\n\n".join(paragraphs)

    chunks = chunker.chunk("doc-1", text)

    assert len(chunks) >= 2
    # IDs are deterministic and unique per index.
    assert len({c.chunk_id for c in chunks}) == len(chunks)
    # Indices are sequential.
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunker_invalid_params_raise():
    with pytest.raises(ValueError):
        SlidingWindowChunker(max_tokens=0, overlap_tokens=0)
    with pytest.raises(ValueError):
        SlidingWindowChunker(max_tokens=10, overlap_tokens=10)


def test_chunker_offsets_slice_back_to_chunk_text():
    """``text[chunk.start_char:chunk.end_char]`` must equal ``chunk.text``.

    This is the provenance invariant: offsets are how downstream consumers
    map a graph element back to the exact source span.
    """
    chunker = SlidingWindowChunker(max_tokens=20, overlap_tokens=2)
    text = "\n\n".join(
        f"Paragraph number {i} has some content." for i in range(20)
    )
    chunks = chunker.chunk("doc-1", text)
    assert len(chunks) >= 2
    for c in chunks:
        assert text[c.start_char : c.end_char] == c.text


def test_chunker_offsets_hold_with_zero_overlap():
    chunker = SlidingWindowChunker(max_tokens=20, overlap_tokens=0)
    text = "\n\n".join(
        f"Paragraph number {i} has some content." for i in range(20)
    )
    chunks = chunker.chunk("doc-1", text)
    for c in chunks:
        assert text[c.start_char : c.end_char] == c.text


def test_chunker_handles_oversized_sentence():
    """A single sentence longer than max_chars is hard-cut, and offsets stay valid."""
    chunker = SlidingWindowChunker(max_tokens=10, overlap_tokens=0)  # 40 chars
    text = "x" * 200  # one giant 'sentence' with no breaks
    chunks = chunker.chunk("doc-1", text)
    assert len(chunks) >= 4
    # Every chunk's text is exactly what its offsets point to.
    for c in chunks:
        assert text[c.start_char : c.end_char] == c.text
    # And concatenating them in order reproduces the source (since overlap=0).
    assert "".join(c.text for c in chunks) == text
