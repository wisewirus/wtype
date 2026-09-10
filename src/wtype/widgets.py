from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPointF, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import (
    QColor,
    QEnterEvent,
    QFocusEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPalette,
    QPen,
)
from PySide6.QtWidgets import QLabel, QSizePolicy, QSlider, QStyle, QStyleOptionSlider, QWidget


class ElidedLabel(QLabel):
    """Keep the full accessible text while fitting a label into a narrow layout."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.text_padding = 0
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(QPalette.ColorRole.WindowText))
        rect = self.contentsRect().adjusted(self.text_padding, 0, -self.text_padding, 0)
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, rect.width())
        painter.drawText(rect, self.alignment(), text)


class SmoothSlider(QSlider):
    """Horizontal slider with direct dragging and an animated, generous hit area."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(28)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._hovered = False
        self._emphasis = 0.0
        self._drag_offset = 0.0
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(130)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._animate)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(160, 28)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(70, 28)

    def _animate(self, value: object) -> None:
        self._emphasis = float(str(value))
        self.update()

    def _update_emphasis(self) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._emphasis)
        self._animation.setEndValue(float(self._hovered or self.hasFocus() or self.isSliderDown()))
        self._animation.start()

    def _upside_down(self) -> bool:
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        return option.upsideDown

    def _thumb_x(self) -> float:
        span = max(1, self.maximum() - self.minimum())
        fraction = (self.sliderPosition() - self.minimum()) / span
        if self._upside_down():
            fraction = 1 - fraction
        return 12 + fraction * max(0, self.width() - 24)

    def _move_thumb(self, x: float) -> None:
        span = max(1, self.width() - 24)
        position = max(0, min(span, round(x - self._drag_offset - 12)))
        self.setSliderPosition(QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), position, span, self._upside_down()
        ))
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        offset = event.position().x() - self._thumb_x()
        self._drag_offset = offset if abs(offset) <= 10 else 0.0
        self.setSliderDown(True)
        self._move_thumb(event.position().x())
        self._update_emphasis()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.isSliderDown():
            self._move_thumb(event.position().x())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.isSliderDown():
            self._move_thumb(event.position().x())
            self.setSliderDown(False)
            self._update_emphasis()
            event.accept()
        else:
            event.ignore()

    def enterEvent(self, event: QEnterEvent) -> None:  # noqa: N802
        self._hovered = True
        self._update_emphasis()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:  # noqa: N802
        self._hovered = False
        self._update_emphasis()
        super().leaveEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:  # noqa: N802
        self._update_emphasis()
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:  # noqa: N802
        self._update_emphasis()
        super().focusOutEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        accent = palette.color(QPalette.ColorRole.Link)
        muted = palette.color(QPalette.ColorRole.PlaceholderText)
        if not self.isEnabled():
            accent = muted
        track = QColor(muted)
        track.setAlpha(55)
        y = self.height() / 2
        x = self._thumb_x()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(12, y - 2, max(0, self.width() - 24), 4), 2, 2)
        start = x if self._upside_down() else 12
        end = self.width() - 12 if self._upside_down() else x
        painter.setBrush(accent)
        painter.drawRoundedRect(QRectF(start, y - 2, max(0, end - start), 4), 2, 2)
        if self._emphasis > 0 and self.isEnabled():
            halo = QColor(accent)
            halo.setAlpha(round(30 * self._emphasis))
            painter.setBrush(halo)
            painter.drawEllipse(QPointF(x, y), 11, 11)
        radius = 5.5 + self._emphasis
        painter.setPen(QPen(accent, 1.5))
        painter.setBrush(palette.color(QPalette.ColorRole.Base))
        painter.drawEllipse(QPointF(x, y), radius, radius)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawEllipse(QPointF(x, y), 2, 2)
