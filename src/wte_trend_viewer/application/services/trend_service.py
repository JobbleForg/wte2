from __future__ import annotations

from ...domain.models import TraceRequest, TraceSeries
from ...domain.protocols import Downsampler, TrendRepository


class TrendService:
    """Reserved for phases 3, 4, 5, and 8."""

    def __init__(self, repository: TrendRepository, downsampler: Downsampler) -> None:
        self._repository = repository
        self._downsampler = downsampler

    def get_visible_trace(self, request: TraceRequest) -> TraceSeries:
        raw = self._repository.get_trace(request)
        if request.pixel_width is None:
            return raw
        return self._downsampler.downsample(request, raw)
