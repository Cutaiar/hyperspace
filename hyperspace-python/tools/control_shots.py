#!/usr/bin/env python3
"""Screenshots of the control window, one per page of the panel (WP5a).

Runs the real app in-process for a few frames per page, cycling
``ui.page``, and reads the control window's framebuffer back after each
imgui render — so what lands in docs/plans/assets/07-shell/ is exactly
what the window shows. A panel exception is re-raised (the app's loop
would otherwise swallow it into the hot-reload toast).

  HYPERSPACE_HOME=$(mktemp -d) uv run python tools/control_shots.py [--mod]

--mod holds a lane on a few params so the ghost markers show.
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
from hyperspace.ui import PAGES

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "07-shell"
SETTLE = 12          # frames on a page before the shot (imgui needs a frame or two)
MOD = "--mod" in sys.argv
MODULATED = {"view.bright": 0.18, "view.faces": 1.0, "camera.zoom": 0.12,
             "master.gain": -0.15, "band.0.atk": 0.2, "pattern.mod.0": 0.3}

state = {"frame": 0, "panel": None, "shot": None}
schedule = [(k, key) for k, (key, _, _) in enumerate(PAGES)]

_draw = ui.Panel.draw


def draw(self, dt, fps):
    state["panel"] = self
    n = state["frame"]
    k = min(n // SETTLE, len(schedule) - 1)
    self.reg["ui.page"].set(schedule[k][0])
    if MOD:
        for pid, u in MODULATED.items():
            self.reg[pid].modulate(u)
        self.reg.apply()
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


if __name__ == "__main__":
    ui.Panel.draw = draw
    app.GlfwRenderer = ShotRenderer
    import os

    os.environ["HYPERSPACE_FRAMES"] = str(SETTLE * len(schedule) + 2)
    app.main()
