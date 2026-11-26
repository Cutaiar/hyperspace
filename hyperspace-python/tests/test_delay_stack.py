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


# ---------------------------------------------------------------- Devin on #519

def test_a_keyed_delay_still_hands_its_stack_to_a_reader(ctx):
    """Black is clear on a delay wraps it in a key node; the stack port still
    reads the delay under it (Devin on #519)."""
    section = {**READ, "keys": ["delay"]}
    r, s = _rig(ctx, section, depth=4, values={"read": {"at": 1.0}})
    got = [_draw(ctx, r, s, h, t=1.0 + i / 60) for i, h in enumerate(HUES)]
    np.testing.assert_allclose(got[-1][0], _hue_rgb(HUES[-3]), atol=2)


def test_a_load_gives_back_a_stacks_room(ctx):
    """A load forgets what a stack holds and the room it took, so an old deep
    stack never counts against the next look's budget (Devin on #519)."""
    r, s = _rig(ctx, READ, depth=16, values={"read": {"at": 0.0}})
    for i, h in enumerate(HUES):
        _draw(ctx, r, s, h, t=1.0 + i / 60)
    st = r.delay_stack("delay")
    assert st.depth == 16
    r.reset_delays()
    s.delay["delay"].depth = 2
    for i, h in enumerate(HUES):
        _draw(ctx, r, s, h, t=2.0 + i / 60)
    assert st.depth == 2


def test_two_decks_on_one_context_share_one_budget(ctx, monkeypatch):
    """Sibling renderers (the two decks) share a GL context, so their stacks
    share one budget (Devin on #519)."""
    from test_graph_faces import _fbo

    from hyperspace import stack
    from hyperspace.outputs import Switches, View

    a, sa = _rig(ctx, READ, depth=4, values={"read": {"at": 0.0}})
    b = a.sibling()
    b.ghost.state.on = False
    b.wiring = a.wiring
    b.fx.state.values["colour"].update({"on": True, "saturation": 1.0, "value": 1.0})
    b.fx.state.values["read"]["on"] = True
    sb = _state()
    sb.delay = {"delay": type(sa.delay["delay"])(depth=4)}
    one = stack.frame_bytes((32, 24)) * 4
    monkeypatch.setattr(stack, "BUDGET", one + one // 2)          # room for one, not two
    for i in range(4):
        for r, s in ((a, sa), (b, sb)):
            v = View(Switches(), (32, 24), target=_fbo(ctx, 32, 24))
            r.draw_outputs(s, 32, 24, 1.0, [v], t_now=1.0 + i / 60)
    held = [r.delay_stack("delay") for r in (a, b)]
    assert sum(st.tex is not None for st in held) == 1
    assert any("past the" in st.error for st in held)


def test_a_stack_inlet_of_a_saved_group_stays_open():
    """A group saved with Read but not its delay keeps the stack inlet, so the
    spawned group's pin and Wire as saved can reconnect it (Devin on #519)."""
    from hyperspace import graphview

    spec = _spec({"frame": "wired", "nodes": [{"kind": "effect", "file": "read"}],
                  "wires": [{"from": "read", "to": "output.1.image"}]})
    entry = {"id": "group.1", "name": "g", "nodes": ["render:read"],
             "ports": [{"id": "in", "type": "stack", "to": "read.stack", "was": "delay"}]}
    assert graphview.open_ports(spec, entry) == [entry["ports"][0]]


def test_a_reader_fits_a_stack_of_another_shape_by_cover(ctx):
    """A square stack read into a wide frame is cropped, as the delay's own
    picture is (`OWN_FIT`), never stretched (Devin on #519): a ramp across
    the frame (a Line field, promoted) through a square resize reads the same
    column for column through Read at 0 as through the delay itself."""
    from test_graph_faces import _fbo, _px

    from hyperspace.outputs import Switches, View
    from hyperspace.view import ResizeState

    section = wired(("line", "resize.image"), ("resize", "delay.image"),
                    ("delay", "read.stack"), ("read", "output.1.image"),
                    ("delay", "output.2.image"), nodes=("colour", "line", "read"))
    section["nodes"].append({"kind": "resize"})
    # (the ramp runs up the frame: cover crops a square's top and bottom in a
    # wide frame, so it is the rows that show a stretch)
    r, s = _rig(ctx, section, depth=2, values={"read": {"at": 0.0}, "line": {"angle": 1.5708}})
    s.resize["resize"] = ResizeState(size=2, aspect=1)            # square
    for i in range(3):
        vs = [View(Switches(), (64, 16), target=_fbo(ctx, 64, 16)) for _ in range(2)]
        r.draw_outputs(s, 64, 16, 1.0, vs, t_now=1.0 + i / 60)
    read, own = (_px(v.target) for v in vs)
    assert own[0, 32, 0] != own[15, 32, 0]                        # a ramp, not flat
    assert np.abs(read[:, 32, :3] - own[:, 32, :3]).max() <= 4


def test_trail_over_takes_a_keyed_scenes_clear_black_as_clear(ctx):
    """Keyed black recorded into a stack stays see-through even in an opaque
    window, so Trail's over does not cover older copies with it (Devin on #519)."""
    section = wired(("colour", "delay.image"), ("delay", "trail.stack"),
                    ("trail", "output.1.image"), nodes=("colour", "trail"))
    section["keys"] = ["colour"]
    r, s = _rig(ctx, section, depth=3, values={"trail": {"level": 1.0, "fade": 10.0, "lay": 0}})
    from hyperspace.view import KeyState

    s.keys["colour"] = KeyState(level=0.5, soft=0.0)
    r.bg_alpha = 1.0
    seq = [0.0, 0.0, 0.0]                         # red, then black (value 0) on top
    for i, hue in enumerate(seq):
        r.fx.state.values["colour"]["value"] = 1.0 if i == 0 else 0.0
        got = _draw(ctx, r, s, hue, t=1.0 + i / 60)
    got = _draw(ctx, r, s, 0.0, t=1.0 + 3 / 60)
    assert got[0][0] > 200, got[0]                # the red copy shows through clear black


def test_a_saved_stack_inlet_has_words_in_the_patch_list():
    """A patch saved with a stack inlet is listed with words for it, never a
    KeyError that closes the browser (Devin on #519)."""
    from hyperspace import graphview

    doc = {"ports": [{"id": "in", "type": "stack", "to": "read.stack", "was": "delay"},
                     {"id": "out", "type": "image", "from": "read"}]}
    words = graphview.patch_words(doc)
    assert "in: stack" in words


def test_the_stack_budget_survives_a_hot_reload_of_its_module(ctx):
    """A reload of `stack` keeps what every live stack holds counted (Devin on #519)."""
    import importlib

    from hyperspace import stack

    st = stack.DelayStack()
    assert st.ensure(ctx, (8, 8), 2)
    importlib.reload(stack)
    assert stack.held(ctx) == st.bytes()
    st.release()
