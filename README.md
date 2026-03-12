# WTE Trend Viewer

This branch has been reset to a clean, phase-aware scaffold based on the PDF
blueprint in `Building a Modern SCADA Trend Viewer.pdf`.

The goal of this scaffold is to make future implementation predictable:

- `ui/` owns the PySide6 and PyQtGraph presentation layer
- `application/` owns orchestration and phase-level use cases
- `domain/` owns stable data contracts and extension points
- `infrastructure/` owns concrete adapters for Excel, downsampling, and threading
- `docs/` maps the PDF phases to the codebase so future work lands in the right place

## Current status

- The old prototype code has been removed from this branch.
- A minimal phase-1 shell is in place and can be launched.
- The later-phase modules exist as intentional scaffolding and extension points, not as full features.

## Repository layout

```text
docs/
  architecture.md
  phase-roadmap.md
src/wte_trend_viewer/
  bootstrap.py
  config/
  domain/
  application/
  infrastructure/
  ui/
tests/
  smoke/
```

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .[dev]
.\.venv\Scripts\wte-trend-viewer
```

## Next implementation path

1. Finish phase 1 polish inside `ui/`.
2. Build the Polars workbook ingestion contracts in `infrastructure/data_sources/`.
3. Add the downsampling pipeline in `infrastructure/processing/`.
4. Connect the application services to the UI one phase at a time.
