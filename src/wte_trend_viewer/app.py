from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .main_window import APP_STYLESHEET, TrendViewerMainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("WTE Trend Viewer")
    app.setOrganizationName("WORKBOT")
    app.setStyleSheet(APP_STYLESHEET)

    window = TrendViewerMainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

