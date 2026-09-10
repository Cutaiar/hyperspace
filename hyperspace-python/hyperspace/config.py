"""Rig configuration — an optional config.toml in the working directory.

Everything has a default, so the file is only for what differs on this
machine. Adapters are enabled here, not in code (BLUEPRINT §3.6).

    [midi]
    enabled = true          # false leaves the adapter out entirely
    port = "APC40"          # substring of the port name; default from the profile
    profile = "apc40"       # device profile (hyperspace/<profile>.py)
    map = "midi_map.json"   # binding table; written by right-click → Learn

    [overlay]
    on_start = false        # launch straight into overlay mode
    passthrough = true      # clicks go to the window underneath (G / pan toggles)
    bg = 0.0                # ground darkness in overlay: 0 see-through, 1 black
    alpha = 1.0             # whole-window opacity
"""

from __future__ import annotations

import tomllib
from pathlib import Path

FILE = Path("config.toml")

DEFAULTS: dict = {
    "midi": {"enabled": True, "port": None, "profile": "apc40", "map": "midi_map.json"},
    # overlay.py: start floating over the screen; ground 0 = see-through
    "overlay": {"on_start": False, "passthrough": True, "bg": 0.0, "alpha": 1.0},
}


def load(path: Path = FILE) -> dict:
    cfg = {k: dict(v) for k, v in DEFAULTS.items()}
    if not path.exists():
        return cfg
    try:
        data = tomllib.loads(path.read_text())
    except (OSError, ValueError) as e:
        cfg["error"] = f"config: {e}"
        return cfg
    for section, values in data.items():
        if isinstance(values, dict):
            cfg.setdefault(section, {}).update(values)
        else:
            cfg[section] = values
    return cfg
