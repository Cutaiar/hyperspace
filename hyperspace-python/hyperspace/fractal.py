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
# how many levels above the rooted cell are drawn
ABOVE = 8
# a cell splits once its radius is this share of the picture's shorter side;
# what the split adds fades in over the next factor of 2, by when its own
# children begin to
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
# the most cells split in a frame; over it the frame is drawn coarser
BUDGET = 2600
# what the stroke density reads (render.draw_scene's `dens`): a constant, so
# a frame's weight does not move with how many edges it happens to hold
DENS_M = 384


@dataclass(frozen=True, eq=False)
class Fractal:
    """A shape made of copies of itself: `V`, `E` the whole shape's corners
    (n, 3) and edges, unit circumradius about the origin; cell k is the
    shape × `ratio` about `centres[k]`. `new_V`, `new_E`: what splitting a
    cell adds to its outline — its children's edges but for those that lie
    along its own — and `new_dot`, which of those points are new corners."""

    V: np.ndarray
    E: np.ndarray
    centres: np.ndarray
    ratio: float
    new_V: np.ndarray = field(init=False)
    new_E: np.ndarray = field(init=False)
    new_dot: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
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
                if all(np.linalg.norm(np.cross(x - V[a], d)) < 1e-6
                       and -1e-6 <= np.dot(x - V[a], d) / np.dot(d, d) <= 1 + 1e-6
                       for x in (p, q)):
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


def _sierpinski() -> Fractal:
    V = np.asarray(geometry._tetra3(), dtype=np.float64)
    V = V / np.linalg.norm(V[0])
    E = np.array([[a, b] for a in range(4) for b in range(a + 1, 4)], dtype=np.int32)
    return Fractal(V, E, V.copy(), 0.5)


# by the shape's name in the catalog (geometry.SHAPES)
FRACTALS: dict[str, Fractal] = {"Sierpinski tetrahedron": _sierpinski()}


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
    camera.pan has no word for; `last`, the zoom `step` last saw."""

    path: list[int] = field(default_factory=list)
    z: float = 0.0
    last: float = 1.0

    def reset(self) -> None:
        self.path.clear()
        self.z, self.last = 0.0, 1.0


def turn(s) -> np.ndarray:
    """The view's turn of a 3D shape, 3×3: a point x (a row) lands at
    x @ turn(s) — `geometry.world_points` at the shape's own angles."""
    la = geometry.view_angles(s.shape, s.ang, getattr(s, "held", False))
    P, _, _ = geometry.world_points(np.eye(4)[:3], la, s.yaw, s.pitch, d4=s.depth4)
    return P


def step(s, reg=None) -> None:
    """Once a frame, after the params have landed: re-root the view (module
    docstring). Moves `s.zoom`, `s.pan` and `s.dive` together, so the frame
    drawn next is the same picture; with a registry the move goes onto the
    params' bases as well (a ratio on camera.zoom, a nudge on camera.pan),
    so a route or a performer's offset rides on it as on any other move."""
    d = s.dive
    spec = spec_of(s.shape)
    if spec is None:
        if d.path or d.z:
            d.reset()
        return
    M = turn(s)
    r = spec.ratio
    zoom0 = zoom = max(float(s.zoom), 1e-3)
    p0 = np.array([float(s.pan[0]), -float(s.pan[1]), d.z])
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
    d.z = float(p[2])
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
    p = np.array([float(s.pan[0]), -float(s.pan[1]), d.z])
    fov = getattr(s, "eye_fov", EYE_FOV)
    dist = getattr(s, "eye_distance", EYE_DISTANCE)
    tan = math.tan(math.radians(fov) / 2.0)
    aspect = max(float(w), 1.0) / max(float(h), 1.0)
    tx, ty = (tan * aspect, tan) if aspect >= 1.0 else (tan, tan / aspect)
    nx, ny = math.hypot(1.0, tx), math.hypot(1.0, ty)
    px = min(w, h) / 2.0 / tan                      # px a unit spans at distance 1
    far = min(dist * 2.0 ** CUE_FAR, EYE_FAR)
    gone = dist * 2.0 ** -CUE_GONE
    r = spec.ratio

    # the top cell: up the path from the rooted one (scale 1 at the origin)
    scale, origin = 1.0, np.zeros(3)
    above = d.path[-ABOVE:] if d.path else []
    for k in reversed(above):
        scale = scale / r
        origin = origin - scale * (1.0 - r) * spec.centres[k]
    whole = len(above) == len(d.path)

    split = SPLIT * min(w, h)
    while True:
        sc = np.array([scale])
        og = origin[None]
        got_s, got_o, got_a = [], [], []
        total = 0
        for _ in range(ABOVE + 24):
            c = zoom * (og @ M) + p                  # the cells' centres in the world
            R = zoom * sc
            depth = dist - c[:, 2]
            range_ = np.sqrt(c[:, 0] ** 2 + c[:, 1] ** 2 + depth ** 2)
            seen = ((depth + R > EYE_NEAR) & (range_ - R < far) & (range_ + R > gone)
                    & ((np.abs(c[:, 0]) - tx * depth) / nx < R)
                    & ((np.abs(c[:, 1]) - ty * depth) / ny < R))
            size = R / np.maximum(range_, 1e-9) * px
            go = seen & (size > split)
            if not go.any():
                break
            sc, og, size, range_ = sc[go], og[go], size[go], range_[go]
            # what this split adds: in over the next factor of 2 in size,
            # out over the far end of the cue
            cue = -np.log2(np.maximum(range_, 1e-9) / dist)
            fog = (_smooth((cue + CUE_FAR) / (FOG * (CUE_NEAR + CUE_FAR)))
                   * _smooth((CUE_GONE - cue) / (CUE_GONE - CUE_NEAR)))
            got_s.append(sc)
            got_o.append(og)
            got_a.append(_smooth((size - split) / split) * fog)
            total += len(sc)
            if total > BUDGET:
                break
            n = len(spec.centres)
            og = (og[:, None, :] + (sc * (1.0 - r))[:, None, None] * spec.centres[None]).reshape(-1, 3)
            sc = np.repeat(sc * r, n)
        if total <= BUDGET:
            break
        split *= 1.35                                # too much to draw: coarser

    nv, ne = len(spec.new_V), len(spec.new_E)
    if got_s:
        S, O, A = np.concatenate(got_s), np.concatenate(got_o), np.concatenate(got_a)
        X = (S[:, None, None] * spec.new_V[None] + O[:, None, :]).reshape(-1, 3)
        E = (spec.new_E[None] + (np.arange(len(S)) * nv)[:, None, None]).reshape(-1, 2)
        e_alpha = np.repeat(A, ne)
        p_alpha = (A[:, None] * spec.new_dot[None]).reshape(-1)
    else:
        X, E = np.zeros((0, 3)), np.zeros((0, 2), dtype=np.int64)
        e_alpha, p_alpha = np.zeros(0), np.zeros(0)
    if whole:
        # the whole shape's own outline, while the view can reach it
        E = np.concatenate([E, spec.E + len(X)])
        X = np.concatenate([X, scale * spec.V + origin])
        e_alpha = np.concatenate([e_alpha, np.ones(len(spec.E))])
        p_alpha = np.concatenate([p_alpha, np.ones(len(spec.V))])

    P = X @ M
    P[:, 2] += d.z / zoom
    world = zoom * P
    world[:, 0] += p[0]
    world[:, 1] += p[1]
    range_ = np.sqrt(world[:, 0] ** 2 + world[:, 1] ** 2 + (dist - world[:, 2]) ** 2)
    pd = np.clip(-np.log2(np.maximum(range_, 1e-9) / dist), -CUE_FAR, CUE_NEAR)
    n, m = len(X), len(E)
    st = {"e_alpha": e_alpha, "e_width": np.ones(m), "e_rgb": np.ones((m, 3)),
          "e_m": np.full(m, float(DENS_M)), "p_alpha": p_alpha, "p_rgb": np.ones((n, 3)),
          "p_tinted": np.zeros(n, bool), "f_alpha": np.ones(0)}
    g = {"V": X, "E": E.astype(np.int32), "n": n, "m": m, "style": st,
         "cue": (-CUE_FAR, CUE_NEAR), "dens_m": DENS_M}
    return g, P, np.full(n, float(s.depth4)), pd
