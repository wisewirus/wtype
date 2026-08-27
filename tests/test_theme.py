import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from wtype.theme import THEME_CHOICES, THEMES, apply_theme


def test_requested_theme_families_are_available() -> None:
    keys = {key for key, _label in THEME_CHOICES}

    assert {
        "tokyo-night",
        "catppuccin",
        "everforest",
        "nord",
        "gruvbox",
        "equilibrium",
        "solarized",
        "adapta",
    } <= keys


@pytest.mark.parametrize("theme_key", THEMES)
def test_theme_applies_its_palette(qapp, theme_key: str) -> None:  # type: ignore[no-untyped-def]
    assert isinstance(qapp, QApplication)

    effective = apply_theme(qapp, theme_key)

    assert effective == theme_key
    assert THEMES[theme_key].window in qapp.styleSheet()


def test_translucent_theme_uses_outfit_and_rectangular_neutral_editor(qapp) -> None:  # type: ignore[no-untyped-def]
    apply_theme(qapp, "tokyo-night", 0.72)

    stylesheet = qapp.styleSheet()
    assert 'font-family: "Outfit", "Vazirmatn"' in stylesheet
    assert "background: rgba(" in stylesheet
    assert "border-radius: 0;" in stylesheet
    assert "QTextEdit#editor:focus {\n    border-color: #737780;" in stylesheet


def test_code_backgrounds_are_translucent_neutral_grays() -> None:
    for theme in THEMES.values():
        color = theme.code_background
        assert color.red() == color.green() == color.blue()
        assert 0 < color.alpha() < 255
