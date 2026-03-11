# wte2

Local SCADA-style trend viewer for Excel exports, with interaction patterns modeled on ABB 800xA trend ruler behavior.

## Included

- `scada_trend_viewer/`: self-contained Python webapp
- `docs/Raw Data.xlsx`: sample workbook for immediate testing
- `docs/System 800xA Operations page 163.pdf`: ABB vertical ruler reference
- `docs/System 800xA Operations page 165.pdf`: ABB horizontal ruler reference

## Run

```bash
python3 scada_trend_viewer/server.py
```

Then open `http://127.0.0.1:8123`.

If you are running in WSL, VM, or another remote environment, use:

```bash
python3 scada_trend_viewer/server.py --host 0.0.0.0
```

Then open `http://<host-ip>:8123`.
