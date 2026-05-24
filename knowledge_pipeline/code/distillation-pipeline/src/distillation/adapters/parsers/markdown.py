"""Markdown parser.

Markdown is preserved verbatim — the LLM benefits from the structural cues
(``#`` headers, lists) when reasoning about authors, topics, and conclusions.
We only normalize unicode and trim trailing whitespace per line.
"""

from __future__ import annotations

import unicodedata

from ...domain.document import DocumentFormat, SourceDocument
from ...ports.document_parser import DocumentParser


class MarkdownParser(DocumentParser):
    @property
    def supported_formats(self) -> set[DocumentFormat]:
        return {DocumentFormat.MARKDOWN}

    def parse(self, document: SourceDocument) -> str:
        text = document.raw_bytes.decode("utf-8", errors="replace")
        text = unicodedata.normalize("NFKC", text)
        # Trim trailing whitespace on each line; preserve blank lines.
        lines = [line.rstrip() for line in text.splitlines()]
        return "\n".join(lines).strip()
