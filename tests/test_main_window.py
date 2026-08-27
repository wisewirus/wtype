from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from wtype.main_window import MainWindow
from wtype.recovery import RecoveryService


def test_primary_shortcuts_drive_formatting_and_table(
    qtbot, qapp, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    window.recovery_service = RecoveryService(tmp_path / "recovery")
    qtbot.addWidget(window)
    window.show()
    window.activateWindow()
    window.editor.setFocus()
    qapp.processEvents()
    window.editor.set_markdown("Fast")

    cursor = window.editor.textCursor()
    cursor.select(QTextCursor.SelectionType.Document)
    window.editor.setTextCursor(cursor)
    qtbot.keyClick(window.editor, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    assert "**Fast**" in window.editor.markdown()

    cursor.clearSelection()
    window.editor.setTextCursor(cursor)
    qtbot.keyClick(window.editor, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
    assert window.editor.textCursor().blockFormat().headingLevel() == 2

    window.editor.set_markdown("")
    qtbot.keyClick(window.editor, Qt.Key.Key_T, Qt.KeyboardModifier.ControlModifier)
    assert window.editor.textCursor().currentTable() is not None

    # Prevent a modal unsaved-changes prompt during pytest-qt cleanup.
    window.session.current_markdown = window.session.saved_markdown
