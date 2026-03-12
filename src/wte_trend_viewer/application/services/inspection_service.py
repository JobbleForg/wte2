from __future__ import annotations

from ...domain.models import VisibleStats


class InspectionService:
    """Reserved for phase 7 cursor analytics and inspection-mode calculations."""

    def summarize_visible_trace(self, tag_name: str) -> VisibleStats:
        raise NotImplementedError("Phase 7 analytics have not been implemented yet.")
