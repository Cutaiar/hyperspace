"""Synthetic Ultraleap hands: namespaces shaped like the ``leap`` bindings'.

An open hand or a fist, either side, anywhere in the box — every digit's
four bones with joints, widths and a rotation, the palm frame and the
arm. What `hands.core.features` and `hands.core.skeleton` read, so the
tests (and tools/hands_tape.py synth) can drive the ghost hands with no camera.
Desktop mode: palm down, fingers pointing away from the performer (−z).
"""

from __future__ import annotations

import math
from types import SimpleNamespace as NS

import numpy as np

# per finger: (lateral offset at the knuckle toward the thumb, mm; length scale)
FINGERS = {"index": (26.0, 0.95), "middle": (8.0, 1.0), "ring": (-10.0, 0.95),
           "pinky": (-27.0, 0.78)}
LENGTHS = (60.0, 42.0, 26.0, 20.0)        # metacarpal, proximal, intermediate, distal
WIDTHS = (19.0, 18.0, 16.5, 15.0)
OPEN = (0.0, 4.0, 4.0, 4.0)               # degrees each bone bends past the last
FIST = (0.0, 85.0, 95.0, 55.0)


def v3(p) -> NS:
    return NS(x=float(p[0]), y=float(p[1]), z=float(p[2]))


def _bone(a, b, w) -> NS:
    return NS(prev_joint=v3(a), next_joint=v3(b), width=w, rotation=NS(x=0.0, y=0.0, z=0.0, w=1.0))


def hand(side: str = "right", grip: str = "open", at=(0.0, 200.0, 0.0), conf: float = 1.0,
         spread: float = 1.0) -> NS:
    """A hand namespace. `grip` "open" or "fist"; `at` the palm in mm."""
    palm = np.asarray(at, dtype=float)
    f = np.array([0.0, 0.0, -1.0])                          # fingers forward
    n = np.array([0.0, -1.0, 0.0])                          # palm down
    s = np.array([-1.0 if side == "right" else 1.0, 0.0, 0.0])   # toward the thumb
    bends = FIST if grip == "fist" else OPEN
    digits = {}
    for name, (lat, scale) in FINGERS.items():
        base = palm - f * 38.0 + s * lat * 0.45
        knuckle = palm + f * 40.0 + s * lat * spread
        joints = [base, knuckle]
        theta = 0.0
        for k in (1, 2, 3):
            theta += math.radians(bends[k])
            d = math.cos(theta) * f + math.sin(theta) * n
            joints.append(joints[-1] + d * LENGTHS[k] * scale)
        digits[name] = joints
    # the thumb: no metacarpal length, out from the palm's thumb side
    tb = palm - f * 20.0 + s * 32.0
    out = s * 0.5 + f * 0.85
    out /= np.linalg.norm(out)
    if grip == "fist":
        across = -s * 0.6 + f * 0.5 + n * 0.6
        across /= np.linalg.norm(across)
        tj = [tb, tb, tb + out * 38.0, tb + out * 38.0 + across * 28.0,
              tb + out * 38.0 + across * 50.0]
    else:
        tj = [tb, tb, tb + out * 38.0, tb + out * 64.0, tb + out * 84.0]
    digits = {"thumb": tj, **digits}
    ns = NS(type=NS(name=side.capitalize()), confidence=conf,
            grab_strength=1.0 if grip == "fist" else 0.0, pinch_strength=0.0,
            grab_angle=math.pi if grip == "fist" else 0.0, pinch_distance=60.0,
            palm=NS(position=v3(palm), normal=v3(n), direction=v3(f), width=85.0),
            arm=_bone(palm - f * 260.0, palm - f * 45.0, 60.0))
    for name, j in digits.items():
        bones = [_bone(j[k], j[k + 1], WIDTHS[k]) for k in range(4)]
        setattr(ns, name, NS(metacarpal=bones[0], proximal=bones[1], intermediate=bones[2],
                             distal=bones[3], bones=bones))
    return ns
