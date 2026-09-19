#!/usr/bin/env python3
"""Screenshots of the control window, one per page of the panel (WP5a).

Runs the real app in-process for a few frames per page, cycling
``ui.page``, and reads the control window's framebuffer back after each
imgui render — so what lands in docs/plans/assets/07-shell/ is exactly
what the window shows. A panel exception is re-raised (the app's loop
would otherwise swallow it into the hot-reload toast).

  HYPERSPACE_HOME=$(mktemp -d) uv run python tools/control_shots.py [--mod | --bands]

--mod holds a lane on a few params so the ghost markers show.
--bands (WP5b) feeds the analyser a synthetic signal — a kick, a
sweeping tone, hat bursts — with the audio engine switched on, so the
spectrogram fills and the legacy routes run live; adds a lane → band
route so the editor's ghost and the matrix's live bars show; and shoots
the analyzer page (as analyzer-editor.png) and the routing page after
the history ring has filled.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

import glfw
import numpy as np
from OpenGL import GL
from PIL import Image

from hyperspace import app, ui
from hyperspace.routing import Binding
from hyperspace.ui import PAGE_KEYS, PAGES

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "07-shell"
SETTLE = 12          # frames on a page before the shot (imgui needs a frame or two)
MOD = "--mod" in sys.argv
BANDS = "--bands" in sys.argv
MODULATED = {"view.bright": 0.18, "view.faces": 1.0, "camera.zoom": 0.12,
             "master.gain": -0.15, "band.0.atk": 0.2, "pattern.mod.0": 0.3}

state = {"frame": 0, "panel": None, "shot": None, "router": None, "t": 0.0}
if BANDS:
    # the ring holds 4 s of frame time: settle long enough to fill it
    SETTLE = 600
    schedule = [(PAGE_KEYS.index("analyzer"), "analyzer-editor"),
                (PAGE_KEYS.index("routing"), "routing")]
else:
    schedule = [(k, key) for k, (key, _, _) in enumerate(PAGES)]

_draw = ui.Panel.draw


def synth(t0: float, n: int, sr: float) -> np.ndarray:
    """A bar of fake music: kick every half second, a tone sweeping
    200 Hz → 2 kHz over four seconds, hats on the off-beats, a noise floor."""
    t = t0 + np.arange(n) / sr
    beat = t % 0.5
    kick = np.sin(2 * np.pi * (55 + 40 * np.exp(-beat * 20)) * beat) * np.exp(-beat * 9)
    sweep = np.sin(2 * np.pi * 200 * 10 ** ((t % 4.0) / 4.0) * t) * 0.35
    hat = np.random.default_rng(int(t0 * 1000)).standard_normal(n) * 0.25
    hat *= np.exp(-((t + 0.25) % 0.5) * 30)
    floor = np.random.default_rng(int(t0 * 7919)).standard_normal(n) * 0.004
    return (kick + sweep + hat + floor).astype(np.float64)


def draw(self, dt, fps):
    state["panel"] = self
    n = state["frame"]
    k = min(n // SETTLE, len(schedule) - 1)
    self.reg["ui.page"].set(schedule[k][0])
    if MOD:
        for pid, u in MODULATED.items():
            self.reg[pid].modulate(u)
        self.reg.apply()
    if BANDS:
        a = self.audio
        if not a.on:
            a.on = True                       # no stream: step() just runs the chain
            a.chain.warm = 0
            r = state["router"]
            if r is not None:
                r.table.add(Binding("lane:1", "band.0.f", "mod", 0.25))
                self.router = r
        a.analyser.feed(synth(state["t"], int(a.sr / 60) + 64, a.sr))
        state["t"] += 1 / 60
    try:
        _draw(self, dt, fps)
    except Exception:  # noqa: BLE001 — surface it, the loop would swallow it
        traceback.print_exc()
        raise SystemExit(1)
    state["shot"] = schedule[k][1] if n % SETTLE == SETTLE - 1 else None
    state["frame"] = n + 1


class ShotRenderer(app.GlfwRenderer):
    def render(self, draw_data):
        super().render(draw_data)
        name = state["shot"]
        if name is None:
            return
        w, h = glfw.get_framebuffer_size(self.window)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"{name}{'-mod' if MOD else ''}.png"
        Image.fromarray(px).save(path, optimize=True)
        print(f"wrote {path}")


class ShotRouter(app.Router):
    """The app's router, caught on construction so --bands can reach it."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        state["router"] = self


if __name__ == "__main__":
    ui.Panel.draw = draw
    app.GlfwRenderer = ShotRenderer
    app.Router = ShotRouter
    import os

    os.environ["HYPERSPACE_FRAMES"] = str(SETTLE * len(schedule) + 2)
    app.main()
