"""Sliding-window chunker with token estimation.

We avoid pulling in a full tokenizer here — a 4-chars-per-token heuristic is
good enough for chunk sizing. Adapters that need exact token accounting can
implement their own ``Chunker``.

Chunk boundaries are placed at paragraph breaks where possible, falling back
to sentence boundaries, then to hard cuts. The implementation tracks
``(start, end)`` character offsets into the original text throughout, so the
``start_char`` / ``end_char`` on each emitted chunk slice the source string
back to the chunk's text exactly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ...domain.document import Chunk
from ...domain.ids import deterministic_id
from ...ports.chunker import Chunker

_CHARS_PER_TOKEN = 4
_PARA_RE = re.compile(r"\n\s*\n")
_SENT_RE = re.compile(r"(?<=[.!?])\s+")


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


@dataclass(slots=True)
class _Segment:
    """A paragraph/sentence/hard-cut span identified by absolute offsets."""

    start: int
    end: int


class SlidingWindowChunker(Chunker):
    """Greedy chunker targeting ``max_tokens`` per chunk with overlap.

    The algorithm:
      1. Identify segments (paragraphs first; oversized paragraphs are
         re-split by sentence; oversized sentences are hard-cut by char).
         Each segment is recorded as an absolute ``(start, end)`` range
         within the input text.
      2. Walk segments in order. Maintain a current chunk window
         ``[window_start, window_end)``.
      3. When appending the next segment would exceed ``max_chars``, emit
         the current chunk and start a new one whose ``window_start`` is
         ``max(0, window_end - overlap_chars)`` — guaranteeing offsets
         remain consistent with the source text.
    """

    def __init__(self, max_tokens: int = 800, overlap_tokens: int = 100) -> None:
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")
        if overlap_tokens < 0 or overlap_tokens >= max_tokens:
            raise ValueError("overlap_tokens must be in [0, max_tokens)")
        self._max_tokens = max_tokens
        self._overlap_tokens = overlap_tokens
        self._max_chars = max_tokens * _CHARS_PER_TOKEN
        self._overlap_chars = overlap_tokens * _CHARS_PER_TOKEN

    def chunk(self, document_id: str, text: str) -> list[Chunk]:
        if not text.strip():
            return []

        segments = list(self._segments(text))
        if not segments:
            return []

        chunks: list[Chunk] = []
        window_start = segments[0].start
        window_end = segments[0].start  # empty until we accept the first seg

        for seg in segments:
            current_len = window_end - window_start

            # Always accept the first non-empty segment of a fresh window.
            if current_len == 0:
                window_start = seg.start
                window_end = seg.end
                continue

            # Fits: extend the window to the end of this segment.
            if (seg.end - window_start) <= self._max_chars:
                window_end = seg.end
                continue

            # Doesn't fit: emit current window, start a new one with overlap.
            chunks.append(
                self._make_chunk(document_id, len(chunks), text, window_start, window_end)
            )
            new_start = max(window_end - self._overlap_chars, 0)
            window_start = new_start
            window_end = max(seg.end, new_start)
            # Guard: if a single segment is large enough that the new
            # window (overlap + segment) exceeds max_chars, hard-cut.
            while (window_end - window_start) > self._max_chars:
                cut_end = window_start + self._max_chars
                chunks.append(
                    self._make_chunk(document_id, len(chunks), text, window_start, cut_end)
                )
                window_start = max(cut_end - self._overlap_chars, 0)

        if window_end > window_start:
            chunks.append(
                self._make_chunk(document_id, len(chunks), text, window_start, window_end)
            )

        return chunks

    # --- internals --------------------------------------------------------

    def _segments(self, text: str):
        """Yield non-empty ``_Segment`` spans by paragraph→sentence→hard-cut."""
        for para_start, para_end in self._iter_paragraphs(text):
            paragraph = text[para_start:para_end]
            if not paragraph.strip():
                continue
            if (para_end - para_start) <= self._max_chars:
                yield _Segment(para_start, para_end)
                continue
            yield from self._sentence_segments(text, para_start, para_end)

    def _iter_paragraphs(self, text: str):
        """Yield ``(start, end)`` for each paragraph block."""
        start = 0
        for m in _PARA_RE.finditer(text):
            yield (start, m.start())
            start = m.end()
        if start < len(text):
            yield (start, len(text))

    def _sentence_segments(self, text: str, para_start: int, para_end: int):
        sub = text[para_start:para_end]
        sub_offset = para_start
        breakpoints = [m.start() for m in _SENT_RE.finditer(sub)]
        bounds = [0, *breakpoints, len(sub)]
        for i in range(len(bounds) - 1):
            s_local = bounds[i]
            e_local = bounds[i + 1]
            while s_local < e_local and sub[s_local].isspace():
                s_local += 1
            if s_local >= e_local:
                continue
            s_abs = sub_offset + s_local
            e_abs = sub_offset + e_local
            if (e_abs - s_abs) <= self._max_chars:
                yield _Segment(s_abs, e_abs)
            else:
                cur = s_abs
                while cur < e_abs:
                    cut = min(cur + self._max_chars, e_abs)
                    yield _Segment(cur, cut)
                    cur = cut

    def _make_chunk(
        self,
        document_id: str,
        index: int,
        text: str,
        start_char: int,
        end_char: int,
    ) -> Chunk:
        chunk_text = text[start_char:end_char]
        return Chunk(
            chunk_id=deterministic_id(document_id, "chunk", str(index)),
            document_id=document_id,
            index=index,
            text=chunk_text,
            start_char=start_char,
            end_char=end_char,
            token_estimate=_estimate_tokens(chunk_text),
        )
