from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np


@dataclass(frozen=True)
class WorkbookSheet:
    name: str
    row_count: int
    column_count: int
    timestamp_column: str | None = None


@dataclass(frozen=True)
class TagDescriptor:
    name: str
    unit: str | None = None
    source_sheet: str | None = None
    path: tuple[str, ...] = ()


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class TraceRequest:
    tag_name: str
    window: TimeWindow
    pixel_width: int | None = None
    offset: timedelta | None = None


@dataclass(frozen=True)
class TraceSeries:
    tag_name: str
    timestamps: np.ndarray
    values: np.ndarray
    offset: timedelta | None = None


@dataclass(frozen=True)
class VisibleStats:
    tag_name: str
    current_value: float | None
    minimum: float | None
    maximum: float | None
    average: float | None
    previous_values: tuple[float | None, ...] = field(default_factory=tuple)
    next_values: tuple[float | None, ...] = field(default_factory=tuple)
