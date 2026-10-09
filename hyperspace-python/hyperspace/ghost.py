"""Ghost hands — both tracked hands drawn as 3D hands over the finished frame.

A display for the performer and for newcomers ("my hands are in there"),
not a control source: nothing here feeds the routing table, and the hands'
twelve axes and eight switches are untouched. The skeleton arrives as
plain data (`hands.core.skeleton`, kept by `HandsIO.poll` in
`HandsIO.skeleton` for the hands present this frame); this module draws
it raw — no smoothing, none of the per-axis shaping — so the ghost never
lags or drifts from the real hand.

Its own pass, after everything else (`Renderer._draw_frame`): the scene,
the look-back composite and the FX chain have all written the target
when the hands go on, so no effect, echo or dream ever touches them and
the look-back history (captured from the scene texture) never sees them.
The hands draw opaque, with a depth buffer, into their own framebuffer;
one composite then lays that over the target at `ghost.alpha`, so a
translucent hand shows no overlaps of its own. On an opaque ground the
composite leaves the target's alpha exactly as it was (plan 14 WP1, the
Pepper's Ghost rig); off, the pass does not run at all and the frame is
bit-identical to one without it.

Its own camera: a fixed perspective view, independent of the 4D view's
camera, zoom and instances. Leap space (mm, origin at the camera, the
table in hands/core.py) goes through the tracking mode's basis (`MODES`)
into the *stage* — x right, y up, z toward the performer — and the
camera, behind and above the performer's hands, fits the calibrated box
(the HANDS page's ranges, `<home>/hands.json`; the defaults without one)
padded by a hand's reach, so the box fills the frame.

Leaving the box: a hand that is no longer reported fades out over
FADE_OUT where it was last seen, and fades in over FADE_IN when it comes
back — it neither freezes nor snaps.

The drawn object is swappable (`ghost.style`, plan 21 WP6). `HandPose` is
the data path (stage-space joints and the bones' raw rotations, per hand,
with its fade and colour); a style is a pure function from one pose to
spheres, tubes and triangles (`PARTS`: HANDS — a sphere per joint, a
capsule per bone and a palm — JOINTS, PALMS, CAGE, MARIONETTE), and
`Geometry` draws whichever is picked. The guide is not a style's: `Ghost`
passes its rows to `Geometry.draw` beside the hands'. A skinned mesh is
another parts function, or another class with the same `draw`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import pairwise

import moderngl
import numpy as np

from .glsl import QUAD_VS

GROUP = "ghost"

FADE_IN = 0.10      # s: a hand that enters comes up this fast
FADE_OUT = 0.30     # s: one that leaves fades over this, where it was last seen
PAD = 60.0          # mm around the palm box: the fingers reach past the palm
FOV_Y = 38.0        # degrees, the camera's vertical field of view
ELEVATION = 32.0    # degrees the camera looks down onto the hands
SAMPLES = 4         # MSAA for the hands' own framebuffer
FINGER_R = 0.085    # finger radius as a fraction of palm width, when bones give none
BONE_R = 0.42       # a bone's capsule radius as a fraction of its reported width

# per hand, linear: both near-white — the guide's axes own the colours —
# with a faint cool tint on the left, a light red one on the right
COLOURS = {"left": (0.88, 0.92, 1.00), "right": (1.00, 0.82, 0.78)}

# tracking mode → Leap axes in stage axes: stage = M · leap, rows are the
# stage's x (right), y (up), z (toward the performer). Desktop is the
# table in hands/core.py. Screentop and HMD are not measured: screentop is
# the desktop camera turned over about its z axis (it hangs above the
# hands, looking down); HMD follows the Ultraleap Unity plugin's default
# head mount (+y out of the face, +z down). `ghost.mirror` flips x after.
MODES: dict[str, tuple[tuple[float, float, float], ...]] = {
    "desktop": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "screentop": ((-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "hmd": ((-1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, -1.0, 0.0)),
}

# ------------------------------------------------------------------ params

GUIDES = ["OFF", "BESIDE", "ON HAND"]
STYLES = ["HANDS", "JOINTS", "PALMS", "CAGE", "MARIONETTE"]   # PARTS, in this order

@dataclass
class GhostState:
    """What the ghost.* params write. Session, not performance: see
    `register`."""

    on: bool = False
    alpha: float = 0.6
    mirror: bool = False
    guide: int = 0          # GUIDES: off, a gauge beside each hand, or on the palm
    tethers: bool = False   # with a guide: a labelled line from each routed mark
    style: int = 0          # STYLES: what is drawn from the poses (HANDS, the capsules)


def register(reg, state: GhostState) -> None:
    """ghost.* — session params (params.SESSION_GROUPS): the hands are the
    room's display, like the output's placement, so a preset load never
    switches them off mid-set. They show on the HANDS page and can be
    learned onto a desk button or knob. Only `on` and `alpha` are
    modulatable (a hand or an LFO may drive them); `mirror`, `guide`,
    `tethers` and `style` are settings of the rig and the show — a
    performer's row on the mirror would flip the hands with a hand's move,
    and a style stepping under an LFO would swap the drawn object
    mid-gesture (plan 21 WP5 R12, WP6)."""
    if f"{GROUP}.on" in reg:
        return
    reg.toggle(f"{GROUP}.on", "Ghost hands", lambda: state.on,
               lambda v: setattr(state, "on", bool(v)), group=GROUP,
               tip="Draw both tracked hands over the render, after every effect — "
                   "so a newcomer sees their hands are in there. Needs the tracker on.")
    reg.continuous(f"{GROUP}.alpha", "Ghost opacity", lambda: state.alpha,
                   lambda v: setattr(state, "alpha", float(v)), lo=0.0, hi=1.0,
                   fmt=lambda v: f"{v * 100:.0f}%", group=GROUP,
                   tip="How solid the ghost hands are over the picture.")
    reg.toggle(f"{GROUP}.mirror", "Ghost mirror", lambda: state.mirror,
               lambda v: setattr(state, "mirror", bool(v)), group=GROUP, modulatable=False,
               tip="Flip the ghost hands left for right, the hands only — for a real "
                   "mirror in front of the performer's hands. For a Pepper's Ghost "
                   "glass use Flip X / Flip Y on the OUTPUT page, which mirror the whole "
                   "picture; with an output flip on, leave this off or the hands flip "
                   "twice.")
    reg.enum(f"{GROUP}.guide", "Ghost guide", lambda: state.guide,
             lambda i: setattr(state, "guide", int(i)), GUIDES, group=GROUP,
             modulatable=False,
             tip="What each hand is doing: a ball per axis (x red, y green, z blue), a "
                 "ring per rotation with a dot where the fingers point (pitch, yaw) or "
                 "the palm faces (roll), and the four pinch switches. All six always "
                 "show; the ones the setup routes are brighter and show what the table "
                 "is fed. Beside the hand, or on it.")
    reg.toggle(f"{GROUP}.tethers", "Ghost tethers", lambda: state.tethers,
               lambda v: setattr(state, "tethers", bool(v)), group=GROUP, modulatable=False,
               tip="With a guide on: a line from each routed axis, pinch or grab to a "
                   "label at the edge of the frame naming the params it drives.")
    reg.enum(f"{GROUP}.style", "Ghost style", lambda: getattr(state, "style", 0),
             lambda i: setattr(state, "style", int(i)), STYLES, group=GROUP,
             modulatable=False,
             tip="What is drawn where your hands are: HANDS (capsule hands), JOINTS (a "
                 "bead per joint), PALMS (an orb that swells as the hand opens, a ring, a "
                 "spoke where the fingers point), CAGE (a wire octahedron that turns with "
                 "the palm and breathes with the grip), MARIONETTE (fingertips on strings "
                 "from a bar). The guide and the tethers are the same in every style.")


# ------------------------------------------------------------------ camera

def basis(mode: str, mirror: bool = False) -> np.ndarray:
    """Leap → stage, 3×3, for a tracking mode (desktop when unknown)."""
    m = np.array(MODES.get(str(mode).lower(), MODES["desktop"]), dtype=np.float64)
    if mirror:
        m[0] *= -1.0
    return m


def box_of(source) -> tuple[tuple[float, float], ...]:
    """The palm box in Leap mm, ((x lo, hi), (y …), (z …)).

    For each of x, y and z: the interaction box's bound when the source
    has one (`HandsIO.box`, plan 18 — a hand outside it is absent, so the
    frame is exactly where a hand counts and its ghost fades at the edge).
    Otherwise, as before there was a box: the union over both hands of
    each hand's range — its calibrated range where the setup has that
    axis (`HandsIO.axes` / `.state`, which hold hands.json's ranges),
    hands/core.py's default for that hand where it has not — so a hand is
    in frame whichever axes the setup keeps. Anything without axes gets
    both hands' defaults."""
    # here, not at the top: params (and through it routing) imports this
    # module, and routing must never pull in the hands adapter
    from .hands.core import SIDES, default_range

    axes, state = getattr(source, "axes", None) or (), getattr(source, "state", None) or ()
    have = {(a.side, a.feature): (min(st.lo, st.hi), max(st.lo, st.hi))
            for a, st in zip(axes, state) if st.hi != st.lo}
    bounds = getattr(source, "box", None) or {}
    out = []
    for feat in "xyz":
        if bounds.get(feat) is not None:
            out.append((float(bounds[feat][0]), float(bounds[feat][1])))
            continue
        ranges = [have.get((sd, feat), default_range(sd, feat)) for sd in SIDES]
        out.append((float(min(r[0] for r in ranges)), float(max(r[1] for r in ranges))))
    return tuple(out)


def _look(eye: np.ndarray, at: np.ndarray) -> np.ndarray:
    f = at - eye
    f /= np.linalg.norm(f)
    r = np.cross(f, (0.0, 1.0, 0.0))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    v = np.eye(4)
    v[0, :3], v[1, :3], v[2, :3] = r, u, -f
    v[:3, 3] = -v[:3, :3] @ eye
    return v


def _perspective(fovy: float, aspect: float, near: float, far: float) -> np.ndarray:
    f = 1.0 / math.tan(math.radians(fovy) / 2.0)
    p = np.zeros((4, 4))
    p[0, 0], p[1, 1] = f / aspect, f
    p[2, 2] = (far + near) / (near - far)
    p[2, 3] = 2.0 * far * near / (near - far)
    p[3, 2] = -1.0
    return p


def stage_box(box, m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(lo, hi) of the palm box in the stage, padded by PAD: what the
    camera frames."""
    corners = np.array([(x, y, z) for x in box[0] for y in box[1] for z in box[2]])
    st = corners @ m.T
    return st.min(axis=0) - PAD, st.max(axis=0) + PAD


def camera(box, m: np.ndarray, aspect: float) -> tuple[np.ndarray, np.ndarray]:
    """(view_proj 4×4, eye) for a palm box in Leap mm seen through the
    stage basis `m`: behind the performer's hands and ELEVATION above
    them, looking at the box's centre, as close as it can stand with every
    corner of the padded box in frame."""
    lo, hi = stage_box(box, m)
    centre = (lo + hi) / 2.0
    pad = np.array([(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                    for z in (lo[2], hi[2])]) - centre
    e = math.radians(ELEVATION)
    back = np.array([0.0, math.sin(e), math.cos(e)])      # from the centre toward the eye
    right = np.array([1.0, 0.0, 0.0])
    up = np.cross(back, right)
    ty = math.tan(math.radians(FOV_Y) / 2.0)
    tx = ty * max(aspect, 1e-3)
    # each corner c (relative to the centre) is in frame when its distance
    # along the view, d − c·back, covers its offsets across it
    along = pad @ back
    d = float(np.max(np.maximum(np.abs(pad @ right) / tx, np.abs(pad @ up) / ty) + along))
    eye = centre + back * d
    reach = float(np.linalg.norm(hi - lo))
    near, far = max(d - reach, 5.0), d + reach
    return _perspective(FOV_Y, aspect, near, far) @ _look(eye, centre), eye


# ------------------------------------------------------------------ poses

@dataclass
class HandPose:
    """One hand, ready to draw, in stage space (mm).

    `joints` is (5, 5, 3): per digit (thumb … pinky) its five joints, base
    to tip — or (0, 5, 3) for a palm-only skeleton. `widths` (5, 4) the
    bones' reported widths (0 where unreported). `rots` (5, 4, 4) the
    bones' raw quaternions in Leap space; `basis` takes Leap to stage
    (a skinned mesh composes the two). `palm`, `normal`, `direction` and
    `width` the palm frame; `fade` 0–1; `colour` linear RGB."""

    side: str
    palm: np.ndarray
    normal: np.ndarray
    direction: np.ndarray
    width: float
    joints: np.ndarray
    widths: np.ndarray
    rots: np.ndarray
    basis: np.ndarray
    fade: float = 1.0
    colour: tuple[float, float, float] = (1.0, 1.0, 1.0)
    # the guide drawn with this hand (`guide`): sphere rows (x, y, z, r, rgba)
    # and tube rows (ax, ay, az, bx, by, bz, r, rgba), already coloured
    guide: tuple[list, list] = field(default_factory=lambda: ([], []), repr=False)
    # the tethers drawn from this hand's guide (`tethers`): (anchor in the
    # stage, rgb, label) per routed mark
    tethers: list = field(default_factory=list, repr=False)


def pose(side: str, skel: dict, m: np.ndarray, fade: float = 1.0) -> HandPose:
    """A `hands.core.skeleton` dict as a `HandPose` through basis `m`."""
    from .hands.core import PALM_W  # lazily: see box_of

    v = lambda p: m @ np.asarray(p, dtype=np.float64)
    digits = skel.get("digits") or []
    if digits:
        j = np.array([[d[0]["prev"]] + [b["next"] for b in d] for d in digits], dtype=np.float64)
        joints = j @ m.T
        widths = np.array([[b.get("width", 0.0) for b in d] for d in digits], dtype=np.float64)
        rots = np.array([[b.get("rot", (0, 0, 0, 1)) for b in d] for d in digits],
                        dtype=np.float64)
    else:
        joints = np.zeros((0, 5, 3))
        widths, rots = np.zeros((0, 4)), np.zeros((0, 4, 4))
    return HandPose(side, v(skel["palm"]), v(skel["normal"]), v(skel["direction"]),
                    float(skel.get("width") or PALM_W), joints, widths, rots, m, fade,
                    COLOURS.get(side, (1.0, 1.0, 1.0)))


# ------------------------------------------------------------------ the guide

# what each hand is sending, drawn beside it: the translation axes as balls
# on three lines, the rotations as dots on three gimbal rings. Colours are
# the usual x / y / z = red / green / blue; a ring takes its axis's colour
AXIS_RGB = {"x": (0.95, 0.26, 0.24), "y": (0.30, 0.88, 0.36), "z": (0.32, 0.52, 1.00)}
RING_OF = {"pitch": "x", "yaw": "y", "roll": "z"}     # the axis a rotation turns about
PINCH_RGB = (1.0, 0.85, 0.30)
GRAB_RGB = (0.85, 0.55, 1.00)
GUIDE_LINE_R = 0.8       # mm: the axis lines and rings
GUIDE_BALL_R = 5.5       # mm: a value's ball or dot
GUIDE_SPAN = 0.15        # half an axis, as a fraction of the framed box's width
RING_SEGMENTS = 40


GUIDE_FEATURES = ("x", "y", "z", "roll", "pitch", "yaw", "grab")
PINCH_NAMES = ("index", "middle", "ring", "pinky")
# an axis no routing row uses: drawn grey, thinner and smaller — still moving
UNROUTED_RGB = (0.42, 0.42, 0.44)
UNROUTED_SIZE = 0.6


def routed_rows(router, source) -> dict[str, list[str]] | None:
    """hand lane ("left.roll", "right.pinch.index", …) → the labels of the
    params its enabled performer rows drive, in table order — what the
    hands are actually wired to. None when there is no table to ask."""
    table = getattr(router, "table", None)
    addresses = getattr(getattr(source, "layout", None), "addresses", None)
    if table is None or addresses is None:
        return None
    reg = getattr(router, "reg", None)
    out: dict[str, list[str]] = {}
    for b in table.mods():
        scheme, i = router.lane(b.source)
        if scheme == "hand" and 0 <= i < len(addresses):
            p = reg[b.target] if reg is not None and b.target in reg else None
            label = getattr(p, "label", None) or b.target
            names = out.setdefault(addresses[i], [])
            if label not in names:
                names.append(label)
    return out


def routed_names(router, source) -> set[str] | None:
    """The hand lanes an enabled performer row reads now (`routed_rows`'
    keys); None when there is no table to ask (every value then draws lit)."""
    rows = routed_rows(router, source)
    return None if rows is None else set(rows)


def guide_values(source, side: str, routed: set[str] | None = None
                 ) -> dict[str, tuple[float, float, float, bool]]:
    """feature → (y, lo, hi, routed) for the hand's x y z roll pitch yaw
    and grab — all of them, whatever the setup or the table holds, so the
    guide is the whole picture. An axis the setup has gives its shaped
    output (`AxisState.y`, 0–1, what a row would be fed) over its own
    range; any other feature its native reading (`HandsIO.frame`)
    normalised over hands/core.py's default range for that hand.
    `routed` (`routed_names`) says which a routing row uses; None: all.
    A feature with no value (the hand just left) is absent."""
    from .hands.core import default_range  # lazily: see box_of

    lit = lambda f: routed is None or f"{side}.{f}" in routed
    out = {}
    for a, st in zip(getattr(source, "axes", None) or (), getattr(source, "state", None) or ()):
        y = getattr(st, "y", None)
        if a.side == side and a.feature in GUIDE_FEATURES and y is not None:
            out[a.feature] = (float(y), float(st.lo), float(st.hi), lit(a.feature))
    feats = (getattr(source, "frame", None) or {}).get(side) or {}
    for f in GUIDE_FEATURES:
        v = feats.get(f)
        if f in out or v is None:
            continue
        lo, hi = default_range(side, f)
        u = (float(v) - lo) / (hi - lo) if hi != lo else 0.5
        out[f] = (min(max(u, 0.0), 1.0), float(lo), float(hi), lit(f))
    return out


def guide_pinches(source, side: str) -> list[bool]:
    """The hand's four pinch switches, index … pinky (all open without them)."""
    gates = (getattr(source, "gates", None) or {}).get(side, {})
    return [bool(getattr(gates.get(f), "on", False)) for f in PINCH_NAMES]


def _tone(rgb: tuple, value: tuple | None) -> tuple[tuple, float]:
    """(colour, size) of one value's marks: its own colour at full size
    when a routing row reads it; grey and smaller when nothing does (or
    there is no value) — colour says "this drives something", grey says
    "this is only the hand"."""
    if value is not None and (len(value) < 4 or value[3]):
        return rgb, 1.0
    return UNROUTED_RGB, UNROUTED_SIZE


def guide(side: str, values: dict, pinches: list[bool], centre: np.ndarray, span: float,
          m: np.ndarray, fade: float, anchors: dict | None = None) -> tuple[list, list]:
    """(sphere rows, tube rows) of one hand's guide about `centre` (stage
    mm), each half-axis `span` long, through basis `m` so a ball moves on
    screen the way the hand does.

      x y z        a line per axis (its ends are the axis's range) and a
                   ball at the value: 0 at one end, 1 at the other, ½ in the
                   middle. Move only up and only the green ball moves.
      pitch, yaw   an arc about x / y, a dot where the fingers point; roll an
                   arc about z, a dot where the palm faces. Each arc spans
                   the axis's range (calibrated, else the default) and no
                   more — the reach of the hand — with a tick at neutral;
                   the dot is the value mapped back through that range, so
                   a dead zone or a curve shows as the dot sticking or
                   speeding.
      pinches      four beads under the gauge, lit while a switch is closed.
      grab         a ring beside the beads that closes as the hand does: an
                   open hand a wide ring, a fist a small one round a full ball.

    Routed (a routing row reads it): the axis's own colour, full size.
    Not routed: grey, thinner and smaller — still moving (`_tone`).

    `anchors`, when given, is filled with each mark's fixed point (stage
    mm) — never the moving ball — for the tethers: an axis line's outer end,
    an arc's neutral tick (its middle when neutral is out of range), a
    pinch bead, the grab ring's centre, the gauge's centre for presence.
    """
    anchors = {} if anchors is None else anchors
    c = np.asarray(centre, dtype=np.float64)
    e = {k: m @ np.eye(3)[i] for i, k in enumerate("xyz")}      # Leap axes in the stage
    out_x = e["x"] if side == "right" else -e["x"]              # the hand's outward side
    dim = lambda rgb, k: (*(v * k for v in rgb), fade)
    spheres, tubes = [], []
    for k in "xyz":
        rgb, size = _tone(AXIS_RGB[k], values.get(k))
        a, b = c - e[k] * span, c + e[k] * span
        # the line's outer end toward the frame edge the hand's labels sit at
        # (x: the hand's outward side; y, z: their + end), so a tether never
        # crosses its own gauge
        anchors[k] = (c + out_x * span) if k == "x" else b
        tubes.append((*a, *b, GUIDE_LINE_R * size, *dim(rgb, 0.55)))
        spheres += [(*a, 2.0 * GUIDE_LINE_R * size, *dim(rgb, 0.55)),
                    (*b, 2.0 * GUIDE_LINE_R * size, *dim(rgb, 0.55))]
        if k in values:
            u = values[k][0] * 2.0 - 1.0
            spheres.append((*(c + e[k] * span * u), GUIDE_BALL_R * size, *dim(rgb, 1.0)))
    spheres.append((*c, 1.6 * GUIDE_LINE_R, *dim((1.0, 1.0, 1.0), 0.5)))
    anchors["present"] = c
    # the arcs: each in the plane of two directions, neutral at the first
    forward, up, down = -e["z"], e["y"], -e["y"]
    thumb_down = -out_x            # a level palm's thumb side, away from the outward side
    planes = {"pitch": (forward, up),               # fingers up: the dot rises
              "yaw": (forward, out_x),              # fingers outward: the dot goes out
              "roll": (down, thumb_down)}           # thumb up: the palm turns inward
    r = 0.78 * span
    at = lambda deg, n0, n1: c + r * (math.cos(math.radians(deg)) * n0
                                      + math.sin(math.radians(deg)) * n1)
    for name, (n0, n1) in planes.items():
        if name not in values:
            continue
        rgb, size = _tone(AXIS_RGB[RING_OF[name]], values[name])
        y, lo, hi = values[name][:3]
        a0, a1 = min(lo, hi), max(lo, hi)
        n = max(3, round(RING_SEGMENTS * (a1 - a0) / 360.0))
        arc = [at(d, n0, n1) for d in np.linspace(a0, a1, n + 1)]
        tubes += [(*p, *q, GUIDE_LINE_R * size, *dim(rgb, 0.55)) for p, q in pairwise(arc)]
        spheres += [(*arc[0], 2.0 * GUIDE_LINE_R * size, *dim(rgb, 0.55)),     # the reach
                    (*arc[-1], 2.0 * GUIDE_LINE_R * size, *dim(rgb, 0.55))]
        if a0 <= 0.0 <= a1:
            spheres.append((*at(0.0, n0, n1), 1.6 * GUIDE_LINE_R * size, *dim(rgb, 0.8)))
        anchors[name] = at(0.0 if a0 <= 0.0 <= a1 else (a0 + a1) / 2.0, n0, n1)
        spheres.append((*at(lo + y * (hi - lo), n0, n1), 0.8 * GUIDE_BALL_R * size,
                        *dim(rgb, 1.0)))
    for i, closed in enumerate(pinches):
        p = c - e["y"] * span * 1.25 + out_x * span * (-0.45 + 0.3 * i)
        anchors[f"pinch.{PINCH_NAMES[i]}"] = p
        lit = dim(PINCH_RGB, 1.0) if closed else dim(UNROUTED_RGB, 0.6)
        spheres.append((*p, 0.6 * GUIDE_BALL_R, *lit))
    if "grab" in values:
        g = values["grab"][0]
        rgb, size = _tone(GRAB_RGB, values["grab"])
        gc = c - e["y"] * span * 1.25 + out_x * span * 0.9
        anchors["grab"] = gc
        gr = 0.22 * span * (1.0 - 0.7 * g)                   # closes with the hand
        ring = [gc + gr * (math.cos(a) * e["x"] + math.sin(a) * e["y"])
                for a in np.linspace(0.0, 2 * math.pi, RING_SEGMENTS // 2 + 1)]
        tubes += [(*p, *q, GUIDE_LINE_R * size, *dim(rgb, 0.8)) for p, q in pairwise(ring)]
        spheres.append((*gc, (0.2 + 0.8 * g) * 0.7 * GUIDE_BALL_R * size, *dim(rgb, 1.0)))
    return spheres, tubes


# ------------------------------------------------------------------ tethers

TETHER_LABEL_MAX = 34    # characters: a long label is cut with an ellipsis
TETHER_TEXT_H = 0.024    # label cap height as a fraction of the frame's height
TETHER_MARGIN = 0.02     # the labels' distance from the frame's edge, ditto


def tether_rgb(mark: str) -> tuple[float, float, float]:
    """A tether's colour: the mark's own (an axis, its arc's axis, a pinch,
    the grab), white for presence."""
    if mark in AXIS_RGB:
        return AXIS_RGB[mark]
    if mark in RING_OF:
        return AXIS_RGB[RING_OF[mark]]
    if mark.startswith("pinch."):
        return PINCH_RGB
    if mark == "grab":
        return GRAB_RGB
    return (1.0, 1.0, 1.0)


def tethers(side: str, rows: dict[str, list[str]], anchors: dict) -> list:
    """(anchor, rgb, label) for each of the hand's routed marks that the
    guide draws: the label is the params its rows drive, joined. Marks in
    the gauge's order, so the labels stack the way the gauge reads."""
    out = []
    for mark, at in anchors.items():
        names = rows.get(f"{side}.{mark}")
        if not names:
            continue
        text = " · ".join(names)
        if len(text) > TETHER_LABEL_MAX:
            text = text[:TETHER_LABEL_MAX - 1].rstrip() + "…"
        out.append((np.asarray(at, dtype=np.float64), tether_rgb(mark), text))
    return out


def layout_tethers(items: list, view_proj: np.ndarray, size: tuple[int, int],
                   text_w) -> list:
    """Screen layout for one hand's tethers: [(anchor px, label box (x, y,
    w, h), the line's far end px, rgb, text)], y down. The labels stack
    at the frame edge on the hand's side (where its anchors are), sorted
    by their anchors' height so the lines do not cross, centred on them
    and kept inside the frame. `text_w(text, h)` is a label's width."""
    w, h = size
    if not items:
        return []
    th = max(10.0, TETHER_TEXT_H * h)
    row = th * 1.55
    margin = TETHER_MARGIN * h
    px = []
    for at, rgb, text in items:
        c = view_proj @ np.append(at, 1.0)
        if c[3] <= 1e-6:
            continue
        px.append(((c[0] / c[3] + 1.0) * 0.5 * w, (1.0 - c[1] / c[3]) * 0.5 * h, rgb, text))
    if not px:
        return []
    px.sort(key=lambda r: r[1])
    left = sum(r[0] for r in px) / len(px) < w / 2
    total = row * len(px)
    y0 = min(max(sum(r[1] for r in px) / len(px) - total / 2, margin), max(h - margin - total,
                                                                            margin))
    out = []
    for k, (ax, ay, rgb, text) in enumerate(px):
        tw = text_w(text, th)
        y = y0 + k * row + (row - th) / 2
        x = margin if left else w - margin - tw
        end = (x + tw + 0.6 * th, y + th / 2) if left else (x - 0.6 * th, y + th / 2)
        out.append(((ax, ay), (x, y, tw, th), end, rgb, text))
    return out


_FONT_PATHS = (
    ("/System/Library/Fonts/Avenir Next.ttc", 5),
    ("/System/Library/Fonts/Helvetica.ttc", 0),
    ("C:/Windows/Fonts/segoeuib.ttf", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
)


def _font(px: int):
    """A PIL font at `px`: the system face the panel uses where there is
    one, else the Roboto imgui_bundle ships (found by path, not imported),
    else PIL's own."""
    from PIL import ImageFont

    cands = list(_FONT_PATHS)
    try:
        import importlib.util
        spec = importlib.util.find_spec("imgui_bundle")
        for loc in (spec.submodule_search_locations or []) if spec else []:
            cands.append((f"{loc}/assets/fonts/Roboto/Roboto-Bold.ttf", 0))
            cands.append((f"{loc}/assets/fonts/Roboto/Roboto-Regular.ttf", 0))
    except (ImportError, ValueError):
        pass
    for path, index in cands:
        try:
            return ImageFont.truetype(path, px, index=index)
        except OSError:
            continue
    return ImageFont.load_default(px)


TETHER_VS = """
#version 330
in vec2 in_px;       // pixels, y down
in vec2 in_uv;
in vec4 in_col;      // premultiplied
uniform vec2 u_size;
out vec2 v_uv;
out vec4 v_col;
void main() {
    gl_Position = vec4(2.0 * in_px.x / u_size.x - 1.0, 1.0 - 2.0 * in_px.y / u_size.y, 0.0, 1.0);
    v_uv = in_uv;
    v_col = in_col;
}
"""

TETHER_FS = """
#version 330
in vec2 v_uv;
in vec4 v_col;
uniform sampler2D u_text;
uniform int u_textured;
out vec4 f_color;
void main() {
    float a = u_textured != 0 ? texture(u_text, v_uv).r : 1.0;
    f_color = v_col * a;
}
"""


class TetherLabels:
    """The tethers and their labels, drawn flat over the hands in pixels:
    a line from each fixed anchor to its label, the label rasterised once
    (PIL) into a texture and kept while it is in use."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        made: list = []          # all or nothing: released again if a later step raises
        try:
            self.prog = ctx.program(vertex_shader=TETHER_VS, fragment_shader=TETHER_FS)
            made.append(self.prog)
            self.buf = ctx.buffer(reserve=64 * 6 * 8 * 4, dynamic=True)
            made.append(self.buf)
            self.vao = ctx.vertex_array(self.prog, [(self.buf, "2f 2f 4f", "in_px", "in_uv",
                                                     "in_col")])
        except Exception:
            for res in made:
                res.release()
            raise
        self._text: dict[tuple[str, int], tuple[moderngl.Texture, float]] = {}
        self._fonts: dict[int, object] = {}

    def width(self, text: str, h: float) -> float:
        _, aspect = self._label(text, round(h))
        return aspect * h

    def _label(self, text: str, px: int) -> tuple[moderngl.Texture, float]:
        key = (text, px)
        hit = self._text.get(key)
        if hit is not None:
            return hit
        from PIL import Image, ImageDraw

        font = self._fonts.get(px) or self._fonts.setdefault(px, _font(px))
        l, t, r, b = font.getbbox(text)
        pad = max(1, px // 6)
        img = Image.new("L", (max(1, r - l + 2 * pad), max(1, px + 2 * pad)), 0)
        ImageDraw.Draw(img).text((pad - l, pad + (px - (b - t)) / 2 - t), text, fill=255,
                                 font=font)
        tex = self.ctx.texture(img.size, 1, img.tobytes())
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        hit = self._text[key] = (tex, img.size[0] / img.size[1])
        return hit

    def draw(self, layout: list, fade_of: list[float], size: tuple[int, int]) -> None:
        """`layout` from `layout_tethers` per hand, flattened; `fade_of`
        each item's hand fade. Lines first, then the labels."""
        if not layout:
            return
        self.prog["u_size"].value = (float(size[0]), float(size[1]))
        lw = max(1.0, size[1] / 900.0)
        verts = []
        for ((ax, ay), _, (ex, ey), rgb, _), f in zip(layout, fade_of):
            col = (*(v * 0.85 * f * 0.8 for v in rgb), 0.8 * f)
            verts += _quad_line(ax, ay, ex, ey, lw, col)
            verts += _quad_box(ax - 1.8 * lw, ay - 1.8 * lw, 3.6 * lw, 3.6 * lw, col)
        self._render(verts, None)
        for (_, (x, y, w, h), _, rgb, text), f in zip(layout, fade_of):
            tex, aspect = self._label(text, round(h))
            bh = w / aspect
            light = tuple(f * (0.55 * v + 0.45) for v in rgb)
            self._render(_quad_box(x, y + (h - bh) / 2, w, bh, (*light, f), uv=True), tex)
        if len(self._text) > 96:        # labels no longer shown: let them go
            keep = {(t, round(b[3])) for (_, b, _, _, t) in layout}
            for k in [k for k in self._text if k not in keep]:
                self._text.pop(k)[0].release()

    def _render(self, verts: list, tex) -> None:
        if not verts:
            return
        data = np.asarray(verts, dtype="f4")
        self.buf.orphan(max(data.nbytes, self.buf.size))
        self.buf.write(data.tobytes())
        self.prog["u_textured"].value = int(tex is not None)
        if tex is not None:
            tex.use(location=1)
            self.prog["u_text"].value = 1
        self.vao.render(moderngl.TRIANGLES, vertices=len(data))

    def release(self) -> None:
        for tex, _ in self._text.values():
            tex.release()
        self._text.clear()
        for res in (self.vao, self.buf, self.prog):
            res.release()


def _quad_line(ax, ay, bx, by, w, col) -> list:
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy) or 1.0
    nx, ny = -dy / n * w / 2, dx / n * w / 2
    a, b, c, d = (ax + nx, ay + ny), (ax - nx, ay - ny), (bx + nx, by + ny), (bx - nx, by - ny)
    return [(*p, 0.0, 0.0, *col) for p in (a, b, c, b, d, c)]


def _quad_box(x, y, w, h, col, uv: bool = False) -> list:
    corners = ((x, y, 0, 0), (x + w, y, 1, 0), (x, y + h, 0, 1), (x + w, y + h, 1, 1))
    pick = (0, 2, 1, 1, 2, 3)
    return [(c[0], c[1], c[2] if uv else 0.0, c[3] if uv else 0.0, *col)
            for c in (corners[i] for i in pick)]


# ------------------------------------------------------------------ geometry

def _sphere(n_lon: int = 14, n_lat: int = 9) -> np.ndarray:
    """A unit UV sphere as triangles, (n, 3) float32; position = normal."""
    tri = []
    for i in range(n_lat):
        t0, t1 = math.pi * i / n_lat, math.pi * (i + 1) / n_lat
        for k in range(n_lon):
            p0, p1 = 2 * math.pi * k / n_lon, 2 * math.pi * (k + 1) / n_lon
            q = [(math.sin(t) * math.cos(p), math.cos(t), math.sin(t) * math.sin(p))
                 for t, p in ((t0, p0), (t1, p0), (t1, p1), (t0, p1))]
            tri += [q[0], q[1], q[2], q[0], q[2], q[3]]
    return np.array(tri, dtype=np.float32)


def _tube(n: int = 14) -> np.ndarray:
    """A unit open cylinder along +z from 0 to 1, radius 1: (n, 3) float32."""
    tri = []
    for k in range(n):
        a, b = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(b), math.sin(b)
        tri += [(ca, sa, 0), (cb, sb, 0), (cb, sb, 1), (ca, sa, 0), (cb, sb, 1), (ca, sa, 1)]
    return np.array(tri, dtype=np.float32)


SHADE_FS = """
#version 330
in vec3 v_pos;
in vec3 v_n;
in vec4 v_col;
uniform vec3 u_eye;
out vec4 f_color;
void main() {
    vec3 n = normalize(v_n);
    vec3 v = normalize(u_eye - v_pos);
    if (dot(n, v) < 0.0) n = -n;                    // the palm is two-sided
    vec3 l = normalize(vec3(-0.35, 0.8, 0.5));
    float diff = max(dot(n, l), 0.0);
    float rim = pow(1.0 - max(dot(n, v), 0.0), 2.0);
    vec3 rgb = v_col.rgb * (0.28 + 0.62 * diff) + 0.45 * rim * mix(v_col.rgb, vec3(1.0), 0.5);
    // premultiplied by the hand's fade: the composite lays it over at ghost.alpha
    f_color = vec4(min(rgb, vec3(1.0)) * v_col.a, v_col.a);
}
"""

SPHERE_VS = """
#version 330
in vec3 in_unit;
in vec4 in_sphere;   // centre, radius
in vec4 in_col;      // rgb, fade
uniform mat4 u_vp;
out vec3 v_pos;
out vec3 v_n;
out vec4 v_col;
void main() {
    v_pos = in_sphere.xyz + in_sphere.w * in_unit;
    v_n = in_unit;
    v_col = in_col;
    gl_Position = u_vp * vec4(v_pos, 1.0);
}
"""

TUBE_VS = """
#version 330
in vec3 in_unit;
in vec3 in_a;
in vec4 in_b;        // end, radius
in vec4 in_col;
uniform mat4 u_vp;
out vec3 v_pos;
out vec3 v_n;
out vec4 v_col;
void main() {
    vec3 ax = in_b.xyz - in_a;
    vec3 w = normalize(ax);
    vec3 h = abs(w.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0);
    vec3 u = normalize(cross(w, h));
    vec3 v = cross(w, u);
    v_n = u * in_unit.x + v * in_unit.y;
    v_pos = in_a + ax * in_unit.z + in_b.w * v_n;
    v_col = in_col;
    gl_Position = u_vp * vec4(v_pos, 1.0);
}
"""

MESH_VS = """
#version 330
in vec3 in_pos;
in vec3 in_n;
in vec4 in_col;
uniform mat4 u_vp;
out vec3 v_pos;
out vec3 v_n;
out vec4 v_col;
void main() {
    v_pos = in_pos;
    v_n = in_n;
    v_col = in_col;
    gl_Position = u_vp * vec4(in_pos, 1.0);
}
"""

COMPOSITE_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_hands;
uniform float u_alpha;
uniform ivec2 u_flip;        // plan 23 WP1: the output's mirror (0 0: as drawn)
out vec4 f_color;
void main() {
    vec2 uv = v_uv;
    if (u_flip.x != 0) uv.x = 1.0 - uv.x;
    if (u_flip.y != 0) uv.y = 1.0 - uv.y;
    f_color = texture(u_hands, uv) * u_alpha;
}
"""


# ---- the styles: what is drawn from one pose ----
#
# A style is a pure function from one `HandPose` to (spheres, tubes,
# triangles) in the stage (mm): each sphere (centre, r), each tube (a, b,
# r), each triangle three (position, normal). No GL, no colour, no fade —
# `Geometry.draw` gives every part the hand's colour and fade — and no
# guide: `Ghost` hands the guide's rows to `draw` as `extra`, so no style
# knows the guide exists (plan 21 WP6). A palm-only pose (no digits) draws
# a palm in every style.

# openness: the mean fingertip distance from the palm over the palm's
# width, mapped so a fist is 0 and an open hand 1 (the tests' synthetic
# hands measure 0.42 and 1.37 on this scale)
FIST_REACH = 0.45
OPEN_REACH = 1.35
WIRE_R = 0.03        # a wire's radius (the cage, the palm's ring), as a fraction of palm width
STRING_R = 0.025     # a marionette string's
RING_SEG = 24


def openness(p: HandPose) -> float:
    """0 for a fist, 1 for an open hand, from the pose alone (no route,
    no new data); 0.5 for a palm-only pose, which has no fingertips."""
    if not len(p.joints):
        return 0.5
    reach = float(np.mean(np.linalg.norm(p.joints[:, 4] - p.palm, axis=1)))
    u = (reach / max(p.width, 1e-6) - FIST_REACH) / (OPEN_REACH - FIST_REACH)
    return min(max(u, 0.0), 1.0)


def palm_frame(p: HandPose) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(forward, side, normal), unit, in the stage: where the fingers
    point, across the palm, out of it."""
    n = p.normal / max(np.linalg.norm(p.normal), 1e-9)
    f = p.direction / max(np.linalg.norm(p.direction), 1e-9)
    s = np.cross(n, f)
    s /= max(np.linalg.norm(s), 1e-9)
    return f, s, n


def _orb(p: HandPose) -> tuple:
    """The palm orb every style but HANDS draws for a palm-only pose."""
    return (p.palm, 0.32 * p.width)


def _loop(points: list, r: float) -> list:
    """Tubes joining `points` round in a closed loop."""
    return [(a, b, r) for a, b in pairwise([*points, points[0]])]


def hands_parts(p: HandPose) -> tuple[list, list, list]:
    """HANDS, the capsule hands: a sphere per joint, a capsule per bone, a
    palm (an ellipse in the palm's plane for a palm-only pose)."""
    col_r = FINGER_R * p.width
    spheres, tubes, tris = [], [], []
    n = p.normal / max(np.linalg.norm(p.normal), 1e-9)
    if len(p.joints):
        for d in range(len(p.joints)):
            for b in range(4):
                w = p.widths[d, b]
                r = BONE_R * w if w > 0 else col_r
                if d == 0 and b == 0:
                    continue            # the thumb's metacarpal has no length
                a, e = p.joints[d, b], p.joints[d, b + 1]
                if np.linalg.norm(e - a) > 1e-3:
                    tubes.append((a, e, r))
                spheres.append((e, r))
                if b == 0 or (d == 0 and b == 1):
                    spheres.append((a, r))
        # the palm: the four finger metacarpals' bases and knuckles
        ring = ([p.joints[d, 0] for d in (1,)] + [p.joints[d, 1] for d in (1, 2, 3, 4)]
                + [p.joints[d, 0] for d in (4, 3, 2)])
    else:
        # palm only: an ellipse in the palm's plane, a palm long and wide
        f = p.direction / max(np.linalg.norm(p.direction), 1e-9)
        s = np.cross(n, f)
        ring = [p.palm + f * 0.55 * p.width * math.cos(a) + s * 0.5 * p.width * math.sin(a)
                for a in np.linspace(0.0, 2 * math.pi, 16, endpoint=False)]
    c = np.mean(ring, axis=0)
    for k in range(len(ring)):
        tris.append(((c, n), (ring[k], n), (ring[(k + 1) % len(ring)], n)))
    if len(p.joints):
        # the web between the thumb and the index metacarpal
        tb, tm = p.joints[0, 1], p.joints[0, 2]
        ib, ik = p.joints[1, 0], p.joints[1, 1]
        tris.append(((tb, n), (tm, n), (ik, n)))
        tris.append(((tb, n), (ik, n), (ib, n)))
    return spheres, tubes, tris


def joints_parts(p: HandPose) -> tuple[list, list, list]:
    """JOINTS: a bead per joint and nothing between them — small at the
    wrist, a little larger at the knuckles, largest at the fingertips —
    and one at the palm."""
    w = p.width
    if not len(p.joints):
        return [_orb(p)], [], []
    spheres = [(p.palm, 0.17 * w)]
    sizes = (0.055, 0.075, 0.065, 0.07, 0.12)       # base, knuckle, two mid joints, tip
    for d in range(len(p.joints)):
        for j in range(5):
            if d == 0 and j == 0:
                continue            # the thumb's metacarpal has no length: one bead there
            spheres.append((p.joints[d, j], sizes[j] * w))
    return spheres, [], []


def palms_parts(p: HandPose) -> tuple[list, list, list]:
    """PALMS: an orb at the palm that swells as the hand opens, a wire ring
    in the palm's plane round it, and a spoke out of the ring's edge where
    the fingers point, a bead at its end."""
    w, (f, s, _) = p.width, palm_frame(p)
    o = openness(p)
    orb = (0.2 + 0.2 * o) * w
    ring_r = 0.78 * w
    ring = [p.palm + ring_r * (math.cos(a) * f + math.sin(a) * s)
            for a in np.linspace(0.0, 2 * math.pi, RING_SEG, endpoint=False)]
    tip = p.palm + f * (ring_r + 0.55 * w)
    spheres = [(p.palm, orb), (tip, 0.09 * w)]
    tubes = [*_loop(ring, WIRE_R * w), (p.palm + f * orb, tip, 1.5 * WIRE_R * w)]
    return spheres, tubes, []


# the octahedron: its six corners as (forward, side, normal) signs, the
# twelve edges between them, the eight faces
_OCTA = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
_OCTA_EDGES = tuple((a, b) for a in range(6) for b in range(a + 1, 6) if a // 2 != b // 2)
_OCTA_FACES = tuple((a, b, c) for a in (0, 1) for b in (2, 3) for c in (4, 5))


def cage_parts(p: HandPose) -> tuple[list, list, list]:
    """CAGE: a wire octahedron round the hand, set in the palm's frame so it
    turns with the palm, longest where the fingers point; it breathes with
    the grip (a fist pulls it in, an open hand pushes it out). Inside, at
    the palm, a small solid octahedron turned an eighth of a turn."""
    w, (f, s, n) = p.width, palm_frame(p)
    k = (0.55 + 0.55 * openness(p)) * w
    centre = p.palm + f * 0.3 * w
    axes = (f * 1.25 * k, s * k, n * 0.75 * k)
    corners = [centre + sum(c * a for c, a in zip(sign, axes)) for sign in _OCTA]
    spheres = [(c, 0.05 * w) for c in corners]
    tubes = [(corners[a], corners[b], WIRE_R * w) for a, b in _OCTA_EDGES]
    # the little polytope: the same shape, solid, turned about the normal
    g = 0.17 * w
    fa, sa = (f + s) / math.sqrt(2.0), (s - f) / math.sqrt(2.0)
    inner = [p.palm + g * (c[0] * fa + c[1] * sa + 0.8 * c[2] * n) for c in _OCTA]
    tris = []
    for a, b, c in _OCTA_FACES:
        pa, pb, pc = inner[a], inner[b], inner[c]
        nn = np.cross(pb - pa, pc - pa)
        nn /= max(np.linalg.norm(nn), 1e-9)
        tris.append(((pa, nn), (pb, nn), (pc, nn)))
    if not len(p.joints):
        spheres.append(_orb(p))
    return spheres, tubes, tris


def marionette_parts(p: HandPose) -> tuple[list, list, list]:
    """MARIONETTE: a bead per fingertip, each hung on a string from a
    control bar above the hand — the bar level, across the hand, a short
    crossbar along it where the fingers point, a string from its front to
    the back of the palm."""
    w, (f, s, _) = p.width, palm_frame(p)
    up = np.array([0.0, 1.0, 0.0])
    across = s - up * float(s @ up)
    if np.linalg.norm(across) < 1e-3:
        across = np.array([1.0, 0.0, 0.0])
    across /= np.linalg.norm(across)
    ahead = np.cross(across, up)
    if float(ahead @ f) < 0.0:
        ahead = -ahead
    tips = list(p.joints[:, 4]) if len(p.joints) else []
    top = max([float(p.palm[1]), *(float(t[1]) for t in tips)])
    bar_c = np.array([p.palm[0], top + 1.6 * w, p.palm[2]])
    half = 0.7 * w
    ends = (bar_c - across * half, bar_c + across * half)
    front = bar_c + ahead * 0.45 * w
    spheres = [(ends[0], 0.07 * w), (ends[1], 0.07 * w), (front, 0.06 * w)]
    tubes = [(ends[0], ends[1], 0.045 * w), (bar_c - ahead * 0.45 * w, front, 0.04 * w)]
    for t in tips:
        u = min(max(float((t - bar_c) @ across), -half), half)
        hook = bar_c + across * u
        tubes.append((hook, t, STRING_R * w))
        spheres.append((t, 0.11 * w))
    # the palm's own string, from the crossbar's front
    tubes.append((front, p.palm, STRING_R * w))
    spheres.append(_orb(p) if not tips else (p.palm, 0.1 * w))
    return spheres, tubes, []


PARTS = (hands_parts, joints_parts, palms_parts, cage_parts, marionette_parts)


def style_parts(i) -> object:
    """The parts function of style index `i` (HANDS for anything else)."""
    try:
        k = int(i)
    except (TypeError, ValueError):
        return hands_parts
    return PARTS[k] if 0 <= k < len(PARTS) else hands_parts


def _clear_depth(ctx: moderngl.Context, fbo: moderngl.Framebuffer) -> None:
    """Clear `fbo`'s depth and leave its colour: the clear with the colour
    masked (moderngl applies a framebuffer's mask when it is bound)."""
    fbo.color_mask = (False, False, False, False)
    try:
        fbo.use()
        ctx.clear(depth=1.0)
    finally:
        fbo.color_mask = (True, True, True, True)
        fbo.use()


class Geometry:
    """Draws poses as a style's parts — spheres, tubes and triangles,
    built per frame (a few dozen instances) — into whatever is bound, with
    the depth test on.

    `draw(poses, view_proj, eye, parts, extra)`: `parts` is one of
    `PARTS` (None draws no hand at all), `extra` per pose the rows drawn
    with it, already coloured (the guide's, from `Ghost`)."""

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._unit_s = ctx.buffer(_sphere().tobytes())
        self._unit_t = ctx.buffer(_tube().tobytes())
        self._n_s, self._n_t = len(_sphere()), len(_tube())
        self._inst_s = ctx.buffer(reserve=64 * 8 * 4, dynamic=True)
        self._inst_t = ctx.buffer(reserve=64 * 11 * 4, dynamic=True)
        self._mesh = ctx.buffer(reserve=128 * 10 * 4, dynamic=True)
        self._build()

    def _build(self) -> None:
        ctx = self.ctx
        made: list = []
        try:
            ps = ctx.program(vertex_shader=SPHERE_VS, fragment_shader=SHADE_FS)
            made.append(ps)
            pt = ctx.program(vertex_shader=TUBE_VS, fragment_shader=SHADE_FS)
            made.append(pt)
            pm = ctx.program(vertex_shader=MESH_VS, fragment_shader=SHADE_FS)
            made.append(pm)
            vs = ctx.vertex_array(ps, [(self._unit_s, "3f", "in_unit"),
                                       (self._inst_s, "4f 4f/i", "in_sphere", "in_col")])
            made.append(vs)
            vt = ctx.vertex_array(pt, [(self._unit_t, "3f", "in_unit"),
                                       (self._inst_t, "3f 4f 4f/i", "in_a", "in_b", "in_col")])
            made.append(vt)
            vm = ctx.vertex_array(pm, [(self._mesh, "3f 3f 4f", "in_pos", "in_n", "in_col")])
        except Exception:
            for res in made:
                res.release()
            raise
        self.progs, self.vaos = (ps, pt, pm), (vs, vt, vm)

    def on_reload(self) -> None:
        old = (*self.vaos, *self.progs)
        self._build()
        for res in old:
            res.release()

    def draw(self, poses: list[HandPose], view_proj: np.ndarray, eye: np.ndarray,
             parts=hands_parts, extra: list | None = None) -> None:
        """Each pose as `parts` draws it, in its colour and fade, then the
        pose's `extra` rows — (sphere rows, tube rows), aligned with `poses`
        — in the same instanced draws, so they share the depth test. With
        `parts` None only the extra rows draw."""
        s_rows, t_rows, m_rows = [], [], []
        for k, p in enumerate(poses):
            if parts is not None:
                col = (*p.colour, float(p.fade))
                spheres, tubes, tris = parts(p)
                s_rows += [(*c, r, *col) for c, r in spheres]
                t_rows += [(*a, *b, r, *col) for a, b, r in tubes]
                for tri in tris:
                    m_rows += [(*q, *nn, *col) for q, nn in tri]
            if extra is not None and k < len(extra):
                s_rows += extra[k][0]
                t_rows += extra[k][1]
        vp = np.asarray(view_proj, dtype="f4").T.tobytes()     # column-major
        ey = tuple(float(x) for x in eye)
        for prog in self.progs:
            prog["u_vp"].write(vp)
            prog["u_eye"].value = ey
        for rows, buf, vao, verts in ((m_rows, self._mesh, self.vaos[2], None),
                                      (s_rows, self._inst_s, self.vaos[0], self._n_s),
                                      (t_rows, self._inst_t, self.vaos[1], self._n_t)):
            if not rows:
                continue
            data = np.asarray(rows, dtype="f4")
            buf.orphan(max(data.nbytes, buf.size))
            buf.write(data.tobytes())
            if verts is None:
                vao.render(moderngl.TRIANGLES, vertices=len(data))
            else:
                vao.render(moderngl.TRIANGLES, vertices=verts, instances=len(data))

    def release(self) -> None:
        for res in (*self.vaos, *self.progs, self._unit_s, self._unit_t, self._inst_s,
                    self._inst_t, self._mesh):
            res.release()


class CapsuleHands(Geometry):
    """The first geometry's name, kept: a `Geometry` that draws HANDS."""

    parts = staticmethod(hands_parts)


# ------------------------------------------------------------------ the pass

@dataclass
class _Side:
    fade: float = 0.0
    skel: dict | None = field(default=None, repr=False)    # last seen


class Ghost:
    """The ghost-hands pass: `layer` renders the hands once a frame into
    their own texture (`tex`), `composite` lays it over a target — after
    the FX chain, onto each output that shows the hands (plan 21 WP1).
    `draw` is the two together, onto one target.

    `source` is anything with ``.skeleton`` (side → `hands.core.skeleton`
    for the hands present this frame) — the HandsIO, set by the app when
    the tracker is on; ``.cfg["mode"]`` and ``.axes`` / ``.state`` give the
    tracking mode and the calibrated box when it has them. None (no
    tracker): nothing draws."""

    def __init__(self, ctx: moderngl.Context, state: GhostState | None = None):
        self.ctx = ctx
        self.state = state if state is not None else GhostState()
        self.source = None
        self.router = None       # the routing table, for which values the guide lights
        self.sides = {"left": _Side(), "right": _Side()}
        self.geometry: Geometry | None = None          # built on first use
        self._comp: moderngl.Program | None = None
        self._comp_vao: moderngl.VertexArray | None = None
        self._t: float | None = None
        self.size = (0, 0)
        self._tex: moderngl.Texture | None = None
        self._fbo: moderngl.Framebuffer | None = None     # on the texture
        self._msaa: moderngl.Framebuffer | None = None    # multisampled, with depth
        self._res: list = []
        self._shown = False      # `layer` drew this frame: `tex` is the layer
        # the readout layer (plan 21 WP2): the guide and the tethers apart
        # from the hands, made on first use, only while a pipeline puts the
        # hands through the effects with the guide on
        self._ro_size = (0, 0)
        self._ro_tex: moderngl.Texture | None = None
        self._ro_fbo: moderngl.Framebuffer | None = None
        self._ro_msaa: moderngl.Framebuffer | None = None
        self._ro_res: list = []
        self._ro_shown = False
        # why the pass could not build or draw — the first reason, kept until
        # the ghost is switched off or the module reloads (the HANDS page
        # shows it); `_build_failed` alone stops the build being retried
        self.error = ""
        self._build_failed = False
        self._labels: TetherLabels | None = None    # the tethers' text, on first use
        self._labels_failed = False                 # …which would not build or draw

    # ---- per frame ----

    def step(self, t: float) -> list[tuple[str, dict, float]]:
        """Advance the fades to `t` (the renderer's clock) and return
        (side, skeleton, fade) for every hand still visible."""
        dt = 0.0 if self._t is None else min(max(t - self._t, 0.0), 0.1)
        self._t = t
        src = self.source
        skel = (getattr(src, "skeleton", None) or {}) if src is not None else {}
        out = []
        for side, sd in self.sides.items():
            now = skel.get(side)
            if now is not None:
                # the first frame counts as one: a hand is never invisible on arrival
                sd.skel = now
                sd.fade = min(1.0, sd.fade + max(dt, 1.0 / 60.0) / FADE_IN)
            else:
                sd.fade = max(0.0, sd.fade - dt / FADE_OUT)
            if sd.fade > 0.0 and sd.skel is not None:
                out.append((side, sd.skel, sd.fade))
        return out

    def poses(self, t: float, aspect: float):
        """This frame's poses and camera, or None when nothing would show."""
        st = self.state
        if not st.on or st.alpha <= 0.0 or self.source is None:
            for sd in self.sides.values():           # off: no stale hand on the way back
                sd.fade, sd.skel = 0.0, None
            self._t = None
            # …and a failed draw is forgotten: switching the ghost off and
            # on again tries it afresh (a build the driver refused waits
            # for a reload). getattr: a Ghost from before the flag existed
            if not getattr(self, "_build_failed", False):
                self.error = ""
            self._labels_failed = False
            return None
        seen = self.step(t)
        if not seen:
            return None
        cfg = getattr(self.source, "cfg", None) or {}
        m = basis(cfg.get("mode", "desktop"), st.mirror)
        box = box_of(self.source)
        vp, eye = camera(box, m, aspect)
        poses = [pose(side, sk, m, fade) for side, sk, fade in seen]
        if st.guide:
            lo, hi = stage_box(box, m)
            span = GUIDE_SPAN * float(hi[0] - lo[0])
            mid = (lo + hi) / 2.0
            rows = routed_rows(self.router, self.source)
            routed = None if rows is None else set(rows)
            for p in poses:
                if st.guide == 1:        # beside: a fixed gauge low on the hand's side
                    # (the hand's side of the room, through the basis: every
                    # mode maps Leap x onto the stage's x, mirror included)
                    out = m @ np.array([1.0 if p.side == "right" else -1.0, 0.0, 0.0])
                    centre = mid + out * 0.36 * float(hi[0] - lo[0]) \
                        - np.array([0.0, 0.2 * float(hi[1] - lo[1]), 0.0])
                else:                    # on the hand: about the palm
                    centre = p.palm
                anchors: dict = {}
                p.guide = guide(p.side, guide_values(self.source, p.side, routed),
                                guide_pinches(self.source, p.side), centre, span, m, p.fade,
                                anchors)
                if st.tethers and rows:
                    p.tethers = tethers(p.side, rows, anchors)
        return poses, vp, eye

    def draw(self, target: moderngl.Framebuffer, vp: tuple[int, int, int, int], t: float,
             opaque: bool = True) -> bool:
        """The hands over `target`'s viewport `vp`, if any show: `layer` at
        the viewport's size, then `composite`. Leaves `target` bound with
        that viewport, a raise included; touches no GL state when nothing
        draws. True when it drew."""
        vx, vy, vw, vh = vp
        try:
            if not self.layer((max(vw, 1), max(vh, 1)), t):
                return False
        except BaseException:
            self.ctx.disable(moderngl.DEPTH_TEST)
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            target.use()
            self.ctx.viewport = (vx, vy, vw, vh)
            raise
        self.composite(target, vp, opaque)
        return True

    @property
    def tex(self) -> moderngl.Texture | None:
        """The hands' layer `layer` drew last (premultiplied by each hand's
        fade, frame-sized, the guide and the tethers in it unless `readout`
        holds them); None when it drew nothing. Valid until the next
        `layer`."""
        return self._tex if getattr(self, "_shown", False) else None

    @property
    def readout(self) -> moderngl.Texture | None:
        """The readout layer (plan 21 WP2, fork F3): the guide and the
        tethers' labels, apart from the hands so the effects never bend
        them — drawn by `layer(…, readout=True)` only while the guide is on;
        None otherwise (then they are in `tex`, as they always were)."""
        return self._ro_tex if getattr(self, "_ro_shown", False) else None

    def layer(self, size: tuple[int, int], t: float, readout: bool = False) -> bool:
        """Render the hands' layer at `size` (the frame's) for time `t`:
        the fades stepped, the hands drawn opaque with depth into their own
        framebuffer, the tethers flat over them, resolved into `tex`.
        False — nothing drawn, no GL state touched when nothing shows —
        when the ghost is off, no hand shows, or the programs or the
        target would not build (`error` says why). Called once a frame;
        `composite` lays it over as many targets as want it. Leaves its own
        framebuffer bound: the caller binds its target next (a raise
        included — `draw` and `Renderer._draw_frame` do).

        `readout` (a pipeline will put the hands through the effects): the
        guide and the tethers go into a second layer, `readout`, instead —
        the hands drawn there depth-only first, so an ON HAND gauge is
        still hidden behind the palm, then the guide's spheres and tubes,
        then the tethers. Only while the guide is on; with it off, or if
        that layer will not build, the one layer as ever."""
        self._shown = self._ro_shown = False
        w, h = max(int(size[0]), 1), max(int(size[1]), 1)
        got = self.poses(t, w / h)
        if got is None:
            return False
        poses, view_proj, eye = got
        ctx = self.ctx
        if self.geometry is None and not self._build():
            return False
        if not self._ensure((w, h)):
            return False                 # nothing bound, nothing drawn: no layer
        split = (readout and any(p.guide[0] or p.guide[1] or p.tethers for p in poses)
                 and self._ensure_readout((w, h)))
        # the style draws the hands; the guide's rows ride with each pose as
        # `extra` (no style knows the guide exists, plan 21 WP6).
        # getattr: a GhostState from before the style existed
        parts = style_parts(getattr(self.state, "style", 0))
        guides = [p.guide for p in poses]
        try:
            draw_fbo = self._msaa if self._msaa is not None else self._fbo
            draw_fbo.use()
            ctx.viewport = (0, 0, *self.size)
            ctx.clear(0.0, 0.0, 0.0, 0.0, depth=1.0)
            ctx.disable(moderngl.BLEND)
            ctx.enable(moderngl.DEPTH_TEST)
            # HANDS draws the guide in the same depth-tested pass, as ever (an
            # ON HAND gauge partly behind the palm). Any other style puts a
            # solid at the palm far bigger than a guide ball, so its guide
            # goes over it: the style first, then the depth cleared, then
            # the guide — the guide reads the same in every style
            over = parts is not hands_parts
            self.geometry.draw(poses, view_proj, eye, parts,
                               None if split or over else guides)
            if over and not split and any(g[0] or g[1] for g in guides):
                _clear_depth(ctx, draw_fbo)
                ctx.viewport = (0, 0, *self.size)
                self.geometry.draw(poses, view_proj, eye, None, guides)
            ctx.disable(moderngl.DEPTH_TEST)
            if not split and any(p.tethers for p in poses):
                self._draw_tethers(poses, view_proj)
            if self._msaa is not None:
                ctx.copy_framebuffer(self._fbo, self._msaa)
            if split:
                ro = self._ro_msaa if self._ro_msaa is not None else self._ro_fbo
                ro.use()
                ctx.viewport = (0, 0, w, h)
                ctx.clear(0.0, 0.0, 0.0, 0.0, depth=1.0)
                ctx.enable(moderngl.DEPTH_TEST)
                # the hands into the depth buffer only: moderngl applies a
                # framebuffer's colour mask when it is bound, hence the use()s.
                # Only for HANDS: any other style's guide is drawn over it
                if not over:
                    ro.color_mask = (False, False, False, False)
                    try:
                        ro.use()
                        self.geometry.draw(poses, view_proj, eye, parts)
                    finally:
                        ro.color_mask = (True, True, True, True)
                        ro.use()
                ctx.viewport = (0, 0, w, h)
                self.geometry.draw(poses, view_proj, eye, None, guides)
                ctx.disable(moderngl.DEPTH_TEST)
                if any(p.tethers for p in poses):
                    self._draw_tethers(poses, view_proj)
                if self._ro_msaa is not None:
                    ctx.copy_framebuffer(self._ro_fbo, self._ro_msaa)
        finally:
            # a raise anywhere above leaves the state the frame's other
            # passes expect: blending on, as the scene pass sets it
            ctx.disable(moderngl.DEPTH_TEST)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self._shown, self._ro_shown = True, bool(split)
        return True

    def composite(self, target: moderngl.Framebuffer, vp: tuple[int, int, int, int],
                  opaque: bool = True, flip: tuple[bool, bool] = (False, False)) -> bool:
        """Lay the layer `layer` drew over `target`'s rect `vp` at
        `ghost.alpha`, premultiplied, scaled to the rect (1:1 when it is
        the layer's size). On an opaque ground the target's alpha is left
        exactly as it is (plan 14 WP1); on overlay's see-through ground the
        hands add their coverage to it. Leaves `target` bound with `vp`
        and blending on, a raise included. False when there is no layer.
        `flip` (x, y) mirrors it inside `vp` — an output's mirror (plan 23
        WP1), passed only at the output stage, never into the effects'
        input (hands-through: the frame is flipped whole when shown)."""
        return self._lay(self.tex, target, vp, opaque, flip)

    def composite_readout(self, target: moderngl.Framebuffer,
                          vp: tuple[int, int, int, int], opaque: bool = True,
                          flip: tuple[bool, bool] = (False, False)) -> bool:
        """`composite` for the readout layer, when there is one."""
        return self._lay(self.readout, target, vp, opaque, flip)

    def _lay(self, tex, target, vp, opaque: bool,
             flip: tuple[bool, bool] = (False, False)) -> bool:
        if tex is None or self._comp is None:
            return False
        ctx = self.ctx
        try:
            target.use()
            ctx.viewport = tuple(vp)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = ((moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA, moderngl.ZERO,
                               moderngl.ONE) if opaque else
                              (moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA, moderngl.ONE,
                               moderngl.ONE_MINUS_SRC_ALPHA))
            tex.use(location=0)
            self._comp["u_hands"].value = 0
            self._comp["u_alpha"].value = float(self.state.alpha)
            self._comp["u_flip"].value = (int(bool(flip[0])), int(bool(flip[1])))
            self._comp_vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            target.use()
            ctx.viewport = tuple(vp)
        return True

    def _draw_tethers(self, poses: list[HandPose], view_proj: np.ndarray) -> None:
        """The tethers, flat over the hands, into the bound hands' framebuffer
        (premultiplied, so the composite treats them like the hands).

        No labels, never no hands: a program, a font or a label that will
        not build or draw stops the tethers — the hands still composite —
        says why once on `error` (the HANDS page shows it) and is not
        tried again until the ghost is switched off or the module reloads.
        `ghost.tethers` is left as the performer set it: the render stack
        only reads parameters (ARCHITECTURE §3)."""
        if getattr(self, "_labels_failed", False):   # getattr: a pre-reload Ghost
            return
        ctx = self.ctx
        try:
            if self._labels is None:
                self._labels = TetherLabels(ctx)
            layout, fades = [], []
            for p in poses:
                got = layout_tethers(p.tethers, view_proj, self.size, self._labels.width)
                layout += got
                fades += [p.fade] * len(got)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA
            self._labels.draw(layout, fades, self.size)
        except Exception as e:  # noqa: BLE001 — no labels, never no hands
            self._labels_failed = True
            if not self.error:
                self.error = f"ghost tethers: {type(e).__name__}: {e}"[:160]
        finally:
            ctx.disable(moderngl.BLEND)

    # ---- programs and targets ----

    def _build(self) -> bool:
        """The geometry and the composite, all or nothing: a driver that
        refuses a shader leaves nothing half-made, says why once on
        `error`, and the pass stays off rather than retrying every frame.
        Only a refused build stops it (`_build_failed`): a frame that
        raised before the first build — a malformed skeleton — does not
        keep the hands off once the data is good."""
        if getattr(self, "_build_failed", False):
            return False
        made: list = []
        try:
            geo = Geometry(self.ctx)
            made.append(geo)
            comp = self.ctx.program(vertex_shader=QUAD_VS, fragment_shader=COMPOSITE_FS)
            made.append(comp)
            vao = self.ctx.vertex_array(comp, [])
        except Exception as e:  # noqa: BLE001 — the hands must not take the frame down
            for res in made:
                res.release()
            self.error = f"ghost: {type(e).__name__}: {e}"[:160]
            self._build_failed = True
            return False
        self.geometry, self._comp, self._comp_vao = geo, comp, vao
        return True

    def _make(self, size: tuple[int, int]):
        """(texture, its framebuffer, the multisampled one with depth or
        None, every resource) for one layer at `size`, all or nothing: what
        was made is released again if a piece raises, and the raise goes on."""
        ctx = self.ctx
        made: list = []
        try:
            tex = ctx.texture(size, 4)
            made.append(tex)
            tex.repeat_x = tex.repeat_y = False
            n = min(SAMPLES, int(getattr(ctx, "max_samples", 0) or 0))
            if n > 1:
                rb = ctx.renderbuffer(size, 4, samples=n)
                made.append(rb)
                depth = ctx.depth_renderbuffer(size, samples=n)
                made.append(depth)
                msaa = ctx.framebuffer(color_attachments=[rb], depth_attachment=depth)
                made.append(msaa)
                fbo = ctx.framebuffer(color_attachments=[tex])
                res = [msaa, rb, depth, fbo]
            else:
                depth = ctx.depth_renderbuffer(size)
                made.append(depth)
                msaa = None
                fbo = ctx.framebuffer(color_attachments=[tex], depth_attachment=depth)
                res = [fbo, depth]
        except Exception:
            for r in reversed(made):
                r.release()
            raise
        return tex, fbo, msaa, res

    def _ensure(self, size: tuple[int, int]) -> bool:
        """The hands' layer at `size`, all or nothing: built into locals and
        kept only when every piece was made. A piece the driver refuses
        releases the rest, leaves no target (so the next frame tries again
        from nothing, never on a half-built set), says why once on `error`
        and returns False: that frame draws no hands."""
        if size == self.size and self._fbo is not None:
            return True
        self.release_targets()
        try:
            tex, fbo, msaa, res = self._make(size)
        except Exception as e:  # noqa: BLE001 — the hands must not take the frame down
            if not self.error:
                self.error = f"ghost layer {size[0]}×{size[1]}: {type(e).__name__}: {e}"[:160]
            return False
        self.size, self._tex, self._fbo, self._msaa, self._res = size, tex, fbo, msaa, res
        return True

    def _ensure_readout(self, size: tuple[int, int]) -> bool:
        """The readout layer at `size`, as `_ensure` builds the hands' one.
        False (the guide stays in the hands' layer this frame): it would not
        build, and `error` says why. getattr: a Ghost from before WP2."""
        if size == getattr(self, "_ro_size", None) and getattr(self, "_ro_fbo", None) is not None:
            return True
        self.release_readout()
        try:
            tex, fbo, msaa, res = self._make(size)
        except Exception as e:  # noqa: BLE001 — the guide must not take the hands down
            if not self.error:
                self.error = f"ghost readout {size[0]}×{size[1]}: {type(e).__name__}: {e}"[:160]
            return False
        self._ro_size, self._ro_tex, self._ro_fbo, self._ro_msaa, self._ro_res = (
            size, tex, fbo, msaa, res)
        return True

    def release_readout(self) -> None:
        for res in (*(getattr(self, "_ro_res", None) or []), getattr(self, "_ro_tex", None)):
            if res is not None:
                res.release()
        self._ro_res, self._ro_tex, self._ro_fbo, self._ro_msaa = [], None, None, None
        self._ro_size, self._ro_shown = (0, 0), False

    def release_targets(self) -> None:
        for res in (*self._res, self._tex):
            if res is not None:
                res.release()
        self._res, self._tex, self._fbo, self._msaa = [], None, None, None
        self.size = (0, 0)

    def on_reload(self) -> None:
        """Hot-swap hook: rebuild every program (geometry and composite)
        from this module's current source; a build that fails keeps the
        old set drawing."""
        self._build_failed = self._labels_failed = False
        if self.geometry is None:
            self.error = ""      # an edit may have fixed what would not build
            return
        if self._labels is not None:        # rebuilt from the new source on next use
            self._labels.release()
            self._labels = None
        old = (self.geometry, self._comp_vao, self._comp)
        self.geometry = self._comp = self._comp_vao = None
        self.error = ""
        if self._build():
            for res in old:
                res.release()
        else:
            self.geometry, self._comp_vao, self._comp = old
