from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import re

import numpy as np
from PySide6.QtCore import QObject, QThread, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from .data_manager import DataManager, WorkbookSheetInfo
from .plot_canvas import TrendPlotCanvas
from .tag_tree_model import TagTreeModel

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

QToolBar {
    background-color: #D5D5D5;
    border: 1px solid #747474;
    spacing: 6px;
    padding: 4px;
}

QToolButton {
    background-color: #E6E6E6;
    border: 1px solid #8A8A8A;
    padding: 6px 10px;
    margin-right: 4px;
}

QToolButton:hover {
    background-color: #F0F0F0;
}

QToolButton:pressed {
    background-color: #D0D0D0;
}

QMenu {
    background-color: #F2F2F2;
    border: 1px solid #8A8A8A;
}

QMenu::item:selected {
    background-color: #6B7F8E;
    color: #FFFFFF;
}

QSplitter::handle {
    background-color: #B9B9B9;
}

QWidget#plotCanvas {
    background-color: #FFFFFF;
    border: 1px solid #7A7A7A;
}

QStatusBar {
    background-color: #D5D5D5;
    border-top: 1px solid #747474;
}
"""

ANALYTICS_HEADERS = [
    "Tag",
    "Cursor Time",
    "Value",
    "Prev 6",
    "Prev 5",
    "Prev 4",
    "Prev 3",
    "Prev 2",
    "Prev 1",
    "Next 1",
    "Next 2",
    "Next 3",
    "Next 4",
    "Next 5",
    "Next 6",
    "Min",
    "Max",
    "Avg",
]
OFFSET_PATTERN = re.compile(
    r"^\s*([+-]?\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|week|weeks)\s*$",
    re.IGNORECASE,
)
OFFSET_UNIT_MAP = {
    "s": "seconds",
    "sec": "seconds",
    "secs": "seconds",
    "second": "seconds",
    "seconds": "seconds",
    "m": "minutes",
    "min": "minutes",
    "mins": "minutes",
    "minute": "minutes",
    "minutes": "minutes",
    "h": "hours",
    "hr": "hours",
    "hrs": "hours",
    "hour": "hours",
    "hours": "hours",
    "d": "days",
    "day": "days",
    "days": "days",
    "w": "weeks",
    "week": "weeks",
    "weeks": "weeks",
}


class ExcelLoadWorker(QObject):
    progress = Signal(str)
    loaded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, file_path: str, sheet_names: tuple[str, ...]) -> None:
        super().__init__()
        self._file_path = file_path
        self._sheet_names = sheet_names

    @Slot()
    def run(self) -> None:
        try:
            workbook_name = Path(self._file_path).name
            manager = DataManager()
            if len(self._sheet_names) <= 1:
                selected_sheet = self._sheet_names[0] if self._sheet_names else None
                sheet_suffix = f" / {selected_sheet}" if selected_sheet else ""
                self.progress.emit(f"Reading {workbook_name}{sheet_suffix} with Polars...")
                manager.load_excel(self._file_path, sheet_name=selected_sheet)
            else:
                self.progress.emit(
                    f"Reading {len(self._sheet_names)} selected worksheets from {workbook_name}..."
                )
                manager.load_workbook(self._file_path, sheet_names=self._sheet_names)
            self.progress.emit(
                f"Loaded {len(manager.available_tags)} tags from {len(manager.sheet_names) or 1} worksheet(s)."
            )
            self.loaded.emit(manager)
        except Exception as exc:  # pragma: no cover - UI path
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()


class SheetSelectionDialog(QDialog):
    def __init__(
        self,
        workbook_name: str,
        sheet_info: tuple[WorkbookSheetInfo, ...],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select Data Sheets")
        self.resize(680, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        description = QLabel(
            (
                f"Select one or more worksheets from {workbook_name}.\n"
                "Sheets with detected timestamp columns are pre-selected."
            ),
            self,
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self._sheet_list = QListWidget(self)
        for info in sheet_info:
            item = QListWidgetItem(self._describe_sheet(info))
            item.setData(Qt.UserRole, info.name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if info.is_data_sheet else Qt.Unchecked)
            tooltip = (
                f"Detected timestamp column: {info.timestamp_column}"
                if info.timestamp_column
                else "No timestamp column detected automatically."
            )
            item.setToolTip(tooltip)
            self._sheet_list.addItem(item)
        layout.addWidget(self._sheet_list, stretch=1)

        quick_actions = QHBoxLayout()
        select_suggested_button = QPushButton("Select Suggested", self)
        select_suggested_button.clicked.connect(self._select_suggested)
        quick_actions.addWidget(select_suggested_button)

        select_all_button = QPushButton("Select All", self)
        select_all_button.clicked.connect(self._select_all)
        quick_actions.addWidget(select_all_button)

        clear_button = QPushButton("Clear", self)
        clear_button.clicked.connect(self._clear_selection)
        quick_actions.addWidget(clear_button)
        quick_actions.addStretch(1)
        layout.addLayout(quick_actions)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=self,
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def selected_sheet_names(self) -> tuple[str, ...]:
        selected_names: list[str] = []
        for index in range(self._sheet_list.count()):
            item = self._sheet_list.item(index)
            if item.checkState() == Qt.Checked:
                sheet_name = item.data(Qt.UserRole)
                if isinstance(sheet_name, str):
                    selected_names.append(sheet_name)
        return tuple(selected_names)

    def accept(self) -> None:
        if not self.selected_sheet_names():
            QMessageBox.warning(
                self,
                "No Sheets Selected",
                "Select at least one worksheet to continue.",
            )
            return
        super().accept()

    def _select_suggested(self) -> None:
        for index in range(self._sheet_list.count()):
            item = self._sheet_list.item(index)
            suggested = "Detected timestamp column:" in item.toolTip()
            item.setCheckState(Qt.Checked if suggested else Qt.Unchecked)

    def _select_all(self) -> None:
        for index in range(self._sheet_list.count()):
            self._sheet_list.item(index).setCheckState(Qt.Checked)

    def _clear_selection(self) -> None:
        for index in range(self._sheet_list.count()):
            self._sheet_list.item(index).setCheckState(Qt.Unchecked)

    def _describe_sheet(self, info: WorkbookSheetInfo) -> str:
        if info.is_data_sheet and info.timestamp_column:
            return (
                f"{info.name}  ({info.tag_count} tags, {info.row_count} rows, "
                f"time column: {info.timestamp_column})"
            )
        return f"{info.name}  ({info.row_count} rows, no timestamp detected)"


class TrendViewerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WTE Trend Viewer")
        self.resize(1560, 960)

        self._data_manager: DataManager | None = None
        self._load_thread: QThread | None = None
        self._load_worker: ExcelLoadWorker | None = None
        self._tag_offsets: dict[str, list[timedelta]] = {}
        self._current_cursor_time: datetime | None = None

        self._visible_range_timer = QTimer(self)
        self._visible_range_timer.setSingleShot(True)
        self._visible_range_timer.setInterval(70)
        self._visible_range_timer.timeout.connect(self._refresh_visible_data)

        self._tag_model = TagTreeModel()
        self._tag_tree = self._build_tag_tree()
        self._plot_canvas = TrendPlotCanvas(self)
        self._analytics_table = self._build_analytics_table()

        self._plot_canvas.tagDropped.connect(self._handle_tag_request)
        self._plot_canvas.visibleRangeChanged.connect(self._schedule_visible_refresh)
        self._plot_canvas.cursorTimestampChanged.connect(self._handle_cursor_timestamp)

        self.setCentralWidget(self._build_central_widget())
        self._build_toolbar()

        status_bar = QStatusBar(self)
        status_bar.showMessage("Ready. Open an Excel export to begin.")
        self.setStatusBar(status_bar)
        self._show_placeholder_analytics("Load an Excel workbook to begin.")

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Trend Controls", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self._open_action = QAction("Open Excel", self)
        self._open_action.triggered.connect(self._prompt_open_workbook)
        toolbar.addAction(self._open_action)

        self._clear_action = QAction("Clear Traces", self)
        self._clear_action.triggered.connect(self._clear_traces)
        toolbar.addAction(self._clear_action)

        self._reset_view_action = QAction("Reset View", self)
        self._reset_view_action.triggered.connect(self._reset_view)
        toolbar.addAction(self._reset_view_action)

    def _build_central_widget(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        top_splitter = QSplitter(Qt.Horizontal, container)
        top_splitter.setChildrenCollapsible(False)
        top_splitter.addWidget(self._build_tag_dock())
        top_splitter.addWidget(self._plot_canvas)
        top_splitter.setStretchFactor(0, 0)
        top_splitter.setStretchFactor(1, 1)
        top_splitter.setSizes([320, 1240])

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
        tree.setModel(self._tag_model)
        tree.setHeaderHidden(True)
        tree.setAlternatingRowColors(True)
        tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tree.setUniformRowHeights(True)
        tree.setDragEnabled(True)
        tree.doubleClicked.connect(self._handle_tree_double_click)
        return tree

    def _build_analytics_table(self) -> QTableWidget:
        table = QTableWidget(0, len(ANALYTICS_HEADERS), self)
        table.setHorizontalHeaderLabels(ANALYTICS_HEADERS)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setShowGrid(True)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_analytics_context_menu)
        table.itemSelectionChanged.connect(self._sync_focus_from_selection)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(90)
        return table

    def _prompt_open_workbook(self) -> None:
        if self._load_thread is not None:
            self.statusBar().showMessage("A workbook is already loading.")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Trend Export",
            "",
            "Excel Files (*.xlsx *.xlsb)",
        )
        if not file_path:
            return

        workbook_name = Path(file_path).name
        self.statusBar().showMessage(f"Scanning worksheets in {workbook_name}...")
        QApplication.processEvents()

        try:
            sheet_info = DataManager.inspect_workbook(file_path)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Workbook Scan Failed",
                f"Unable to inspect worksheets in {workbook_name}.\n\n{exc}",
            )
            self.statusBar().showMessage("Workbook scan failed.", 5000)
            return

        if not sheet_info:
            QMessageBox.warning(
                self,
                "No Worksheets Found",
                f"No readable worksheets were found in {workbook_name}.",
            )
            self.statusBar().showMessage("No worksheets found.", 5000)
            return

        if len(sheet_info) == 1:
            selected_sheets = (sheet_info[0].name,)
        else:
            dialog = SheetSelectionDialog(workbook_name, sheet_info, self)
            if dialog.exec() != QDialog.Accepted:
                self.statusBar().showMessage("Workbook load cancelled.", 3000)
                return
            selected_sheets = dialog.selected_sheet_names()

        self._start_background_load(file_path, selected_sheets)

    def _start_background_load(self, file_path: str, sheet_names: tuple[str, ...]) -> None:
        self._open_action.setEnabled(False)
        workbook_name = Path(file_path).name
        sheet_summary = self._format_sheet_summary(sheet_names)
        self.statusBar().showMessage(
            f"Starting background load for {workbook_name} ({sheet_summary})..."
        )

        worker = ExcelLoadWorker(file_path, sheet_names)
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self.statusBar().showMessage)
        worker.loaded.connect(self._handle_workbook_loaded)
        worker.failed.connect(self._handle_load_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(self._clear_load_worker)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._handle_load_finished)

        self._load_worker = worker
        self._load_thread = thread
        thread.start()

    @Slot(object)
    def _handle_workbook_loaded(self, manager: DataManager) -> None:
        self._data_manager = manager
        self._tag_offsets.clear()
        self._current_cursor_time = None
        self._plot_canvas.clear_traces()
        self._tag_model.set_tags(manager.available_tags)
        self._tag_tree.expandAll()
        self._show_placeholder_analytics("Drag a tag onto the plot to begin analysis.")

        time_range = manager.time_range()
        if time_range is not None:
            self._plot_canvas.set_time_range(*time_range)

        source_name = manager.source_path.name if manager.source_path else "workbook"
        sheet_summary = self._format_sheet_summary(manager.sheet_names or ("active sheet",))
        self.statusBar().showMessage(
            f"Loaded {len(manager.available_tags)} tags from {source_name} ({sheet_summary}).",
            5000,
        )

    @Slot(str)
    def _handle_load_error(self, message: str) -> None:
        QMessageBox.critical(self, "Workbook Load Failed", message)
        self.statusBar().showMessage("Workbook load failed.", 5000)

    @Slot()
    def _clear_load_worker(self) -> None:
        if self._load_worker is not None:
            self._load_worker.deleteLater()
            self._load_worker = None

    @Slot()
    def _handle_load_finished(self) -> None:
        self._load_thread = None
        self._open_action.setEnabled(True)

    @Slot()
    def _clear_traces(self) -> None:
        self._tag_offsets.clear()
        self._current_cursor_time = None
        self._plot_canvas.clear_traces()
        self._show_placeholder_analytics("No active tags. Drag a tag onto the plot.")

    @Slot()
    def _reset_view(self) -> None:
        if self._data_manager is None:
            return
        time_range = self._data_manager.time_range()
        if time_range is None:
            return
        self._plot_canvas.set_time_range(*time_range)

    @Slot(object)
    def _handle_tree_double_click(self, index) -> None:
        tag_name = self._tag_model.tag_for_index(index)
        if tag_name:
            self._handle_tag_request(tag_name)

    @Slot(str)
    def _handle_tag_request(self, tag_name: str) -> None:
        if self._data_manager is None:
            self.statusBar().showMessage("Open an Excel workbook before adding tags.", 4000)
            return
        if tag_name not in self._data_manager.available_tags:
            self.statusBar().showMessage(f"Tag not available in current workbook: {tag_name}", 4000)
            return

        was_empty = not self._plot_canvas.active_tags()
        self._plot_canvas.ensure_trace(tag_name)
        self._tag_offsets.setdefault(tag_name, [])
        self._plot_canvas.set_focus(tag_name)

        if was_empty:
            time_range = self._data_manager.time_range()
            if time_range is not None:
                self._plot_canvas.set_time_range(*time_range)

        self._refresh_visible_data()
        self.statusBar().showMessage(f"Added {tag_name} to the plot.", 3000)

    @Slot(object, object)
    def _schedule_visible_refresh(self, *_range) -> None:
        if self._data_manager is None or not self._plot_canvas.active_tags():
            return
        self._visible_range_timer.start()

    @Slot(object)
    def _handle_cursor_timestamp(self, timestamp: datetime) -> None:
        self._current_cursor_time = timestamp
        self._update_analytics_table(timestamp)

    def _refresh_visible_data(self) -> None:
        if self._data_manager is None:
            return

        active_tags = self._plot_canvas.active_tags()
        if not active_tags:
            return

        current_range = self._plot_canvas.current_time_range() or self._data_manager.time_range()
        if current_range is None:
            return

        start, end = current_range
        pixel_width = self._plot_canvas.plot_pixel_width()

        for tag_name in active_tags:
            raw_timestamps, raw_values = self._data_manager.get_tag_window_arrays(
                start=start,
                end=end,
                tag=tag_name,
            )
            reduced = self._data_manager.downsample_series(raw_timestamps, raw_values, pixel_width)
            self._plot_canvas.update_trace_data(
                tag_name,
                raw_timestamps=raw_timestamps,
                raw_values=raw_values,
                display_timestamps=reduced.timestamps,
                display_values=reduced.values,
            )

            for delta in self._tag_offsets.get(tag_name, []):
                shifted_start = start + delta
                shifted_end = end + delta
                offset_raw_timestamps, offset_raw_values = self._data_manager.get_tag_window_arrays(
                    start=shifted_start,
                    end=shifted_end,
                    tag=tag_name,
                )
                aligned_timestamps = self._shift_timestamps(offset_raw_timestamps, -delta)
                offset_reduced = self._data_manager.downsample_series(
                    aligned_timestamps,
                    offset_raw_values,
                    pixel_width,
                )
                self._plot_canvas.update_offset_data(
                    tag_name,
                    delta,
                    raw_timestamps=aligned_timestamps,
                    raw_values=offset_raw_values,
                    display_timestamps=offset_reduced.timestamps,
                    display_values=offset_reduced.values,
                )

        self._update_analytics_table(self._current_cursor_time)

    def _show_analytics_context_menu(self, position) -> None:
        if self._analytics_table.rowCount() == 0:
            return

        row = self._analytics_table.rowAt(position.y())
        if row < 0:
            return

        tag_item = self._analytics_table.item(row, 0)
        if tag_item is None:
            return
        tag_name = tag_item.data(Qt.UserRole)
        if not isinstance(tag_name, str):
            return

        menu = QMenu(self)
        add_offset_action = menu.addAction("Add Time Offset Trace")
        chosen_action = menu.exec(self._analytics_table.viewport().mapToGlobal(position))
        if chosen_action is add_offset_action:
            self._prompt_time_offset(tag_name)

    def _prompt_time_offset(self, tag_name: str) -> None:
        default_text = "-24h"
        offset_text, accepted = QInputDialog.getText(
            self,
            "Add Time Offset Trace",
            f"Enter the offset for {tag_name} (for example -24h or -7d):",
            text=default_text,
        )
        if not accepted or not offset_text.strip():
            return

        try:
            delta = self._parse_time_offset(offset_text)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Offset", str(exc))
            return

        offsets = self._tag_offsets.setdefault(tag_name, [])
        if delta in offsets:
            self.statusBar().showMessage(
                f"Offset trace {offset_text.strip()} already exists for {tag_name}.",
                4000,
            )
            return

        offsets.append(delta)
        self._plot_canvas.ensure_offset_trace(tag_name, delta)
        self._refresh_visible_data()
        self.statusBar().showMessage(
            f"Added time-offset trace {offset_text.strip()} for {tag_name}.",
            4000,
        )

    def _sync_focus_from_selection(self) -> None:
        selected_items = self._analytics_table.selectedItems()
        if not selected_items:
            self._plot_canvas.set_focus(None)
            return

        tag_item = self._analytics_table.item(selected_items[0].row(), 0)
        if tag_item is None:
            self._plot_canvas.set_focus(None)
            return
        tag_name = tag_item.data(Qt.UserRole)
        self._plot_canvas.set_focus(tag_name if isinstance(tag_name, str) else None)

    def _update_analytics_table(self, cursor_time: datetime | None) -> None:
        active_tags = self._plot_canvas.active_tags()
        if not active_tags:
            self._show_placeholder_analytics("No active tags. Drag a tag onto the plot.")
            return

        self._analytics_table.setRowCount(len(active_tags))
        for row_index, tag_name in enumerate(active_tags):
            trace_state = self._plot_canvas.trace_state(tag_name)
            if trace_state is None:
                continue

            cursor_value = (
                self._interpolate_value(trace_state.raw_timestamps, trace_state.raw_values, cursor_time)
                if cursor_time is not None
                else None
            )
            prev_values, next_values = (
                self._adjacent_values(trace_state.raw_timestamps, trace_state.raw_values, cursor_time, count=6)
                if cursor_time is not None
                else ([None] * 6, [None] * 6)
            )
            minimum, maximum, average = self._window_stats(trace_state.raw_values)

            row_values = [
                tag_name,
                cursor_time.strftime("%Y-%m-%d %H:%M:%S") if cursor_time else "-",
                self._format_number(cursor_value),
                *[self._format_number(value) for value in prev_values],
                *[self._format_number(value) for value in next_values],
                self._format_number(minimum),
                self._format_number(maximum),
                self._format_number(average),
            ]
            self._populate_analytics_row(
                row_index,
                row_values,
                tag_name=tag_name,
                color=trace_state.color,
            )

    def _populate_analytics_row(
        self,
        row_index: int,
        values: list[str],
        *,
        tag_name: str,
        color: str,
    ) -> None:
        for column_index, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            if column_index == 0:
                item.setData(Qt.UserRole, tag_name)
                tint = QColor(color)
                tint.setAlpha(70)
                item.setBackground(tint)
            self._analytics_table.setItem(row_index, column_index, item)

    def _show_placeholder_analytics(self, message: str) -> None:
        self._analytics_table.setRowCount(1)
        for column_index, header in enumerate(ANALYTICS_HEADERS):
            value = message if column_index == 0 else "-"
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            self._analytics_table.setItem(0, column_index, item)

    def _parse_time_offset(self, value: str) -> timedelta:
        match = OFFSET_PATTERN.match(value)
        if not match:
            raise ValueError("Use offsets like -24h, -7d, 30m, or 2w.")

        amount = int(match.group(1))
        unit = OFFSET_UNIT_MAP[match.group(2).lower()]
        return timedelta(**{unit: amount})

    def _shift_timestamps(self, timestamps: np.ndarray, delta: timedelta) -> np.ndarray:
        array = np.asarray(timestamps).astype("datetime64[us]")
        microseconds = int(delta.total_seconds() * 1_000_000)
        return array + np.timedelta64(microseconds, "us")

    def _interpolate_value(
        self,
        timestamps: np.ndarray,
        values: np.ndarray,
        cursor_time: datetime | None,
    ) -> float | None:
        if cursor_time is None or timestamps.size == 0 or values.size == 0:
            return None

        y_values = np.asarray(values, dtype=float)
        finite_mask = np.isfinite(y_values)
        if not np.any(finite_mask):
            return None

        x_values = np.asarray(timestamps).astype("datetime64[us]").astype(np.int64)
        x_values = x_values[finite_mask]
        y_values = y_values[finite_mask]
        target = np.datetime64(cursor_time, "us").astype(np.int64)

        if target <= x_values[0]:
            return float(y_values[0])
        if target >= x_values[-1]:
            return float(y_values[-1])
        return float(np.interp(target, x_values, y_values))

    def _adjacent_values(
        self,
        timestamps: np.ndarray,
        values: np.ndarray,
        cursor_time: datetime | None,
        *,
        count: int,
    ) -> tuple[list[float | None], list[float | None]]:
        if cursor_time is None or timestamps.size == 0 or values.size == 0:
            return [None] * count, [None] * count

        time_values = np.asarray(timestamps).astype("datetime64[us]")
        value_array = np.asarray(values, dtype=float)
        target = np.datetime64(cursor_time, "us")

        prev_end = int(np.searchsorted(time_values, target, side="left"))
        next_start = int(np.searchsorted(time_values, target, side="right"))

        prev_slice = value_array[max(0, prev_end - count):prev_end].tolist()
        next_slice = value_array[next_start:next_start + count].tolist()

        prev_values: list[float | None] = [None] * (count - len(prev_slice)) + prev_slice
        next_values: list[float | None] = next_slice + [None] * (count - len(next_slice))
        return prev_values, next_values

    def _window_stats(self, values: np.ndarray) -> tuple[float | None, float | None, float | None]:
        array = np.asarray(values, dtype=float)
        finite_values = array[np.isfinite(array)]
        if finite_values.size == 0:
            return None, None, None
        return (
            float(np.nanmin(finite_values)),
            float(np.nanmax(finite_values)),
            float(np.nanmean(finite_values)),
        )

    def _format_number(self, value: float | None) -> str:
        if value is None or np.isnan(value):
            return "-"
        return f"{value:.3f}"

    def _format_sheet_summary(self, sheet_names: tuple[str, ...]) -> str:
        if not sheet_names:
            return "default sheet"
        if len(sheet_names) == 1:
            return f"sheet: {sheet_names[0]}"
        preview = ", ".join(sheet_names[:2])
        if len(sheet_names) > 2:
            preview = f"{preview}, +{len(sheet_names) - 2} more"
        return f"{len(sheet_names)} sheets: {preview}"
