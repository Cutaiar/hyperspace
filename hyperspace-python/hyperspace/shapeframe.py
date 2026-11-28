"""What the scene pass draws of a shape this frame: one interface,
`provider(i).frame(view, w, h, offset)` → `ShapeFrame`, for every kind of
shape, so `render.draw_scene` draws them all by one rule and asks no shape
what it is.

- **A fixed shape** (a polytope, a solid, a surface, a curve) is its cached
  `geometry.geom`, turned by `geometry.shape_world`.
- **A scene** is its layers, each at its own spin (the same call; the
  scene's per-layer weights are its `style`).
- **A fractal** (fractal.py) is made for the frame: `fractal.walk` picks the
  cells the eye can see. Sorted, the CPU makes their geometry
  (`fractal.geometry_of`) and the pass painter-sorts it as any shape's;
  additive, the cells go to the GPU as instance rows (`walk`, drawn by
  fractal_gl.py) and nothing is sorted.

A fractal's differences from a fixed shape are fields here: the depth
cue's fixed ends (`cue`), the count the stroke density reads (`dens_m`),
whether a legacy stroke scales with camera.zoom (`zoom_strokes`), and the
frame's own triangles and their uvs and weights. For a fixed shape or a
scene every field is what `geometry` gives for it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from . import fractal
from .geometry import face_triangles, face_uvs, geom, shape_world, turned_depth


@dataclass(eq=False)
class ShapeFrame:
    """One frame of a shape, as the scene pass draws it.

    `g`: the geometry dict (`V`, `E`, `n`, `m`, and a scene's `style`, a
    curve's `curve`, a star's `corners`); `P`, `w4`, `pd`: each point in 3D before camera.zoom and
    pan, its 4D divisor and its depth cue (nearer is larger). `cue`: the
    cue's fixed ends, None for `pd`'s own extent. `dens_m`: the edge count
    the stroke density reads. `zoom_strokes`: on the legacy path a stroke
    scales with camera.zoom. `walk`: a fractal drawn on the GPU (its cells;
    `P` is then only their bounding box's corners, for the copies' cull)."""

    g: dict
    P: np.ndarray
    w4: np.ndarray
    pd: np.ndarray
    cue: tuple[float, float] | None = None
    dens_m: int = 0
    zoom_strokes: bool = True
    walk: fractal.Walk | None = None
    # the faces, made only when drawn: (T, 4) corners and face id, (T, 3, 2)
    # uvs, and each triangle's own weight (None: every one 1)
    _faces: Callable[[], tuple] | None = field(default=None, repr=False)

    @property
    def style(self) -> dict | None:
        return self.g.get("style")

    def faces(self) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
        """(tris, uv, alpha): the triangles, (T, 4) — three corners and the
        face — their corners' uvs (T, 3, 2), and each one's weight or None."""
        assert self._faces is not None
        return self._faces()


class Fixed:
    """A shape whose geometry is built once (`geometry.geom`)."""

    def __init__(self, i: int):
        self.i = i

    def frame(self, s, w: int, h: int, offset=None) -> ShapeFrame:
        i = self.i
        g = geom(i)
        P, w4, pd = shape_world(i, s.ang, s.yaw, s.pitch, d4=s.depth4,
                                flat=getattr(s, "held", False), body=getattr(s, "body", None))
        if offset is not None:
            # a turned offset turns a 3D shape before
            # the painter sort and the depth cue read its depth, so it sorts and
            # shades by where it is now; a 4D shape's cue stays its w
            pd = turned_depth(i, P, pd, offset)
        return ShapeFrame(g, P, w4, pd, dens_m=g["m"],
                          _faces=lambda: (face_triangles(i),
                                          face_uvs(i).reshape(-1, 3, 2), None))


class Scene(Fixed):
    """A scene: its layers, each turned at its own spin
    by `shape_world`, each edge's and point's weight its layer's (`style`)."""


class Fractal:
    """A self-similar shape (fractal.py), made for the frame. `additive`:
    the cells go to the GPU unsorted (`view.frac_additive`); else the CPU
    makes the frame's geometry and the pass sorts it."""

    def __init__(self, spec: fractal.Fractal):
        self.spec = spec

    def frame(self, s, w: int, h: int, offset=None) -> ShapeFrame:
        wk = fractal.walk(self.spec, s, w, h, offset)
        if getattr(s, "frac_additive", False):
            return self._gpu(wk)
        g, P, w4, pd = fractal.geometry_of(wk)
        return ShapeFrame(g, P, w4, pd, cue=g["cue"], dens_m=g["dens_m"], zoom_strokes=False,
                          _faces=lambda: (g["tris"], g["tri_uv"], g["tri_alpha"]))

    @staticmethod
    def _gpu(wk: fractal.Walk) -> ShapeFrame:
        # the cells' reach as a box, for the copies' cull (render._copies_of):
        # each cell's centre ± its radius, placed as its points would be
        X = np.concatenate([wk.line_o, wk.face_o, wk.origin[None]])
        R = np.concatenate([wk.line_s, wk.face_s, [wk.scale]])
        P, div4, _, _ = wk.place(X)
        r = (R * wk.d4 / div4)[:, None]              # its radius, through the 4D divide
        box = np.concatenate([P - r, P + r])
        g = {"V": X, "E": np.zeros((0, 2), np.int32), "n": len(box), "m": 0}
        return ShapeFrame(g, box, np.ones(len(box)), np.zeros(len(box)), cue=wk.cue,
                          dens_m=fractal.DENS_M, zoom_strokes=False, walk=wk,
                          _faces=lambda: (np.zeros((0, 4), np.int32), np.zeros((0, 3, 2)), None))


def drawn_offset(s, world_off=None, bounded: bool = True):
    """The offset the scene pass composes after the shape's own geometry (a
    4×4 in the home's frame, as `world.World.offset_matrix`; None the
    identity). A fractal the view is inside draws the room
    placement it had as an object (`Dive.shift`, fixed in world units: in the
    home's frame ÷ camera.zoom); its flight is folded into the view itself.
    Otherwise the world's offset on the shape — while the world's shape is
    an object (`bounded`); while it is the space, no shape draws it."""
    d = getattr(s, "dive", None)
    if d is not None and d.inside and fractal.spec_of(s.shape) is not None:
        sh = np.asarray(d.shift, dtype=np.float64)
        if not sh.any():
            return None
        m = np.eye(4)
        m[:3, 3] = sh / max(float(s.zoom), 1e-3)
        return m
    return world_off if bounded else None


def provider(i: int, by_geom: bool = False) -> Fixed | Fractal:
    """Shape i's provider: a fractal's, a scene's or a fixed shape's.
    `by_geom`: a fractal as its built levels (a view with no `dive`, which
    cannot be zoomed into)."""
    spec = fractal.spec_of(i)
    if spec is not None and not by_geom:
        return Fractal(spec)
    if geom(i).get("layers"):
        return Scene(i)
    return Fixed(i)


def frame(s, w: int, h: int, offset=None) -> ShapeFrame:
    """The shape `s` shows, this frame (`provider(s.shape).frame`)."""
    return provider(s.shape, by_geom=not hasattr(s, "dive")).frame(s, w, h, offset)
