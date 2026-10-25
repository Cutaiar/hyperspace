#!/usr/bin/env python3
"""The Flow mark's demo: the vector subject, flat and as capsules, drawn
offscreen by the real renderer.

  uv run python tools/flow_demo.py

Writes `docs/plans/assets/28-catalog/flow-demo.mp4` (1280×720, 30 fps,
through ffmpeg on the PATH; not committed, run it to see it). Dillon's,
from PR #214, unchanged but for this line. Each segment is a ViewState turned by
`ViewState.integrate`, as the app turns it; the stage, the captions and
the encoder are catalog_demo's.
"""

from __future__ import annotations

import math
import shutil
import subprocess

from catalog_demo import FPS, OUT, H, Segment, Stage, W, caption

from hyperspace import geometry as G
from hyperspace.patterns import NAMES as PATTERN_NAMES
from hyperspace.view import ViewState

MARK, CAPS = G.shape_index("Flow mark"), G.shape_index("Flow capsules")
# what the patterns segment walks through, a second and a half each
WALK = ["PLAID", "RINGS", "MOIRE", "BLOOM", "CAUSTIC", "PLASMA", "KALEIDO", "METER"]
STILL = [False] * 6


def walk_patterns(v, u):
    v.pattern = PATTERN_NAMES.index(WALK[min(int(u * len(WALK)), len(WALK) - 1)])


def walk_caption(u: float) -> tuple[str, str]:
    name = WALK[min(int(u * len(WALK)), len(WALK) - 1)]
    sub = (f"pattern {name} · the mark's face UVs are its own plane: one picture "
           "through the five bars")
    return ("Face patterns through the mark", sub)


def sway(amp: float, rate: float):
    """Turn the camera back and forth, the shape's own angles left alone."""
    def each(v, u):
        v.yaw = amp * math.sin(2 * math.pi * rate * u)
    return each


def segments() -> list[Segment]:
    return [
        Segment("Flow mark", "vector · five stadia read off wisprflow.ai's SVG, "
                "drawn as the mark is drawn", 4.0,
                {"shape": MARK, "bright": 1.3, "speed": 0.0}, planes=STILL),
        Segment("Flow mark · turning", "a plane figure: its depth cue spans the unit "
                "sphere, so face-on it is at full weight and a tilt dims its far side", 7.0,
                {"shape": MARK, "bright": 1.3, "speed": 0.25},
                each=sway(0.95, 1.0), planes=[True, False, False, False, False, False]),
        Segment("", "", 12.0,
                {"shape": MARK, "faces": True, "bright": 1.7, "speed": 0.0},
                each=walk_patterns, caption=walk_caption, planes=STILL),
        Segment("Flow capsules", "each bar lifted into a capsule round its own axis", 7.0,
                {"shape": CAPS, "bright": 1.3, "speed": 0.0},
                each=sway(0.9, 1.0), planes=STILL),
        Segment("Flow capsules · tumbling", "faces on, pattern BLOOM wrapped round each "
                "bar: u round it, v along it", 8.0,
                {"shape": CAPS, "faces": True, "bright": 1.6, "speed": 0.5,
                 "pattern": PATTERN_NAMES.index("BLOOM")},
                planes=[False, True, True, False, False, False]),   # a 3D shape: 3D planes
        Segment("A field of marks", "nine instances on a grid, RIPPLE: the app's "
                "instancing, on the new subject", 7.0,
                {"shape": MARK, "bright": 1.2, "speed": 0.0, "instances": 9,
                 "inst_motion": 3, "inst_amp": 0.3, "zoom": 0.45},
                each=sway(0.7, 1.0), planes=STILL),
    ]


def run() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is not on the PATH")
    stage = Stage()
    segs = segments()
    out = OUT / "flow-demo.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset",
         "slow", "-crf", "27", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         str(out)], stdin=subprocess.PIPE)
    t = 0.0
    for k, seg in enumerate(segs, 1):
        v = ViewState(**seg.view)
        v.planes = list(seg.planes)
        v.ang = [0.0] * 6
        frames = int(seg.seconds * FPS)
        for f in range(frames):
            u = f / max(frames - 1, 1)
            if seg.each is not None:
                seg.each(v, u)
            im = stage.shot(v, t)
            title, sub = seg.caption(u) if seg.caption else (seg.title, seg.sub)
            ff.stdin.write(caption(im, title, sub, k, len(segs)).tobytes())
            v.integrate(1 / FPS)
            t += 1 / FPS
        print(f"{k:2d}/{len(segs)} {seg.title or 'patterns'}")
    ff.stdin.close()
    ff.wait()
    print("wrote", out)


if __name__ == "__main__":
    run()
