from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QMimeData
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
from wtype.editor import MarkdownEditor
from wtype.pdf_export import PdfExporter
from wtype.typography import ARABIC_FONT_FAMILY, BODY_FONT_FAMILY, CODE_FONT_FAMILY


@pytest.mark.parametrize("source_kind", ["markdown", "editor", "command"])
def test_pdf_heading_sizes_and_inline_styles(
    qtbot, source_kind: str
) -> None:  # type: ignore[no-untyped-def]
    markdown = "\n\n".join(
        [f"{'#' * level} Heading *italic* `code` سلام" for level in range(1, 7)]
        + ["Body text"]
    )
    exporter = PdfExporter()
    if source_kind == "markdown":
        document = exporter._print_document(markdown, "Headings")
    else:
        editor = MarkdownEditor()
        qtbot.addWidget(editor)
        editor.configure_typography(QFont(BODY_FONT_FAMILY, 24))
        if source_kind == "editor":
            editor.set_markdown(markdown)
        else:
            editor.set_markdown(markdown.replace("#", "").lstrip())
            block = editor.document().begin()
            for level in range(1, 7):
                editor.setTextCursor(QTextCursor(block))
                editor.set_heading(level)
                block = block.next()
        original = editor.document().toHtml()
        document = exporter._print_source_document(editor.document(), "Headings")
        assert editor.document().toHtml() == original

    block = document.begin()
    for size in (22, 18.37, 15.62, 13.75, 12.32, 11.44):
        iterator = block.begin()
        italic_found = code_found = False
        while not iterator.atEnd():
            fragment = iterator.fragment()
            char_format = fragment.charFormat()
            assert char_format.fontPointSize() == pytest.approx(size)
            assert char_format.fontWeight() >= QFont.Weight.DemiBold
            if fragment.text() == "italic":
                italic_found = char_format.fontItalic()
            if fragment.text() == "code":
                code_found = CODE_FONT_FAMILY in char_format.fontFamilies()
            iterator += 1
        assert italic_found and code_found
        block = block.next()
    assert block.text() == "Body text"
    assert block.begin().fragment().charFormat().fontPointSize() in (0, 11)
    assert document.defaultFont().pointSizeF() == 11


def test_pdf_export_creates_pdf_with_unicode(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    _load_bundled_fonts()
    destination = tmp_path / "document.pdf"

    pdf_font = PdfExporter.preferred_pdf_font()
    assert pdf_font == BODY_FONT_FAMILY
    assert QFontDatabase.WritingSystem.Arabic in QFontDatabase.writingSystems(
        ARABIC_FONT_FAMILY
    )

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


def test_pdf_source_document_preserves_mixed_styles_inside_rtl_text(
    qapp, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    _load_bundled_fonts()
    source = QTextDocument("سلام دنیا")
    expected_styles = [
        (False, False),
        (False, False),
        (False, True),
        (True, False),
        (True, True),
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

    assert document.toPlainText() == "سلام دنیا"
    assert actual_styles == expected_styles

    destination = tmp_path / "mixed-styles.pdf"
    exporter.export_document(source, destination)
    pdf = QPdfDocument()
    assert pdf.load(str(destination)) == QPdfDocument.Error.None_
    assert "*" not in pdf.getAllText(0).text()


def test_pdf_export_preserves_pasted_markdown_table(qapp, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    _load_bundled_fonts()
    source = MarkdownEditor()
    clipboard = QMimeData()
    clipboard.setText(
        "# Weekly project plan\n\n"
        "## Upcoming tasks\n\n"
        "| Task | Status | Notes |\n"
        "|---|---|---|\n"
        "| Write documentation | In progress | Add usage examples. |\n"
        "| Review tests | Planned | Check export formats. |\n"
    )
    source.insertFromMimeData(clipboard)
    destination = tmp_path / "project-plan.pdf"

    PdfExporter().export_document(source.document(), destination)

    pdf = QPdfDocument()
    assert pdf.load(str(destination)) == QPdfDocument.Error.None_
    extracted = pdf.getAllText(0).text()
    normalized = " ".join(extracted.split())
    assert "Weekly project plan" in normalized
    assert "Upcoming tasks" in normalized
    assert "Write documentation" in normalized
    assert "Review tests" in normalized
    assert "|---|" not in normalized


@pytest.mark.parametrize("from_editor", [False, True])
def test_pdf_embeds_body_code_and_persian_fonts(
    qapp, tmp_path: Path, from_editor: bool
) -> None:  # type: ignore[no-untyped-def]
    _load_bundled_fonts()
    markdown = (
        "# Heading\n\nOutfit body **bold** and `inline_code`.\n\n"
        "سلام دنیا\n\n```\nprint('Hello')\n```\n"
    )
    exporter = PdfExporter()
    destination = tmp_path / "fonts.pdf"
    if from_editor:
        editor = MarkdownEditor()
        editor.set_markdown(markdown)
        exporter.export_document(editor.document(), destination)
    else:
        exporter.export(markdown, destination)

    data = destination.read_bytes()
    for font in (b"Outfit-Regular", b"Outfit-Bold", b"CascadiaMono-Regular", b"Vazirmatn-Regular"):
        assert font in data
    assert b"/FontFile2" in data
    pdf = QPdfDocument()
    assert pdf.load(str(destination)) == QPdfDocument.Error.None_
    extracted = pdf.getAllText(0).text()
    assert "Outfit body" in extracted
    assert "سلام دنیا" in extracted
    assert "inline_code" in extracted
    assert "print" in extracted
