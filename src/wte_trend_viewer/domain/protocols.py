from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from .models import TimeWindow, TraceRequest, TraceSeries, WorkbookSheet


class WorkbookSource(Protocol):
    def inspect(self, source: str | Path) -> tuple[WorkbookSheet, ...]:
        """Return workbook metadata without touching the UI."""

    def load(
        self,
        source: str | Path,
        *,
        sheet_names: Sequence[str],
    ) -> object:
        """Return the normalized workbook dataset for selected sheets."""


class Downsampler(Protocol):
    def downsample(self, request: TraceRequest, series: TraceSeries) -> TraceSeries:
        """Return a visually equivalent, screen-width-sized trace."""


class TrendRepository(Protocol):
    def get_trace(self, request: TraceRequest) -> TraceSeries:
        """Return raw or normalized trace data for a tag and time window."""

    def get_window(self, window: TimeWindow, tags: Sequence[str]) -> object:
        """Return a filtered dataset for analytics or export workflows."""
