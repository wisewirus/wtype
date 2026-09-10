"""Undoable passage alternatives, stored in portable Markdown comments."""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import asdict, dataclass
from uuid import uuid4

from PySide6.QtGui import (
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextDocumentFragment,
    QTextFormat,
    QTextFrame,
    QTextFrameFormat,
)

from wtype.document_service import DocumentError

PROPERTY = int(QTextFormat.Property.UserProperty) + 101
DIALECT = QTextDocument.MarkdownFeature.MarkdownDialectGitHub
_OPEN = re.compile(
    r"^<!-- wtype:alternatives:v1 ([a-f0-9]{32}) ([A-Za-z0-9+/=]+) -->[ \t]*$",
    re.MULTILINE,
)


def _outside_fences(markdown: str) -> str:
    """Mask code fences without changing offsets into the original Markdown."""
    lines = []
    fence = ""
    for line in markdown.splitlines(keepends=True):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line.rstrip("\r\n"))
        if fence:
            lines.append(re.sub(r"[^\r\n]", " ", line))
            if (
                match and match[1][0] == fence[0]
                and len(match[1]) >= len(fence) and not match[2].strip()
            ):
                fence = ""
        elif match:
            fence = match[1]
            lines.append(re.sub(r"[^\r\n]", " ", line))
        else:
            lines.append(line)
    return "".join(lines)


@dataclass
class Version:
    name: str
    markdown: str


@dataclass
class Passage:
    id: str
    active: int
    versions: list[Version]

    def encode(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def decode(cls, text: str) -> Passage:
        try:
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError
            identifier, active, versions = value["id"], value["active"], value["versions"]
            if not isinstance(identifier, str) or not re.fullmatch(r"[a-f0-9]{32}", identifier):
                raise ValueError
            if not isinstance(versions, list) or not versions:
                raise ValueError
            if type(active) is not int or not 0 <= active < len(versions):
                raise ValueError
            parsed = []
            for version in versions:
                if not isinstance(version, dict):
                    raise ValueError
                name, markdown = version["name"], version["markdown"]
                if not isinstance(name, str) or not name.strip() or not isinstance(markdown, str):
                    raise ValueError
                parsed.append(Version(name, markdown))
            return cls(identifier, active, parsed)
        except (ValueError, KeyError, TypeError) as exc:
            raise DocumentError("The paragraph alternatives in this file are damaged.") from exc


def contents(frame: QTextFrame) -> QTextCursor:
    cursor = frame.firstCursorPosition()
    cursor.setPosition(frame.lastPosition(), QTextCursor.MoveMode.KeepAnchor)
    return cursor


def current_frame(cursor: QTextCursor) -> QTextFrame | None:
    frame = cursor.currentFrame()
    while frame is not None:
        if frame.frameFormat().hasProperty(PROPERTY):
            return frame
        frame = frame.parentFrame()
    return None


def passage(frame: QTextFrame) -> Passage:
    result = Passage.decode(str(frame.frameFormat().property(PROPERTY)))
    result.versions[result.active].markdown = _selection_markdown(contents(frame))
    return result


def _selection_markdown(cursor: QTextCursor) -> str:
    if not cursor.hasSelection():
        return ""
    document = QTextDocument()
    target = QTextCursor(document)
    target.insertFragment(cursor.selection())
    first = QTextCursor(document.begin())
    fmt = cursor.document().findBlock(cursor.selectionStart()).blockFormat()
    fmt.setObjectIndex(first.blockFormat().objectIndex())
    first.setBlockFormat(fmt)
    return document.toMarkdown(DIALECT)


def _set_passage(frame: QTextFrame, value: Passage) -> None:
    fmt = frame.frameFormat()
    fmt.setProperty(PROPERTY, value.encode())
    frame.setFrameFormat(fmt)


def replace_contents(frame: QTextFrame, markdown: str) -> None:
    parsed = QTextDocument()
    parsed.setDefaultFont(frame.document().defaultFont())
    parsed.setMarkdown(markdown, DIALECT)
    cursor = contents(frame)
    cursor.removeSelectedText()
    cursor.setBlockFormat(QTextBlockFormat())
    cursor.setCharFormat(QTextCharFormat())
    cursor.insertFragment(QTextDocumentFragment(parsed))
    # Qt merges the first inserted block into its destination. Restore its semantic
    # format explicitly so a heading/quote cannot leak from one version to another.
    first = frame.firstCursorPosition()
    fmt = parsed.begin().blockFormat()
    fmt.setObjectIndex(first.blockFormat().objectIndex())
    first.setBlockFormat(fmt)


def can_create(cursor: QTextCursor) -> bool:
    frame = current_frame(cursor)
    if frame is not None:
        return (
            frame.firstPosition() <= cursor.selectionStart()
            <= cursor.selectionEnd() <= frame.lastPosition()
        )
    # Start with a prose paragraph. A version can grow into several paragraphs as it is edited.
    if cursor.currentFrame() != cursor.document().rootFrame():
        return False
    first = cursor.document().findBlock(cursor.selectionStart())
    last = cursor.document().findBlock(max(cursor.selectionStart(), cursor.selectionEnd() - 1))
    return (
        first == last
        and bool(first.text().strip())
        and first.textList() is None
        and not first.blockFormat().hasProperty(QTextFormat.Property.BlockCodeFence)
    )


def create(cursor: QTextCursor) -> QTextCursor:
    if not can_create(cursor):
        raise ValueError("Place the cursor in a text paragraph to create an alternative.")
    cursor = QTextCursor(cursor)
    cursor.beginEditBlock()
    frame = current_frame(cursor)
    if frame is None:
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        original = _selection_markdown(cursor)
        cursor.removeSelectedText()
        cursor.setBlockFormat(QTextBlockFormat())
        cursor.setCharFormat(QTextCharFormat())
        frame = cursor.insertFrame(QTextFrameFormat())
        replace_contents(frame, original)
        value = Passage(uuid4().hex, 0, [Version("Original", original)])
    else:
        value = passage(frame)
    number = len(value.versions) + 1
    while any(version.name == f"Version {number}" for version in value.versions):
        number += 1
    value.versions.append(Version(f"Version {number}", value.versions[value.active].markdown))
    value.active = len(value.versions) - 1
    _set_passage(frame, value)
    cursor.endEditBlock()
    return contents(frame)


def switch(frame: QTextFrame, index: int) -> QTextCursor:
    value = passage(frame)
    if not 0 <= index < len(value.versions):
        raise ValueError("Unknown paragraph alternative")
    if index == value.active:
        return contents(frame)
    cursor = contents(frame)
    cursor.beginEditBlock()
    replace_contents(frame, value.versions[index].markdown)
    value.active = index
    _set_passage(frame, value)
    cursor.endEditBlock()
    return contents(frame)


def rename(frame: QTextFrame, name: str) -> None:
    name = name.strip()
    if not name:
        return
    value = passage(frame)
    value.versions[value.active].name = name
    _set_passage(frame, value)


def remove(frame: QTextFrame) -> QTextCursor:
    value = passage(frame)
    cursor = contents(frame)
    cursor.beginEditBlock()
    if len(value.versions) > 1:
        del value.versions[value.active]
        value.active = min(value.active, len(value.versions) - 1)
        replace_contents(frame, value.versions[value.active].markdown)
    if len(value.versions) == 1:
        result = _unwrap(frame)
    else:
        _set_passage(frame, value)
        result = contents(frame)
    cursor.endEditBlock()
    return result


def _unwrap(frame: QTextFrame) -> QTextCursor:
    """Turn the last version back into ordinary text without losing formatting."""
    fragment = contents(frame).selection()
    first_format = frame.firstCursorPosition().blockFormat()
    cursor = QTextCursor(frame.document())
    cursor.setPosition(frame.firstPosition() - 1)
    cursor.setPosition(frame.lastPosition() + 1, QTextCursor.MoveMode.KeepAnchor)
    cursor.removeSelectedText()
    if cursor.positionInBlock() > 0:
        cursor.insertBlock(QTextBlockFormat(), QTextCharFormat())
    start = QTextCursor(cursor)
    start.setKeepPositionOnInsert(True)
    cursor.insertFragment(fragment)
    start.clearSelection()
    first_format.setObjectIndex(start.blockFormat().objectIndex())
    start.setBlockFormat(first_format)
    start.setPosition(cursor.position(), QTextCursor.MoveMode.KeepAnchor)
    return start


def serialize(document: QTextDocument) -> str:
    frames = [
        frame for frame in document.rootFrame().childFrames()
        if frame.frameFormat().hasProperty(PROPERTY)
    ]
    if not frames:
        return document.toMarkdown(DIALECT)
    pieces: list[str] = []
    position = 0
    for frame in frames:
        cursor = QTextCursor(document)
        cursor.setPosition(position)
        cursor.setPosition(frame.firstPosition() - 1, QTextCursor.MoveMode.KeepAnchor)
        pieces.append(_selection_markdown(cursor).strip("\n"))
        value = passage(frame)
        payload = base64.b64encode(value.encode().encode("utf-8")).decode("ascii")
        pieces.extend((
            f"<!-- wtype:alternatives:v1 {value.id} {payload} -->",
            value.versions[value.active].markdown.strip("\n"),
            f"<!-- /wtype:alternatives {value.id} -->",
        ))
        position = frame.lastPosition() + 1
    cursor = QTextCursor(document)
    cursor.setPosition(position)
    cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
    pieces.append(_selection_markdown(cursor).strip("\n"))
    return "\n\n".join(piece for piece in pieces if piece) + "\n\n"


def load(document: QTextDocument, markdown: str) -> None:
    # Validate everything before touching the current document.
    parts: list[tuple[str, Passage | None]] = []
    position = 0
    seen: set[str] = set()
    searchable = _outside_fences(markdown)
    for match in _OPEN.finditer(searchable):
        if match.start() < position:
            continue
        identifier, payload = match.groups()
        closing = re.search(
            rf"^<!-- /wtype:alternatives {identifier} -->[ \t]*$",
            searchable[match.end():], re.MULTILINE,
        )
        if closing is None:
            raise DocumentError("A paragraph alternative is missing its closing marker.")
        try:
            value = Passage.decode(base64.b64decode(payload, validate=True).decode("utf-8"))
        except (binascii.Error, UnicodeError) as exc:
            raise DocumentError("The paragraph alternatives in this file are damaged.") from exc
        if value.id != identifier or identifier in seen:
            raise DocumentError("The paragraph alternatives in this file have conflicting IDs.")
        seen.add(identifier)
        parts.append((markdown[position:match.start()], None))
        parts.append((markdown[match.end():match.end() + closing.start()], value))
        position = match.end() + closing.end()
    parts.append((markdown[position:], None))
    if any(
        re.search(r"^<!-- wtype:alternatives:", _outside_fences(text), re.MULTILINE)
        for text, value in parts if value is None
    ):
        raise DocumentError("This file contains an unsupported or damaged paragraph alternative.")
    if not seen:
        document.setMarkdown(markdown, DIALECT)
        return
    document.clear()
    cursor = QTextCursor(document)
    for text, stored_passage in parts:
        if stored_passage is None:
            if text.strip():
                cursor.insertMarkdown(text, DIALECT)
        else:
            frame = cursor.insertFrame(QTextFrameFormat())
            replace_contents(frame, text)
            _set_passage(frame, stored_passage)
            cursor = QTextCursor(document)
            cursor.setPosition(frame.lastPosition() + 1)
