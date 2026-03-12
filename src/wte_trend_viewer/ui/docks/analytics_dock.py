from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


ANALYTICS_HEADERS = [
    "Tag",
    "Cursor Time",
    "Value",
    "Prev 1",
    "Prev 2",
    "Prev 3",
    "Next 1",
    "Next 2",
    "Next 3",
    "Min",
    "Max",
    "Avg",
]


class AnalyticsDock(QDockWidget):
    """Phase-1 legend and analytics shell reserved for phase 7 expansion."""

    def __init__(self, parent=None) -> None:
        super().__init__("Legend and Analytics", parent)
        self.setFeatures(QDockWidget.NoDockWidgetFeatures)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)

        self.table = QTableWidget(1, len(ANALYTICS_HEADERS), container)
        self.table.setHorizontalHeaderLabels(ANALYTICS_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setItem(0, 0, self._new_item("Analytics scaffold"))
        for index in range(1, len(ANALYTICS_HEADERS)):
            self.table.setItem(0, index, self._new_item("-"))

        layout.addWidget(self.table)
        self.setWidget(container)

    def _new_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item
