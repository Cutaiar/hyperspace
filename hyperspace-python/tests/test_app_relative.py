"""Plan 09 WP2 — audit simulation 1 against the app's relative writers.

The mouse, the sticks and ↑/↓ live outside the binding table: they move a
param by a delta each frame. The audit found them reading the *effective*
value and writing the base, so a performer's offset folded into the base
on every drag frame (+0.01 rad asked, +0.32 got). They now move the base
through Param.nudge / Param.scale (tested on their own in test_params);
here the app's two moves with geometry of their own — `_ride_depth` and
`_zoom_about` — and the plain nudge/scale the drags and sticks make run
under a constant offset with the registry's real apply(), in the order
the frame loop runs them, at the app's own per-frame rates. No window:
the params sit on a plain object, and nothing here touches glfw.
"""

import math
from types import SimpleNamespace

import pytest

from hyperspace import tapers
from hyperspace.app import D4_RATE0, _ride_depth, _zoom_about
from hyperspace.params import Registry

OCT = tapers.OCT                                   # T_DEPTH: detents per octave of (depth − 1)


def _view():
    """A yaw (wrapping), a zoom (log), a pan and the real 4D depth taper on one object."""
    obj = SimpleNamespace(yaw=0.0, zoom=1.0, pan=[0.0, 0.0], depth4=tapers.T_DEPTH.map(80))
    reg = Registry()
    reg.continuous("camera.yaw", "Yaw", lambda: obj.yaw, lambda v: setattr(obj, "yaw", v),
                   lo=-math.pi, hi=math.pi, wrap=True)
    reg.continuous("camera.zoom", "Zoom", lambda: obj.zoom, lambda v: setattr(obj, "zoom", v),
                   lo=0.05, hi=40.0, log=True)
    for i, axis in enumerate("xy"):
        reg.continuous(f"camera.pan.{axis}", f"Pan {axis}", lambda i=i: obj.pan[i],
                       lambda v, i=i: obj.pan.__setitem__(i, v), lo=-4000.0, hi=4000.0)
    reg.continuous("view.depth4", "4D depth", lambda: obj.depth4,
                   lambda v: setattr(obj, "depth4", v), taper=tapers.T_DEPTH)
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
    _frames(reg, yaw, off, n, lambda: yaw.nudge(d))
    assert yaw.modulated
    assert yaw.base == pytest.approx(n * d, abs=1e-12)
    assert obj.yaw == pytest.approx(n * d + off * 2 * math.pi, abs=1e-9)
    reg.apply()                                    # the performer lets go
    assert not yaw.modulated and obj.yaw == pytest.approx(n * d, abs=1e-12)


def test_zoom_under_a_performer_scales_the_base_by_its_factor():
    """The multiplicative twin: N stick frames of ×f leave the base at f^N,
    and the effective zoom at that times the offset's octaves (a log
    range's offset is a ratio, so the picture zooms with the stick and
    the hand's pinch stays the same *fraction* on top)."""
    obj, reg = _view()
    zoom = reg["camera.zoom"]
    f, n, off = 1.01, 20, 0.1
    ratios = []
    _frames(reg, zoom, off, n, lambda: ratios.append(zoom.scale(f)))
    assert zoom.base == pytest.approx(f ** n, rel=1e-9)
    assert obj.zoom == pytest.approx(f ** n * 2.0 ** (off * math.log2(40.0 / 0.05)), rel=1e-9)
    assert ratios == pytest.approx([f] * n)         # nothing at a stop: each tick lands whole
    reg.apply()
    assert obj.zoom == pytest.approx(f ** n, rel=1e-9)


def test_ride_depth_under_a_performer_moves_the_base_in_octaves():
    """↑ at the instant of the press: D4_RATE0 octaves/s is 0.0075 per
    frame at 60 Hz, well under T_DEPTH's 0.05-octave detent. The base
    must move on the very first frame and add up exactly — set_value's
    detent snap would have parked it for a second of hold — and only the
    base moves; the performer's share of depth is untouched."""
    obj, reg = _view()
    depth = reg["view.depth4"]
    o, n, off = D4_RATE0 / 60, 40, 0.1
    assert o == pytest.approx(0.0075) and o * OCT < 0.5   # sub-detent, the case that stuck
    start = depth.base
    _frames(reg, depth, off, 1, lambda: _ride_depth(depth, o))
    assert depth.base > start                                 # it moved, this frame
    _frames(reg, depth, off, n - 1, lambda: _ride_depth(depth, o))
    want = tapers.T_DEPTH.map(80 + n * o * OCT)               # 80 detents + 0.3 octave
    assert depth.base == pytest.approx(want, rel=1e-9)
    assert obj.depth4 == pytest.approx(tapers.T_DEPTH.map(80 + n * o * OCT + off * 160), rel=1e-9)
    reg.apply()
    assert obj.depth4 == pytest.approx(want, rel=1e-9)


def test_ride_depth_without_a_performer_accumulates_sub_detent_moves():
    """The same press with nothing riding depth: the object takes the raw
    value each frame, so 40 frames land 0.3 octave up, not on the detent
    the press started from. A gamepad trigger at 60 % (0.0024 oct/frame)
    moves it too."""
    obj, reg = _view()
    depth = reg["view.depth4"]
    for _ in range(40):
        _ride_depth(depth, D4_RATE0 / 60)
    assert obj.depth4 == pytest.approx(tapers.T_DEPTH.map(86), rel=1e-9)
    before = obj.depth4
    _ride_depth(depth, 0.6 * 2.4 / 60)
    assert obj.depth4 > before


# ---------------------------------------------------------------- zoom about the cursor

def test_wheel_zoom_keeps_the_point_under_the_cursor():
    """No performer: the picture zooms by the wheel's factor about the
    projection centre, and the pan moves so the cursor's point stays put."""
    obj, reg = _view()
    zoom, px, py = reg["camera.zoom"], reg["camera.pan.x"], reg["camera.pan.y"]
    _zoom_about(zoom, px, py, obj, 1.0, 100.0, 500.0, 800.0, 600.0)
    f = 2.0 ** 0.15
    assert obj.zoom == pytest.approx(f)
    assert obj.pan[0] == pytest.approx((400 - 100) * (f - 1))
    assert obj.pan[1] == pytest.approx((300 - 500) * (f - 1))


def test_wheel_zoom_pinned_at_a_stop_by_a_performer_moves_only_the_return_value():
    """Base 30×, a performer pushing the effective past 40× — the picture
    is pinned at the stop. Wheeling in moves the base (what shows when the
    performer leaves) and nothing on screen, so the pan must not move."""
    obj, reg = _view()
    zoom, px, py = reg["camera.zoom"], reg["camera.pan.x"], reg["camera.pan.y"]
    obj.zoom = 30.0
    zoom.modulate(0.5)
    reg.apply()
    assert obj.zoom == pytest.approx(40.0) and zoom.base == pytest.approx(30.0)
    _zoom_about(zoom, px, py, obj, 1.0, 100.0, 500.0, 800.0, 600.0)
    assert zoom.base == pytest.approx(30.0 * 2.0 ** 0.15)
    assert obj.pan == pytest.approx([0.0, 0.0], abs=1e-9)
    assert (px.base, py.base) == pytest.approx((0.0, 0.0), abs=1e-9)
    # off the stop, the pan follows the ratio the picture actually moves by:
    # a base ×f under a performer's ratio K lands at min(30·K·f, 40)
    reg.apply()                                    # the performer lets go
    obj.zoom = 30.0
    zoom.modulate(0.03)                            # 36.7×: the wheel's ×1.11 hits the stop
    reg.apply()
    eff = obj.zoom
    assert 36.0 < eff < 40.0 and eff * 2.0 ** 0.15 > 40.0
    _zoom_about(zoom, px, py, obj, 1.0, 100.0, 500.0, 800.0, 600.0)
    factor = min(eff * 2.0 ** 0.15, 40.0) / eff
    assert 1.0 < factor < 2.0 ** 0.15
    assert obj.pan[0] == pytest.approx((400 - 100) * (factor - 1))
