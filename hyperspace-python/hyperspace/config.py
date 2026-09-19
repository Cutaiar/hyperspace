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

    [bridge]                # lanes out / external lanes in over MIDI (bridge.py)
    enabled = false         # true opens the bridge; off, it is never imported
    out = "IAC"             # substring of the virtual port the lanes go out on ("" = none)
    in = ""                 # substring of the port external lanes come in on ("" = none)
    encoding = "pitch"      # "pitch": lane i → pitch bend on channel+i (16 lanes)
                            # "cc14": lane i → CC cc+i (MSB) / cc+i+32 (LSB) on channel
    channel = 0             # 0-based: the first lane's channel (pitch) / the pair channel
    cc = 16                 # cc14: the first lane's MSB controller, 0–31 (32−cc lanes)
    rate = 100              # messages a second per lane at most (0 = every frame)
    send = ["lane:*"]       # what goes out, in lane order: "lane:*", "lane:3", "param:<id>"
    in_lanes = 16           # size of the `ext` vector the inbound lanes fill
"""

from __future__ import annotations

import tomllib
from pathlib import Path

FILE = Path("config.toml")

DEFAULTS: dict = {
    "midi": {"enabled": True, "port": None, "profile": "apc40", "map": "midi_map.json"},
    # overlay.py: start floating over the screen; ground 0 = see-through
    "overlay": {"on_start": False, "passthrough": True, "bg": 0.0, "alpha": 1.0},
    # bridge.py: the analyzer's lanes out to a DAW, external lanes in — off by default
    "bridge": {"enabled": False, "out": "IAC", "in": "", "encoding": "pitch", "channel": 0,
               "cc": 16, "rate": 100, "send": ["lane:*"], "in_lanes": 16},
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
