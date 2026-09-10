from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, QRect, QSettings, Qt, QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QLabel, QLineEdit, QToolButton

from wtype import alternatives
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


def test_text_sizes_and_zoom_preserve_content_selection_and_undo(
    qtbot, qapp, tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    settings = QSettings(str(tmp_path / "type.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("wtype.main_window.QSettings", lambda: settings)
    window = MainWindow()
    window.recovery_service = RecoveryService(tmp_path / "recovery")
    qtbot.addWidget(window)
    window.editor.set_markdown(
        "# Heading\n\nBody with **bold** and `code`.\n\n```\ncode block\n```\n"
    )
    original = window.editor.markdown()
    cursor = window.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    window.editor.setTextCursor(cursor)
    window.editor.insertPlainText(" extra")
    cursor = window.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.PreviousWord, QTextCursor.MoveMode.KeepAnchor)
    window.editor.setTextCursor(cursor)
    selected = cursor.selectedText()
    edited = window.editor.markdown()
    print_before = window.pdf_exporter._print_source_document(
        window.editor.document(), "Test"
    ).toHtml()
    window.session.saved_markdown = edited
    window.editor.document().setModified(False)

    window.show_appearance()
    window.writing_size_spin.setValue(16)
    window.interface_size_spin.setValue(14)
    window.zoom_slider.setValue(150)
    qapp.processEvents()

    assert window.editor.document().defaultFont().pointSizeF() == 24
    assert window.editor.font().pointSizeF() == 24
    assert window.editor.heading_point_size(1) == 48
    assert window.find_input.font().pointSize() == 14
    assert window.menuBar().font().pointSize() == 14
    assert window.document_stats.font().pointSize() == 14
    assert window.interface_size_spin.font().pointSize() == 14
    assert window.editor.markdown() == edited
    assert window.editor.textCursor().selectedText() == selected
    assert not window.session.dirty
    assert not window.editor.document().isModified()
    assert window.pdf_exporter._print_source_document(
        window.editor.document(), "Test"
    ).toHtml() == print_before
    window.set_theme("nord")
    assert window.editor.document().defaultFont().pointSizeF() == 24
    window.editor.undo()
    assert window.editor.markdown() == original
    window.editor.redo()
    assert window.editor.markdown() == edited

    restored = MainWindow()
    restored.recovery_service = RecoveryService(tmp_path / "restored-recovery")
    qtbot.addWidget(restored)
    assert restored.writing_font_size == 16
    assert restored.interface_font_size == 14
    assert restored.zoom_percent == 150
    assert restored.theme_preference == "nord"
    assert restored.zoom_value.text() == "150%"
    assert restored.editor.document().defaultFont().pointSizeF() == 24
    restored.zoom_value.click()
    assert restored.zoom_percent == 100
    assert restored.editor.document().defaultFont().pointSizeF() == 16
    assert restored.interface_font_size == 14
    window.session.current_markdown = window.session.saved_markdown


@pytest.mark.parametrize("window_state", ["normal", "maximized", "fullscreen"])
def test_appearance_font_inputs_resize_with_interface_text(
    qtbot, qapp, tmp_path: Path, monkeypatch, window_state: str
) -> None:  # type: ignore[no-untyped-def]
    settings = QSettings(str(tmp_path / "sizing.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("wtype.main_window.QSettings", lambda: settings)
    window = MainWindow()
    window.recovery_service = RecoveryService(tmp_path / "recovery")
    qtbot.addWidget(window)
    window.resize(760, 520)
    if window_state == "fullscreen":
        window.showFullScreen()
    elif window_state == "maximized":
        window.showMaximized()
    else:
        window.show()
    qapp.processEvents()
    assert window.appearance_button.isVisible()
    window.appearance_button.click()
    dialog = window.appearance_dialog
    assert dialog is not None
    assert dialog.isVisible()
    assert dialog.windowModality() == Qt.WindowModality.WindowModal
    dialog.resize(480, 440)

    # Exercise live changes in both directions, including the largest supported font.
    for size in (9, 14, 20, 10):
        window.interface_size_spin.setValue(size)
        qapp.processEvents()
        for spin in (window.writing_size_spin, window.interface_size_spin):
            line_edit = spin.findChild(QLineEdit)
            assert line_edit is not None
            assert spin.height() >= spin.sizeHint().height()
            assert line_edit.height() >= line_edit.fontMetrics().height()
            assert line_edit.width() >= line_edit.fontMetrics().horizontalAdvance(spin.text())
        writing_rect = QRect(
            window.writing_size_spin.mapTo(dialog, QPoint()), window.writing_size_spin.size()
        )
        interface_rect = QRect(
            window.interface_size_spin.mapTo(dialog, QPoint()), window.interface_size_spin.size()
        )
        assert not writing_rect.intersects(interface_rect)
        if size == 20:
            assert dialog.scroll_area.verticalScrollBar().maximum() > 0
            dialog.scroll_area.ensureWidgetVisible(window.theme_combo)
            qapp.processEvents()
            theme_rect = QRect(
                window.theme_combo.mapTo(dialog.scroll_area.viewport(), QPoint()),
                window.theme_combo.size(),
            )
            assert dialog.scroll_area.viewport().rect().contains(theme_rect)

    increase = dialog.findChild(QToolButton, "interfaceIncrease")
    assert increase is not None
    increase.click()
    assert window.interface_font_size == 11
    dialog.reset_button.click()
    assert window.interface_font_size == 10
    assert window.writing_font_size == 12
    qtbot.keyClick(dialog, Qt.Key.Key_Escape)
    assert not dialog.isVisible()
    window.appearance_button.click()
    assert dialog.isVisible()


@pytest.mark.parametrize("before_show", [True, False])
def test_status_messages_replace_document_stats(
    qtbot, qapp, tmp_path: Path, monkeypatch, before_show: bool
) -> None:  # type: ignore[no-untyped-def]
    settings = QSettings(str(tmp_path / "status.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("wtype.main_window.QSettings", lambda: settings)
    window = MainWindow()
    window.recovery_service = RecoveryService(tmp_path / "recovery")
    qtbot.addWidget(window)
    if not before_show:
        window.show()
        qapp.processEvents()
    window.statusBar().showMessage("Background blur enabled")
    window.show()
    qapp.processEvents()
    assert not window.document_stats.isVisible()
    window._update_window_state()
    window.set_interface_font_size(20)
    qapp.processEvents()
    assert not window.document_stats.isVisible()
    window.statusBar().clearMessage()
    qapp.processEvents()
    assert window.document_stats.isVisible()


def test_zoom_shortcuts_wheel_and_bounds(
    qtbot, qapp, tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QWheelEvent

    settings = QSettings(str(tmp_path / "zoom.ini"), QSettings.Format.IniFormat)
    settings.setValue("appearance/writing_font_size", "invalid")
    settings.setValue("appearance/interface_font_size", 200)
    settings.setValue("appearance/zoom_percent", -50)
    monkeypatch.setattr("wtype.main_window.QSettings", lambda: settings)
    window = MainWindow()
    window.recovery_service = RecoveryService(tmp_path / "recovery")
    qtbot.addWidget(window)
    assert window.writing_font_size == 12
    assert window.interface_font_size == 20
    assert window.zoom_percent == 50
    window.set_interface_font_size(10)
    window.set_zoom(100)
    window.show()
    window.activateWindow()
    window.editor.setFocus()
    qapp.processEvents()
    qtbot.keyClick(window.editor, Qt.Key.Key_Equal, Qt.KeyboardModifier.ControlModifier)
    assert window.zoom_percent == 110
    qtbot.keyClick(window.editor, Qt.Key.Key_Minus, Qt.KeyboardModifier.ControlModifier)
    assert window.zoom_percent == 100
    for delta in (60, 60):
        event = QWheelEvent(
            QPointF(30, 30), QPointF(30, 30), QPoint(), QPoint(0, delta),
            Qt.MouseButton.NoButton, Qt.KeyboardModifier.ControlModifier,
            Qt.ScrollPhase.NoScrollPhase, False,
        )
        qapp.sendEvent(window.editor.viewport(), event)
    assert window.zoom_percent == 110
    qtbot.keyClick(
        window.editor, Qt.Key.Key_0,
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
    )
    assert window.zoom_percent == 100
    window.set_zoom(500)
    assert window.zoom_slider.value() == 200
    window.set_zoom(0)
    assert window.zoom_slider.value() == 50


def test_paragraph_alternatives_ui_save_recovery_and_export(
    qtbot, qapp, tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    settings = QSettings(str(tmp_path / "alternatives.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("wtype.main_window.QSettings", lambda: settings)
    window = MainWindow()
    qtbot.addWidget(window)
    window.recovery_service = RecoveryService(tmp_path / "recovery")
    window._set_editor_markdown("Original paragraph.\n\nUntouched ending.")
    window.session.current_markdown = window.editor.markdown()
    path = tmp_path / "document.md"
    assert window._save_to_path(path)
    window.show()
    window.activateWindow()
    window.editor.setFocus()
    qapp.processEvents()
    qtbot.keyClick(
        window.editor, Qt.Key.Key_N,
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier,
    )
    assert window.alternatives_bar.isVisible()
    assert window.choose_alternative_button.text() == "Versions (2)"
    assert window.current_alternative_label.text() == "Current: Version 2"
    assert window.session.dirty
    qtbot.keyClicks(window.editor, "Another opening.")
    window._populate_alternatives_menu()
    window.alternatives_menu.actions()[0].trigger()
    assert window.editor.active_markdown() == "Original paragraph.\n\nUntouched ending.\n\n"
    window._populate_alternatives_menu()
    window.alternatives_menu.actions()[1].trigger()
    assert "Another opening." in window.editor.toPlainText()
    monkeypatch.setattr(
        "wtype.main_window.QInputDialog.getText", lambda *args, **kwargs: ("Direct", True)
    )
    window._rename_alternative()
    assert window.current_alternative_label.text() == "Current: Direct"
    assert window.save_document()
    assert not window.session.dirty
    saved = path.read_text(encoding="utf-8")
    assert "wtype:alternatives:v1" in saved

    restored = MainWindow()
    qtbot.addWidget(restored)
    restored.recovery_service = window.recovery_service
    assert restored.open_path(path)
    qapp.processEvents()
    assert restored.editor.markdown() == saved
    assert not restored.session.dirty
    frame = restored.editor.document().rootFrame().childFrames()[0]
    restored.editor.setTextCursor(alternatives.contents(frame))
    assert restored.current_alternative_label.text() == "Current: Direct"
    restored.editor.insertPlainText("Unsaved alternative.")
    record = restored.recovery_service.save(restored.session)
    assert record is not None
    window._restore_record(record)
    assert "Unsaved alternative." in window.editor.toPlainText()
    frame = window.editor.document().rootFrame().childFrames()[0]
    window.editor.setTextCursor(alternatives.contents(frame))
    window._switch_alternative(0)
    assert "Original paragraph." in window.editor.toPlainText()

    exported = tmp_path / "shared.md"
    monkeypatch.setattr(
        "wtype.main_window.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (str(exported), ""),
    )
    window.export_active_markdown()
    assert exported.read_text(encoding="utf-8") == window.editor.active_markdown()
    assert "wtype:alternatives" not in exported.read_text(encoding="utf-8")
    assert path.read_text(encoding="utf-8") == saved
    assert window.session.path == path

    window._remove_alternative()
    assert not window.alternatives_bar.isVisible()
    assert alternatives.current_frame(window.editor.textCursor()) is None
    window.editor.undo()
    assert window.choose_alternative_button.text() == "Versions (2)"
    for item in (window, restored):
        item.session.saved_markdown = item.session.current_markdown
        item.recovery_service.remove(item.session.document_id)


def test_choose_version_menu_can_jump_to_any_draft_without_removing_others(
    qtbot, qapp, tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    settings = QSettings(str(tmp_path / "version-menu.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("wtype.main_window.QSettings", lambda: settings)
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "_maybe_save_changes", lambda: True)
    window.recovery_service = RecoveryService(tmp_path / "recovery")
    window._set_editor_markdown("Original opening.\n\nUnchanged ending.")
    window.show()
    qapp.processEvents()
    texts = ["Original opening.", "Second opening.", "Third opening.", "Fourth opening."]
    for text in texts[1:]:
        window.new_alternative()
        window.editor.insertPlainText(text)

    current = 3
    for index in (0, 2, 1, 3, 2):
        observed = []

        def choose(selected=index, results=observed) -> None:  # type: ignore[no-untyped-def]
            menu = window.alternatives_menu
            actions = menu.actions()
            results.append((
                menu.isVisible(), len(actions),
                [i for i, action in enumerate(actions) if action.isChecked()],
                actions[selected].toolTip(),
            ))
            qtbot.mouseClick(
                menu, Qt.MouseButton.LeftButton,
                pos=menu.actionGeometry(actions[selected]).center(),
            )

        QTimer.singleShot(0, choose)
        qtbot.mouseClick(window.choose_alternative_button, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda results=observed: bool(results))
        assert observed == [(True, 4, [current], texts[index])]
        frame = alternatives.current_frame(window.editor.textCursor())
        value = alternatives.passage(frame)
        assert value.active == index
        assert len(value.versions) == 4
        assert window.editor.active_markdown() == texts[index] + "\n\nUnchanged ending.\n\n"
        assert window.current_alternative_label.text() == f"Current: {value.versions[index].name}"
        current = index
        if index == 2:
            texts[2] = "Edited third opening."
            window.editor.insertPlainText(texts[2])
    window.session.saved_markdown = window.session.current_markdown


def test_open_damaged_alternatives_keeps_current_document(
    qtbot, tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    settings = QSettings(str(tmp_path / "damaged.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("wtype.main_window.QSettings", lambda: settings)
    window = MainWindow()
    qtbot.addWidget(window)
    window.recovery_service = RecoveryService(tmp_path / "recovery")
    window._set_editor_markdown("Keep this document")
    window.session.current_markdown = window.editor.markdown()
    original = window.editor.markdown()
    path = tmp_path / "broken.md"
    path.write_text("Other text\n\n<!-- wtype:alternatives:v99 damaged -->", encoding="utf-8")
    errors = []
    monkeypatch.setattr(window, "_show_error", lambda *args: errors.append(args))
    assert not window.open_path(path)
    assert errors
    assert window.editor.markdown() == original
    assert window.session.current_markdown == original
    assert not window._loading
    window.session.saved_markdown = window.session.current_markdown


def test_alternatives_can_close_reopen_and_finish_without_losing_text(
    qtbot, qapp, tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    settings = QSettings(str(tmp_path / "dismiss.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("wtype.main_window.QSettings", lambda: settings)
    window = MainWindow()
    qtbot.addWidget(window)
    monkeypatch.setattr(window, "_maybe_save_changes", lambda: True)
    window.recovery_service = RecoveryService(tmp_path / "recovery")
    window._set_editor_markdown("Original paragraph.\n\nUnchanged ending.")
    original = window.editor.markdown()
    window.show()
    window.new_alternative()
    window.editor.insertPlainText("A different version.")
    saved = window.editor.markdown()
    window.close_alternatives_button.click()
    assert not window.alternatives_bar.isVisible()
    window.set_interface_font_size(20)
    cursor = window.editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.Left)
    window.editor.setTextCursor(cursor)
    qapp.processEvents()
    assert not window.alternatives_bar.isVisible()
    assert window.editor.markdown() == saved
    window.action_registry["edit.show_alternatives"].trigger()
    assert window.alternatives_bar.isVisible()
    assert window.editor.markdown() == saved
    window.editor.setFocus()
    qtbot.keyClick(window.editor, Qt.Key.Key_Escape)
    assert not window.alternatives_bar.isVisible()
    window.show_alternatives()
    window.remove_alternative_button.click()
    assert not window.alternatives_bar.isVisible()
    assert window.editor.markdown() == original
    window.editor.undo()
    assert window.editor.markdown() == saved
    assert window.alternatives_bar.isVisible()
    window.session.saved_markdown = window.session.current_markdown


def test_slider_drags_coalesce_updates_and_skip_full_theme(
    qtbot, tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from unittest.mock import Mock

    settings = QSettings(str(tmp_path / "sliders.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr("wtype.main_window.QSettings", lambda: settings)
    window = MainWindow()
    window.recovery_service = RecoveryService(tmp_path / "recovery")
    qtbot.addWidget(window)
    full_theme = Mock(side_effect=AssertionError("Slider must not rebuild the theme"))
    monkeypatch.setattr(window, "set_theme", full_theme)
    typography = Mock(wraps=window._apply_editor_typography)
    monkeypatch.setattr(window, "_apply_editor_typography", typography)
    window.zoom_slider.setSliderDown(True)
    for value in range(110, 161):
        window.zoom_slider.setValue(value)
    assert window.zoom_value.text() == "160%"
    assert typography.call_count == 0
    qtbot.waitUntil(lambda: typography.call_count == 1)
    assert window.editor.font().pointSizeF() == 19.2
    window.zoom_slider.setValue(175)
    window.zoom_slider.setSliderDown(False)
    assert window.editor.font().pointSizeF() == 21
    assert settings.value("appearance/zoom_percent", type=int) == 175
    assert not window._zoom_timer.isActive()

    window.opacity_slider.setSliderDown(True)
    for value in range(99, 59, -1):
        window.opacity_slider.setValue(value)
    window.opacity_slider.setSliderDown(False)
    assert window.opacity_value.text() == "60%"
    assert settings.value("appearance/background_opacity", type=int) == 60
    assert not window._opacity_timer.isActive()
    full_theme.assert_not_called()
