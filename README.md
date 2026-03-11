# WTE Trend Viewer

Phases 1 through 9 of the SCADA trend viewer blueprint are now implemented in this repository.

Current scope:

- ISA-101-style PySide6 desktop shell with toolbar, tag browser, plot area, and analytics grid
- Background Excel loading on a worker thread with Polars `engine="calamine"`
- Automatic timestamp-column inference for workbook imports
- Normalized master timeline with forward-filled sparse tag values
- Custom hierarchical `QAbstractItemModel` tag tree with drag-and-drop support
- PyQtGraph multi-axis trend canvas with linked X ranges and independent Y axes
- `tsdownsample` MinMaxLTTB middleware for screen-width-aware active zoom
- Live ruler/cursor analytics with adjacent raw values and visible-window min/max/avg
- ABB-style time-offset overlays with dashed comparison traces

Backend example:

```python
from wte_trend_viewer import DataManager

manager = DataManager()
manager.load_excel("trend-export.xlsx", timestamp_column="Timestamp")

window = manager.get_window(
    start="2026-03-01T00:00:00",
    end="2026-03-01T12:00:00",
    tags=["SD_Pressure", "FW_Flow"],
)

downsampled = manager.get_downsampled_window(
    start="2026-03-01T00:00:00",
    end="2026-03-01T12:00:00",
    tag="SD_Pressure",
    pixel_width=1920,
)
```

UI workflow:

- Launch the app
- Click `Open Excel`
- Wait for the workbook to load in the background
- Drag a tag from the left tree onto the plot
- Zoom or pan to trigger active resampling
- Move the mouse across the plot to update the analytics grid
- Right-click a table row to add a time-offset trace

Run locally:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\wte-trend-viewer
```

