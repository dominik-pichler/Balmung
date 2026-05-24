"""PDF parser backed by ``pypdf``.

Page text is joined with form-feed (``\\f``) so a downstream chunker can
respect page boundaries if it wants to. For OCR-only PDFs the output will
be empty and the caller should treat that as a parse failure.
"""

from __future__ import annotations

import io
import unicodedata

from ...domain.document import DocumentFormat, SourceDocument
from ...ports.document_parser import DocumentParser


class PdfParser(DocumentParser):
    @property
    def supported_formats(self) -> set[DocumentFormat]:
        return {DocumentFormat.PDF}

    def parse(self, document: SourceDocument) -> str:
        # Lazy import so test environments without pypdf still load this module.
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(document.raw_bytes))
        pages: list[str] = []
        for page in reader.pages:
            extracted = page.extract_text() or ""
            pages.append(unicodedata.normalize("NFKC", extracted).strip())
        return "\f".join(pages).strip()
