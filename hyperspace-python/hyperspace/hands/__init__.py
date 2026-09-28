"""Ultraleap hands — a self-contained instrument, host optional.

This package is written to be lifted out whole. The rule that keeps it
liftable: **core.py and signal.py import nothing from hyperspace.** They
are the instrument — tracking, features, the analog chain, the pinch
switches, MIDI out. Everything they need from a host arrives as an
argument, duck-typed, never imported:

  register(reg, settings)     `reg` is anything with .continuous / .enum
                              / .toggle — the parameter registry. Drop it
                              and the setup is still plain dataclasses.
  HandsIO(settings, cfg,      `source` is anything with .latest(); `out`
          source=…, out=…)    anything with .send(). Both default to the
                              real ones, so tests and a host substitute.
  HandsIO.poll(dt, learn,     `learn` needs .learning / .learn_source(src,
                router)       when=) (the host's learn.Learn); `router` needs .feed and
                              takes .labels / .gates / .rests dicts (poll
                              creates any that are missing). Pass neither
                              and the hands still run.

panel.py is the one piece that knows this host: it draws the HANDS page
with the host's imgui panel and palette. Extracting the package means
replacing panel.py, nothing else. tests/test_hands_boundary.py fails the
build if core or signal ever grows a hyperspace import.

What the host must still provide when embedded (see app.py):
  * call register() once, so the setup becomes saveable params
  * call poll() once a render frame
  * an entry in ui.PAGES and a page method, to reach panel.page()
"""

from __future__ import annotations

from .core import (
    BIPOLAR,
    CAL_FILE,
    CAL_MIN_SAMPLES,
    CAL_SCHEMA,
    DEFAULT_DOFS,
    DEFAULTS,
    FEATURES,
    GROUP,
    LEARN_MOVE,
    PALM_W,
    PINCHES,
    SHAPE_KEYS,
    SIDES,
    STALE_S,
    TRACKING_MODES,
    X_RANGE,
    AxisSettings,
    AxisState,
    Gate,
    HandSettings,
    HandsIO,
    LeapSource,
    OneEuro,
    conflicts,
    default_range,
    features,
    load_calibration,
    mirror,
    pinches,
    register,
    save_calibration,
)

__all__ = [
    "BIPOLAR", "CAL_FILE", "CAL_MIN_SAMPLES", "CAL_SCHEMA", "DEFAULTS", "DEFAULT_DOFS",
    "FEATURES", "GROUP", "LEARN_MOVE", "PALM_W", "PINCHES", "SHAPE_KEYS", "SIDES",
    "STALE_S", "TRACKING_MODES", "X_RANGE", "AxisSettings", "AxisState", "Gate",
    "HandSettings", "HandsIO", "LeapSource", "OneEuro", "conflicts", "default_range",
    "features", "load_calibration", "mirror", "pinches", "register", "save_calibration",
]
