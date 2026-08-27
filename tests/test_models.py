from pathlib import Path

from wtype.models import DiskFingerprint, DocumentSession


def test_document_session_dirty_lifecycle() -> None:
    session = DocumentSession(current_markdown="same", saved_markdown="same")
    assert not session.dirty

    session.current_markdown = "changed"
    assert session.dirty

    fingerprint = DiskFingerprint(7, 1, "abc")
    session.mark_saved(Path("notes.md"), fingerprint)
    assert not session.dirty
    assert session.fingerprint == fingerprint


def test_untitled_display_name() -> None:
    assert DocumentSession().display_name == "Untitled"
