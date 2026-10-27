# ruff: noqa: F811 — `ctx` is test_graph_faces' fixture, taken as each GL test's argument
"""Plan 34 T4 — the resize (Z, row 368): a picture cropped and made at a size
of its own, so a delay or an effect after it runs small — the owner's "no
1080p buffer into the faces for no reason".

`ResizeNode` is built where the wires reach it (plan 35 B: `_Build._make`),
its values (`resize[.n].*`, `params.declare_resizes`) live while its entry
does, reached or not (Review Focus 6). What it must keep honest: its own
size is `resize_size`'s; a delay through it holds that size and an effect
after it runs in that size's pool (Review Focus 5); a loop through it and a
delay never reads what it writes (Review Focus 1); the crop is a value,
never a rebuild; a size step remakes its target once each way (Review
Focus 4).

The sections are wired frames (`test_graph_wired.wired`) over the factory
frame's six wires (`FACTORY_FRAME`); every test that wires `output.2` draws
two views (plan 35 R12). The GL tests use test_graph_faces' harness and
skip without a standalone context."""

from __future__ import annotations

import numpy as np
import pytest
from test_graph_faces import (
    Still,
    _faces,
    _fbo,
    _media,
    _px,
    _rgba,
    ctx,  # noqa: F401 — the GL context fixture, taken as each GL test's argument
)
from test_graph_wired import wired

from hyperspace import graph as G
from hyperspace import media_tex, params, view
from hyperspace.outputs import Switches, View
from hyperspace.view import ResizeState

RED, GREEN, BLUE, WHITE = (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)
RESIZE = {"kind": "resize"}
DELAY = {"kind": "delay"}
ACID2 = {"kind": "effect", "file": "acid", "instance": 2}
# the factory frame (`wired_wiring(G.Wiring())`'s wires, in its order; plan
# 36 T4: the look-back off in the old words, so none is drawn)
FACTORY_FRAME = (("shape", "scene.geometry"), ("scene", "output.all.image"),
                 ("hands.layer", "output.all.hands"), ("hands.layer", "output.all.guide"))


# plan 36 T2: and the hidden edges' wires the factory frame ends with
FACTORY_EDGES = (("pattern", "shape.faces"), ("hands", "hands.layer.hands"))


def test_the_factory_frame_is_the_wired_default():
    from hyperspace.graphmigrate import wired_wiring

    assert tuple((w.src, w.dst) for w in wired_wiring(G.Wiring()).wires) == (
        *FACTORY_FRAME, *FACTORY_EDGES)


def _spec(*pairs, nodes=(), effects=None):
    spec = G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=nodes),
                        **({"effects": effects} if effects is not None else {}))
    assert not spec.notes, spec.notes
    return spec


# ---------------------------------------------------------------- the model

def test_resize_size_model():
    assert G.resize_size(256, "input", (1920, 1080)) == (256, 144)
    assert G.resize_size(256, "input", (1080, 1920)) == (144, 256)
    assert G.resize_size(16, "input", (1920, 1080)) == (16, 9)
    assert G.resize_size(64, "square", (1920, 1080)) == (64, 64)
    assert G.resize_size(256, "input", (1024, 1024)) == (256, 256)


def test_the_fits_are_the_media_fits():
    assert view.RESIZE_FITS == media_tex.FITS
    assert view.RESIZE_SIDES == (16, 32, 64, 128, 256, 512, 1024, 2048)
    assert view.RESIZE_ASPECTS == ("input", "square")
    assert view.RESIZE_FILTERS == ("linear", "nearest")
    st = ResizeState()
    assert view.RESIZE_SIDES[st.size] == 256
    assert (st.aspect, st.fit, st.filter) == (0, 0, 0)
    assert (st.crop_x, st.crop_y, st.crop_w, st.crop_h) == (0.5, 0.5, 1.0, 1.0)
    assert view.ViewState().resize == {}


def test_the_resize_node_says_what_it_is():
    assert G.ResizeNode.KIND == "resize" and G.ResizeNode.INPUTS == {"image": G.IMAGE}
    assert G.ResizeNode.OUTPUT == G.IMAGE and G.ResizeNode.TIMED


def test_declare_resizes_comes_and_goes():
    reg = params.Registry()
    got = params.declare_resizes(reg, ["resize", "resize.2"])
    ids = params.resize_ids("resize") + params.resize_ids("resize.2")
    assert sorted(got) == sorted(ids) and len(ids) == 16
    for pid in ids:
        assert reg[pid].group == params.RESIZE_GROUP == "resize", pid
        assert reg[pid].modulatable, pid
        assert params.is_resize_id(pid), pid
    assert reg["resize.2.size"].choices == [str(s) for s in view.RESIZE_SIDES]
    assert reg["resize.2.size"].value == 4
    assert reg["resize.crop_w"].value == 1.0
    assert reg["resize.2.crop_h"].lo == 0.01 and reg["resize.crop_x"].lo == 0.0
    assert reg["resize.size"].label == "resize size" and reg["resize.crop_h"].label == (
        "resize crop h")
    gone = params.declare_resizes(reg, ["resize"])
    assert sorted(gone) == sorted(params.resize_ids("resize.2"))
    assert not [p for p in reg if p.id.startswith("resize.2.")]
    assert "resize.2" not in reg.resize_state
    reg["resize.crop_x"].set(0.25)
    assert reg.resize_state["resize"].crop_x == 0.25
    kept = reg.resize_state["resize"]
    assert params.declare_resizes(reg, ["resize"]) == []
    assert reg.resize_state["resize"] is kept
    assert not params.is_resize_id("resize.1.size") and not params.is_resize_id("resize.crop")
    assert params.is_resize_id("resize.12.filter")
    assert params.RESIZE_GROUP in params.PERFORMANCE_GROUPS
    groups = params.PERFORMANCE_GROUPS
    assert groups.index("resize") == groups.index("switch") + 1


def test_the_registry_writes_the_view_states_resizes():
    from types import SimpleNamespace

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control

    v = view.ViewState()
    chain = Analyzer(Analyser())
    reg = params.build_registry(v, Control(chain), SimpleNamespace(chain=chain))
    assert reg.resize_state is v.resize
    params.declare_resizes(reg, ["resize"])
    reg["resize.size"].set(2)
    assert v.resize["resize"].size == 2


def test_a_resize_is_built_only_when_reached():
    """Review Focus 6: a resize that reaches no sink is never built; one
    wired into an output is; one into an output with nothing in is
    dormant, in words."""
    vs = [View(Switches(), (64, 48)) for _ in range(2)]
    spec = _spec(("channel.a", "resize.image"), nodes=[RESIZE])
    assert "resize" not in G.reaches(spec)
    g = G.build_graph(vs, spec.wiring())
    assert not [n for n in g.nodes.values() if isinstance(n, G.ResizeNode)]
    spec = _spec(("channel.a", "resize.image"), ("resize", "output.2.image"), nodes=[RESIZE])
    g = G.build_graph(vs, spec.wiring())
    assert isinstance(g.nodes["resize"], G.ResizeNode)
    assert g.nodes["resize"].inputs["image"] is g.nodes["channel.a"]
    spec = _spec(("resize", "output.2.image"), nodes=[RESIZE])
    g = G.build_graph(vs, spec.wiring())
    assert not [n for n in g.nodes.values() if isinstance(n, G.ResizeNode)]
    assert g.dormant["resize"] == "resize is fed by nothing here: wire its input"


# ---------------------------------------------------------------- GL
moderngl = pytest.importorskip("moderngl")


def _wired_renderer(ctx, media=None, pairs=(), nodes=(), instances=None, values=None):
    """`test_graph_faces._renderer`'s shape over a wired frame: `pairs`, then
    the factory frame's six wires."""
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    r.ghost.state.on = False
    r.media = media
    st = r.fx.state
    if instances:
        st.set_instances(instances)
    for name, v in (values or {}).items():
        st.values[name].update(v)
    spec = G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=nodes), effects=set(st.specs))
    assert not spec.notes, spec.notes
    r.wiring = spec.wiring()
    return r


def _views(ctx, size, n=2):
    return [View(Switches(), size, target=_fbo(ctx, *size)) for _ in range(n)]


def _frame(ctx, r, s, vs, size, k=0):
    r.draw_outputs(s, *size, 1.0, vs, t_now=2.0 + k / 60)
    assert ctx.error == "GL_NO_ERROR"
    return [_px(v.target) for v in vs]


def _s(**kw) -> view.ViewState:
    return _faces(resize={"resize": ResizeState(**kw)})


def _own(r, size=None):
    keys = [k for k in r._frames if isinstance(k, tuple) and k[0] == "resize#own"]
    if size is None:
        return keys
    return r._frames[("resize#own", size)][0]


def _f2(tex) -> np.ndarray:
    w, h = tex.size
    return np.frombuffer(tex.read(), np.float16).reshape(h, w, 4)[::-1].astype(float)


CHANNEL_OUT = [("channel.a", "resize.image"), ("resize", "output.2.image")]
WIDE = (160, 90)


def test_a_resize_makes_its_own_size(ctx):
    r = _wired_renderer(ctx, _media(a=Still(_rgba(16, 9))), CHANNEL_OUT, [RESIZE])
    _frame(ctx, r, _s(size=2), _views(ctx, WIDE), WIDE)
    assert _own(r) == [("resize#own", (64, 36))]
    assert _own(r, (64, 36)).dtype == "f2"
    assert "resize" in r._graph.timed
    assert r._graph.nodes["resize"].said == "64×36 · cover · linear"


def test_an_effect_after_a_resize_runs_at_its_size(ctx):
    """Review Focus 5: acid.2 after the resize runs in the 64×36 pool, every
    pass into a 64×36 target."""
    r = _wired_renderer(ctx, _media(a=Still(_rgba(16, 9))),
                        [("channel.a", "resize.image"), ("resize", "acid.2.image"),
                         ("acid.2", "output.2.image")], [RESIZE, ACID2],
                        {"acid": 2}, {"acid.2": {"on": True, "mix": 1.0}})
    sizes = []
    real = r.fx.run_one

    def spy(name, src, dst, *a, **k):
        if name == "acid.2":
            sizes.append(tuple(dst.color_attachments[0].size))
        return real(name, src, dst, *a, **k)

    r.fx.run_one = spy
    _frame(ctx, r, _s(size=2), _views(ctx, WIDE), WIDE)
    assert "acid.2" in r.stats["effects"]
    assert (64, 36) in r._pools
    assert sizes and set(sizes) == {(64, 36)}, sizes


def test_a_delay_through_a_resize_holds_a_small_buffer(ctx):
    """Review Focus 5: the owner's headline — the scene at 64² square into
    the delay onto the faces: the delay holds 64×64, its write after the
    resize and before the outputs."""
    r = _wired_renderer(ctx, None, [("scene", "resize.image"), ("resize", "delay.image"),
                                    ("delay", "shape.faces")], [RESIZE, DELAY])
    s, vs = _s(size=2, aspect=1), _views(ctx, WIDE, 1)
    for k in range(2):
        _frame(ctx, r, s, vs, WIDE, k)
    assert r.delay_pair("delay").read[0].size == (64, 64)
    order = [n.name for n in r._graph.order]
    # (plan 36 T4: no look-back is drawn in this frame — the write before the outputs)
    assert order.index("resize") < order.index("delay(write)") < order.index("output.1")


def test_a_loop_through_a_resize_and_a_delay_is_legal(ctx):
    """Review Focus 1: `delay → resize`, `resize → delay` reads with no notes,
    draws with no GL error, and the resize never samples the delay's write
    side."""
    pairs = [("delay", "resize.image"), ("resize", "delay.image"), ("delay", "output.2.image")]
    assert not G.read_graph(wired(*pairs, *FACTORY_FRAME, nodes=[DELAY, RESIZE])).notes
    r = _wired_renderer(ctx, None, pairs, [DELAY, RESIZE])
    seen: list[tuple[int, int | None]] = []
    real = r._refit

    def spy(tex, dst, *a, **k):
        pair = getattr(r, "_delays", {}).get("delay")
        write = pair.write[0].glo if pair is not None and pair.write is not None else None
        seen.append((tex.glo, write))
        return real(tex, dst, *a, **k)

    r._refit = spy
    # (an empty loop stays empty, R7: the pair is seeded with a red frame,
    # so the picture goes round — delay → resize → delay(write) — 4 times)
    pair = r.delay_pair("delay")
    pair.target(ctx, WIDE).clear(1.0, 0.0, 0.0, 1.0)
    pair.wrote = True
    s, vs = _s(size=2), _views(ctx, WIDE)
    outs = []
    for k in range(4):
        outs.append(_frame(ctx, r, s, vs, WIDE, k)[1])
    assert ctx.error == "GL_NO_ERROR"
    assert r.delay_pair("delay").holds and r.delay_pair("delay").read[0].size == (64, 36)
    assert tuple(outs[-1][45, 80, :3]) == RED
    assert len(seen) >= 8
    for tex, write in seen:
        assert tex != write, (tex, write)


def _quadrants(n=64) -> np.ndarray:
    px = _rgba(n, n, RED)
    h = n // 2
    px[:h, h:, :3] = GREEN
    px[h:, :h, :3] = BLUE
    px[h:, h:, :3] = WHITE
    return px


def test_the_crop_takes_the_rect(ctx):
    size = (64, 64)
    r = _wired_renderer(ctx, _media(a=Still(_quadrants())), CHANNEL_OUT, [RESIZE])
    out = _frame(ctx, r, _s(size=2, crop_x=0.25, crop_y=0.25, crop_w=0.5, crop_h=0.5),
                 _views(ctx, size), size)[1]
    for y, x in ((32, 32), (4, 4), (4, 59), (59, 4), (59, 59)):
        assert tuple(out[y, x, :3]) == RED, (y, x, out[y, x])


def test_a_crop_past_the_edge_is_transparent(ctx):
    r = _wired_renderer(ctx, _media(a=Still(_rgba(16, 9))), CHANNEL_OUT, [RESIZE])
    _frame(ctx, r, _s(size=2, crop_x=0.9, crop_w=0.5), _views(ctx, WIDE), WIDE)
    made = _f2(_own(r, (64, 36)))
    w = made.shape[1]
    right = made[:, int(w * 0.75):]
    left = made[:, :int(w * 0.6)]
    assert (right == 0.0).all(), right[0, :, :]
    assert (np.abs(left - (1.0, 0.0, 0.0, 1.0)) < 0.01).all(), left[0, :4]


def _checker(n=64) -> np.ndarray:
    px = _rgba(n, n, RED)
    h = n // 2
    px[:h, h:, :3] = BLUE
    px[h:, :h, :3] = BLUE
    return px


def test_nearest_keeps_hard_pixels(ctx):
    size = (64, 64)
    for filt, hard in ((1, True), (0, False)):
        r = _wired_renderer(ctx, _media(a=Still(_checker())), CHANNEL_OUT, [RESIZE])
        out = _frame(ctx, r, _s(size=0, filter=filt), _views(ctx, size), size)[1][..., :3]
        flat = out.reshape(-1, 3)
        pure = np.all((flat == RED) | (flat == BLUE), axis=1)
        assert pure.all() == hard, (filt, flat[~pure][:4])


def _stripes(n=512) -> np.ndarray:
    px = _rgba(n, n, (0, 0, 0))
    px[:, ::2, 0] = 255
    return px


def test_linear_mipmaps_a_big_reduction(ctx):
    size = (512, 512)
    for filt in (0, 1):
        r = _wired_renderer(ctx, _media(a=Still(_stripes())), CHANNEL_OUT, [RESIZE])
        mips = []
        real = r._refit

        def spy(tex, dst, *a, real=real, mips=mips, **k):
            mips.append(k.get("mip", False))
            return real(tex, dst, *a, **k)

        r._refit = spy
        _frame(ctx, r, _s(size=0, filter=filt), _views(ctx, size), size)
        red = _f2(_own(r, (16, 16)))[..., 0]
        if filt == 0:
            assert (np.abs(red - 0.5) <= 0.1).all(), red
            assert mips[0] is True
        else:
            assert np.isin(red, (0.0, 1.0)).all(), red
            assert not any(mips)


def test_a_crop_change_is_a_value_never_a_rebuild(ctx):
    r = _wired_renderer(ctx, _media(a=Still(_quadrants())), CHANNEL_OUT, [RESIZE])
    graphs = []
    real = r._graph_for

    def spy(*a, **k):
        g = real(*a, **k)
        graphs.append(g)
        return g

    r._graph_for = spy
    s, vs, size = _s(size=2), _views(ctx, (64, 64)), (64, 64)
    outs = []
    for k in range(5):
        if k == 4:
            s.resize["resize"].crop_w = 0.5
        outs.append(_frame(ctx, r, s, vs, size, k)[1])
    assert len({id(g) for g in graphs}) == 1
    assert not np.array_equal(outs[0], outs[4])


def test_a_size_step_reallocates_once_each_way(ctx):
    """Review Focus 4: 64 → 128 → 64 → 128 makes two own targets, each once,
    and keeps both (`SIZED_KEEP_FRAMES`)."""
    r = _wired_renderer(ctx, _media(a=Still(_rgba(16, 9))), CHANNEL_OUT, [RESIZE])
    s, vs = _s(size=2), _views(ctx, WIDE)
    glo = []
    for k, idx in enumerate((2, 3, 2, 3)):
        s.resize["resize"].size = idx
        _frame(ctx, r, s, vs, WIDE, k)
        own = (64, 36) if idx == 2 else (128, 72)
        glo.append(_own(r, own).glo)
    assert sorted(_own(r)) == [("resize#own", (64, 36)), ("resize#own", (128, 72))]
    assert glo[0] == glo[2] and glo[1] == glo[3] and glo[0] != glo[1]


def test_the_resize_says_its_size_fit_filter_and_crop(ctx):
    r = _wired_renderer(ctx, _media(a=Still(_rgba(16, 9))), CHANNEL_OUT, [RESIZE])
    _frame(ctx, r, _s(size=2, crop_w=0.5, filter=1), _views(ctx, WIDE), WIDE)
    assert r._graph.nodes["resize"].said == "64×36 · cover · nearest · crop 50%×100%"
    r = _wired_renderer(ctx, _media(), CHANNEL_OUT, [RESIZE])
    _frame(ctx, r, _s(size=2), _views(ctx, WIDE), WIDE)
    assert r._graph.nodes["resize"].said == "its input reads nothing"


def test_resize_knobs_survive_a_hot_reload_of_view(monkeypatch):
    """Review fix round 1: after a hot reload of `view` (`params.ResizeState`
    a new class), a redeclare keeps the live state the params are bound to —
    so the knob and the renderer's state stay one."""
    import dataclasses

    reg = params.Registry()
    params.declare_resizes(reg, ["resize"])
    live = reg.resize_state["resize"]
    reg["resize.crop_x"].set(0.3)
    reloaded = dataclasses.make_dataclass(
        "ResizeState", [(f.name, f.type, dataclasses.field(default=f.default))
                        for f in dataclasses.fields(ResizeState)])
    monkeypatch.setattr(params, "ResizeState", reloaded)
    assert params.declare_resizes(reg, ["resize"]) == []
    assert reg.resize_state["resize"] is live
    assert reg["resize.crop_x"].value == live.crop_x == 0.3
    reg["resize.crop_x"].set(0.7)
    assert reg.resize_state["resize"].crop_x == 0.7
    params.declare_resizes(reg, ["resize", "resize.2"])
    assert isinstance(reg.resize_state["resize.2"], reloaded)


def test_two_consumers_of_one_resize_refit_from_the_one_small_picture(ctx):
    """Review fix round 1: `resize` into output 2 (160×90) and onto the faces
    (1024²) is made once a frame and refitted twice from that one small
    picture; in steady state no frame target is made."""
    r = _wired_renderer(ctx, _media(a=Still(_rgba(16, 9))),
                        [("channel.a", "resize.image"), ("resize", "output.2.image"),
                         ("resize", "shape.faces")], [RESIZE])
    calls: list[tuple[int, tuple[int, int]]] = []
    real = r._refit

    def spy(tex, dst, *a, **k):
        calls.append((tex.glo, tuple(dst.viewport[2:])))
        return real(tex, dst, *a, **k)

    r._refit = spy
    s, vs = _s(size=2), _views(ctx, WIDE)
    keys = None
    for k in range(4):
        calls.clear()
        _frame(ctx, r, s, vs, WIDE, k)
        small = _own(r, (64, 36)).glo
        made = [c for c in calls if c[1] == (64, 36)]
        fitted = [c for c in calls if c[0] == small]
        assert len(made) == 1 and made[0][0] != small, calls
        assert len(fitted) == 2, calls
        assert {c[1] for c in fitted} == {WIDE, (G.FACE_PIC, G.FACE_PIC)}, calls
        if k >= 1:
            if keys is not None:
                assert set(r._frames) == keys
            keys = set(r._frames)


def test_a_load_frees_the_last_presets_frame_targets(ctx):
    """R16 (final review): preset A (channel a through a resize into
    outputs 2 and 3), then preset B (channel b alone into output 2): 60
    frames later none of A's frame targets — its `shown(...)` end, the
    resize's own size, channel a's fit — is held, and what is
    held is what B alone holds in steady state."""
    media = _media(a=Still(_rgba(16, 9)), b=Still(_rgba(16, 9, BLUE)))
    s, vs = _s(size=2), _views(ctx, WIDE, 3)
    r = _wired_renderer(ctx, media, [*CHANNEL_OUT, ("resize", "output.3.image")], [RESIZE])
    for k in range(3):
        _frame(ctx, r, s, vs, WIDE, k)
    a_keys = set(r._frames)
    assert {"shown(resize)", "media.a", ("resize#own", (64, 36))} <= a_keys, a_keys
    b = [("channel.b", "output.2.image")]
    r.wiring = _spec(*b).wiring()
    _frame(ctx, r, s, vs, WIDE, 0)
    b_keys = set(r._frames) - a_keys
    for k in range(60):
        _frame(ctx, r, s, vs, WIDE, k)
    left = set(r._frames)
    assert not [k for k in left if "resize" in str(k) or "media.a" in str(k)], left
    fresh = _wired_renderer(ctx, media, b)
    for k in range(60):
        _frame(ctx, fresh, s, vs, WIDE, k)
    assert left == set(fresh._frames) and b_keys <= left, (left, set(fresh._frames))
