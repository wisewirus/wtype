from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandSpec:
    command_id: str
    label: str
    shortcuts: tuple[str, ...] = ()
    checkable: bool = False
    status_tip: str = ""


COMMAND_SPECS: tuple[CommandSpec, ...] = (
    CommandSpec("file.new", "New", ("Primary+N",), status_tip="Create a new document"),
    CommandSpec("file.open", "Open…", ("Primary+O",), status_tip="Open a Markdown file"),
    CommandSpec("file.save", "Save", ("Primary+S",), status_tip="Save the current document"),
    CommandSpec("file.save_as", "Save As…", ("Primary+Shift+S",)),
    CommandSpec("file.export_pdf", "Export as PDF…", ("Primary+Shift+E",)),
    CommandSpec("file.quit", "Quit", ("Primary+Q",)),
    CommandSpec("edit.undo", "Undo", ("Primary+Z",)),
    CommandSpec("edit.redo", "Redo", ("Primary+Shift+Z", "Primary+Y")),
    CommandSpec("edit.cut", "Cut", ("Primary+X",)),
    CommandSpec("edit.copy", "Copy", ("Primary+C",)),
    CommandSpec("edit.paste", "Paste", ("Primary+V",)),
    CommandSpec("edit.select_all", "Select All", ("Primary+A",)),
    CommandSpec("edit.find", "Find", ("Primary+F",)),
    CommandSpec("format.bold", "Bold", ("Primary+B",), True),
    CommandSpec("format.italic", "Italic", ("Primary+I",), True),
    CommandSpec("format.strike", "Strikethrough", ("Primary+Shift+X",), True),
    CommandSpec("format.inline_code", "Inline Code", ("Primary+E",), True),
    CommandSpec("format.link", "Insert or Edit Link…", ("Primary+K",)),
    CommandSpec("format.paragraph", "Paragraph", ("Primary+0",), True),
    *(
        CommandSpec(
            f"format.h{level}",
            f"Heading {level}",
            (f"Primary+{level}",),
            True,
        )
        for level in range(1, 7)
    ),
    CommandSpec("format.bullet_list", "Bullet List", ("Primary+Shift+8",), True),
    CommandSpec("format.numbered_list", "Numbered List", ("Primary+Shift+7",), True),
    CommandSpec("format.blockquote", "Blockquote", ("Primary+Shift+Q",), True),
    CommandSpec("format.code_block", "Code Block", ("Primary+Shift+C",), True),
    CommandSpec("insert.table", "Insert Table", ("Primary+T",)),
    CommandSpec("insert.horizontal_rule", "Horizontal Rule", ("Primary+Shift+H",)),
    CommandSpec("table.add_row", "Add Row Below"),
    CommandSpec("table.add_column", "Add Column Right"),
    CommandSpec("table.delete_row", "Delete Row"),
    CommandSpec("table.delete_column", "Delete Column"),
    CommandSpec("help.shortcuts", "Keyboard Shortcuts", ("Primary+/",)),
)


COMMANDS_BY_ID = {spec.command_id: spec for spec in COMMAND_SPECS}


def qt_shortcut(portable_shortcut: str) -> str:
    """Translate the plan's Primary modifier to Qt's portable Ctrl notation.

    Qt maps Ctrl in a QKeySequence to the platform primary modifier and displays
    the native Command glyph on macOS.
    """

    return portable_shortcut.replace("Primary", "Ctrl")
