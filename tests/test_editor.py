import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCursor, QTextFormat

from wtype.editor import MarkdownEditor
from wtype.typography import CODE_FONT_FAMILY


def test_heading_two_command_serializes_to_markdown(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.set_markdown("Fast writing")

    editor.set_heading(2)

    assert editor.markdown().lstrip().startswith("## Fast writing")


def test_heading_levels_have_distinct_visual_sizes(
    qtbot, qapp
) -> None:  # type: ignore[no-untyped-def]
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.configure_typography(QFont("Sans Serif", 12))

    rendered_sizes: list[float] = []
    for level in range(1, 7):
        editor.set_markdown("Heading")
        editor.set_heading(level)
        qapp.processEvents()
        formats = editor.document().begin().layout().formats()
        assert formats
        rendered_sizes.append(formats[0].format.fontPointSize())

    assert rendered_sizes == sorted(rendered_sizes, reverse=True)
    assert len(set(rendered_sizes)) == 6


def test_bold_command_formats_selection(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.set_markdown("fast")
    cursor = editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    editor.setTextCursor(cursor)

    editor.toggle_bold()

    assert "**fast**" in editor.markdown()


def test_heading_input_rule_and_immediate_backspace(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.show()
    editor.setFocus()

    qtbot.keyClicks(editor, "## ")
    assert editor.textCursor().blockFormat().headingLevel() == 2

    qtbot.keyClick(editor, Qt.Key.Key_Backspace)
    assert editor.toPlainText() == "## "


@pytest.mark.parametrize(
    ("typed", "state_key"),
    [
        ("- ", "format.bullet_list"),
        ("1. ", "format.numbered_list"),
        ("> ", "format.blockquote"),
    ],
)
def test_block_input_rules(qtbot, typed: str, state_key: str) -> None:  # type: ignore[no-untyped-def]
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.show()
    editor.setFocus()

    qtbot.keyClicks(editor, typed)

    assert editor.format_state()[state_key]


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("**fast**", "**fast**"),
        ("*fast*", "*fast*"),
        ("~~fast~~", "~~fast~~"),
        ("`fast`", "`fast`"),
    ],
)
def test_inline_input_rules(qtbot, typed: str, expected: str) -> None:  # type: ignore[no-untyped-def]
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.show()
    editor.setFocus()

    qtbot.keyClicks(editor, typed)

    assert expected in editor.markdown()


def test_code_fence_input_rule(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.show()
    editor.setFocus()

    qtbot.keyClicks(editor, "```")
    qtbot.keyClick(editor, Qt.Key.Key_Return)
    qtbot.keyClicks(editor, "print('fast')")

    assert "```\nprint('fast')\n```" in editor.markdown()


def test_code_uses_cascadia_mono_and_translucent_rectangles(
    qtbot, qapp
) -> None:  # type: ignore[no-untyped-def]
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    background = QColor(96, 96, 96, 32)
    editor.set_code_background(background)
    editor.set_markdown("Plain `inline` text\n\n```python\nprint('fast')\n```\n")
    qapp.processEvents()

    inline_formats = editor.document().begin().layout().formats()
    assert any(
        CODE_FONT_FAMILY in item.format.fontFamilies()
        and item.format.background().color() == background
        for item in inline_formats
    )

    code_block = editor.document().begin().next()
    block_formats = code_block.layout().formats()
    assert any(CODE_FONT_FAMILY in item.format.fontFamilies() for item in block_formats)

    selections = editor.extraSelections()
    assert len(selections) == 1
    assert selections[0].format.boolProperty(
        QTextFormat.Property.FullWidthSelection
    )
    assert selections[0].format.background().color() == background
    assert selections[0].format.background().color().alpha() < 255
    assert "`inline`" in editor.markdown()
    assert "```python\nprint('fast')\n```" in editor.markdown()


def test_insert_table_and_tab_at_last_cell_adds_row(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.insert_table()
    table = editor.textCursor().currentTable()
    assert table is not None
    assert (table.rows(), table.columns()) == (3, 3)

    editor.setTextCursor(table.cellAt(2, 2).firstCursorPosition())
    qtbot.keyClick(editor, Qt.Key.Key_Tab)

    assert table.rows() == 4
    assert "|Column 1|Column 2|Column 3|" in editor.markdown()
    assert "|--------|--------|--------|" in editor.markdown()


def test_horizontal_rule_preserves_existing_paragraph(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.set_markdown("before")

    editor.insert_horizontal_rule()

    markdown = editor.markdown()
    assert markdown.startswith("before\n\n")
    assert markdown.count("- - -") == 1
