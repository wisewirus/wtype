from wtype.commands import COMMANDS_BY_ID, qt_shortcut


def test_speed_shortcuts_are_explicit() -> None:
    expected = {
        "format.bold": "Primary+B",
        "format.italic": "Primary+I",
        "format.h2": "Primary+2",
        "insert.table": "Primary+T",
        "file.export_pdf": "Primary+Shift+E",
    }
    for command_id, shortcut in expected.items():
        assert COMMANDS_BY_ID[command_id].shortcuts[0] == shortcut


def test_primary_shortcuts_translate_to_qt_portable_notation() -> None:
    assert qt_shortcut("Primary+Shift+X") == "Ctrl+Shift+X"


def test_command_ids_are_unique() -> None:
    assert len(COMMANDS_BY_ID) == len(set(COMMANDS_BY_ID))
