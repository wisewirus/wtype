from __future__ import annotations

import html
from collections.abc import Callable
from functools import partial
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QCloseEvent,
    QFont,
    QKeySequence,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from wtype.actions import ActionRegistry
from wtype.background_effect import BackgroundEffect
from wtype.commands import COMMAND_SPECS
from wtype.document_service import (
    DocumentError,
    DocumentService,
    ExternalChangeError,
)
from wtype.editor import MarkdownEditor
from wtype.models import DocumentSession
from wtype.pdf_export import PdfExporter, PdfExportError
from wtype.recovery import RecoveryRecord, RecoveryService
from wtype.theme import THEME_CHOICES, THEMES, apply_theme


class MainWindow(QMainWindow):
    def __init__(self, initial_path: Path | None = None) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.resize(1200, 820)
        self.setMinimumSize(760, 520)
        self.setUnifiedTitleAndToolBarOnMac(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.document_service = DocumentService()
        self.recovery_service = RecoveryService()
        self.pdf_exporter = PdfExporter()
        self.settings = QSettings()
        self.session = DocumentSession()
        self._loading = False
        self.theme_preference = "system"
        self.background_opacity = 100
        self.blur_enabled = False
        self.background_effect = BackgroundEffect(self)

        self.editor = MarkdownEditor(self)
        self.editor.setObjectName("editor")
        editor_font = QFont(self.pdf_exporter.preferred_editor_font(), 12)
        editor_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.editor.configure_typography(editor_font)
        self.editor.setMaximumWidth(920)
        self.editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.find_bar = self._create_find_bar()
        self.setCentralWidget(self._create_editor_shell())
        self.action_registry = ActionRegistry(self, self._command_callbacks())
        self._create_menus()
        self._create_toolbar()
        self._create_escape_action()
        self._connect_signals()
        self._restore_settings()
        self._update_window_state()

        if initial_path is not None:
            self.open_path(initial_path)
        QTimer.singleShot(0, self._initialize_background_effect)
        QTimer.singleShot(0, self._offer_recovery)

    # Construction ------------------------------------------------------
    def _create_editor_shell(self) -> QWidget:
        shell = QWidget(self)
        shell.setObjectName("editorShell")
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(24, 22, 24, 14)
        outer.setSpacing(12)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.editor, 8)
        row.addStretch(1)
        outer.addLayout(row, 1)
        outer.addWidget(self.find_bar)
        return shell

    def _create_find_bar(self) -> QWidget:
        bar = QWidget(self)
        bar.setObjectName("findBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Find"))
        self.find_input = QLineEdit(bar)
        self.find_input.setClearButtonEnabled(True)
        self.find_input.setPlaceholderText("Search in this document")
        layout.addWidget(self.find_input, 1)
        previous = QPushButton("Previous", bar)
        next_button = QPushButton("Next", bar)
        close = QPushButton("Close", bar)
        previous.clicked.connect(lambda: self._find(backwards=True))
        next_button.clicked.connect(lambda: self._find(backwards=False))
        close.clicked.connect(self._hide_find)
        self.find_input.returnPressed.connect(lambda: self._find(backwards=False))
        layout.addWidget(previous)
        layout.addWidget(next_button)
        layout.addWidget(close)
        bar.hide()
        return bar

    def _command_callbacks(self) -> dict[str, Callable[[], object]]:
        callbacks: dict[str, Callable[[], object]] = {
            "file.new": self.new_document,
            "file.open": self.open_document,
            "file.save": self.save_document,
            "file.save_as": self.save_document_as,
            "file.export_pdf": self.export_pdf,
            "file.quit": self.close,
            "edit.undo": self.editor.undo,
            "edit.redo": self.editor.redo,
            "edit.cut": self.editor.cut,
            "edit.copy": self.editor.copy,
            "edit.paste": self.editor.paste,
            "edit.select_all": self.editor.selectAll,
            "edit.find": self.show_find,
            "format.bold": self.editor.toggle_bold,
            "format.italic": self.editor.toggle_italic,
            "format.strike": self.editor.toggle_strikethrough,
            "format.inline_code": self.editor.toggle_inline_code,
            "format.link": self.editor.insert_or_edit_link,
            "format.paragraph": self.editor.set_paragraph,
            "format.bullet_list": self.editor.toggle_bullet_list,
            "format.numbered_list": self.editor.toggle_numbered_list,
            "format.blockquote": self.editor.toggle_blockquote,
            "format.code_block": self.editor.toggle_code_block,
            "insert.table": self.editor.insert_table,
            "insert.horizontal_rule": self.editor.insert_horizontal_rule,
            "table.add_row": self.editor.add_table_row,
            "table.add_column": self.editor.add_table_column,
            "table.delete_row": self.editor.delete_table_row,
            "table.delete_column": self.editor.delete_table_column,
            "help.shortcuts": self.show_shortcuts,
        }
        for level in range(1, 7):
            callbacks[f"format.h{level}"] = partial(self.editor.set_heading, level)
        return callbacks

    def _create_menus(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        self._add_actions(file_menu, "file.new", "file.open")
        file_menu.addSeparator()
        self._add_actions(file_menu, "file.save", "file.save_as", "file.export_pdf")
        file_menu.addSeparator()
        self._add_actions(file_menu, "file.quit")

        edit_menu = menu_bar.addMenu("&Edit")
        self._add_actions(edit_menu, "edit.undo", "edit.redo")
        edit_menu.addSeparator()
        self._add_actions(edit_menu, "edit.cut", "edit.copy", "edit.paste", "edit.select_all")
        edit_menu.addSeparator()
        self._add_actions(edit_menu, "edit.find")

        format_menu = menu_bar.addMenu("F&ormat")
        self._add_actions(
            format_menu,
            "format.bold",
            "format.italic",
            "format.strike",
            "format.inline_code",
            "format.link",
        )
        headings = format_menu.addMenu("Headings")
        self._add_actions(headings, "format.paragraph", *(f"format.h{i}" for i in range(1, 7)))
        format_menu.addSeparator()
        self._add_actions(
            format_menu,
            "format.bullet_list",
            "format.numbered_list",
            "format.blockquote",
            "format.code_block",
        )

        insert_menu = menu_bar.addMenu("&Insert")
        self._add_actions(insert_menu, "insert.table", "insert.horizontal_rule")
        table_menu = insert_menu.addMenu("Table")
        self._add_actions(
            table_menu,
            "table.add_row",
            "table.add_column",
            "table.delete_row",
            "table.delete_column",
        )

        view_menu = menu_bar.addMenu("&View")
        theme_menu = view_menu.addMenu("Theme")
        group = QActionGroup(self)
        group.setExclusive(True)
        self.theme_actions: dict[str, QAction] = {}
        for index, (preference, label) in enumerate(THEME_CHOICES):
            if index in {1, 3}:
                theme_menu.addSeparator()
            action = QAction(label, self, checkable=True)
            action.triggered.connect(lambda _checked=False, value=preference: self.set_theme(value))
            group.addAction(action)
            theme_menu.addAction(action)
            self.theme_actions[preference] = action

        view_menu.addSeparator()
        opacity_menu = view_menu.addMenu("Background Opacity")
        opacity_control = QWidget(opacity_menu)
        opacity_layout = QHBoxLayout(opacity_control)
        opacity_layout.setContentsMargins(12, 7, 12, 7)
        opacity_layout.setSpacing(10)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal, opacity_control)
        self.opacity_slider.setObjectName("opacitySlider")
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setSingleStep(5)
        self.opacity_slider.setPageStep(10)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setMinimumWidth(150)
        self.opacity_slider.setToolTip("Set the opacity of WType's background surfaces")
        self.opacity_value = QLabel("100%", opacity_control)
        self.opacity_value.setObjectName("opacityValue")
        self.opacity_value.setMinimumWidth(38)
        opacity_layout.addWidget(self.opacity_slider, 1)
        opacity_layout.addWidget(self.opacity_value)
        opacity_action = QWidgetAction(self)
        opacity_action.setDefaultWidget(opacity_control)
        opacity_menu.addAction(opacity_action)
        self.opacity_slider.valueChanged.connect(self.set_background_opacity)

        self.blur_action = QAction("Background Blur", self, checkable=True)
        self.blur_action.setToolTip("Request blur through ext-background-effect-v1")
        self.blur_action.setStatusTip(
            "Request background blur from Niri or another supported Wayland compositor"
        )
        self.blur_action.toggled.connect(self.set_blur_enabled)
        view_menu.addAction(self.blur_action)

        help_menu = menu_bar.addMenu("&Help")
        self._add_actions(help_menu, "help.shortcuts")

    def _create_toolbar(self) -> None:
        toolbar = QToolBar("Formatting", self)
        toolbar.setObjectName("formattingToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        brand_label = QLabel("WType", toolbar)
        brand_label.setObjectName("brandLabel")
        toolbar.addWidget(brand_label)
        toolbar.addSeparator()

        toolbar_labels = {
            "format.bold": "Bold",
            "format.italic": "Italic",
            "format.strike": "Strike",
            "format.inline_code": "Code",
            "format.h1": "H1",
            "format.h2": "H2",
            "format.h3": "H3",
            "format.bullet_list": "Bullets",
            "format.numbered_list": "Numbers",
            "format.blockquote": "Quote",
            "format.code_block": "Code Block",
            "insert.table": "Table",
            "table.add_row": "+ Row",
            "table.add_column": "+ Column",
        }

        def add_toolbar_action(command_id: str) -> None:
            action = self.action_registry[command_id]
            action.setIconText(toolbar_labels[command_id])
            toolbar.addAction(action)

        for command_id in (
            "format.bold",
            "format.italic",
            "format.strike",
            "format.inline_code",
        ):
            add_toolbar_action(command_id)
        toolbar.addSeparator()
        for command_id in ("format.h1", "format.h2", "format.h3"):
            add_toolbar_action(command_id)
        toolbar.addSeparator()
        for command_id in (
            "format.bullet_list",
            "format.numbered_list",
            "format.blockquote",
            "format.code_block",
            "insert.table",
        ):
            add_toolbar_action(command_id)
        toolbar.addSeparator()
        for command_id in ("table.add_row", "table.add_column"):
            add_toolbar_action(command_id)
        self.addToolBar(toolbar)

    def _create_escape_action(self) -> None:
        escape = QAction(self)
        escape.setShortcut(QKeySequence(Qt.Key.Key_Escape))
        escape.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        escape.triggered.connect(self._close_transient_ui)
        self.addAction(escape)

    def _connect_signals(self) -> None:
        self.recovery_timer = QTimer(self)
        self.recovery_timer.setSingleShot(True)
        self.recovery_timer.setInterval(2000)
        self.recovery_timer.timeout.connect(self._write_recovery)
        self.editor.markdown_changed.connect(self._on_markdown_changed)
        self.editor.format_state_changed.connect(self._sync_format_actions)
        self.editor.table_state_changed.connect(self._sync_table_actions)
        self.editor.copyAvailable.connect(self.action_registry["edit.copy"].setEnabled)
        self.editor.copyAvailable.connect(self.action_registry["edit.cut"].setEnabled)
        self.editor.undoAvailable.connect(self.action_registry["edit.undo"].setEnabled)
        self.editor.redoAvailable.connect(self.action_registry["edit.redo"].setEnabled)
        self.action_registry["edit.copy"].setEnabled(False)
        self.action_registry["edit.cut"].setEnabled(False)
        self._sync_table_actions(False)

    def _add_actions(self, menu: QMenu, *command_ids: str) -> None:
        for command_id in command_ids:
            menu.addAction(self.action_registry[command_id])

    # Document lifecycle ------------------------------------------------
    def new_document(self) -> None:
        if not self._maybe_save_changes():
            return
        self.recovery_service.remove(self.session.document_id)
        self.session = DocumentSession()
        self._set_editor_markdown("")
        self._update_window_state()

    def open_document(self) -> None:
        if not self._maybe_save_changes():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Markdown",
            str(self.session.path.parent if self.session.path else Path.home()),
            "Markdown files (*.md *.markdown);;Text files (*.txt);;All files (*)",
        )
        if filename:
            self.open_path(Path(filename))

    def open_path(self, path: Path) -> bool:
        try:
            markdown, fingerprint = self.document_service.read(path)
        except (DocumentError, OSError) as exc:
            self._show_error("Could not open document", str(exc))
            return False
        self.recovery_service.remove(self.session.document_id)
        self._set_editor_markdown(markdown)
        normalized = self.editor.markdown()
        self.session = DocumentSession(
            path=path.expanduser().resolve(),
            current_markdown=normalized,
            saved_markdown=normalized,
            fingerprint=fingerprint,
        )
        self.editor.document().setModified(False)
        self._update_window_state()
        self.statusBar().showMessage(f"Opened {path.name}", 3000)
        return True

    def save_document(self) -> bool:
        if self.session.path is None:
            return self.save_document_as()
        return self._save_to_path(self.session.path)

    def save_document_as(self) -> bool:
        default = self.session.path or Path.home() / "Untitled.md"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Markdown",
            str(default),
            "Markdown files (*.md);;All files (*)",
        )
        if not filename:
            return False
        path = Path(filename)
        if path.suffix == "":
            path = path.with_suffix(".md")
        return self._save_to_path(path, save_as=True)

    def _save_to_path(self, path: Path, *, save_as: bool = False, force: bool = False) -> bool:
        expected = None if save_as or path != self.session.path else self.session.fingerprint
        try:
            fingerprint = self.document_service.write(
                path,
                self.session.current_markdown,
                expected=expected,
                force=force,
            )
        except ExternalChangeError:
            return self._resolve_external_change(path)
        except DocumentError as exc:
            self._show_error("Could not save document", str(exc))
            return False
        self.session.mark_saved(path.expanduser().resolve(), fingerprint)
        self.editor.document().setModified(False)
        self.recovery_service.remove(self.session.document_id)
        self._update_window_state()
        self.statusBar().showMessage(f"Saved {path.name}", 3000)
        return True

    def _resolve_external_change(self, path: Path) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("File changed outside WType")
        box.setText(f"{path.name} was changed by another application.")
        box.setInformativeText("Choose how to protect your work.")
        reload_button = box.addButton("Reload from Disk", QMessageBox.ButtonRole.AcceptRole)
        overwrite_button = box.addButton("Overwrite", QMessageBox.ButtonRole.DestructiveRole)
        save_as_button = box.addButton("Save As…", QMessageBox.ButtonRole.ActionRole)
        cancel_button = box.addButton(QMessageBox.StandardButton.Cancel)
        box.setDefaultButton(cancel_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is reload_button:
            return self.open_path(path)
        if clicked is overwrite_button:
            return self._save_to_path(path, force=True)
        if clicked is save_as_button:
            return self.save_document_as()
        return False

    def _maybe_save_changes(self) -> bool:
        if not self.session.dirty:
            return True
        result = QMessageBox.warning(
            self,
            "Unsaved changes",
            f"Save changes to {self.session.display_name}?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if result == QMessageBox.StandardButton.Save:
            return self.save_document()
        if result == QMessageBox.StandardButton.Discard:
            self.recovery_service.remove(self.session.document_id)
            return True
        return False

    # Recovery ----------------------------------------------------------
    def _write_recovery(self) -> None:
        try:
            self.recovery_service.save(self.session)
        except DocumentError as exc:
            self.statusBar().showMessage(f"Could not write recovery draft: {exc}", 5000)

    def _offer_recovery(self) -> None:
        pending = self.recovery_service.pending()
        if self.session.path is not None:
            target = str(self.session.path)
            pending = [record for record in pending if record.source_path == target]
        if not pending:
            return
        record = pending[0]
        source_name = (
            Path(record.source_path).name
            if record.source_path
            else "an untitled document"
        )
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Recovery draft found")
        box.setText(f"WType found unsaved work for {source_name}.")
        box.setInformativeText("Restore it in the editor or discard the recovery draft?")
        restore = box.addButton("Restore", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(restore)
        box.exec()
        if box.clickedButton() is restore:
            self._restore_record(record)
        elif box.clickedButton() is discard:
            self.recovery_service.remove(record.document_id)

    def _restore_record(self, record: RecoveryRecord) -> None:
        path = Path(record.source_path) if record.source_path else None
        saved_markdown = record.saved_markdown
        fingerprint = None
        if path is not None and path.exists():
            try:
                disk_markdown, fingerprint = self.document_service.read(path)
                temporary = MarkdownEditor()
                temporary.set_markdown(disk_markdown)
                saved_markdown = temporary.markdown()
                temporary.deleteLater()
            except DocumentError:
                path = None
        self.session = DocumentSession(
            document_id=record.document_id,
            path=path,
            current_markdown=record.markdown,
            saved_markdown=saved_markdown,
            fingerprint=fingerprint,
            recovered=True,
        )
        self._set_editor_markdown(record.markdown)
        self._update_window_state()
        self.statusBar().showMessage("Recovery draft restored; save to keep it", 6000)

    # PDF ---------------------------------------------------------------
    def export_pdf(self) -> None:
        default_name = (self.session.path.stem if self.session.path else "Untitled") + ".pdf"
        directory = self.session.path.parent if self.session.path else Path.home()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF",
            str(directory / default_name),
            "PDF files (*.pdf)",
        )
        if not filename:
            return
        destination = Path(filename)
        if destination.suffix.lower() != ".pdf":
            destination = destination.with_suffix(".pdf")
        try:
            self.pdf_exporter.export(self.session.current_markdown, destination)
        except (PdfExportError, OSError) as exc:
            self._show_error("Could not export PDF", str(exc))
            return
        self.statusBar().showMessage(f"Exported {destination.name}", 5000)

    # Find and help -----------------------------------------------------
    def show_find(self) -> None:
        self.find_bar.show()
        if self.editor.textCursor().hasSelection():
            self.find_input.setText(self.editor.textCursor().selectedText())
        self.find_input.selectAll()
        self.find_input.setFocus()

    def _hide_find(self) -> None:
        self.find_bar.hide()
        self.editor.setFocus()

    def _find(self, *, backwards: bool) -> None:
        query = self.find_input.text()
        if not query:
            return
        flags = QTextDocument.FindFlag.FindBackward if backwards else QTextDocument.FindFlag(0)
        if self.editor.find(query, flags):
            return
        cursor = self.editor.textCursor()
        cursor.movePosition(
            QTextCursor.MoveOperation.End
            if backwards
            else QTextCursor.MoveOperation.Start
        )
        self.editor.setTextCursor(cursor)
        self.editor.find(query, flags)

    def show_shortcuts(self) -> None:
        rows: list[str] = []
        for spec in COMMAND_SPECS:
            if not spec.shortcuts:
                continue
            action = self.action_registry.get(spec.command_id)
            if action is None:
                continue
            shortcuts = ", ".join(
                shortcut.toString(QKeySequence.SequenceFormat.NativeText)
                for shortcut in action.shortcuts()
            )
            rows.append(
                f"<tr><td style='padding:3px 18px 3px 0'>{html.escape(spec.label)}</td>"
                f"<td><code>{html.escape(shortcuts)}</code></td></tr>"
            )
        QMessageBox.information(
            self,
            "Keyboard shortcuts",
            "<h3>WType keyboard shortcuts</h3><table>" + "".join(rows) + "</table>",
        )

    def _close_transient_ui(self) -> None:
        if self.find_bar.isVisible():
            self._hide_find()
        else:
            self.editor.setFocus()

    # UI state ----------------------------------------------------------
    def _on_markdown_changed(self, markdown: str) -> None:
        if self._loading:
            return
        self.session.current_markdown = markdown
        self.recovery_timer.start()
        self._update_window_state()

    def _set_editor_markdown(self, markdown: str) -> None:
        self._loading = True
        try:
            self.editor.set_markdown(markdown)
        finally:
            self._loading = False

    def _sync_format_actions(self) -> None:
        self.action_registry.set_checked_states(self.editor.format_state())

    def _sync_table_actions(self, in_table: bool) -> None:
        for command_id in (
            "table.add_row",
            "table.add_column",
            "table.delete_row",
            "table.delete_column",
        ):
            self.action_registry[command_id].setEnabled(in_table)
            self.action_registry[command_id].setVisible(in_table)

    def _update_window_state(self) -> None:
        marker = "*" if self.session.dirty else ""
        self.setWindowTitle(f"{marker}{self.session.display_name} — WType")
        text = self.editor.toPlainText()
        words = len(text.split())
        self.statusBar().showMessage(f"{words} words   {len(text)} characters")
        self._sync_format_actions()

    def _restore_settings(self) -> None:
        geometry = self.settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        opacity_value = self.settings.value("appearance/background_opacity", 100, type=int)
        opacity = opacity_value if isinstance(opacity_value, int) else 100
        self.background_opacity = max(30, min(100, opacity))
        previous = self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(self.background_opacity)
        self.opacity_slider.blockSignals(previous)
        self.opacity_value.setText(f"{self.background_opacity}%")

        preference = self.settings.value("appearance/theme", "system", type=str)
        if preference not in {key for key, _label in THEME_CHOICES}:
            preference = "system"
        self.set_theme(preference)

        self.blur_enabled = bool(
            self.settings.value("appearance/background_blur", False, type=bool)
        )
        previous = self.blur_action.blockSignals(True)
        self.blur_action.setChecked(self.blur_enabled)
        self.blur_action.blockSignals(previous)
        self.background_effect.set_enabled(self.blur_enabled)

    def set_theme(self, preference: str) -> None:
        app = QApplication.instance()
        if not isinstance(app, QApplication):
            return
        self.theme_preference = preference
        is_wayland = app.platformName().lower() == "wayland"
        surface_opacity = self.background_opacity / 100 if is_wayland else 1.0
        self.setWindowOpacity(1.0 if is_wayland else self.background_opacity / 100)
        effective = apply_theme(app, preference, surface_opacity)
        self.editor.set_heading_color(THEMES[effective].accent)
        self.settings.setValue("appearance/theme", preference)
        for value, action in self.theme_actions.items():
            action.setChecked(value == preference)

    def set_background_opacity(self, opacity: int) -> None:
        self.background_opacity = max(30, min(100, opacity))
        self.opacity_value.setText(f"{self.background_opacity}%")
        if self.opacity_slider.value() != self.background_opacity:
            previous = self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(self.background_opacity)
            self.opacity_slider.blockSignals(previous)
        self.settings.setValue("appearance/background_opacity", self.background_opacity)
        self.set_theme(self.theme_preference)

    def set_blur_enabled(self, enabled: bool) -> None:
        self.blur_enabled = enabled
        if self.blur_action.isChecked() != enabled:
            previous = self.blur_action.blockSignals(True)
            self.blur_action.setChecked(enabled)
            self.blur_action.blockSignals(previous)
        self.settings.setValue("appearance/background_blur", enabled)
        applied = self.background_effect.set_enabled(enabled)
        if enabled and self.background_effect.available and applied:
            self.statusBar().showMessage("Background blur enabled", 3000)
        elif enabled and self.isVisible():
            self.statusBar().showMessage(
                self.background_effect.error or "Blur will be requested when the window is ready",
                5000,
            )

    def _initialize_background_effect(self) -> None:
        available = self.background_effect.initialize()
        if available:
            self.blur_action.setStatusTip(
                "Background blur is supported by this Wayland compositor"
            )
            if self.blur_enabled:
                self.statusBar().showMessage("Background blur enabled", 3000)
        else:
            self.blur_action.setStatusTip(self.background_effect.error)
            if self.blur_enabled:
                self.statusBar().showMessage(self.background_effect.error, 5000)

    def _show_error(self, title: str, detail: str) -> None:
        QMessageBox.critical(self, title, detail)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt override)
        if not self._maybe_save_changes():
            event.ignore()
            return
        self.recovery_timer.stop()
        self.recovery_service.remove(self.session.document_id)
        self.settings.setValue("window/geometry", self.saveGeometry())
        self.background_effect.close()
        event.accept()
