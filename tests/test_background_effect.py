import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QWidget

from wtype.background_effect import BackgroundEffect


def test_blur_setting_degrades_safely_without_wayland(qapp) -> None:  # type: ignore[no-untyped-def]
    window = QWidget()
    effect = BackgroundEffect(window)

    assert not effect.initialize()
    assert not effect.set_enabled(True)
    assert effect.enabled
    assert not effect.available
    assert effect.error
