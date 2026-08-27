from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class DiskFingerprint:
    """Identity of a file version used to detect external modifications."""

    size: int
    modified_ns: int
    sha256: str


@dataclass(slots=True)
class DocumentSession:
    """Mutable state for the single document shown by WType."""

    document_id: str = field(default_factory=lambda: str(uuid4()))
    path: Path | None = None
    current_markdown: str = ""
    saved_markdown: str = ""
    fingerprint: DiskFingerprint | None = None
    recovered: bool = False

    @property
    def dirty(self) -> bool:
        return self.current_markdown != self.saved_markdown

    @property
    def display_name(self) -> str:
        return self.path.name if self.path else "Untitled"

    def replace_with_saved(
        self,
        markdown: str,
        path: Path,
        fingerprint: DiskFingerprint,
    ) -> None:
        self.path = path
        self.current_markdown = markdown
        self.saved_markdown = markdown
        self.fingerprint = fingerprint
        self.recovered = False
    def mark_saved(self, path: Path, fingerprint: DiskFingerprint) -> None:
        self.path = path
        self.saved_markdown = self.current_markdown
        self.fingerprint = fingerprint
        self.recovered = False
