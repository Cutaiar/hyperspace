"""tools/app_driver.py's script for SC3a: the real app, real looks, each on a pinned clock
and a fixed rotation step for a capture of output 1's window, and the loop's frame
times over a stretch of each. Run on the build before and the build after, and compare:

    uv run python tools/app_driver.py tools/drive_sc3a.py --out <scratch>/run --every 3

`--every` large is a timing run: no capture to slow the loop. Loads go through
`panel.library.load("presets", name)`. `SC3A_LOOKS` names the looks (comma-separated);
the timing goes to `<cwd>/sc3a_times.json`, or `SC3A_TIMES`. `SC3A_RGBA=<dir>`: every 40th
swap of output 1's window, its back buffer with alpha as `.npy`, and the window's
see-through flags in the times file, for an overlay run (a `--home` whose config says
`[output] overlay = true`, `on_start = true`).
"""

import json
import os
import time

import glfw
import numpy as np
from OpenGL import GL

from hyperspace import render
from hyperspace.view import ViewState

LOOKS = ("party-tumble", "party-acid", "party-faces", "party-trip", "woven-lattice",
         "spiral-silk", "hands-orbit", "strobe-cage")
FRAMES = int(os.environ.get("SC3A_FRAMES", "12"))
TIMED = int(os.environ.get("SC3A_TIMED", "300"))

# the same picture at the same frame on any build: at import, before the app's first
# frame, so no frame's wall clock has moved anything yet
_integrate = ViewState.integrate
render.Renderer.now = lambda self, t=None: 12.5
ViewState.integrate = lambda self, dt: _integrate(self, 1.0 / 120.0)

RGBA = os.environ.get("SC3A_RGBA", "")
_swap = glfw.swap_buffers
_swaps = [0]


def _swap_reading(win):
    if glfw.get_window_title(win) == "Hyperspace":
        _swaps[0] += 1
        if _swaps[0] % 40 == 0:
            w, h = glfw.get_framebuffer_size(win)
            GL.glReadBuffer(GL.GL_BACK)
            raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
            np.save(f"{RGBA}/{_swaps[0]:05d}.npy", np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 4))
    _swap(win)


if RGBA:
    os.makedirs(RGBA, exist_ok=True)
    glfw.swap_buffers = _swap_reading


def _see_through(win) -> dict:
    import objc

    ns = objc.objc_object(c_void_p=glfw.get_cocoa_window(win))
    return {"isOpaque": bool(ns.isOpaque()), "level": int(ns.level()),
            "ignoresMouse": bool(ns.ignoresMouseEvents()), "alphaValue": float(ns.alphaValue()),
            "frame_buffer": list(glfw.get_framebuffer_size(win))}


def script(d, panel):
    looks = os.environ.get("SC3A_LOOKS", "")
    looks = looks.split(",") if looks else LOOKS
    out = {}
    for name in looks:
        panel.library.load("presets", name)
        yield from d.wait(FRAMES)
        times = []
        last = time.perf_counter()
        for _ in range(TIMED):
            yield
            now = time.perf_counter()
            times.append((now - last) * 1000.0)
            last = now
        t = np.array(times[10:] or times)
        out[name] = {"fps": round(1000.0 / float(t.mean()), 1), "p50": round(float(np.median(t)), 3),
                     "p99": round(float(np.percentile(t, 99)), 3), "max": round(float(t.max()), 3),
                     "sd": round(float(t.std()), 3)}
    out["load"] = os.getloadavg()[0]
    if RGBA:
        out["window"] = _see_through(panel.outputs[0].win)
    with open(os.environ.get("SC3A_TIMES", "sc3a_times.json"), "w") as f:
        json.dump(out, f, indent=1)
