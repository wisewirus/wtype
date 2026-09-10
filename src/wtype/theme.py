from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

from wtype.typography import BODY_FONT_FAMILIES


@dataclass(frozen=True, slots=True)
class Theme:
    key: str
    label: str
    dark: bool
    window: str
    surface: str
    elevated: str
    editor: str
    text: str
    muted: str
    border: str
    accent: str
    accent_hover: str
    selection: str
    selected_text: str

    @property
    def code_background(self) -> QColor:
        if self.dark:
            return QColor(192, 192, 192, 28)
        return QColor(64, 64, 64, 20)


THEMES: dict[str, Theme] = {
    "light": Theme(
        "light",
        "WType Light",
        False,
        "#f4f5f7",
        "#eceef2",
        "#ffffff",
        "#ffffff",
        "#20242c",
        "#687080",
        "#d9dde5",
        "#5667e8",
        "#4556d6",
        "#cfd6ff",
        "#171a21",
    ),
    "catppuccin-latte": Theme(
        key="catppuccin-latte",
        label="Catppuccin Latte",
        dark=False,
        window="#e6e9ef",
        surface="#dce0e8",
        elevated="#eff1f5",
        editor="#eff1f5",
        text="#4c4f69",
        muted="#5c5f77",
        border="#bcc0cc",
        accent="#8839ef",
        accent_hover="#1e66f5",
        selection="#ccd0da",
        selected_text="#4c4f69",
    ),
    "solarized-light": Theme(
        key="solarized-light",
        label="Solarized Light",
        dark=False,
        window="#eee8d5",
        surface="#eee8d5",
        elevated="#fdf6e3",
        editor="#fdf6e3",
        text="#073642",
        muted="#586e75",
        border="#93a1a1",
        accent="#268bd2",
        accent_hover="#6c71c4",
        selection="#eee8d5",
        selected_text="#073642",
    ),
    "gruvbox-light": Theme(
        key="gruvbox-light",
        label="Gruvbox Light",
        dark=False,
        window="#f2e5bc",
        surface="#ebdbb2",
        elevated="#fbf1c7",
        editor="#fbf1c7",
        text="#3c3836",
        muted="#665c54",
        border="#bdae93",
        accent="#9d0006",
        accent_hover="#af3a03",
        selection="#d5c4a1",
        selected_text="#3c3836",
    ),
    "dark": Theme(
        "dark",
        "WType Dark",
        True,
        "#15171b",
        "#1c1f25",
        "#252932",
        "#1a1d23",
        "#e8eaf0",
        "#9ca3b3",
        "#343945",
        "#8da2fb",
        "#a7b7ff",
        "#3d4f82",
        "#ffffff",
    ),
    "tokyo-night": Theme(
        "tokyo-night",
        "Tokyo Night",
        True,
        "#1a1b26",
        "#1f2335",
        "#24283b",
        "#16161e",
        "#c0caf5",
        "#a9b1d6",
        "#3b4261",
        "#7aa2f7",
        "#89b4fa",
        "#33467c",
        "#f1f5ff",
    ),
    "catppuccin": Theme(
        "catppuccin",
        "Catppuccin Mocha",
        True,
        "#1e1e2e",
        "#181825",
        "#313244",
        "#11111b",
        "#cdd6f4",
        "#a6adc8",
        "#45475a",
        "#cba6f7",
        "#d7b9ff",
        "#45475a",
        "#f5e0ff",
    ),
    "everforest": Theme(
        "everforest",
        "Everforest Dark",
        True,
        "#2d353b",
        "#343f44",
        "#3d484d",
        "#272e33",
        "#d3c6aa",
        "#9da9a0",
        "#475258",
        "#a7c080",
        "#b6cf8e",
        "#4f5b58",
        "#f3f0df",
    ),
    "nord": Theme(
        "nord",
        "Nord",
        True,
        "#2e3440",
        "#3b4252",
        "#434c5e",
        "#292e39",
        "#eceff4",
        "#d8dee9",
        "#4c566a",
        "#88c0d0",
        "#8fbcbb",
        "#4c566a",
        "#ffffff",
    ),
    "gruvbox": Theme(
        "gruvbox",
        "Gruvbox Dark",
        True,
        "#282828",
        "#32302f",
        "#3c3836",
        "#1d2021",
        "#ebdbb2",
        "#bdae93",
        "#504945",
        "#d79921",
        "#fabd2f",
        "#665c54",
        "#1d2021",
    ),
    "equilibrium": Theme(
        "equilibrium",
        "Equilibrium",
        True,
        "#111318",
        "#181c25",
        "#222630",
        "#0c0e12",
        "#afaba2",
        "#817f78",
        "#303540",
        "#6a9ef2",
        "#82adf5",
        "#283b5d",
        "#f4f2ec",
    ),
    "solarized": Theme(
        "solarized",
        "Solarized Dark",
        True,
        "#002b36",
        "#073642",
        "#0b414d",
        "#00252e",
        "#93a1a1",
        "#839496",
        "#1b5662",
        "#268bd2",
        "#2aa198",
        "#16536d",
        "#fdf6e3",
    ),
    "adapta": Theme(
        "adapta",
        "Adapta Nokto",
        True,
        "#263238",
        "#2f3c43",
        "#37474f",
        "#202a2f",
        "#eceff1",
        "#b0bec5",
        "#455a64",
        "#00bcd4",
        "#26c6da",
        "#156a78",
        "#ffffff",
    ),
}

THEME_CHOICES: tuple[tuple[str, str], ...] = (
    ("system", "Follow system"),
    ("light", THEMES["light"].label),
    ("catppuccin-latte", THEMES["catppuccin-latte"].label),
    ("solarized-light", THEMES["solarized-light"].label),
    ("gruvbox-light", THEMES["gruvbox-light"].label),
    ("dark", THEMES["dark"].label),
    ("tokyo-night", THEMES["tokyo-night"].label),
    ("catppuccin", THEMES["catppuccin"].label),
    ("everforest", THEMES["everforest"].label),
    ("nord", THEMES["nord"].label),
    ("gruvbox", THEMES["gruvbox"].label),
    ("equilibrium", THEMES["equilibrium"].label),
    ("solarized", THEMES["solarized"].label),
    ("adapta", THEMES["adapta"].label),
)


def system_prefers_dark(app: QApplication) -> bool:
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return False


def resolve_theme(app: QApplication, preference: str) -> Theme:
    if preference == "system":
        preference = "dark" if system_prefers_dark(app) else "light"
    return THEMES.get(preference, THEMES["light"])


def _build_palette(theme: Theme) -> QPalette:
    palette = QPalette()
    colors = {
        QPalette.ColorRole.Window: theme.window,
        QPalette.ColorRole.WindowText: theme.text,
        QPalette.ColorRole.Base: theme.editor,
        QPalette.ColorRole.AlternateBase: theme.surface,
        QPalette.ColorRole.ToolTipBase: theme.elevated,
        QPalette.ColorRole.ToolTipText: theme.text,
        QPalette.ColorRole.Text: theme.text,
        QPalette.ColorRole.Button: theme.surface,
        QPalette.ColorRole.ButtonText: theme.text,
        QPalette.ColorRole.BrightText: theme.selected_text,
        QPalette.ColorRole.Link: theme.accent,
        QPalette.ColorRole.Highlight: theme.selection,
        QPalette.ColorRole.HighlightedText: theme.selected_text,
        QPalette.ColorRole.PlaceholderText: theme.muted,
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(theme.muted))
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(theme.muted),
    )
    return palette


def _with_opacity(color: str, opacity: float) -> str:
    opacity = max(0.0, min(1.0, opacity))
    if opacity >= 0.999:
        return color
    value = QColor(color)
    return f"rgba({value.red()}, {value.green()}, {value.blue()}, {round(opacity * 255)})"


def _build_stylesheet(
    theme: Theme, background_opacity: float = 1.0,
    *, interface_font_size: int = 10, editor_font_size: float = 12,
) -> str:
    window_background = _with_opacity(theme.window, background_opacity)
    surface_background = _with_opacity(theme.surface, background_opacity)
    elevated_background = _with_opacity(theme.elevated, background_opacity)
    editor_background = _with_opacity(theme.editor, background_opacity)
    editor_border = theme.border
    body_font_stack = ", ".join(f'"{family}"' for family in BODY_FONT_FAMILIES)
    chevron = (Path(__file__).with_name("assets") / "chevron-down.svg").as_posix()
    return f"""
QMainWindow {{
    background: transparent;
}}
QWidget {{
    color: {theme.text};
    font-family: {body_font_stack};
    font-size: {interface_font_size}pt;
}}
QDialog {{
    background: {theme.window};
}}
QScrollArea#appearanceScroll, QWidget#appearanceContent {{
    background: {theme.window};
    border: 0;
}}
QFrame#appearanceSection {{
    background: {theme.surface};
    border: 1px solid {theme.border};
    border-radius: 10px;
}}
QLabel#appearanceSectionTitle {{
    font-weight: 600;
}}
QLabel#appearanceHint {{
    color: {theme.muted};
}}
QDialog#appearanceDialog QSpinBox, QDialog#appearanceDialog QComboBox {{
    background: {theme.editor};
}}
QDialog#appearanceDialog QToolButton {{
    background: {theme.elevated};
    border-color: {theme.border};
    padding: 7px 14px;
}}
QDialog#appearanceDialog QToolButton:hover {{
    background: {theme.selection};
    border-color: {theme.accent};
}}
QLabel#documentTitle {{
    font-size: {interface_font_size + 2}pt;
    font-weight: 600;
}}
QLabel#appearanceTitle {{
    font-size: {interface_font_size + 5}pt;
    font-weight: 600;
}}
QLabel#documentState, QLabel#documentStats {{
    color: {theme.muted};
}}
QPushButton#saveButton {{
    background: {theme.selection};
    color: {theme.selected_text};
    border-color: {theme.border};
    padding-left: 14px;
    padding-right: 14px;
}}
QPushButton#saveButton:hover {{
    background: {theme.selection};
    border-color: {theme.accent};
}}
QPushButton#chooseAlternativeButton {{
    background: {elevated_background};
    color: {theme.text};
    border-color: {theme.border};
    padding-right: 24px;
}}
QComboBox QAbstractItemView {{
    background: {theme.elevated};
    selection-background-color: {theme.selection};
    selection-color: {theme.selected_text};
}}
QWidget#editorShell {{
    background: {window_background};
}}
QMenuBar {{
    background: {window_background};
    color: {theme.text};
    border: 0;
    padding: 2px 12px;
}}
QMenuBar::item {{
    background: transparent;
    border-radius: 6px;
    padding: 5px 9px;
}}
QMenuBar::item:selected {{
    background: {elevated_background};
}}
QMenu {{
    background: {elevated_background};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    border-radius: 6px;
    padding: 7px 30px 7px 12px;
}}
QMenu::item:selected {{
    background: {theme.selection};
    color: {theme.selected_text};
}}
QMenu::item:disabled {{
    color: {theme.muted};
}}
QMenu::separator {{
    background: {theme.border};
    height: 1px;
    margin: 5px 8px;
}}
QToolBar {{
    background: transparent;
    border: 0;
    border-bottom: 1px solid {theme.border};
    spacing: 3px;
    padding: 2px 0 8px 0;
}}
QToolBar::separator {{
    background: {theme.border};
    width: 1px;
    margin: 7px 6px;
}}
QToolButton {{
    background: transparent;
    color: {theme.text};
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 7px;
}}
QToolButton:hover {{
    background: {elevated_background};
    border-color: {theme.border};
}}
QToolButton:focus {{
    border-color: {theme.accent};
}}
QToolButton[popupMode="2"] {{
    padding-right: 16px;
}}
QToolButton#qt_toolbar_ext_button {{
    padding: 0;
    border: 0;
}}
QToolButton::menu-indicator, QPushButton::menu-indicator {{
    image: url("{chevron}");
    width: 12px;
    height: 12px;
    subcontrol-position: right center;
    right: 5px;
}}
QToolButton:pressed, QToolButton:checked {{
    background: {theme.selection};
    color: {theme.selected_text};
    border-color: {theme.accent};
}}
QToolButton:disabled {{
    color: {theme.muted};
}}
QLabel#brandLabel {{
    color: {theme.text};
    font-size: {interface_font_size + 3}pt;
    font-weight: 700;
    padding: 0 7px 0 2px;
}}
QTextEdit#editor {{
    background: {editor_background};
    color: {theme.text};
    border: 1px solid {editor_border};
    border-radius: 12px;
    padding: 32px 36px;
    font-size: {editor_font_size}pt;
    selection-background-color: {theme.selection};
    selection-color: {theme.selected_text};
}}
QTextEdit#editor:focus {{
    border-color: {editor_border};
}}
QWidget#findBar, QWidget#alternativesBar {{
    background: {surface_background};
    border: 1px solid {theme.border};
    border-radius: 7px;
}}
QLineEdit, QSpinBox, QComboBox {{
    background: {editor_background};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: {theme.selection};
    selection-color: {theme.selected_text};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {theme.accent};
}}
QComboBox {{
    padding-right: 28px;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: 0;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: url("{chevron}");
    width: 12px;
    height: 12px;
}}
QPushButton {{
    background: {elevated_background};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 6px;
    padding: 7px 12px;
}}
QPushButton:hover {{
    background: {theme.selection};
    color: {theme.selected_text};
    border-color: {theme.accent};
}}
QPushButton:focus {{
    border-color: {theme.accent};
}}
QPushButton:pressed {{
    background: {theme.accent};
}}
QStatusBar {{
    background: {window_background};
    color: {theme.muted};
    border-top: 1px solid {theme.border};
    padding: 2px 16px;
}}
QStatusBar::item {{
    border: 0;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 5px 2px;
}}
QScrollBar::handle:vertical {{
    background: {theme.border};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {theme.muted};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
    border: 0;
}}
QToolTip {{
    background: {elevated_background};
    color: {theme.text};
    border: 1px solid {theme.border};
    padding: 5px;
}}
"""


def apply_theme(
    app: QApplication, preference: str, background_opacity: float = 1.0,
    *, interface_font_size: int = 10, editor_font_size: float = 12,
) -> str:
    theme = resolve_theme(app, preference)
    font = QFont(app.font())
    font.setFamilies(list(BODY_FONT_FAMILIES))
    font.setPointSize(interface_font_size)
    font.setFixedPitch(False)
    app.setFont(font)
    app.setPalette(_build_palette(theme))
    apply_theme_stylesheet(
        app, theme, background_opacity,
        interface_font_size=interface_font_size, editor_font_size=editor_font_size,
    )
    return theme.key


def apply_theme_stylesheet(
    app: QApplication, theme: Theme, background_opacity: float = 1.0,
    *, interface_font_size: int = 10, editor_font_size: float = 12,
) -> None:
    app.setStyleSheet(_build_stylesheet(
        theme, background_opacity,
        interface_font_size=interface_font_size, editor_font_size=editor_font_size,
    ))
