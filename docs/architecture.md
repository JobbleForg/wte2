# Architecture

## Intent

The PDF describes a phased implementation, but the feature set spans multiple
technical concerns: desktop UI, time-series ingestion, downsampling, analytics,
and asynchronous execution. This scaffold separates those concerns so each phase
can be implemented without collapsing the codebase into a single monolithic
window file.

## Layers

### `domain/`

Holds stable business objects and interfaces that should survive UI rewrites or
data-source changes.

- `models.py`
  Purpose: tag metadata, time windows, trace requests, analytics summaries.
- `protocols.py`
  Purpose: contracts for workbook sources, downsamplers, and repositories.

### `application/`

Owns the use-case layer. These modules orchestrate the domain contracts and are
the right home for logic that spans multiple widgets or infrastructure pieces.

- `services/workbook_service.py`
  PDF phases: 2, 9, future ingestion backends.
- `services/trend_service.py`
  PDF phases: 3, 4, 5, 8.
- `services/inspection_service.py`
  PDF phase: 7.

### `infrastructure/`

Concrete adapters and low-level integrations live here. This keeps third-party
library choices localized.

- `data_sources/excel_calamine_source.py`
  Current target: Polars + `engine="calamine"`.
  Future additions: Parquet, SQL, REST historian adapters.
- `processing/downsampler.py`
  Current target: `tsdownsample` MinMaxLTTB.
- `threading/workbook_loader.py`
  Current target: Qt thread and signal plumbing for non-blocking loads.

### `ui/`

The presentation layer. It should depend on `application/`, not the other way
around.

- `main_window.py`
  Main shell composition and dock layout.
- `docks/`
  Tag browser and analytics panes.
- `plot/`
  Plot canvas and future multi-axis plotting code.
- `models/`
  Qt item and table models.
- `styles/`
  ISA-101 visual tokens and stylesheet generation.

## Why this structure fits the PDF phases

- Phase 1 can be built almost entirely inside `ui/`.
- Phases 2 and 3 land in `infrastructure/` behind `domain` contracts.
- Phases 4 through 8 become smaller because the UI widgets already have a home
  and the orchestration layer already exists.
- Phase 9 plugs into the existing `threading/` package without rewriting the UI.

## Future expansion points

- Alternative data sources can be added under `infrastructure/data_sources/`
  without changing the plotting widgets.
- Export, annotations, bookmarks, alarms, or report generation can become new
  `application/services/` modules.
- A richer analytics table model can replace the placeholder table without
  changing the main window layout contract.
