from __future__ import annotations

from ...domain.models import TraceRequest, TraceSeries


class TsDownsampleAdapter:
    """Planned tsdownsample integration for phase 3."""

    def downsample(self, request: TraceRequest, series: TraceSeries) -> TraceSeries:
        raise NotImplementedError("Phase 3 downsampling is not implemented yet.")
