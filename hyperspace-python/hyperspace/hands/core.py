"""Ultraleap hands — two tracked hands as twelve axes and eight switches,
and the dance sources beside them.

The hands are the performing surface; the APC40 stays on presets and
master controls. Each hand gives the palm's rigid-body pose — six axes by
default — and every axis is an analog signal (signal.py): calibrated,
smoothed, shaped (dead zone, curve), enveloped (attack, decay), sprung
back to a rest value when the hand leaves, and glided back onto the hand
when it returns. The output y ∈ [0, 1] goes two ways:

  * inside Hyperspace, as ``hand:<name>`` sources in the routing table
    (routing.py) at float precision — ``hand:right.roll``,
    ``hand:left.present``, ``hand:left.pinch.index`` (`Layout`): right-click → Learn writes a
    `position` route (the hand is the fader), and the ROUTING page can
    `push` or `position` anything with it — one performer per param, the
    table's referee asks before a hand takes over. No MIDI in between,
    so no 7-bit steps and no channel shared with the APC40.
  * outside, as MIDI for a DAW: per axis 7-bit CC, 14-bit CC, pitch
    bend or channel pressure on any channel, rate-limited, plus a
    presence note per hand, and a note per pinch switch. This module
    makes the messages and opens no port (plan 27 B3): each frame's go
    to `outbox`, and whoever carries them out drains it (`carry`) — the
    host's `hands-daw` sink, a `midi-out` port the `[hands] out` setting
    becomes (a virtual "Hyperspace Hands" port unless it names another),
    which also brings the DAW up to date when its port comes back
    (`resync`). A caller with a port of its own hands it in as `out`.

What Ultraleap reports (LeapC through the ``leap`` Python bindings; units
are the SDK's, coordinates right-handed with the origin at the camera, +y
away from it, +z toward the performer in desktop mode):

  feature     source                            native unit    default range
  x y z       palm.position                     mm             calibrated per hand
  roll        palm.normal    atan2(n.x, −n.y)   degrees        ±90
  pitch       palm.direction atan2(d.y, −d.z)   degrees        ±60
  yaw         palm.direction atan2(d.x, −d.z)   degrees        ±45
  grab        grab_strength                     0–1            0–1
  pinch       pinch_strength                    0–1            0–1
  grab_angle  grab_angle                        rad → degrees  0–180
  pinch_mm    pinch_distance                    mm             15–100
  pinch_index thumb tip → index tip  ÷ palm.width  ×palm        0.15–1.00
  pinch_middle  … middle                                       0.15–1.05
  pinch_ring    … ring                                         0.20–1.10
  pinch_pinky   … pinky                                        0.25–1.15

The four pinches are ratios, not distances: dividing by palm width makes
one threshold fit every hand. Each also drives a switch (`Gate`) — eight
more signals, on top of the analog axes: a Schmitt trigger so they don't
chatter where the fingers hover, then a debounce so one noisy frame
can't flip them. The switches work whether or not the ratios were chosen
as dofs, and go out as the last eight hand lanes and as note on/off
(`[hands] pinch_note`). Thumb-index is by far the most reliable; ring
and pinky are weaker — occlusion when the palm turns away, and the two
fingers don't move independently, so a thumb-ring pinch tends to bring
the pinky with it.

Roll and yaw are anatomical, not room-relative: thumb-up roll and
fingers-outward yaw read as increasing on both hands, so the hands are
mirror images. x stays room-relative (left → right on both hands).

Where things live: every per-axis setting and the few global ones are
registry params in the ``hands`` group (`register`), so the library's
preset strip saves and loads a *setup*, a project carries it, and an
APC40 knob can be learned onto, say, the smoothing. The calibrated
ranges belong to the box, not to a setup: they live in
``<home>/hands.json`` (the HANDS page's calibrate button, or
tools/hands_probe.py --calibrate). Rig choices — tracking mode, which
features, the MIDI port — are the ``[hands]`` section of config.toml.

The same file holds the interaction box (plan 18): bounds on the palm's
x, y and z in the Leap's millimetres, one box for both hands, any
coordinate open. A hand the tracker sees but whose palm is outside it
reads absent — its axes NaN, its switches dropped, presence off, no
skeleton — exactly as if tracking had lost it (`HandsIO.poll`), with a
Schmitt edge (`BOX_EDGE`) so a hand on a face does not flicker. The
sweep sets the box from where the palms went (`_sweep_box`); "reset
ranges" opens it; no box, the default, bounds nothing.

  {"schema": "hyperspace.hands/3",
   "axes": {"left.x": {"lo": -214.2, "hi": 18.5}, …},
   "box": {"x": [-262.0, 262.0], "y": [71.5, 402.0], "z": null},
   "units": {"mm": null, "origin": null, "tilt": 32.0}}

``box`` is absent or null (no bounds) or has x, y, z each ``[lo, hi]``
or null (open). ``units`` (plan 26 A2, `Units`) is the calibration from
the Leap's mm into the shape's units — millimetres per shape unit, the
Leap point at the world's centre, the tilt toward the eye; null for
"from the box". A ``/1`` file has no box, a ``/2`` file no units; each
is read as it is and never rewritten at load; the first save over a file
that is not ``/3`` first keeps it beside itself as ``hands.json.bak-v1``
or ``.bak-v2`` (`_keep`).

The tracking service calls back on its own thread; `LeapSource` keeps
the newest frame under a lock and the render loop reads it once per
frame (`HandsIO.poll`), so nothing from the SDK thread touches the
registry.

Beside the features, each frame keeps each hand's skeleton (`skeleton`):
the palm frame and every digit's four bones, copied into plain floats on
the SDK thread. The ghost hands draw it (hyperspace/ghost.py) and it goes
through none of the axes' shaping: no axis and no MIDI reads it. The
dance sources do (below).

The dance sources (plan 24 C4, H2) sit beside the twelve axes, routable
like them and shaped more simply (signal.py: `Smooth`, `Flick`), with no
setup params and no DAW output:

  hand:<side>.curl.<digit>  how bent each digit is (thumb … pinky), 0
                            straight … 1 a fist: the bone-to-bone angles
                            summed (`curls`, `bend`)
  hand:<side>.spread        how far the fingers fan: index to pinky in
                            the palm's plane (`spread`)
  hand:<side>.energy        smoothed speed of the palm and the fingertips
  hand:<side>.flick         a hit on a sharp flick: spikes to its strength
                            and decays (`Flick`)
  hands:gap                 the distance between the two palms (`gap`)
  hands:twist               one hand's roll against the other's, 0.5 when
                            they mirror each other (`twist`)

The per-hand ones are lanes of the ``hand`` vector, after the pinch
switches so no older lane moves (`Layout`); the two-hand ones are a
scheme of their own, ``hands``, with its own rests. Each reads NaN while
its hand is away (the pair: either hand), so a row lets go like an
axis's; the curls and the spread need the skeleton and read NaN without
one. The constants (ranges, time constants, the flick's thresholds) are
under `DANCE`.

The grab (plan 24 C5, H1) is a fifth switch per hand, beside the pinches:

  hand:<side>.grab          a closed fist: 1 while the hand is closed, 0
                            open — the four fingers' curls (`fist`)
                            through a `Gate`, Schmitt + debounce like a
                            pinch (`GRAB_CLOSE`, `GRAB_OPEN`, `GRAB_HOLD_S`)

It is a lane after the dance sources (so no older lane moves) and a gate
the routing UI offers beside the pinches (`Layout.gates`), so a row can
act only while that hand is closed: the owner's "close a hand near the
shape and it follows the hand; open it to let go" is `position` rows from
the hand's roll / pitch / yaw, each `when` ``hand:right.grab``. Like the
dance sources it has no setup params and no DAW note; it needs the
skeleton, so with none it never closes.
"""

from __future__ import annotations

import copy
import itertools
import json
import math
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import mido

from .signal import (
    FULL,
    HYST_14,
    OUTS,
    RESTS,
    Flick,
    Follower,
    Smooth,
    describe,
    encode,
    quantize,
    shape,
    unit,
    valid,
)
from .tape import STALE_S, TapeSource  # STALE_S: no frame for this long, no hands

SIDES = ("left", "right")
LEARN_MOVE = 0.25        # y an axis must travel to win a learn
CAL_FILE = "hands.json"
# /3 (plan 26 A2): the file gains "units", the calibration from the Leap's
# mm into the shape's units; a /2 file reads as it is (units: from the box)
# and is kept beside itself as hands.json.bak-v2 before the first save
CAL_SCHEMA = "hyperspace.hands/3"
# the calibration's tilt when the file names none: the Leap's up turned
# this far toward the eye, so the eye on the shape's axis sees the hands
# from above as the ghost hands' own camera does (ghost.ELEVATION)
UNITS_TILT = 32.0
CAL_MIN_SAMPLES = 30
# the interaction box: bounds on the palm, in the Leap's mm (plan 18 WP1)
BOX_AXES = ("x", "y", "z")
BOX_MARGIN = 40.0     # mm: the sweep's box stands this far outside what the palms covered
BOX_EDGE = 15.0       # mm: a hand that is in stays in until it is this far past a face
BOX_MIN_SPAN = 120.0  # mm: a coordinate swept over less than this is left open
# "x" / "y" / "z" → (lo, hi) in mm, or None for an open coordinate
Box = dict[str, tuple[float, float] | None]
GROUP = "hands"

# feature → (unit, default lo, default hi); x has a per-hand default below
FEATURES: dict[str, tuple[str, float, float]] = {
    "x": ("mm", -120.0, 120.0),
    "y": ("mm", 100.0, 350.0),
    "z": ("mm", -100.0, 100.0),
    "roll": ("deg", -90.0, 90.0),
    "pitch": ("deg", -60.0, 60.0),
    "yaw": ("deg", -45.0, 45.0),
    "grab": ("0-1", 0.0, 1.0),
    "pinch": ("0-1", 0.0, 1.0),
    "grab_angle": ("deg", 0.0, 180.0),
    "pinch_mm": ("mm", 15.0, 100.0),
    # thumb tip to each finger tip, over palm width: hand-size independent
    "pinch_index": ("×palm", 0.15, 1.00),
    "pinch_middle": ("×palm", 0.15, 1.05),
    "pinch_ring": ("×palm", 0.20, 1.10),
    "pinch_pinky": ("×palm", 0.25, 1.15),
}
# the four thumb-to-finger pinches, in the order they are reported
PINCHES = ("index", "middle", "ring", "pinky")
PALM_W = 85.0            # mm, the fallback when the SDK reports no palm width
# each hand works its own side of the camera
X_RANGE = {"left": (-220.0, 20.0), "right": (-20.0, 220.0)}
# shaped about their middle: a neutral hand reads 0.5
BIPOLAR = {"x", "z", "roll", "pitch", "yaw"}

DEFAULT_DOFS = ["x", "y", "z", "roll", "pitch", "yaw"]
DEADZONE_CENTRED = 0.04  # a level hand reads exactly neutral; a height axis starts at 0

# [hands] in config.toml — the rig, not the performance. The one table:
# config.DEFAULTS["hands"] is this dict, HandSettings.from_config and
# HandsIO fill from it, so a key exists exactly here.
DEFAULTS: dict = {
    "enabled": False,
    "mode": "desktop",       # desktop | screentop | hmd — where the camera looks from
    "dofs": DEFAULT_DOFS,    # per hand, in axis order
    "out": "Hyperspace Hands",   # MIDI out for a DAW: an existing port by
                                 # substring, else a virtual port ("" = none).
                                 # The host's: config.py makes it the
                                 # `hands-daw` midi-out sink (plan 27 B3);
                                 # HandsIO opens no port
    "channel": 16,           # 1-based: the default channel every axis starts on
    "cc": 102,               # left hand cc … cc+n−1, right hand cc+n … cc+2n−1
    "presence": True,        # note on/off to the DAW as each hand enters / leaves
    "note": 120,             # left hand's presence note; right is note+1
    "min_confidence": 0.1,
    "calibration": CAL_FILE,
    "pinch_gates": True,     # the eight thumb-to-finger switches
    "pinch_notes": True,     # each one as a note on/off to the DAW
    "pinch_note": 100,       # left index…pinky = note…note+3, right = note+4…note+7
    "tape": "",              # a recorded hand tape (tape.py) to play instead of the camera
}
# config mode → leap.TrackingMode member
TRACKING_MODES = {"desktop": "Desktop", "screentop": "ScreenTop", "hmd": "HMD"}


# ------------------------------------------------------------- features

def _side(hand) -> str:
    t = getattr(hand.type, "name", None) or str(hand.type)
    return "left" if t.rsplit(".", 1)[-1].lower() == "left" else "right"


def _tip(digit):
    """The fingertip: the far end of the distal bone."""
    return digit.distal.next_joint


def pinches(hand) -> dict[str, float]:
    """Thumb tip to each finger tip, divided by palm width.

    A ratio, not a distance, so one threshold fits every hand: a big hand
    and a small hand touching read alike. Empty when the bindings gave no
    digits (the palm-only namespaces the tests build).
    """
    thumb = getattr(hand, "thumb", None)
    if thumb is None:
        return {}
    t = _tip(thumb)
    scale = float(getattr(hand.palm, "width", 0.0) or 0.0) or PALM_W
    out = {}
    for f in PINCHES:
        d = _tip(getattr(hand, f))
        out[f"pinch_{f}"] = math.dist((t.x, t.y, t.z), (d.x, d.y, d.z)) / scale
    return out


def features(hand) -> dict[str, float]:
    """Every feature of one ``leap`` Hand in its native unit (see the table).

    Duck-typed on the bindings' attribute names, so tests pass plain
    namespaces. Rotations are already mirrored for the left hand.
    """
    palm = hand.palm
    p, n, d = palm.position, palm.normal, palm.direction
    roll = math.degrees(math.atan2(n.x, -n.y))
    pitch = math.degrees(math.atan2(d.y, -d.z))
    yaw = math.degrees(math.atan2(d.x, -d.z))
    if _side(hand) == "right":
        roll = -roll         # thumb-up is −roll on the right hand
    else:
        yaw = -yaw           # fingers-outward is −x on the left hand
    return {
        "x": float(p.x), "y": float(p.y), "z": float(p.z),
        "roll": roll, "pitch": pitch, "yaw": yaw,
        "grab": float(hand.grab_strength), "pinch": float(hand.pinch_strength),
        "grab_angle": math.degrees(float(hand.grab_angle)),
        "pinch_mm": float(hand.pinch_distance),
        **pinches(hand),
    }


# the skeleton's digits and bones, in the bindings' attribute names and order
DIGITS = ("thumb", "index", "middle", "ring", "pinky")
BONES = ("metacarpal", "proximal", "intermediate", "distal")
_NO_ROT = (0.0, 0.0, 0.0, 1.0)

# ---- the dance sources (plan 24 C4, H2): beside the twelve axes, never
# instead of them. Per hand, after the pinch switches in the `hand` vector:
# five curls (DIGITS order), spread, energy, flick; and the two-hand
# `hands` scheme: gap, twist. Each 0–1, NaN while its hand (or, for the
# pair, either hand) is away. The curls and the spread read the skeleton
# (`skeleton`), so a source that gives none (a palm-only fake) reads NaN
# there; energy and flick fall back to the palm; gap and twist read the
# features. The numbers below are the shaping (decision register draft
# rows, plan 24 C4): ranges in the native unit, then time constants.
DANCE = tuple(f"curl.{f}" for f in DIGITS) + ("spread", "energy", "flick")
PAIR = ("gap", "twist")
PAIR_RESTS = (0.0, 0.5)        # gap rests closed, twist level (it is centred)
# a digit's bend, summed over its joints, degrees: open → 0, a fist → 1.
# The thumb has one joint fewer that bends much, so its own range
CURL_RANGE = {"thumb": (10.0, 80.0)}
CURL_RANGE_FINGER = (20.0, 220.0)
CURL_S = 0.05                  # s, the curls' and the spread's smoothing (attack = decay)
# the fan: the angle between the index's and the pinky's proximal bones in
# the palm's plane, degrees. A finger bent more than ~70° at the knuckle
# has no direction in that plane: the spread reads 0 (a fist does not fan)
SPREAD_RANGE = (10.0, 60.0)
SPREAD_MIN_FLAT = 0.35         # in-plane length / bone length under which a finger is "down"
# energy: the mean speed of the palm and the five tips, mm/s, over a floor
# that a still hand's tracking jitter stays under; fast up, slow down
ENERGY_RANGE = (60.0, 1000.0)
ENERGY_ATTACK_S = 0.06
ENERGY_DECAY_S = 0.5
# flick: the fastest tip (the palm, with no skeleton), mm/s. Fires at ON,
# re-arms under OFF, strength speed / FULL; past CEILING it is a tracking
# jump. The hit decays with time constant FLICK_DECAY_S
FLICK_ON = 1500.0
FLICK_OFF = 700.0
FLICK_FULL = 3000.0
FLICK_CEILING = 10000.0
FLICK_DECAY_S = 0.15
SPEED_GAP_S = 0.1              # frames further apart than this measure no speed
# the pair: the palms' distance, mm; and the twist — the right hand's
# anatomical roll less the left's, so mirror-image hands (both palms down,
# a clap) read level and turning a wheel clockwise, as the performer sees
# it, reads up — degrees each way from level to the ends
GAP_RANGE = (60.0, 600.0)
TWIST_FULL = 90.0
PAIR_S = 0.05                  # s, the pair's smoothing
# the grab switch (plan 24 C5): a fist is the mean raw curl of the four
# fingers (the thumb tucks or not — a fist either way). Closes past
# GRAB_CLOSE, lets go only under GRAB_OPEN (the Schmitt gap: a hand
# hovering half-closed does not chatter), and an edge must hold
# GRAB_HOLD_S before it counts. Low enough that a real fist, which may
# not bend as far as the curl range's top, still closes it
GRAB_FINGERS = ("index", "middle", "ring", "pinky")
GRAB_CLOSE = 0.65
GRAB_OPEN = 0.45
GRAB_HOLD_S = 0.05


def _v3(v) -> tuple[float, float, float]:
    return (float(v.x), float(v.y), float(v.z))


def _quat(q) -> tuple[float, float, float, float]:
    if q is None:
        return _NO_ROT
    return (float(q.x), float(q.y), float(q.z), float(q.w))


def _bone(b) -> dict:
    return {"prev": _v3(b.prev_joint), "next": _v3(b.next_joint),
            "width": float(getattr(b, "width", 0.0) or 0.0),
            "rot": _quat(getattr(b, "rotation", None))}


def _digit_bones(digit) -> list:
    """A digit's four bones, base to tip: by name, else the `bones` list."""
    named = [getattr(digit, n, None) for n in BONES]
    if all(b is not None for b in named):
        return named
    return list(getattr(digit, "bones", ()))[:len(BONES)]


def skeleton(hand) -> dict:
    """One ``leap`` Hand's skeleton as plain floats (mm, the SDK's frame):

      palm, normal, direction   3-tuples; width (mm, PALM_W when unreported)
      digits                    five lists (DIGITS order) of four bones
                                (BONES order), each {prev, next, width, rot}:
                                joints as 3-tuples, rot a quaternion (x, y, z, w)
      arm                       one bone (elbow → wrist), or None

    Copied, so nothing the SDK owns outlives its callback. `digits` is
    empty when the bindings gave none (the palm-only namespaces tests build).
    """
    palm = hand.palm
    digits = []
    if getattr(hand, "thumb", None) is not None:
        for name in DIGITS:
            bones = _digit_bones(getattr(hand, name))
            if len(bones) != len(BONES):
                digits = []
                break
            digits.append([_bone(b) for b in bones])
    arm = getattr(hand, "arm", None)
    return {
        "palm": _v3(palm.position), "normal": _v3(palm.normal),
        "direction": _v3(palm.direction),
        "width": float(getattr(palm, "width", 0.0) or 0.0) or PALM_W,
        "digits": digits,
        "arm": _bone(arm) if arm is not None and hasattr(arm, "prev_joint") else None,
    }


def _sub(a, b) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _len(a) -> float:
    return math.sqrt(_dot(a, a))


def _angle(a, b) -> float | None:
    """Degrees between two vectors; None when either has no length."""
    la, lb = _len(a), _len(b)
    if la < 1e-6 or lb < 1e-6:
        return None
    return math.degrees(math.acos(min(1.0, max(-1.0, _dot(a, b) / (la * lb)))))


def bend(bones: list) -> float:
    """A digit's bend, degrees: the angles between each bone and the next,
    summed, skipping a bone with no length (the thumb's metacarpal)."""
    dirs = [d for d in (_sub(b["next"], b["prev"]) for b in bones) if _len(d) > 1e-6]
    return sum(a for a in (_angle(u, v) for u, v in itertools.pairwise(dirs)) if a is not None)


def curls(skel: dict | None) -> dict[str, float]:
    """How bent each digit is, 0 (straight) … 1 (a fist), from a `skeleton`:
    `bend` over CURL_RANGE. Empty when the skeleton has no digits. The
    raw form the curl lanes smooth, and what a grab switch can read."""
    digits = (skel or {}).get("digits") or []
    if len(digits) != len(DIGITS):
        return {}
    return {f: unit(bend(d), *CURL_RANGE.get(f, CURL_RANGE_FINGER))
            for f, d in zip(DIGITS, digits)}


def spread(skel: dict | None) -> float | None:
    """How far the fingers fan, 0 … 1: the angle between the index's and
    the pinky's proximal bones, both laid into the palm's plane, over
    SPREAD_RANGE. 0 when either finger points out of the plane (bent
    down past SPREAD_MIN_FLAT); None with no digits or no palm normal."""
    digits = (skel or {}).get("digits") or []
    n = (skel or {}).get("normal")
    if len(digits) != len(DIGITS) or n is None or _len(n) < 1e-6:
        return None
    nn = _len(n)
    flat = []
    for f in ("index", "pinky"):
        b = digits[DIGITS.index(f)][1]                  # the proximal bone
        d = _sub(b["next"], b["prev"])
        k = _dot(d, n) / (nn * nn)
        p = (d[0] - k * n[0], d[1] - k * n[1], d[2] - k * n[2])
        if _len(d) < 1e-6 or _len(p) < SPREAD_MIN_FLAT * _len(d):
            return 0.0
        flat.append(p)
    a = _angle(*flat)
    return None if a is None else unit(a, *SPREAD_RANGE)


def points(feats: dict, skel: dict | None) -> list[tuple[float, float, float]]:
    """What energy and flick watch move: the palm, then the five
    fingertips when the skeleton has them (mm). Empty for a frame without
    a whole palm: nothing measured."""
    palm = _palm(feats)
    if palm is None:
        return []
    out = [palm]
    digits = (skel or {}).get("digits") or []
    if len(digits) == len(DIGITS):
        out += [tuple(d[-1]["next"]) for d in digits]
    return out


def _palm(feats: dict) -> tuple[float, float, float] | None:
    """The palm's (x, y, z) from `features`, None unless all three are finite."""
    try:
        p = tuple(float(feats[c]) for c in BOX_AXES)
    except (KeyError, TypeError, ValueError):
        return None
    return p if all(math.isfinite(v) for v in p) else None


def twist(left: dict, right: dict) -> float | None:
    """The right hand's roll less the left's (`features`, anatomical:
    mirror-image hands read 0), wrapped to ±180°, over ±TWIST_FULL about
    0.5. None when either roll is missing."""
    try:
        d = float(right["roll"]) - float(left["roll"])
    except (KeyError, TypeError, ValueError):
        return None
    if not math.isfinite(d):
        return None
    return unit((d + 180.0) % 360.0 - 180.0, -TWIST_FULL, TWIST_FULL)


def gap(left: dict, right: dict) -> float | None:
    """The distance between the palms (`features` x, y, z) over GAP_RANGE;
    None without both whole palms."""
    a, b = _palm(left), _palm(right)
    return None if a is None or b is None else unit(math.dist(a, b), *GAP_RANGE)


def fist(c: dict | None) -> float | None:
    """How closed the hand is, 0 open … 1 a fist: the mean of the four
    fingers' curls (`curls`, raw), the thumb left out. None unless all
    four were read (no skeleton): the grab switch then holds where it is."""
    try:
        v = [float(c[f]) for f in GRAB_FINGERS]
    except (KeyError, TypeError, ValueError):
        return None
    return sum(v) / len(v) if all(math.isfinite(x) for x in v) else None


def step_grab(gate: Gate, c: dict | None, t: float) -> bool:
    """Step one hand's grab switch from its raw curls. `Gate` closes
    *under* its threshold (a pinch's distance), so it is fed how open
    the hand is, 1 − `fist`: it closes when the fist passes GRAB_CLOSE
    and lets go when it falls under GRAB_OPEN."""
    f = fist(c)
    return gate.step(None if f is None else 1.0 - f, t, close=1.0 - GRAB_CLOSE,
                     open_=1.0 - GRAB_OPEN, hold=GRAB_HOLD_S)


class Dance:
    """One hand's dance sources at run time — never saved. `curl` is per
    digit (DIGITS); `raw` the last unsmoothed readings (the curls by
    digit, the spread, the energy's and the flick's speeds in mm/s), for
    the page and for anything — a grab switch — that wants the curls
    before smoothing."""

    def __init__(self) -> None:
        self.curl = {f: Smooth() for f in DIGITS}
        self.spread = Smooth()
        self.energy = Smooth()
        self.flick = Flick()
        self.raw: dict = {}
        self._prev: tuple | None = None     # (t, points) of the last tracking frame
        self._target = 0.0                  # the energy's last measured target

    def reset(self) -> None:
        """The hand left: every reading forgets."""
        for sm in (*self.curl.values(), self.spread, self.energy):
            sm.y = None
        self.flick.reset()
        self.raw, self._prev, self._target = {}, None, 0.0

    def step(self, dt: float, t: float, fresh: bool, feats: dict | None,
             skel: dict | None) -> None:
        """One render frame; `feats` None while the hand is away. A fresh
        tracking frame measures (curls, spread, speeds); every frame
        smooths, and the flick decays."""
        if feats is None:
            self.reset()
            return
        top = None
        if fresh or not self.raw:
            # no speed measured this frame (the first after a gap, or the
            # point count changed): the energy falls toward 0 at its decay
            # rather than holding its last target
            speed, self._target = None, 0.0
            pts = points(feats, skel)
            prev, self._prev = self._prev, (t, pts)
            if (pts and prev is not None and len(prev[1]) == len(pts)
                    and 0.0 < t - prev[0] <= SPEED_GAP_S):
                v = [math.dist(a, b) / (t - prev[0]) for a, b in zip(pts, prev[1])]
                speed, top = sum(v) / len(v), max(v[1:] or v)
                self._target = unit(speed, *ENERGY_RANGE)
            self.raw = {"curl": curls(skel), "spread": spread(skel), "energy": speed,
                        "flick": top}
        c = self.raw["curl"]
        for f in DIGITS:
            self.curl[f].step(dt, c.get(f), CURL_S, CURL_S)
        self.spread.step(dt, self.raw["spread"], CURL_S, CURL_S)
        self.energy.step(dt, self._target, ENERGY_ATTACK_S, ENERGY_DECAY_S)
        self.flick.step(dt, top, on=FLICK_ON, off=FLICK_OFF, full=FLICK_FULL,
                        decay_s=FLICK_DECAY_S, ceiling=FLICK_CEILING)

    def values(self) -> list[float]:
        """The hand's `DANCE` lanes, in order; NaN for a reading it has not got."""
        nan = lambda y: math.nan if y is None else y
        return ([nan(self.curl[f].y) for f in DIGITS]
                + [nan(self.spread.y), nan(self.energy.y), self.flick.y])


class OneEuro:
    """The One Euro filter (Casiez et al. 2012) over a scalar: a low-pass
    whose cutoff rises with speed — a still hand does not shimmer, a moving
    one does not lag. `reset` forgets the history."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 4.0, d_cutoff: float = 1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.reset()

    def reset(self) -> None:
        self.x: float | None = None
        self.dx = 0.0
        self.t = 0.0

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: float, t: float) -> float:
        if self.x is None:
            self.x, self.t = x, t
            return x
        dt = t - self.t
        if dt <= 0.0:
            return self.x
        self.t = t
        a_d = self._alpha(self.d_cutoff, dt)
        self.dx += a_d * ((x - self.x) / dt - self.dx)
        a = self._alpha(self.min_cutoff + self.beta * abs(self.dx), dt)
        self.x += a * (x - self.x)
        return self.x


# ------------------------------------------------------------- settings

class Gate:
    """A pinch as a switch: Schmitt trigger, then a debounce.

    Two thresholds, not one — a bare ``d < k`` chatters where the fingers
    hover at k. It closes under `close`, and only lets go above `open_`,
    which is deliberately the wider gap. A candidate edge then has to hold
    for `hold` seconds before it counts, so a single noisy frame cannot
    flip the switch.
    """

    __slots__ = ("_edge", "_since", "on")

    def __init__(self) -> None:
        self.on = False
        self._edge: bool | None = None    # the flip being timed, if any
        self._since = 0.0

    def reset(self) -> None:
        """The hand left: drop the switch and forget any pending edge."""
        self.on = False
        self._edge = None

    def step(self, d: float | None, t: float, *, close: float, open_: float,
             hold: float) -> bool:
        if d is None or math.isnan(d):
            return self.on
        want = d < close if not self.on else not d > max(open_, close)
        if want == self.on:
            self._edge = None
        else:
            if self._edge != want:
                self._edge, self._since = want, t
            if t - self._since >= hold:
                self.on = want
                self._edge = None
        return self.on


@dataclass
class AxisSettings:
    """What a setup says about one axis — every field is a registry param.

    The three shape fields that depend on the feature (`bipolar`,
    `deadzone`, `rest_value`) default to None and are filled from
    `BIPOLAR` in `__post_init__`; the MIDI fields default from `DEFAULTS`.
    So there is no second table of defaults here: a bare
    ``AxisSettings("right", "roll")`` is the axis `from_config` builds.
    """

    side: str
    feature: str
    invert: bool = False
    bipolar: bool | None = None      # None: centred iff the feature is in BIPOLAR
    deadzone: float | None = None    # centred: half-width about the middle; else at the bottom
    curve: float = 0.0               # −1 … 1, the exponent 4^c
    attack: float = 0.0              # s, rising
    decay: float = 0.0               # s, falling
    rest: str = "return"             # "hold" | "return" when the hand leaves
    rest_value: float | None = None  # None: the middle when centred, else the bottom
    return_s: float = 0.5            # spring settle time back to rest
    bounce: float = 0.15             # 0 critically damped … 1 rings
    out: str = "cc"                  # OUTS
    channel: int = DEFAULTS["channel"]   # 1-based
    number: int = DEFAULTS["cc"]

    def __post_init__(self) -> None:
        if self.bipolar is None:
            self.bipolar = self.feature in BIPOLAR
        if self.deadzone is None:
            self.deadzone = DEADZONE_CENTRED if self.bipolar else 0.0
        if self.rest_value is None:
            self.rest_value = 0.5 if self.bipolar else 0.0

    @property
    def name(self) -> str:
        return f"{self.side}.{self.feature}"

    @property
    def label(self) -> str:
        return f"{self.side[0].upper()} {self.feature}"


@dataclass
class HandSettings:
    """A whole setup: the axes plus the global feel."""

    axes: list[AxisSettings] = field(default_factory=list)
    smooth: float = 1.0          # One Euro min cutoff, Hz — lower is steadier at rest
    response: float = 4.0        # One Euro beta — higher follows fast moves closer
    catch_s: float = 0.15        # glide onto a returning hand
    learn_depth: float = 0.25    # the depth a Learn lands with when it lands as a push
    rate: int = 200              # MIDI messages a second per axis at most (0 = no cap)
    steady: float = 0.35         # 7-bit hysteresis, in steps past the half-step
    pinch_close: float = 0.34    # ×palm: tips closer than this close the switch
    pinch_open: float = 0.46     # ×palm: it only lets go past this — the wider gap
    pinch_hold: float = 0.04     # s an edge must hold before it counts

    @classmethod
    def from_config(cls, cfg: dict | None = None) -> HandSettings:
        """The axes a rig config asks for: `dofs` per hand, left then
        right, on consecutive CCs from `cc` on `channel`."""
        cfg = rig(cfg)
        dofs = list(cfg["dofs"])
        bad = [d for d in dofs if d not in FEATURES]
        if bad:
            raise ValueError(f"unknown hand dofs {bad}; known: {', '.join(FEATURES)}")
        cc0, ch = int(cfg["cc"]), int(cfg["channel"])
        if cc0 < 0 or cc0 + 2 * len(dofs) - 1 > 127:
            raise ValueError(f"hands: cc {cc0} + {2 * len(dofs)} axes runs past 127")
        if cfg["pinch_gates"] and cfg["pinch_notes"]:
            n0, n1 = int(cfg["pinch_note"]), int(cfg["pinch_note"]) + 2 * len(PINCHES) - 1
            note = int(cfg["note"])
            if n0 < 0 or n1 > 127:
                raise ValueError(f"hands: pinch_note {n0} + 8 switches runs past 127")
            if cfg["presence"] and n0 <= note + 1 and note <= n1:
                raise ValueError(f"hands: pinch notes {n0}–{n1} collide with the "
                                 f"presence notes {note}–{note + 1}")
        axes = [AxisSettings(side, feat, channel=ch, number=cc0 + s * len(dofs) + k)
                for s, side in enumerate(SIDES) for k, feat in enumerate(dofs)]
        return cls(axes)


def rig(cfg: dict | None) -> dict:
    """A ``[hands]`` section with every default filled in, as a copy that
    shares nothing with the table. Idempotent: config.load fills the
    section from the same DEFAULTS, and `from_config` and `HandsIO` each
    accept a partial one (tests, the probe's overrides), so the fill runs
    wherever a section arrives and there is still one table."""
    return copy.deepcopy({**DEFAULTS, **(cfg or {})})


def register(reg, settings: HandSettings) -> None:
    """Every setting as a param in the ``hands`` group — what a setup
    preset saves. Not modulatable: a lane shouldn't bend the instrument."""
    if f"{GROUP}.smooth" in reg:
        return

    def cont(pid, label, obj, attr, lo, hi, *, tip, fmt=None, integer=False, log=False):
        reg.continuous(pid, label, lambda: getattr(obj, attr),
                       lambda v: setattr(obj, attr, int(v) if integer else float(v)),
                       lo=lo, hi=hi, integer=integer, log=log, fmt=fmt, group=GROUP,
                       tip=tip, modulatable=False)

    def choice(pid, label, obj, attr, names, tip):
        reg.enum(pid, label, lambda: names.index(getattr(obj, attr)),
                 lambda i: setattr(obj, attr, names[int(i)]), names, group=GROUP, tip=tip,
                 modulatable=False)

    def flag(pid, label, obj, attr, tip):
        reg.toggle(pid, label, lambda: getattr(obj, attr),
                   lambda v: setattr(obj, attr, bool(v)), group=GROUP, tip=tip,
                   modulatable=False)

    secs = lambda v: f"{v * 1000:.0f} ms" if v < 1 else f"{v:.2f} s"
    g = settings
    cont(f"{GROUP}.smooth", "Steadiness", g, "smooth", 0.1, 10.0, log=True,
         fmt=lambda v: f"{v:.2f} Hz",
         tip="Smoothing at rest (One Euro cutoff). Lower: a held hand is stiller; "
             "higher: less lag on slow moves.")
    cont(f"{GROUP}.response", "Response", g, "response", 0.0, 20.0,
         tip="How much fast moves open the smoothing up. Higher: quick gestures "
             "track closer; lower: steadier but laggier.")
    cont(f"{GROUP}.catch", "Catch", g, "catch_s", 0.0, 1.0, fmt=secs,
         tip="When a hand comes back, glide onto it over this long instead of jumping.")
    cont(f"{GROUP}.learn_depth", "Learn depth", g, "learn_depth", 0.05, 1.0,
         fmt=lambda v: f"{v:.2f}",
         tip="The depth a hand Learn lands with when it lands as a push — the number "
             "the ROUTING row shows. 0.25: the whole tilt moves the param a quarter of "
             "its throw, half each way from where you set it. Rows you already have "
             "keep theirs.")
    cont(f"{GROUP}.rate", "MIDI rate", g, "rate", 0, 1000, integer=True,
         fmt=lambda v: "no cap" if v <= 0 else f"{int(v)}/s",
         tip="Most messages a second per axis to the DAW port (0: no cap). "
             "The last value always gets through.")
    cont(f"{GROUP}.steady", "Hysteresis", g, "steady", 0.0, 2.0,
         tip="How far past a 7-bit step a value must go before it's sent — "
             "stops a still hand flickering between two values.")
    ratio = lambda v: f"{v:.2f}×palm"
    cont(f"{GROUP}.pinch_close", "Pinch close", g, "pinch_close", 0.1, 1.0, fmt=ratio,
         tip="How close thumb and fingertip must come to close a pinch switch, "
             "as a fraction of palm width — so it fits any hand.")
    cont(f"{GROUP}.pinch_open", "Pinch release", g, "pinch_open", 0.1, 1.5, fmt=ratio,
         tip="How far they must part again to let go. Keep it above Pinch close: "
             "the gap between the two is what stops the switch chattering.")
    cont(f"{GROUP}.pinch_hold", "Pinch debounce", g, "pinch_hold", 0.0, 0.5, fmt=secs,
         tip="How long a pinch must hold before it counts, so one noisy frame "
             "can't flip the switch.")
    for a in g.axes:
        p = f"{GROUP}.{a.name}"
        flag(f"{p}.invert", "Invert", a, "invert", "Flip the axis end for end.")
        flag(f"{p}.bipolar", "Centred", a, "bipolar",
             "Shape about the middle (a tilt, a sideways move): the dead zone sits "
             "at neutral. Off: at the bottom (height).")
        cont(f"{p}.deadzone", "Dead zone", a, "deadzone", 0.0, 0.5,
             tip="A flat band where the output doesn't move — at neutral when "
                 "centred, else at the bottom. The rest of the throw still "
                 "reaches both ends.")
        cont(f"{p}.curve", "Curve", a, "curve", -1.0, 1.0,
             tip="+: fine near neutral, fast at the ends. −: the reverse. 0: linear.")
        cont(f"{p}.attack", "Attack", a, "attack", 0.0, 2.0, fmt=secs,
             tip="Time constant while the output rises.")
        cont(f"{p}.decay", "Decay", a, "decay", 0.0, 2.0, fmt=secs,
             tip="Time constant while the output falls.")
        choice(f"{p}.rest", "On exit", a, "rest", RESTS,
               "When the hand leaves: hold the last value, or spring back to rest.")
        cont(f"{p}.rest_value", "Rest", a, "rest_value", 0.0, 1.0,
             tip="Where the output returns to when the hand leaves.")
        cont(f"{p}.return", "Return", a, "return_s", 0.05, 3.0, fmt=secs,
             tip="How long the spring takes to settle at rest.")
        cont(f"{p}.bounce", "Bounce", a, "bounce", 0.0, 1.0,
             tip="0: glides home. Higher: overshoots and rings like a spring.")
        choice(f"{p}.out", "MIDI out", a, "out", OUTS,
               "What goes to the DAW port: 7-bit CC, 14-bit CC (MSB n, LSB n+32), "
               "pitch bend or channel pressure (one axis per channel), or nothing.")
        cont(f"{p}.channel", "Channel", a, "channel", 1, 16, integer=True,
             tip="MIDI channel, 1–16.")
        cont(f"{p}.number", "CC", a, "number", 0, 127, integer=True,
             tip="CC number (0–31 for 14-bit).")

    # the selected axis — the HANDS page's list and a desk knob share it —
    # and `hands.sel.return`, a view onto that axis's return time (the
    # APC40's global layer has it on a track knob). Neither is saved or
    # performed; the host resolves the alias through `reg.aliases`, when
    # it has one (duck-typed: this module imports nothing from the host)
    if not g.axes:
        return
    sel = [0]
    axis = lambda: g.axes[min(max(sel[0], 0), len(g.axes) - 1)]
    reg.enum(f"{GROUP}.select", "Axis", lambda: min(max(sel[0], 0), len(g.axes) - 1),
             lambda i: sel.__setitem__(0, int(i)), [a.label for a in g.axes], group=GROUP,
             persist=False, modulatable=False,
             tip="Which axis the page edits — hands.sel.* follow it.")
    reg.continuous(f"{GROUP}.sel.return", "Return", lambda: axis().return_s,
                   lambda v: setattr(axis(), "return_s", float(v)), lo=0.05, hi=3.0,
                   fmt=secs, group=GROUP, alias=True,
                   tip="The selected axis's return: how long its spring takes to "
                       "settle at rest.")
    aliases = getattr(reg, "aliases", None)
    if aliases is not None:
        aliases[f"{GROUP}.sel."] = lambda p: reg.get(f"{GROUP}.{axis().name}.{p.id[10:]}")


SHAPE_KEYS = ("invert", "bipolar", "deadzone", "curve", "attack", "decay", "rest",
              "rest_value", "return_s", "bounce")


def mirror(settings: HandSettings, name: str) -> AxisSettings | None:
    """Copy an axis's feel (shape, dynamics, rest — not its MIDI out) to
    the same axis on the other hand, so both hands answer alike."""
    src = next((a for a in settings.axes if a.name == name), None)
    if src is None:
        return None
    other = "right" if src.side == "left" else "left"
    dst = next((a for a in settings.axes if a.side == other and a.feature == src.feature),
               None)
    if dst is not None:
        for k in SHAPE_KEYS:
            setattr(dst, k, getattr(src, k))
    return dst


def conflicts(settings: HandSettings) -> dict[str, str]:
    """axis name → why its MIDI output is a problem, for the page."""
    out: dict[str, str] = {}
    seen: dict[tuple, str] = {}
    for a in settings.axes:
        why = valid(a.out, a.number)
        if why:
            out[a.name] = why
            continue
        if a.out == "off":
            continue
        if a.out in ("pitch", "pressure"):
            keys = [(a.out, a.channel)]
        elif a.out == "cc14":
            keys = [("cc", a.channel, a.number), ("cc", a.channel, a.number + 32)]
        else:
            keys = [("cc", a.channel, a.number)]
        for k in keys:
            if k in seen:
                out[a.name] = f"shares its output with {seen[k]}"
            else:
                seen[k] = a.name
    return out


# ----------------------------------------------------------- calibration

def default_range(side: str, feature: str) -> tuple[float, float]:
    return X_RANGE[side] if feature == "x" else FEATURES[feature][1:]


def load_calibration(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    try:
        return dict(json.loads(path.read_text()).get("axes", {}))
    except (OSError, ValueError, AttributeError) as e:
        print(f"hands: {path}: {e}", file=sys.stderr)
        return {}


def _pair(v) -> tuple[float, float] | None:
    """A box coordinate as the file spells it, ``[lo, hi]``: two finite
    numbers, lo < hi — else None."""
    if not isinstance(v, (list, tuple)) or len(v) != 2:
        return None
    if any(isinstance(n, bool) or not isinstance(n, (int, float)) for n in v):
        return None
    lo, hi = float(v[0]), float(v[1])
    return (lo, hi) if math.isfinite(lo) and math.isfinite(hi) and lo < hi else None


def load_box(path: Path | None) -> Box | None:
    """The interaction box in the calibration file, or None when it has
    none (no file, a ``/1`` file, ``"box": null``, every coordinate open).

    A bad box opens, it never hides the hands: a coordinate that is not
    ``[lo, hi]`` with two finite numbers, lo < hi, is open, and a `box`
    that is no object is no box — each said once on stderr. A file that
    does not read is `load_calibration`'s to report."""
    if path is None or not path.exists():
        return None
    try:
        raw = json.loads(path.read_text()).get("box")
    except (OSError, ValueError, AttributeError):
        return None
    if raw is None:
        return None
    if not isinstance(raw, dict):
        print(f"hands: {path.name}: box: not an object ({str(raw)[:40]!r}); no box",
              file=sys.stderr)
        return None
    box: Box = {}
    for c in BOX_AXES:
        v = raw.get(c)
        box[c] = None if v is None else _pair(v)
        if box[c] is None and (v is not None or c not in raw):
            why = ("missing" if c not in raw
                   else f"not [lo, hi] with lo < hi ({str(v)[:40]!r})")
            print(f"hands: {path.name}: box.{c}: {why}; left open", file=sys.stderr)
    return box if any(b is not None for b in box.values()) else None


def inside(box: Box | None, feats: dict, grow: float = 0.0) -> bool:
    """Is a palm (`features`' x, y, z in mm) in the box? Each coordinate
    with a bound must lie within it, `grow` mm past either face allowed
    (the Schmitt edge: `BOX_EDGE` for a hand already in). No box: True."""
    if box is None:
        return True
    for c in BOX_AXES:
        b = box.get(c)
        if b is not None and c in feats and not b[0] - grow <= feats[c] <= b[1] + grow:
            return False
    return True


@dataclass
class Units:
    """The calibration from the Leap's millimetres into the shape's units
    (plan 26 A2): where the hands sit in the one world the shape is drawn
    in, so the eye (`eye.*`) sees both. A point p (Leap mm) lands at

        world = R_x(tilt) · stage(p − origin) / mm

    where stage is the tracking mode's basis (`ghost.basis`, `ghost.mirror`
    included) and R_x turns the stage's up `tilt` degrees toward the eye.
    `mm` is how many millimetres make one shape unit (the shape's unit
    circumradius) and `origin` the Leap point at the world's centre — each
    None for "from the box": the box's centre, and the scale that fits the
    padded box in the eye's frame as the ghost hands' camera fits it
    (`ghost.calibration`). Room settings, beside the ranges and the box in
    hands.json; the defaults are all "from the box"."""

    mm: float | None = None
    origin: tuple[float, float, float] | None = None
    tilt: float = UNITS_TILT

    def to_json(self) -> dict:
        return {"mm": None if self.mm is None else round(self.mm, 4),
                "origin": None if self.origin is None else [round(n, 3) for n in self.origin],
                "tilt": round(self.tilt, 3)}


def load_units(path: Path | None) -> Units:
    """The calibration in the file, or the defaults (all from the box) when
    it has none: no file, a /1 or /2 file, ``"units": null``. A bad entry
    is left at its default and said once on stderr — a typo never moves
    the hands out of the frame."""
    if path is None or not path.exists():
        return Units()
    try:
        raw = json.loads(path.read_text()).get("units")
    except (OSError, ValueError, AttributeError):
        return Units()
    if raw is None:
        return Units()
    if not isinstance(raw, dict):
        print(f"hands: {path.name}: units: not an object ({str(raw)[:40]!r}); from the box",
              file=sys.stderr)
        return Units()

    def number(v) -> float | None:
        ok = (isinstance(v, (int, float)) and not isinstance(v, bool)
              and math.isfinite(float(v)))
        return float(v) if ok else None

    out = Units()
    mm, origin, tilt = raw.get("mm"), raw.get("origin"), raw.get("tilt", UNITS_TILT)
    if mm is not None:
        n = number(mm)
        if n is None or n <= 0.0:
            print(f"hands: {path.name}: units.mm: not a positive number ({str(mm)[:40]!r}); "
                  "from the box", file=sys.stderr)
        else:
            out.mm = n
    if origin is not None:
        ns = [number(v) for v in origin] if isinstance(origin, (list, tuple)) else []
        if len(ns) != 3 or any(n is None for n in ns):
            print(f"hands: {path.name}: units.origin: not [x, y, z] ({str(origin)[:40]!r}); "
                  "from the box", file=sys.stderr)
        else:
            out.origin = (ns[0], ns[1], ns[2])
    if tilt is not None:
        n = number(tilt)
        if n is None:
            print(f"hands: {path.name}: units.tilt: not a number ({str(tilt)[:40]!r}); "
                  f"{UNITS_TILT:g}°", file=sys.stderr)
        else:
            out.tilt = n
    return out


def save_calibration(path: Path, ranges: dict[str, tuple[float, float]],
                     box: Box | None = None, units: Units | None = None) -> None:
    data = {"schema": CAL_SCHEMA,
            "axes": {k: {"lo": round(lo, 3), "hi": round(hi, 3)}
                     for k, (lo, hi) in ranges.items()},
            "box": None if box is None else
            {c: None if box.get(c) is None else [round(n, 3) for n in box[c]]
             for c in BOX_AXES},
            "units": (units or Units()).to_json()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n")


def _old_schema(path: Path) -> str | None:
    """What a file about to be overwritten is, when it is not this
    build's: its schema's number ("1"), "1" for a file with no schema or
    one that does not parse — None when there is no file or it is
    already `CAL_SCHEMA` (nothing to keep)."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError:
        return "1"              # there, unreadable: let `_keep` say why
    try:
        schema = json.loads(raw).get("schema")
    except (ValueError, AttributeError):
        return "1"
    if schema == CAL_SCHEMA:
        return None
    n = schema.rsplit("/", 1)[-1] if isinstance(schema, str) else ""
    return n if n.isdigit() else "1"


def _keep(path: Path, schema: str = "1") -> Path:
    """The file as it is, copied beside itself before the first save of
    this build rewrites it: ``hands.json.bak-v1``, or
    ``hands.json.bak-v1-<YYYYmmdd-HHMMSS>`` (then ``-2``, ``-3`` …) when
    that name is taken. An exclusive create, so nothing already there —
    an earlier backup, a copy the owner made — is ever overwritten.
    routing.backup's naming and rule, spelled here because this module
    imports nothing from the host (only its own package's signal and
    tape). Raises OSError when no copy could be made; the caller saves
    all the same."""
    data = path.read_bytes()
    base = f"{path.name}.bak-v{schema}"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    names = itertools.chain([base, f"{base}-{stamp}"],
                            (f"{base}-{stamp}-{n}" for n in range(2, 100)))
    for name in names:
        bak = path.with_name(name)
        try:
            f = bak.open("xb")
        except FileExistsError:
            continue
        try:
            with f:
                f.write(data)
        except OSError:
            bak.unlink(missing_ok=True)     # ours, and incomplete
            raise
        return bak
    raise FileExistsError(f"every name from {base} on is taken")


# --------------------------------------------------------------- source

class LeapSource:
    """The Ultraleap tracking service through the ``leap`` bindings.

    Connects on a thread (the service may be slow or absent; the show
    must not wait), sets the tracking mode, and keeps the newest frame.
    `latest()` is what the render loop reads.
    """

    def __init__(self, mode: str = "desktop", clock=time.monotonic):
        import leap  # optional: only here, only when [hands] is enabled

        self.clock = clock
        self.status = "connecting"
        self._lock = threading.Lock()
        self._hands: dict[str, tuple[dict, float]] = {}
        self._skel: dict[str, dict] = {}
        self._seq = 0
        self._t = -1.0
        src = self

        class _Listener(leap.Listener):
            def on_connection_event(self, event):
                src.status = "connected"

            def on_connection_lost_event(self, event):
                src.status = "service lost"

            def on_device_event(self, event):
                src.status = "tracking"

            def on_device_lost_event(self, event):
                src.status = "no camera"

            def on_tracking_event(self, event):
                src._frame(event.hands)

            def on_error(self, error):
                # the SDK's poll thread reports anything that raised in a
                # callback here — _frame included — and otherwise drops it,
                # so a hand that never shows would have no reason given
                src.status = f"error: {type(error).__name__}: {error}"[:120]

        self.conn = leap.Connection()
        self.conn.add_listener(_Listener())
        tmode = getattr(leap.TrackingMode, TRACKING_MODES.get(mode.lower(), "Desktop"))

        def connect():
            try:
                self.conn.connect(auto_poll=True)
                self.conn.set_tracking_mode(tmode)
            except Exception as e:  # noqa: BLE001 — service missing / refused
                self.status = f"{type(e).__name__}: {e}"[:120]

        # kept so a test (or a probe) can wait for the attempt to finish
        self.connecting = threading.Thread(target=connect, name="leap-connect", daemon=True)
        self.connecting.start()

    def _frame(self, hands) -> None:
        """SDK thread: one tracking frame. Two hands of one side (rare,
        briefly, on a crossover) keep the more confident — for the
        features and the skeleton alike, so both are the same hand."""
        out: dict[str, tuple[dict, float]] = {}
        skel: dict[str, dict] = {}
        for h in hands:
            side, conf = _side(h), float(h.confidence)
            if side not in out or conf > out[side][1]:
                out[side] = (features(h), conf)
                try:
                    skel[side] = skeleton(h)
                except Exception:  # noqa: BLE001 — display only: never cost the axes a frame
                    skel.pop(side, None)
        with self._lock:
            self._hands, self._skel = out, skel
            self._seq, self._t = self._seq + 1, self.clock()
        # a tracking frame is proof the tracker is live: an error, a lost
        # service or a lost camera the SDK reported before it (a USB or
        # HDMI re-sync, one callback that raised) is over. Without this the
        # status stayed bad while frames kept coming, `on` stayed false and
        # HandsIO fed the router nothing: the ghost hands drew, but no
        # route moved, in any preset, until the next launch
        self.status = "tracking"

    def latest(self) -> tuple[int, float, dict[str, tuple[dict, float]]]:
        """(frame seq, receipt time, side → (features, confidence))."""
        with self._lock:
            seq, t, hands = self._seq, self._t, self._hands
        if self.clock() - t > STALE_S:
            hands = {}
        return seq, t, hands

    def skeletons(self) -> tuple[int, float, dict[str, dict]]:
        """(frame seq, receipt time, side → `skeleton`), under the same
        lock and the same staleness rule as `latest()`."""
        seq, t, _, skel = self.snapshot()
        return seq, t, skel

    def snapshot(self) -> tuple[int, float, dict, dict]:
        """`latest()` and `skeletons()` of one frame, read under one lock:
        (seq, receipt time, side → (features, confidence), side → skeleton)."""
        with self._lock:
            seq, t, hands, skel = self._seq, self._t, self._hands, self._skel
        if self.clock() - t > STALE_S:
            hands, skel = {}, {}
        return seq, t, hands, skel

    @property
    def on(self) -> bool:
        return self.status in ("connected", "tracking")

    def close(self) -> None:
        try:
            self.conn.disconnect()
        except Exception:  # noqa: BLE001, S110
            pass


# -------------------------------------------------------------- adapter

@dataclass
class AxisState:
    """One axis at run time — never saved."""

    lo: float
    hi: float
    filt: OneEuro = field(default_factory=OneEuro, repr=False)
    follow: Follower = field(default_factory=Follower, repr=False)
    raw: float | None = None      # native value, last frame the hand was seen
    u: float | None = None        # normalized + smoothed, before shaping
    target: float | None = None   # shaped; None while the hand is away
    q: int | None = None          # last value sent to the DAW
    next_ok: float = 0.0          # rate limit: when the next send may go

    @property
    def y(self) -> float | None:
        return self.follow.y

    def norm(self, v: float) -> float:
        span = self.hi - self.lo
        return (v - self.lo) / span if span else 0.0


def pinch_name(side: str, finger: str) -> str:
    """A pinch switch's address name: "right.pinch.index"."""
    return f"{side}.pinch.{finger}"


def grab_name(side: str) -> str:
    """A grab switch's address name: "right.grab"."""
    return f"{side}.grab"


def addresses(axes: list[AxisSettings]) -> list[str]:
    """Every hand lane's address name, in lane order: the axes as
    `[hands] dofs` spells them (`AxisSettings.name`, "left.roll"), then
    "left.present" / "right.present", then the pinch switches
    ("left.pinch.index" … "right.pinch.pinky"), then each hand's dance
    sources ("left.curl.thumb" … "left.flick", then the right's: `DANCE`),
    then the grab switches ("left.grab", "right.grab": `grab_name`).
    The two-hand sources are a scheme of their own: `pair_addresses`."""
    return ([a.name for a in axes] + [f"{s}.present" for s in SIDES]
            + [pinch_name(s, f) for s in SIDES for f in PINCHES]
            + [f"{s}.{k}" for s in SIDES for k in DANCE]
            + [grab_name(s) for s in SIDES])


def _dance_label(kind: str) -> str:
    """A dance lane's short label, after the side's letter: "curl ind",
    "spread", "energy", "flick"."""
    what, _, finger = kind.partition(".")
    return f"{what} {finger[:3]}" if finger else what


def pair_addresses() -> list[str]:
    """The ``hands`` scheme's lanes — the two hands together — by name:
    ``hands:gap``, ``hands:twist`` (`PAIR`)."""
    return list(PAIR)


def default_addresses() -> list[str]:
    """`addresses` on the default layout — `DEFAULTS`' dofs."""
    return addresses(HandSettings.from_config({}).axes)


class Layout:
    """Where each lane sits in the ``hand`` vector — written here once.

    Axes first (in setup order), then one presence lane per hand, then
    the eight pinch switches. A lane is addressed by **name** (decision
    register row 20, audit N7): ``hand:left.roll``, ``hand:right.present``,
    ``hand:left.pinch.index`` (`addresses`); `index` maps each name to
    its lane and is what the adapter publishes as ``router.names["hand"]``,
    so a row keeps its axis whatever order or subset `dofs` lists, and a
    name this rig lacks is dormant. ``hand:<i>`` — the lane at index i —
    still reads, which is why every lane added since goes after the
    switches (the dance sources, plan 24 C4; then the grab switches, C5):
    no older lane moves. The labels and the gate list are published beside
    it (`labels["hand"]`, `gates["hand"]`: the eight pinches, then the two
    grabs); `presence`, `gate`, `dance` and `grab` are the index maps
    `lanes()` and `rests()` fill by. Every count here is derived — a
    caller reads `n`, never a number of its own.

    The two-hand ``hands`` scheme is laid out here too — `pair_names`,
    `pair_addresses`, `pair_index` (``hands:gap``, ``hands:twist``) — a
    vector of its own, fed beside the ``hand`` one (`pair_lanes`).
    """

    __slots__ = ("addresses", "dance", "gate", "gates", "grab", "index", "n", "n_axes",
                 "names", "pair_addresses", "pair_index", "pair_names", "presence")

    def __init__(self, axes: list[AxisSettings]):
        self.n_axes = len(axes)
        self.presence = {s: self.n_axes + i for i, s in enumerate(SIDES)}
        self.gate = {(s, f): self.n_axes + len(SIDES) + i * len(PINCHES) + k
                     for i, s in enumerate(SIDES) for k, f in enumerate(PINCHES)}
        base = self.n_axes + len(SIDES) + len(SIDES) * len(PINCHES)
        self.dance = {(s, k): base + i * len(DANCE) + j
                      for i, s in enumerate(SIDES) for j, k in enumerate(DANCE)}
        base += len(SIDES) * len(DANCE)
        self.grab = {s: base + i for i, s in enumerate(SIDES)}
        self.n = base + len(SIDES)
        self.names = ([a.label for a in axes]
                      + [f"{s[0].upper()} in" for s in SIDES]
                      + [f"{s[0].upper()} {f[:3]}" for s in SIDES for f in PINCHES]
                      + [f"{s[0].upper()} {_dance_label(k)}" for s in SIDES for k in DANCE]
                      + [f"{s[0].upper()} grab" for s in SIDES])
        self.addresses = addresses(axes)
        self.index = {name: i for i, name in enumerate(self.addresses)}
        self.gates = ([(self.gate[(s, f)], self.names[self.gate[(s, f)]])
                       for s in SIDES for f in PINCHES]
                      + [(self.grab[s], self.names[self.grab[s]]) for s in SIDES])
        self.pair_names = list(PAIR)
        self.pair_addresses = pair_addresses()
        self.pair_index = {name: i for i, name in enumerate(self.pair_addresses)}


class HandsIO:
    """Polled once per render frame: source → axes → hand lanes, DAW MIDI.

    `source` is anything with ``latest()`` (tests pass a fake). The DAW
    messages: with `out` (an object with ``send()``, the caller's — a
    test's fake, a tool's port) each frame's go straight to it, and one
    that fails is let go of, never reopened; without one they wait in
    `outbox` for the frame's carrier (`carry`: the host's `hands-daw`
    sink, plan 27 B3), and nothing here opens a port.
    """

    def __init__(self, settings: HandSettings, cfg: dict | None = None, *, source=None,
                 out=None, cal_path: Path | None = None, clock=time.monotonic):
        self.settings = settings
        self.cfg = rig(cfg)
        self.cal_path = cal_path
        self.clock = clock
        cal = load_calibration(cal_path)
        # the interaction box, None for no bounds (the default, an old file)
        self.box: Box | None = load_box(cal_path)
        # the calibration into the shape's units (plan 26 A2), from the box
        # unless the file says otherwise
        self.units: Units = load_units(cal_path)
        self.state = []
        for a in settings.axes:
            lo, hi = default_range(a.side, a.feature)
            c = cal.get(a.name, {})
            self.state.append(AxisState(float(c.get("lo", lo)), float(c.get("hi", hi))))
        self.min_conf = float(self.cfg["min_confidence"])
        if source is None and self.cfg.get("tape"):
            # a recorded tape instead of the camera: its frames, its mode
            source = TapeSource(Path(self.cfg["tape"]), clock)
            self.cfg["mode"] = source.mode
        self.source = source if source is not None else LeapSource(self.cfg["mode"], clock)
        self.layout = Layout(settings.axes)
        self._rests: list[float] | None = None      # the rests vector last published
        self.error = ""
        # the DAW messages: a port of the caller's (`out`, never reopened),
        # else this frame's wait in `outbox` for the carrier (`carry`), which
        # names its port (`daw`) and says why it has none (`daw_error`)
        self.out = out
        self.outbox: list[mido.Message] = []
        self.daw = ""
        self.daw_error = ""
        self.present = {s: False for s in SIDES}
        # the eight pinch switches, whether or not the ratios are axes
        self.gates = {s: {f: Gate() for f in PINCHES} for s in SIDES}
        # the dance sources (plan 24 C4): each hand's, and the pair's
        self.dance = {s: Dance() for s in SIDES}
        self.pair = {k: Smooth() for k in PAIR}
        # the grab switches (plan 24 C5): a closed fist, from the curls
        self.grab = {s: Gate() for s in SIDES}
        self.frame: dict[str, dict | None] = {s: None for s in SIDES}  # native features
        # side → the features of a hand the tracker sees but the box keeps
        # out: absent to everything, drawn hollow on the HANDS page
        self.outside: dict[str, dict | None] = {s: None for s in SIDES}
        # side → `skeleton` for each hand present this frame: display data
        # (the ghost hands), never shaped; empty from a source without one
        self.skeleton: dict[str, dict] = {}
        self.solo: int | None = None      # axis index: only it goes to the DAW
        self.last = ""                    # the last MIDI sent, for the status line
        self._seq = -1
        self._learn_base: list[float | None] | None = None
        # calibration sweep in progress: axis name → raw samples
        self._cal: dict[str, list[float]] | None = None
        # and where the palms went during it, (x, y, z) mm and whose, both
        # hands in one list whatever the dofs: what the box is made from
        self._palm: list[tuple] | None = None       # (x, y, z, side)
        # the box's Schmitt state per hand: was the palm in, last frame it was seen
        self._in_box = {s: False for s in SIDES}
        self._kept = False      # this build's one backup of an old file was made
        self._cal_until = 0.0
        self.cal_note = ""

    @property
    def axes(self) -> list[AxisSettings]:
        return self.settings.axes

    @property
    def lane_names(self) -> list[str]:
        return self.layout.names

    @property
    def status(self) -> str:
        return getattr(self.source, "status", "")

    @property
    def out_name(self) -> str:
        """The DAW port's name: the caller's port's, else the one the
        carrier last sent through (`carry`); "" with none."""
        if self.out is not None:
            return getattr(self.out, "name", "")
        return getattr(self, "daw", "")

    def axis(self, name: str) -> int:
        """Index of "left.pitch" etc.; ValueError when there is none."""
        return [a.name for a in self.axes].index(name)

    def gate_lane(self, side: str, finger: str) -> int:
        """Lane index of one pinch switch."""
        return self.layout.gate[(side, finger)]

    def address(self, i: int) -> str:
        """Lane i as the source address a row names: ``hand:right.roll``."""
        return f"hand:{self.layout.addresses[i]}"

    def held_gate(self, side: str | None = None) -> str | None:
        """The pinch being held right now as a source address, or None.

        This is what lets a learn started while pinching wear the pinch:
        the hand that learned the axis gets asked first, so a left-hand
        move gated by a left-hand thumb is the natural reading.
        """
        order = ([side] + [s for s in SIDES if s != side]) if side else list(SIDES)
        for s in order:
            for f in PINCHES:
                if self.gates[s][f].on:
                    return f"hand:{pinch_name(s, f)}"
        return None

    def lanes(self) -> list[float]:
        """This frame's ``hand`` vector, in `Layout` order. Each axis's
        output y — NaN while its hand is out of the box (or never seen),
        so a routing row lets go and the base returns the frame the hand
        leaves; the spring and `hold` shape only the DAW output
        (`Follower.live`; the catch glide on a returning hand is live).
        Then presence (1 in view, 0 not), the pinch switches (1 closed),
        each hand's dance sources (`DANCE`: NaN while the hand is away,
        or for a reading its source cannot give — no skeleton, no curls),
        and the grab switches (1 a closed fist, 0 open or away)."""
        lay = self._layout()
        out = [math.nan] * lay.n
        out[:lay.n_axes] = [st.y if st.follow.live else math.nan for st in self.state]
        for s in SIDES:
            out[lay.presence[s]] = 1.0 if self.present[s] else 0.0
            for f in PINCHES:
                out[lay.gate[(s, f)]] = 1.0 if self.gates[s][f].on else 0.0
            if self.present[s]:
                for k, v in zip(DANCE, self.dance[s].values()):
                    out[lay.dance[(s, k)]] = v
            out[lay.grab[s]] = 1.0 if self._grabs()[s].on else 0.0
        return out

    def rests(self) -> list[float]:
        """Where each lane idles — the axis's own configured rest, so a
        push row centred on it pushes nothing from an absent hand whatever
        the setup says `rest` is; presence, pinches, the dance sources and
        the grabs 0 (an open, still hand)."""
        lay = self._layout()
        out = [0.0] * lay.n
        out[:lay.n_axes] = [float(a.rest_value) for a in self.axes]
        return out

    def pair_lanes(self) -> list[float]:
        """This frame's ``hands`` vector (`PAIR`: gap, twist), NaN unless
        both hands are present."""
        both = all(self.present[s] for s in SIDES)
        return [self.pair[k].y if both and self.pair[k].y is not None else math.nan
                for k in PAIR]

    def pair_rests(self) -> list[float]:
        """Where the ``hands`` lanes idle: the gap closed, the twist level."""
        return list(PAIR_RESTS)

    def _dances(self, dt: float, t: float, fresh: bool) -> None:
        """Step each hand's dance sources and the pair's from this frame's
        features (`frame`, present hands only) and skeletons."""
        if getattr(self, "dance", None) is None:      # a HandsIO from before a hot reload
            self.dance = {s: Dance() for s in SIDES}
            self.pair = {k: Smooth() for k in PAIR}
        for s in SIDES:
            self.dance[s].step(dt, t, fresh, self.frame[s], self.skeleton.get(s))
            # the grab: from this hand's raw curls; a hand that left drops it
            gate = self._grabs()[s]
            if self.frame[s] is None:
                gate.reset()
            else:
                step_grab(gate, self.dance[s].raw.get("curl"), t)
        left, right = self.frame["left"], self.frame["right"]
        both = left is not None and right is not None
        for k, fn in (("gap", gap), ("twist", twist)):
            self.pair[k].step(dt, fn(left, right) if both else None, PAIR_S, PAIR_S)

    def _grabs(self) -> dict[str, Gate]:
        """The grab switches, made for a HandsIO from before a hot reload."""
        if getattr(self, "grab", None) is None:
            self.grab = {s: Gate() for s in SIDES}
        return self.grab

    def _layout(self) -> Layout:
        """The layout, rebuilt when it is one from before a hot reload
        (no address map, no dance, pair or grab lanes)."""
        if (getattr(self.layout, "pair_index", None) is None
                or getattr(self.layout, "grab", None) is None):
            self.layout = Layout(self.axes)
        return self.layout

    def _publish(self, router) -> None:
        """The layout to the router: the address map, names and switches
        once per router (they only change with the setup, which builds a
        new adapter), the rests only when a rest value moved. `feed` is
        every frame."""
        lay = self._layout()
        names = getattr(router, "names", None)      # None: a router that knows no names
        if router.labels.get("hand") is not lay.names or (
                names is not None and names.get("hand") is not lay.index):
            router.labels["hand"] = lay.names
            # the switches, so the routing UI can offer them without
            # knowing anything about hands
            router.gates["hand"] = lay.gates
            # name → lane: how the router finds `hand:right.roll` (row 20)
            if names is not None:
                names["hand"] = lay.index
        # the two hands together, `hands:gap` / `hands:twist`: a scheme of
        # their own, published the same way — no switches among them
        if router.labels.get("hands") is not lay.pair_names or (
                names is not None and names.get("hands") is not lay.pair_index):
            router.labels["hands"] = lay.pair_names
            router.gates["hands"] = []
            if names is not None:
                names["hands"] = lay.pair_index
        rests = self.rests()
        if rests != self._rests or router.rests.get("hand") is not self._rests:
            self._rests = rests
            router.rests["hand"] = rests
        if router.rests.get("hands") is None:
            router.rests["hands"] = self.pair_rests()

    # ---- per frame ----

    def poll(self, dt: float, learn=None, router=None) -> list[mido.Message]:
        """One render frame. `learn` is the host's armed-param state (a
        learn.Learn: `learning`, `learn_source`) a moved axis completes;
        `router` the routing.Router fed the ``hand`` lanes. Returns this
        frame's DAW messages (for tests and the probe): sent to `out` when
        there is one, else left in `outbox` for the carrier."""
        g = self.settings
        snap = getattr(self.source, "snapshot", None)
        if snap is not None:          # features and skeletons of one frame
            seq, t, hands, skel = snap()
        else:
            (seq, t, hands), skel = self.source.latest(), {}
        now = self.clock()
        fresh = seq != self._seq
        self._seq = seq
        msgs: list[mido.Message] = []
        for s, side in enumerate(SIDES):
            h = hands.get(side)
            # in the box: the tracker has the hand, and its palm is inside
            # the bounds — past a face by BOX_EDGE before a hand that is in
            # goes out, so one on a face does not flicker. No box bounds
            # nothing, and a sweep ignores it, or it could never be swept
            # wider. (getattr: a HandsIO from before a hot reload has none.)
            # The edge's state is the palm's own (`_in_box`), kept through a
            # frame the confidence floor drops, so a dip in confidence cannot
            # put a hand in the edge band out for good; it is forgotten when
            # the tracker has no hand at all.
            tracked = h is not None and h[1] >= self.min_conf
            box = getattr(self, "box", None)
            if getattr(self, "_in_box", None) is None:
                self._in_box = {sd: False for sd in SIDES}
            if h is None:
                self._in_box[side] = False
            elif box is not None:
                self._in_box[side] = inside(box, h[0],
                                            BOX_EDGE if self._in_box[side] else 0.0)
            here = tracked and (box is None or self._cal is not None or self._in_box[side])
            if getattr(self, "outside", None) is None:
                self.outside = {sd: None for sd in SIDES}
            self.outside[side] = h[0] if tracked and not here else None
            palm = getattr(self, "_palm", None)
            if tracked and fresh and self._cal is not None and palm is not None:
                at = tuple(float(h[0].get(c, math.nan)) for c in BOX_AXES)
                if all(math.isfinite(v) for v in at):     # a partial frame is no sample
                    palm.append((*at, side))
            self.frame[side] = h[0] if here else None
            if here != self.present[side]:
                self.present[side] = here
                if self.cfg["presence"] and self.solo is None:
                    msgs.append(mido.Message(
                        "note_on" if here else "note_off",
                        channel=int(self.cfg["channel"]) - 1,
                        note=int(self.cfg["note"]) + s, velocity=127 if here else 0))
            msgs += self._pinches(side, s, here, t)
        self._skeletons(skel)
        self._dances(dt, t, fresh)
        for i, (a, st) in enumerate(zip(self.axes, self.state)):
            h = hands.get(a.side) if self.present[a.side] else None
            if h is None:
                if st.target is not None:
                    st.filt.reset()       # a returning hand starts fresh
                st.target = None
            elif fresh or st.target is None:
                st.raw = h[0][a.feature]
                st.filt.min_cutoff, st.filt.beta = g.smooth, g.response
                u = st.norm(st.raw)
                u = min(1.0, max(0.0, st.filt(1.0 - u if a.invert else u, t)))
                st.u = u
                st.target = shape(u, bipolar=a.bipolar, deadzone=a.deadzone, c=a.curve)
                if self._cal is not None:
                    self._cal[a.name].append(st.raw)
            y = st.follow.step(dt, st.target, attack=a.attack, decay=a.decay,
                               catch_s=g.catch_s, rest=a.rest, rest_value=a.rest_value,
                               return_s=a.return_s, bounce=a.bounce)
            if y is None or a.out == "off" or (self.solo is not None and self.solo != i):
                continue
            if valid(a.out, a.number) or now < st.next_ok:
                continue
            full = FULL[a.out]
            q = quantize(y, st.q, g.steady if full == 127 else HYST_14, full)
            if q != st.q:
                st.q = q
                st.next_ok = now + (1.0 / g.rate if g.rate > 0 else 0.0)
                msgs += encode(a.out, a.channel - 1, a.number, q)
        self._finish_calibration(now)
        if getattr(self, "out", None) is not None:
            self._deliver(msgs, self._send)
        else:
            # the carrier's (the host's hands-daw sink): this frame's only —
            # a frame no one carried is dropped, as a missing port's always was
            self.outbox = msgs
        if router is not None:
            live = getattr(self.source, "on", True)
            router.feed("hand", self.lanes() if live else None)
            router.feed("hands", self.pair_lanes() if live else None)
            self._publish(router)
        if learn is not None:
            self._learn(learn)
        return msgs

    def _skeletons(self, skel: dict) -> None:
        """This frame's skeletons (read with its features, `snapshot`),
        for the hands that are present (the same confidence floor as the
        axes). Raw: no axis's shaping, so the ghost hands never lag or
        drift from the real ones."""
        self.skeleton = {s: skel[s] for s in SIDES if self.present[s] and s in skel}

    def _pinches(self, side: str, s: int, here: bool, t: float) -> list[mido.Message]:
        """Step one hand's four pinch switches; note on/off on each edge.

        The ratios are read straight off the frame rather than through an
        axis, so the switches work whether or not they were chosen as
        dofs. A hand that leaves drops its switches (and sends the note
        off), so nothing is left hanging on in the DAW.
        """
        g, cfg = self.settings, self.cfg
        if not cfg["pinch_gates"]:
            return []
        feats = self.frame[side] or {}
        msgs: list[mido.Message] = []
        for k, f in enumerate(PINCHES):
            gate = self.gates[side][f]
            was = gate.on
            if not here:
                gate.reset()
            else:
                gate.step(feats.get(f"pinch_{f}"), t, close=g.pinch_close,
                          open_=g.pinch_open, hold=g.pinch_hold)
            if gate.on != was and cfg["pinch_notes"] and self.solo is None:
                msgs.append(mido.Message(
                    "note_on" if gate.on else "note_off",
                    channel=int(cfg["channel"]) - 1,
                    note=int(cfg["pinch_note"]) + s * len(PINCHES) + k,
                    velocity=127 if gate.on else 0))
        return msgs

    def _learn(self, learn) -> None:
        """While a param is armed to learn, the axis that has moved
        furthest (≥ LEARN_MOVE) since the learn began takes it — a hand
        moves all its axes at once, so first-to-move won't do. The route
        goes into the loaded preset through `learn.learn_source` (the
        referee and the Replace / Keep prompt as ever); no file is written,
        the preset shows dirty until a save (plan 13 §3.3).

        A learn says what it waits for (plan 17 WP2: `learn.accepts`,
        asked per axis address): under "Learn hand ▸ left" only the left
        hand's axes can win, under "Learn desk" none can; a learn object
        without `accepts` takes any axis, as before."""
        ok = getattr(learn, "accepts", None)
        pid = getattr(learn, "learning", None)
        if pid is None or (ok is not None
                           and not any(ok(self.address(i)) for i in range(len(self.state)))):
            self._learn_base = None
            return
        # a re-arm starts a fresh baseline (`armed_n`: also of the same param and want)
        key = (pid, getattr(learn, "want", None), getattr(learn, "armed_n", None))
        if key != getattr(self, "_learn_key", None):
            self._learn_base, self._learn_key = None, key
        # only a hand counts as movement: an axis whose hand is away reads
        # None, so a return spring can never complete a learn
        ys = [st.y if st.follow.live else None for st in self.state]
        if self._learn_base is None:
            self._learn_base = ys
            return
        moved = [abs(y - b) if y is not None and b is not None
                 and (ok is None or ok(self.address(i))) else 0.0
                 for i, (y, b) in enumerate(zip(ys, self._learn_base))]
        # an axis first seen after the learn began gets its base now
        self._learn_base = [b if b is not None else y for y, b in zip(ys, self._learn_base)]
        best = max(range(len(moved)), key=moved.__getitem__)
        if moved[best] >= LEARN_MOVE:
            self._learn_base = None
            # pinched while learning: the pinch becomes the row's gate, so
            # the same movement means this only while the thumb agrees
            gate = self.held_gate(self.axes[best].side)
            # what the row lands as is the learn's (plan 18 WP3): told whether
            # this axis rests in the middle — its setup now, not the feature
            # table — and the session's depth for a push
            centred = bool(self.axes[best].bipolar)
            depth = float(self.settings.learn_depth)
            learn.learn_source(self.address(best), when=gate, centred=centred, depth=depth)

    # ---- the DAW messages, out ----

    def carry(self, send, name: str = "", error: str = "") -> list[mido.Message]:
        """This frame's DAW messages (`outbox`) handed to `send` — a
        callable taking one message, False when its port is gone (then the
        rest of the frame's are dropped, as a missing port's always were) —
        and the outbox emptied. The host's `hands-daw` sink calls it after
        the frame's hands poll (plan 27 B3); `name` is its port's, for the
        HANDS page (`out_name`), `error` why it has none. Returns what went
        out."""
        msgs, self.outbox = self.outbox, []
        self.daw, self.daw_error = name, error
        return self._deliver(msgs, send)

    def _deliver(self, msgs: list[mido.Message], send) -> list[mido.Message]:
        sent = []
        for m in msgs:
            if not send(m):
                break
            sent.append(m)
        if sent:
            self.last = describe(sent[-1])
        return sent

    def resync(self) -> list[mido.Message]:
        """The DAW's port is back after a gap it did not hear: every axis
        resends its value at its next change-check (this frame's, when the
        carrier asks before the hands poll), and the notes that are on right
        now (presence, pinches) are returned to go out again first."""
        cfg = self.cfg
        for st in self.state:
            st.q, st.next_ok = None, 0.0
        if self.solo is not None:
            return []
        ch = int(cfg["channel"]) - 1
        out: list[mido.Message] = []
        for s, side in enumerate(SIDES):
            if cfg["presence"] and self.present[side]:
                out.append(mido.Message("note_on", channel=ch, note=int(cfg["note"]) + s,
                                        velocity=127))
            if cfg["pinch_gates"] and cfg["pinch_notes"]:
                for k, f in enumerate(PINCHES):
                    if self.gates[side][f].on:
                        out.append(mido.Message(
                            "note_on", channel=ch,
                            note=int(cfg["pinch_note"]) + s * len(PINCHES) + k, velocity=127))
        return out

    def _send(self, m: mido.Message) -> bool:
        """One message to the caller's port (`out`); False when it went
        away under the send — it is let go of and never reopened (the
        caller's)."""
        if self.out is None:
            return False
        try:
            self.out.send(m)
            return True
        except Exception as e:  # noqa: BLE001 — port yanked mid-frame
            self.error = f"send: {e}"[:120]
            _close_port(self.out)
            self.out = None
            return False

    # ---- calibration ----

    @property
    def calibrating(self) -> float:
        """Seconds left in a sweep, 0 when none is running."""
        return max(0.0, self._cal_until - self.clock()) if self._cal is not None else 0.0

    def start_calibration(self, seconds: float = 20.0) -> None:
        self._cal = {a.name: [] for a in self.axes}
        self._palm = []
        self._cal_until = self.clock() + seconds
        self.cal_note = "sweep every axis end to end"

    def cancel_calibration(self) -> None:
        self._cal = None
        self._palm = None
        self.cal_note = "calibration cancelled"

    def _finish_calibration(self, now: float) -> None:
        if self._cal is None or now < self._cal_until:
            return
        seen, self._cal = self._cal, None
        done = 0
        for a, st in zip(self.axes, self.state):
            v = sorted(seen[a.name])
            if len(v) < CAL_MIN_SAMPLES:
                continue
            lo, hi = v[int(0.02 * (len(v) - 1))], v[int(0.98 * (len(v) - 1))]
            if hi - lo > 1e-6:
                st.lo, st.hi = lo, hi
                done += 1
        missed = len(self.axes) - done
        self.cal_note = f"calibrated {done} axes" + (f", {missed} not reached" if missed else "")
        palm, self._palm = getattr(self, "_palm", None), None
        self.cal_note += " · " + self._sweep_box(palm or [])
        self.save_ranges()

    def _sweep_box(self, palm: list[tuple]) -> str:
        """The box from where the palms went in a sweep, and the note
        that says so. Per coordinate, the 2nd–98th percentile of both
        hands' samples together (the ranges' own rule) pushed out by
        BOX_MARGIN — the margin is what lets a hand hold an axis at its
        end stop. A coordinate no hand swept over BOX_MIN_SPAN is left
        open (a sweep that never moved sideways must not make a slot;
        each hand's own travel is what counts, so two still hands held
        apart are not a sweep), and x is made symmetric about the camera,
        so sweeping one hand cannot shut the other out. Too few samples:
        the box stays as it was."""
        if len(palm) < CAL_MIN_SAMPLES:
            return "box left as it was (too few palm samples)"
        pct = lambda v: (v[int(0.02 * (len(v) - 1))], v[int(0.98 * (len(v) - 1))])
        box: Box = {}
        for k, c in enumerate(BOX_AXES):
            lo, hi = pct(sorted(p[k] for p in palm))
            own = [pct(sorted(p[k] for p in palm if p[3] == sd)) for sd in SIDES
                   if any(p[3] == sd for p in palm)]
            if max(b - a for a, b in own) < BOX_MIN_SPAN:
                box[c] = None
            elif c == "x":
                half = max(abs(lo), abs(hi)) + BOX_MARGIN
                box[c] = (-half, half)
            else:
                box[c] = (lo - BOX_MARGIN, hi + BOX_MARGIN)
        is_open = [c for c in BOX_AXES if box[c] is None]
        self.box = box if len(is_open) < len(BOX_AXES) else None
        if self.box is None:
            return "box: open (not swept)"
        if is_open:
            return f"box: {', '.join(is_open)} open (not swept)"
        return "box " + " × ".join(f"{box[c][1] - box[c][0]:.0f}" for c in BOX_AXES) + " mm"

    def reset_ranges(self) -> None:
        for a, st in zip(self.axes, self.state):
            st.lo, st.hi = default_range(a.side, a.feature)
        self.box = None
        self.cal_note = "ranges back to the defaults, box open"
        self.save_ranges()

    def save_ranges(self) -> None:
        """The ranges and the box to hands.json. The first time the file
        there is not this build's (`_old_schema`), it is first kept beside
        itself (`_keep`); a copy that cannot be made is said in `cal_note`
        and never stops the save."""
        if self.cal_path is None:
            return
        try:
            old = None if getattr(self, "_kept", False) else _old_schema(self.cal_path)
            if old is not None:
                bak = _keep(self.cal_path, old)
                self._kept = True       # once: a save that fails must not copy again
                self.cal_note += f" · the old file kept as {bak.name}"
        except OSError as e:
            self.cal_note += f" · no backup of the old file: {e}"[:120]
        try:
            save_calibration(self.cal_path,
                             {a.name: (st.lo, st.hi) for a, st in zip(self.axes, self.state)},
                             getattr(self, "box", None), getattr(self, "units", None))
        except OSError as e:
            self.cal_note = f"save: {e}"[:120]

    def close(self) -> None:
        _close_port(self.out)
        if hasattr(self.source, "close"):
            self.source.close()


def _close_port(port) -> None:
    """Best effort: a dropped or finished port is closed, so a virtual one
    is unregistered rather than left for the next open to find."""
    # bridge._close_port's twin, kept for the caller's injected `out=`: this
    # module may not import the host's bridge.py (tests/test_hands_boundary.py)
    if port is not None and hasattr(port, "close"):
        try:
            port.close()
        except Exception:  # noqa: BLE001, S110
            pass


