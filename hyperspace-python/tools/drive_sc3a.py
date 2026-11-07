"""tools/app_driver.py's script for SC3a: the real app, real looks, each held still
(clock and rotation pinned) for a capture of output 1's window, and the loop's frame
times over a stretch of each. Run on the build before and the build after, and compare:

    uv run python tools/app_driver.py tools/drive_sc3a.py --out <scratch>/run --every 3

`--every` large is a timing run: no capture to slow the loop. Loads go through
`panel.library.load("presets", name)`. `SC3A_LOOKS` names the looks (comma-separated);
the timing goes to `<cwd>/sc3a_times.json`, or `SC3A_TIMES`.
"""

import json
import os
import time

import numpy as np

from hyperspace import render
from hyperspace.view import ViewState

LOOKS = ("party-tumble", "party-acid", "party-faces", "party-trip", "woven-lattice",
         "spiral-silk", "hands-orbit", "strobe-cage")
FRAMES = int(os.environ.get("SC3A_FRAMES", "12"))
TIMED = int(os.environ.get("SC3A_TIMED", "300"))


def script(d, panel):
    looks = os.environ.get("SC3A_LOOKS", "")
    looks = looks.split(",") if looks else LOOKS
    # still: the same picture on any build, whenever the frame lands
    render.Renderer.now = lambda self, t=None: 12.5
    ViewState.integrate = lambda self, dt: None
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
    with open(os.environ.get("SC3A_TIMES", "sc3a_times.json"), "w") as f:
        json.dump(out, f, indent=1)
