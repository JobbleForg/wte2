from __future__ import annotations

from pathlib import Path
from typing import Sequence

from ...domain.protocols import WorkbookSource


class WorkbookService:
    """Owns workbook inspection and loading orchestration for phases 2 and 9."""

    def __init__(self, source: WorkbookSource) -> None:
        self._source = source

    def inspect_workbook(self, source_path: str | Path):
        return self._source.inspect(source_path)

    def load_workbook(
        self,
        source_path: str | Path,
        *,
        sheet_names: Sequence[str],
    ) -> object:
        return self._source.load(source_path, sheet_names=sheet_names)
