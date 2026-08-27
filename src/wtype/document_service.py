from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from wtype.models import DiskFingerprint


class DocumentError(RuntimeError):
    """Base class for user-facing document failures."""


class DocumentEncodingError(DocumentError):
    """Raised when a Markdown document is not valid UTF-8."""


@dataclass(slots=True)
class ExternalChangeError(DocumentError):
    """Raised when saving would overwrite a version changed outside WType."""

    path: Path
    expected: DiskFingerprint | None
    current: DiskFingerprint | None

    def __str__(self) -> str:
        return f"{self.path.name} changed outside WType"


class DocumentService:
    """UTF-8 file IO with atomic replacement and conflict detection."""

    @staticmethod
    def fingerprint(path: Path) -> DiskFingerprint:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        stat = path.stat()
        return DiskFingerprint(
            size=stat.st_size,
            modified_ns=stat.st_mtime_ns,
            sha256=digest.hexdigest(),
        )

    def read(self, path: Path) -> tuple[str, DiskFingerprint]:
        path = path.expanduser().resolve()
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise DocumentError(f"Could not read {path}: {exc}") from exc
        try:
            # utf-8-sig accepts a BOM but does not retain it. All writes are plain UTF-8.
            markdown = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentEncodingError(f"{path.name} is not a valid UTF-8 file") from exc
        try:
            fingerprint = self.fingerprint(path)
        except OSError as exc:
            raise DocumentError(f"Could not inspect {path}: {exc}") from exc
        return markdown, fingerprint

    def write(
        self,
        path: Path,
        markdown: str,
        *,
        expected: DiskFingerprint | None = None,
        force: bool = False,
    ) -> DiskFingerprint:
        path = path.expanduser().resolve()
        current: DiskFingerprint | None = None
        if path.exists():
            try:
                current = self.fingerprint(path)
            except OSError as exc:
                raise DocumentError(f"Could not inspect {path}: {exc}") from exc

        if not force and expected is not None and current != expected:
            raise ExternalChangeError(path, expected, current)

        try:
            self._atomic_write(path, markdown.encode("utf-8"))
            return self.fingerprint(path)
        except OSError as exc:
            raise DocumentError(f"Could not save {path}: {exc}") from exc

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if path.exists():
                os.chmod(temporary_path, path.stat().st_mode)
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)
