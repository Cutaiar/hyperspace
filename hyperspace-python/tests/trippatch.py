"""A Trip warp look as a patch of primitives — the mapping the
comparison (`tests/test_trip_patch.py`) and the field example use.

    noise (Out flow: two drifting octaves)  ─▶ combine (multiply) ─▶ scale (× 0.4 Amount) ─┐
    rings (the distance from the middle)    ─▶ combine.field                               │
    point ─▶ scale.2 (× the zoom)  ─────────────────────────────▶ combine.2 (add) ◀────────┘
    combine.2 ─▶ displace.field (Amount 0.5);  the picture ─▶ displace.image

Near, not equal: warp.glsl
counts in fractions of the frame's width and height, the field nodes in frame
heights, so the patch's edge weight is round where the file's is an ellipse
fitted to the frame, and its swim is as long across as up where the file's is
stretched across the width. The zoom is the file's exactly. Displace sits at its
top Amount (0.5) and the two Scales are doubled, as Cell action's push is."""

from __future__ import annotations

NODES = [{"kind": "effect", "file": "point"},
         {"kind": "effect", "file": "noise"},
         {"kind": "effect", "file": "rings"},
         {"kind": "effect", "file": "combine"},
         {"kind": "effect", "file": "scale"},
         {"kind": "effect", "file": "scale", "instance": 2},
         {"kind": "effect", "file": "combine", "instance": 2},
         {"kind": "effect", "file": "displace"}]
WIRES = [{"from": "noise", "to": "combine.image"},
         {"from": "rings", "to": "combine.field"},
         {"from": "combine", "to": "scale.image"},
         {"from": "point", "to": "scale.2.image"},
         {"from": "scale", "to": "combine.2.image"},
         {"from": "scale.2", "to": "combine.2.field"},
         {"from": "combine.2", "to": "displace.field"}]
INSTANCES = {"scale": 2, "combine": 2}


def trip_patch(v: dict) -> dict[str, dict]:
    """Trip warp's values (`fx.warp.<key>` without the prefix) → each node's.
    The file reads `w + flow × 0.2 × r × Amount`, `w` the frame zoomed in by
    up to 10 % (`1 − 0.1 × min(1, 1.5 Amount)`): the flow's gain is 0.2 Amount
    and the zoom's `−0.1 min(1, 1.5 Amount)`, each doubled for Displace's 0.5."""
    on, a = v.get("on", True), v["amount"]
    return {
        "point": {"x": 0.0, "y": 0.0, "on": on},
        "noise": {"out": 1, "scale": v["scale"], "drift": v["drift"], "speed": v["speed"], "on": on},
        "rings": {"out": 0, "scale": 1.0, "on": on},
        "combine": {"how": 1, "on": on},
        "scale": {"mul": 2.0 * 0.2 * a, "offset": 0.0, "on": on},
        "scale.2": {"mul": 2.0 * -0.1 * min(1.0, a * 1.5), "offset": 0.0, "on": on},
        "combine.2": {"how": 0, "on": on},
        "displace": {"amount": 0.5, "split": 0.0, "mix": v["mix"], "blend": v["blend"], "on": on},
    }
