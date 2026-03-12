from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class TrendCanvasPlaceholder(QFrame):
    """Phase-1 placeholder canvas on the future plot widget path."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("trendCanvas")
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("QFrame#trendCanvas { background-color: #FFFFFF; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._title = QLabel("Main Trend Viewport", self)
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet(
            "background: transparent; color: #5B5B5B; font-size: 11pt; font-weight: 600;"
        )
        layout.addWidget(self._title)
        layout.addStretch(1)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        frame_rect = self.rect().adjusted(48, 52, -24, -36)
        painter.setPen(QPen(QColor("#7A7A7A"), 1))
        painter.drawRect(frame_rect)

        grid_pen = QPen(QColor("#B0B0B0"), 1, Qt.DashLine)
        painter.setPen(grid_pen)
        for step in range(1, 5):
            y = frame_rect.top() + step * frame_rect.height() / 5
            painter.drawLine(frame_rect.left(), int(y), frame_rect.right(), int(y))

        axis_pen = QPen(QColor("#4E5963"), 2)
        painter.setPen(axis_pen)
        painter.drawLine(frame_rect.bottomLeft(), frame_rect.topLeft())
        painter.drawLine(frame_rect.bottomLeft(), frame_rect.bottomRight())

        trace_pen = QPen(QColor("#365C7D"), 2)
        painter.setPen(trace_pen)
        points = [
            QPointF(frame_rect.left() + frame_rect.width() * 0.05, frame_rect.bottom() - 20),
            QPointF(frame_rect.left() + frame_rect.width() * 0.25, frame_rect.top() + 80),
            QPointF(frame_rect.left() + frame_rect.width() * 0.45, frame_rect.top() + 110),
            QPointF(frame_rect.left() + frame_rect.width() * 0.65, frame_rect.top() + 45),
            QPointF(frame_rect.left() + frame_rect.width() * 0.9, frame_rect.top() + 130),
        ]
        for start, end in zip(points, points[1:]):
            painter.drawLine(start, end)
