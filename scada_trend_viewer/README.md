# SCADA Trend Viewer

Local ABB 800xA-inspired trend viewer for Excel workbooks.

## Run

```bash
python3 scada_trend_viewer/server.py
```

Then open `http://127.0.0.1:8123`.

## Notes

- Bundled `.xlsx` files in [`docs`](/home/jakob/OpenAI/docs) appear automatically in the workbook selector.
- You can also upload another Excel workbook directly from the UI.
- Mouse and keyboard controls mirror the ABB pages:
  - `Vertical` mode: click/drag in the trend area, then use `Left` and `Right`
  - `Horizontal` mode: click/drag in the trend area, then use `Up` and `Down`
  - Mouse wheel zooms the visible time window
