"""tools/app_driver.py script: zooming into the Sierpinski tetrahedron
forever (fractal.py) — in for sixteen levels at the stick's rate, a pan
across it deep inside, then all the way out to the whole shape. Each
frame's `camera.zoom` and depth go to `$FRACTAL_LOG` (a JSON list), for a
readout under the video. With `$FRACTAL_TOUR` (shape names, comma-separated)
it visits those instead, each in and out again.

    uv run python tools/app_driver.py tools/drive_fractal.py --out /tmp/fractal --every 1
"""

import json
import os

from hyperspace.geometry import shape_index

IN = 2.0 ** (1 / 22)        # a level every 22 frames


def script(d, panel):
    reg, view = panel.reg, panel.view
    log = []

    def frames(n, zoom=1.0, pan=(0.0, 0.0), say=""):
        for _ in range(n):
            if zoom != 1.0:
                reg["camera.zoom"].scale(zoom)
            if pan[0]:
                reg["camera.pan.x"].nudge(pan[0])
            if pan[1]:
                reg["camera.pan.y"].nudge(pan[1])
            log.append({"zoom": float(view.zoom), "depth": len(view.dive.path), "say": say})
            yield

    tour = os.environ.get("FRACTAL_TOUR")
    if tour:
        # the others, one after another: in, and out again
        for name in tour.split(","):
            reg["view.shape"].set(shape_index(name))
            reg["camera.reset"].fire()
            reg["camera.zoom"].set_value(1.3)
            reg["camera.yaw"].set_value(0.45)
            reg["camera.pitch"].set_value(0.3)
            yield from d.wait(4)
            n = int(os.environ.get("FRACTAL_LEVELS", "11"))
            yield from frames(40, say=name)
            yield from frames(22 * n, zoom=IN, say=f"{name}: zooming in")
            yield from frames(int(os.environ.get("FRACTAL_HOLD", "30")), say=f"{name}: turning, deep inside")
            yield from frames(22 * n, zoom=1 / IN, say=f"{name}: zooming out")
            yield from frames(40, say=f"{name}: out")
        _save(log)
        return
    reg["view.shape"].set(shape_index("Sierpinski tetrahedron"))
    reg["camera.zoom"].set_value(0.9)
    reg["camera.yaw"].set_value(0.45)
    reg["camera.pitch"].set_value(0.3)
    reg["camera.pan.x"].set_value(0.0)
    reg["camera.pan.y"].set_value(0.0)
    yield from d.wait(10)
    log.clear()
    yield from frames(60, say="the whole shape")
    yield from frames(22 * 16, zoom=IN, say="zooming in: the stick held")
    yield from frames(45, say="sixteen levels in")
    yield from frames(120, pan=(0.035, 0.012), say="a pan, deep inside")
    yield from frames(22 * 6, zoom=IN, say="and in again")
    yield from frames(22 * 22, zoom=1 / IN, say="zooming out")
    yield from frames(70, say="out: the whole shape, centred")
    _save(log)


def _save(log) -> None:
    if os.environ.get("FRACTAL_LOG"):
        with open(os.environ["FRACTAL_LOG"], "w") as f:
            json.dump(log, f)
