#!/usr/bin/env python3
"""Run the real app with a scripted mouse and keyboard, and capture its
windows — for a demo video or a look at a change working end to end.

    uv run python tools/app_driver.py tools/drive_instances.py --out /tmp/run

A script is a Python file with ``script(d, panel)``: a generator of
`tests/ui_driver.Driver` actions, one ``yield`` a frame, finding controls by
param id (``yield from d.click("view.inst_fit")``). The app's own loop steps
it once a frame after the panel draws; when it ends, the app closes.

Each window's frames land in ``OUT/<window>/NNNNN.png`` every ``--every``
frames (the control window and the render window, as the app swapped
them), and ``OUT/frames.json`` lists them with the mouse per frame, for a
cursor overlay — imgui draws none of its own.

A known start: a fresh home (``--home`` to keep one) seeded with the test
corpus as the tests' homes are (`conftest.seed`: the corpus loadable patches and
the party show, opened at launch — an empty home opens an unwired loadable patch
and a black output), a config with no devices and no dream, the mouse
parked. ``--empty`` skips the corpus. The panel opens where a fresh home
opens it (GRAPH, nothing focused): a script focuses the section it wants
first — ``panel.reg["ui.page"].set(PAGE_KEYS.index("view"))``, a frame or two
before it looks for a control, or ``d.click("pane.view")`` on the header —
and loads a loadable patch with ``panel.loaded_patch.load(name)`` if it wants another.

Off the Mac, run it under the virtual display (the cloud session's
DISPLAY=:99, or ``xvfb-run -a``). The software rasteriser draws what the
Mac draws, slower: the app's FPS readout here says nothing about the rig.
"""

from __future__ import annotations

import argparse
import ctypes
import importlib.util
import json
import os
import sys
import tempfile
import traceback
from pathlib import Path

import glfw
import numpy as np
from OpenGL import GL
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))      # ui_driver lives beside the tests that use it

from conftest import seed
from ui_driver import Driver

from hyperspace import app, ui

# no [[devices]] entry at all: no desk, pad, hands or bridge is opened
CONFIG = """[[devices]]
role = "none"
kind = "midi"
enabled = false

[dream]
enabled = false
"""


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.script


def run(script, out: Path, every: int = 2, home: Path | None = None, settle: int = 20,
        corpus: bool = True) -> None:
    out.mkdir(parents=True, exist_ok=True)
    fresh = home is None
    home = home or Path(tempfile.mkdtemp(prefix="hyperspace-drive-"))
    home.mkdir(parents=True, exist_ok=True)
    if fresh and corpus:
        seed(home)
    cfg = home / "config.toml"
    if not cfg.exists():
        cfg.write_text(CONFIG)
    os.environ["HYPERSPACE_HOME"] = str(home)
    os.environ.setdefault("HYPERSPACE_FRAMES", "100000")

    d = Driver()
    d.record()
    st = {"n": 0, "action": None, "done": False, "windows": {}}   # address → window
    shots: list[dict] = []
    draw = ui.Panel.draw

    def step(panel):
        st["n"] += 1
        if st["done"]:
            return
        if st["action"] is None and st["n"] >= settle:
            st["action"] = script(d, panel)
        if st["action"] is not None:
            try:
                next(st["action"])
            except StopIteration:
                st["done"] = True
                for w in st["windows"].values():
                    glfw.set_window_should_close(w, True)
            except Exception:  # noqa: BLE001 — the loop would swallow it into a toast
                traceback.print_exc()
                os._exit(1)

    def stepped(panel, dt, fps):
        # the class's draw as it is now, so a hot reload's new `Panel` is what runs; a draw
        # that raises still steps, or a script waiting to report that error never would
        try:
            type(panel).draw(panel, dt, fps)
        finally:
            step(panel)

    def first_draw(self, dt, fps):
        # from here on the wrapper is the panel's own, which a re-class leaves in place
        ui.Panel.draw = draw
        self.draw = lambda dt, fps: stepped(self, dt, fps)
        stepped(self, dt, fps)

    swap, destroy = glfw.swap_buffers, glfw.destroy_window

    def destroyed(window):
        st["windows"].pop(ctypes.addressof(window.contents), None)    # (a display went: SC3b)
        destroy(window)

    def captured(window):
        st["windows"][ctypes.addressof(window.contents)] = window
        n = st["n"]
        if st["action"] is not None and not st["done"] and n % every == 0:
            name = (glfw.get_window_title(window) or "window").split("—")[-1].strip()
            name = "".join(c if c.isalnum() else "-" for c in name.lower()) or "window"
            w, h = glfw.get_framebuffer_size(window)
            if w > 0 and h > 0:
                GL.glReadBuffer(GL.GL_BACK)
                raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
                px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
                path = out / name / f"{n:05d}.png"
                path.parent.mkdir(exist_ok=True)
                Image.fromarray(px).save(path, compress_level=1)
                shots.append({"frame": n, "window": name, "png": str(path.relative_to(out)),
                              "mouse": list(d.mouse)})
        swap(window)

    ui.Panel.draw = first_draw
    glfw.swap_buffers = captured
    glfw.destroy_window = destroyed
    sys.argv = sys.argv[:1]         # app.main parses its own flags: these were this tool's
    try:
        app.main()
    finally:
        glfw.swap_buffers = swap
        glfw.destroy_window = destroy
        if ui.Panel.draw is first_draw:     # the app never drew
            ui.Panel.draw = draw
        (out / "frames.json").write_text(json.dumps(shots, indent=0))
    print(f"{len(shots)} frames in {out}; home {home}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("script", type=Path, help="a file defining script(d, panel)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--every", type=int, default=2, help="capture every Nth frame (default 2)")
    ap.add_argument("--home", type=Path, help="a home to use (default: a fresh temp folder)")
    ap.add_argument("--empty", action="store_true", help="a fresh home without the corpus")
    a = ap.parse_args()
    run(_load(a.script), a.out, every=a.every, home=a.home, corpus=not a.empty)


if __name__ == "__main__":
    main()
