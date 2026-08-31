"""Global interface themes — emulator-style save states for the whole surface.

A theme snapshots everything the control surface can set in one go: the
full ViewState (shape, planes, speed, brightness, 4D depth, camera
transform, instances, face pattern, bitmap layer…), the six EQ band
strips, the master faders and the selected scene. Loading one cuts the
whole look over in a single frame, so two contrasting slots can be
flipped between on the beat.

F1–F8 load slots 1–8; ⇧F1–F8 save into them. Slots persist in
presets.json in the working directory, next to imgui.ini. Slots 1 and 2
ship seeded with the two house moods and can be overwritten like any
other slot (delete presets.json to get the seeds back).
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .bands import Params

SLOTS = 8
FILE = Path("presets.json")

# Rotation phases stay live across a switch: a theme changes the look,
# not where the shape happens to be in its spin, so motion never snaps.
VIEW_SKIP = {"ang"}

# slot 0 — one big slow torus rolling under water caustics
BIG_BLUE_WAVE = {
    "name": "BIG BLUE WAVE",
    "scene": 2,  # Glacial Drift
    "view": {
        "shape": 17,          # Clifford torus
        "speed": 0.22,
        "depth4": 2.2,
        "bright": 1.25,
        "points": False,
        "faces": True,
        "planes": [False, False, True, True, False, False],
        "pattern": 5,         # CAUSTIC
        "pattern_mix": 1.0,
        "zoom": 0.9,
    },
}

# slot 1 — a grid of 24-cells orbiting each other, faces on fire
EMBER_ORBIT = {
    "name": "EMBER ORBIT",
    "scene": 1,  # Kick & Sizzle
    "view": {
        "shape": 10,          # 24-cell
        "speed": 0.85,
        "depth4": 2.9,
        "bright": 1.5,
        "points": True,
        "lines": False,
        "faces": True,
        "planes": [True, True, False, True, False, True],
        "pattern": 11,        # EMBER
        "pattern_mix": 1.0,
        "instances": 9,
        "inst_motion": 1,     # ORBIT
        "inst_amp": 0.35,
        "inst_rate": 1.4,
        "zoom": 0.5,
    },
}

DEFAULT_THEMES = [BIG_BLUE_WAVE, EMBER_ORBIT]


class Presets:
    """Owns the slot table, applies and captures themes, persists the file."""

    def __init__(self, view, control, audio, path: Path = FILE):
        self.view = view
        self.control = control
        self.audio = audio
        self.path = path
        self.slots: list[dict | None] = [None] * SLOTS
        self.active = -1  # last slot loaded, -1 until one is
        self.error = ""
        self._read()
        for i, theme in enumerate(DEFAULT_THEMES):
            if self.slots[i] is None:
                self.slots[i] = theme

    # ---- capture / apply ----

    def capture(self, name: str) -> dict:
        v, chain = self.view, self.audio.chain
        view = {
            f.name: getattr(v, f.name)
            for f in dataclasses.fields(v)
            if f.name not in VIEW_SKIP
        }
        view["planes"] = list(v.planes)
        view["pan"] = list(v.pan)
        return {
            "name": name,
            "scene": self.control.scene,
            "view": view,
            "bands": [dataclasses.asdict(p) for p in chain.params],
            "master": {"gain": chain.gain, "dyn": chain.dyn, "trim": chain.trim},
        }

    def save(self, k: int) -> None:
        if not 0 <= k < SLOTS:
            return
        old = self.slots[k]
        name = old["name"] if old else f"THEME {k + 1}"
        self.slots[k] = self.capture(name)
        self.active = k
        self._write()

    def load(self, k: int) -> None:
        if not 0 <= k < SLOTS or self.slots[k] is None:
            return
        t, v, chain = self.slots[k], self.view, self.audio.chain
        # missing view keys fall back to dataclass defaults, so a theme is
        # the same state no matter what it was loaded on top of
        stored = t.get("view", {})
        for f in dataclasses.fields(v):
            if f.name in VIEW_SKIP:
                continue
            if f.name in stored:
                val = stored[f.name]
            elif f.default is not dataclasses.MISSING:
                val = f.default
            else:
                val = f.default_factory()
            setattr(v, f.name, list(val) if isinstance(val, list) else val)
        self.control.clear_undo()
        self.control.scene = t.get("scene", 0)
        if "bands" in t:
            for i, d in enumerate(t["bands"][:6]):
                chain.params[i] = Params(**d)
                chain.st[i] = {}
        else:  # seeded themes carry a scene, not band values
            chain.apply_preset(self.control.scene)
        m = t.get("master")
        if m:
            chain.gain, chain.dyn, chain.trim = m["gain"], m["dyn"], m["trim"]
        self.active = k

    def cycle(self, step: int = 1) -> None:
        """Flip to the next saved slot — the gamepad's theme button."""
        filled = [k for k, s in enumerate(self.slots) if s is not None]
        if not filled:
            return
        if self.active in filled:
            k = filled[(filled.index(self.active) + step) % len(filled)]
        else:
            k = filled[0]
        self.load(k)

    # ---- persistence ----

    def _write(self) -> None:
        try:
            self.path.write_text(json.dumps({"version": 1, "slots": self.slots}, indent=1))
            self.error = ""
        except OSError as e:
            self.error = f"presets: {e}"

    def _read(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text())
            for i, slot in enumerate(data.get("slots", [])[:SLOTS]):
                self.slots[i] = slot
        except (OSError, ValueError) as e:
            self.error = f"presets: {e}"
