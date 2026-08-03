"""Port: format-specific text extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.document import DocumentFormat, SourceDocument


class DocumentParser(ABC):
    """Extracts UTF-8 text from raw document bytes."""

    @property
    @abstractmethod
    def supported_formats(self) -> set[DocumentFormat]:
        """Formats this parser can handle."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, document: SourceDocument) -> str:
        """Return normalized UTF-8 text.

        Implementations must NOT chunk — that is the chunker's job. They
        should, however, normalize whitespace and unicode so downstream
        stages see a clean string.
        """
        raise NotImplementedError


class ParserRegistry:
    """Dispatches ``SourceDocument`` to the right ``DocumentParser``.

    Concrete adapters register themselves at construction time; the pipeline
    only depends on this registry.
    """

    def __init__(self, parsers: list[DocumentParser]) -> None:
        self._by_format: dict[DocumentFormat, DocumentParser] = {}
        for parser in parsers:
            for fmt in parser.supported_formats:
                self._by_format[fmt] = parser

    def parse(self, document: SourceDocument) -> str:
        parser = self._by_format.get(document.format)
        if parser is None:
            raise ValueError(
                f"No parser registered for format={document.format.value!r}"
            )
        return parser.parse(document)
