"""Plan 90 H1: a delay keeps its past frames as a stack (`stack.DelayStack`),
and Read and Trail — effect files that take a stack — read it.

The picture a delay makes stays last frame's (plan 34's z⁻¹, byte for byte);
its Depth says how many of the pictures it takes (at its rate, plan 34 D)
it keeps for a reader. A stack port takes a delay
and nothing else, in words. Drawn through the real renderer: a Colour
generator whose hue moves each frame, into a delay, read back."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

from hyperspace import fx
from hyperspace import graph as G
from hyperspace.fx import FxState

sys.path.insert(0, str(Path(__file__).parent))

moderngl = pytest.importorskip("moderngl")

# a hue a frame, at full saturation and value: red, yellow, green, cyan, blue …
HUES = [0.0, 1 / 6, 2 / 6, 3 / 6, 4 / 6, 5 / 6]


def wired(*pairs, nodes=("colour", "read")):
    return {"frame": "wired",
            "nodes": [{"kind": "effect", "file": n} for n in nodes] + [{"kind": "delay"}],
            "wires": [{"from": a, "to": b} for a, b in pairs]}


READ = wired(("colour", "delay.image"), ("delay", "read.stack"), ("read", "output.1.image"),
             ("delay", "output.2.image"))


def _spec(section):
    return G.read_graph(section, effects=set(FxState().specs))


def _rig(ctx, section, depth=4, frames=1, values=None):
    from hyperspace.render import Renderer
    from hyperspace.view import DelayState

    r = Renderer(ctx)
    r.ghost.state.on = False
    spec = _spec(section)
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    r.fx.state.values["colour"].update({"on": True, "saturation": 1.0, "value": 1.0})
    for name, v in (values or {}).items():
        r.fx.state.values[name].update({"on": True, **v})
    s = _state()
    s.delay["delay"] = DelayState(depth=depth, frames=frames)
    return r, s


def _state():
    from test_graph_faces import _faces

    return _faces()


def _draw(ctx, r, s, hue, t):
    from test_graph_faces import _fbo, _px

    from hyperspace.outputs import Switches, View

    r.fx.state.values["colour"]["hue"] = hue
    vs = [View(Switches(), (32, 24), target=_fbo(ctx, 32, 24)) for _ in range(2)]
    r.draw_outputs(s, 32, 24, 1.0, vs, t_now=t)
    assert ctx.error == "GL_NO_ERROR"
    return [_px(v.target)[12, 16, :3] for v in vs]


def _hue_rgb(h):
    import colorsys

    return np.array([round(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)])


# ---------------------------------------------------------------- types and words

def test_read_and_trail_take_a_stack_and_no_picture():
    for f in ("read", "trail"):
        makes, takes = fx.ports_of(f)
        assert makes == fx.PICTURE
        assert takes.get("stack") == fx.STACK and "image" not in takes


def test_the_stack_type_is_one_word_in_both_modules():
    assert G.STACK == fx.STACK and G.STACK_PORT == fx.STACK_PORT


def test_a_stack_port_takes_a_delay_and_nothing_else_in_words():
    bad = _spec(wired(("colour", "read.stack"), ("read", "output.1.image")))
    said = " ".join(bad.notes)
    assert "takes a stack of past frames" in said and "wire a delay into it" in said
    assert not _spec(READ).notes


def test_a_file_that_reads_a_stack_has_no_hook():
    src = ("// @takes stack stack\n// @hook mandel\n"
           "vec4 effect(vec2 uv) { return vec4(0.0); }\n")
    with pytest.raises(fx.SpecError, match="has no @hook"):
        fx.parse("x", src)


def test_the_stack_port_takes_only_a_stack():
    with pytest.raises(fx.SpecError):
        fx.parse("x", "// @takes stack image\nvec4 effect(vec2 uv) { return vec4(0.0); }\n")
    with pytest.raises(fx.SpecError):
        fx.parse("x", "// @takes image stack\nvec4 effect(vec2 uv) { return vec4(0.0); }\n")


def test_only_a_stack_reader_declares_the_stack():
    """Every other file's source is as it was (no `u_stack` in it)."""
    st = FxState()
    for name, spec in st.specs.items():
        src = fx.fragment_source(st.lib, spec.source, st.common, spec.clocks, spec.makes,
                                 stack=spec.takes.get("stack") == fx.STACK)
        assert ("u_stack" in src) == (name in ("read", "trail")), name


# ---------------------------------------------------------------- through the renderer

def test_read_shows_the_frame_at_frames_back(ctx):
    for at in (0, 1, 2):
        r, s = _rig(ctx, READ, depth=4, values={"read": {"at": float(at), "mix": 1.0}})
        got = [_draw(ctx, r, s, h, t=1.0 + i / 60) for i, h in enumerate(HUES)]
        # frame k shows the frame drawn `at + 1` frames before it
        k = len(HUES) - 1
        np.testing.assert_allclose(got[k][0], _hue_rgb(HUES[k - 1 - at]), atol=2)


def test_the_delays_own_picture_is_still_last_frames(ctx):
    r, s = _rig(ctx, READ, depth=4, values={"read": {"at": 2.0}})
    got = [_draw(ctx, r, s, h, t=1.0 + i / 60) for i, h in enumerate(HUES)]
    np.testing.assert_allclose(got[-1][1], _hue_rgb(HUES[-2]), atol=2)


def test_read_past_what_it_keeps_is_its_oldest(ctx):
    r, s = _rig(ctx, READ, depth=2, values={"read": {"at": 9.0}})
    got = [_draw(ctx, r, s, h, t=1.0 + i / 60) for i, h in enumerate(HUES)]
    np.testing.assert_allclose(got[-1][0], _hue_rgb(HUES[-3]), atol=2)


def test_a_fraction_blends_the_two_frames_either_side_unless_nearest(ctx):
    for between, want in ((0, (_hue_rgb(HUES[-2]) + _hue_rgb(HUES[-3])) / 2),
                          (1, _hue_rgb(HUES[-3]))):
        r, s = _rig(ctx, READ, depth=4, values={"read": {"at": 0.5 + between * 0.25,
                                                         "between": between}})
        got = [_draw(ctx, r, s, h, t=1.0 + i / 60) for i, h in enumerate(HUES)]
        np.testing.assert_allclose(got[-1][0], want, atol=3)


def test_the_stack_keeps_the_pictures_the_delay_takes_at_its_rate(ctx):
    # the delay's own rate (plan 34 D): every second frame — the stack keeps
    # those, so one step back is two frames back
    r, s = _rig(ctx, READ, depth=4, frames=2, values={"read": {"at": 1.0}})
    got = [_draw(ctx, r, s, h, t=1.0 + i / 60) for i, h in enumerate(HUES)]
    kept = [HUES[i] for i in range(0, len(HUES) - 1, 2)]       # 0, 2, 4 of 0 … 4
    np.testing.assert_allclose(got[-1][0], _hue_rgb(kept[-2]), atol=2)


def test_trail_lays_the_kept_frames_by_age(ctx):
    section = wired(("colour", "delay.image"), ("delay", "trail.stack"),
                    ("trail", "output.1.image"), nodes=("colour", "trail"))
    r, s = _rig(ctx, section, depth=3, values={"trail": {"level": 1.0, "fade": 10.0, "lay": 1}})
    for i in range(5):            # one colour throughout: three frames of it, summed
        got = _draw(ctx, r, s, 0.0, t=1.0 + i / 60)
    # red three times at nearly full strength, added: clamped red
    assert got[0][0] == 255 and got[0][1] < 3 and got[0][2] < 3


def test_trail_over_is_the_newest_where_it_covers(ctx):
    section = wired(("colour", "delay.image"), ("delay", "trail.stack"),
                    ("trail", "output.1.image"), nodes=("colour", "trail"))
    r, s = _rig(ctx, section, depth=3, values={"trail": {"level": 1.0, "fade": 10.0, "lay": 0}})
    got = [_draw(ctx, r, s, h, t=1.0 + i / 60) for i, h in enumerate(HUES)]
    # every frame opaque: over, the newest (last frame's) covers the rest
    np.testing.assert_allclose(got[-1][0], _hue_rgb(HUES[-2]), atol=3)


def test_a_reader_with_no_delay_wired_shows_nothing(ctx):
    section = {"frame": "wired", "nodes": [{"kind": "effect", "file": "read"}],
               "wires": [{"from": "read", "to": "output.1.image"}]}
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    spec = _spec(section)
    r.wiring = spec.wiring()
    r.fx.state.values["read"]["on"] = True
    from test_graph_faces import _fbo, _px

    from hyperspace.outputs import Switches, View
    v = View(Switches(), (32, 24), target=_fbo(ctx, 32, 24))
    r.draw_outputs(_state(), 32, 24, 1.0, [v], t_now=1.0)
    assert ctx.error == "GL_NO_ERROR"
    assert _px(v.target)[12, 16, :3].max() == 0


def test_a_depth_driven_down_keeps_what_the_stack_holds(ctx):
    """Depth is modulatable: lowered, the stack is kept and a reader reads the
    newest Depth of it; raised past its room, it is made again, clean."""
    r, s = _rig(ctx, READ, depth=4, values={"read": {"at": 3.0}})
    for i, h in enumerate(HUES[:5]):
        _draw(ctx, r, s, h, t=1.0 + i / 60)
    st = r.delay_stack("delay")
    tex = st.tex
    s.delay["delay"].depth = 2
    got = _draw(ctx, r, s, HUES[5], t=1.0 + 5 / 60)
    assert st.tex is tex and len(st.entries) == 4
    np.testing.assert_allclose(got[0], _hue_rgb(HUES[3]), atol=2)     # at 3 → its 2nd newest
    s.delay["delay"].depth = 8
    _draw(ctx, r, s, HUES[0], t=1.0 + 6 / 60)
    assert st.tex is not tex and len(st.entries) == 1


def test_the_slit_scan_example_shows_two_moments_across_the_frame(ctx):
    """A Line field on Read's At (plan 90: a time displace, no node of its own):
    the left and the right of the frame show different frames."""
    section = wired(("colour", "delay.image"), ("delay", "read.stack"),
                    ("read", "output.1.image"), nodes=("colour", "read", "line"))
    section["wires"].append({"from": "line", "to": "read.at", "depth": 3.0})
    r, s = _rig(ctx, section, depth=8, values={"read": {"at": 2.0}, "line": {}})
    from test_graph_faces import _fbo, _px

    from hyperspace.outputs import Switches, View
    for i, h in enumerate(HUES):
        r.fx.state.values["colour"]["hue"] = h
        v = View(Switches(), (64, 24), target=_fbo(ctx, 64, 24))
        r.draw_outputs(s, 64, 24, 1.0, [v], t_now=1.0 + i / 60)
    px = _px(v.target)
    left, right = px[12, 2, :3], px[12, 61, :3]
    assert np.abs(left - right).max() > 60, (left, right)
