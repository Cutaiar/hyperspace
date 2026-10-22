"""The instance field: where each copy of the shape sits on screen.

The renderer projects the shape once and the GPU draws it once per copy
(render.py, instanced draws). What it needs per copy is four numbers —
the copy's centre on screen, its scale and its alpha — and that is all
this module makes. Pure numpy and no GL, so the layouts, the fit and the
cull are tested without a context.

Units. A *cell* is the room one copy is given: ``CELL · min(w, h)`` px
at zoom 1, the spacing between neighbours in every layout. Every shape's
projected diameter stays under ``SHAPE_EXTENT`` of a cell whatever its
pose (measured over every shape; geometry normalises them), so copies a
cell apart never touch and a copy given a whole cell inside the screen is
never cut by its edge.

Layouts. Three are flat, in the screen's plane — GRID, HEX (a honeycomb
spiral from the centre), RING. Six are 3D lattices with the nearest
neighbours one cell apart — CUBIC, BCC, FCC, HCP, HEX PRISM (stacked
honeycombs), DIAMOND — turned by the view's camera (yaw and pitch, the
turn every copy's own projection takes) and seen through the field's own
perspective (`perspective`): copies nearer the viewer are drawn larger
and brighter, and the field is drawn far to near so the painter's order
holds between copies as it does inside one.

Fit (`view.inst_fit`). Off, the field is laid out about the centre and the
camera's zoom and pan look over it: copies past the edge are cut, as they
always were. On, the field is fitted to the screen: a flat grid or
honeycomb takes the rows and columns that give a copy the most room at
the screen's aspect (whole rows; a part row is centred) and stretches to
partition the screen exactly, so every copy sits whole in its own cell
and the margins are symmetric. Zooming in then snaps to whole cells —
the screen shows k columns by j rows, its edges on cell boundaries — and
pan moves the window a whole cell at a time. A ring or a lattice is
framed whole, centred, every copy's room inside the screen; zoom past 1
magnifies it about the centre.

Copies wholly off screen are dropped (`cull`), so a zoomed-in field of
thousands costs what it shows.
"""

from __future__ import annotations

import math
from functools import lru_cache

import numpy as np

from .geometry import _camera

CELL = 0.72            # a cell, as a fraction of the viewport's shorter side, at zoom 1
SHAPE_EXTENT = 0.94    # the widest any shape's projection gets, in cells (any pose)
PAD_PX = 5.0           # what a copy draws past its vertices at scale 1: a point's radius, half a line
EDGE_PX = 1.5          # and at any scale: a line or point is never drawn under a pixel
MAX_INSTANCES = 4096   # the instance count's top (params.T_INSTANCES)

(LAYOUT_GRID, LAYOUT_HEX, LAYOUT_RING,
 LAYOUT_CUBIC, LAYOUT_BCC, LAYOUT_FCC, LAYOUT_HCP, LAYOUT_HEXPRISM, LAYOUT_DIAMOND) = range(9)
# params.INST_LAYOUT's names, in this order
NAMES = ["GRID", "HEX", "RING", "CUBIC", "BCC", "FCC", "HCP", "HEX PRISM", "DIAMOND"]
LAYOUTS_3D = frozenset(range(LAYOUT_CUBIC, LAYOUT_DIAMOND + 1))
SNAPS = frozenset((LAYOUT_GRID, LAYOUT_HEX))   # fitted layouts whose zoom snaps to cells

_HEX_STEPS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))   # axial (q, r)
_R3 = math.sqrt(3.0)


def is_3d(layout: int) -> bool:
    return int(layout) in LAYOUTS_3D


# ---- the flat layouts, about the centre (fit off) ----

@lru_cache(maxsize=32)
def _hex_spiral(n: int) -> np.ndarray:
    """The first `n` cells of a honeycomb spiral as (n, 2) float64 (gx, gy):
    the centre, then ring 1 (six cells), ring 2 (twelve), ring m (6m), each
    walked from axial (−m, m) taking m steps along each direction in turn.
    A cell's place does not depend on `n`."""
    out = [(0.0, 0.0)]
    m = 0
    while len(out) < n:
        m += 1
        q, r = -m, m
        for dq, dr in _HEX_STEPS:
            for _ in range(m):
                out.append((q + r / 2, r * _R3 / 2))
                q, r = q + dq, r + dr
    cells = np.array(out[:n], dtype=np.float64).reshape(-1, 2)
    cells.setflags(write=False)
    return cells


def inst_positions(n: int, layout: int) -> tuple[np.ndarray, np.ndarray]:
    """(gx, gy) for `n` copies, float32, in cells, y down: where each copy
    sits about the centre before the camera. Pure: no GL, no state.

    GRID (and any layout it does not know) — rows of ``ceil(sqrt(n))``,
    centred. HEX — a honeycomb spiral from the centre: whole hexagons at
    7, 19, 37, 61 and 91, and a copy never moves as the count grows.
    RING — one circle, copy 0 at the top, clockwise on screen (y is down),
    its radius ``1 / (2 sin(π / n))`` so neighbours stay one cell apart.
    A 3D lattice — its front view, unturned: (x, −y) of `lattice`.

    No copies is two empty arrays and one copy is the centre, in every
    layout."""
    n = max(0, int(n))
    if n == 0:
        return np.zeros(0, dtype=np.float32), np.zeros(0, dtype=np.float32)
    if layout == LAYOUT_HEX:
        cells = _hex_spiral(n)
        return cells[:, 0].astype(np.float32), cells[:, 1].astype(np.float32)
    if layout == LAYOUT_RING:
        if n == 1:
            return np.zeros(1, dtype=np.float32), np.zeros(1, dtype=np.float32)
        radius = 1.0 / (2.0 * math.sin(math.pi / n))
        th = 2.0 * math.pi * np.arange(n, dtype=np.float64) / n
        return ((radius * np.sin(th)).astype(np.float32),
                (-radius * np.cos(th)).astype(np.float32))
    if is_3d(layout):
        p = lattice(n, int(layout))
        return p[:, 0].astype(np.float32), (-p[:, 1]).astype(np.float32)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    k = np.arange(n, dtype=np.float32)
    gx = k % cols - (cols - 1) / 2      # grid position about the centre
    gy = k // cols - (rows - 1) / 2
    return gx, gy


# ---- the 3D lattices: nearest neighbours one cell apart ----

def _basis(layout: int) -> tuple[np.ndarray, np.ndarray, float]:
    """(basis as columns, the motif's points, points per cell³) — x right,
    y up, z toward the viewer; layers (HCP, HEX PRISM) stack along z."""
    eye = np.eye(3)
    if layout == LAYOUT_BCC:
        a = 2.0 / _R3
        return eye * a, np.array([[0, 0, 0], [0.5, 0.5, 0.5]]) * a, 2.0 / a ** 3
    if layout == LAYOUT_FCC:
        a = math.sqrt(2.0)
        motif = np.array([[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]) * a
        return eye * a, motif, 4.0 / a ** 3
    if layout == LAYOUT_DIAMOND:
        a = 4.0 / _R3
        fcc = np.array([[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]])
        return eye * a, np.vstack([fcc, fcc + 0.25]) * a, 8.0 / a ** 3
    if layout == LAYOUT_HCP:
        c = math.sqrt(8.0 / 3.0)
        b = np.array([[1.0, -0.5, 0.0], [0.0, _R3 / 2, 0.0], [0.0, 0.0, c]])
        motif = np.array([[0.0, 0.0, 0.0], [0.0, 1.0 / _R3, c / 2]])
        return b, motif, 2.0 / (_R3 / 2 * c)
    if layout == LAYOUT_HEXPRISM:
        b = np.array([[1.0, 0.5, 0.0], [0.0, _R3 / 2, 0.0], [0.0, 0.0, 1.0]])
        return b, np.zeros((1, 3)), 1.0 / (_R3 / 2)
    return eye, np.zeros((1, 3)), 1.0          # CUBIC


def _points_in_cube(layout: int, half: float) -> np.ndarray:
    """Every lattice point with |x|, |y|, |z| ≤ `half` — all of them: the
    index range covers the cube's corners pulled back through the basis."""
    b, motif, _ = _basis(layout)
    inv = np.linalg.inv(b)
    corners = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1)
                        for sz in (-1, 1)], dtype=np.float64) * half
    idx = corners @ inv.T
    lo = np.floor(idx.min(axis=0)) - 1
    hi = np.ceil(idx.max(axis=0)) + 1
    axes = [np.arange(lo[k], hi[k] + 1) for k in range(3)]
    ijk = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
    base = ijk @ b.T
    pts = (base[:, None, :] + motif[None, :, :]).reshape(-1, 3)
    keep = (np.abs(pts) <= half + 1e-9).all(axis=1)
    return pts[keep]


def _select(pts: np.ndarray, d: np.ndarray, n: int, box: bool) -> np.ndarray:
    """The first `n` of `pts` by `d`; ties — a shell's points — the nearest
    the viewer, the highest, the leftmost, and in a box first by distance
    from the centre (its part shell fills from its faces' middles out, so
    it grows symmetrically)."""
    keys = (np.round(pts[:, 0], 6), -np.round(pts[:, 1], 6), -np.round(pts[:, 2], 6))
    if box:
        keys = (*keys, np.round(np.sqrt((pts * pts).sum(axis=1)), 6))
    return pts[np.lexsort((*keys, np.round(d, 6)))[:n]]


@lru_cache(maxsize=64)
def _lattice(n: int, layout: int, box: tuple[float, float, float] | None) -> np.ndarray:
    b, _, rho = _basis(layout)
    ext = np.ones(3) if box is None else np.asarray(box, dtype=np.float64) / max(box)
    # a cube big enough to hold n points inside the selection's metric
    # (with a cell to spare for a box's shifted centre), grown until it does
    half = max(1.0, (n / (rho * 8.0 * float(np.prod(ext)))) ** (1 / 3) + 1.0)
    while True:
        pts = _points_in_cube(layout, half + 1.0)
        if box is None:
            d = np.sqrt((pts * pts).sum(axis=1))
            if (d <= half).sum() >= n:
                break
        elif ((np.abs(pts) / ext).max(axis=1) <= half).sum() >= n:
            break
        half *= 1.4
    if box is None:
        keep = d <= half
        out = _select(pts[keep], d[keep], n, False)
    else:
        # a brick may centre on a point or between points along each basis
        # vector (an even count of layers): take the centre whose n-th point
        # closes its shell, or leaves the least of it open
        best = None
        for f in ((0, 0, 0), (0.5, 0, 0), (0, 0.5, 0), (0, 0, 0.5), (0.5, 0.5, 0),
                  (0.5, 0, 0.5), (0, 0.5, 0.5), (0.5, 0.5, 0.5)):
            q = pts - b @ np.asarray(f, dtype=np.float64)
            dq = np.round((np.abs(q) / ext).max(axis=1), 6)
            keep = dq <= half
            dk = np.sort(dq[keep])
            if len(dk) < n:
                continue
            last = dk[n - 1]
            open_ = int(np.searchsorted(dk, last, side="right")) - n
            if best is None or open_ < best[0]:
                best = (open_, q[keep], dq[keep])
        out = _select(best[1], best[2], n, True)
        out = out - (out.min(axis=0) + out.max(axis=0)) / 2     # the box about the centre
    out.setflags(write=False)
    return out


def lattice(n: int, layout: int, box: tuple[float, float, float] | None = None) -> np.ndarray:
    """`n` points of a 3D lattice as (n, 3) float64, in cells, y up and z
    toward the viewer. `box` None: a ball grown from a lattice point at the
    origin, nearest first, so a copy never moves as the count grows. A box
    (its half-extents' proportions): the n points nearest the centre in
    that box's metric — a brick of the screen's shape — about the centre.
    Cached; the array is read-only."""
    n = max(0, int(n))
    if n == 0:
        return np.zeros((0, 3))
    if box is not None:
        box = tuple(round(float(v), 2) for v in box)
    return _lattice(n, int(layout) if is_3d(layout) else LAYOUT_CUBIC, box)


# ---- fitted flat layouts: rows and columns for the screen ----

def _hex_count(cols: int, rows: int) -> int:
    """Copies in `rows` rows that alternate `cols` and `cols − 1`."""
    return (rows + 1) // 2 * cols + rows // 2 * (cols - 1)


def _hex_room(sx: float, sy: float) -> float:
    """The room a copy has in a honeycomb stretched by (sx, sy) px per
    cell: its nearest neighbour along a row or in the next row half a cell
    over, and no more than a cell's height (the top and bottom rows' copies
    sit half a cell inside the screen)."""
    return min(sx, sy, math.hypot(0.5 * sx, _R3 / 2 * sy))


@lru_cache(maxsize=256)
def fit_dims(n: int, layout: int, aspect: float) -> tuple[int, int]:
    """(columns, rows) for `n` copies fitted to a screen `aspect` (w / h)
    wide: the arrangement that gives a copy the most room, with no empty
    row. Among those within a fifth of the best, a full one (no part row)
    is preferred, then the roomier. HEX rows alternate columns and
    columns − 1, so the honeycomb is symmetric."""
    n = max(1, int(n))
    hexl = layout == LAYOUT_HEX
    cands = []
    for cols in range(1, n + 1):
        if hexl:
            if cols == 1:
                rows = n if n == 1 else 0
                if not rows:
                    continue
            else:
                rows = 1
                while _hex_count(cols, rows) < n:
                    rows += 1
            full = _hex_count(cols, rows)
            last = cols if rows % 2 else cols - 1
            if rows > 1 and full - last >= n:
                continue
            height = (rows - 1) * _R3 / 2 + 1
            room = _hex_room(aspect / cols, 1.0 / height) if cols > 1 else min(
                aspect, 1.0 / n)
        else:
            rows = math.ceil(n / cols)
            if (rows - 1) * cols >= n:
                continue
            full = cols * rows
            room = min(aspect / cols, 1.0 / rows)
        cands.append((room, full == n, cols, rows))
    best = max(c[0] for c in cands)
    near = [c for c in cands if c[0] >= 0.8 * best]
    room, _, cols, rows = max(near, key=lambda c: (c[1], c[0], -c[2]))
    return cols, rows


def _rows(n: int, cols: int, rows: int, hexl: bool) -> np.ndarray:
    """(n, 2) float64 (x, y) in cells about the centre, y down, rows top to
    bottom: each row centred, the part row last; HEX rows alternate
    `cols` and `cols − 1` (the narrow ones sit half a cell over)."""
    out = np.empty((n, 2))
    k = 0
    pitch = _R3 / 2 if hexl else 1.0
    for r in range(rows):
        width = cols - (r % 2) if hexl and cols > 1 else cols
        m = min(width, n - k)
        x = np.arange(m) - (m - 1) / 2
        if hexl and (width - m) % 2:        # a part row keeps its half-cell offset
            x = x + 0.5
        out[k:k + m, 0] = x
        out[k:k + m, 1] = (r - (rows - 1) / 2) * pitch
        k += m
        if k >= n:
            break
    return out


@lru_cache(maxsize=256)
def _fit_rows(n: int, layout: int, aspect: float) -> tuple[np.ndarray, int, int]:
    cols, rows = fit_dims(n, layout, aspect)
    out = _rows(n, cols, rows, layout == LAYOUT_HEX)
    out.setflags(write=False)
    return out, cols, rows


# ---- the field, per frame ----

def _motion(g: np.ndarray, mode: int, amp: float, ph: float) -> np.ndarray:
    """Each copy's displacement, in cells: (n, 2) for a flat field (y
    down), (n, 3) for a lattice (y up). The phase comes from the copy's
    place, so the field moves as one figure."""
    if not mode or amp <= 0.0 or not len(g):
        return np.zeros_like(g)
    flat = g.shape[1] == 2
    gx, gy = g[:, 0], g[:, 1]
    gz = np.zeros_like(gx) if flat else g[:, 2]
    if mode == 1:      # ORBIT — circles in a traveling wave
        th = ph + (gx + gy + gz) * 0.9
        d = [np.cos(th), np.sin(th), np.zeros_like(th)]
    elif mode == 2:    # WAVE — bob by column, sway by row
        d = [0.35 * np.sin(ph * 0.7 + gy * 1.1), np.sin(ph + gx * 1.1),
             0.35 * np.sin(ph * 0.9 + (gx - gy) * 0.8)]
    else:              # RIPPLE — radial swell from the centre
        rr = np.sqrt(gx * gx + gy * gy + gz * gz)
        u = np.sin(ph - rr * 1.2) / np.maximum(rr, 1.0)
        d = [gx * u, gy * u, gz * u]
    return amp * np.stack(d[:g.shape[1]], axis=1)


def perspective(z: np.ndarray, radius: float, persp: float) -> np.ndarray:
    """The field's own perspective: each copy's scale from its depth `z`
    (cells, toward the viewer). The eye sits so that the nearest a copy
    can be (`radius` from the centre) is drawn 1 + 1.5·persp times its
    size at the centre; 0 is orthographic, every copy one size."""
    mag = 1.0 + 1.5 * max(float(persp), 0.0)
    if mag <= 1.0 + 1e-6 or radius <= 0.0:
        return np.ones_like(z)
    eye = radius * mag / (mag - 1.0)
    return eye / np.maximum(eye - z, 0.25 * eye)     # never past 4×, whatever moves


def field(s, w: float, h: float, t: float = 0.0, radius_px: float | None = None,
          pad_px: float = PAD_PX) -> np.ndarray:
    """Where the copies of view `s` go in a (w, h) viewport at time `t`:
    (m, 4) float32 rows of (cx, cy, k, alpha) — each drawn copy's centre
    on screen (logical px), its scale against the shape at zoom 1, and its
    alpha. Ordered far to near; copies wholly off screen are dropped when
    `radius_px` (the shape's projected radius at zoom 1) is given. Fit
    gives each copy room for its widest pose and `pad_px` round it. No
    copies is (0, 4).

    One copy with fit off is the camera alone: centre + pan, scale zoom."""
    n = max(0, int(s.instances))
    if n == 0:
        return np.zeros((0, 4), dtype=np.float32)
    layout = int(getattr(s, "inst_layout", 0))
    fit = bool(getattr(s, "inst_fit", False))
    spacing = max(float(getattr(s, "inst_spacing", 1.0)), 0.05)
    persp = float(getattr(s, "inst_persp", 0.5))
    zoom = max(float(s.zoom), 1e-3)
    pan = (float(s.pan[0]), float(s.pan[1]))
    cell0 = CELL * min(w, h)                    # a cell at zoom 1, px
    # the widest a copy draws at scale 1, in cells — never under one, so a
    # fitted copy keeps the gap it has a cell from its neighbour
    size = max(1.0, (SHAPE_EXTENT * cell0 + 2.0 * max(pad_px, 0.0)) / cell0)
    ph = t * float(s.inst_rate)
    mode, amp = int(s.inst_motion), float(s.inst_amp)
    if n == 1 and not fit:
        return np.array([[w / 2 + pan[0], h / 2 + pan[1], zoom, 1.0]], dtype=np.float32)
    if is_3d(layout):
        out = _field_3d(n, layout, fit, spacing, persp, zoom, pan, w, h, cell0, size,
                        s.yaw, s.pitch, mode, amp, ph)
    elif fit and layout in SNAPS:
        out = _field_snapped(n, layout, spacing, zoom, pan, w, h, cell0, size, mode, amp, ph)
    elif fit:
        out = _field_framed_flat(n, layout, spacing, zoom, pan, w, h, cell0, size, mode, amp,
                                 ph)
    else:
        gx, gy = inst_positions(n, layout)
        cell = cell0 * zoom
        g = np.stack([gx, gy], axis=1).astype(np.float64)
        d = _motion(g, mode, amp, ph)
        # the copies' offsets as the pre-field renderer made them, in float32
        offs = np.stack([gx * cell * spacing, gy * cell * spacing], axis=1).astype(np.float32)
        offs[:, 0] += (cell * d[:, 0]).astype(np.float32)
        offs[:, 1] += (cell * d[:, 1]).astype(np.float32)
        out = np.empty((n, 4), dtype=np.float64)
        out[:, 0] = w / 2 + pan[0] + offs[:, 0].astype(np.float64)
        out[:, 1] = h / 2 + pan[1] + offs[:, 1].astype(np.float64)
        out[:, 2] = zoom
        out[:, 3] = 1.0
    if radius_px is not None:
        out = cull(out, w, h, radius_px)
    return out.astype(np.float32)


def _field_snapped(n, layout, spacing, zoom, pan, w, h, cell0, size, mode, amp,
                   ph) -> np.ndarray:
    """A fitted grid or honeycomb: the screen partitioned into its cells.
    At zoom ≤ 1 the whole field; past it the window k columns by j rows,
    each rounded from the field's over the zoom, its edges on cell
    boundaries, moved by the pan a whole cell at a time."""
    hexl = layout == LAYOUT_HEX
    pos, cols, rows = _fit_rows(n, layout, round(w / h, 3))
    z = max(zoom, 1.0)
    kx = min(max(round(cols / z), 1), cols)
    ky = min(max(round(rows / z), 1), rows)
    pitch = _R3 / 2 if hexl else 1.0
    span_y = (ky - 1) * pitch + 1.0             # the window's height in cells
    sx, sy = w / kx, h / span_y                 # px per cell, each way
    # the window's top-left cell: centred on the field, then the pan in
    # whole cells (dragging right shows what is to the left), held inside
    cx = min(max((cols - kx) // 2 - _cells(pan[0] / sx), 0), cols - kx)
    cy = min(max((rows - ky) // 2 - _cells(pan[1] / (sy * pitch)), 0), rows - ky)
    x0 = -cols / 2 + cx                         # the window's left edge, field cells
    y0 = (cy - (rows - 1) / 2) * pitch - 0.5    # its top edge
    room = _hex_room(sx, sy) if hexl else min(sx, sy)
    d = _motion(pos, mode, amp, ph) * room
    out = np.empty((n, 4))
    out[:, 0] = (pos[:, 0] - x0) * sx + d[:, 0]
    out[:, 1] = (pos[:, 1] - y0) * sy + d[:, 1]
    out[:, 2] = max(room - 2.0 * EDGE_PX, 0.5) / (cell0 * max(spacing, size))   # inside its room
    out[:, 3] = 1.0
    return out


def _cells(x: float) -> int:
    """A pan in cells, to the nearest whole one (halves away from zero)."""
    return int(math.copysign(math.floor(abs(x) + 0.5), x))


def _framed(q: np.ndarray, k: np.ndarray, zoom, pan, w, h, cell0):
    """Fit points `q` (cells, y down, each copy `k` cells wide) whole and
    centred in the viewport; past zoom 1, magnify about the centre and
    pan. (centres px, px per cell)."""
    lo = (q - 0.5 * k[:, None]).min(axis=0)
    hi = (q + 0.5 * k[:, None]).max(axis=0)
    bw, bh = max(hi[0] - lo[0], 1e-6), max(hi[1] - lo[1], 1e-6)
    u = min(max(w - 2.0 * EDGE_PX, 1.0) / bw, max(h - 2.0 * EDGE_PX, 1.0) / bh)
    z = max(zoom, 1.0)
    mid = (lo + hi) / 2
    c = np.empty_like(q)
    c[:, 0] = w / 2 + (q[:, 0] - mid[0]) * u * z + (pan[0] if z > 1.0 else 0.0)
    c[:, 1] = h / 2 + (q[:, 1] - mid[1]) * u * z + (pan[1] if z > 1.0 else 0.0)
    return c, u * z


def _field_framed_flat(n, layout, spacing, zoom, pan, w, h, cell0, size, mode, amp, ph):
    """A fitted ring (or any flat layout that does not snap): framed whole."""
    gx, gy = inst_positions(n, layout)
    g = np.stack([gx, gy], axis=1).astype(np.float64)
    q = g * spacing + _motion(g, mode, amp, ph)
    c, u = _framed(q, np.full(n, size), zoom, pan, w, h, cell0)
    out = np.empty((n, 4))
    out[:, :2] = c
    out[:, 2] = u / cell0
    out[:, 3] = 1.0
    return out


def _field_3d(n, layout, fit, spacing, persp, zoom, pan, w, h, cell0, size,
              yaw, pitch, mode, amp, ph) -> np.ndarray:
    """A lattice: turned by the camera, through the field's perspective,
    far to near; dimmer with distance. Fit off: about the centre at the
    camera's zoom and pan. On: a brick of the screen's shape, framed."""
    box = (w / h, 1.0, 1.0) if fit else None
    g = lattice(n, layout, box)
    # the eye is placed from the still field, so the motion never moves it
    radius = float(np.sqrt((g * g).sum(axis=1)).max()) * spacing + 0.5
    g = g * spacing + _motion(g, mode, amp, ph)
    x1, y1, z1 = _camera(g[:, 0], g[:, 1], g[:, 2], yaw, pitch)
    kp = perspective(z1, radius, persp)
    q = np.stack([x1 * kp, -y1 * kp], axis=1)
    out = np.empty((n, 4))
    if fit:
        c, u = _framed(q, kp * size, zoom, pan, w, h, cell0)
        out[:, :2] = c
        out[:, 2] = kp * u / cell0
    else:
        cell = cell0 * zoom
        out[:, 0] = w / 2 + pan[0] + q[:, 0] * cell
        out[:, 1] = h / 2 + pan[1] + q[:, 1] * cell
        out[:, 2] = kp * zoom
    # depth fade: the nearest copy at full alpha, the farthest at a quarter
    near, far = z1.max(), z1.min()
    tz = (near - z1) / max(near - far, 1e-6)
    out[:, 3] = 1.0 - 0.75 * tz
    return out[np.argsort(z1, kind="stable")]       # far first: the painter's order


def cull(rows: np.ndarray, w: float, h: float, radius_px: float) -> np.ndarray:
    """The rows of `field` whose copy reaches into the (w, h) viewport: a
    copy is its centre and `radius_px · k` about it."""
    if not len(rows):
        return rows
    r = radius_px * rows[:, 2]
    keep = ((rows[:, 0] + r >= 0) & (rows[:, 0] - r <= w)
            & (rows[:, 1] + r >= 0) & (rows[:, 1] - r <= h))
    return rows[keep]
