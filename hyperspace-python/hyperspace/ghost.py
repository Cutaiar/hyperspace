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

The geometry is replaceable. `HandPose` is the data path (stage-space
joints and the bones' raw rotations, per hand, with its fade and
colour); `CapsuleHands` turns poses into a sphere per joint, a capsule
per bone and a palm. A skinned mesh is another class with the same
`draw(poses, view_proj, eye)`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import moderngl
import numpy as np

GROUP = "ghost"

FADE_IN = 0.10      # s: a hand that enters comes up this fast
FADE_OUT = 0.30     # s: one that leaves fades over this, where it was last seen
PAD = 60.0          # mm around the palm box: the fingers reach past the palm
FOV_Y = 38.0        # degrees, the camera's vertical field of view
ELEVATION = 32.0    # degrees the camera looks down onto the hands
SAMPLES = 4         # MSAA for the hands' own framebuffer
FINGER_R = 0.085    # finger radius as a fraction of palm width, when bones give none
BONE_R = 0.42       # a bone's capsule radius as a fraction of its reported width

# per hand, linear: the HANDS page's colours (left white, right red), cooled
COLOURS = {"left": (0.80, 0.88, 1.00), "right": (1.00, 0.36, 0.30)}

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

# the palm box when there is no source to ask: hands/core.py's defaults
# (X_RANGE for both hands, FEATURES' y and z)
DEFAULT_BOX = ((-220.0, 220.0), (100.0, 350.0), (-100.0, 100.0))


# ------------------------------------------------------------------ params

@dataclass
class GhostState:
    """What the ghost.* params write. Session, not performance: see
    `register`."""

    on: bool = False
    alpha: float = 0.6
    mirror: bool = False


def register(reg, state: GhostState) -> None:
    """ghost.on / .alpha / .mirror — session params (params.SESSION_GROUPS):
    the hands are the room's display, like the output's placement, so a
    preset load never switches them off mid-set. Ordinary otherwise: they
    show on the HANDS page and can be learned onto a button or a knob."""
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
               lambda v: setattr(state, "mirror", bool(v)), group=GROUP,
               tip="Flip the ghost hands left for right — for a rig that shows the "
                   "render in a mirror or on a Pepper's Ghost glass.")


# ------------------------------------------------------------------ camera

def basis(mode: str, mirror: bool = False) -> np.ndarray:
    """Leap → stage, 3×3, for a tracking mode (desktop when unknown)."""
    m = np.array(MODES.get(str(mode).lower(), MODES["desktop"]), dtype=np.float64)
    if mirror:
        m[0] *= -1.0
    return m


def box_of(source) -> tuple[tuple[float, float], ...]:
    """The palm box in Leap mm, ((x lo, hi), (y …), (z …)): the union of
    both hands' calibrated ranges for x, y and z where the setup has those
    axes (`HandsIO.axes` / `.state`, which hold hands.json's ranges), the
    defaults for the rest. Duck-typed: anything without axes gets
    DEFAULT_BOX."""
    out = []
    axes, state = getattr(source, "axes", None) or (), getattr(source, "state", None) or ()
    for k, feat in enumerate("xyz"):
        lo, hi = DEFAULT_BOX[k]
        seen = [(min(st.lo, st.hi), max(st.lo, st.hi)) for a, st in zip(axes, state)
                if a.feature == feat and st.hi != st.lo]
        if seen:
            lo, hi = min(s[0] for s in seen), max(s[1] for s in seen)
        out.append((float(lo), float(hi)))
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


def camera(box, m: np.ndarray, aspect: float) -> tuple[np.ndarray, np.ndarray]:
    """(view_proj 4×4, eye) for a palm box in Leap mm seen through the
    stage basis `m`: behind the performer's hands and ELEVATION above
    them, looking at the box's centre, as close as it can stand with every
    corner of the padded box in frame."""
    corners = np.array([(x, y, z) for x in box[0] for y in box[1] for z in box[2]])
    st = corners @ m.T
    lo, hi = st.min(axis=0) - PAD, st.max(axis=0) + PAD
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


def pose(side: str, skel: dict, m: np.ndarray, fade: float = 1.0) -> HandPose:
    """A `hands.core.skeleton` dict as a `HandPose` through basis `m`."""
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
                    float(skel.get("width") or 85.0), joints, widths, rots, m, fade,
                    COLOURS.get(side, (1.0, 1.0, 1.0)))


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

COMPOSITE_VS = """
#version 330
out vec2 v_uv;
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    v_uv = p;
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""

COMPOSITE_FS = """
#version 330
in vec2 v_uv;
uniform sampler2D u_hands;
uniform float u_alpha;
out vec4 f_color;
void main() { f_color = texture(u_hands, v_uv) * u_alpha; }
"""


class CapsuleHands:
    """The first geometry: a sphere per joint, a capsule per bone, a palm.

    Built per frame from the poses (a few dozen instances), drawn into
    whatever is bound with the depth test on. Replace this class — same
    `draw` — to put a skinned mesh on the same data."""

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

    @staticmethod
    def parts(p: HandPose) -> tuple[list, list, list]:
        """(spheres, tubes, palm triangles) for one pose: each sphere
        (centre, r), each tube (a, b, r), each triangle three (pos, normal)."""
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

    def draw(self, poses: list[HandPose], view_proj: np.ndarray, eye: np.ndarray) -> None:
        s_rows, t_rows, m_rows = [], [], []
        for p in poses:
            col = (*p.colour, float(p.fade))
            spheres, tubes, tris = self.parts(p)
            s_rows += [(*c, r, *col) for c, r in spheres]
            t_rows += [(*a, *b, r, *col) for a, b, r in tubes]
            for tri in tris:
                m_rows += [(*q, *nn, *col) for q, nn in tri]
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


# ------------------------------------------------------------------ the pass

@dataclass
class _Side:
    fade: float = 0.0
    skel: dict | None = field(default=None, repr=False)    # last seen


class Ghost:
    """The ghost-hands pass: `draw` after the FX chain, onto the target.

    `source` is anything with ``.skeleton`` (side → `hands.core.skeleton`
    for the hands present this frame) — the HandsIO, set by the app when
    the tracker is on; ``.cfg["mode"]`` and ``.axes`` / ``.state`` give the
    tracking mode and the calibrated box when it has them. None (no
    tracker): nothing draws."""

    def __init__(self, ctx: moderngl.Context, state: GhostState | None = None):
        self.ctx = ctx
        self.state = state if state is not None else GhostState()
        self.source = None
        self.sides = {"left": _Side(), "right": _Side()}
        self.geometry: CapsuleHands | None = None      # built on first use
        self._comp: moderngl.Program | None = None
        self._comp_vao: moderngl.VertexArray | None = None
        self._t: float | None = None
        self.size = (0, 0)
        self._tex: moderngl.Texture | None = None
        self._fbo: moderngl.Framebuffer | None = None     # on the texture
        self._msaa: moderngl.Framebuffer | None = None    # multisampled, with depth
        self._res: list = []

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
            return None
        seen = self.step(t)
        if not seen:
            return None
        cfg = getattr(self.source, "cfg", None) or {}
        m = basis(cfg.get("mode", "desktop"), st.mirror)
        vp, eye = camera(box_of(self.source), m, aspect)
        return [pose(side, sk, m, fade) for side, sk, fade in seen], vp, eye

    def draw(self, target: moderngl.Framebuffer, vp: tuple[int, int, int, int], t: float,
             opaque: bool = True) -> bool:
        """The hands over `target`'s viewport `vp`, if any show. Leaves
        `target` bound with that viewport; touches no GL state when nothing
        draws. True when it drew."""
        vx, vy, vw, vh = vp
        got = self.poses(t, max(vw, 1) / max(vh, 1))
        if got is None:
            return False
        poses, view_proj, eye = got
        ctx = self.ctx
        if self.geometry is None:
            self.geometry = CapsuleHands(ctx)
            self._comp = ctx.program(vertex_shader=COMPOSITE_VS, fragment_shader=COMPOSITE_FS)
            self._comp_vao = ctx.vertex_array(self._comp, [])
        self._ensure((max(vw, 1), max(vh, 1)))
        try:
            draw_fbo = self._msaa if self._msaa is not None else self._fbo
            draw_fbo.use()
            ctx.viewport = (0, 0, *self.size)
            ctx.clear(0.0, 0.0, 0.0, 0.0, depth=1.0)
            ctx.disable(moderngl.BLEND)
            ctx.enable(moderngl.DEPTH_TEST)
            self.geometry.draw(poses, view_proj, eye)
            ctx.disable(moderngl.DEPTH_TEST)
            if self._msaa is not None:
                ctx.copy_framebuffer(self._fbo, self._msaa)
            # over the target, premultiplied. On an opaque ground its alpha
            # is left exactly as it is (plan 14 WP1); on overlay's
            # see-through ground the hands add their coverage to it
            target.use()
            ctx.viewport = (vx, vy, vw, vh)
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = ((moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA, moderngl.ZERO,
                               moderngl.ONE) if opaque else
                              (moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA, moderngl.ONE,
                               moderngl.ONE_MINUS_SRC_ALPHA))
            self._tex.use(location=0)
            self._comp["u_hands"].value = 0
            self._comp["u_alpha"].value = float(self.state.alpha)
            self._comp_vao.render(moderngl.TRIANGLES, vertices=3)
        finally:
            ctx.disable(moderngl.DEPTH_TEST)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            target.use()
            ctx.viewport = (vx, vy, vw, vh)
        return True

    # ---- targets ----

    def _ensure(self, size: tuple[int, int]) -> None:
        if size == self.size and self._tex is not None:
            return
        self.release_targets()
        ctx = self.ctx
        self.size = size
        self._tex = ctx.texture(size, 4)
        self._tex.repeat_x = self._tex.repeat_y = False
        n = min(SAMPLES, int(getattr(ctx, "max_samples", 0) or 0))
        if n > 1:
            rb = ctx.renderbuffer(size, 4, samples=n)
            depth = ctx.depth_renderbuffer(size, samples=n)
            self._msaa = ctx.framebuffer(color_attachments=[rb], depth_attachment=depth)
            self._fbo = ctx.framebuffer(color_attachments=[self._tex])
            self._res = [self._msaa, rb, depth, self._fbo]
        else:
            depth = ctx.depth_renderbuffer(size)
            self._fbo = ctx.framebuffer(color_attachments=[self._tex], depth_attachment=depth)
            self._res = [self._fbo, depth]

    def release_targets(self) -> None:
        for res in (*self._res, self._tex):
            if res is not None:
                res.release()
        self._res, self._tex, self._fbo, self._msaa = [], None, None, None
        self.size = (0, 0)

    def on_reload(self) -> None:
        if self.geometry is not None:
            self.geometry.on_reload()
