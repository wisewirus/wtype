from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
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


def _build_stylesheet(theme: Theme, background_opacity: float = 1.0) -> str:
    accent_text = "#ffffff" if not theme.dark else theme.editor
    window_background = _with_opacity(theme.window, background_opacity)
    surface_background = _with_opacity(theme.surface, background_opacity)
    elevated_background = _with_opacity(theme.elevated, background_opacity)
    editor_background = _with_opacity(theme.editor, background_opacity)
    editor_border = "#737780" if theme.dark else "#a5a9b1"
    body_font_stack = ", ".join(f'"{family}"' for family in BODY_FONT_FAMILIES)
    return f"""
QMainWindow {{
    background: transparent;
}}
QWidget {{
    color: {theme.text};
    font-family: {body_font_stack};
}}
QWidget#editorShell {{
    background: {window_background};
}}
QMenuBar {{
    background: {surface_background};
    color: {theme.text};
    border: 0;
    border-bottom: 1px solid {theme.border};
    padding: 4px 8px;
    font-size: 13px;
}}
QMenuBar::item {{
    background: transparent;
    border-radius: 6px;
    padding: 6px 10px;
}}
QMenuBar::item:selected {{
    background: {elevated_background};
}}
QMenu {{
    background: {elevated_background};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 9px;
    padding: 6px;
    font-size: 13px;
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
    background: {surface_background};
    border: 0;
    border-bottom: 1px solid {theme.border};
    spacing: 4px;
    padding: 8px 12px;
}}
QToolBar::separator {{
    background: {theme.border};
    width: 1px;
    margin: 5px 7px;
}}
QToolButton {{
    background: transparent;
    color: {theme.text};
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 7px 9px;
    font-size: 13px;
}}
QToolButton:hover {{
    background: {elevated_background};
    border-color: {theme.border};
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
    font-size: 15px;
    font-weight: 700;
    padding: 0 7px 0 2px;
}}
QTextEdit#editor {{
    background: {editor_background};
    color: {theme.text};
    border: 1px solid {editor_border};
    border-radius: 0;
    padding: 42px 54px;
    font-size: 12pt;
    selection-background-color: {theme.selection};
    selection-color: {theme.selected_text};
}}
QTextEdit#editor:focus {{
    border-color: {editor_border};
}}
QWidget#findBar {{
    background: {surface_background};
    border: 1px solid {theme.border};
    border-radius: 10px;
}}
QLineEdit {{
    background: {editor_background};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 7px;
    padding: 7px 10px;
    font-size: 13px;
    selection-background-color: {theme.selection};
    selection-color: {theme.selected_text};
}}
QLineEdit:focus {{
    border-color: {theme.accent};
}}
QPushButton {{
    background: {elevated_background};
    color: {theme.text};
    border: 1px solid {theme.border};
    border-radius: 7px;
    padding: 7px 12px;
    font-size: 13px;
}}
QPushButton:hover {{
    background: {theme.accent_hover};
    color: {accent_text};
    border-color: {theme.accent_hover};
}}
QPushButton:pressed {{
    background: {theme.accent};
}}
QStatusBar {{
    background: {surface_background};
    color: {theme.muted};
    border-top: 1px solid {theme.border};
    padding: 3px 10px;
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
QSlider#opacitySlider::groove:horizontal {{
    background: {theme.border};
    border: 0;
    border-radius: 2px;
    height: 4px;
}}
QSlider#opacitySlider::sub-page:horizontal {{
    background: {theme.accent};
    border-radius: 2px;
}}
QSlider#opacitySlider::handle:horizontal {{
    background: {theme.text};
    border: 2px solid {theme.accent};
    border-radius: 7px;
    height: 12px;
    width: 12px;
    margin: -5px 0;
}}
QLabel#opacityValue {{
    color: {theme.muted};
}}
"""


def apply_theme(app: QApplication, preference: str, background_opacity: float = 1.0) -> str:
    theme = resolve_theme(app, preference)
    app.setPalette(_build_palette(theme))
    app.setStyleSheet(_build_stylesheet(theme, background_opacity))
    return theme.key
