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
