from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QFontDatabase

from wtype.app import _load_bundled_fonts


def test_bundled_fonts_are_loadable(qapp) -> None:  # type: ignore[no-untyped-def]
    assets = Path(__file__).parents[1] / "src" / "wtype" / "assets"

    assert (assets / "Outfit-Regular.ttf").is_file()
    assert (assets / "Outfit-SemiBold.ttf").is_file()
    assert (assets / "Outfit-Bold.ttf").is_file()
    assert (assets / "OFL-Outfit.txt").is_file()
    assert (assets / "CascadiaMono-Regular.ttf").is_file()
    assert (assets / "OFL-Cascadia.txt").is_file()
    assert (assets / "Vazirmatn-Regular.ttf").is_file()
    assert (assets / "OFL-Vazirmatn.txt").is_file()
    assert _load_bundled_fonts() == "Outfit"
    assert "Outfit" in QFontDatabase.families()
    assert "Cascadia Mono" in QFontDatabase.families()
    assert "Vazirmatn" in QFontDatabase.families()
    assert QFontDatabase.WritingSystem.Arabic in QFontDatabase.writingSystems(
        "Vazirmatn"
    )
