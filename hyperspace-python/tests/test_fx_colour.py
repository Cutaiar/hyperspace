"""Colour (`shaders/fx/colour.glsl`): a generator of one flat colour, a place
on the HSV cylinder — Hue the way round (it wraps), Saturation out from the
grey middle, Value up from black — and Spin, a clock that turns the hue.

Held here: it takes no input, so `graph.runs_unfed` says it runs fed by
nothing and the wired frame builds and draws it straight into an output; its
pixels are `hsv(h, s, v)` whatever comes in, opaque; Hue wraps; Spin moves the
hue by its clock, so a Spin step never jumps where the hue is.
"""

import colorsys

import numpy as np
import pytest

from hyperspace import graph as G
from hyperspace.fx import FX_DIR, FxChain, FxState, parse

W, H = 32, 16

moderngl = pytest.importorskip("moderngl")


def spec():
    return parse("colour", (FX_DIR / "colour.glsl").read_text())


def test_it_is_a_generator_of_three_knobs_and_a_spin():
    s = spec()
    assert s.label == "Colour" and s.family == "generators"
    assert [p.key for p in s.params] == ["hue", "saturation", "value", "spin"]
    hue = s.params[0]
    assert hue.wrap and (hue.lo, hue.hi, hue.default) == (0.0, 1.0, 0.0)
    assert [(c.uniform, c.rate, c.period) for c in s.clocks] == [("u_spin_t", "spin", 1.0)]
    assert [(p.keys, p.label) for p in s.pads] == [(("hue", "saturation", "value"), "HSV")]
    # no input port: the one rule runs it fed by nothing
    assert "image" not in G.effect_ports("colour")[1]
    assert G.runs_unfed("colour") and G.runs_unfed("colour.2")
    assert "colour" in G.generators_of(FxState()) and FxState().errors == {}


def run(ctx, picture=None, t=0.0, **values) -> np.ndarray:
    st = FxState()
    st.values["colour"].update(on=True, **values)
    chain = FxChain(ctx, st)
    pic = picture if picture is not None else np.zeros((H, W, 4), np.uint8)
    src = ctx.texture((W, H), 4, np.ascontiguousarray(pic).tobytes())
    out = ctx.framebuffer(color_attachments=[ctx.texture((W, H), 4)])
    chain.run_one("colour", src, out, t, opaque=0)
    assert ctx.error == "GL_NO_ERROR" and st.errors == {}
    px = np.frombuffer(out.read(components=4), dtype=np.uint8).reshape(H, W, 4).copy()
    for o in (src, out):
        o.release()
    return px


def want(h, s, v):
    return np.array([round(255 * c) for c in colorsys.hsv_to_rgb(h % 1.0, s, v)])


@pytest.mark.parametrize("h, s, v", [(0.0, 1.0, 1.0), (1 / 3, 1.0, 1.0), (2 / 3, 1.0, 1.0),
                                     (0.1, 0.5, 0.8), (0.75, 0.0, 0.6), (0.5, 1.0, 0.0)])
def test_every_pixel_is_its_place_on_the_cylinder(ctx, h, s, v):
    px = run(ctx, hue=h, saturation=s, value=v)
    assert (px[..., 3] == 255).all()
    flat = px[..., :3].reshape(-1, 3).astype(int)
    assert (flat == flat[0]).all(), "not one flat colour"
    assert np.abs(flat[0] - want(h, s, v)).max() <= 2, (flat[0], want(h, s, v))


def test_it_is_the_same_whatever_comes_in(ctx):
    noise = np.random.default_rng(3).integers(0, 256, (H, W, 4), dtype=np.uint8)
    assert np.array_equal(run(ctx, noise, hue=0.4), run(ctx, None, hue=0.4))


def test_hue_wraps_round_the_cylinder(ctx):
    assert np.abs(run(ctx, hue=0.0).astype(int) - run(ctx, hue=1.0).astype(int)).max() <= 1


def test_spin_turns_the_hue_by_its_clock_without_a_jump():
    """`u_spin_t` += speed × spin × dt, kept in [0, 1): a second at Spin 0.25
    is a quarter turn; a Spin step after it changes the rate, not the phase."""
    st = FxState()
    st.values["colour"].update(on=True, spin=0.25)
    for _ in range(4):
        st.advance(0.25)
    t = st.clocks["colour"]["u_spin_t"]
    assert t == pytest.approx(0.25, abs=1e-6)
    st.values["colour"]["spin"] = -2.0
    st.advance(0.0)
    assert st.clocks["colour"]["u_spin_t"] == pytest.approx(t)


def test_wired_straight_into_an_output_it_draws(ctx):
    """With nothing wired in, the wired frame builds it (the one rule) and
    the output is its colour; GRAPH and the FX pane do not call it fed by
    nothing."""
    from test_mandel import _drawn, _wired

    from hyperspace import graphview, ui_fx

    r, s, vs = _wired(ctx, [("colour", "output.1.image")],
                      {"colour": {"on": True, "hue": 2 / 3, "saturation": 1.0, "value": 1.0}})
    px = _drawn(ctx, r, s, vs)
    g = r._graph
    assert "colour" in g.nodes and "colour" not in g.dormant
    assert np.abs(px.reshape(-1, 3) - want(2 / 3, 1.0, 1.0)).max() <= 2
    spec_ = G.read_graph({"frame": "wired", "nodes": [{"kind": "effect", "file": "colour"}],
                          "wires": [{"from": "colour", "to": "output.1.image"}]},
                         effects=set(FxState().specs))
    assert "colour" not in G.unfed(spec_) and "colour" not in graphview.unreached(spec_)
    assert dict(ui_fx.groups(spec_)) == {"→ output 1": ["colour"]}
