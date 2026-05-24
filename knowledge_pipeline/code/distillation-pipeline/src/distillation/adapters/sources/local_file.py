"""Local-filesystem source adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from ...domain.document import DocumentFormat, DocumentMetadata, SourceDocument
from ...ports.document_source import DocumentSource

_EXT_TO_FORMAT: dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".html": DocumentFormat.HTML,
    ".htm": DocumentFormat.HTML,
    ".md": DocumentFormat.MARKDOWN,
    ".markdown": DocumentFormat.MARKDOWN,
    ".txt": DocumentFormat.TEXT,
    ".docx": DocumentFormat.DOCX,
}


class LocalFileSource(DocumentSource):
    """Reads documents from a list of local paths.

    Format is inferred from the file extension. Unknown extensions default
    to ``DocumentFormat.TEXT`` — the parser stage will fail loudly if that's
    wrong, which is the right behavior for ambiguous input.
    """

    def __init__(self, paths: list[Path], tenant_id: str) -> None:
        self._paths = paths
        self._tenant_id = tenant_id

    async def stream(self) -> AsyncIterator[SourceDocument]:
        for path in self._paths:
            yield self._load(path)

    def _load(self, path: Path) -> SourceDocument:
        fmt = _EXT_TO_FORMAT.get(path.suffix.lower(), DocumentFormat.TEXT)
        raw = path.read_bytes()
        meta = DocumentMetadata(
            tenant_id=self._tenant_id,
            source_id=path.name,
            uri=path.resolve().as_uri(),
        )
        return SourceDocument(metadata=meta, format=fmt, raw_bytes=raw)
