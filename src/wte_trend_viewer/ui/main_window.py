from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QSplitter, QToolBar, QVBoxLayout, QWidget

from ..config.settings import WINDOW_DEFAULTS
from .docks.analytics_dock import AnalyticsDock
from .docks.tag_browser_dock import TagBrowserDock
from .plot.trend_canvas import TrendCanvasPlaceholder


class TrendViewerMainWindow(QMainWindow):
    """Minimal phase-1 shell built on the new long-term package layout."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WTE Trend Viewer")
        self.resize(WINDOW_DEFAULTS.width, WINDOW_DEFAULTS.height)

        self._tag_browser_dock = TagBrowserDock(self)
        self._analytics_dock = AnalyticsDock(self)
        self._trend_canvas = TrendCanvasPlaceholder(self)

        self.setCentralWidget(self._build_central_widget())
        self._build_toolbar()
        self.statusBar().showMessage("Scaffold ready. Phase 2 begins in the data layer.")

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Primary Toolbar", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        for title in ("Open Workbook", "Reset View", "Inspection Mode", "Export"):
            action = QAction(title, self)
            action.setEnabled(False)
            toolbar.addAction(action)

    def _build_central_widget(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal, container)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._tag_browser_dock)
        splitter.addWidget(self._trend_canvas)
        splitter.setSizes([WINDOW_DEFAULTS.minimum_left_pane_width, 1240])

        layout.addWidget(splitter, stretch=5)
        layout.addWidget(self._analytics_dock, stretch=2)
        return container
