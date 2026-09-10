from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from wtype.theme import THEME_CHOICES


class AppearanceDialog(QDialog):
    def __init__(
        self, parent: QWidget, writing_size: int, interface_size: int, theme: str
    ) -> None:
        super().__init__(parent)
        self.setObjectName("appearanceDialog")
        self.setWindowTitle("Appearance")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self._controls: list[QWidget] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        title = QLabel("Appearance", self)
        title.setObjectName("appearanceTitle")
        layout.addWidget(title)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("appearanceScroll")
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("appearanceContent")
        sections = QVBoxLayout(content)
        sections.setContentsMargins(0, 0, 8, 0)
        sections.setSpacing(12)
        sections.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        self.writing_size_spin = self._size_input(9, 32, writing_size, "Writing text")
        self.interface_size_spin = self._size_input(9, 20, interface_size, "Interface text")
        sections.addWidget(self._section(
            "&Writing text", "Text in your document.", self.writing_size_spin,
            self._size_row(self.writing_size_spin, "writing"),
        ))
        sections.addWidget(self._section(
            "&Interface text", "Menus, buttons, and controls.", self.interface_size_spin,
            self._size_row(self.interface_size_spin, "interface"),
        ))
        self.theme_combo = QComboBox(self)
        self.theme_combo.setAccessibleName("Theme")
        self.theme_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        for key, label in THEME_CHOICES:
            self.theme_combo.addItem(label, key)
        self.theme_combo.setCurrentIndex(self.theme_combo.findData(theme))
        self._controls.append(self.theme_combo)
        sections.addWidget(self._section(
            "&Theme", "Colors for your writing space.", self.theme_combo, self.theme_combo,
        ))
        sections.addStretch()
        self.scroll_area.setWidget(content)
        layout.addWidget(self.scroll_area, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        self.reset_button = buttons.addButton(
            "Reset text sizes", QDialogButtonBox.ButtonRole.ResetRole
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.refresh_control_sizes()
        self.resize(480, 620)

    def _size_input(self, minimum: int, maximum: int, value: int, name: str) -> QSpinBox:
        spin = QSpinBox(self)
        spin.setRange(minimum, maximum)
        spin.setSuffix(" pt")
        spin.setValue(value)
        spin.setAccessibleName(name)
        spin.setKeyboardTracking(False)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._controls.append(spin)
        return spin

    def _size_row(self, spin: QSpinBox, name: str) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for text, step in (("−", -1), ("+", 1)):
            button = QToolButton(row)
            button.setObjectName(f"{name}{'Decrease' if step < 0 else 'Increase'}")
            button.setText(text)
            button.setProperty("wtypeIcon", "minus" if step < 0 else "plus")
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setIconSize(QSize(18, 18))
            button.setAccessibleName(
                f"{'Decrease' if step < 0 else 'Increase'} {name} text size"
            )
            button.setAutoRepeat(True)
            button.clicked.connect(lambda _checked=False, delta=step: spin.stepBy(delta))
            self._controls.append(button)
            layout.addWidget(button)
            if step < 0:
                layout.addWidget(spin, 1)
        return row

    def _section(self, title: str, description: str, buddy: QWidget, control: QWidget) -> QFrame:
        section = QFrame(self)
        section.setObjectName("appearanceSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(8)
        label = QLabel(title, section)
        label.setObjectName("appearanceSectionTitle")
        label.setBuddy(buddy)
        label.setWordWrap(True)
        hint = QLabel(description, section)
        hint.setObjectName("appearanceHint")
        hint.setWordWrap(True)
        layout.addWidget(label)
        layout.addWidget(hint)
        layout.addWidget(control)
        return section

    def refresh_control_sizes(self) -> None:
        # Explicit minimums keep the editable text area intact as the live UI font changes.
        # Extra content scrolls instead of squeezing the inputs into the available height.
        for control in self._controls:
            control.ensurePolished()
            control.setMinimumSize(control.sizeHint())
            control.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def fit_to_screen(self) -> None:
        screen = self.screen()
        if screen is not None:
            available = screen.availableGeometry()
            self.resize(
                min(max(480, self.width()), available.width() - 48),
                min(max(620, self.height()), available.height() - 64),
            )
