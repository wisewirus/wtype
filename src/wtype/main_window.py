from __future__ import annotations

import html
from collections.abc import Callable
from functools import partial
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, QTimer
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
    QAbstractButton,
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from wtype import alternatives
from wtype.actions import ActionRegistry
from wtype.appearance import AppearanceDialog
from wtype.background_effect import BackgroundEffect
from wtype.commands import COMMAND_SPECS
from wtype.document_service import (
    DocumentError,
    DocumentService,
    ExternalChangeError,
)
from wtype.editor import MarkdownEditor
from wtype.icons import COMMAND_ICONS, line_icon
from wtype.models import DocumentSession
from wtype.pdf_export import PdfExporter, PdfExportError
from wtype.recovery import RecoveryRecord, RecoveryService
from wtype.theme import THEME_CHOICES, THEMES, Theme, apply_theme, apply_theme_stylesheet
from wtype.typography import BODY_FONT_FAMILIES
from wtype.widgets import ElidedLabel, SmoothSlider


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
        self.writing_font_size = 12
        self.interface_font_size = 10
        self.zoom_percent = 100
        self._zoom_timer = QTimer(self)
        self._zoom_timer.setSingleShot(True)
        self._zoom_timer.setInterval(16)
        self._zoom_timer.timeout.connect(self._apply_zoom)
        self._opacity_timer = QTimer(self)
        self._opacity_timer.setSingleShot(True)
        self._opacity_timer.setInterval(32)
        self._opacity_timer.timeout.connect(self._apply_opacity)
        self.appearance_dialog: AppearanceDialog | None = None
        self._alternatives_dismissed = False
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
        self._create_status_bar()
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
        self.editor_shell_layout = outer
        outer.setContentsMargins(20, 14, 20, 16)
        outer.setSpacing(12)
        header = QWidget(shell)
        header.setObjectName("documentHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 0, 4, 0)
        header_layout.setSpacing(12)
        self.document_icon = QLabel(header)
        self.document_icon.setObjectName("documentIcon")
        header_layout.addWidget(self.document_icon)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.document_title = ElidedLabel(header)
        self.document_title.setText("Untitled")
        self.document_title.setObjectName("documentTitle")
        self.document_title.setTextFormat(Qt.TextFormat.PlainText)
        self.document_title.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.document_state = QLabel("Ready to write", header)
        self.document_state.setObjectName("documentState")
        titles.addWidget(self.document_title)
        titles.addWidget(self.document_state)
        header_layout.addLayout(titles, 1)
        open_button = self._icon_button("open", "Open document", header)
        open_button.clicked.connect(self.open_document)
        save_button = QPushButton("Save", header)
        save_button.setObjectName("saveButton")
        save_button.setProperty("wtypeIcon", "save")
        save_button.setIconSize(QSize(16, 16))
        save_button.clicked.connect(self.save_document)
        self.appearance_button = self._icon_button("settings", "Appearance", header)
        self.appearance_button.setObjectName("appearanceButton")
        self.appearance_button.clicked.connect(self.show_appearance)
        header_layout.addWidget(self.appearance_button)
        header_layout.addWidget(open_button)
        header_layout.addWidget(save_button)
        outer.addWidget(header)
        outer.addWidget(self._create_alternatives_bar())
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.editor, 8)
        row.addStretch(1)
        outer.addLayout(row, 1)
        outer.addWidget(self.find_bar)
        return shell

    @staticmethod
    def _icon_button(name: str, label: str, parent: QWidget) -> QToolButton:
        button = QToolButton(parent)
        button.setProperty("wtypeIcon", name)
        button.setText(label)
        button.setToolTip(label)
        button.setAccessibleName(label)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setIconSize(QSize(18, 18))
        button.setAutoRaise(True)
        return button

    def _apply_icons(self, theme: Theme) -> None:
        icons = {name: line_icon(name, theme) for name in set(COMMAND_ICONS.values()) | {
            "file", "settings", "rename", "close", "up", "down", "more",
        }}
        for command_id, name in COMMAND_ICONS.items():
            action = self.action_registry.get(command_id)
            if action is not None:
                action.setIcon(icons[name])
                shortcut = action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
                action.setToolTip(action.text() + (f" ({shortcut})" if shortcut else ""))
        for button in self.findChildren(QAbstractButton):
            name = button.property("wtypeIcon")
            if isinstance(name, str) and name in icons:
                button.setIcon(icons[name])
        self.document_icon.setPixmap(icons["file"].pixmap(QSize(22, 22)))

    def _create_alternatives_bar(self) -> QWidget:
        self.alternatives_bar = QWidget(self)
        self.alternatives_bar.setObjectName("alternativesBar")
        row = QHBoxLayout(self.alternatives_bar)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(6)
        self.current_alternative_label = ElidedLabel(self.alternatives_bar)
        self.current_alternative_label.setTextFormat(Qt.TextFormat.PlainText)
        self.current_alternative_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        row.addWidget(self.current_alternative_label, 1)
        self.choose_alternative_button = QPushButton("Choose version…", self.alternatives_bar)
        self.choose_alternative_button.setObjectName("chooseAlternativeButton")
        self.choose_alternative_button.setProperty("wtypeIcon", "versions")
        self.choose_alternative_button.setIconSize(QSize(16, 16))
        self.choose_alternative_button.setToolTip("See every version and choose which one to use")
        self.alternatives_menu = QMenu(self.choose_alternative_button)
        self.alternatives_menu.setToolTipsVisible(True)
        self.alternatives_menu.aboutToShow.connect(self._populate_alternatives_menu)
        self.choose_alternative_button.setMenu(self.alternatives_menu)
        row.addWidget(self.choose_alternative_button)
        new = self._icon_button("plus", "New version", self.alternatives_bar)
        new.clicked.connect(self.new_alternative)
        rename = self._icon_button("rename", "Rename version", self.alternatives_bar)
        rename.clicked.connect(self._rename_alternative)
        self.remove_alternative_button = self._icon_button(
            "trash", "Remove version", self.alternatives_bar
        )
        self.remove_alternative_button.setToolTip("Remove this version; Undo brings it back")
        self.remove_alternative_button.clicked.connect(self._remove_alternative)
        row.addWidget(new)
        row.addWidget(rename)
        row.addWidget(self.remove_alternative_button)
        self.close_alternatives_button = self._icon_button(
            "close", "Close paragraph alternatives", self.alternatives_bar
        )
        self.close_alternatives_button.clicked.connect(self._hide_alternatives)
        row.addWidget(self.close_alternatives_button)
        self.alternatives_bar.hide()
        return self.alternatives_bar

    def new_alternative(self) -> None:
        if not alternatives.can_create(self.editor.textCursor()):
            self.statusBar().showMessage("Place the cursor in a text paragraph first", 3000)
            return
        self._alternatives_dismissed = False
        self.editor.setTextCursor(alternatives.create(self.editor.textCursor()))
        self.editor.setFocus()
        self._sync_alternatives()

    def show_alternatives(self) -> None:
        if alternatives.current_frame(self.editor.textCursor()) is None:
            self.new_alternative()
            return
        self._alternatives_dismissed = False
        self._sync_alternatives()

    def _hide_alternatives(self) -> None:
        self._alternatives_dismissed = True
        self.alternatives_bar.hide()
        self.editor.setFocus()

    def _switch_alternative(self, index: int) -> None:
        frame = alternatives.current_frame(self.editor.textCursor())
        if frame is not None:
            self.editor.setTextCursor(alternatives.switch(frame, index))
            self.editor.setFocus()
            self._sync_alternatives()

    def _populate_alternatives_menu(self) -> None:
        self.alternatives_menu.clear()
        frame = alternatives.current_frame(self.editor.textCursor())
        if frame is None:
            return
        value = alternatives.passage(frame)
        for index, version in enumerate(value.versions):
            label = version.name.replace("&", "&&")
            if index == value.active:
                label += " (current)"
            action = self.alternatives_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(index == value.active)
            action.setData(index)
            preview = QTextDocument()
            preview.setMarkdown(version.markdown)
            action.setToolTip(preview.toPlainText()[:300] or "Empty version")
            action.triggered.connect(
                lambda _checked=False, selected=index, passage_id=value.id:
                self._choose_alternative(passage_id, selected)
            )

    def _choose_alternative(self, passage_id: str, index: int) -> None:
        frame = alternatives.current_frame(self.editor.textCursor())
        if frame is not None and alternatives.passage(frame).id == passage_id:
            self._switch_alternative(index)

    def _rename_alternative(self) -> None:
        frame = alternatives.current_frame(self.editor.textCursor())
        if frame is None:
            return
        value = alternatives.passage(frame)
        name, accepted = QInputDialog.getText(
            self, "Rename paragraph version", "Name:",
            text=value.versions[value.active].name,
        )
        if accepted and name.strip():
            alternatives.rename(frame, name.strip()[:80])
            self._sync_alternatives()

    def _remove_alternative(self) -> None:
        frame = alternatives.current_frame(self.editor.textCursor())
        if frame is not None:
            self.editor.setTextCursor(alternatives.remove(frame))
            self.editor.setFocus()
            self._sync_alternatives()

    def _sync_alternatives(self) -> None:
        cursor = self.editor.textCursor()
        self.action_registry["edit.new_alternative"].setEnabled(alternatives.can_create(cursor))
        self.action_registry["edit.show_alternatives"].setEnabled(alternatives.can_create(cursor))
        frame = alternatives.current_frame(cursor)
        self.alternatives_bar.setVisible(frame is not None and not self._alternatives_dismissed)
        if frame is None:
            return
        value = alternatives.passage(frame)
        current = f"Current: {value.versions[value.active].name}"
        self.current_alternative_label.setText(current)
        self.current_alternative_label.setToolTip(current)
        self.choose_alternative_button.setText(f"Versions ({len(value.versions)})")
        self.remove_alternative_button.setText(
            "Remove version" if len(value.versions) > 1 else "Finish alternatives"
        )
        self.remove_alternative_button.setAccessibleName(self.remove_alternative_button.text())
        self.remove_alternative_button.setToolTip(self.remove_alternative_button.text())

    def _create_find_bar(self) -> QWidget:
        bar = QWidget(self)
        bar.setObjectName("findBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        search_label = QLabel("Find", bar)
        search_label.setObjectName("documentState")
        layout.addWidget(search_label)
        self.find_input = QLineEdit(bar)
        self.find_input.setClearButtonEnabled(True)
        self.find_input.setPlaceholderText("Search in this document")
        layout.addWidget(self.find_input, 1)
        previous = self._icon_button("up", "Previous match", bar)
        next_button = self._icon_button("down", "Next match", bar)
        close = self._icon_button("close", "Close search", bar)
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
            "file.export_active": self.export_active_markdown,
            "file.quit": self.close,
            "edit.undo": self.editor.undo,
            "edit.redo": self.editor.redo,
            "edit.cut": self.editor.cut,
            "edit.copy": self.editor.copy,
            "edit.paste": self.editor.paste,
            "edit.select_all": self.editor.selectAll,
            "edit.find": self.show_find,
            "edit.new_alternative": self.new_alternative,
            "edit.show_alternatives": self.show_alternatives,
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
            "view.zoom_in": lambda: self.set_zoom(self.zoom_percent + 10),
            "view.zoom_out": lambda: self.set_zoom(self.zoom_percent - 10),
            "view.zoom_reset": lambda: self.set_zoom(100),
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
        self._add_actions(file_menu, "file.export_active")
        file_menu.addSeparator()
        self._add_actions(file_menu, "file.quit")

        edit_menu = menu_bar.addMenu("&Edit")
        self._add_actions(edit_menu, "edit.show_alternatives", "edit.new_alternative")
        edit_menu.addSeparator()
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
        appearance = view_menu.addAction("Appearance…")
        appearance.triggered.connect(self.show_appearance)
        zoom_menu = view_menu.addMenu("Zoom")
        self._add_actions(zoom_menu, "view.zoom_in", "view.zoom_out", "view.zoom_reset")
        view_menu.addSeparator()
        theme_menu = view_menu.addMenu("Theme")
        group = QActionGroup(self)
        group.setExclusive(True)
        self.theme_actions: dict[str, QAction] = {}
        for preference, label in THEME_CHOICES:
            if preference in {"light", "dark"}:
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
        self.opacity_slider = SmoothSlider(opacity_control)
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
        self.opacity_slider.sliderReleased.connect(self._apply_opacity)

        self.blur_action = QAction("Background Blur", self, checkable=True)
        self.blur_action.setToolTip("Blur the desktop behind WType")
        self.blur_action.setStatusTip("Use native background blur when supported")
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
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        toolbar.setIconSize(QSize(18, 18))
        extension = toolbar.findChild(QToolButton, "qt_toolbar_ext_button")
        if extension is not None:
            extension.setProperty("wtypeIcon", "more")
            extension.setAccessibleName("More formatting tools")
            extension.setToolTip("More formatting tools")
            extension.setIconSize(QSize(12, 12))

        def add(command_id: str) -> None:
            action = self.action_registry[command_id]
            toolbar.addAction(action)
            button = toolbar.widgetForAction(action)
            if isinstance(button, QToolButton):
                button.setAccessibleName(action.text())

        add("edit.undo")
        add("edit.redo")
        toolbar.addSeparator()
        self.heading_button = self._icon_button("type", "Paragraph style", toolbar)
        self.heading_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.heading_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        heading_menu = QMenu(self.heading_button)
        self._add_actions(heading_menu, "format.paragraph", *(f"format.h{i}" for i in range(1, 7)))
        self.heading_button.setMenu(heading_menu)
        toolbar.addWidget(self.heading_button)
        toolbar.addSeparator()
        for command_id in ("format.bold", "format.italic", "format.strike", "format.inline_code"):
            add(command_id)
        toolbar.addSeparator()
        for command_id in ("format.bullet_list", "format.numbered_list", "format.blockquote"):
            add(command_id)
        toolbar.addSeparator()
        add("format.link")
        insert_button = self._icon_button("plus", "Insert", toolbar)
        insert_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        insert_menu = QMenu(insert_button)
        self._add_actions(
            insert_menu, "format.code_block", "insert.table", "insert.horizontal_rule"
        )
        insert_button.setMenu(insert_menu)
        toolbar.addWidget(insert_button)
        for command_id in ("table.add_row", "table.add_column"):
            add(command_id)
        toolbar.addSeparator()
        add("edit.show_alternatives")
        spacer = QWidget(toolbar)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        add("edit.find")
        self.editor_shell_layout.insertWidget(1, toolbar)

    def _create_status_bar(self) -> None:
        self.document_stats = ElidedLabel(self)
        self.document_stats.setObjectName("documentStats")
        self.document_stats.text_padding = 12
        self.statusBar().addWidget(self.document_stats, 1)
        # A message can arrive before the status bar is visible. Hide the stats
        # explicitly so Qt does not reveal them underneath that message on show.
        self.statusBar().messageChanged.connect(
            lambda message: self.document_stats.setVisible(not bool(message))
        )
        zoom_control = QWidget(self)
        layout = QHBoxLayout(zoom_control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        minus = self._icon_button("minus", "Zoom out", zoom_control)
        minus.setAccessibleName("Zoom out")
        minus.setToolTip("Zoom out")
        minus.clicked.connect(lambda: self.set_zoom(self.zoom_percent - 10))
        self.zoom_slider = SmoothSlider(zoom_control)
        self.zoom_slider.setObjectName("zoomSlider")
        self.zoom_slider.setRange(50, 200)
        self.zoom_slider.setSingleStep(10)
        self.zoom_slider.setPageStep(25)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(128)
        self.zoom_slider.setAccessibleName("Document zoom")
        self.zoom_slider.setToolTip("Zoom the writing area (50–200%)")
        self.zoom_slider.valueChanged.connect(self.set_zoom)
        self.zoom_slider.sliderReleased.connect(self._apply_zoom)
        plus = self._icon_button("plus", "Zoom in", zoom_control)
        plus.setAccessibleName("Zoom in")
        plus.setToolTip("Zoom in")
        plus.clicked.connect(lambda: self.set_zoom(self.zoom_percent + 10))
        self.zoom_value = QToolButton(zoom_control)
        self.zoom_value.setText("100%")
        self.zoom_value.setToolTip("Reset zoom to 100% (Ctrl/Cmd+Shift+0)")
        self.zoom_value.setAccessibleName("Reset document zoom to 100 percent")
        self.zoom_value.clicked.connect(lambda: self.set_zoom(100))
        for widget in (minus, self.zoom_slider, plus, self.zoom_value):
            layout.addWidget(widget)
        format_label = QLabel("Markdown", self)
        format_label.setObjectName("documentState")
        format_label.setToolTip("UTF-8 Markdown document")
        self.statusBar().addPermanentWidget(format_label)
        self.statusBar().addPermanentWidget(zoom_control)
        self.editor.zoom_requested.connect(
            lambda steps: self.set_zoom(self.zoom_percent + steps * 10)
        )

    def show_appearance(self) -> None:
        if self.appearance_dialog is None:
            dialog = AppearanceDialog(
                self, self.writing_font_size, self.interface_font_size, self.theme_preference
            )
            self.writing_size_spin = dialog.writing_size_spin
            self.interface_size_spin = dialog.interface_size_spin
            self.theme_combo = dialog.theme_combo
            self.writing_size_spin.valueChanged.connect(self.set_writing_font_size)
            self.interface_size_spin.valueChanged.connect(self.set_interface_font_size)
            self.theme_combo.currentIndexChanged.connect(
                lambda: self.set_theme(str(self.theme_combo.currentData()))
            )
            dialog.reset_button.clicked.connect(self._reset_text_sizes)
            self.appearance_dialog = dialog
            self._apply_icons(THEMES[self._effective_theme])
        self.appearance_dialog.refresh_control_sizes()
        self.appearance_dialog.fit_to_screen()
        self.appearance_dialog.show()
        self.appearance_dialog.raise_()
        self.appearance_dialog.activateWindow()

    def _reset_text_sizes(self) -> None:
        self.set_writing_font_size(12)
        self.set_interface_font_size(10)

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
            self._set_editor_markdown(markdown)
        except (DocumentError, OSError) as exc:
            self._show_error("Could not open document", str(exc))
            return False
        self.recovery_service.remove(self.session.document_id)
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
        try:
            self._set_editor_markdown(record.markdown)
        except DocumentError as exc:
            self._show_error("Could not restore draft", str(exc))
            return
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
        self._update_window_state()
        self.statusBar().showMessage("Recovery draft restored; save to keep it", 6000)

    # PDF ---------------------------------------------------------------
    def export_active_markdown(self) -> None:
        source = self.session.path or Path.home() / "Untitled.md"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export current paragraph versions",
            str(source.with_name(f"{source.stem}-current.md")), "Markdown files (*.md)",
        )
        if not filename:
            return
        destination = Path(filename).expanduser().resolve()
        if destination.suffix == "":
            destination = destination.with_suffix(".md")
        if self.session.path is not None and destination == self.session.path.resolve():
            self._show_error(
                "Choose another file", "Export to a different file to keep your alternatives."
            )
            return
        try:
            self.document_service.write(destination, self.editor.active_markdown(), force=True)
        except DocumentError as exc:
            self._show_error("Could not export document", str(exc))
            return
        self.statusBar().showMessage(f"Exported {destination.name}", 3000)

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
            self.pdf_exporter.export_document(self.editor.document(), destination)
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
        elif self.alternatives_bar.isVisible():
            self._hide_alternatives()
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
        level = self.editor.textCursor().blockFormat().headingLevel()
        self.heading_button.setText(f"Heading {level}" if level else "Paragraph")
        self._sync_alternatives()

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
        self.document_title.setText(self.session.display_name)
        self.document_title.setToolTip(str(self.session.path or self.session.display_name))
        self.document_state.setText(
            "Unsaved changes" if self.session.dirty else
            "Saved to this device" if self.session.path else "Ready to write"
        )
        text = self.editor.toPlainText()
        words = len(text.split())
        self.document_stats.setText(f"{words} words    ·    {len(text)} characters")
        self.document_stats.setToolTip(self.document_stats.text())
        self._sync_format_actions()

    def _restore_settings(self) -> None:
        geometry = self.settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        self.writing_font_size = self._read_size_setting("writing_font_size", 12, 9, 32)
        self.interface_font_size = self._read_size_setting("interface_font_size", 10, 9, 20)
        self.zoom_percent = self._read_size_setting("zoom_percent", 100, 50, 200)
        previous = self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(self.zoom_percent)
        self.zoom_slider.blockSignals(previous)
        self.zoom_value.setText(f"{self.zoom_percent}%")
        opacity_value = self.settings.value("appearance/background_opacity", 100, type=int)
        opacity = opacity_value if isinstance(opacity_value, int) else 100
        self.background_opacity = max(30, min(100, opacity))
        previous = self.opacity_slider.blockSignals(True)
        self.opacity_slider.setValue(self.background_opacity)
        self.opacity_slider.blockSignals(previous)
        self.opacity_value.setText(f"{self.background_opacity}%")

        preference = self.settings.value("appearance/theme", "system", type=str)
        if not isinstance(preference, str) or preference not in {
            key for key, _label in THEME_CHOICES
        }:
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
        uses_translucent_surfaces = app.platformName().lower() in {"wayland", "windows"}
        surface_opacity = self.background_opacity / 100 if uses_translucent_surfaces else 1.0
        self.setWindowOpacity(
            1.0 if uses_translucent_surfaces else self.background_opacity / 100
        )
        effective = apply_theme(
            app, preference, surface_opacity,
            interface_font_size=self.interface_font_size,
            editor_font_size=self.writing_font_size * self.zoom_percent / 100,
        )
        self._effective_theme = effective
        self._apply_icons(THEMES[effective])
        self._apply_editor_typography()
        self.editor.set_heading_color(THEMES[effective].accent)
        self.editor.set_code_background(THEMES[effective].code_background)
        self.settings.setValue("appearance/theme", preference)
        for value, action in self.theme_actions.items():
            action.setChecked(value == preference)
        if self.appearance_dialog is not None:
            previous = self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(self.theme_combo.findData(preference))
            self.theme_combo.blockSignals(previous)
            self.appearance_dialog.refresh_control_sizes()

    def _read_size_setting(self, key: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(str(self.settings.value(f"appearance/{key}", default)))
        except (ValueError, TypeError):
            value = default
        return max(minimum, min(maximum, value))

    def _apply_editor_typography(self) -> None:
        font = QFont()
        font.setFamilies(list(BODY_FONT_FAMILIES))
        font.setPointSizeF(self.writing_font_size * self.zoom_percent / 100)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        stylesheet = f"QTextEdit#editor {{ font-size: {font.pointSizeF():g}pt; }}"
        if self.editor.styleSheet() != stylesheet:
            self.editor.setStyleSheet(stylesheet)
        self.editor.configure_typography(font)
        self.editor.setMaximumWidth(round(920 * self.zoom_percent / 100))

    def set_writing_font_size(self, size: int) -> None:
        self.writing_font_size = max(9, min(32, size))
        self.settings.setValue("appearance/writing_font_size", self.writing_font_size)
        if self.appearance_dialog is not None:
            previous = self.writing_size_spin.blockSignals(True)
            self.writing_size_spin.setValue(self.writing_font_size)
            self.writing_size_spin.blockSignals(previous)
        self.set_theme(self.theme_preference)

    def set_interface_font_size(self, size: int) -> None:
        self.interface_font_size = max(9, min(20, size))
        self.settings.setValue("appearance/interface_font_size", self.interface_font_size)
        if self.appearance_dialog is not None:
            previous = self.interface_size_spin.blockSignals(True)
            self.interface_size_spin.setValue(self.interface_font_size)
            self.interface_size_spin.blockSignals(previous)
        self.set_theme(self.theme_preference)

    def set_zoom(self, percent: int) -> None:
        self.zoom_percent = max(50, min(200, percent))
        previous = self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(self.zoom_percent)
        self.zoom_slider.blockSignals(previous)
        self.zoom_value.setText(f"{self.zoom_percent}%")
        if self.zoom_slider.isSliderDown():
            if not self._zoom_timer.isActive():
                self._zoom_timer.start()
        else:
            self._apply_zoom()

    def _apply_zoom(self) -> None:
        self._zoom_timer.stop()
        self._apply_editor_typography()
        if not self.zoom_slider.isSliderDown():
            self.settings.setValue("appearance/zoom_percent", self.zoom_percent)

    def set_background_opacity(self, opacity: int) -> None:
        self.background_opacity = max(30, min(100, opacity))
        self.opacity_value.setText(f"{self.background_opacity}%")
        if self.opacity_slider.value() != self.background_opacity:
            previous = self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(self.background_opacity)
            self.opacity_slider.blockSignals(previous)
        if self.opacity_slider.isSliderDown():
            if not self._opacity_timer.isActive():
                self._opacity_timer.start()
        else:
            self._apply_opacity()

    def _apply_opacity(self) -> None:
        self._opacity_timer.stop()
        app = QApplication.instance()
        if isinstance(app, QApplication):
            if app.platformName().lower() in {"wayland", "windows"}:
                apply_theme_stylesheet(
                    app, THEMES[self._effective_theme], self.background_opacity / 100,
                    interface_font_size=self.interface_font_size,
                    editor_font_size=self.writing_font_size * self.zoom_percent / 100,
                )
            else:
                self.setWindowOpacity(self.background_opacity / 100)
        if not self.opacity_slider.isSliderDown():
            self.settings.setValue("appearance/background_opacity", self.background_opacity)

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
            self.blur_action.setStatusTip("Background blur is supported by this window system")
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
