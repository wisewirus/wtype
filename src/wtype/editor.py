from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QSyntaxHighlighter,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextListFormat,
    QTextTableFormat,
)
from PySide6.QtWidgets import QInputDialog, QTextEdit, QWidget

from wtype.typography import CODE_FONT_FAMILIES


class MarkdownHighlighter(QSyntaxHighlighter):
    """Adds view-only heading and code typography without changing Markdown."""

    _SCALE = (2.0, 1.67, 1.42, 1.25, 1.12, 1.04)

    def __init__(self, document: QTextDocument, base_size: float) -> None:
        super().__init__(document)
        self._base_size = base_size
        self._color: QColor | None = None
        self._code_background = QColor(128, 128, 128, 28)

    def point_size(self, level: int) -> float:
        if not 1 <= level <= len(self._SCALE):
            return self._base_size
        return self._base_size * self._SCALE[level - 1]

    def set_base_size(self, base_size: float) -> None:
        self._base_size = base_size
        self.rehighlight()

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.rehighlight()

    def set_code_background(self, color: QColor) -> None:
        self._code_background = QColor(color)
        self.rehighlight()

    @staticmethod
    def _code_font_format() -> QTextCharFormat:
        char_format = QTextCharFormat()
        char_format.setFontFixedPitch(True)
        char_format.setFontFamilies(list(CODE_FONT_FAMILIES))
        return char_format

    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt override)
        block = self.currentBlock()
        block_format = block.blockFormat()
        if block_format.hasProperty(QTextFormat.Property.BlockCodeFence):
            self.setFormat(0, len(text), self._code_font_format())
            return

        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            if fragment.isValid() and fragment.charFormat().fontFixedPitch():
                code_format = self._code_font_format()
                code_format.setBackground(self._code_background)
                self.setFormat(
                    fragment.position() - block.position(),
                    fragment.length(),
                    code_format,
                )
            iterator += 1

        level = block_format.headingLevel()
        if 1 <= level <= len(self._SCALE):
            heading_format = QTextCharFormat()
            heading_format.setFontPointSize(self.point_size(level))
            heading_format.setFontWeight(
                QFont.Weight.Bold if level <= 2 else QFont.Weight.DemiBold
            )
            if self._color is not None:
                heading_format.setForeground(self._color)
            self.setFormat(0, len(text), heading_format)


class MarkdownEditor(QTextEdit):
    """A QTextEdit that exposes semantic Markdown formatting commands."""

    markdown_changed = Signal(str)
    format_state_changed = Signal()
    table_state_changed = Signal(bool)

    _INLINE_RULES = (
        (re.compile(r"\*\*([^*\n]+)\*\*$"), "bold"),
        (re.compile(r"~~([^~\n]+)~~$"), "strike"),
        (re.compile(r"`([^`\n]+)`$"), "code"),
        (re.compile(r"(?<!\*)\*([^*\n]+)\*$"), "italic"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loading = False
        self._input_rule_just_applied = False
        self.setAcceptRichText(False)
        self.setTabChangesFocus(False)
        self.setUndoRedoEnabled(True)
        self.setPlaceholderText("Start writing…")
        self.setFrameShape(QTextEdit.Shape.NoFrame)

        option = self.document().defaultTextOption()
        option.setTextDirection(Qt.LayoutDirection.LayoutDirectionAuto)
        self.document().setDefaultTextOption(option)
        self._code_background = QColor(128, 128, 128, 28)
        self._markdown_highlighter = MarkdownHighlighter(
            self.document(),
            max(self.font().pointSizeF(), 1.0),
        )

        self.textChanged.connect(self._on_text_changed)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.selectionChanged.connect(self.format_state_changed)

    def configure_typography(self, font: QFont) -> None:
        self.setFont(font)
        self.document().setDefaultFont(font)
        self._markdown_highlighter.set_base_size(max(font.pointSizeF(), 1.0))

    def set_heading_color(self, color: str) -> None:
        self._markdown_highlighter.set_color(color)

    def set_code_background(self, color: QColor) -> None:
        self._code_background = QColor(color)
        self._markdown_highlighter.set_code_background(color)
        self._refresh_code_block_backgrounds()

    def heading_point_size(self, level: int) -> float:
        return self._markdown_highlighter.point_size(level)

    def set_markdown(self, markdown: str) -> None:
        self._loading = True
        try:
            self.document().setMarkdown(
                markdown,
                QTextDocument.MarkdownFeature.MarkdownDialectGitHub,
            )
            self.document().clearUndoRedoStacks()
            self.document().setModified(False)
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.setTextCursor(cursor)
        finally:
            self._loading = False
        self._markdown_highlighter.rehighlight()
        self._refresh_code_block_backgrounds()
        self._on_cursor_changed()

    def markdown(self) -> str:
        return self.document().toMarkdown(
            QTextDocument.MarkdownFeature.MarkdownDialectGitHub
        )

    def _on_text_changed(self) -> None:
        self._refresh_code_block_backgrounds()
        if not self._loading:
            self.markdown_changed.emit(self.markdown())

    def _refresh_code_block_backgrounds(self) -> None:
        selections: list[QTextEdit.ExtraSelection] = []
        block = self.document().begin()
        while block.isValid():
            if block.blockFormat().hasProperty(QTextFormat.Property.BlockCodeFence):
                selection = QTextEdit.ExtraSelection()
                selection.cursor = QTextCursor(block)
                selection.format.setBackground(self._code_background)
                selection.format.setProperty(
                    QTextFormat.Property.FullWidthSelection,
                    True,
                )
                selections.append(selection)
            block = block.next()
        self.setExtraSelections(selections)

    def _on_cursor_changed(self) -> None:
        self.format_state_changed.emit()
        self.table_state_changed.emit(self.textCursor().currentTable() is not None)

    # Inline formatting -------------------------------------------------
    def toggle_bold(self) -> None:
        current = self.textCursor().charFormat().fontWeight()
        char_format = QTextCharFormat()
        char_format.setFontWeight(
            QFont.Weight.Normal if current >= QFont.Weight.Bold else QFont.Weight.Bold
        )
        self._merge_character_format(char_format)

    def toggle_italic(self) -> None:
        char_format = QTextCharFormat()
        char_format.setFontItalic(not self.textCursor().charFormat().fontItalic())
        self._merge_character_format(char_format)

    def toggle_strikethrough(self) -> None:
        char_format = QTextCharFormat()
        current = self.textCursor().charFormat().fontStrikeOut()
        char_format.setFontStrikeOut(not current)
        self._merge_character_format(char_format)

    def toggle_inline_code(self) -> None:
        current = self.textCursor().charFormat().fontFixedPitch()
        char_format = QTextCharFormat()
        char_format.setFontFixedPitch(not current)
        if not current:
            char_format.setFontFamilies(list(CODE_FONT_FAMILIES))
        else:
            char_format.clearProperty(QTextFormat.Property.FontFamilies)
        self._merge_character_format(char_format)

    def insert_or_edit_link(self) -> None:
        cursor = self.textCursor()
        existing = cursor.charFormat().anchorHref()
        url, accepted = QInputDialog.getText(
            self,
            "Insert link",
            "URL:",
            text=existing or "https://",
        )
        if not accepted or not url.strip():
            return
        url = url.strip()
        cursor.beginEditBlock()
        if not cursor.hasSelection():
            cursor.insertText(url)
            cursor.movePosition(
                QTextCursor.MoveOperation.Left,
                QTextCursor.MoveMode.KeepAnchor,
                len(url),
            )
        char_format = QTextCharFormat()
        char_format.setAnchor(True)
        char_format.setAnchorHref(url)
        char_format.setFontUnderline(True)
        cursor.mergeCharFormat(char_format)
        cursor.clearSelection()
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def _merge_character_format(self, char_format: QTextCharFormat) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.mergeCharFormat(char_format)
        cursor.endEditBlock()
        self.mergeCurrentCharFormat(char_format)
        self.format_state_changed.emit()

    # Block formatting --------------------------------------------------
    def set_heading(self, level: int) -> None:
        cursor = self.textCursor()
        current_level = cursor.blockFormat().headingLevel()
        target = 0 if level == current_level else level
        block_format = cursor.blockFormat()
        block_format.setHeadingLevel(target)
        cursor.beginEditBlock()
        cursor.setBlockFormat(block_format)
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self._markdown_highlighter.rehighlight()
        self._refresh_code_block_backgrounds()
        self.format_state_changed.emit()

    def set_paragraph(self) -> None:
        cursor = self.textCursor()
        block_format = cursor.blockFormat()
        block_format.setHeadingLevel(0)
        block_format.clearProperty(QTextFormat.Property.BlockCodeFence)
        block_format.clearProperty(QTextFormat.Property.BlockCodeLanguage)
        block_format.clearProperty(QTextFormat.Property.BlockQuoteLevel)
        cursor.setBlockFormat(block_format)
        self._markdown_highlighter.rehighlightBlock(cursor.block())
        self._refresh_code_block_backgrounds()
        self.format_state_changed.emit()

    def toggle_bullet_list(self) -> None:
        self._toggle_list(QTextListFormat.Style.ListDisc)

    def toggle_numbered_list(self) -> None:
        self._toggle_list(QTextListFormat.Style.ListDecimal)

    def _toggle_list(self, style: QTextListFormat.Style) -> None:
        cursor = self.textCursor()
        current_list = cursor.currentList()
        cursor.beginEditBlock()
        if current_list is not None and current_list.format().style() == style:
            block = cursor.block()
            current_list.remove(block)
            block_format = cursor.blockFormat()
            block_format.setIndent(0)
            block_format.setObjectIndex(-1)
            cursor.setBlockFormat(block_format)
        else:
            list_format = QTextListFormat()
            list_format.setStyle(style)
            list_format.setIndent(1)
            cursor.createList(list_format)
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.format_state_changed.emit()

    def toggle_blockquote(self) -> None:
        cursor = self.textCursor()
        block_format = cursor.blockFormat()
        current = block_format.intProperty(QTextFormat.Property.BlockQuoteLevel)
        if current:
            block_format.clearProperty(QTextFormat.Property.BlockQuoteLevel)
        else:
            block_format.setProperty(QTextFormat.Property.BlockQuoteLevel, 1)
        cursor.setBlockFormat(block_format)
        self.format_state_changed.emit()

    def toggle_code_block(self) -> None:
        cursor = self.textCursor()
        block_format = cursor.blockFormat()
        enabled = block_format.hasProperty(QTextFormat.Property.BlockCodeFence)
        if enabled:
            block_format.clearProperty(QTextFormat.Property.BlockCodeFence)
            block_format.clearProperty(QTextFormat.Property.BlockCodeLanguage)
        else:
            block_format.setProperty(QTextFormat.Property.BlockCodeFence, "```")
            block_format.setProperty(QTextFormat.Property.BlockCodeLanguage, "")
        cursor.setBlockFormat(block_format)
        self._markdown_highlighter.rehighlightBlock(cursor.block())
        self._refresh_code_block_backgrounds()
        self.format_state_changed.emit()

    def insert_horizontal_rule(self) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if cursor.block().text():
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            rule_format = QTextBlockFormat()
            rule_format.setProperty(
                QTextFormat.Property.BlockTrailingHorizontalRulerWidth,
                1,
            )
            cursor.insertBlock(rule_format)
        else:
            rule_format = cursor.blockFormat()
            rule_format.setProperty(
                QTextFormat.Property.BlockTrailingHorizontalRulerWidth,
                1,
            )
            cursor.setBlockFormat(rule_format)
        cursor.insertBlock()
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    # Tables ------------------------------------------------------------
    def insert_table(self) -> None:
        cursor = self.textCursor()
        if cursor.currentTable() is not None:
            return
        table_format = QTextTableFormat()
        table_format.setBorder(1)
        table_format.setCellPadding(6)
        table_format.setCellSpacing(0)
        table_format.setHeaderRowCount(1)
        table = cursor.insertTable(3, 3, table_format)
        for column in range(3):
            header_cursor = table.cellAt(0, column).firstCursorPosition()
            header_cursor.insertText(f"Column {column + 1}")
        first_header = table.cellAt(0, 0).firstCursorPosition()
        first_header.movePosition(
            QTextCursor.MoveOperation.EndOfBlock,
            QTextCursor.MoveMode.KeepAnchor,
        )
        self.setTextCursor(first_header)

    def add_table_row(self) -> None:
        cursor = self.textCursor()
        table = cursor.currentTable()
        if table is None:
            return
        cell = table.cellAt(cursor)
        table.insertRows(cell.row() + 1, 1)

    def add_table_column(self) -> None:
        cursor = self.textCursor()
        table = cursor.currentTable()
        if table is None:
            return
        cell = table.cellAt(cursor)
        table.insertColumns(cell.column() + 1, 1)

    def delete_table_row(self) -> None:
        cursor = self.textCursor()
        table = cursor.currentTable()
        if table is None or table.rows() <= 2:
            return
        table.removeRows(table.cellAt(cursor).row(), 1)

    def delete_table_column(self) -> None:
        cursor = self.textCursor()
        table = cursor.currentTable()
        if table is None or table.columns() <= 1:
            return
        table.removeColumns(table.cellAt(cursor).column(), 1)

    # State -------------------------------------------------------------
    def format_state(self) -> dict[str, bool]:
        cursor = self.textCursor()
        char_format = cursor.charFormat()
        block_format = cursor.blockFormat()
        current_list = cursor.currentList()
        state = {
            "format.bold": char_format.fontWeight() >= QFont.Weight.Bold,
            "format.italic": char_format.fontItalic(),
            "format.strike": char_format.fontStrikeOut(),
            "format.inline_code": char_format.fontFixedPitch(),
            "format.paragraph": block_format.headingLevel() == 0,
            "format.bullet_list": bool(
                current_list
                and current_list.format().style() == QTextListFormat.Style.ListDisc
            ),
            "format.numbered_list": bool(
                current_list
                and current_list.format().style() == QTextListFormat.Style.ListDecimal
            ),
            "format.blockquote": bool(
                block_format.intProperty(QTextFormat.Property.BlockQuoteLevel)
            ),
            "format.code_block": block_format.hasProperty(
                QTextFormat.Property.BlockCodeFence
            ),
        }
        for level in range(1, 7):
            state[f"format.h{level}"] = block_format.headingLevel() == level
        return state

    # Keyboard input rules ---------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt override)
        if (
            event.key() == Qt.Key.Key_Backspace
            and self._input_rule_just_applied
            and self.document().isUndoAvailable()
        ):
            self.document().undo()
            self._input_rule_just_applied = False
            return

        self._input_rule_just_applied = False

        if event.key() in (
            Qt.Key.Key_Tab,
            Qt.Key.Key_Backtab,
        ) and self._move_in_table(backwards=event.key() == Qt.Key.Key_Backtab):
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            marker = self.textCursor().block().text().strip()
            if marker == "```":
                self._convert_marker_to_code_block()
                return
            if marker == "---":
                self._convert_marker_to_horizontal_rule()
                return

        super().keyPressEvent(event)

        if event.text() == " ":
            self._apply_block_input_rule()
        elif event.text() in {"*", "~", "`"}:
            self._apply_inline_input_rule()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt override)
        self._input_rule_just_applied = False
        super().mousePressEvent(event)

    def _is_code_block(self) -> bool:
        return self.textCursor().blockFormat().hasProperty(
            QTextFormat.Property.BlockCodeFence
        )

    def _apply_block_input_rule(self) -> None:
        if self._is_code_block():
            return
        text = self.textCursor().block().text()
        heading = re.fullmatch(r"(#{1,6}) ", text)
        action: str | None = None
        level = 0
        if heading:
            action = "heading"
            level = len(heading.group(1))
        elif text in {"- ", "* "}:
            action = "bullet"
        elif text == "1. ":
            action = "numbered"
        elif text == "> ":
            action = "quote"
        if action is None:
            return

        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
        self.setTextCursor(cursor)
        if action == "heading":
            self.set_heading(level)
        elif action == "bullet":
            self.toggle_bullet_list()
        elif action == "numbered":
            self.toggle_numbered_list()
        else:
            self.toggle_blockquote()
        cursor.endEditBlock()
        self._input_rule_just_applied = True

    def _apply_inline_input_rule(self) -> None:
        if self._is_code_block():
            return
        cursor = self.textCursor()
        block = cursor.block()
        before_cursor = block.text()[: cursor.position() - block.position()]
        for pattern, kind in self._INLINE_RULES:
            match = pattern.search(before_cursor)
            if match is None:
                continue
            start = block.position() + match.start()
            end = block.position() + match.end()
            inner = match.group(1)
            replacement = QTextCursor(self.document())
            replacement.setPosition(start)
            replacement.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            replacement.beginEditBlock()
            replacement.insertText(inner)
            replacement.setPosition(start)
            replacement.setPosition(start + len(inner), QTextCursor.MoveMode.KeepAnchor)
            char_format = QTextCharFormat()
            if kind == "bold":
                char_format.setFontWeight(QFont.Weight.Bold)
            elif kind == "italic":
                char_format.setFontItalic(True)
            elif kind == "strike":
                char_format.setFontStrikeOut(True)
            else:
                char_format.setFontFixedPitch(True)
                char_format.setFontFamilies(list(CODE_FONT_FAMILIES))
            replacement.mergeCharFormat(char_format)
            replacement.clearSelection()
            replacement.setPosition(start + len(inner))
            replacement.endEditBlock()
            self.setTextCursor(replacement)
            self.setCurrentCharFormat(QTextCharFormat())
            self._input_rule_just_applied = True
            return

    def _convert_marker_to_code_block(self) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
        block_format = cursor.blockFormat()
        block_format.setProperty(QTextFormat.Property.BlockCodeFence, "```")
        block_format.setProperty(QTextFormat.Property.BlockCodeLanguage, "")
        cursor.setBlockFormat(block_format)
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self._markdown_highlighter.rehighlightBlock(cursor.block())
        self._refresh_code_block_backgrounds()
        self._input_rule_just_applied = True

    def _convert_marker_to_horizontal_rule(self) -> None:
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.removeSelectedText()
        block_format = cursor.blockFormat()
        block_format.setProperty(
            QTextFormat.Property.BlockTrailingHorizontalRulerWidth,
            1,
        )
        cursor.setBlockFormat(block_format)
        cursor.insertBlock(QTextBlockFormat())
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self._input_rule_just_applied = True

    def _move_in_table(self, *, backwards: bool) -> bool:
        cursor = self.textCursor()
        table = cursor.currentTable()
        if table is None:
            return False
        cell = table.cellAt(cursor)
        index = cell.row() * table.columns() + cell.column()
        if backwards:
            if index == 0:
                return False
            index -= 1
        else:
            index += 1
            if index == table.rows() * table.columns():
                table.appendRows(1)
        row, column = divmod(index, table.columns())
        self.setTextCursor(table.cellAt(row, column).firstCursorPosition())
        return True
