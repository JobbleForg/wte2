# Phase Roadmap

The PDF defines nine implementation phases. This repo is now organized so each
phase has a clear landing zone.

## Phase 1: Environment Initialization and Core GUI Skeleton

Primary modules:

- `src/wte_trend_viewer/bootstrap.py`
- `src/wte_trend_viewer/ui/main_window.py`
- `src/wte_trend_viewer/ui/docks/tag_browser_dock.py`
- `src/wte_trend_viewer/ui/docks/analytics_dock.py`
- `src/wte_trend_viewer/ui/plot/trend_canvas.py`
- `src/wte_trend_viewer/ui/styles/isa101.py`

## Phase 2: High-Performance Polars Data Ingestion Layer

Primary modules:

- `src/wte_trend_viewer/domain/protocols.py`
- `src/wte_trend_viewer/application/services/workbook_service.py`
- `src/wte_trend_viewer/infrastructure/data_sources/excel_calamine_source.py`

## Phase 3: SIMD-Accelerated Downsampling Middleware

Primary modules:

- `src/wte_trend_viewer/domain/protocols.py`
- `src/wte_trend_viewer/application/services/trend_service.py`
- `src/wte_trend_viewer/infrastructure/processing/downsampler.py`

## Phase 4: PyQtGraph Multi-Axis Canvas Implementation

Primary modules:

- `src/wte_trend_viewer/ui/plot/trend_canvas.py`
- `src/wte_trend_viewer/application/services/trend_service.py`

## Phase 5: Dynamic Resampling on Zoom/Pan

Primary modules:

- `src/wte_trend_viewer/ui/plot/trend_canvas.py`
- `src/wte_trend_viewer/application/services/trend_service.py`

## Phase 6: Drag-and-Drop Tag Tree Management

Primary modules:

- `src/wte_trend_viewer/ui/models/tag_tree_model.py`
- `src/wte_trend_viewer/ui/docks/tag_browser_dock.py`
- `src/wte_trend_viewer/ui/plot/trend_canvas.py`

## Phase 7: Rulers, Analytics, and Inspection Mode

Primary modules:

- `src/wte_trend_viewer/application/services/inspection_service.py`
- `src/wte_trend_viewer/ui/docks/analytics_dock.py`
- `src/wte_trend_viewer/ui/plot/trend_canvas.py`

## Phase 8: Time Offset and Trace Manipulation

Primary modules:

- `src/wte_trend_viewer/application/services/trend_service.py`
- `src/wte_trend_viewer/ui/docks/analytics_dock.py`
- `src/wte_trend_viewer/ui/plot/trend_canvas.py`

## Phase 9: Multithreading and Asynchronous Operations

Primary modules:

- `src/wte_trend_viewer/infrastructure/threading/workbook_loader.py`
- `src/wte_trend_viewer/application/services/workbook_service.py`
- `src/wte_trend_viewer/ui/main_window.py`

## After phase 9

Likely future additions the scaffold already anticipates:

- Parquet and SQL sources in `infrastructure/data_sources/`
- annotations and bookmarks in `application/services/`
- export and reporting workflows in `application/services/`
- richer Qt models in `ui/models/`
