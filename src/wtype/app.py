from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from wtype.main_window import MainWindow


def _load_bundled_fonts() -> str:
    assets = Path(__file__).with_name("assets")
    for filename in (
        "Outfit-Regular.ttf",
        "Outfit-SemiBold.ttf",
        "Outfit-Bold.ttf",
    ):
        path = assets / filename
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))
    return "Outfit" if "Outfit" in QFontDatabase.families() else "Sans Serif"


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv if argv is None else argv)
    QCoreApplication.setOrganizationName("WType")
    QCoreApplication.setOrganizationDomain("wtype.local")
    QCoreApplication.setApplicationName("WType")
    QCoreApplication.setApplicationVersion("0.1.0")

    app = QApplication(arguments)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    app.setApplicationDisplayName("WType")
    app.setFont(QFont(_load_bundled_fonts(), 10))

    initial_path = None
    if len(arguments) > 1 and not arguments[1].startswith("-"):
        initial_path = Path(arguments[1])
    window = MainWindow(initial_path)
    window.show()
    return app.exec()
