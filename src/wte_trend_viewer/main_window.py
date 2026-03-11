from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDockWidget,
    QHeaderView,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #E0E0E0;
    color: #2F2F2F;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QDockWidget {
    border: 1px solid #747474;
}

QDockWidget::title {
    background-color: #D5D5D5;
    color: #2F2F2F;
    padding: 7px 10px;
    border-bottom: 1px solid #747474;
    font-weight: 600;
}

QTreeView,
QTableWidget {
    background-color: #F2F2F2;
    border: 1px solid #8A8A8A;
    selection-background-color: #6B7F8E;
    selection-color: #FFFFFF;
    alternate-background-color: #ECECEC;
    gridline-color: #B0B0B0;
}

QHeaderView::section {
    background-color: #DCDCDC;
    color: #2F2F2F;
    border: none;
    border-right: 1px solid #A7A7A7;
    border-bottom: 1px solid #A7A7A7;
    padding: 6px;
    font-weight: 600;
}

QSplitter::handle {
    background-color: #B9B9B9;
}

QWidget#plotCanvas {
    background-color: #FFFFFF;
    border: 1px solid #7A7A7A;
}

QLabel#plotTitle {
    background: transparent;
    color: #2F2F2F;
    font-size: 14pt;
    font-weight: 600;
}

QLabel#plotSubtitle {
    background: transparent;
    color: #5B5B5B;
}

QStatusBar {
    background-color: #D5D5D5;
    border-top: 1px solid #747474;
}
"""


class PlotCanvasPlaceholder(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("plotCanvas")
        self.setMinimumSize(720, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(4)

        title = QLabel("Main Trend Viewport", self)
        title.setObjectName("plotTitle")
        layout.addWidget(title, alignment=Qt.AlignLeft | Qt.AlignTop)

        subtitle = QLabel(
            "Phase 1 placeholder canvas prepared for a future high-performance plotting engine.",
            self,
        )
        subtitle.setObjectName("plotSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle, alignment=Qt.AlignLeft | Qt.AlignTop)
        layout.addStretch()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        margin_left = 70
        margin_top = 70
        margin_right = 30
        margin_bottom = 45
        plot_rect = QRectF(
            margin_left,
            margin_top,
            max(0, self.width() - margin_left - margin_right),
            max(0, self.height() - margin_top - margin_bottom),
        )

        grid_pen = QPen(QColor("#C7C7C7"))
        grid_pen.setStyle(Qt.DashLine)
        axis_pen = QPen(QColor("#6C6C6C"))
        axis_pen.setWidth(1)
        label_pen = QPen(QColor("#5A5A5A"))

        painter.setPen(grid_pen)
        for step in range(1, 5):
            x = plot_rect.left() + (plot_rect.width() * step / 5)
            y = plot_rect.top() + (plot_rect.height() * step / 5)
            painter.drawLine(int(x), int(plot_rect.top()), int(x), int(plot_rect.bottom()))
            painter.drawLine(int(plot_rect.left()), int(y), int(plot_rect.right()), int(y))

        painter.setPen(axis_pen)
        painter.drawRect(plot_rect)

        painter.setPen(label_pen)
        painter.drawText(int(plot_rect.left()), int(plot_rect.bottom()) + 24, "Time")
        painter.save()
        painter.translate(24, int(plot_rect.center().y()))
        painter.rotate(-90)
        painter.drawText(0, 0, "Process Value")
        painter.restore()


class TrendViewerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WTE Trend Viewer")
        self.resize(1440, 900)

        self._tag_tree = self._build_tag_tree()
        self._trend_canvas = PlotCanvasPlaceholder(self)
        self._analytics_table = self._build_analytics_table()

        self.setCentralWidget(self._build_central_widget())

        status_bar = QStatusBar(self)
        status_bar.showMessage("Phase 1 ready: UI skeleton initialized.")
        self.setStatusBar(status_bar)

    def _build_central_widget(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        top_splitter = QSplitter(Qt.Horizontal, container)
        top_splitter.setChildrenCollapsible(False)
        top_splitter.addWidget(self._build_tag_dock())
        top_splitter.addWidget(self._trend_canvas)
        top_splitter.setStretchFactor(0, 0)
        top_splitter.setStretchFactor(1, 1)
        top_splitter.setSizes([320, 1080])

        layout.addWidget(top_splitter, stretch=5)
        layout.addWidget(self._build_analytics_dock(), stretch=2)

        return container

    def _build_tag_dock(self) -> QDockWidget:
        dock = QDockWidget("Tag Browser", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dock.setWidget(self._tag_tree)
        return dock

    def _build_analytics_dock(self) -> QDockWidget:
        dock = QDockWidget("Legend and Analytics", self)
        dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        dock.setWidget(self._analytics_table)
        return dock

    def _build_tag_tree(self) -> QTreeView:
        tree = QTreeView(self)
        tree.setHeaderHidden(True)
        tree.setAlternatingRowColors(True)
        tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tree.setUniformRowHeights(True)

        model = QStandardItemModel(tree)
        root = model.invisibleRootItem()

        structure = {
            "Boiler House": [
                ("Steam Drum", ["SD_Pressure", "SD_Level", "SD_Temperature"]),
                ("Feedwater", ["FW_Flow", "FW_Temperature"]),
            ],
            "Turbine Hall": [
                ("Main Turbine", ["MT_Speed", "MT_BearingTemp_A", "MT_BearingTemp_B"]),
                ("Generator", ["GEN_Load", "GEN_Voltage"]),
            ],
            "Utilities": [
                ("Cooling Water", ["CW_InletTemp", "CW_OutletTemp"]),
            ],
        }

        for area_name, groups in structure.items():
            area_item = QStandardItem(area_name)
            area_item.setEditable(False)
            for group_name, tags in groups:
                group_item = QStandardItem(group_name)
                group_item.setEditable(False)
                for tag_name in tags:
                    tag_item = QStandardItem(tag_name)
                    tag_item.setEditable(False)
                    group_item.appendRow(tag_item)
                area_item.appendRow(group_item)
            root.appendRow(area_item)

        tree.setModel(model)
        tree.expandAll()
        return tree

    def _build_analytics_table(self) -> QTableWidget:
        headers = ["Tag", "Cursor Value", "Window Min", "Window Max", "Window Avg"]
        table = QTableWidget(1, len(headers), self)
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setShowGrid(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setMinimumSectionSize(120)

        placeholders = ["No active tags", "-", "-", "-", "-"]
        for column, value in enumerate(placeholders):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(0, column, item)

        return table
