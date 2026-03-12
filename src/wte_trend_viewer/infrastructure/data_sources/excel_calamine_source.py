from __future__ import annotations

from pathlib import Path
from typing import Sequence


class ExcelCalamineSource:
    """Planned Polars + calamine workbook source for phase 2."""

    def inspect(self, source: str | Path):
        raise NotImplementedError("Phase 2 workbook inspection is not implemented yet.")

    def load(
        self,
        source: str | Path,
        *,
        sheet_names: Sequence[str],
    ) -> object:
        raise NotImplementedError("Phase 2 workbook loading is not implemented yet.")
