from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtPdf import QPdfDocument

from wtype.pdf_export import PdfExporter


def test_pdf_export_creates_pdf_with_unicode(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    destination = tmp_path / "document.pdf"

    PdfExporter().export("# Hello\n\nسلام دنیا\n", destination)

    assert destination.read_bytes().startswith(b"%PDF-")
    assert destination.stat().st_size > 500

    document = QPdfDocument()
    assert document.load(str(destination)) == QPdfDocument.Error.None_
    extracted = document.getAllText(0).text()
    assert "Hello" in extracted
    assert "سلام دنیا" in extracted
