import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QPoint, Qt

from wtype.widgets import SmoothSlider


@pytest.mark.parametrize("reversed_track", [False, True])
def test_slider_direct_drag_and_keyboard(qtbot, reversed_track: bool) -> None:  # type: ignore[no-untyped-def]
    slider = SmoothSlider()
    qtbot.addWidget(slider)
    slider.setRange(50, 200)
    slider.setSingleStep(10)
    slider.resize(224, 28)
    slider.setInvertedAppearance(reversed_track)
    slider.show()
    with qtbot.waitSignal(slider.sliderReleased):
        qtbot.mousePress(slider, Qt.MouseButton.LeftButton, pos=QPoint(112, 14))
        assert slider.value() == 125
        qtbot.mouseMove(slider, QPoint(212, 14))
        assert slider.value() == (50 if reversed_track else 200)
        qtbot.mouseRelease(slider, Qt.MouseButton.LeftButton, pos=QPoint(12, 14))
    assert slider.value() == (200 if reversed_track else 50)
    assert not slider.isSliderDown()
    qtbot.keyClick(slider, Qt.Key.Key_Home)
    assert slider.value() == 50
    qtbot.keyClick(slider, Qt.Key.Key_Right)
    assert slider.value() == 60
    qtbot.keyClick(slider, Qt.Key.Key_End)
    assert slider.value() == 200
