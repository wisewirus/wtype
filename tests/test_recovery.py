from pathlib import Path

from wtype.models import DocumentSession
from wtype.recovery import RECOVERY_SCHEMA_VERSION, RecoveryService


def test_dirty_document_round_trips_through_recovery(tmp_path: Path) -> None:
    service = RecoveryService(tmp_path / "recovery")
    session = DocumentSession(
        document_id="draft-1",
        path=tmp_path / "notes.md",
        current_markdown="unsaved سلام",
        saved_markdown="saved",
    )

    saved = service.save(session)
    pending = service.pending()

    assert saved is not None
    assert saved.schema_version == RECOVERY_SCHEMA_VERSION
    assert pending == [saved]


def test_clean_document_removes_recovery(tmp_path: Path) -> None:
    service = RecoveryService(tmp_path / "recovery")
    session = DocumentSession(
        document_id="draft-2",
        current_markdown="changed",
        saved_markdown="saved",
    )
    service.save(session)
    session.saved_markdown = session.current_markdown

    assert service.save(session) is None
    assert service.pending() == []


def test_corrupt_and_future_records_are_ignored(tmp_path: Path) -> None:
    directory = tmp_path / "recovery"
    directory.mkdir()
    (directory / "broken.json").write_text("not json", encoding="utf-8")
    (directory / "future.json").write_text(
        '{"schema_version":999,"document_id":"future","source_path":null,'
        '"markdown":"x","saved_markdown":"","updated_at":1}',
        encoding="utf-8",
    )

    assert RecoveryService(directory).pending() == []
