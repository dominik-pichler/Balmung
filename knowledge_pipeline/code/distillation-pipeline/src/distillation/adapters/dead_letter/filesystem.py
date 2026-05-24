"""Filesystem dead-letter store.

One JSON file per failure, named ``<document_id>__<stage>__<utc>.json``.
The raw bytes are NOT persisted — only metadata + error context — so the
store stays compact and PII-light by default.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ...domain.document import SourceDocument
from ...ports.dead_letter_store import DeadLetterStore


class FilesystemDeadLetterStore(DeadLetterStore):
    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)

    async def record(
        self,
        document: SourceDocument,
        *,
        stage: str,
        error: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        path = self._dir / f"{document.document_id}__{stage}__{timestamp}.json"
        record = {
            "document_id": document.document_id,
            "tenant_id": document.metadata.tenant_id,
            "source_id": document.metadata.source_id,
            "uri": document.metadata.uri,
            "format": document.format.value,
            "content_sha256": document.content_sha256,
            "stage": stage,
            "error": error,
            "context": context or {},
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        path.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
