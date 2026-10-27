"""The view — the live object the view, rotation and camera params write.

`ViewState` mirrors the reference's S object (its render-relevant fields)
and is the thing `Renderer.draw` reads; `integrate` is the one direct
writer of `ang` (ARCHITECTURE §3.2, "object writer"). It lives here, apart
from render.py, so that the registry, the library and every test that
wants the plain dataclass can have it without importing moderngl (audit
V3). render.py re-exports it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .geometry import EYE_DISTANCE, EYE_FOV, RATE, rot_matrix

N_MOD = 8   # pattern.mod.* inputs the face shader reads as u_mod[N_MOD]
RED = (1.0, 43 / 255, 43 / 255)   # the points' colour, and the panel's one accent (ui.RED)

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


@dataclass
class ViewState:
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
    # the eye (eye.* — session): the one fixed camera, framed on the Leap
    # box; the defaults are project_h's divide (geometry.EYE_FOV / EYE_DISTANCE)
    eye_fov: float = EYE_FOV           # degrees across the shorter side
    eye_distance: float = EYE_DISTANCE  # world units from the origin
    # the point clouds (cloud.* — session; plan 26 A4b, graph.PointCloud):
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
    pattern: int = 0             # face pattern mode (0 = flat fill)
    pattern_mix: float = 1.0     # flat ↔ pattern blend
    # plan 32 (row 331): a media channel over the face pattern, where the
    # one bitmap file (view.bmp_*) was; the same alpha, size and path. Which
    # channel is the preset graph's wire into `pattern.media` (plan 33 T7:
    # `view.media` is retired)
    media_alpha: float = 1.0     # its opacity fader
    media_scale: float = 0.9     # its width, face-UV units (face spans 1.0)
    media_mode: int = 0          # its path: 0 still, 1 orbit, 2 fig-8, 3 sway
    media_amp: float = 0.15      # path amplitude about the face centre, UV units
    media_rate: float = 1.0      # path angular rate, rad/s
    # the backdrop (row 330): a picture under the scene — which one is the
    # preset graph's wire into `backdrop.image` (plan 33 T7: `backdrop.channel`
    # is retired)
    backdrop_alpha: float = 1.0
    backdrop_history: bool = False   # the look-back captures the backdrop too
    # plan 33 S: each switch node's pick (`switch[.n].select`, declared from
    # the preset's graph: params.declare_switches) — switch name → 0 off,
    # 1–8 its input; read once a frame by the renderer
    switch: dict[str, int] = field(default_factory=dict)
    # plan 34 Z: each resize node's values (`resize[.n].*`, declared from the
    # preset's graph: params.declare_resizes) — resize name → its state
    resize: dict[str, ResizeState] = field(default_factory=dict)
    # plan 36 T4: each extra look-back's values (`dream.<n>.*`, declared from
    # the preset's graph: params.declare_lookbacks) — `lookback.<n>` → its
    # `lookback.DreamState` (`lookback`'s are the renderer's own, `dream.*`)
    lookback: dict[str, Any] = field(default_factory=dict)
    # modulation targets (params.py rot.rate.* / pattern.mod.*): per-plane
    # rate multipliers and the face patterns' inputs — 1.0 is the undriven
    # look; an audio lane routed to them (routing.py) is what the reference
    # called PLANEDRIVE and u_bands (here the u_mod[8] uniform)
    rate: list[float] = field(default_factory=lambda: [1.0] * 6)
    pattern_mod: list[float] = field(default_factory=lambda: [1.0] * N_MOD)

    def integrate(self, dt: float) -> None:
        """The frame() angle update: ang[p] += dt·speed·RATE[p]·rate[p].

        The 3D switch (plan 28), on the frame it changes: a 4D shape is
        drawn as R(ang)·body while it is off and as T(ang)·body while it is
        on, T the 3D planes alone (geometry.view_angles). Going on, body
        takes the pose R(ang)·body had, less the 3D turn T(ang) about to be
        put back on it; going off, the reverse. The pose is the same either
        side of the switch, so nothing jumps; while it is on, w is held and
        the 3D planes turn the shape rigidly; the W planes stop."""
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
