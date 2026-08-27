from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMarginsF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QPageLayout,
    QPageSize,
    QTextBlock,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextTable,
    QTextTableFormat,
)
from PySide6.QtPrintSupport import QPrinter

from wtype.typography import CODE_FONT_FAMILIES


class PdfExportError(RuntimeError):
    pass


class PdfExporter:
    """Render Markdown into a clean, searchable A4 PDF."""

    EDITOR_FONTS = (
        "Outfit",
        "Vazirmatn",
        "Noto Sans Arabic",
        "Noto Naskh Arabic",
        "Noto Sans",
        "DejaVu Sans",
    )
    # Some variable Arabic fonts render correctly but produce unreliable PDF
    # Unicode maps in Qt. Prefer fixed desktop fonts with stable text extraction.
    PDF_FONTS = (
        "Outfit",
        "DejaVu Sans",
        "Arial",
        "Segoe UI",
        "Geeza Pro",
        "Vazirmatn",
        "Noto Sans Arabic",
        "Noto Naskh Arabic",
        "Noto Sans",
    )
    CODE_FONTS = CODE_FONT_FAMILIES

    @classmethod
    def _preferred_font(cls, candidates: tuple[str, ...]) -> str:
        installed = set(QFontDatabase.families())
        return next((family for family in candidates if family in installed), "Sans Serif")

    @classmethod
    def preferred_editor_font(cls) -> str:
        return cls._preferred_font(cls.EDITOR_FONTS)

    @classmethod
    def preferred_pdf_font(cls) -> str:
        return cls._preferred_font(cls.PDF_FONTS)

    @classmethod
    def preferred_code_font(cls) -> str:
        return cls._preferred_font(cls.CODE_FONTS)

    def export(self, markdown: str, destination: Path) -> None:
        destination = destination.expanduser().resolve()
        document = self._print_document(markdown, destination.stem)

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(destination))
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)
        printer.setPageMargins(
            QMarginsF(18.0, 18.0, 18.0, 18.0),
            QPageLayout.Unit.Millimeter,
        )
        printer.setDocName(destination.stem)
        printer.setCreator("WType")

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            document.print_(printer)
        except Exception as exc:  # Qt can surface platform print-engine exceptions.
            raise PdfExportError(f"Could not export PDF: {exc}") from exc
        if not destination.exists() or destination.stat().st_size == 0:
            raise PdfExportError("Qt did not create the PDF file")

    def _print_document(self, markdown: str, title: str) -> QTextDocument:
        document = QTextDocument()
        font = QFont(self.preferred_pdf_font(), 11)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        document.setDefaultFont(font)
        document.setDocumentMargin(0)
        document.setMetaInformation(QTextDocument.MetaInformation.DocumentTitle, title)
        document.setMarkdown(
            markdown,
            QTextDocument.MarkdownFeature.MarkdownDialectGitHub,
        )

        code_font = QFont(self.preferred_code_font(), 10)
        code_font.setFixedPitch(True)
        code_background = QColor(128, 128, 128, 24)
        block = document.begin()
        while block.isValid():
            cursor = QTextCursor(block)
            block_format = block.blockFormat()
            block_format.setLayoutDirection(Qt.LayoutDirection.LayoutDirectionAuto)
            heading = block_format.headingLevel()
            is_code_block = block_format.hasProperty(
                QTextFormat.Property.BlockCodeFence
            )
            if heading:
                block_format.setTopMargin(18 if heading <= 2 else 12)
                block_format.setBottomMargin(6)
                block_format.setPageBreakPolicy(
                    QTextFormat.PageBreakFlag.PageBreak_Auto
                )
            elif is_code_block:
                previous = block.previous()
                following = block.next()
                block_format.setTopMargin(
                    6 if not self._is_code_block(previous) else 0
                )
                block_format.setBottomMargin(
                    8 if not self._is_code_block(following) else 0
                )
                block_format.setLeftMargin(10)
                block_format.setRightMargin(10)
                block_format.setTextIndent(8)
                block_format.setBackground(code_background)
            elif block_format.intProperty(QTextFormat.Property.BlockQuoteLevel):
                block_format.setLeftMargin(18)
                block_format.setRightMargin(8)
                block_format.setTopMargin(4)
                block_format.setBottomMargin(4)
            else:
                block_format.setBottomMargin(7)
            cursor.setBlockFormat(block_format)
            if is_code_block:
                cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                code_format = QTextCharFormat()
                code_format.setFont(code_font)
                cursor.mergeCharFormat(code_format)
            else:
                self._style_inline_code(block, code_font, code_background)
            block = block.next()

        self._style_tables(document)
        return document

    @staticmethod
    def _is_code_block(block: QTextBlock) -> bool:
        return block.isValid() and block.blockFormat().hasProperty(
            QTextFormat.Property.BlockCodeFence
        )

    @staticmethod
    def _style_inline_code(
        block: QTextBlock,
        code_font: QFont,
        background: QColor,
    ) -> None:
        ranges: list[tuple[int, int]] = []
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            if fragment.isValid() and fragment.charFormat().fontFixedPitch():
                ranges.append((fragment.position(), fragment.length()))
            iterator += 1

        for start, length in ranges:
            cursor = QTextCursor(block.document())
            cursor.setPosition(start)
            cursor.setPosition(start + length, QTextCursor.MoveMode.KeepAnchor)
            code_format = QTextCharFormat()
            code_format.setFont(code_font)
            code_format.setBackground(background)
            cursor.mergeCharFormat(code_format)

    @staticmethod
    def _style_tables(document: QTextDocument) -> None:
        frames = list(document.rootFrame().childFrames())
        while frames:
            frame = frames.pop()
            frames.extend(frame.childFrames())
            if not isinstance(frame, QTextTable):
                continue
            table_format = QTextTableFormat(frame.format())
            table_format.setBorder(0.75)
            table_format.setCellPadding(5)
            table_format.setCellSpacing(0)
            table_format.setHeaderRowCount(1)
            frame.setFormat(table_format)
