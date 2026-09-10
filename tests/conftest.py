import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp(qapp):  # type: ignore[no-untyped-def]
    from PySide6.QtGui import QFont

    from wtype.app import _load_bundled_fonts

    # Match application startup before any editor or PDF test. The Windows
    # offscreen backend has no system fonts, and test order must not supply them.
    qapp.setFont(QFont(_load_bundled_fonts(), 10))
    return qapp
