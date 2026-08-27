from __future__ import annotations

import json
import os
import time
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from wtype.document_service import DocumentService
from wtype.models import DocumentSession

RECOVERY_SCHEMA_VERSION = 1


def default_recovery_directory() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys_platform() == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "WType" / "recovery"


def sys_platform() -> str:
    # Kept behind a function so path selection is straightforward to test.
    import sys

    return sys.platform


@dataclass(frozen=True, slots=True)
class RecoveryRecord:
    schema_version: int
    document_id: str
    source_path: str | None
    markdown: str
    saved_markdown: str
    updated_at: float

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> RecoveryRecord:
        return cls(
            schema_version=int(value["schema_version"]),
            document_id=str(value["document_id"]),
            source_path=(str(value["source_path"]) if value.get("source_path") else None),
            markdown=str(value["markdown"]),
            saved_markdown=str(value.get("saved_markdown", "")),
            updated_at=float(value["updated_at"]),
        )


class RecoveryService:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or default_recovery_directory()
        self._writer = DocumentService()

    def save(self, session: DocumentSession) -> RecoveryRecord | None:
        if not session.dirty:
            self.remove(session.document_id)
            return None
        record = RecoveryRecord(
            schema_version=RECOVERY_SCHEMA_VERSION,
            document_id=session.document_id,
            source_path=str(session.path) if session.path else None,
            markdown=session.current_markdown,
            saved_markdown=session.saved_markdown,
            updated_at=time.time(),
        )
        path = self._record_path(record.document_id)
        payload = json.dumps(asdict(record), ensure_ascii=False, indent=2) + "\n"
        self._writer.write(path, payload, force=True)
        return record

    def pending(self) -> list[RecoveryRecord]:
        if not self.directory.exists():
            return []
        records: list[RecoveryRecord] = []
        for path in self.directory.glob("*.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                record = RecoveryRecord.from_dict(value)
            except (OSError, ValueError, KeyError, TypeError):
                continue
            if record.schema_version != RECOVERY_SCHEMA_VERSION:
                continue
            if record.markdown == record.saved_markdown:
                self.remove(record.document_id)
                continue
            records.append(record)
        return sorted(records, key=lambda record: record.updated_at, reverse=True)

    def remove(self, document_id: str) -> None:
        # Recovery cleanup must never prevent closing or saving a document.
        with suppress(OSError):
            self._record_path(document_id).unlink(missing_ok=True)

    def _record_path(self, document_id: str) -> Path:
        safe_id = "".join(
            character
            for character in document_id
            if character.isalnum() or character == "-"
        )
        return self.directory / f"{safe_id}.json"
