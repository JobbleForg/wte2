from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .config.settings import APP_NAME, ORGANIZATION_NAME
from .ui.main_window import TrendViewerMainWindow
from .ui.styles.isa101 import build_stylesheet


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setStyleSheet(build_stylesheet())

    window = TrendViewerMainWindow()
    window.show()
    return app.exec()
