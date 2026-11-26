"""The view — the live object the view, rotation and camera params write.

`ViewState` mirrors the reference's S object (its render-relevant fields)
and is the thing `Renderer.draw` reads; `integrate` is the one direct
writer of `ang` (ARCHITECTURE §3.2, "object writer"). It lives here, apart
from render.py, so that the registry, the library and every test that
wants the plain dataclass can have it without importing moderngl (audit
V3). render.py re-exports it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import fractal, writes
from .fractal import Dive
from .geometry import (
    EYE_DISTANCE,
    EYE_FOV,
    RATE,
    SHAPES,
    is_3d,
    pose_angles,
    rot_matrix,
    view_angles,
)

N_MOD = 8   # pattern.mod.* inputs the face shader reads as u_mod[N_MOD]
RED = (1.0, 43 / 255, 43 / 255)   # the points' colour, and the panel's one accent (ui.RED)

# K3 (row 578): the periods the integrated phases wrap at — a whole period
# of every use. The media path reads sin/cos of ph and 2·ph (2π); the
# field's motion reads ph, 0.7·ph and 0.9·ph (field._motion), whose common
# period is 20π (0.7·20π = 14π, 0.9·20π = 18π)
MEDIA_PERIOD = 2.0 * np.pi
INST_PERIOD = 20.0 * np.pi

# plan 34 Z (row 368): a resize node's choices — the long side it makes its
# picture at (`resize[.n].size`, an index: 4 is 256), the shape (the input's
# aspect, or square), how the crop is laid into that size (`media_tex.FITS`'
# order: a test holds them equal; written out, as this module imports no
# media module) and the filter it samples with
RESIZE_SIDES = (16, 32, 64, 128, 256, 512, 1024, 2048)
RESIZE_ASPECTS = ("input", "square")
RESIZE_FITS = ("cover", "contain", "stretch")
RESIZE_FILTERS = ("linear", "nearest")


@dataclass
class ResizeState:
    """One resize node's values (plan 34 Z, `resize[.n].*`: params.declare_resizes),
    read once a frame by the renderer (`ViewState.resize`, `graph.Frame.resizes`):
    indexes into `RESIZE_SIDES`, `RESIZE_ASPECTS`, `RESIZE_FITS` and
    `RESIZE_FILTERS`, and the crop — a normalised rect of the input, its centre
    (`crop_x`, `crop_y`, from the top left) and its size. A value, never a rebuild."""

    size: int = 4
    aspect: int = 0
    fit: int = 0
    filter: int = 0
    crop_x: float = 0.5
    crop_y: float = 0.5
    crop_w: float = 1.0
    crop_h: float = 1.0


# plan 39 T2 (W2): a matte's sources — what makes a pixel pass: its
# brightness, its own coverage (how a cut picture becomes a mask again), or
# its closeness to a keyed hue (a chroma key)
MATTE_FROM = ("luma", "alpha", "chroma")
MATTE_FEATHER = 32.0      # the most px a matte's feather blurs its mask by


@dataclass
class MatteState:
    """One matte node's values (plan 39 T2, `matte[.n].*`: params.declare_mattes),
    read once a frame by the renderer (`ViewState.mattes`, `graph.Frame.mattes`):
    `source` an index into `MATTE_FROM` (`matte.from`), `key` where a pixel starts
    to pass, `soft` the edge's width about it (0 hard), `invert`, `feather` a
    blur of the mask in px, and the keyed colour a chroma matte measures from
    (`hue` 0–1 round the wheel, `sat`). The defaults make a wired matte on a
    plain picture pass its bright half, hard-edged. A value, never a rebuild."""

    source: int = 0
    key: float = 0.5
    soft: float = 0.0
    invert: bool = False
    feather: float = 0.0
    hue: float = 1.0 / 3.0
    sat: float = 1.0


# plan 87, black is clear: what a keyed node measures a pixel's brightness
# by — the largest of r, g, b, or Rec. 709 luma — by index (`key.<node>.measure`)
KEY_MEASURES = ("peak", "luma")
# plan 90 (H1): the key's ramp from clear to solid — smooth (plan 87's), or
# linear: at level 0, soft 1 on peak, a pixel's brightness *is* its coverage
# (the look-back's and the dream's old rule, as a choice of the key's)
KEY_RAMPS = ("smooth", "linear")


@dataclass
class KeyState:
    """One keyed node's black is clear (plan 87, `key.<node>.*`:
    params.declare_keys), read once a frame by the renderer (`ViewState.keys`,
    `graph.Frame.keys`): `measure` an index into `KEY_MEASURES`, `level` the
    brightness at or below which a pixel is clear, `soft` the ramp above it
    (to solid at level + soft; 0 a hard edge), `keep` keep colour
    (premultiplied colour untouched, alpha from the ramp), `feather` a blur
    of the ramp in px, `invert` white is clear instead. A value, never a
    rebuild: whether a node is keyed at all is its graph's (`"keys"`)."""

    measure: int = 0
    level: float = 0.02
    soft: float = 0.1
    keep: bool = True
    feather: float = 0.0
    invert: bool = False
    ramp: int = 0                # plan 90 (H1): an index into `KEY_RAMPS`


@dataclass
class CutState:
    """One cut node's values (plan 39 T3, `cut[.n].*`: params.declare_cuts),
    read once a frame by the renderer (`ViewState.cuts`, `graph.Frame.cuts`):
    `invert` keeps the hole and cuts the rest; `amount` how far the cut goes,
    0–1 — the cut-away part is the picture × (1 − amount): 1 cuts it to
    nothing, 0.5 dims it by half, 0 leaves the picture whole. The defaults
    cut fully where the mask does not pass. A value, never a rebuild."""

    invert: bool = False
    amount: float = 1.0


# plan 90 (H1): a delay's depth — how many past frames it keeps, the stack its
# readers take (`@takes stack`); 1 is the plain z⁻¹ of plan 34
DELAY_DEPTH = (1, 64)
DELAY_GAP = (0.0, 0.25)    # seconds between the frames it keeps (0: every frame)


@dataclass
class DelayState:
    """One delay node's values (plan 90 H1, `delay[.n].*`: params.declare_delays),
    read once a frame by the renderer (`ViewState.delays`, `graph.Frame.delays`):
    `depth` the frames it keeps (1 the one before this, plan 34's z⁻¹), `gap`
    the seconds between them (0 every frame). A value, never a rebuild: a
    depth change makes its stack again, clean."""

    depth: int = 1
    gap: float = 0.0


# plan 39 T4 (W4): a segment's modes — a person model (the worker's), a
# background model (motion: GLSL on the frame thread), and any subject
# (declared, refused in words until a later build) — and the model's levels
SEGMENT_MODES = ("person", "motion", "subject")
SEGMENT_QUALITY = ("fast", "balanced", "accurate")
SEGMENT_FEATHER = 32.0    # the most px a segment's feather blurs its matte by
SEGMENT_LEARN = (0.1, 30.0)   # motion's learn: seconds for a still thing to fade in


@dataclass
class SegmentState:
    """One segment node's values (plan 39 T4, `segment[.n].*`:
    params.declare_segments), read once a frame by the renderer
    (`ViewState.segments`, `graph.Frame.segments`): `mode` an index into
    `SEGMENT_MODES`, `quality` into `SEGMENT_QUALITY` (the model's level),
    `feather` a blur of the matte in px, `smooth` 0–1 how much of the last
    matte each new one keeps (against flicker; 0 the model's matte as it
    is), `on` (off: the input whole on `fg`, nothing on `bg` and `mask`, the
    worker idle), and motion's `sense` (how far a pixel must differ from
    the background to be foreground, 0–1) and `learn` (seconds for a still
    thing to fade into the background). The defaults add nothing to the
    model's own matte. A value, never a rebuild."""

    mode: int = 0
    quality: int = 0
    feather: float = 0.0
    smooth: float = 0.0
    on: bool = True
    sense: float = 0.1
    learn: float = 3.0


@dataclass
class ViewState(writes.Observed):
    """Mirror of the reference's S object (render-relevant fields)."""

    shape: int = 3
    speed: float = 0.30
    depth4: float = 2.6
    bright: float = 1.0
    points: bool = True
    lines: bool = True
    # the layers' opacities (plan 24 C2): 1 is the picture as it was before
    # them, 0 draws the layer fully transparent; each multiplies the alpha
    # draw_scene already gives an edge or a point
    lines_alpha: float = 1.0
    points_alpha: float = 1.0
    # plan 26 A2b (owner, 2026-10-14): where the strokes' weight lives.
    # False (the default) — world space: the line width and the point
    # radius are × camera.zoom, so a stroke grows and shrinks with the shape
    # (the pre-A2 feel). True — screen space: they keep their pixel weight
    # whatever the zoom (A2's behaviour)
    screen_strokes: bool = False
    # plan 64: a fractal's line order. True (the default since 2026-11-24, the
    # owner's call on row 884 after field-wave-slow's scene node cost ~21 ms
    # sorted, ~8 ms additive) — additive: its cells go to the GPU, one
    # instance each, and blend unsorted (fractal_gl.py). False — sorted: the
    # CPU makes the frame and the painter sorts it, as any shape. Not saved
    frac_additive: bool = True
    # plan 64's fractal section: how much detail a fractal shows (× its split
    # size's reciprocal: 2 splits a cell at half the size on screen), and how
    # far and how near its cells are drawn (octaves added to the fractal's own
    # reach, `Fractal.far` / `Fractal.near`). The look's own: saved, routable
    frac_detail: float = 1.0
    frac_far: float = 0.0
    frac_near: float = 0.0
    # plan 81: a fractal's dive, in levels a second (× 1 / ratio each), signed:
    # a velocity on the zoom, integrated by `fractal.step`, so a route on it
    # dives without end and a negative one climbs back out to the whole shape.
    # The look's own: saved and routable (`view.frac_dive`)
    frac_dive: float = 0.0
    playing: bool = True
    planes: list[bool] = field(default_factory=lambda: [False, False, True, True, False, False])
    ang: list[float] = field(default_factory=lambda: [0.0] * 6)
    yaw: float = 0.0
    pitch: float = 0.0
    faces: bool = False          # translucent face fills under the wireframe
    three_d: bool = False        # plan 28: hold a 4D shape's pose, turn it on in 3D (integrate)
    held: bool = False           # whether body is the held pose (three_d, as integrate last saw it)
    body: object = None          # a 4D shape's turn before its angles (4×4), None for none
    cut_through: bool = True     # overlay only: fills lower the window's alpha (render.py)
    # plan 26 A2: camera.zoom / camera.pan are the shape's world transform
    # (geometry.model_matrix): its scale about the world origin and its
    # position in world units (the unit circumradius; pan.y positive down)
    zoom: float = 1.0
    pan: list[float] = field(default_factory=lambda: [0.0, 0.0])
    # where the view is inside a self-similar shape (fractal.py): the host's
    # `fractal.step` re-roots zoom and pan through it each frame, so the zoom
    # never runs out. Empty for every other shape; not saved
    dive: Dive = field(default_factory=Dive)
    # the eye (eye.* — the loadable patch's since plan 43 C2): the one fixed camera
    # the scene is seen through; the defaults are project_h's divide
    # (geometry.EYE_FOV / EYE_DISTANCE), the meta controller's reference eye the hands'
    # calibration is fitted to (ghost.calibration)
    eye_fov: float = EYE_FOV           # degrees across the shorter side
    eye_distance: float = EYE_DISTANCE  # world units from the origin
    # the point clouds (cloud.* — meta controller; plan 26 A4b, graph.PointCloud):
    # how a recorded or live cloud is drawn in the shared camera. Nothing
    # reads them until a `cloud` device is listed
    cloud_size: float = 2.0      # a point's radius, logical px
    cloud_scale: float = 0.3     # the cloud's units → world units (shape radii)
    cloud_bright: float = 1.0    # × the point's colour
    cloud_colors: bool = True    # the cloud's own colours; off (or none): white
    instances: int = 1           # synchronized copies, laid out by inst_layout; 0 draws nothing
    # 0 grid, 1 hex (a honeycomb spiral), 2 ring; 3–8 the 3D lattices: cubic,
    # bcc, fcc, hcp, hex prism, diamond (field.py)
    inst_layout: int = 0
    inst_fit: bool = False       # fit the field to the screen, whole copies only (field.py)
    inst_spacing: float = 1.0    # neighbour spacing, in cells
    inst_persp: float = 0.5      # a 3D lattice's own perspective: 0 flat … 1 deep
    inst_motion: int = 0         # field motion: 0 still, 1 orbit, 2 wave, 3 ripple
    inst_amp: float = 0.25       # motion amplitude, fraction of a cell (the neighbour spacing)
    inst_rate: float = 1.0       # motion angular rate, rad/s
    # K3 (row 578): the motion's phase, rad — inst_rate integrated by the
    # host (integrate), so a step on the rate changes how fast the field
    # moves and never where it is; not a param, never saved
    inst_phase: float = 0.0
    pattern: int = 0             # face pattern mode (0 = flat fill)
    pattern_mix: float = 1.0     # flat ↔ pattern blend
    # plan 32 (row 331): a media channel over the face pattern, where the
    # one bitmap file (view.bmp_*) was; the same alpha, size and path. Which
    # channel is the loadable patch graph's wire into `pattern.media` (plan 33 T7:
    # `view.media` is retired)
    media_alpha: float = 1.0     # its opacity fader
    media_scale: float = 0.9     # its width, face-UV units (face spans 1.0)
    media_mode: int = 0          # its path: 0 still, 1 orbit, 2 fig-8, 3 sway
    media_amp: float = 0.15      # path amplitude about the face centre, UV units
    media_rate: float = 1.0      # path angular rate, rad/s
    # K3 (row 578): the path's phase, rad — media_rate integrated by the
    # host, as inst_phase; not a param, never saved
    media_phase: float = 0.0
    # the backdrop (row 330): a picture under the scene — which one is the
    # loadable patch graph's wire into `backdrop.image` (plan 33 T7: `backdrop.channel`
    # is retired)
    backdrop_alpha: float = 1.0
    backdrop_history: bool = False   # the look-back captures the backdrop too
    # plan 33 S: each switch node's pick (`switch[.n].select`, declared from
    # the loadable patch's graph: params.declare_switches) — switch name → 0 off,
    # 1–8 its input; read once a frame by the renderer
    switch: dict[str, int] = field(default_factory=dict)
    # plan 34 Z: each resize node's values (`resize[.n].*`, declared from the
    # loadable patch's graph: params.declare_resizes) — resize name → its state
    resize: dict[str, ResizeState] = field(default_factory=dict)
    # plan 39 T2: each matte node's values (`matte[.n].*`, declared from the
    # loadable patch's graph: params.declare_mattes) — matte name → its state
    mattes: dict[str, MatteState] = field(default_factory=dict)
    # plan 39 T3: each cut node's values (`cut[.n].*`, declared from the
    # loadable patch's graph: params.declare_cuts) — cut name → its state
    cuts: dict[str, CutState] = field(default_factory=dict)
    # plan 90 (H1): each delay node's depth and gap (`delay[.n].*`, declared from
    # the loadable patch's graph: params.declare_delays) — delay name → its state
    delays: dict[str, DelayState] = field(default_factory=dict)
    # plan 87: each keyed node's black is clear (`key.<node>.*`, declared from
    # the loadable patch's graph `"keys"`: params.declare_keys) — node → its state
    keys: dict[str, KeyState] = field(default_factory=dict)
    # plan 39 T4: each segment node's values (`segment[.n].*`, declared from
    # the loadable patch's graph: params.declare_segments) — segment name → its state
    segments: dict[str, SegmentState] = field(default_factory=dict)
    # plan 36 T4: each extra look-back's values (`dream.<n>.*`, declared from
    # the loadable patch's graph: params.declare_lookbacks) — `lookback.<n>` → its
    # `lookback.DreamState` (`lookback`'s are the renderer's own, `dream.*`)
    lookback: dict[str, Any] = field(default_factory=dict)
    # modulation targets (params.py rot.rate.* / pattern.mod.*): per-plane
    # rate multipliers and the face patterns' inputs — 1.0 is the undriven
    # look; an audio lane routed to them (routing.py) is what the reference
    # called PLANEDRIVE and u_bands (here the u_mod[8] uniform)
    rate: list[float] = field(default_factory=lambda: [1.0] * 6)
    pattern_mod: list[float] = field(default_factory=lambda: [1.0] * N_MOD)

    def seed_phases(self, t: float) -> None:
        """Set the field's and the media path's phases as if their rates had
        always been what they are now, `t` seconds in (K3, row 578): what
        t × rate read before the host integrated them —
        `Renderer._pattern_clock`'s first call. For a pinned clock (the
        golden harness, the shot tools): seeded at t, then `integrate(dt)`
        each frame, the phase is (t + k·dt) · rate at a constant rate."""
        self.inst_phase = (t * self.inst_rate) % INST_PERIOD
        self.media_phase = (t * self.media_rate) % MEDIA_PERIOD

    def integrate(self, dt: float) -> None:
        """The frame() angle update: ang[p] += dt·speed·RATE[p]·rate[p].

        The 3D switch (plan 28), on the frame it changes: a 4D shape is
        drawn as R(ang)·body while it is off and as T(ang)·body while it is
        on, T the 3D planes alone (geometry.view_angles). Going on, body
        takes the pose R(ang)·body had, less the 3D turn T(ang) about to be
        put back on it; going off, the reverse. The pose is the same either
        side of the switch, so nothing jumps; while it is on, w is held and
        the 3D planes turn the shape rigidly; the W planes stop.

        K3 (row 578): the field's motion and the media path, integrated
        here and not as t × rate in the draw — a step on `inst_rate` or
        `media_rate` changes the slope of the phase, never its value. Each
        is wrapped at a period of every use (`INST_PERIOD`, `MEDIA_PERIOD`)
        so it never grows. They run whether or not the turn is playing, as
        the wall clock they replace did."""
        self.inst_phase = (self.inst_phase + dt * self.inst_rate) % INST_PERIOD
        self.media_phase = (self.media_phase + dt * self.media_rate) % MEDIA_PERIOD
        if self.three_d != self.held:
            R = rot_matrix(self.ang)
            T = rot_matrix([*self.ang[:3], 0.0, 0.0, 0.0])
            B = np.eye(4) if self.body is None else self.body
            self.body = (T.T @ R @ B) if self.three_d else (R.T @ T @ B)
            self.held = self.three_d
        if not self.playing:
            return
        for p in range(6 if not self.three_d else 3):
            if self.planes[p]:
                self.ang[p] += dt * self.speed * RATE[p] * self.rate[p]

    def reroot(self, reg=None, off=None, dt: float = 0.0) -> None:
        """A self-similar shape's view, re-rooted once the zoom has gone a
        level in or out (`fractal.step`): the same picture, at a zoom that
        never runs out, zoomed and turned about the middle of the screen
        (plan 81). Once a frame, after `integrate`; `reg` takes the move
        onto the camera params' bases; `off`, the offset drawn after the
        shape (`shapeframe.drawn_offset`), read for the cell under the eye;
        `dt`, the frame's seconds, for the dive rate (`frac_dive`).
        Nothing for any other shape."""
        fractal.step(self, reg, off, dt)

    def pose(self) -> list[float]:
        """The spin's pose as six plane angles, each in (−π, π] — what a
        loadable patch saves (plan 43 C2, row 573: `params.POSE_IDS`) — one pose
        per picture, by one road (review 2.4):

        - a 3D shape: its own XY, XZ and YZ folded, the W planes 0 — body
          or none (its W planes and any body do nothing to it);
        - a 4D shape with no body turned in: its angles as drawn
          (`geometry.view_angles`: the 3D ones alone while the switch
          holds), each folded on its own plane — the same rotation *and*
          the same motion after a load (review 3.1: re-deriving the six
          from the matrix can pick another branch, cos < 0 on a plane,
          which turns that plane backwards once the integrator adds to it);
        - a 4D shape with a body: the turn it is drawn at — R(its
          angles)·body — read back as six angles (`geometry.pose_angles`),
          the body folded in, so a load that sets them (`set_pose`) draws
          it the same whichever way the switch stands;
        - a scene (`Shape.layers`): its layers turn at fractions of the
          angles (`spin` 0.4, −0.7 …), so a turn is not a fold of one — the
          angles as they stand, unfolded (a 3D scene's W planes 0); a 4D
          scene with a body turned in folds it as a 4D shape does, its 3D
          layers taking the folded XY, XZ and YZ (the one case not exact).

        The folded roads return angles in (−π, π]; a scene's are as they
        stand (`loadable.pose_angle` rounds both the same way)."""
        ang = [float(a) for a in self.ang]
        scene = bool(SHAPES[self.shape].layers)
        if scene and (is_3d(self.shape) or (self.body is None and not self.held)):
            return ang[:3] + [0.0] * 3 if is_3d(self.shape) else ang
        if is_3d(self.shape) or self.body is None:
            drawn = view_angles(self.shape, ang, self.held)
            return [math.remainder(float(a), 2.0 * math.pi) + 0.0 for a in drawn]
        B = np.asarray(self.body, dtype=np.float64)
        return pose_angles(rot_matrix(view_angles(self.shape, ang, self.held)) @ B)

    def set_pose(self, angles) -> None:
        """Set the turn to six plane angles (`pose`): no body, the 3D switch
        not yet holding — the next `integrate` folds the pose into a fresh
        body if the switch is on, the same pose either side, and a draw
        before it sees R(angles) alone, the same picture (plan 43 C2)."""
        self.ang = [float(a) for a in angles]
        self.body = None
        self.held = False
