"""Rig configuration — an optional config.toml in the library home.

The home is ``$HYPERSPACE_HOME`` (default ``~/Hyperspace``, library.py);
a config.toml still sitting in the working directory is copied there on
the first run. Everything has a default, so the file is only for what
differs on this machine. Adapters are enabled here, not in code
(BLUEPRINT §3.6).

    [midi]
    enabled = true          # false leaves the adapter out entirely
    port = "APC40"          # substring of the port name; default from the profile
    profile = "apc40"       # device profile (hyperspace/<profile>.py)
    map = "midi_map.json"   # binding table, relative to the library home;
                            # written by right-click → Learn

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

    [dream]                 # the look-back's Deep Dream worker (dream.py, torch)
    enabled = false         # true opens the worker; off, torch is never imported
    device = "auto"         # "auto" (MPS when there, else CPU), "mps", "cpu"
    precision = "fp32"      # or "fp16": ~10 % faster on VGG, more p99 outliers
    weights_dir = ""        # pretrained weights; "" = <library home>/weights

    [hands]                 # Ultraleap hands → MIDI (hands.py, the `leap` bindings)
    enabled = false         # true opens the tracker; off, `leap` is never imported
    mode = "desktop"        # camera looks up from below; "screentop" from above, "hmd"
    dofs = ["x", "y", "z", "roll", "pitch", "yaw"]   # per hand, in CC order; also
                            # grab, pinch, grab_angle, pinch_mm
    channel = 15            # 0-based (MIDI ch 16), clear of the APC40
    cc = 102                # left hand cc…cc+n−1, right cc+n…cc+2n−1
    presence = true         # note on/off as a hand enters / leaves
    note = 120              # left hand's presence note, right is note+1
    out = ""                # MIDI out for a DAW: port substring, else a new
                            # virtual port of that name ("" = none)
    min_confidence = 0.1
    min_cutoff = 1.0        # smoothing at rest (Hz) — lower is steadier
    beta = 4.0              # smoothing speed gain — higher follows fast moves closer
    hysteresis = 0.35       # MIDI steps past the half-step before a value moves
    calibration = "hands.json"   # ranges, relative to the library home
                                 # (tools/hands_probe.py --calibrate writes it)
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from . import library

FILE = Path("config.toml")

DEFAULTS: dict = {
    "midi": {"enabled": True, "port": None, "profile": "apc40", "map": "midi_map.json"},
    # overlay.py: start floating over the screen; ground 0 = see-through
    "overlay": {"on_start": False, "passthrough": True, "bg": 0.0, "alpha": 1.0},
    # bridge.py: the analyzer's lanes out to a DAW, external lanes in — off by default
    "bridge": {"enabled": False, "out": "IAC", "in": "", "encoding": "pitch", "channel": 0,
               "cc": 16, "rate": 100, "send": ["lane:*"], "in_lanes": 16},
    # dream.py: the temporal Deep Dream behind the look-back — off by default
    "dream": {"enabled": False, "device": "auto", "precision": "fp32", "weights_dir": ""},
    # hands.py: Ultraleap hands as MIDI CCs and hand lanes — off by default;
    # the rest of its defaults live in hands.DEFAULTS
    "hands": {"enabled": False, "calibration": "hands.json"},
}


def load(path: Path | None = None) -> dict:
    """The config, defaults filled in; `path` defaults to the library home's."""
    if path is None:
        path = library.ensure_home() / FILE
    cfg = {k: dict(v) for k, v in DEFAULTS.items()}
    if path.exists():
        try:
            data = tomllib.loads(path.read_text())
        except (OSError, ValueError) as e:
            cfg["error"] = f"config: {e}"
            data = {}
        for section, values in data.items():
            if isinstance(values, dict):
                cfg.setdefault(section, {}).update(values)
            else:
                cfg[section] = values
    # the MIDI map lives next to the config unless it says otherwise
    m = cfg["midi"].get("map")
    if m and not Path(m).is_absolute():
        cfg["midi"]["map"] = str(path.parent / m)
    c = cfg["hands"].get("calibration")
    if c and not Path(c).is_absolute():
        cfg["hands"]["calibration"] = str(path.parent / c)
    return cfg
