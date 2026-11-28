"""A Wave look as a patch of primitives — the mapping the proof
(`tests/test_wave_patch.py`) and the field example use.

    point ─▶ <along>.field, <along>.2.field          (Centre X / Y)
    <along>   (Line, Rings or Spokes; a value)  ─▶ waveform ─▶ combine.field
    <along>.2 (the same; the push's way)        ─▶ combine.image
    combine (multiply) ─▶ displace.field;  the picture ─▶ displace.image

Wave's push is a way (the measure's direction: squeeze; a quarter turn on:
slide) scaled by the waveform's value, then Amount, then the split. The Point
is always wired: a measure with none counts from the middle by other
arithmetic (`centred`), an ulp apart from wave.glsl's `from_point`."""

from __future__ import annotations

ALONG = ("line", "rings", "spokes")      # Wave's Along → the measure's file


def nodes(v: dict) -> list[dict]:
    m = ALONG[v["along"]]
    return [{"kind": "effect", "file": "point"},
            {"kind": "effect", "file": m},
            {"kind": "effect", "file": m, "instance": 2},
            {"kind": "effect", "file": "waveform"},
            {"kind": "effect", "file": "combine"},
            {"kind": "effect", "file": "displace"}]


def wires(v: dict) -> list[dict]:
    m = ALONG[v["along"]]
    return [{"from": "point", "to": f"{m}.field"},
            {"from": "point", "to": f"{m}.2.field"},
            {"from": m, "to": "waveform.image"},
            {"from": f"{m}.2", "to": "combine.image"},
            {"from": "waveform", "to": "combine.field"},
            {"from": "combine", "to": "displace.field"}]


def wave_patch(v: dict) -> dict[str, dict]:
    """Wave's values (`fx.wave.<key>` without the prefix) → each node's."""
    m, on = ALONG[v["along"]], v.get("on", True)
    place = {"scale": 1.0, "on": on, **({"angle": v["angle"]} if m == "line" else {})}
    return {
        "point": {"x": v["cx"], "y": v["cy"], "on": on},
        m: {**place, "out": 0},
        f"{m}.2": {**place, "out": 1 if v["push"] == 1 else 2},   # squeeze: along; slide: across
        "waveform": {"waves": v["waves"], "shape": v["shape"], "round": 1 if v["along"] == 2 else 0,
                     "drift": v["drift"], "steps": v["steps"], "speed": v["speed"], "on": on},
        "combine": {"how": 1, "on": on},
        "displace": {"amount": v["amount"], "split": v["split"], "mix": v["mix"],
                     "blend": v["blend"], "on": on},
    }
