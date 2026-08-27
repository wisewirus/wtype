from __future__ import annotations

from collections.abc import Callable, Mapping

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget

from wtype.commands import COMMAND_SPECS, qt_shortcut


class ActionRegistry:
    """Owns the shared actions used by shortcuts, menus, and toolbars."""

    def __init__(
        self,
        parent: QWidget,
        callbacks: Mapping[str, Callable[[], object]],
    ) -> None:
        self._actions: dict[str, QAction] = {}
        for spec in COMMAND_SPECS:
            callback = callbacks.get(spec.command_id)
            if callback is None:
                continue
            action = QAction(spec.label, parent)
            action.setObjectName(spec.command_id)
            action.setCheckable(spec.checkable)
            action.setStatusTip(spec.status_tip)
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
            action.setShortcutVisibleInContextMenu(True)
            if spec.shortcuts:
                action.setShortcuts(
                    [QKeySequence(qt_shortcut(shortcut)) for shortcut in spec.shortcuts]
                )
            action.triggered.connect(lambda _checked=False, fn=callback: fn())
            parent.addAction(action)
            self._actions[spec.command_id] = action

    def __getitem__(self, command_id: str) -> QAction:
        return self._actions[command_id]

    def get(self, command_id: str) -> QAction | None:
        return self._actions.get(command_id)

    def set_checked_states(self, states: Mapping[str, bool]) -> None:
        for command_id, checked in states.items():
            action = self._actions.get(command_id)
            if action is None or not action.isCheckable():
                continue
            previous = action.blockSignals(True)
            action.setChecked(checked)
            action.blockSignals(previous)
