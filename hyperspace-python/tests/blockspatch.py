"""Plan 67: a Blocks look as a patch of primitives — the mapping the proof
(`tests/test_blocks_patch.py`) and the field example use, and the one the
format lane's migration will use when `blocks.glsl` retires.

    measure   (cells, a value: the cell's number, its size riding along)
        ─▶ waveform (Shape, Drift, Phase ¼) ─▶ cell action.image
    measure.2 (cells, direction: the pixel's place in its cell) ─▶ cell action.field
    cell action (Action, Amount, Angle) ─▶ displace.field (Amount 0.5, Split)

Cell action's push is in half frame heights, so Displace at its top Amount
(0.5) pushes by it exactly.

Blocks' Cell is in pixels and a Measure counts cells to a frame height, so the
mapping takes the height of the frame it draws: the patch is Blocks at that
size (at another, Blocks keeps its pixels and the patch its share of the frame)."""

from __future__ import annotations

import math

NODES = [{"kind": "effect", "file": "measure"},
         {"kind": "effect", "file": "measure", "instance": 2},
         {"kind": "effect", "file": "waveform"},
         {"kind": "effect", "file": "cellaction"},
         {"kind": "effect", "file": "displace"}]
WIRES = [{"from": "measure", "to": "waveform.image"},
         {"from": "waveform", "to": "cellaction.image"},
         {"from": "measure.2", "to": "cellaction.field"},
         {"from": "cellaction", "to": "displace.field"}]


def pairs(v: dict) -> int:
    """Swap pairs blocks across (1) or up (2), whichever its Angle is nearer;
    every other action numbers every block alone (0)."""
    if v["action"] != 5:
        return 0
    return 1 if abs(math.cos(v["angle"])) >= abs(math.sin(v["angle"])) else 2


def blocks_patch(v: dict, height: int) -> dict[str, dict]:
    """Blocks' values (`fx.blocks.<key>` without the prefix), drawn `height`
    pixels high → each node's."""
    on = v.get("on", True)
    grid = {"along": 3, "scale": height / v["cell"], "aspect": v["aspect"], "group": v["group"],
            "rule": v["rule"], "spread": v["spread"], "pairs": pairs(v), "cx": 0.0, "cy": 0.0,
            "on": on}
    return {
        "measure": {**grid, "out": 0},
        "measure.2": {**grid, "out": 1},
        # a quarter cycle on: at rest a sine sits on its crest (blocks.glsl)
        "waveform": {"waves": 1.0, "shape": v["shape"], "round": 0, "drift": v["drift"],
                     "start": 0.25, "steps": 0, "speed": v["speed"], "on": on},
        "cellaction": {"action": v["action"], "amount": v["amount"], "angle": v["angle"], "on": on},
        "displace": {"amount": 0.5, "split": v["split"], "mix": v["mix"], "blend": v["blend"],
                     "on": on},
    }


def on_edges(v: dict, width: int, height: int):
    """The pixels of a `width` × `height` frame whose centre lies exactly on a
    cell's edge in Blocks `v`'s grid: there the file (counting in pixels) and
    the patch (counting in frame heights) may round to either cell."""
    import numpy as np

    def ties(n, cs):
        q = ((np.arange(n) + 0.5) / n - 0.5) * n / cs + 0.5
        return np.abs(q - np.round(q)) < 1e-4

    return (ties(height, v["cell"])[:, None]
            | ties(width, v["cell"] * v["aspect"])[None, :])
