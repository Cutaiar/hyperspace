"""Plan 90 H4: Time Displace is not a node — it is Read with a field on At
(§4.8; H1's `stack-slit`). The proof, against PR #488's own shader kept as a
test fixture (`tests/fixtures/time-displace-488/timedisplace488.glsl`: #488's
file with only the past it reads swapped — the delay's stack for the look-back's
atlas).

Both drawn over one delay of a Colour generator whose hue moves each frame:
#488's line field (`x` across the frame, `a = x · Span` seconds back, walked over
the frames' ages and blended between two) against `Line → Read.at` (At =
`(Span / 2 − a₀) / g`, the wire's depth `Span / (g · aspect)`, with `a₀` the
newest frame's age and `g` the spacing — a stack's index is its unit, seconds
`a₀ + k · g`). Equal to rounding wherever `a ≥ a₀`. Where `a < a₀` #488 blended
toward the picture *now*, which no stack holds: Read reads its newest there
(§4.8, "At below 0 reads the newest"), and a slit-scan that must include now
lays the picture over by a composite."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace import fx
from hyperspace import graph as G
from hyperspace.fx import FxState

sys.path.insert(0, str(Path(__file__).parent))

moderngl = pytest.importorskip("moderngl")

FIXTURE = Path(__file__).parent / "fixtures" / "time-displace-488" / "timedisplace488.glsl"
TD = "timedisplace488"
SIZE = (96, 24)
FRAMES = 40
HZ = 60.0
SPAN = 0.4          # seconds back at the right edge: 24 frames, inside a depth of 32


def _fx_dir(tmp_path: Path, monkeypatch) -> Path:
    """The shipped files and the fixture in one folder, read as the shipped
    one (a file's ports are read from there: `fx.ports_of`)."""
    d = tmp_path / "fx"
    shutil.copytree(fx.FX_DIR, d, ignore=shutil.ignore_patterns("retired"))
    shutil.copy(FIXTURE, d / FIXTURE.name)
    monkeypatch.setattr(fx, "FX_DIR", d)
    monkeypatch.delitem(fx._PORTS, TD, raising=False)
    return d


def _section(depth: float):
    return {"frame": "wired",
            "nodes": [{"kind": "effect", "file": f} for f in ("colour", TD, "read", "line")]
            + [{"kind": "delay"}],
            "wires": [{"from": "colour", "to": "delay.image"},
                      {"from": "colour", "to": f"{TD}.image"},
                      {"from": "delay", "to": f"{TD}.stack"},
                      {"from": "delay", "to": "read.stack"},
                      {"from": "line", "to": "read.at", "depth": depth},
                      {"from": TD, "to": "output.1.image"},
                      {"from": "read", "to": "output.2.image"}]}


def _run(ctx, fx_dir: Path, at: float, depth: float):
    """The two outputs after FRAMES frames, and the delay's ages then."""
    from test_graph_faces import _faces, _fbo, _px

    from hyperspace.outputs import Switches, View
    from hyperspace.render import Renderer
    from hyperspace.view import DelayState

    r = Renderer(ctx, fx=FxState(fx_dir))
    r.ghost.state.on = False
    spec = G.read_graph(_section(depth), effects=set(r.fx.state.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    v = r.fx.state.values
    v["colour"].update({"on": True, "saturation": 1.0, "value": 1.0})
    v[TD].update({"on": True, "mix": 1.0, "span": SPAN, "shape": 0, "angle": 0.0,
                  "repeat": 1, "drift": 0.0, "steps": 0, "flip": 0, "between": 0})
    v["read"].update({"on": True, "mix": 1.0, "at": at, "between": 0})
    v["line"].update({"on": True, "angle": 0.0, "scale": 1.0, "out": 0})
    s = _faces()
    s.delay["delay"] = DelayState(depth=32, frames=1)
    for i in range(FRAMES):
        v["colour"]["hue"] = (i * 0.013) % 1.0          # a slow sweep: no hue wraps between frames
        views = [View(Switches(), SIZE, target=_fbo(ctx, *SIZE)) for _ in range(2)]
        r.draw_outputs(s, *SIZE, 1.0, views, t_now=1.0 + i / HZ)
        assert ctx.error == "GL_NO_ERROR"
    got = r.delay_pair("delay").stack.read()
    return [_px(x.target)[SIZE[1] // 2, :, :3] for x in views], got["ages"]


def test_read_with_a_line_on_at_is_488s_time_displace(ctx, tmp_path, monkeypatch):
    d = _fx_dir(tmp_path, monkeypatch)
    _, ages = _run(ctx, d, 0.0, 0.0)                 # (the frames' ages, at this cadence)
    a0, g = ages[0], ages[1] - ages[0]
    assert np.allclose(np.diff(ages), g, atol=1e-4) and g > 0
    aspect = SIZE[0] / SIZE[1]
    at, depth = (SPAN / 2 - a0) / g, SPAN / (g * aspect)
    (td, read), _ = _run(ctx, d, at, depth)
    x = (np.arange(SIZE[0]) + 0.5) / SIZE[0]         # each column's centre, #488's x
    held = x * SPAN >= a0 + 1e-3                     # where #488 reads the stack, not now
    assert held.sum() > SIZE[0] * 0.8
    diff = np.abs(td.astype(int) - read.astype(int)).max(axis=1)
    assert diff[held].max() <= 2, diff[held]         # to rounding (8 bits, two lerps)
    # (and the picture moves across the frame: these are different moments)
    assert np.abs(np.diff(td[held].astype(int), axis=0)).sum() > 0


def test_where_488_blended_toward_now_read_reads_its_newest(ctx, tmp_path, monkeypatch):
    """The one place the two differ (§4.8): an age younger than the newest
    frame. #488 blended toward the picture now; a stack holds no now, so Read
    reads its newest there — a slit-scan wanting now composites the picture."""
    d = _fx_dir(tmp_path, monkeypatch)
    _, ages = _run(ctx, d, 0.0, 0.0)
    a0, g = ages[0], ages[1] - ages[0]
    at, depth = (SPAN / 2 - a0) / g, SPAN / (g * SIZE[0] / SIZE[1])
    (td, read), _ = _run(ctx, d, at, depth)
    first = 0                                        # the left edge: now, in #488
    assert (0.5 / SIZE[0]) * SPAN < a0
    (_, newest), _ = _run(ctx, d, 0.0, 0.0)          # Read at 0 everywhere: the newest frame
    assert np.abs(read[first].astype(int) - newest[first].astype(int)).max() <= 2
    assert np.abs(td[first].astype(int) - read[first].astype(int)).max() > 2
