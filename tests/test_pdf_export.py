from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import (
    QFont,
    QFontDatabase,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)
from PySide6.QtPdf import QPdfDocument

from wtype.app import _load_bundled_fonts
from wtype.pdf_export import PdfExporter
from wtype.typography import ARABIC_FONT_FAMILY, CODE_FONT_FAMILY


def test_pdf_export_creates_pdf_with_unicode(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    _load_bundled_fonts()
    destination = tmp_path / "document.pdf"

    pdf_font = PdfExporter.preferred_pdf_font()
    assert pdf_font == ARABIC_FONT_FAMILY
    assert QFontDatabase.WritingSystem.Arabic in QFontDatabase.writingSystems(
        pdf_font
    ), pdf_font

    PdfExporter().export("# Hello\n\nسلام دنیا\n", destination)

    assert destination.read_bytes().startswith(b"%PDF-")
    assert destination.stat().st_size > 500

    document = QPdfDocument()
    assert document.load(str(destination)) == QPdfDocument.Error.None_
    extracted = document.getAllText(0).text()
    assert "Hello" in extracted
    assert "سلام دنیا" in extracted


def test_pdf_code_uses_cascadia_and_gray_box(qapp) -> None:  # type: ignore[no-untyped-def]
    _load_bundled_fonts()
    document = PdfExporter()._print_document("Text `inline`\n\n```\ncode\n```\n", "Code")

    inline_block = document.begin()
    inline_fragments = []
    iterator = inline_block.begin()
    while not iterator.atEnd():
        inline_fragments.append(iterator.fragment())
        iterator += 1
    inline_code = next(
        fragment for fragment in inline_fragments if fragment.text() == "inline"
    )
    assert CODE_FONT_FAMILY in inline_code.charFormat().fontFamilies()
    assert 0 < inline_code.charFormat().background().color().alpha() < 255

    code_block = inline_block.next()
    assert code_block.blockFormat().hasProperty(QTextFormat.Property.BlockCodeFence)
    assert 0 < code_block.blockFormat().background().color().alpha() < 255
    assert CODE_FONT_FAMILY in code_block.begin().fragment().charFormat().fontFamilies()


def test_pdf_source_document_preserves_mixed_styles_inside_rtl_word(
    qapp, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _load_bundled_fonts()
    source = QTextDocument("برادر")
    expected_styles = [
        (False, False),
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ]
    for position, (bold, italic) in enumerate(expected_styles):
        cursor = QTextCursor(source)
        cursor.setPosition(position)
        cursor.setPosition(position + 1, QTextCursor.MoveMode.KeepAnchor)
        char_format = QTextCharFormat()
        if bold:
            char_format.setFontWeight(QFont.Weight.Bold)
        if italic:
            char_format.setFontItalic(True)
        cursor.mergeCharFormat(char_format)

    exporter = PdfExporter()
    document = exporter._print_source_document(source, "Mixed styles")
    actual_styles: list[tuple[bool, bool]] = []
    iterator = document.begin().begin()
    while not iterator.atEnd():
        fragment = iterator.fragment()
        style = (
            fragment.charFormat().fontWeight() >= QFont.Weight.Bold,
            fragment.charFormat().fontItalic(),
        )
        actual_styles.extend([style] * len(fragment.text()))
        iterator += 1

    assert document.toPlainText() == "برادر"
    assert actual_styles == expected_styles

    destination = tmp_path / "mixed-styles.pdf"
    exporter.export_document(source, destination)
    pdf = QPdfDocument()
    assert pdf.load(str(destination)) == QPdfDocument.Error.None_
    assert "*" not in pdf.getAllText(0).text()
