"""Rig configuration — an optional config.toml in the library home.

The home is ``$HYPERSPACE_HOME`` (default ``~/Hyperspace``, library.py);
a config.toml still sitting in the working directory is copied there on
the first run. Everything has a default, so the file is only for what
differs on this machine. Adapters are enabled here, not in code
(BLUEPRINT §3.6). Three are on by default: the MIDI adapter (it is the one
that also holds Learn) and the gamepad cost nothing when the device is
absent, and the dream worker is part of the show (decision 23 (a),
2026-09-29: torch is a main dependency). The bridge and the hands tracker
are off until asked for, and their modules are never imported until then;
dream.py, too, is imported only when its gate is open.

    [midi]
    enabled = true          # false leaves the adapter out entirely (and hand Learn with it)
    port = "APC40"          # substring of the port name; default from the profile
    profile = "apc40"       # device profile (hyperspace/<profile>.py)
    map = "midi_map.json"   # a pre-plan-09 MIDI map, relative to this file's
                            # folder (the library home when loaded from there);
                            # read once, only when bindings.json does
                            # not exist yet (Bindings.load). Learn writes
                            # <home>/bindings.json (routing.py), not this file

    [output]                # where the render window goes and how it looks
                            # (overlay.py; app.py seeds the output.* params)
    overlay = false         # overlay mode exists at all (decision 21 (a)): false,
                            # the render window is always opaque — no transparent
                            # framebuffer, and T / MASTER select / the panel cannot
                            # float it see-through; true for a laptop demo
    monitor = -1            # which screen the RENDER window opens on, and the one
                            # fullscreen covers: a screen index, or -1 = where it
                            # was last time (else the primary screen)
    control_monitor = -1    # which screen the CONTROL window opens on: an index,
                            # or -1 = where it was last time (else the primary).
                            # "Last time" is <home>/windows.json (placement.py),
                            # written on quit and on restart; delete it to forget.
                            # An index with no such screen is treated as -1, with
                            # a note
    fullscreen = false      # launch fullscreen on that screen
    on_start = false        # launch straight into overlay mode (needs overlay = true)
    passthrough = true      # clicks go to the window underneath (G / pan toggles)
    bg = 0.0                # ground darkness in overlay: 0 see-through, 1 black
    alpha = 1.0             # whole-window opacity
                            # [overlay] is the pre-split name of this section:
                            # still read, merged under [output] (which wins),
                            # and noted once on stderr so the file gets renamed

A file that will not parse is not fatal: the defaults stand and
``cfg["error"]`` carries the message; ``cfg["notes"]`` carries requests
like the rename above. The SYSTEM page shows both.

    [gamepad]               # the Xbox pad polled through GLFW (gamepad.py)
    enabled = true          # false never polls for one

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
    enabled = true          # on by default; false keeps torch from ever being imported
    device = "auto"         # "auto" (MPS when there, else CPU), "mps", "cpu"
    precision = "fp32"      # or "fp16": ~10 % faster on VGG, more p99 outliers
    weights_dir = ""        # pretrained weights; "" = <library home>/weights

    [hands]                 # Ultraleap hands (hands/, the `leap` bindings) — the rig;
                            # the performance setup is the HANDS page / `hands` presets.
                            # The defaults are hands/core.py's DEFAULTS, the one table
    enabled = false         # true opens the tracker; off, `leap` is never imported
    mode = "desktop"        # camera looks up from below; "screentop" from above, "hmd"
    dofs = ["x", "y", "z", "roll", "pitch", "yaw"]   # per hand, in axis order; also
                            # grab, pinch, grab_angle, pinch_mm
    out = "Hyperspace Hands"   # MIDI out for a DAW: port substring, else a new
                               # virtual port of that name ("" = none)
    channel = 16            # 1-based: the channel every axis starts on
    cc = 102                # starting CCs: left hand cc…cc+n−1, right cc+n…cc+2n−1
    presence = true         # note on/off to the DAW as a hand enters / leaves
    note = 120              # left hand's presence note, right is note+1
    min_confidence = 0.1
    calibration = "hands.json"   # the box's ranges, relative to the library home
    tape = ""               # a hand tape (tools/hands_tape.py record) to play instead
                            # of the camera, relative to this file; "" = the camera
"""

from __future__ import annotations

import copy
import sys
import tomllib
from pathlib import Path

from . import library, placement

FILE = Path("config.toml")
LEGACY_OUTPUT = "overlay"   # the section [output] was called before the split

DEFAULTS: dict = {
    # midi.map: the legacy midi_map.json, merged once when bindings.json is missing
    "midi": {"enabled": True, "port": None, "profile": "apc40", "map": "midi_map.json"},
    # overlay.py: the render window's placement and look; ground 0 = see-through.
    # overlay: off, the window is opaque and overlay cannot switch on
    # (decision 21 (a), plan 14 WP2). monitor / control_monitor: the screen
    # each window opens on, −1 = where it was last time (placement.py)
    "output": {"overlay": False, "monitor": -1, "control_monitor": -1, "fullscreen": False,
               "on_start": False, "passthrough": True, "bg": 0.0, "alpha": 1.0},
    # gamepad.py: the Xbox pad — on by default, inert when absent
    "gamepad": {"enabled": True},
    # bridge.py: the analyzer's lanes out to a DAW, external lanes in — off by default
    "bridge": {"enabled": False, "out": "IAC", "in": "", "encoding": "pitch", "channel": 0,
               "cc": 16, "rate": 100, "send": ["lane:*"], "in_lanes": 16},
    # dream.py: the temporal Deep Dream behind the look-back — on by default
    # (decision 23 (a)); a worker that will not start is said on the panel
    "dream": {"enabled": True, "device": "auto", "precision": "fp32", "weights_dir": ""},
    # hands/: Ultraleap hands as MIDI CCs and hand lanes — off by default.
    # Its section is not here: load() fills it from hands/core.py's DEFAULTS,
    # the one table (every key documented there), read at call time so this
    # module imports no adapter
}


def load(path: Path | None = None) -> dict:
    """The config, defaults filled in; `path` defaults to the library home's."""
    if path is None:
        path = library.ensure_home() / FILE
    from .hands.core import DEFAULTS as HANDS  # the one [hands] table (audit N1)

    cfg = copy.deepcopy(DEFAULTS)                 # a file may append to a list
    cfg["hands"] = copy.deepcopy(HANDS)
    if path.exists():
        try:
            data = tomllib.loads(path.read_text())
        except (OSError, ValueError) as e:
            cfg["error"] = f"config: {e}"
            data = {}
        bad = []
        for section, values in data.items():
            if isinstance(values, dict):
                cfg.setdefault(section, {}).update(values)
            else:
                # `midi = true` in place of [midi]: the defaults stand and the
                # SYSTEM page says so — the _open_* gates expect a table
                bad.append(f"[{section}] must be a table, not {values!r}")
        if bad:
            cfg["error"] = "config: " + "; ".join(bad)
        legacy = cfg.pop(LEGACY_OUTPUT, None)
        if isinstance(legacy, dict):
            # the pre-split section name: its keys land under [output], a
            # real [output] wins key by key, and the file is asked to catch up
            # — on stderr and on the SYSTEM page (cfg["notes"])
            real = data.get("output")
            real = real if isinstance(real, dict) else {}   # a scalar was reported above
            cfg["output"] = {**DEFAULTS["output"], **legacy, **real}
            note = f"config: [{LEGACY_OUTPUT}] is now [output] — rename the section in {path}"
            cfg["notes"] = [note]
            print(note, file=sys.stderr)
    # a screen index is a whole number: `monitor = "left"` is −1 from here
    # on (where the window was last time) and the SYSTEM page says so —
    # whether that screen exists is placement's to say, at the launch
    for key in ("monitor", "control_monitor"):
        cfg["output"][key], note = placement.read(key, cfg["output"].get(key, -1))
        if note:
            cfg.setdefault("notes", []).append(note)
            print(note, file=sys.stderr)
    # the MIDI map lives next to the config unless it says otherwise
    m = cfg["midi"].get("map")
    if m and not Path(m).is_absolute():
        cfg["midi"]["map"] = str(path.parent / m)
    for key in ("calibration", "tape"):
        c = cfg["hands"].get(key)
        if c and not Path(c).is_absolute():
            cfg["hands"][key] = str(path.parent / c)
    return cfg
