# WTE Trend Viewer

Phase 1 of the SCADA trend viewer blueprint is now scaffolded in this repository.

Current scope:

- PySide6 application bootstrap
- Main window skeleton with a left tag browser dock
- Placeholder white trend canvas
- Bottom legend and analytics dock
- ISA-101-inspired muted industrial styling

Run locally:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\wte-trend-viewer
```

