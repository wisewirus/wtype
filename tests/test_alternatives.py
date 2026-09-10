from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QTextCursor
from PySide6.QtPdf import QPdfDocument

from wtype import alternatives as drafts
from wtype.document_service import DocumentError
from wtype.editor import MarkdownEditor
from wtype.pdf_export import PdfExporter


@pytest.fixture
def editor(qtbot):  # type: ignore[no-untyped-def]
    result = MarkdownEditor()
    qtbot.addWidget(result)
    result.set_markdown("Before\n\nAn **original** paragraph.\n\nAfter\n")
    result.setTextCursor(QTextCursor(result.document().findBlockByNumber(1)))
    return result


def test_versions_preserve_edits_formatting_and_surrounding_text(editor):  # type: ignore[no-untyped-def]
    original = editor.active_markdown()
    editor.setTextCursor(drafts.create(editor.textCursor()))
    frame = drafts.current_frame(editor.textCursor())
    editor.textCursor().insertMarkdown("A *different* paragraph.\n\nWith a second paragraph.")
    changed = editor.active_markdown()
    assert changed.startswith("Before\n\n")
    assert changed.endswith("After\n\n")
    editor.setTextCursor(drafts.switch(frame, 0))
    assert editor.active_markdown() == original
    editor.setTextCursor(drafts.switch(frame, 1))
    assert editor.active_markdown() == changed
    assert drafts.passage(frame).versions[0].markdown == "An **original** paragraph.\n\n"


def test_create_switch_rename_and_remove_are_undoable(editor):  # type: ignore[no-untyped-def]
    original = editor.markdown()
    editor.setTextCursor(drafts.create(editor.textCursor()))
    created = editor.markdown()
    editor.undo()
    assert editor.markdown() == original
    editor.redo()
    assert editor.markdown() == created
    frame = editor.document().rootFrame().childFrames()[0]
    editor.setTextCursor(drafts.contents(frame))
    editor.insertPlainText("An alternate passage.")
    edited = editor.markdown()
    editor.setTextCursor(drafts.switch(frame, 0))
    editor.undo()
    assert editor.markdown() == edited
    editor.redo()
    drafts.rename(frame, "Short introduction")
    assert drafts.passage(frame).versions[0].name == "Short introduction"
    editor.undo()
    assert drafts.passage(frame).versions[0].name == "Original"
    before_remove = editor.markdown()
    editor.setTextCursor(drafts.remove(frame))
    assert drafts.current_frame(editor.textCursor()) is None
    assert "wtype:alternatives" not in editor.markdown()
    assert "An alternate passage." in editor.toPlainText()
    editor.undo()
    assert editor.markdown() == before_remove


def test_save_roundtrip_keeps_independent_passages_and_unicode(editor, qtbot):  # type: ignore[no-untyped-def]
    editor.setTextCursor(drafts.create(editor.textCursor()))
    first = drafts.current_frame(editor.textCursor())
    drafts.rename(first, "مقدمه")
    editor.insertPlainText("سلام دنیا")
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    editor.setTextCursor(drafts.create(cursor))
    editor.insertPlainText("Another ending")
    saved = editor.markdown()
    restored = MarkdownEditor()
    qtbot.addWidget(restored)
    restored.set_markdown(saved)
    assert restored.markdown() == saved
    frames = restored.document().rootFrame().childFrames()
    assert len(frames) == 2
    assert drafts.passage(frames[0]).versions[1].name == "مقدمه"
    restored.setTextCursor(drafts.switch(frames[0], 0))
    assert "An **original** paragraph." in restored.active_markdown()
    assert "Another ending" in restored.active_markdown()
    restored.setTextCursor(drafts.switch(frames[1], 0))
    assert restored.active_markdown().endswith("After\n\n")


def test_empty_version_and_duplicate_paragraphs_roundtrip(editor, qtbot):  # type: ignore[no-untyped-def]
    editor.set_markdown("Same\n\nSame\n\nSame")
    editor.setTextCursor(QTextCursor(editor.document().findBlockByNumber(1)))
    editor.setTextCursor(drafts.create(editor.textCursor()))
    editor.textCursor().removeSelectedText()
    serialized = editor.markdown()
    restored = MarkdownEditor()
    qtbot.addWidget(restored)
    restored.set_markdown(serialized)
    assert restored.markdown() == serialized
    frame = restored.document().rootFrame().childFrames()[0]
    restored.setTextCursor(drafts.switch(frame, 0))
    assert restored.toPlainText().count("Same") == 3
    restored.setTextCursor(drafts.switch(frame, 1))
    assert restored.toPlainText().count("Same") == 2


def test_external_edit_updates_active_version_without_losing_other_versions(editor):  # type: ignore[no-untyped-def]
    editor.setTextCursor(drafts.create(editor.textCursor()))
    serialized = editor.markdown().replace("An **original** paragraph.", "Edited elsewhere")
    editor.set_markdown(serialized)
    frame = editor.document().rootFrame().childFrames()[0]
    assert drafts.passage(frame).versions[1].markdown == "Edited elsewhere\n\n"
    editor.setTextCursor(drafts.switch(frame, 0))
    assert "An **original** paragraph." in editor.active_markdown()


@pytest.mark.parametrize("damage", ["payload", "closing", "version"])
def test_damaged_alternatives_do_not_replace_open_document(editor, damage):  # type: ignore[no-untyped-def]
    editor.setTextCursor(drafts.create(editor.textCursor()))
    saved = editor.markdown()
    if damage == "payload":
        match = drafts._OPEN.search(saved)
        damaged = saved.replace(match.group(2), "e30=")
    elif damage == "closing":
        damaged = saved.replace("<!-- /wtype:alternatives", "<!-- missing")
    else:
        damaged = saved.replace("wtype:alternatives:v1", "wtype:alternatives:v99")
    with pytest.raises(DocumentError):
        editor.set_markdown(damaged)
    assert editor.markdown() == saved


def test_pdf_and_plain_markdown_export_include_only_active_version(
    editor, tmp_path: Path
):  # type: ignore[no-untyped-def]
    editor.setTextCursor(drafts.create(editor.textCursor()))
    editor.insertPlainText("Visible alternative")
    assert "original" not in editor.active_markdown()
    assert "wtype:alternatives" not in editor.active_markdown()
    destination = tmp_path / "active.pdf"
    PdfExporter().export_document(editor.document(), destination)
    pdf = QPdfDocument()
    assert pdf.load(str(destination)) == QPdfDocument.Error.None_
    extracted = "\n".join(pdf.getAllText(page).text() for page in range(pdf.pageCount()))
    assert "Visible alternative" in extracted
    assert "original" not in extracted


def test_document_deletion_and_undo_restore_alternatives(editor):  # type: ignore[no-untyped-def]
    editor.setTextCursor(drafts.create(editor.textCursor()))
    saved = editor.markdown()
    editor.selectAll()
    editor.textCursor().removeSelectedText()
    assert "wtype:alternatives" not in editor.markdown()
    editor.undo()
    assert editor.markdown() == saved


def test_alternatives_reject_multiblock_selection_and_tables(editor):  # type: ignore[no-untyped-def]
    editor.selectAll()
    assert not drafts.can_create(editor.textCursor())
    editor.set_markdown("| A | B |\n|---|---|\n| C | D |")
    table = editor.document().rootFrame().childFrames()[0]
    assert not drafts.can_create(table.firstCursorPosition())


@pytest.mark.parametrize("original", ["# Heading", "> Quote", "A **bold** paragraph"])
def test_block_formatting_does_not_leak_between_versions(editor, original):  # type: ignore[no-untyped-def]
    editor.set_markdown(original + "\n\nAfter")
    unchanged = editor.active_markdown()
    editor.setTextCursor(drafts.create(editor.textCursor()))
    assert editor.active_markdown() == unchanged
    frame = drafts.current_frame(editor.textCursor())
    editor.insertPlainText("Different")
    editor.set_heading(2)
    editor.setTextCursor(drafts.switch(frame, 0))
    assert editor.active_markdown() == unchanged
    saved = editor.markdown()
    editor.set_markdown(saved)
    assert editor.markdown() == saved


def test_documenting_metadata_in_code_does_not_create_alternatives(editor):  # type: ignore[no-untyped-def]
    editor.set_markdown("Example\n\n```html\n<!-- wtype:alternatives:v99 example -->\n```\n")
    assert "wtype:alternatives:v99" in editor.toPlainText()
    assert not editor.document().rootFrame().childFrames()


def test_pasting_formatted_version_keeps_heading_and_original(editor):  # type: ignore[no-untyped-def]
    original = editor.active_markdown()
    editor.setTextCursor(drafts.create(editor.textCursor()))
    frame = drafts.current_frame(editor.textCursor())
    clipboard = QMimeData()
    clipboard.setText("## Another opening\n\nWith **emphasis**.")
    editor.insertFromMimeData(clipboard)
    assert "## Another opening" in editor.active_markdown()
    assert "**emphasis**" in editor.active_markdown()
    saved = editor.markdown()
    editor.setTextCursor(drafts.switch(frame, 0))
    assert editor.active_markdown() == original
    editor.set_markdown(saved)
    assert editor.markdown() == saved


@pytest.mark.parametrize("text", ["# Heading\n\nMore **text**.", "سلام دنیا", ""])
def test_removing_last_extra_draft_unwraps_passage_and_undo_restores_it(editor, text):  # type: ignore[no-untyped-def]
    editor.setTextCursor(drafts.create(editor.textCursor()))
    frame = drafts.current_frame(editor.textCursor())
    drafts.replace_contents(frame, text)
    expected = editor.active_markdown()
    editor.setTextCursor(drafts.switch(frame, 0))
    saved = editor.markdown()
    editor.setTextCursor(drafts.remove(frame))
    assert editor.markdown() == expected
    assert not editor.document().rootFrame().childFrames()
    editor.undo()
    assert editor.markdown() == saved
    editor.redo()
    assert editor.markdown() == expected
