"""Plan 09 WP2 — audit simulation 1 against the app's relative writers.

The mouse, the sticks and ↑/↓ live outside the binding table: they move a
param by a delta each frame. The audit found them reading the *effective*
value and writing the base, so a performer's offset folded into the base
on every drag frame (+0.01 rad asked, +0.32 got). app.py now moves the
base through three pure helpers — `_nudge`, `_scale`, `_ride_depth` —
and here each runs under a constant offset with the registry's real
apply(), in the order the frame loop runs them. No window: the params
sit on a plain object, and nothing here touches glfw.
"""

import math
from types import SimpleNamespace

import pytest

from hyperspace.app import _nudge, _ride_depth, _scale
from hyperspace.params import Registry


def _view():
    """A yaw (wrapping), a zoom (log) and a 4D depth (raw range) on one object."""
    obj = SimpleNamespace(yaw=0.0, zoom=1.0, depth4=1.8)
    reg = Registry()
    reg.continuous("camera.yaw", "Yaw", lambda: obj.yaw, lambda v: setattr(obj, "yaw", v),
                   lo=-math.pi, hi=math.pi, wrap=True)
    reg.continuous("camera.zoom", "Zoom", lambda: obj.zoom, lambda v: setattr(obj, "zoom", v),
                   lo=0.05, hi=40.0, log=True)
    reg.continuous("view.depth4", "4D depth", lambda: obj.depth4,
                   lambda v: setattr(obj, "depth4", v), lo=1.0 + 0.05 * 2.0 ** -4,
                   hi=1.0 + 0.05 * 2.0 ** 8)
    return obj, reg


def _frames(reg, p, offset: float, n: int, move) -> None:
    """n frames: the writer moves, the performer holds `offset`, apply() lands both."""
    for _ in range(n):
        move()
        p.modulate(offset)
        reg.apply()


# ---------------------------------------------------------------- simulation 1

def test_orbit_under_a_performer_moves_the_base_by_its_delta():
    """A +d drag for N frames moves the base by exactly N·d; the effective
    yaw is that plus the performer's offset, every frame. Reading the
    effective value instead compounds the offset N times."""
    obj, reg = _view()
    yaw = reg["camera.yaw"]
    d, n, off = 0.01, 32, 0.05                     # rad/frame, frames, norm offset
    _frames(reg, yaw, off, n, lambda: _nudge(yaw, d))
    assert yaw.modulated
    assert yaw.base == pytest.approx(n * d, abs=1e-12)
    assert obj.yaw == pytest.approx(n * d + off * 2 * math.pi, abs=1e-9)
    reg.apply()                                    # the performer lets go
    assert not yaw.modulated and obj.yaw == pytest.approx(n * d, abs=1e-12)


def test_zoom_under_a_performer_scales_the_base_by_its_factor():
    """The multiplicative twin: N wheel ticks of ×f leave the base at f^N,
    and the effective zoom at that times the offset's octaves (a log
    range's offset is a ratio, so the picture zooms with the wheel and
    the hand's pinch stays the same *fraction* on top)."""
    obj, reg = _view()
    zoom = reg["camera.zoom"]
    f, n, off = 1.01, 20, 0.1
    ratios = []
    _frames(reg, zoom, off, n, lambda: ratios.append(_scale(zoom, f)))
    assert zoom.base == pytest.approx(f ** n, rel=1e-9)
    assert obj.zoom == pytest.approx(f ** n * 2.0 ** (off * math.log2(40.0 / 0.05)), rel=1e-9)
    assert ratios == pytest.approx([f] * n)         # nothing at a stop: each tick lands whole
    reg.apply()
    assert obj.zoom == pytest.approx(f ** n, rel=1e-9)


def test_ride_depth_under_a_performer_moves_the_base_in_octaves():
    """↑ held: each frame adds `o` octaves of (depth − 1) to the base, and
    only the base — the performer's share of depth is untouched."""
    obj, reg = _view()
    depth = reg["view.depth4"]
    o, n, off = 0.05, 40, 0.1
    u0 = math.log2((depth.base - 1.0) / 0.05)
    _frames(reg, depth, off, n, lambda: _ride_depth(depth, o))
    want = 1.0 + 0.05 * 2.0 ** (u0 + n * o)
    assert depth.base == pytest.approx(want, rel=1e-9)
    assert depth.eff_norm == pytest.approx(depth.norm + off, abs=1e-9)
    reg.apply()
    assert obj.depth4 == pytest.approx(want, rel=1e-9)


# ---------------------------------------------------------------- unmodulated

def test_unmodulated_writers_are_plain_arithmetic_on_the_object():
    """With no performer the helpers are what they replaced: value + delta,
    value × factor, wrapped or clamped by the range."""
    obj, reg = _view()
    yaw, zoom, depth = reg["camera.yaw"], reg["camera.zoom"], reg["view.depth4"]
    _nudge(yaw, 0.25)
    assert obj.yaw == pytest.approx(0.25) and not yaw.modulated
    obj.yaw = math.pi - 0.005
    _nudge(yaw, 0.01)                              # yaw wraps
    assert obj.yaw == pytest.approx(-math.pi + 0.005)
    assert _scale(zoom, 2.0) == pytest.approx(2.0) and obj.zoom == pytest.approx(2.0)
    obj.zoom = 39.0
    assert _scale(zoom, 2.0) == pytest.approx(40.0 / 39.0)   # the stop: less than asked
    assert obj.zoom == pytest.approx(40.0)
    _ride_depth(depth, 1.0)                        # one octave of (depth − 1)
    assert obj.depth4 == pytest.approx(1.0 + 0.8 * 2.0)
