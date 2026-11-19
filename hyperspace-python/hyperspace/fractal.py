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

Two ways to draw a frame's cells (plan 64): `frame`, the CPU path, makes
the frame's geometry in numpy and the scene pass painter-sorts it as any
shape's; `instances` hands the same walk (`walk`) to the GPU as one row a
cell, and fractal_gl.py's vertex shaders place, turn and divide each cell's
copy of one mesh, drawn unsorted and additive (`view.frac_additive`). The
cull and the split stay here, on the CPU, either way.

A loadable patch keeps the dive (`loadable.DIVE_KEY`, row 889): a load puts
the view back in the cell it was saved in.

What a grab holds (plan 64, part 2, the module's end): outside, the shape
is an object; inside — too big to keep whole on screen, or gone into a
cell — the space, whose flight is this view's own.
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
# a saved dive's longest path (row 889): far past any dive float64 can tell
# apart, short enough that a hand-edited file can't make a load crawl
MAX_PATH = 4096
# plan 64, part 2: the view goes inside once the shape no longer fits the
# rig's box (a corner past its half, across or up), and comes back out only
# within this share of it, so a zoom riding the edge doesn't flip it
FIT_OUT = 0.9
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
    # the solid's faces, triangulated: corners (T, 3) into V, each corner's
    # uv on its face (T, 3, 2), and which face (T,)
    tris: np.ndarray = field(init=False)
    tri_uv: np.ndarray = field(init=False)
    tri_face: np.ndarray = field(init=False)

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
        # the faces: the triangles of the edge graph (a simplex, an octahedron,
        # an icosahedron), or with none its squares (a cube, a tesseract)
        nb = {i: set() for i in range(len(V))}
        for a, b in E.tolist():
            nb[a].add(b)
            nb[b].add(a)
        cycles = sorted({tuple(sorted((a, b, c))) for a in nb for b in nb[a] for c in nb[a] & nb[b]})
        if not cycles:
            seen: set = set()
            for a, beside in nb.items():
                for b in beside:
                    for c in nb[b] - {a}:
                        for d in (nb[c] & beside) - {b}:
                            if frozenset((a, b, c, d)) not in seen:
                                seen.add(frozenset((a, b, c, d)))
                                cycles.append((a, b, c, d))
        corner = ((0.0, 0.0), (1.0, 0.0), (0.5, 1.0)) if len(cycles[0]) == 3 else (
            (0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
        tris, uv, face = [], [], []
        for fi, cyc in enumerate(cycles):
            for k in range(1, len(cyc) - 1):
                tris.append((cyc[0], cyc[k], cyc[k + 1]))
                uv.append((corner[0], corner[k], corner[k + 1]))
                face.append(fi)
        object.__setattr__(self, "tris", np.array(tris, dtype=np.int32))
        object.__setattr__(self, "tri_uv", np.array(uv, dtype=np.float64))
        object.__setattr__(self, "tri_face", np.array(face, dtype=np.int32))


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


def name_of(spec: Fractal) -> str:
    """The catalog's name of a fractal of `FRACTALS`."""
    for name, f in FRACTALS.items():
        if f is spec:
            return name
    raise KeyError(spec)


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
    fractal's; 0 for a 3D one); `last`, the zoom `step` last saw.

    Inside (plan 64, part 2: `inside`), what a grab holds is the space, and
    its motion is part of this view rather than an offset on a world object:
    `turn` (3×3), the space turned about the middle of the screen, on x, y, z
    before the 4D divide (`fractal.turn`), and `shift` (3, world units), the
    room placement the shape had as an object when the view went inside,
    after the divide. Both are the identity outside. `flown`: the world's
    flight pose already folded into this view (`fold_flight`); None until the
    first fold, or after a reset or a load."""

    path: list[int] = field(default_factory=list)
    z: float = 0.0
    w: float = 0.0
    last: float = 1.0
    inside: bool = False
    turn: np.ndarray = field(default_factory=lambda: np.eye(3))
    shift: np.ndarray = field(default_factory=lambda: np.zeros(3))
    flown: np.ndarray | None = None
    flown_epoch: int = -1             # the world object's epoch `flown` was read in
    shape: int | None = None          # the shape this dive is in (another: it starts over)

    def reset(self) -> None:
        self.path.clear()
        self.z, self.w, self.last = 0.0, 0.0, 1.0
        self.inside = False
        self.turn, self.shift, self.flown = np.eye(3), np.zeros(3), None
        self.flown_epoch, self.shape = -1, None

    def to_json(self, name: str) -> dict:
        """The dive as a loadable patch keeps it (`DIVE_KEY`, row 889)."""
        return {"shape": name, "path": [int(k) for k in self.path],
                "z": float(self.z), "w": float(self.w),
                "turn": [float(x) for x in np.asarray(self.turn).ravel()],
                "shift": [float(x) for x in np.asarray(self.shift).ravel()]}

    def from_json(self, doc, name: str) -> str:
        """This view's dive from a loadable patch's key, for the shape `name`:
        "" when it landed, else why not (the dive left at the top). A key for
        another shape, a cell index outside the fractal, a path too long, a
        number that is not finite or a turn that is not one are refused whole."""
        self.reset()
        if doc is None:
            return ""
        spec = FRACTALS.get(name)
        if not isinstance(doc, dict) or doc.get("shape") != name or spec is None:
            return "the saved dive is for another shape; starts at the top"
        path = doc.get("path", [])
        z, w = doc.get("z", 0.0), doc.get("w", 0.0)
        turn_, shift_ = doc.get("turn", list(np.eye(3).ravel())), doc.get("shift", [0.0] * 3)
        # as written: whole numbers for the cells, real numbers for the rest
        if (not isinstance(path, list) or not all(_whole(k) for k in path)
                or not all(_real(x) for x in (z, w))
                or not isinstance(turn_, list) or len(turn_) != 9
                or not isinstance(shift_, list) or len(shift_) != 3
                or not all(_real(x) for x in (*turn_, *shift_))):
            return "the saved dive would not read; starts at the top"
        path = [int(k) for k in path]
        z, w = float(z), float(w)
        T = np.asarray(turn_, dtype=np.float64).reshape(3, 3)
        sh = np.asarray(shift_, dtype=np.float64)
        n = len(spec.centres)
        if (len(path) > MAX_PATH or any(not 0 <= k < n for k in path)
                or not all(math.isfinite(x) and abs(x) < 1e12 for x in (z, w, *T.ravel(), *sh))
                or not np.allclose(T @ T.T, np.eye(3), atol=1e-6)
                or np.linalg.det(T) <= 0.0):
            return "the saved dive is not one this fractal can take; starts at the top"
        self.path[:] = path
        self.z, self.w, self.turn, self.shift = z, w, T, sh
        self.inside = True
        return ""


def _whole(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _real(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def turn(s) -> np.ndarray:
    """The view's turn of the shape, 4×4: a point x (a row, 4D) lands at
    x @ turn(s) — the shape's own angles (a 4D one's body first), then the
    camera's yaw and pitch on x, y, z, then inside the space's own turn
    (`Dive.turn`); w is the depth the 4D divide reads."""
    la = geometry.view_angles(s.shape, s.ang, getattr(s, "held", False))
    B = np.eye(4)
    body = getattr(s, "body", None)
    if body is not None and not geometry.is_3d(s.shape):
        B = B @ np.asarray(body).T
    v = geometry.rotate4(B, la)
    x, y, z = geometry._camera(v[:, 0], v[:, 1], v[:, 2], s.yaw, s.pitch)
    M = np.stack([x, y, z, v[:, 3]], axis=1)
    d = getattr(s, "dive", None)
    if d is not None and d.inside:
        M = M @ _block(np.asarray(d.turn).T)
    return M


def _block(R3) -> np.ndarray:
    """A 3×3 on x, y, z as a 4×4 that leaves w alone."""
    m = np.eye(4)
    m[:3, :3] = R3
    return m


def step(s, reg=None, off=None) -> None:
    """Once a frame, after the params have landed: re-root the view (module
    docstring). Moves `s.zoom`, `s.pan` and `s.dive` together, so the frame
    drawn next is the same picture; with a registry the move goes onto the
    params' bases as well (a ratio on camera.zoom, a nudge on camera.pan),
    so a route or a performer's offset rides on it as on any other move.

    `off`: the offset the scene pass composes after the walk (`shapeframe.
    drawn_offset`, a 4×4 in the home's frame; None the identity), read only
    for which cell is under the middle of the screen as drawn. A re-root
    happens only inside (plan 64, part 2), where that offset is the room
    placement the shape had (`Dive.shift`), fixed in world units, so it moves
    nothing and nothing here makes up for it."""
    d = s.dive
    spec = spec_of(s.shape)
    if spec is None or (d.shape is not None and d.shape != int(s.shape)):
        if d.path or d.z or d.w or d.inside or d.shape is not None:
            d.reset()                # another shape: its cells are not this one's
        if spec is None:
            return
    d.shape = int(s.shape)
    M = turn(s)
    r = spec.ratio
    zoom0 = zoom = max(float(s.zoom), 1e-3)
    p0 = np.array([float(s.pan[0]), -float(s.pan[1]), d.z, d.w])
    p = p0.copy()
    # the middle of the screen in the walk's world: the origin, or with an
    # offset the point it draws at the origin (the offset is in world units)
    mid = np.zeros(4)
    if off is not None:
        m = np.asarray(off, dtype=np.float64)
        pxy = np.array([p0[0], p0[1], 0.0])
        mid[:3] = np.linalg.solve(m[:3, :3], -zoom0 * m[:3, 3] - pxy) + pxy

    def out() -> None:
        nonlocal zoom, p
        k = d.path.pop()
        zoom = zoom / r
        p = p - zoom * (1.0 - r) * (spec.centres[k] @ M)

    def into() -> None:
        nonlocal zoom, p
        x = ((mid - p) / zoom) @ M.T        # the middle of the screen, in the shape
        k = int(np.argmin(np.linalg.norm(x - (1.0 - r) * spec.centres, axis=1)))
        p = p + zoom * (1.0 - r) * (spec.centres[k] @ M)
        zoom = zoom * r
        d.path.append(k)

    # a pan off the side of the rooted cell: up until the view is over an
    # ancestor, and the zoom rule below takes it down again beside
    while d.path and np.linalg.norm(mid - p) / zoom > OUTSIDE:
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
    _land(s, reg, zoom0, p0, zoom, p)


def _land(s, reg, zoom0: float, p0: np.ndarray, zoom: float, p: np.ndarray) -> None:
    """The view moved to (`zoom`, `p`) from (`zoom0`, `p0`): the same picture,
    written another way. With a registry through `Param.follow` — camera.zoom
    and camera.pan's objects and bases move together, once, so a route or an
    LFO modulating them rides on the move, still or letting go (writing the
    base and the object apart applied it twice, or lost it at a release: the
    reviews of 2026-11-19); without one onto the view alone."""
    d = s.dive
    d.z, d.w = float(p[2]), float(p[3])
    pan = (float(p[0]), float(-p[1]))
    ids = ("camera.zoom", "camera.pan.x", "camera.pan.y")
    if reg is not None and all(i in reg for i in ids):
        for pid, v in zip(ids, (zoom, *pan), strict=True):
            reg[pid].follow(v)
    s.zoom = zoom
    s.pan[0], s.pan[1] = pan


# ---- plan 64, part 2: what a grab holds, outside a fractal and inside it
#
# Outside, the shape is an object: the world's offset on it (plan 59) is
# drawn home ∘ offset, as any shape's. Inside — once it no longer fits the
# rig's box, or the view has gone into a cell (`wants_inside`) — a grab holds
# the space: its motion is folded into this view (`fold_flight`), turning it
# about the middle of the screen and moving it through the fractal's own 4D
# space, and the offset the object had is kept as `Dive.turn` and
# `Dive.shift` (`go_inside`), handed back when the view comes out
# (`go_outside`). Each crossing redraws nothing.


def _pan3(s) -> np.ndarray:
    return np.array([float(s.pan[0]), -float(s.pan[1]), 0.0])


def drawn_corners(s, off=None) -> np.ndarray:
    """Where the whole shape's own corners are drawn (n, 3, world units),
    the view at the top (path empty: the top cell is the shape at p, radius
    camera.zoom), through the 4D divide and then `off`, the offset composed
    after the walk (home frame; None the identity). The fractal lies within
    their convex hull, and the divide keeps a hull a hull, so they bound
    exactly what is drawn."""
    spec = spec_of(s.shape)
    assert spec is not None
    d = s.dive
    zoom = max(float(s.zoom), 1e-3)
    p = np.array([float(s.pan[0]), -float(s.pan[1]), d.z, d.w])
    d4 = float(s.depth4)
    w_gone = d4 * 2.0 ** -W_GONE
    Q = zoom * (spec.V @ turn(s)) + p
    wf = Q[:, :3] * (d4 / np.maximum(d4 - Q[:, 3], w_gone))[:, None]
    if off is None:
        return wf
    return _offset_world(wf, off, p, zoom)


def wants_inside(s, box, off=None) -> bool:
    """Whether the view of a fractal is inside it (plan 64, part 2): it has
    gone into a cell, or is about to, or the shape no longer fits `box` (the
    rig's: half the view across and up, world units, at depth 0) — what can't
    be kept whole on screen is not an object you hold. Out again only once
    every corner is within `FIT_OUT` of the box and the view is at the top."""
    d = s.dive
    if d.path or float(s.zoom) >= Z_IN:
        return True
    c = drawn_corners(s, off)
    over = float(max(np.abs(c[:, 0]).max() / max(float(box[0]), 1e-9),
                     np.abs(c[:, 1]).max() / max(float(box[1]), 1e-9)))
    return over > (FIT_OUT if d.inside else 1.0)


def go_inside(s, reg, off) -> None:
    """Into the space: the object's offset `off` (home frame, plan 59; None the
    identity) becomes the view's own — its turn `Dive.turn`, about the middle
    of the screen before the 4D divide (where a turn commutes with it), the
    view's camera turned with it, and the rest `Dive.shift`, a move in world
    units after the divide. What is drawn is what was: camera ∘ offset is
    shift ∘ the view turned (a rotation and a uniform scale, which goes on
    camera.zoom)."""
    d = s.dive
    zoom0 = max(float(s.zoom), 1e-3)
    p0 = np.array([float(s.pan[0]), -float(s.pan[1]), d.z, d.w])
    A = np.eye(3) if off is None else np.asarray(off, dtype=np.float64)[:3, :3]
    t = np.zeros(3) if off is None else np.asarray(off, dtype=np.float64)[:3, 3]
    k = float(np.cbrt(abs(np.linalg.det(A))))
    R = A / k
    pxy = np.array([p0[0], p0[1], 0.0])
    d.turn, d.inside, d.flown = R, True, None
    # the walk's point Q turns to R Q, scaled by k about the middle: wf → k R wf
    p = p0.copy()
    p[:3] = k * (R @ p0[:3])
    zoom = zoom0 * k
    d.last *= k                      # (a scale is a zoom, not a move: no ease home)
    d.shift = -A @ pxy + zoom0 * t + pxy
    _land(s, reg, zoom0, p0, zoom, p)


def go_outside(s, reg) -> np.ndarray:
    """Out of the space, at the top: the view's own turn and room placement
    (`Dive.turn`, `Dive.shift`) handed back as the object's offset, returned
    (a 4×4 in the home's frame, for `world`); the view unturned. What is drawn
    is what was."""
    d = s.dive
    zoom = max(float(s.zoom), 1e-3)
    p0 = np.array([float(s.pan[0]), -float(s.pan[1]), d.z, d.w])
    R = np.asarray(d.turn, dtype=np.float64)
    p = p0.copy()
    p[:3] = R.T @ p0[:3]
    pxy = np.array([p[0], p[1], 0.0])
    off = np.eye(4)
    off[:3, :3] = R
    off[:3, 3] = (np.asarray(d.shift) + R @ pxy - pxy) / zoom
    d.inside, d.turn, d.shift, d.flown = False, np.eye(3), np.zeros(3), None
    _land(s, reg, zoom, p0, zoom, p)
    return off


def fold_flight(s, reg, flight: np.ndarray, epoch: int = 0) -> None:
    """Inside, the world's flight pose (`flight`, a 4×4 in world units: the
    shape object's offset, home the identity, moved by the grip and its
    physics) folded into the view: what it moved since the last fold turns the
    space about the middle of the screen and moves it through the fractal's
    own space, before the 4D divide — `Dive.turn`, camera.pan, `Dive.z` — and
    turns the room placement (`Dive.shift`) with it. `epoch`: the world
    object's (`WorldObject.epoch`); a pose rewritten since the last fold — a
    crossing, a deck switch, Reset world — is read afresh, never folded."""
    d = s.dive
    F = np.asarray(flight, dtype=np.float64)
    if d.flown is None or d.flown_epoch != epoch:
        d.flown, d.flown_epoch = F.copy(), epoch
        return
    delta = F @ np.linalg.inv(d.flown)
    d.flown = F.copy()
    R, u = delta[:3, :3], delta[:3, 3]
    if np.allclose(R, np.eye(3), atol=1e-12) and not u.any():
        return
    zoom = max(float(s.zoom), 1e-3)
    p0 = np.array([float(s.pan[0]), -float(s.pan[1]), d.z, d.w])
    p = p0.copy()
    p[:3] = R @ p0[:3] + u
    d.turn = R @ np.asarray(d.turn)
    d.shift = R @ np.asarray(d.shift)
    _land(s, reg, zoom, p0, zoom, p)

def _smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


@dataclass(frozen=True, eq=False)
class Walk:
    """One frame's walk of a fractal (`walk`): which cells are drawn and how
    strongly, and the view they were walked in. What the CPU path makes its
    geometry from (`frame`) and the GPU path its instance rows
    (`instances`), so the two draw the same cells.

    Cells are in the shape's own frame: cell k at scale `s` about `o` (4D)
    is the whole shape × s + o. `line_*`: the cells whose split is drawn
    (their `new_E`, at alpha `line_a`); `face_*`: the cells drawn as solids
    (the faces on); `whole`: the whole shape's own outline is drawn too, at
    (`scale`, `origin`). The view: a point x of the shape is at
    zoom · (x @ M) + p in 4D (before the 4D divide); `off`, the world's
    offset on the shape (plan 59), a 4×4 or None."""

    spec: Fractal
    M: np.ndarray
    p: np.ndarray
    zoom: float
    d4: float
    dist: float
    w_gone: float
    w_near: float
    w_far: float
    w_lost: float
    top: float
    faces: bool
    whole: bool
    scale: float
    origin: np.ndarray
    line_s: np.ndarray
    line_o: np.ndarray
    line_a: np.ndarray
    face_s: np.ndarray
    face_o: np.ndarray
    face_a: np.ndarray
    off: np.ndarray | None = None

    @property
    def cue(self) -> tuple[float, float]:
        """The depth cue's fixed ends (render.draw_scene's near and far)."""
        return (-self.spec.far, self.top)

    def place(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Points X of the shape (n, 4), in its own frame, to what the scene
        pass takes: (P, div4, pd, along) — P before camera.zoom and pan (and
        the world's offset), the 4D divisor, the depth cue and the fade along
        w. The vertex shader's `frac_place` (fractal_gl.py) is this, in float32."""
        Q = self.zoom * (X @ self.M) + self.p
        return self.place_q(Q)

    def place_q(self, Q: np.ndarray):
        """`place` from the points already in the view (4D, before the divide)."""
        p, zoom, d4 = self.p, self.zoom, self.d4
        rho = d4 - Q[:, 3]
        world = Q[:, :3] * (d4 / np.maximum(rho, self.w_gone))[:, None]
        P = world.copy()
        P[:, 0] -= p[0]
        P[:, 1] -= p[1]
        P /= zoom
        along = (_smooth((rho - self.w_gone) / (self.w_near - self.w_gone))
                 * _smooth((self.w_lost - rho) / (self.w_lost - self.w_far)))
        if self.off is not None:
            world = _offset_world(world, self.off, p, zoom)
        range_ = np.sqrt(world[:, 0] ** 2 + world[:, 1] ** 2 + (self.dist - world[:, 2]) ** 2)
        pd = np.clip(-np.log2(np.maximum(range_, 1e-9) / self.dist), -self.spec.far, self.top)
        return P, np.maximum(rho, self.w_gone), pd, along


def _offset_world(c: np.ndarray, off, p: np.ndarray, zoom: float) -> np.ndarray:
    """Points `c` where the walk would put them in the world (3D, after the 4D
    divide), moved by the world's offset on the shape: the renderer's model
    matrix is home ∘ offset (geometry.model_matrix), home being camera.zoom
    and pan, so a point P (the scene pass's, before them) lands at
    zoom · off(P) + pan."""
    m = np.asarray(off, dtype=np.float64)
    pxy = np.array([p[0], p[1], 0.0])
    P = (c - pxy) / zoom
    return zoom * (P @ m[:3, :3].T + m[:3, 3]) + pxy


def walk(spec: Fractal, s, w: int, h: int, off=None) -> Walk:
    """The cells of this frame (module docstring, `Walk`): from the top cell
    down, those the eye can see, split while large on screen, faded in as
    they split and out at the cue's ends, at most `BUDGET` edges. `off`, the
    world's offset on the shape (plan 59, `world.World.offset_matrix`): the
    cull and the cue read where a cell is with it, so a grabbed or moved
    fractal is culled where it is drawn."""
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
    # the offset's own scale (a Pose's), on a cell's reach
    k_off = 1.0 if off is None else float(np.cbrt(abs(np.linalg.det(np.asarray(off)[:3, :3]))))

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

    faces = bool(getattr(s, "faces", False))
    split = spec.split * min(w, h)
    grow = 1.0 / r - 1.0                            # a split is all in by a child's own
    most = BUDGET // max(len(spec.new_E), 1)
    while True:
        sc = np.array([scale])
        og = origin[None]
        got_s, got_o, got_a = [], [], []
        f_s, f_o, f_a = [], [], []                   # the cells drawn as solids (faces)
        under = np.ones(1)                           # how far in each cell's parent's split is
        total = 0
        for level in range(48):
            q = zoom * (og @ M) + p                  # the cells' centres, in 4D
            R4 = zoom * sc
            rho = d4 - q[:, 3]                       # how far along w from the 4D eye
            # through the 4D divide: where the cell lands in the world, and
            # the most its radius can be there (its nearest part along w)
            c = q[:, :3] * (d4 / np.maximum(rho, w_gone))[:, None]
            R = R4 * d4 / np.maximum(rho - R4, w_gone) * k_off
            if off is not None:
                c = _offset_world(c, off, p, zoom)
            depth = dist - c[:, 2]
            range_ = np.sqrt(c[:, 0] ** 2 + c[:, 1] ** 2 + depth ** 2)
            seen = ((rho + R4 > w_gone) & (rho - R4 < w_lost)
                    & (depth + R > EYE_NEAR) & (range_ - R < far) & (range_ + R > gone)
                    & ((np.abs(c[:, 0]) - tx * depth) / nx < R)
                    & ((np.abs(c[:, 1]) - ty * depth) / ny < R))
            size = R4 * k_off * d4 / np.maximum(rho, w_gone) / np.maximum(range_, 1e-9) * px
            go = seen & (size > split)
            first = bare and level == 0
            if first:
                go = np.ones(1, bool)
            # what a split adds comes in over the next factor of 1 / ratio in
            # size, and goes out over the far end of the cue
            cue = -np.log2(np.maximum(range_, 1e-9) / dist)
            fog = (_smooth((cue + spec.far) / (FOG * (top + spec.far)))
                   * _smooth((spec.near - cue) / (spec.near - top)))
            grown = np.where(go, _smooth((size - split) / (split * grow)), 0.0)
            if first:
                grown = np.ones(1)
            if faces:
                # every cell is a solid, the split ones too: its faces came
                # in with its parent's split and stay, so a picture on the
                # faces is there at every size, a small one inside a large
                fa = np.where(seen, under * fog, 0.0)
                keep = fa > 0.004
                f_s.append(sc[keep])
                f_o.append(og[keep])
                f_a.append(fa[keep])
            if not go.any():
                break
            sc, og, fog, grown = sc[go], og[go], fog[go], grown[go]
            got_s.append(sc)
            got_o.append(og)
            got_a.append(grown * fog * spec.ink)
            total += len(sc)
            if total > most:
                break
            n = len(spec.centres)
            og = (og[:, None, :] + (sc * (1.0 - r))[:, None, None] * spec.centres[None]).reshape(-1, 4)
            sc = np.repeat(sc * r, n)
            under = np.repeat(grown, n)
        if total <= most:
            break
        split *= 1.35                                # too much to draw: coarser

    def cat(parts, shape):
        return np.concatenate(parts) if parts else np.zeros(shape)

    return Walk(spec, M, p, zoom, d4, dist, w_gone, w_near, w_far, w_lost, top, faces,
                whole, scale, origin, cat(got_s, (0,)), cat(got_o, (0, 4)), cat(got_a, (0,)),
                cat(f_s, (0,)), cat(f_o, (0, 4)), cat(f_a, (0,)),
                None if off is None else np.asarray(off, dtype=np.float64))


def frame(spec: Fractal, s, w: int, h: int, off=None
          ) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    """This frame's geometry, as `render.draw_scene` takes a shape's:
    (g, P, div4, pd) — g a `geometry.geom` dict with a scene's "style" (each
    edge's and point's own alpha: what a split adds fades in, the far end
    fades out), P the points turned as the view turns the shape (before
    camera.zoom and pan), pd their depth cue and g["cue"] its fixed ends.
    The CPU path, and the oracle the GPU path (`instances`, fractal_gl.py)
    is tested against."""
    return geometry_of(walk(spec, s, w, h, off))


def geometry_of(wk: Walk) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    """`frame` from a walk already made."""
    spec = wk.spec
    nv, ne = len(spec.new_V), len(spec.new_E)
    S, O, A = wk.line_s, wk.line_o, wk.line_a
    if len(S):
        X = (S[:, None, None] * spec.new_V[None] + O[:, None, :]).reshape(-1, 4)
        E = (spec.new_E[None] + (np.arange(len(S)) * nv)[:, None, None]).reshape(-1, 2)
        e_alpha = np.repeat(A, ne)
        p_alpha = (A[:, None] * spec.new_dot[None]).reshape(-1)
    else:
        X, E = np.zeros((0, 4)), np.zeros((0, 2), dtype=np.int64)
        e_alpha, p_alpha = np.zeros(0), np.zeros(0)
    if wk.whole:
        # the whole shape's own outline, while the view can reach it
        E = np.concatenate([E, spec.E + len(X)])
        X = np.concatenate([X, wk.scale * spec.V + wk.origin])
        e_alpha = np.concatenate([e_alpha, np.full(len(spec.E), spec.ink)])
        p_alpha = np.concatenate([p_alpha, np.ones(len(spec.V))])

    # the solids' corners, after the lines' points: no dots of their own
    n_lines = len(X)
    tris, tri_uv, tri_alpha = np.zeros((0, 4), np.int32), np.zeros((0, 3, 2)), np.zeros(0)
    if wk.faces and len(wk.face_s):
        FS, FO, FA = wk.face_s, wk.face_o, wk.face_a
        k = len(spec.V)
        X = np.concatenate([X, (FS[:, None, None] * spec.V[None] + FO[:, None, :]).reshape(-1, 4)])
        p_alpha = np.concatenate([p_alpha, np.zeros(len(FS) * k)])
        ix = spec.tris[None] + (n_lines + np.arange(len(FS)) * k)[:, None, None]
        fid = np.broadcast_to(spec.tri_face[None, :, None], (len(FS), len(spec.tris), 1))
        tris = np.concatenate([ix, fid], axis=2).reshape(-1, 4).astype(np.int32)
        tri_uv = np.broadcast_to(spec.tri_uv[None], (len(FS), *spec.tri_uv.shape)).reshape(-1, 3, 2)
        tri_alpha = np.repeat(FA, len(spec.tris))

    # the points: placed in 4D, through the 4D divide (the eye's side of it
    # clamped: what is that near along w has faded out), then back to what
    # the scene pass takes, before camera.zoom and pan
    P, div4, pd, along = wk.place(X)
    if len(E):
        e_alpha = e_alpha * np.minimum(along[E[:, 0]], along[E[:, 1]])
    p_alpha = p_alpha * along
    if len(tris):
        tri_alpha = tri_alpha * along[tris[:, :3]].min(axis=1)
    n, m = len(X), len(E)
    st = {"e_alpha": e_alpha, "e_width": np.ones(m), "e_rgb": np.ones((m, 3)),
          "e_m": np.full(m, float(DENS_M)), "p_alpha": p_alpha, "p_rgb": np.ones((n, 3)),
          "p_tinted": np.zeros(n, bool),
          "f_alpha": np.ones(int(spec.tri_face.max()) + 1)}
    g = {"V": X, "E": E.astype(np.int32), "n": n, "m": m, "style": st,
         "cue": wk.cue, "dens_m": DENS_M,
         "tris": tris, "tri_uv": tri_uv, "tri_alpha": tri_alpha}
    # (the divisor the face shader multiplies back in: the uv stays
    # perspective-correct across the 4D divide)
    return g, P, div4, pd


def instances(wk: Walk) -> dict[str, np.ndarray]:
    """The GPU path's instance rows (fractal_gl.py), float32, one per cell:
    the cell's centre already in the view (4D, zoom · (o @ M) + p, before the
    divide: the large numbers cancel here, in float64, so the vertex shader
    adds only a cell-sized turn of its mesh), its radius in the view
    (zoom · s) and its alpha. "lines": the split cells (their `new_E`);
    "outline": the whole shape's own (empty unless `whole`); "faces": the
    solids (empty with the faces off)."""
    def rows(S, O, A):
        out = np.empty((len(S), 6), dtype=np.float32)
        if len(S):
            out[:, 0:4] = wk.zoom * (O @ wk.M) + wk.p
            out[:, 4] = wk.zoom * S
            out[:, 5] = A
        return out

    spec = wk.spec
    one = np.ones(1)
    return {
        "lines": rows(wk.line_s, wk.line_o, wk.line_a),
        "outline": rows(one * wk.scale, wk.origin[None], one * spec.ink) if wk.whole
        else np.zeros((0, 6), np.float32),
        "corners": rows(one * wk.scale, wk.origin[None], one) if wk.whole
        else np.zeros((0, 6), np.float32),
        "faces": rows(wk.face_s, wk.face_o, wk.face_a) if wk.faces
        else np.zeros((0, 6), np.float32),
    }
