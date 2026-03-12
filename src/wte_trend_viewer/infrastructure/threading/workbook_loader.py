from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal


class WorkbookLoadSignals(QObject):
    """Signal bundle reserved for phase 9 background workbook loading."""

    started = Signal(str)
    failed = Signal(str)
    finished = Signal(object)


class WorkbookLoadTask:
    """Placeholder task wrapper for the future threaded load pipeline."""

    def __init__(self, workbook_path: str | Path) -> None:
        self.workbook_path = Path(workbook_path)
        self.signals = WorkbookLoadSignals()

    def run(self) -> None:
        raise NotImplementedError("Phase 9 background loading is not implemented yet.")
