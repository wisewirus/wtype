from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QLabel

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


def test_appearance_controls_are_persistent_and_brand_has_no_icon(
    qtbot, qapp, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    window = MainWindow()
    window.settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    qtbot.addWidget(window)

    window.set_background_opacity(72)
    window.set_blur_enabled(True)

    assert window.opacity_slider.value() == 72
    assert window.opacity_value.text() == "72%"
    assert window.settings.value("appearance/background_opacity", type=int) == 72
    assert window.blur_action.isChecked()
    assert window.settings.value("appearance/background_blur", type=bool)
    assert window.findChild(QLabel, "brandMark") is None
