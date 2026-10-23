"""The instance field (field.py): the 3D lattices, the fit to the screen,
the snapped zoom and pan, the painter's order between copies and the cull.
Pure numpy — no GL. The frames these rows draw are tests/test_render.py's."""

import math

import numpy as np
import pytest

from hyperspace import field as F
from hyperspace.view import ViewState

ASPECTS = ((1600, 900), (1000, 1000), (900, 1600), (1200, 900))
LATTICES = sorted(F.LAYOUTS_3D)


def _view(n, layout=0, **kw) -> ViewState:
    s = ViewState(instances=n, inst_layout=layout)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def _nearest(p):
    d = np.sqrt(((p[:, None, :] - p[None, :, :]) ** 2).sum(axis=-1))
    np.fill_diagonal(d, np.inf)
    return d.min(axis=1)


def test_every_lattice_has_its_neighbours_one_cell_apart():
    """CUBIC, BCC, FCC, HCP, HEX PRISM and DIAMOND: every point's nearest
    neighbour one cell away, none closer, in a ball and in a brick — and
    each has its own coordination (the number at that distance)."""
    want = {F.LAYOUT_CUBIC: 6, F.LAYOUT_BCC: 8, F.LAYOUT_FCC: 12, F.LAYOUT_HCP: 12,
            F.LAYOUT_HEXPRISM: 8, F.LAYOUT_DIAMOND: 4}
    for layout in LATTICES:
        for box in (None, (16 / 9, 1.0, 1.0)):
            p = F.lattice(400, layout, box)
            assert p.shape == (400, 3) and np.isfinite(p).all()
            assert np.allclose(_nearest(p), 1.0, atol=1e-9), (F.NAMES[layout], box)
        # the centre point of a ball has its whole first shell
        p = F.lattice(400, layout)
        d = np.sqrt((p * p).sum(axis=1))
        assert np.array_equal(p[0], [0, 0, 0])
        assert (np.abs(d - 1.0) < 1e-9).sum() == want[layout], F.NAMES[layout]


def test_a_ball_grows_and_a_copy_never_moves():
    """Fit off, a lattice grows from the centre, nearest first, and the
    first n of a bigger field are the field of n."""
    for layout in LATTICES:
        big = F.lattice(1500, layout)
        r = np.sqrt((big * big).sum(axis=1))
        assert (np.diff(r) >= -1e-9).all(), F.NAMES[layout]
        for n in (1, 2, 13, 100, 777):
            assert np.array_equal(F.lattice(n, layout), big[:n]), (F.NAMES[layout], n)


def test_a_brick_takes_the_screens_shape_about_the_centre():
    """Fit on, a lattice is the screen's shape: wider than tall on a wide
    screen, taller on a tall one, centred."""
    for layout in LATTICES:
        for aspect in (16 / 9, 9 / 16):
            p = F.lattice(600, layout, (aspect, 1.0, 1.0))
            lo, hi = p.min(axis=0), p.max(axis=0)
            assert np.allclose((lo + hi) / 2, 0.0, atol=1e-9)
            ext = hi - lo
            assert (ext[0] > ext[1]) == (aspect > 1), (F.NAMES[layout], aspect, ext)
    cube = F.lattice(4096, F.LAYOUT_CUBIC, (1.0, 1.0, 1.0))     # 16³ on a square screen
    assert all(len(np.unique(np.round(cube[:, k], 6))) == 16 for k in range(3))


def test_the_flat_fit_takes_whole_rows():
    """Rows and columns for the screen: room for every copy, no empty row,
    the most room per copy, a full rectangle when one is nearly as roomy."""
    for n in range(1, 160):
        for w, h in ASPECTS:
            for layout in (F.LAYOUT_GRID, F.LAYOUT_HEX):
                cols, rows = F.fit_dims(n, layout, w / h)
                if layout == F.LAYOUT_GRID:
                    assert cols * rows >= n > (rows - 1) * cols, (n, w, h)
                else:
                    assert F._hex_count(cols, rows) >= n or (cols, rows) == (1, 1)
    assert F.fit_dims(12, F.LAYOUT_GRID, 16 / 9) == (4, 3)       # the visual equation
    assert F.fit_dims(7, F.LAYOUT_GRID, 16 / 9) == (4, 2)        # 4 over 3, the 3 centred
    assert F.fit_dims(64, F.LAYOUT_GRID, 1.0) == (8, 8)
    assert F.fit_dims(2, F.LAYOUT_GRID, 16 / 9) == (2, 1)
    assert F.fit_dims(2, F.LAYOUT_GRID, 9 / 16) == (1, 2)
    pos, cols, rows = F._fit_rows(7, F.LAYOUT_GRID, 16 / 9)
    assert np.allclose(pos[4:, 0], [-1, 0, 1])                    # the part row is centred
    pos, cols, rows = F._fit_rows(19, F.LAYOUT_HEX, 1.0)
    assert np.allclose(np.sort(pos[:, 0]).sum(), 0.0)             # a symmetric honeycomb


def _inside(rows, w, h, radius):
    r = radius * rows[:, 2]
    return ((rows[:, 0] - r >= -1e-3) & (rows[:, 0] + r <= w + 1e-3)
            & (rows[:, 1] - r >= -1e-3) & (rows[:, 1] + r <= h + 1e-3))


def _outside(rows, w, h, radius):
    r = radius * rows[:, 2]
    return ((rows[:, 0] + r <= 1e-3) | (rows[:, 0] - r >= w - 1e-3)
            | (rows[:, 1] + r <= 1e-3) | (rows[:, 1] - r >= h - 1e-3))


@pytest.mark.parametrize("layout", range(9), ids=F.NAMES)
def test_fit_puts_every_copy_whole_on_the_screen(layout):
    """Fit on, still, at zoom 1: every copy's widest pose inside the
    screen, at every count, aspect and camera turn — nothing is cut."""
    for w, h in ASPECTS:
        radius = F.SHAPE_EXTENT / 2 * F.CELL * min(w, h) + F.PAD_PX
        for n in (1, 2, 3, 7, 12, 50, 333):
            for yaw, pitch in ((0.0, 0.0), (0.7, -0.4)):
                s = _view(n, layout, inst_fit=True, yaw=yaw, pitch=pitch)
                rows = F.field(s, w, h)
                assert len(rows) == n
                assert _inside(rows, w, h, radius).all(), (n, w, h, yaw)
    # and the camera's zoom out and pan cannot push it off
    s = _view(40, layout, inst_fit=True, zoom=0.2, pan=[300.0, -200.0])
    radius = F.SHAPE_EXTENT / 2 * F.CELL * 900
    assert _inside(F.field(s, 1600, 900), 1600, 900, radius).all()


def test_fit_off_is_the_field_as_it_was():
    """Fit off, flat: about the centre at the camera's zoom and pan, a cell
    apart, one scale, full alpha — copies past the edge are the camera's."""
    for layout in (F.LAYOUT_GRID, F.LAYOUT_HEX, F.LAYOUT_RING):
        s = _view(30, layout, zoom=0.5, pan=[12.0, -7.0])
        rows = F.field(s, 800, 600)
        gx, gy = F.inst_positions(30, layout)
        cell = F.CELL * 600 * 0.5
        assert np.allclose(rows[:, 0], 400 + 12 + gx * cell, atol=1e-3)
        assert np.allclose(rows[:, 1], 300 - 7 + gy * cell, atol=1e-3)
        assert np.allclose(rows[:, 2], 0.5) and np.allclose(rows[:, 3], 1.0)
    s = _view(1, zoom=2.5, pan=[5.0, 6.0])
    assert np.array_equal(F.field(s, 800, 600), [[405.0, 306.0, 2.5, 1.0]])
    assert F.field(_view(0), 800, 600).shape == (0, 4)
    s = _view(30, inst_spacing=2.0)
    wide = F.field(s, 800, 600)
    assert np.allclose(wide[:, :2] - [400, 300], 2 * (F.field(_view(30), 800, 600)[:, :2]
                                                     - [400, 300]), atol=1e-3)


def test_zooming_a_fitted_grid_snaps_to_whole_cells():
    """Zoom in on a fitted grid: the screen shows whole rows and columns,
    its edges on cell boundaries — every copy wholly in or wholly out —
    and the field fills it edge to edge in even cells."""
    w, h = 1600, 900
    radius = F.SHAPE_EXTENT / 2 * F.CELL * min(w, h)
    for layout in (F.LAYOUT_GRID, F.LAYOUT_HEX):
        for zoom in (1.0, 1.3, 2.0, 3.7, 8.0, 40.0):
            for pan in ([0.0, 0.0], [130.0, -45.0], [-1e5, 1e5]):
                s = _view(240, layout, inst_fit=True, zoom=zoom, pan=pan)
                rows = F.field(s, w, h)
                ins, outs = _inside(rows, w, h, radius), _outside(rows, w, h, radius)
                if layout == F.LAYOUT_GRID:
                    assert (ins | outs).all(), (zoom, pan)
                assert ins.sum() >= 1
    # the grid at zoom 1: columns × rows of even cells, the screen's edges
    # half a cell from the outer copies
    s = _view(12, F.LAYOUT_GRID, inst_fit=True)
    rows = F.field(s, w, h)
    xs, ys = np.unique(np.round(rows[:, 0], 3)), np.unique(np.round(rows[:, 1], 3))
    assert np.allclose(xs, (np.arange(4) + 0.5) * w / 4) and np.allclose(ys, (np.arange(3) + 0.5) * h / 3)
    # zoom 2 on 8 × 8: 4 × 4 whole cells, centred
    s = _view(64, F.LAYOUT_GRID, inst_fit=True, zoom=2.0)
    rows = F.field(s, 1000, 1000)
    shown = rows[_inside(rows, 1000, 1000, radius)]
    assert len(shown) == 16


def test_pan_on_a_fitted_grid_moves_a_whole_cell():
    """Pan less than half a cell and the window stays; a cell's worth and
    it moves one column; it never moves past the field's edge."""
    w = h = 1000

    def xs(pan_x):
        s = _view(100, F.LAYOUT_GRID, inst_fit=True, zoom=2.0, pan=[pan_x, 0.0])
        return F.field(s, w, h)[:, 0]

    cell = w / 5                                    # 10 columns at zoom 2: 5 shown
    assert np.array_equal(xs(0.0), xs(0.4 * cell))
    assert np.allclose(xs(cell), xs(0.0) + cell)
    assert np.array_equal(xs(1e6), xs(3 * cell))    # held at the field's left edge
    # zoom 1 shows it all: the pan does nothing
    s = _view(100, F.LAYOUT_GRID, inst_fit=True, pan=[333.0, 0.0])
    assert np.array_equal(F.field(s, w, h), F.field(_view(100, F.LAYOUT_GRID, inst_fit=True),
                                                    w, h))


@pytest.mark.parametrize("layout", LATTICES, ids=[F.NAMES[k] for k in LATTICES])
def test_a_lattice_is_drawn_far_to_near_through_its_perspective(layout):
    """A lattice: far copies first (the painter's order between copies),
    nearer ones larger and brighter; Field depth 0 is one size for all;
    the camera turns the field."""
    s = _view(200, layout, yaw=0.5, pitch=0.3)
    rows = F.field(s, 1600, 900)
    k, a = rows[:, 2].astype(np.float64), rows[:, 3].astype(np.float64)
    assert len(rows) == 200
    assert (np.diff(k) >= -1e-5).all()              # far (small) to near (large)
    assert (np.diff(a) >= -1e-5).all() and a.max() == pytest.approx(1.0)
    assert a.min() == pytest.approx(0.25, abs=1e-6)
    flat = F.field(_view(200, layout, yaw=0.5, pitch=0.3, inst_persp=0.0), 1600, 900)
    assert np.allclose(flat[:, 2], 1.0)
    turned = F.field(_view(200, layout, yaw=1.2, pitch=0.3), 1600, 900)
    assert not np.allclose(np.sort(turned[:, 0]), np.sort(rows[:, 0]))
    # every motion moves it, and the eye stays put
    for motion in (1, 2, 3):
        m = F.field(_view(200, layout, inst_motion=motion, inst_amp=0.5), 1600, 900, t=1.0)
        assert np.isfinite(m).all() and not np.allclose(np.sort(m[:, 0]), np.sort(
            F.field(_view(200, layout), 1600, 900)[:, 0]))


def test_the_cull_drops_only_copies_wholly_off_screen():
    s = _view(4096, F.LAYOUT_GRID)                  # 64 × 64 cells about a 1.4-cell screen
    w, h = 800, 600
    radius = 0.5 * F.CELL * 600
    every = F.field(s, w, h)
    kept = F.field(s, w, h, radius_px=radius)
    assert len(every) == 4096 and 0 < len(kept) < 40
    assert not _outside(kept, w, h, radius).any()
    dropped = every[~np.isin(every[:, 0] + 1j * every[:, 1], kept[:, 0] + 1j * kept[:, 1])]
    assert _outside(dropped, w, h, radius).all()
    # a field of thousands at zoom 1 costs what it shows
    for layout in range(9):
        rows = F.field(_view(4096, layout), w, h, radius_px=radius)
        assert len(rows) < 400, F.NAMES[layout]


def test_any_count_layout_and_motion_is_finite():
    for layout in (*range(9), -1, 42):
        for fit in (False, True):
            for motion in (0, 1, 2, 3):
                for n in (0, 1, 2, 5, 64, 4096):
                    s = _view(n, layout, inst_fit=fit, inst_motion=motion, inst_amp=1.0,
                              inst_spacing=0.5, inst_persp=1.0, zoom=3.0)
                    rows = F.field(s, 640, 400, t=2.0)
                    assert rows.dtype == np.float32 and rows.shape[1] == 4
                    assert len(rows) == n and np.isfinite(rows).all(), (layout, fit, motion, n)
                    assert (rows[:, 2] > 0).all() and (rows[:, 3] > 0).all()
    assert math.isclose(F.MAX_INSTANCES, 4096)
