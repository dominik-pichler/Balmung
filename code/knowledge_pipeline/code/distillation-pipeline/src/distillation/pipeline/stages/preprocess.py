"""Preprocessing stage: parse + chunk.

Input:  ``SourceDocument``
Output: ``PreprocessedDocument`` (document_id, full text, list of chunks)
"""

from __future__ import annotations

import structlog
from pydantic import BaseModel

from ...domain.document import Chunk, SourceDocument
from ...ports.chunker import Chunker
from ...ports.document_parser import ParserRegistry

log = structlog.get_logger(__name__)


class PreprocessedDocument(BaseModel):
    document_id: str
    text: str
    chunks: list[Chunk]


class PreprocessStage:
    """Parse the raw bytes and split the text into chunks."""

    def __init__(self, parsers: ParserRegistry, chunker: Chunker) -> None:
        self._parsers = parsers
        self._chunker = chunker

    async def run(self, document: SourceDocument) -> PreprocessedDocument:
        text = self._parsers.parse(document)
        if not text.strip():
            raise ValueError(
                f"Parser produced empty text for document_id={document.document_id}"
            )

        chunks = self._chunker.chunk(document.document_id, text)
        if not chunks:
            raise ValueError(
                f"Chunker produced no chunks for document_id={document.document_id}"
            )

        log.info(
            "preprocess.completed",
            document_id=document.document_id,
            text_length=len(text),
            chunk_count=len(chunks),
        )
        return PreprocessedDocument(
            document_id=document.document_id, text=text, chunks=chunks
        )
