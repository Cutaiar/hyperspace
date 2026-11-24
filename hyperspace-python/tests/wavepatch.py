"""Plan 67: a Wave look as a patch of primitives — the mapping the proof
(`tests/test_wave_patch.py`) and the field example use, and the one the format
lane's migration will use when `wave.glsl` retires.

    measure   (Along, a value)      ─▶ waveform (Waves, Shape, Drift, Steps) ─┐
    measure.2 (Along, the push way) ─▶ combine.image        combine.field ◀───┘
    combine (multiply) ─▶ displace.field;  the picture ─▶ displace.image

Wave's push is a way (the measure's direction: squeeze; a quarter turn on:
slide) scaled by the waveform's value, then Amount, then the split."""

from __future__ import annotations

NODES = [{"kind": "effect", "file": "measure"},
         {"kind": "effect", "file": "measure", "instance": 2},
         {"kind": "effect", "file": "waveform"},
         {"kind": "effect", "file": "combine"},
         {"kind": "effect", "file": "displace"}]
WIRES = [{"from": "measure", "to": "waveform.image"},
         {"from": "measure.2", "to": "combine.image"},
         {"from": "waveform", "to": "combine.field"},
         {"from": "combine", "to": "displace.field"}]


def wave_patch(v: dict) -> dict[str, dict]:
    """Wave's values (`fx.wave.<key>` without the prefix) → each node's."""
    place = {"along": v["along"], "angle": v["angle"], "cx": v["cx"], "cy": v["cy"],
             "scale": 1.0, "on": v.get("on", True)}
    return {
        "measure": {**place, "out": 0},
        "measure.2": {**place, "out": 1 if v["push"] == 1 else 2},   # squeeze: along; slide: across
        "waveform": {"waves": v["waves"], "shape": v["shape"], "round": 1 if v["along"] == 2 else 0,
                     "drift": v["drift"], "steps": v["steps"], "speed": v["speed"],
                     "on": v.get("on", True)},
        "combine": {"how": 1, "on": v.get("on", True)},
        "displace": {"amount": v["amount"], "split": v["split"], "mix": v["mix"],
                     "blend": v["blend"], "on": v.get("on", True)},
    }
