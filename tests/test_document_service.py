from pathlib import Path

import pytest

from wtype.document_service import (
    DocumentEncodingError,
    DocumentService,
    ExternalChangeError,
)


def test_write_and_read_utf8_markdown(tmp_path: Path) -> None:
    service = DocumentService()
    path = tmp_path / "یادداشت.md"
    original = "# Hello\n\nسلام دنیا\n"

    written_fingerprint = service.write(path, original)
    loaded, loaded_fingerprint = service.read(path)

    assert loaded == original
    assert loaded_fingerprint == written_fingerprint
    assert not path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_read_accepts_and_removes_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "bom.md"
    path.write_bytes(b"\xef\xbb\xbf# Title\n")

    markdown, _ = DocumentService().read(path)

    assert markdown == "# Title\n"


def test_invalid_utf8_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "invalid.md"
    path.write_bytes(b"\xff\xfe")

    with pytest.raises(DocumentEncodingError):
        DocumentService().read(path)


def test_external_change_is_detected_before_save(tmp_path: Path) -> None:
    service = DocumentService()
    path = tmp_path / "notes.md"
    expected = service.write(path, "first")
    path.write_text("external", encoding="utf-8")

    with pytest.raises(ExternalChangeError):
        service.write(path, "mine", expected=expected)

    assert path.read_text(encoding="utf-8") == "external"


def test_force_overwrites_external_change(tmp_path: Path) -> None:
    service = DocumentService()
    path = tmp_path / "notes.md"
    expected = service.write(path, "first")
    path.write_text("external", encoding="utf-8")

    service.write(path, "mine", expected=expected, force=True)

    assert path.read_text(encoding="utf-8") == "mine"
