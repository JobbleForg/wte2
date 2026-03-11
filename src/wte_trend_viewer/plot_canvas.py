from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


ISA101_TRACE_COLORS = (
    "#365C7D",
    "#587B4D",
    "#5A5A5A",
    "#7A6B3E",
    "#4B6E80",
    "#6A4F6D",
)


@dataclass
class OffsetTraceState:
    delta: timedelta
    curve: pg.PlotDataItem
    raw_timestamps: np.ndarray = field(
        default_factory=lambda: np.array([], dtype="datetime64[us]")
    )
    raw_values: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))


@dataclass
class PlotTraceState:
    tag_name: str
    color: str
    curve: pg.PlotDataItem
    view_box: pg.ViewBox
    axis: pg.AxisItem | None
    uses_primary_view_box: bool
    raw_timestamps: np.ndarray = field(
        default_factory=lambda: np.array([], dtype="datetime64[us]")
    )
    raw_values: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    offsets: list[OffsetTraceState] = field(default_factory=list)


class TrendPlotCanvas(pg.GraphicsLayoutWidget):
    tagDropped = Signal(str)
    visibleRangeChanged = Signal(object, object)
    cursorTimestampChanged = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setObjectName("plotCanvas")
        self.setAcceptDrops(True)
        self.setBackground("#FFFFFF")

        self._date_axis = pg.DateAxisItem(orientation="bottom")
        self._plot_item = self.addPlot(axisItems={"bottom": self._date_axis})
        self._plot_item.setLabel("bottom", "Time")
        self._plot_item.setLabel("left", "Process Value")
        self._plot_item.showGrid(x=True, y=True, alpha=0.22)
        self._plot_item.hideButtons()
        self._plot_item.setMenuEnabled(False)
        self._plot_item.getAxis("left").setTextPen(pg.mkColor("#54606A"))
        self._plot_item.getAxis("left").setPen(pg.mkPen("#54606A"))
        self._plot_item.hideAxis("right")
        self._plot_item.setTitle(
            "Load an Excel file, then drag tags here",
            color="#5B5B5B",
            size="11pt",
        )

        self._cursor_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen("#5F6A74", width=1),
        )
        self._plot_item.addItem(self._cursor_line, ignoreBounds=True)
        self._cursor_line.hide()

        self._plot_item.vb.sigResized.connect(self._sync_overlay_views)
        self._plot_item.vb.sigXRangeChanged.connect(self._emit_visible_range)
        self._mouse_proxy = pg.SignalProxy(
            self.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._handle_mouse_moved,
        )

        self._next_color_index = 0
        self._focused_tag: str | None = None
        self._traces: dict[str, PlotTraceState] = {}

    def active_tags(self) -> tuple[str, ...]:
        return tuple(self._traces)

    def has_trace(self, tag_name: str) -> bool:
        return tag_name in self._traces

    def trace_state(self, tag_name: str) -> PlotTraceState | None:
        return self._traces.get(tag_name)

    def clear_traces(self) -> None:
        for state in self._traces.values():
            for offset in state.offsets:
                state.view_box.removeItem(offset.curve)
            if state.uses_primary_view_box:
                self._plot_item.removeItem(state.curve)
            else:
                state.view_box.removeItem(state.curve)
                self._plot_item.scene().removeItem(state.view_box)
                if state.axis is not None:
                    if state.axis is self._plot_item.getAxis("right"):
                        self._plot_item.hideAxis("right")
                    else:
                        self._plot_item.layout.removeItem(state.axis)
                        if state.axis.scene() is not None:
                            state.axis.scene().removeItem(state.axis)

        self._traces.clear()
        self._next_color_index = 0
        self._focused_tag = None
        self._plot_item.setLabel("left", "Process Value")
        self._plot_item.getAxis("left").setTextPen(pg.mkColor("#54606A"))
        self._plot_item.getAxis("left").setPen(pg.mkPen("#54606A"))
        self._plot_item.setTitle(
            "Load an Excel file, then drag tags here",
            color="#5B5B5B",
            size="11pt",
        )
        self._cursor_line.hide()

    def ensure_trace(self, tag_name: str) -> PlotTraceState:
        existing = self._traces.get(tag_name)
        if existing is not None:
            return existing

        color = ISA101_TRACE_COLORS[self._next_color_index % len(ISA101_TRACE_COLORS)]
        self._next_color_index += 1
        pen = self._make_pen(color, emphasized=True)

        if not self._traces:
            curve = pg.PlotDataItem(pen=pen)
            self._plot_item.addItem(curve)
            self._plot_item.setLabel("left", tag_name, color=color)
            self._plot_item.getAxis("left").setTextPen(pg.mkColor(color))
            self._plot_item.getAxis("left").setPen(pg.mkPen(color))
            state = PlotTraceState(
                tag_name=tag_name,
                color=color,
                curve=curve,
                view_box=self._plot_item.vb,
                axis=self._plot_item.getAxis("left"),
                uses_primary_view_box=True,
            )
        else:
            view_box = pg.ViewBox()
            curve = pg.PlotDataItem(pen=pen)
            view_box.addItem(curve)
            self._plot_item.scene().addItem(view_box)

            if len(self._traces) == 1:
                self._plot_item.showAxis("right")
                axis = self._plot_item.getAxis("right")
            else:
                axis = pg.AxisItem("right")
                axis_column = 2 + (len(self._traces) - 1)
                self._plot_item.layout.addItem(axis, 2, axis_column)

            axis.linkToView(view_box)
            axis.setLabel(tag_name, color=color)
            axis.setTextPen(pg.mkColor(color))
            axis.setPen(pg.mkPen(color))
            axis.setWidth(72)
            view_box.setXLink(self._plot_item.vb)

            state = PlotTraceState(
                tag_name=tag_name,
                color=color,
                curve=curve,
                view_box=view_box,
                axis=axis,
                uses_primary_view_box=False,
            )

        self._traces[tag_name] = state
        self._plot_item.setTitle("")
        self._sync_overlay_views()
        self._apply_focus_style()
        return state

    def ensure_offset_trace(self, tag_name: str, delta: timedelta) -> OffsetTraceState:
        state = self.ensure_trace(tag_name)
        existing = next((item for item in state.offsets if item.delta == delta), None)
        if existing is not None:
            return existing

        curve = pg.PlotDataItem(
            pen=self._make_pen(state.color, emphasized=self._focused_tag in (None, tag_name), dashed=True)
        )
        state.view_box.addItem(curve)
        offset_state = OffsetTraceState(delta=delta, curve=curve)
        state.offsets.append(offset_state)
        return offset_state

    def update_trace_data(
        self,
        tag_name: str,
        *,
        raw_timestamps: np.ndarray,
        raw_values: np.ndarray,
        display_timestamps: np.ndarray,
        display_values: np.ndarray,
    ) -> None:
        state = self.ensure_trace(tag_name)
        state.raw_timestamps = np.asarray(raw_timestamps)
        state.raw_values = np.asarray(raw_values)
        state.curve.setData(
            x=self._to_plot_x_array(display_timestamps),
            y=np.asarray(display_values),
        )
        self._update_view_box_y_range(state)

    def update_offset_data(
        self,
        tag_name: str,
        delta: timedelta,
        *,
        raw_timestamps: np.ndarray,
        raw_values: np.ndarray,
        display_timestamps: np.ndarray,
        display_values: np.ndarray,
    ) -> None:
        offset_state = self.ensure_offset_trace(tag_name, delta)
        offset_state.raw_timestamps = np.asarray(raw_timestamps)
        offset_state.raw_values = np.asarray(raw_values)
        offset_state.curve.setData(
            x=self._to_plot_x_array(display_timestamps),
            y=np.asarray(display_values),
        )

        state = self.ensure_trace(tag_name)
        self._update_view_box_y_range(state)

    def set_focus(self, tag_name: str | None) -> None:
        self._focused_tag = tag_name
        self._apply_focus_style()

    def plot_pixel_width(self) -> int:
        width = int(self._plot_item.vb.sceneBoundingRect().width())
        if width <= 0:
            width = int(self.viewport().width())
        return max(width, 3)

    def current_time_range(self) -> tuple[datetime, datetime] | None:
        x_range = self._plot_item.vb.viewRange()[0]
        if len(x_range) != 2:
            return None
        return self._from_plot_x(x_range[0]), self._from_plot_x(x_range[1])

    def set_time_range(self, start: datetime, end: datetime) -> None:
        self._plot_item.setXRange(self._to_plot_x(start), self._to_plot_x(end), padding=0.02)

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasText():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasText():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasText():
            tag_name = event.mimeData().text().strip()
            if tag_name:
                self.tagDropped.emit(tag_name)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def _emit_visible_range(self, *_args) -> None:
        current_range = self.current_time_range()
        if current_range is None:
            return
        self.visibleRangeChanged.emit(*current_range)

    def _handle_mouse_moved(self, event) -> None:
        pos = event[0]
        if not self._plot_item.sceneBoundingRect().contains(pos):
            return

        mouse_point = self._plot_item.vb.mapSceneToView(pos)
        self._cursor_line.show()
        self._cursor_line.setPos(mouse_point.x())
        self.cursorTimestampChanged.emit(self._from_plot_x(mouse_point.x()))

    def _sync_overlay_views(self) -> None:
        primary_rect = self._plot_item.vb.sceneBoundingRect()
        for state in self._traces.values():
            if state.uses_primary_view_box:
                continue
            state.view_box.setGeometry(primary_rect)
            state.view_box.linkedViewChanged(self._plot_item.vb, state.view_box.XAxis)

    def _update_view_box_y_range(self, state: PlotTraceState) -> None:
        value_sets = [state.raw_values]
        value_sets.extend(offset.raw_values for offset in state.offsets if offset.raw_values.size)
        finite_values = [
            np.asarray(values, dtype=float)[np.isfinite(np.asarray(values, dtype=float))]
            for values in value_sets
            if np.asarray(values).size
        ]
        finite_values = [values for values in finite_values if values.size]
        if not finite_values:
            return

        merged = np.concatenate(finite_values)
        lower = float(np.nanmin(merged))
        upper = float(np.nanmax(merged))
        if np.isclose(lower, upper):
            padding = abs(lower) * 0.05 or 1.0
        else:
            padding = (upper - lower) * 0.05
        state.view_box.setYRange(lower - padding, upper + padding, padding=0.0)

    def _apply_focus_style(self) -> None:
        for state in self._traces.values():
            emphasized = self._focused_tag in (None, state.tag_name)
            state.curve.setPen(self._make_pen(state.color, emphasized=emphasized))
            for offset in state.offsets:
                offset.curve.setPen(
                    self._make_pen(state.color, emphasized=emphasized, dashed=True)
                )

            axis_color = QColor(state.color)
            axis_color.setAlpha(255 if emphasized else 90)
            if state.axis is not None:
                state.axis.setTextPen(axis_color)
                state.axis.setPen(pg.mkPen(axis_color))

    def _make_pen(self, color: str, *, emphasized: bool, dashed: bool = False):
        qcolor = QColor(color)
        qcolor.setAlpha(255 if emphasized else 85)
        return pg.mkPen(
            color=qcolor,
            width=2 if emphasized else 1,
            style=Qt.DashLine if dashed else Qt.SolidLine,
        )

    def _to_plot_x(self, value: datetime | np.datetime64 | float | int) -> float:
        if isinstance(value, datetime):
            return float(value.timestamp())
        if isinstance(value, np.datetime64):
            return float(value.astype("datetime64[us]").astype(object).timestamp())
        return float(value)

    def _to_plot_x_array(self, values: np.ndarray) -> np.ndarray:
        array = np.asarray(values)
        if array.size == 0:
            return np.array([], dtype=float)
        if np.issubdtype(array.dtype, np.datetime64):
            python_datetimes = array.astype("datetime64[us]").astype(object)
            return np.asarray([value.timestamp() for value in python_datetimes], dtype=float)
        return array.astype(float, copy=False)

    def _from_plot_x(self, value: float) -> datetime:
        return datetime.fromtimestamp(value)
