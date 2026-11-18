"""fractal.py: a self-similar shape's view, re-rooted as the zoom grows."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from hyperspace import fractal, geometry
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.params import build_registry
from hyperspace.view import ViewState

SIERPINSKI = geometry.shape_index("Sierpinski tetrahedron")
W, H = 960, 540


EVERY = pytest.mark.parametrize("name", list(fractal.FRACTALS))


def _view(zoom: float = 1.0, name: str = "Sierpinski tetrahedron") -> ViewState:
    s = ViewState(shape=geometry.shape_index(name), zoom=zoom)
    s.ang = [0.3, 0.7, 1.1, 0.0, 0.0, 0.0]
    s.yaw, s.pitch = 0.4, 0.25
    return s


def _reg(s: ViewState):
    chain = Analyzer(Analyser())
    return build_registry(s, Control(chain), SimpleNamespace(chain=chain))


def _world(s: ViewState) -> np.ndarray:
    """Where the frame's points are in the world, each rounded to a key."""
    _, P, _, _ = fractal.frame(fractal.spec_of(s.shape), s, W, H)
    q = max(s.zoom, 1e-3) * P + np.array([s.pan[0], -s.pan[1], 0.0])
    return np.unique(np.round(q, 6), axis=0)


def test_the_split_of_a_tetrahedron_adds_an_octahedron():
    f = fractal.spec_of(SIERPINSKI)
    assert f.new_V.shape == (6, 4) and len(f.new_E) == 12 and f.new_dot.all()


def test_every_fractal_is_in_the_catalog_under_fractals():
    for name in fractal.FRACTALS:
        shape = geometry.SHAPES[geometry.shape_index(name)]
        assert shape.family == ("Fractals" if shape.dims == 3 else "4D fractals")
    assert {s.name for s in geometry.SHAPES if s.family.endswith("ractals")} == set(fractal.FRACTALS)


def test_a_cube_is_cut_as_its_name_says():
    assert [len(fractal.FRACTALS[n].centres)
            for n in ("Menger sponge", "Cantor dust", "Vicsek cross")] == [20, 8, 7]


@EVERY
def test_a_reroot_moves_nothing_in_the_world(name):
    s = _view(fractal.Z_IN * 1.01, name)
    f = fractal.spec_of(s.shape)
    s.pan = [0.3, -0.2]
    before = _world(s)
    for depth in range(1, 6):
        s.reroot()
        assert len(s.dive.path) == depth and s.zoom < fractal.Z_IN
        after = _world(s)
        # (the top cell's own outline is all a deeper root may add or drop)
        both = {tuple(r) for r in before} & {tuple(r) for r in after}
        assert len(both) >= len(before) - len(f.V) and len(both) >= len(after) - len(f.V)
        s.zoom /= f.ratio
        before = _world(s)


@EVERY
def test_the_zoom_never_runs_out(name):
    s = _view(name=name)
    reg = _reg(s)
    for _ in range(600):
        reg["camera.zoom"].scale(1.05)
        reg.apply()
        s.integrate(1 / 60)
        s.reroot(reg)
        assert s.zoom < fractal.Z_IN
        assert reg["camera.zoom"].base == s.zoom
        assert max(abs(s.pan[0]), abs(s.pan[1])) < 11.0
    assert len(s.dive.path) > 20
    g, _, _, _ = fractal.frame(fractal.spec_of(s.shape), s, W, H)
    assert 100 < g["m"] <= fractal.BUDGET + len(fractal.spec_of(s.shape).E)


@EVERY
def test_all_the_way_out_is_the_whole_shape_centred(name):
    s = _view(name=name)
    for _ in range(300):
        s.zoom *= 1.05
        s.integrate(1 / 60)
        s.reroot()
    assert s.dive.path
    for _ in range(400):
        s.zoom /= 1.05
        s.reroot()
    assert not s.dive.path and s.dive.z == 0.0
    assert s.zoom < 1.0 and np.allclose(s.pan, 0.0, atol=1e-9)


def test_reset_view_comes_back_out():
    s = _view(fractal.Z_IN * 9)
    reg = _reg(s)
    s.reroot(reg)
    assert s.dive.path
    reg["camera.reset"].fire()
    assert not s.dive.path and s.zoom == 1.0


def test_another_shape_is_left_alone():
    s = ViewState(shape=3, zoom=37.0)
    s.pan = [1.5, -2.0]
    s.reroot()
    assert (s.zoom, s.pan, s.dive.path, s.dive.z) == (37.0, [1.5, -2.0], [], 0.0)
    assert fractal.spec_of(3) is None
