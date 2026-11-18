"""Self-similar shapes you can zoom into forever (a proof of concept).

A shape named in `FRACTALS` is not drawn from its built geometry
(`geometry.geom`, which stays what thumbnails, digests and the catalog
read) but from one made for the frame, here: `frame` walks the fractal
from the top down, drops what the eye cannot see and stops splitting a
cell once it is small on screen, so the picture has the same amount of
detail at every zoom.

The zoom never runs out because it never grows: `step`, once a frame,
re-roots the view. The fractal is copies of itself — cell k is the whole
shape × `ratio` about `centres[k]` — so the view

    world = zoom · turn(x) + p            (p: camera.pan and `Dive.z`)

of a point x = ratio · x' + (1 − ratio) · c_k of cell k is, exactly,

    world = (zoom · ratio) · turn(x') + p + zoom · (1 − ratio) · turn(c_k)

a view of the whole shape at a smaller zoom and another place. When the
zoom passes `Z_IN` `step` takes that view instead, of the cell under the
middle of the screen, and notes which cell in `Dive.path`; zooming out
below `Z_OUT` undoes it, last cell first, until the path is empty and the
whole shape is back: a bird's-eye view, which ordinary zoom then carries
on out of. `frame` draws the cells' ancestors too (`ABOVE` levels up the
path), so what lies beside the cell the view stands in is still there.

Nothing jumps at a re-root: every point's place in the world is the same
either side of it. Two things do change, by design: the shape turns about
the middle of the cell it is rooted in (so a spinning fractal stays put
under the eye however deep the view), and zooming out of the last cell
eases the shape back to the middle of the screen (`step`), so "all the
way out" is always the whole shape, centred.

What this leaves out, on purpose (proof of concept): faces (a fractal
draws lines and points), the world's offset on the shape (plan 59 — a
grabbed fractal is culled as if it were not turned), and a file format:
`Dive` is not saved, so a loaded view starts at the top.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

import numpy as np

from . import geometry
from .geometry import EYE_DISTANCE, EYE_FAR, EYE_FOV, EYE_NEAR

# the zoom a view inside the fractal is kept in: [Z_OUT, Z_IN), with slack
# below Z_IN · ratio so a zoom riding the boundary does not re-root each frame
Z_IN = 4.0
Z_SLACK = 0.85
# zooming out of the last cell, the shape is back in the middle at this zoom
Z_HOME = 1.0
# the cell the view is rooted in is left for a neighbour once the middle of
# the screen is this many of its radii from its centre (a pan across the
# fractal): past the 2.3 a point inside a cell can be from the nearest of
# its children, so the two rules agree
OUTSIDE = 2.6
# the cells above the rooted one are drawn up to the first this many times
# its size (past it a float32 has too few digits for what is near the eye)
ABOVE = 256.0
# a cell splits once its radius is this share of the picture's shorter side
# (`Fractal.split`, this for the pyramid: a denser fractal takes more); what
# the split adds fades in over the next factor of 1 / ratio, by when its
# own children begin to
SPLIT = 0.055
# the depth cue (the scene pass's `pd`, nearer is larger) is −log2 of the
# distance from the eye, over this many octaves either side of the plane
# the zoom scales about: self-similar, as the picture is. Past the far end
# nothing is drawn; the last FOG of the range fades into it
CUE_NEAR = 1.0       # octaves nearer than the middle: full weight
CUE_FAR = 3.0        # octaves farther: gone
FOG = 0.35
# a cell about to pass the eye dissolves rather than sweep across the
# picture: gone at this many octaves nearer than the middle
CUE_GONE = 2.5
# the most edges in a frame; over it the frame is drawn coarser
BUDGET = 30000
# the same along w, for a 4D fractal, in octaves of the distance from the
# 4D eye (`view.depth4`): full weight to W_NEAR nearer than the middle, gone
# by W_GONE (the divide is by that distance: at the eye it is unbounded);
# full weight to W_FAR farther, lost by W_LOST (where the divide has
# gathered everything into the middle of the picture)
W_NEAR, W_GONE = 0.5, 1.0
W_FAR, W_LOST = 0.5, 1.2
# what the stroke density reads (render.draw_scene's `dens`): a constant, so
# a frame's weight does not move with how many edges it happens to hold
DENS_M = 384


@dataclass(frozen=True, eq=False)
class Fractal:
    """A shape made of copies of itself: `V`, `E` the whole shape's corners
    (n, 3) and edges, unit circumradius about the origin; cell k is the
    shape × `ratio` about `centres[k]`. `new_V`, `new_E`: what splitting a
    cell adds to its outline — its children's edges but for those that lie
    along its own — and `new_dot`, which of those points are new corners.
    `outline`: whether the whole shape's own outline is part of the picture
    (not where the cells stand clear of it: the Vicsek cross); `split`: how
    large a cell is on screen before it splits (`SPLIT`); `far`: how many
    octaves past the middle it is drawn to (`CUE_FAR`) — a fractal that fills
    more of space is seen less far into, or the picture is all lines; `near`:
    how many octaves nearer than the middle a cell is gone (`CUE_GONE`); `ink`:
    × its strokes' alpha, for the same reason."""

    V: np.ndarray
    E: np.ndarray
    centres: np.ndarray
    ratio: float
    outline: bool = True
    split: float = SPLIT
    far: float = CUE_FAR
    near: float = CUE_GONE
    ink: float = 1.0
    new_V: np.ndarray = field(init=False)
    new_E: np.ndarray = field(init=False)
    new_dot: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        for name in ("V", "centres"):               # 4-vectors throughout: a 3D one at w = 0
            a = np.asarray(getattr(self, name), dtype=np.float64)
            if a.shape[1] == 3:
                a = np.concatenate([a, np.zeros((len(a), 1))], axis=1)
            object.__setattr__(self, name, a)
        r, V, E = self.ratio, self.V, self.E
        keys: dict[tuple, int] = {}
        pts: list[np.ndarray] = []

        def idx(p) -> int:
            k = tuple(np.round(p, 6) + 0.0)
            if k not in keys:
                keys[k] = len(pts)
                pts.append(p)
            return keys[k]

        def on_own_edge(p, q) -> bool:
            for a, b in E:
                d = V[b] - V[a]
                ts = [np.dot(x - V[a], d) / np.dot(d, d) for x in (p, q)]
                if all(-1e-6 <= t <= 1 + 1e-6 and np.linalg.norm(x - V[a] - t * d) < 1e-6
                       for t, x in zip(ts, (p, q), strict=True)):
                    return True
            return False

        edges: set[tuple[int, int]] = set()
        for c in self.centres:
            W = r * V + (1.0 - r) * c
            for a, b in E:
                if not on_own_edge(W[a], W[b]):
                    i, j = idx(W[a]), idx(W[b])
                    edges.add((min(i, j), max(i, j)))
        own = {tuple(np.round(v, 6) + 0.0) for v in V}
        object.__setattr__(self, "new_V", np.array(pts, dtype=np.float64))
        object.__setattr__(self, "new_E", np.array(sorted(edges), dtype=np.int32))
        object.__setattr__(self, "new_dot", np.array([k not in own for k in keys], dtype=bool))


def _edges(V: np.ndarray) -> np.ndarray:
    return np.array(geometry.edges_by_min_dist(V.tolist()), dtype=np.int32)


def _at_corners(V3, ratio: float, **kw) -> Fractal:
    """A flake: a copy of the solid at each of its corners."""
    V = np.asarray(V3, dtype=np.float64)
    V = V / np.linalg.norm(V[0])
    return Fractal(V, _edges(V), V.copy(), ratio, **kw)


def _cubes(keep, n: int = 3, **kw) -> Fractal:
    """A cube cut 3 × 3 × 3 (n = 4: a tesseract cut 3 × 3 × 3 × 3), the
    small ones `keep` says (of its place in {−1, 0, 1}ⁿ) kept."""
    V = np.array(list(itertools.product((-1, 1), repeat=n))) / math.sqrt(n)
    at = [c for c in np.ndindex(*(3,) * n) if keep(sorted(abs(x - 1) for x in c))]
    return Fractal(V, _edges(V), (np.array(at, dtype=np.float64) - 1.0) / math.sqrt(n),
                   1.0 / 3.0, **kw)


def _octahedron() -> list:
    return [[s if k == a else 0.0 for k in range(3)] for a in range(3) for s in (1.0, -1.0)]


# by the shape's name in the catalog (geometry.SHAPES). A cube's small cube
# is at a corner (1, 1, 1 from the middle), on an edge (0, 1, 1), in a face
# (0, 0, 1) or the middle one (0, 0, 0)
FRACTALS: dict[str, Fractal] = {
    "Sierpinski tetrahedron": _at_corners(geometry._tetra3(), 0.5),
    "Octahedron flake": _at_corners(_octahedron(), 0.5, split=0.14, far=0.9, near=1.2, ink=0.7),
    "Icosahedron flake": _at_corners(geometry.icosa3(), 1.0 / (1.0 + geometry.PHI), split=0.20, far=0.9, near=1.2, ink=0.7),
    "Menger sponge": _cubes(lambda c: c.count(0) <= 1, split=0.15, far=0.8, near=1.2, ink=0.8),
    "Cantor dust": _cubes(lambda c: c.count(0) == 0, split=0.07, far=2.5),
    "Vicsek cross": _cubes(lambda c: c.count(0) >= 2, outline=False, split=0.08, far=2.0),
    # 4D: the pyramid's elder — a 5-cell at each corner of a 5-cell
    # …and the dust and the cross of a tesseract: its 16 corners; its middle
    # and its 8 cells' middles
    "4D Cantor dust": _cubes(lambda c: c.count(0) == 0, 4, split=0.27, far=1.0, near=1.2, ink=0.7),
    "4D Vicsek cross": _cubes(lambda c: c.count(0) >= 3, 4, outline=False, split=0.31,
                              far=1.0, near=1.2, ink=0.7),
    "Sierpinski 5-cell": _at_corners(geometry.simplex5(), 0.5, split=0.10, far=1.5, near=1.5, ink=0.8),
}


def build(name: str, depth: int) -> dict:
    """The fractal as fixed geometry, `depth` splits deep: what the catalog,
    a thumbnail and `geometry.geom` hold of it (no faces)."""
    f = FRACTALS[name]
    ids: dict[tuple, int] = {}
    V: list[list[float]] = []
    E: set[tuple[int, int]] = set()

    def add(P, edges) -> None:
        ix = []
        for q in P:
            k = geometry.kkey(q)
            if k not in ids:
                ids[k] = len(V)
                V.append([float(x) for x in q])
            ix.append(ids[k])
        E.update((min(ix[a], ix[b]), max(ix[a], ix[b])) for a, b in edges)

    if f.outline:
        add(f.V, f.E)
    cells = [(1.0, np.zeros(4))]
    for _ in range(depth):
        for s, o in cells:
            add(s * f.new_V + o, f.new_E)
        cells = [(s * f.ratio, o + s * (1.0 - f.ratio) * c) for s, o in cells for c in f.centres]
    return {"V": V, "E": [list(e) for e in sorted(E)], "F": []}


def spec_of(i: int) -> Fractal | None:
    """Shape i's fractal, None for a shape that is not one."""
    try:
        return FRACTALS.get(geometry.SHAPES[int(i)].name)
    except (IndexError, ValueError, TypeError):
        return None


@dataclass
class Dive:
    """Where a view is inside its fractal (`ViewState.dive`): `path`, the
    cell of each level taken on the way in, outermost first (empty: the
    whole shape); `z`, the shape's place along the eye's axis, which
    camera.pan has no word for, and `w`, its place along the fourth (a 4D
    fractal's; 0 for a 3D one); `last`, the zoom `step` last saw."""

    path: list[int] = field(default_factory=list)
    z: float = 0.0
    w: float = 0.0
    last: float = 1.0

    def reset(self) -> None:
        self.path.clear()
        self.z, self.w, self.last = 0.0, 0.0, 1.0


def turn(s) -> np.ndarray:
    """The view's turn of the shape, 4×4: a point x (a row, 4D) lands at
    x @ turn(s) — the shape's own angles (a 4D one's body first), then the
    camera's yaw and pitch on x, y, z; w is the depth the 4D divide reads."""
    la = geometry.view_angles(s.shape, s.ang, getattr(s, "held", False))
    B = np.eye(4)
    body = getattr(s, "body", None)
    if body is not None and not geometry.is_3d(s.shape):
        B = B @ np.asarray(body).T
    v = geometry.rotate4(B, la)
    x, y, z = geometry._camera(v[:, 0], v[:, 1], v[:, 2], s.yaw, s.pitch)
    return np.stack([x, y, z, v[:, 3]], axis=1)


def step(s, reg=None) -> None:
    """Once a frame, after the params have landed: re-root the view (module
    docstring). Moves `s.zoom`, `s.pan` and `s.dive` together, so the frame
    drawn next is the same picture; with a registry the move goes onto the
    params' bases as well (a ratio on camera.zoom, a nudge on camera.pan),
    so a route or a performer's offset rides on it as on any other move."""
    d = s.dive
    spec = spec_of(s.shape)
    if spec is None:
        if d.path or d.z or d.w:
            d.reset()
        return
    M = turn(s)
    r = spec.ratio
    zoom0 = zoom = max(float(s.zoom), 1e-3)
    p0 = np.array([float(s.pan[0]), -float(s.pan[1]), d.z, d.w])
    p = p0.copy()

    def out() -> None:
        nonlocal zoom, p
        k = d.path.pop()
        zoom = zoom / r
        p = p - zoom * (1.0 - r) * (spec.centres[k] @ M)

    def into() -> None:
        nonlocal zoom, p
        x = (-p / zoom) @ M.T               # the middle of the screen, in the shape
        k = int(np.argmin(np.linalg.norm(x - (1.0 - r) * spec.centres, axis=1)))
        p = p + zoom * (1.0 - r) * (spec.centres[k] @ M)
        zoom = zoom * r
        d.path.append(k)

    # a pan off the side of the rooted cell: up until the view is over an
    # ancestor, and the zoom rule below takes it down again beside
    while d.path and np.linalg.norm(p) / zoom > OUTSIDE:
        out()
    for _ in range(64):
        if zoom < Z_IN:
            break
        into()
    while d.path and zoom < Z_IN * r * Z_SLACK:
        out()
    if not d.path and zoom < d.last and d.last > Z_HOME:
        # out of the last cell and still zooming out: ease the shape home,
        # there by Z_HOME
        f = (zoom - Z_HOME) / (min(d.last, Z_IN) - Z_HOME)
        p = p * min(max(f, 0.0), 1.0)
    d.last = zoom
    if zoom == zoom0 and np.array_equal(p, p0):
        return
    d.z, d.w = float(p[2]), float(p[3])
    if reg is not None:
        if zoom != zoom0:
            reg["camera.zoom"].scale(zoom / zoom0)
        reg["camera.pan.x"].nudge(float(p[0] - p0[0]))
        reg["camera.pan.y"].nudge(float(-(p[1] - p0[1])))
    s.zoom = zoom
    s.pan[0], s.pan[1] = float(p[0]), float(-p[1])


def _smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def frame(spec: Fractal, s, w: int, h: int) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    """This frame's geometry, as `render.draw_scene` takes a shape's:
    (g, P, div4, pd) — g a `geometry.geom` dict with a scene's "style" (each
    edge's and point's own alpha: what a split adds fades in, the far end
    fades out), P the points turned as the view turns the shape (before
    camera.zoom and pan), pd their depth cue and g["cue"] its fixed ends."""
    d = s.dive
    M = turn(s)
    zoom = max(float(s.zoom), 1e-3)
    p = np.array([float(s.pan[0]), -float(s.pan[1]), d.z, d.w])
    d4 = float(s.depth4)
    w_gone, w_near = d4 * 2.0 ** -W_GONE, d4 * 2.0 ** -W_NEAR
    w_far, w_lost = d4 * 2.0 ** W_FAR, d4 * 2.0 ** W_LOST
    fov = getattr(s, "eye_fov", EYE_FOV)
    dist = getattr(s, "eye_distance", EYE_DISTANCE)
    tan = math.tan(math.radians(fov) / 2.0)
    aspect = max(float(w), 1.0) / max(float(h), 1.0)
    tx, ty = (tan * aspect, tan) if aspect >= 1.0 else (tan, tan / aspect)
    nx, ny = math.hypot(1.0, tx), math.hypot(1.0, ty)
    px = min(w, h) / 2.0 / tan                      # px a unit spans at distance 1
    far = min(dist * 2.0 ** spec.far, EYE_FAR)
    gone = dist * 2.0 ** -spec.near
    top = min(CUE_NEAR, 0.4 * spec.near)            # the cue's near end: full weight
    r = spec.ratio

    # the top cell: up the path from the rooted one (scale 1 at the origin)
    scale, origin, up = 1.0, np.zeros(4), 0
    for k in reversed(d.path):
        if scale >= ABOVE:
            break
        scale = scale / r
        origin = origin - scale * (1.0 - r) * spec.centres[k]
        up += 1
    whole = spec.outline and up == len(d.path)
    # a shape with no outline of its own is its first split: drawn whole,
    # however small, as the others' outlines are
    bare = not spec.outline and up == len(d.path)

    split = spec.split * min(w, h)
    grow = 1.0 / r - 1.0                            # a split is all in by a child's own
    most = BUDGET // max(len(spec.new_E), 1)
    while True:
        sc = np.array([scale])
        og = origin[None]
        got_s, got_o, got_a = [], [], []
        total = 0
        for level in range(48):
            q = zoom * (og @ M) + p                  # the cells' centres, in 4D
            R4 = zoom * sc
            rho = d4 - q[:, 3]                       # how far along w from the 4D eye
            # through the 4D divide: where the cell lands in the world, and
            # the most its radius can be there (its nearest part along w)
            c = q[:, :3] * (d4 / np.maximum(rho, w_gone))[:, None]
            R = R4 * d4 / np.maximum(rho - R4, w_gone)
            depth = dist - c[:, 2]
            range_ = np.sqrt(c[:, 0] ** 2 + c[:, 1] ** 2 + depth ** 2)
            seen = ((rho + R4 > w_gone) & (rho - R4 < w_lost)
                    & (depth + R > EYE_NEAR) & (range_ - R < far) & (range_ + R > gone)
                    & ((np.abs(c[:, 0]) - tx * depth) / nx < R)
                    & ((np.abs(c[:, 1]) - ty * depth) / ny < R))
            size = R4 * d4 / np.maximum(rho, w_gone) / np.maximum(range_, 1e-9) * px
            go = seen & (size > split)
            first = bare and level == 0
            if first:
                go = np.ones(1, bool)
            if not go.any():
                break
            sc, og, size, range_ = sc[go], og[go], size[go], range_[go]
            # what this split adds: in over the next factor of 2 in size,
            # out over the far end of the cue
            cue = -np.log2(np.maximum(range_, 1e-9) / dist)
            fog = (_smooth((cue + spec.far) / (FOG * (top + spec.far)))
                   * _smooth((spec.near - cue) / (spec.near - top)))
            got_s.append(sc)
            got_o.append(og)
            grown = np.ones(1) if first else _smooth((size - split) / (split * grow))
            got_a.append(grown * fog * spec.ink)
            total += len(sc)
            if total > most:
                break
            n = len(spec.centres)
            og = (og[:, None, :] + (sc * (1.0 - r))[:, None, None] * spec.centres[None]).reshape(-1, 4)
            sc = np.repeat(sc * r, n)
        if total <= most:
            break
        split *= 1.35                                # too much to draw: coarser

    nv, ne = len(spec.new_V), len(spec.new_E)
    if got_s:
        S, O, A = np.concatenate(got_s), np.concatenate(got_o), np.concatenate(got_a)
        X = (S[:, None, None] * spec.new_V[None] + O[:, None, :]).reshape(-1, 4)
        E = (spec.new_E[None] + (np.arange(len(S)) * nv)[:, None, None]).reshape(-1, 2)
        e_alpha = np.repeat(A, ne)
        p_alpha = (A[:, None] * spec.new_dot[None]).reshape(-1)
    else:
        X, E = np.zeros((0, 4)), np.zeros((0, 2), dtype=np.int64)
        e_alpha, p_alpha = np.zeros(0), np.zeros(0)
    if whole:
        # the whole shape's own outline, while the view can reach it
        E = np.concatenate([E, spec.E + len(X)])
        X = np.concatenate([X, scale * spec.V + origin])
        e_alpha = np.concatenate([e_alpha, np.full(len(spec.E), spec.ink)])
        p_alpha = np.concatenate([p_alpha, np.ones(len(spec.V))])

    # the points: placed in 4D, through the 4D divide (the eye's side of it
    # clamped: what is that near along w has faded out), then back to what
    # the scene pass takes, before camera.zoom and pan
    Q = zoom * (X @ M) + p
    rho = d4 - Q[:, 3]
    world = Q[:, :3] * (d4 / np.maximum(rho, w_gone))[:, None]
    P = world.copy()
    P[:, 0] -= p[0]
    P[:, 1] -= p[1]
    P /= zoom
    along = (_smooth((rho - w_gone) / (w_near - w_gone))
             * _smooth((w_lost - rho) / (w_lost - w_far)))
    if len(E):
        e_alpha = e_alpha * np.minimum(along[E[:, 0]], along[E[:, 1]])
    p_alpha = p_alpha * along
    range_ = np.sqrt(world[:, 0] ** 2 + world[:, 1] ** 2 + (dist - world[:, 2]) ** 2)
    pd = np.clip(-np.log2(np.maximum(range_, 1e-9) / dist), -spec.far, top)
    n, m = len(X), len(E)
    st = {"e_alpha": e_alpha, "e_width": np.ones(m), "e_rgb": np.ones((m, 3)),
          "e_m": np.full(m, float(DENS_M)), "p_alpha": p_alpha, "p_rgb": np.ones((n, 3)),
          "p_tinted": np.zeros(n, bool), "f_alpha": np.ones(0)}
    g = {"V": X, "E": E.astype(np.int32), "n": n, "m": m, "style": st,
         "cue": (-spec.far, top), "dens_m": DENS_M}
    return g, P, np.full(n, float(s.depth4)), pd
