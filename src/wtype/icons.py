"""Small, theme-aware line icons for WType's native controls."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from wtype.theme import Theme

_SHAPES = {
    "file": '<path d="M14 3H6a1 1 0 0 0-1 1v16h14V8z M14 3v5h5 M8 12h8 M8 16h6"/>',
    "new": '<path d="M14 3H6a1 1 0 0 0-1 1v16h14V8z M14 3v5h5 M9 14h6 M12 11v6"/>',
    "open": '<path d="M3 7V5h6l2 2h10v3 M3 10h18l-3 9H5z"/>',
    "save": '<path d="M5 3h12l4 4v14H3V3z M7 3v6h9V3 M7 21v-8h10v8"/>',
    "export": '<path d="M5 13v7h14v-7 M12 16V3 M7 8l5-5 5 5"/>',
    "undo": '<path d="M8 5 3 10l5 5 M3 10h11a6 6 0 0 1 6 6v3"/>',
    "redo": '<path d="m16 5 5 5-5 5 M21 10H10a6 6 0 0 0-6 6v3"/>',
    "bold": '<path d="M6 4h7a4 4 0 0 1 0 8H6z M6 12h8a4 4 0 0 1 0 8H6z"/>',
    "italic": '<path d="M10 4h9 M5 20h9 M15 4 9 20"/>',
    "strike": '<path d="M17 5c-2-2-10-3-10 2 0 2 2 3 5 4 M7 18c3 3 10 3 10-2 M3 12h18"/>',
    "code": '<path d="m8 6-6 6 6 6 M16 6l6 6-6 6 M14 4l-4 16"/>',
    "code-block": '<rect x="3" y="3" width="18" height="18" rx="3"/>'
                  '<path d="m8 9-3 3 3 3 M16 9l3 3-3 3"/>',
    "bullets": '<path d="M9 6h12 M9 12h12 M9 18h12"/>'
               '<circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/>'
               '<circle cx="4" cy="18" r="1"/>',
    "numbers": '<path d="M10 6h11 M10 12h11 M10 18h11 M3 3h1v6 M2 9h4 '
               'M2 15c0-3 4-3 4 0l-4 5h4"/>',
    "quote": '<path d="M3 6h7v7H6c0 3-1 4-3 5 M14 6h7v7h-4c0 3-1 4-3 5"/>',
    "link": '<path d="m10 8 3-3a4 4 0 0 1 6 6l-3 3 M14 16l-3 3a4 4 0 0 1-6-6l3-3 '
            'M8 16l8-8"/>',
    "table": '<rect x="3" y="4" width="18" height="16" rx="2"/>'
             '<path d="M3 9h18 M3 14h18 M9 4v16 M15 4v16"/>',
    "row": '<rect x="3" y="3" width="18" height="11" rx="2"/>'
           '<path d="M3 8h18 M12 17v5 M9 19.5h6"/>',
    "column": '<rect x="3" y="3" width="11" height="18" rx="2"/>'
              '<path d="M8 3v18 M17 12h5 M19.5 9v6"/>',
    "type": '<path d="M4 5h16 M12 5v15 M8 20h8 M4 5v3 M20 5v3"/>',
    "versions": '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/>'
                '<circle cx="18" cy="5" r="2"/><path d="M6 7v10 M18 7v3c0 4-12 0-12 7"/>',
    "search": '<circle cx="10" cy="10" r="6.5"/><path d="m15 15 6 6"/>',
    "settings": '<path d="M4 7h16 M4 17h16 M8 4v6 M16 14v6"/>',
    "plus": '<path d="M12 5v14 M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "close": '<path d="m6 6 12 12 M6 18 18 6"/>',
    "rename": '<path d="m14 4 6 6 M3 21l5-1L21 7l-5-5L3 15z"/>',
    "trash": '<path d="M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7"/>',
    "up": '<path d="m6 15 6-6 6 6"/>',
    "down": '<path d="m6 9 6 6 6-6"/>',
    "more": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/>'
            '<circle cx="19" cy="12" r="1"/>',
    "rule": '<path d="M4 12h16"/>',
}


def line_icon(name: str, theme: Theme) -> QIcon:
    result = QIcon()
    for mode, state, color in (
        (QIcon.Mode.Normal, QIcon.State.Off, theme.text),
        (QIcon.Mode.Normal, QIcon.State.On, theme.accent),
        (QIcon.Mode.Disabled, QIcon.State.Off, theme.muted),
    ):
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            f'fill="none" stroke="{color}" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round">{_SHAPES[name]}</svg>'
        )
        pixmap = QPixmap(48, 48)
        pixmap.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        pixmap.setDevicePixelRatio(2)
        result.addPixmap(pixmap, mode, state)
    return result


COMMAND_ICONS = {
    "file.new": "new", "file.open": "open", "file.save": "save", "file.save_as": "save",
    "file.export_pdf": "export", "file.export_active": "export",
    "edit.undo": "undo", "edit.redo": "redo", "edit.find": "search",
    "edit.show_alternatives": "versions", "edit.new_alternative": "versions",
    "format.bold": "bold", "format.italic": "italic", "format.strike": "strike",
    "format.inline_code": "code", "format.code_block": "code-block",
    "format.bullet_list": "bullets", "format.numbered_list": "numbers",
    "format.blockquote": "quote", "format.link": "link", "format.paragraph": "type",
    "insert.table": "table", "insert.horizontal_rule": "rule",
    "table.add_row": "row", "table.add_column": "column",
    "table.delete_row": "trash", "table.delete_column": "trash",
    "view.zoom_in": "plus", "view.zoom_out": "minus",
    **{f"format.h{level}": "type" for level in range(1, 7)},
}
