"""Plain-text parser."""

from __future__ import annotations

import re
import unicodedata

from ...domain.document import DocumentFormat, SourceDocument
from ...ports.document_parser import DocumentParser

_WS_RE = re.compile(r"[ \t]+")
_NEWLINES_RE = re.compile(r"\n{3,}")


class PlainTextParser(DocumentParser):
    """Decodes UTF-8 bytes and collapses excessive whitespace."""

    @property
    def supported_formats(self) -> set[DocumentFormat]:
        return {DocumentFormat.TEXT}

    def parse(self, document: SourceDocument) -> str:
        text = document.raw_bytes.decode("utf-8", errors="replace")
        text = unicodedata.normalize("NFKC", text)
        text = _WS_RE.sub(" ", text)
        text = _NEWLINES_RE.sub("\n\n", text)
        return text.strip()
