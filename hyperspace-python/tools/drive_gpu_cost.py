"""tools/app_driver.py script (plan 84): GRAPH's **gpu cost** chip in the real
app — the party show on GRAPH, the chip clicked, every render node marked by
its GPU time (its border and ground up a black-to-white ramp, a badge above
it), the head's line with the frame's total and its three costliest, and an
effect switched off saying it made nothing.

    uv run python tools/app_driver.py tools/drive_gpu_cost.py --out /tmp/cost

The frames worth a look are named in ``<out>/marks.json`` when
``GPU_COST_MARKS`` names a file (app_driver's frame numbers). Under Xvfb the
times are Mesa's software rasteriser's: the marks are right, the numbers say
nothing about the rig.
"""

import json
import os

from hyperspace import graphview, ui_graph

MARKS: dict[str, int] = {}


def _mark(name: str) -> None:
    MARKS[name] = _mark.n
    path = os.environ.get("GPU_COST_MARKS")
    if path:
        with open(path, "w") as f:
            json.dump(MARKS, f)


_mark.n = 0


def _wait(k):
    for _ in range(k):
        _mark.n += 1
        yield


def script(d, panel):
    st = ui_graph._state(panel)
    _mark.n = 20                         # app_driver's settle: the frame the script starts on
    panel.reg["fx.on"].set(True)         # (the party show bypasses every effect)
    yield from d.park()
    yield from _wait(30)
    _mark("off")
    yield from d.click(ui_graph.COST_LABEL)
    _mark.n += 3
    yield from d.park()
    _mark.n += 1
    yield from _wait(90)                 # the medians read back, the marks eased in
    assert st["cost"], "the chip did not light"
    _mark("lit")
    # two effects: Bloom put on the scene's cable to All outputs (it runs, and
    # takes its share), Kaleidoscope added on no wire (unbuilt: made nothing)
    view = st["view"]
    pics = [c for c in view.cables if c.type == graphview.IMAGE]
    cable = next(c for c in pics if c.src_port == "rout:scene")
    at = ui_graph.in_view(panel)
    ui_graph.insert_effect(panel, cable, "bloom", (at[0] + 2490.0, at[1] + 545.0))
    ui_graph.add_render(panel, ui_graph.render_edit(panel), "effect", "kaleido",
                        (at[0] + 2490.0, at[1] + 885.0))
    yield from _wait(120)
    _mark("effects")
    # Bloom switched off: it made nothing from the next frame
    panel.reg["fx.bloom.on"].set(False)
    yield from _wait(40)
    _mark("bloom-off")
