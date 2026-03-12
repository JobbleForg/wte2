from __future__ import annotations

from dataclasses import dataclass


APP_NAME = "WTE Trend Viewer"
ORGANIZATION_NAME = "WORKBOT"


@dataclass(frozen=True)
class WindowDefaults:
    width: int = 1560
    height: int = 960
    minimum_left_pane_width: int = 320


WINDOW_DEFAULTS = WindowDefaults()
