
"""Plan 34 T2 — the delay (D, rows 353–358): last frame's picture, held by
the renderer in a half-float ping-pong pair (`render.DelayPair`), so a loop
drawn on GRAPH through a delay is legal and draws.

`Delay` is the read side (no inputs: what came in last frame), `DelayWrite`
(`delay(write)`) paints its input into the other side before the capture,
and `Renderer._turn_delays` swaps the two once a frame. What it must keep
honest: the first frame reads nothing (the faces show the pattern), no pass
ever samples the texture it writes, a size change or a GRAPH edit elsewhere
loses no frame, a delay that leaves the graph is released, and nothing of
plan 33 has an own size — so the refit never runs for the 693 goldens.

The GL tests use test_graph_faces' harness; they skip without a standalone
context."""

from __future__ import annotations

import math
from itertools import pairwise
from types import SimpleNamespace

import numpy as np
import pytest
from test_graph_faces import (
    Still,
    _draw,
    _empty,
    _faces,
    _fbo,
    _media,
    _px,
    _renderer,
    _rgba,
    _rig_frame,
    _tool,
    section,
)

from hyperspace import graph as G
from hyperspace import media_tex
from hyperspace.graphmigrate import wired_wiring
from hyperspace.media.frame import MediaFrame
from hyperspace.outputs import Switches, View

RED, BLUE, GREEN = (255, 0, 0), (0, 0, 255), (0, 255, 0)
DELAY = [{"kind": "delay"}]
moderngl = pytest.importorskip("moderngl")


def test_own_fit_is_cover():
    """`graph.OWN_FIT` is `media_tex.COVER` (graph.py imports no media
    module, so the constant is written out: plan 34 row 358)."""
    assert G.OWN_FIT == media_tex.COVER
    assert media_tex.FITS[G.OWN_FIT] == "cover"


def test_the_delay_write_runs_after_its_readers():
    """`delay(write)` runs after what reads the delay, so last frame's
    picture is read before this frame's is kept (row 353; plan 90 H2: the
    look-back's capture, which it ran before, is retired)."""
    vs = [View(Switches(), (64, 48))]
    spec = G.read_graph(section(("frame", "fx.image"), ("scene", "delay.image"),
                                ("delay", "shape.faces"), nodes=DELAY))
    assert not spec.notes, spec.notes
    g = G.build_graph(vs, wired_wiring(spec.wiring()))
    order = [n.name for n in g.order]
    write = g.nodes["delay(write)"]
    assert isinstance(write, G.DelayWrite) and write.delay == "delay"
    assert write.inputs["image"] is g.nodes["scene"]
    assert isinstance(g.nodes["delay"], G.Delay)
    assert g.nodes["shape"].inputs["faces"] is g.nodes["delay"]
    assert order.index("delay(write)") > max(order.index("delay"), order.index("shape"),
                                             order.index("scene"))
    assert "delay(write)" in g.timed and not g.dormant


def test_the_delay_nodes_say_what_they_are():
    """The two halves' shapes (the brief's Interfaces)."""
    assert G.Delay.KIND == G.DelayWrite.KIND == "delay"
    assert G.Delay.INPUTS == {} and G.Delay.OUTPUT == G.IMAGE and not G.Delay.TIMED
    assert G.DelayWrite.INPUTS == {"image": G.IMAGE} and G.DelayWrite.OUTPUT is None
    assert G.DelayWrite.TIMED and G.DelayWrite.SIZED == frozenset({"image"})
    assert G.Node.said == "" and G.Node("x").own_size(None) is None


# ---------------------------------------------------------------- GL

def _views(ctx, size, n=2):
    return [View(Switches(), size, target=_fbo(ctx, *size)) for _ in range(n)]


def _frame(ctx, r, s, vs, size, k):
    r.draw_outputs(s, *size, 1.0, vs, t_now=2.0 + k / 60)
    assert ctx.error == "GL_NO_ERROR"
    return [_px(v.target) for v in vs]


def _mid(px):
    h, w = px.shape[:2]
    return tuple(int(c) for c in px[h // 2, w // 2, :3])


def test_a_delay_shows_last_frames_picture(ctx):
    """Channel a's still red, then blue, then green over frames 1–3, with
    `media.a → delay.image` and `delay → output.2.image`: output 2 shows
    the ground at frame 1 (the delay holds nothing yet), red at frame 2 and
    blue at frame 3 — a frame late, exactly (row 353)."""
    size = (160, 120)
    still = Still(_rgba(16, 9, RED))
    r = _renderer(ctx, _media(a=still), [("media.a", "delay.image"),
                                         ("delay", "output.2.image")], DELAY)
    vs = _views(ctx, size)
    s = _faces()
    got = []
    for k, colour in enumerate((RED, BLUE, GREEN)):
        still.f = MediaFrame(_rgba(16, 9, colour), 1.0, k)
        got.append(_mid(_frame(ctx, r, s, vs, size, k)[1]))
    assert got == [(0, 0, 0), RED, BLUE], got


def test_the_first_frame_reads_nothing_and_the_faces_show_the_pattern(ctx):
    """`scene → delay.image`, `delay → shape.faces`: on frame 1 the delay
    reads nothing, so the faces show the pattern — the faces-unwired frame,
    pixel for pixel; on frame 2 they show last frame's scene (row 353)."""
    s = _faces()
    plain = _draw(ctx, _renderer(ctx), s)[0]
    r = _renderer(ctx, None, [("scene", "delay.image"), ("delay", "shape.faces")], DELAY)
    vs = [View(Switches(), (160, 120), target=_fbo(ctx, 160, 120))]
    (first,) = _frame(ctx, r, s, vs, (160, 120), 0)
    assert np.array_equal(first, plain)
    (second,) = _frame(ctx, r, s, vs, (160, 120), 0)
    assert r.face_error == "" and not np.array_equal(second, plain)


def test_a_delay_ping_pongs_half_float(ctx):
    """Review Focus 1: after every frame the pair's two sides are distinct
    half-float textures, and the side read at frame n+1 is the one written
    at frame n (`glo` compared) — no pass reads what it writes (row 354).
    The first frame has no read side yet: nothing came in before it."""
    size = (160, 120)
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9))),
                  [("media.a", "delay.image"), ("delay", "output.2.image")], DELAY)
    vs, s = _views(ctx, size), _faces()
    _frame(ctx, r, s, vs, size, 0)
    pair = r.delay_pair("delay")
    assert pair.read is None and pair.write[0].dtype == "f2"
    wrote = pair.write[0].glo
    for k in range(1, 4):
        _frame(ctx, r, s, vs, size, k)
        pair = r.delay_pair("delay")
        assert pair.read[0].dtype == pair.write[0].dtype == "f2"
        assert pair.read[0].glo != pair.write[0].glo
        assert pair.read[0].glo == wrote and pair.holds
        wrote = pair.write[0].glo


def _trails(ctx):
    tool = _tool()
    return tool.Rig("delay-trails", "absent", ctx)


def test_a_loop_of_effects_never_reads_what_it_writes(ctx):
    """Review Focus 1: the `delay-trails` loop (`delay → zoomblur.2 →
    palette.2 → composite.2.over`, `composite.2 → delay.image`) over 8
    frames: no GL error, and no effect pass samples the texture it writes,
    nor the delay's write side (row 354)."""
    rig = _trails(ctx)
    try:
        r = rig.renderer
        passes: list[tuple[int, int, int | None]] = []
        real = r.fx.run_one

        def spy(name, src, dst, *a, **k):
            pair = getattr(r, "_delays", {}).get("delay")
            write = pair.write[0].glo if pair is not None and pair.write is not None else None
            passes.append((src.glo, dst.color_attachments[0].glo, write))
            return real(name, src, dst, *a, **k)

        r.fx.run_one = spy
        size = (240, 150)
        vs = [View(Switches(), size, target=_fbo(ctx, *size))]
        for _ in range(8):
            rig.frame(vs, size, 1.0)
        assert ctx.error == "GL_NO_ERROR"
        assert "zoomblur.2" in r.stats["effects"] and passes
        assert r.delay_pair("delay").holds
        for src, dst, write in passes:
            assert src != dst and src != write, (src, dst, write)
    finally:
        rig.close()


TRAILS = [("delay", "zoomblur.2.image"), ("zoomblur.2", "palette.2.image"),
          ("scene", "composite.2.under"), ("palette.2", "composite.2.over"),
          ("composite.2", "output.1.image"), ("composite.2", "delay.image")]


def test_the_trails_show_and_fade(ctx):
    """R6: the `delay-trails` fixture after the golden's 8 frames is not
    party-faces' frame (the trail shows), and the trails fade: the same
    graph (last frame darkened by palette.2's val slice to 0.6, added over
    the scene) with the shape drawn for six frames and then an empty scene,
    each frame's picture is strictly darker than the one before and gone
    within fifteen — it decays, never sticks or saturates."""
    trails, _ = _rig_frame(ctx, "delay-trails", frames=8)
    plain, _ = _rig_frame(ctx, "party-faces", frames=8)
    assert np.abs(trails[..., :3] - plain[..., :3]).max() > 40
    assert (trails[..., :3].sum(axis=2) > plain[..., :3].sum(axis=2) + 30).mean() > 0.01
    size = (160, 120)
    r = _renderer(ctx, None, TRAILS,
                  [{"kind": "effect", "file": "zoomblur", "instance": 2},
                   {"kind": "effect", "file": "palette", "instance": 2},
                   {"kind": "composite", "instance": 2, "blend": "add"}, *DELAY],
                  {"zoomblur": 2, "palette": 2},
                  {"zoomblur.2": {"on": True, "mix": 1.0, "amount": 0.15, "glow": 0.0},
                   "palette.2": {"on": True, "mix": 1.0, "val_to": 0.6}})
    vs = [View(Switches(), size, target=_fbo(ctx, *size))]
    for k in range(6):
        _frame(ctx, r, _faces(), vs, size, k)
    sums = []
    for k in range(6, 21):
        (px,) = _frame(ctx, r, _empty(), vs, size, k)
        sums.append(int(px[..., :3].sum()))
        if k == 20:
            assert px[..., :3].max() <= 2, px[..., :3].max()
    assert sums[0] > 0 and "palette.2" in r.stats["effects"]
    assert all(b < a for a, b in pairwise(sums) if a > 0), sums


def test_a_delay_whose_input_read_nothing_reads_nothing(ctx):
    """R7: `media.a → delay.image`, `delay → shape.faces`. While the
    channel shows a still, the faces show last frame's still; the frame its
    feed is lost the delay writes nothing, so the frame after the faces
    fall back to the pattern (plan 33's rule) — the faces-unwired frame,
    pixel for pixel — never black. An empty channel reads nothing from the
    first frame on."""
    size, s = (160, 120), _faces(pattern=2)
    plain_r = _renderer(ctx, _media())
    plain_vs = [View(Switches(), size, target=_fbo(ctx, *size))]
    plain = [_frame(ctx, plain_r, s, plain_vs, size, k)[0] for k in range(4)]
    pairs = [("media.a", "delay.image"), ("delay", "shape.faces")]
    still = Still(_rgba(16, 9))
    r = _renderer(ctx, _media(a=still), pairs, DELAY)
    vs = [View(Switches(), size, target=_fbo(ctx, *size))]
    got = []
    for k in range(4):
        if k == 2:
            still.gone = True                                 # the feed lost
        got.append(_frame(ctx, r, s, vs, size, k)[0])
    assert np.array_equal(got[0], plain[0])                    # nothing came in before
    assert not np.array_equal(got[1], plain[1])                # last frame's still
    assert not np.array_equal(got[2], plain[2])                # (still frame 1's)
    assert np.array_equal(got[3], plain[3]) and r.face_error == ""
    assert not r.delay_pair("delay").holds
    empty = _renderer(ctx, _media(), pairs, DELAY)
    for k in range(3):
        (px,) = _frame(ctx, empty, s, vs, size, k)
        assert np.array_equal(px, plain[k]), k


def test_a_size_change_loses_no_frame(ctx):
    """Review Focus 4: two frames at 240×150, then frame 3 at 200×200 —
    output 2 is not the ground but frame 2's picture fitted (the read side
    kept its size; only the write side is made again, row 357)."""
    still = Still(_rgba(16, 9, RED))
    r = _renderer(ctx, _media(a=still), [("media.a", "delay.image"),
                                         ("delay", "output.2.image")], DELAY)
    s = _faces()
    vs = _views(ctx, (240, 150))
    for k in range(2):
        _frame(ctx, r, s, vs, (240, 150), k)
    still.f = MediaFrame(_rgba(16, 9, BLUE), 1.0, 5)
    vs = _views(ctx, (200, 200))
    out = _frame(ctx, r, s, vs, (200, 200), 2)[1]
    assert _mid(out) == RED                         # frame 2's picture, not the ground
    pair = r.delay_pair("delay")
    assert pair.write[0].size == (200, 200) and pair.read[0].size == (240, 150)
    out = _frame(ctx, r, s, vs, (200, 200), 3)[1]
    assert _mid(out) == BLUE


def test_a_graph_rebuild_keeps_the_delay(ctx):
    """Review Focus 4: a GRAPH edit elsewhere (`media.b → output.3.image`
    added) builds a new graph, and the delay still holds last frame's
    picture at frame 3 (row 354: the pair is the renderer's, by name)."""
    size = (160, 120)
    pairs = [("media.a", "delay.image"), ("delay", "output.2.image")]
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9)), b=Still(_rgba(16, 9, BLUE))), pairs,
                  DELAY)
    vs, s = _views(ctx, size, 3), _faces()
    for k in range(2):
        _frame(ctx, r, s, vs, size, k)
    old = r._graph
    r.wiring = wired_wiring(G.read_graph(section(("frame", "fx.image"), *pairs,
                                    ("media.b", "output.3.image"), nodes=DELAY)).wiring())
    got = _frame(ctx, r, s, vs, size, 2)
    assert r._graph is not old and r.delay_pair("delay").holds
    assert _mid(got[1]) == RED and _mid(got[2]) == BLUE


def test_a_load_resets_the_delays_and_a_rebuild_keeps_them(ctx):
    """R19 (final review, row 354 "rebuilds, not loads"): a delay holding
    red, then `reset_delays` (what a loadable patch load asks) — the next frame
    reads nothing, the ground, as a first frame does, then the picture
    again; with no reset a rebuild of the same graph still holds red."""
    size = (160, 120)
    pairs = [("media.a", "delay.image"), ("delay", "output.2.image")]
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9))), pairs, DELAY)
    vs, s = _views(ctx, size), _faces()
    for k in range(2):
        assert _mid(_frame(ctx, r, s, vs, size, k)[1]) == ((0, 0, 0) if k == 0 else RED)
    r.wiring = wired_wiring(G.read_graph(section(("frame", "fx.image"), *pairs, nodes=DELAY)).wiring())
    assert _mid(_frame(ctx, r, s, vs, size, 2)[1]) == RED
    r.reset_delays()
    assert _mid(_frame(ctx, r, s, vs, size, 3)[1]) == (0, 0, 0)
    assert _mid(_frame(ctx, r, s, vs, size, 4)[1]) == RED


def test_a_loadable_load_asks_for_the_reset_and_a_graph_edit_does_not(tmp_path):
    """R19: `LoadedPatch.load_doc` landing a section asks the attached renderer
    to reset its delays; a GRAPH edit (an `Edit` landing) does not."""
    from test_graph_edit import wired_rig

    rig, e, _ = wired_rig(tmp_path, slug="delay-trails")
    calls = []
    rig.loaded_patch.graph.renderer.reset_delays = lambda: calls.append(1)
    spec = rig.loaded_patch.graph.spec
    w = next(w for w in spec.wires if w.dst != "delay.image" and w.src != "delay")
    assert e.unwire(f"rout:{w.src}", f"rin:{w.node}/{w.port}") is None
    assert calls == []
    rig.lib.load("loadable", "delay-trails")
    assert calls == [1]


def test_a_delay_leaving_the_graph_is_released(ctx):
    """Review Focus 4: the delay's wires removed, its pair is kept for
    `SIZED_KEEP_FRAMES - 1` frames (a flick back costs nothing) and
    released after `SIZED_KEEP_FRAMES` (row 354)."""
    from hyperspace.render import SIZED_KEEP_FRAMES

    size = (96, 64)
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9))),
                  [("media.a", "delay.image"), ("delay", "output.2.image")], DELAY)
    vs, s = _views(ctx, size), _faces()
    for k in range(2):
        _frame(ctx, r, s, vs, size, k)
    assert "delay" in r._delays
    r.wiring = wired_wiring(G.read_graph(section(("frame", "fx.image"))).wiring())
    for k in range(SIZED_KEEP_FRAMES - 1):
        _frame(ctx, r, s, vs, size, k)
        assert "delay" in r._delays, k
    _frame(ctx, r, s, vs, size, 0)
    assert "delay" not in r._delays
    assert "delay#fit" not in r._frames


def test_refit_cover_and_contain(ctx):
    """`Renderer._refit` (row 358): a 200×100 texture, left half red and
    right half blue, into 64×64 — cover crops the sides (columns 0–31 red,
    32–63 blue), contain letterboxes (rows 0–15 and 48–63 transparent
    black, the middle half and half), stretch fills; a sampler object sets
    the filter, so the texture's own is never changed, mipmaps or not."""
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    px = np.zeros((100, 200, 4), np.uint8)
    px[..., 3] = 255
    px[:, :100, 0] = 255
    px[:, 100:, 2] = 255
    tex = ctx.texture((200, 100), 4, px.tobytes())
    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    out = ctx.texture((64, 64), 4)
    fbo = ctx.framebuffer(color_attachments=[out])

    def refit(fit, **kw):
        fbo.use()
        fbo.clear(0.5, 0.5, 0.5, 0.5)
        r._refit(tex, fbo, fit=fit, **kw)
        assert ctx.error == "GL_NO_ERROR"
        return np.frombuffer(out.read(), np.uint8).reshape(64, 64, 4).astype(int)

    red, blue, none = [255, 0, 0, 255], [0, 0, 255, 255], [0, 0, 0, 0]
    got = refit(media_tex.COVER)
    assert (got[:, :32] == red).all() and (got[:, 32:] == blue).all()
    got = refit(media_tex.CONTAIN)
    assert (got[:16] == none).all() and (got[48:] == none).all()
    assert (got[16:48, :32] == red).all() and (got[16:48, 32:] == blue).all()
    got = refit(media_tex.STRETCH)
    assert (got[:, :32] == red).all() and (got[:, 32:] == blue).all()
    got = refit(media_tex.COVER, mip=True)            # (trilinear: the seam blends)
    assert (got[:, :28] == red).all() and (got[:, 36:] == blue).all()
    assert tex.filter == (moderngl.NEAREST, moderngl.NEAREST)


# the plan-34 fixtures: everything else under tests/fixtures/presets/ the
# golden tool draws is plan 33's or earlier
PLAN_34 = {"delay-faces", "delay-trails", "echo-faces", "resize-faces", "resize-crop"}


def test_nothing_of_plan_33_has_an_own_size(ctx):
    """Review Focus 3: no node of the default graph, nor of any earlier
    fixture's graph (landed through the golden tool's `Rig`), has an own
    size — so the `Effect` own-size path and the refit never run for the
    693 goldens (row 368). (Plan 90 H2: but one — a fixture whose old values
    drew a look-back lands it as public parts, and the resize before its
    delay keeps 512 on the long side by design (Q24): the one own size.)"""
    from hyperspace.render import Renderer

    vs = [View(Switches(), (240, 150))]
    graphs = [("default", G.build_graph(vs, wired_wiring(G.Wiring(run=()))), Renderer(ctx))]
    tool = _tool()
    for slug in tool.FIXTURE_LOADABLES:
        if slug in PLAN_34:
            continue
        rig = tool.Rig(slug, "absent", ctx)
        try:
            graphs.append((slug, rig.renderer._graph_for(vs, rig.view), rig.renderer))
        finally:
            rig.close()
    assert len(graphs) > 15
    for slug, g, r in graphs:
        switches = [n.name for n in g.nodes.values() if isinstance(n, G.SwitchNode)]
        for k in range(len(G.SWITCH_PORTS) + 1):          # every pick, off included
            frame = SimpleNamespace(size=(240, 150), r=r,
                                    selects=dict.fromkeys(switches, k))
            frame.root = frame
            writes = [m.inputs["image"] for m in g.nodes.values()
                      if isinstance(m, G.DelayWrite)]
            for n in g.nodes.values():
                if isinstance(n, G.ResizeNode) and any(n is w for w in writes):
                    continue                    # (the migrated look-back's, Q24)
                assert n.own_size(frame) is None, (slug, n.name)


def test_a_query_inside_another_is_a_no_op(ctx):
    """`delay(write)` times its paint, and an effect it paints times its own
    pass: GL allows one time query active at once, so the inner one is a
    no-op and the outer line holds both (`PassTimer.time`)."""
    from hyperspace.render import PassTimer

    t = PassTimer(ctx)
    if not t.on:
        pytest.skip(f"no timer queries: {t.note}")
    with t.time("delay(write)"), t.time("zoomblur.2"):
        pass
    with t.time("zoomblur.2"):
        pass
    assert ctx.error == "GL_NO_ERROR"
    assert [name for name, _ in t._frame] == ["delay(write)", "zoomblur.2"]


# ---------------------------------------------------------------- the rate

def test_delay_params_come_and_go_and_write_the_state():
    """`delay[.n].every / frames / hz` are declared from the graph's delays,
    write a `DelayState` kept while the name stays, and go with the delay."""
    from hyperspace import params
    from hyperspace.view import DELAY_EVERY

    reg = params.Registry()
    made = params.declare_delays(reg, ["delay", "delay.2"])
    assert sorted(made) == sorted(params.delay_ids("delay") + params.delay_ids("delay.2"))
    assert all(reg[pid].group == params.DELAY_GROUP == "delay" for pid in made)
    assert params.DELAY_GROUP in params.PATCH_GROUPS
    reg["delay.frames"].set(5)
    reg["delay.2.every"].set(DELAY_EVERY.index("1/4"))
    assert reg.delay_state["delay"].frames == 5
    assert DELAY_EVERY[reg.delay_state["delay.2"].every] == "1/4"
    kept = reg.delay_state["delay"]
    assert params.declare_delays(reg, ["delay", "delay.2"]) == []
    assert reg.delay_state["delay"] is kept
    gone = params.declare_delays(reg, ["delay"])
    assert sorted(gone) == sorted(params.delay_ids("delay.2"))
    assert "delay.2" not in reg.delay_state
    assert params.is_delay_id("delay.12.hz") and not params.is_delay_id("delay.1.hz")
    assert not params.is_delay_id("delay.rate")


def _booked(st, frames, dt=1 / 60, bpm=120.0):
    """The frames (0-based) a delay at `st` takes a picture on, over `frames`
    frames at `dt`, booked the way `DelayWrite` and `DelayPair.turn` do."""
    from hyperspace.render import DelayPair

    pair, taken = DelayPair(), []
    for k in range(frames):
        t = 10.0 + k * dt
        if G.delay_due(pair, st, t, t * bpm / 60.0):
            taken.append(k)
            pair.wrote = pair.holds_any = True
        else:
            pair.kept = True
        pair.holds = pair.wrote or pair.kept        # (`turn`, without the textures)
        pair.wrote = pair.kept = False
    return taken


def test_every_frame_is_the_default_and_every_nth_takes_each_nth():
    from hyperspace.view import DelayState

    assert _booked(DelayState(), 6) == [0, 1, 2, 3, 4, 5]
    assert _booked(DelayState(frames=3), 10) == [0, 3, 6, 9]
    assert _booked(DelayState(frames=5), 11) == [0, 5, 10]


def test_hz_takes_that_many_a_second_whatever_the_frame_rate():
    from hyperspace.view import DELAY_EVERY, DelayState

    hz = DELAY_EVERY.index("Hz")
    assert len(_booked(DelayState(every=hz, hz=10.0), 120)) in (20, 21)       # 2 s at 60 fps
    assert len(_booked(DelayState(every=hz, hz=10.0), 60, dt=1 / 30)) in (20, 21)
    assert _booked(DelayState(every=hz, hz=120.0), 6) == [0, 1, 2, 3, 4, 5]   # above the rate


def test_tempo_units_take_one_a_cell_of_the_beat():
    from hyperspace.view import DELAY_EVERY, DelayState

    quarter_st = DelayState(every=DELAY_EVERY.index("1/4"))
    # 120 bpm = 2 beats/s: a quarter every 0.5 s, a bar every 2 s; 4 s at 60 fps
    quarter = _booked(quarter_st, 240)
    bar = _booked(DelayState(every=DELAY_EVERY.index("1 bar")), 240)
    assert len(quarter) in (8, 9) and len(bar) in (2, 3)
    assert {b - a for a, b in pairwise(quarter)} == {30}
    assert len(_booked(quarter_st, 240, bpm=240.0)) > len(quarter)


def test_a_delay_that_read_nothing_takes_again_at_once():
    """After a frame the pair held nothing (its input read nothing), the next
    frame takes a picture whatever the rate: no stale wait."""
    from hyperspace.render import DelayPair
    from hyperspace.view import DelayState

    pair, st = DelayPair(), DelayState(frames=8)
    assert G.delay_due(pair, st, 1.0, 2.0)
    pair.holds_any = True
    assert not G.delay_due(pair, st, 1.1, 2.2)
    pair.holds_any = False                               # `DelayPair.turn`: nothing written
    assert G.delay_due(pair, st, 1.2, 2.4)


def test_a_kept_pair_holds_its_picture_between_two():
    from hyperspace.render import DelayPair

    pair = DelayPair()
    pair.read, pair.write = ("a", "fa"), ("b", "fb")
    pair.holds = pair.holds_any = pair.kept = True
    pair.turn()
    assert pair.holds and pair.read == ("a", "fa")       # nothing swapped
    pair.turn()                                          # neither kept nor written
    assert not pair.holds and not pair.holds_any


def test_every_third_frame_holds_the_picture_between(ctx):
    """GL: channel a's still changes colour every frame; `media.a → delay →
    output.2` taking every 3rd frame shows each picture taken for three
    frames running, a frame after it was taken."""
    from hyperspace.view import DelayState

    size = (160, 120)
    still = Still(_rgba(16, 9, RED))
    r = _renderer(ctx, _media(a=still), [("media.a", "delay.image"),
                                         ("delay", "output.2.image")], DELAY)
    vs, s = _views(ctx, size), _faces()
    s.delay = {"delay": DelayState(frames=3)}
    colours = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255),
               (255, 0, 255), (255, 128, 0), (128, 0, 255)]
    got = []
    for k, colour in enumerate(colours):
        still.f = MediaFrame(_rgba(16, 9, colour), 1.0, k)
        got.append(_mid(_frame(ctx, r, s, vs, size, k)[1]))
    assert got == [(0, 0, 0), colours[0], colours[0], colours[0], colours[3], colours[3],
                   colours[3], colours[6]], got


def test_a_downbeat_placed_in_the_first_cell_takes_a_picture():
    """`Clock.trigger` resets the beat and bumps the epoch: entering cell 0 of
    the new grid is a new cell even when the old one was cell 0 too."""
    from hyperspace.render import DelayPair
    from hyperspace.view import DELAY_EVERY, DelayState

    pair, st = DelayPair(), DelayState(every=DELAY_EVERY.index("4 bars"))
    assert G.delay_due(pair, st, 1.0, 0.5, 0)
    pair.holds_any = True
    assert not G.delay_due(pair, st, 2.0, 4.0, 0)        # still cell 0, same grid
    assert G.delay_due(pair, st, 2.1, 0.0, 1)            # the downbeat placed: a new grid


def test_a_modulated_hz_runs_faster_and_slower_not_jumps():
    """The Hz phase advances by dt × the rate now, so a rate swung between 1
    and 3 Hz takes about 2 a second whatever the renderer's uptime."""
    from hyperspace.render import DelayPair
    from hyperspace.view import DELAY_EVERY, DelayState

    for uptime in (0.0, 60.0):
        pair, st, taken = DelayPair(), DelayState(every=DELAY_EVERY.index("Hz")), 0
        for k in range(120):                              # 2 s at 60 fps
            t = uptime + k / 60
            st.hz = 2.0 + math.sin(2 * math.pi * k / 60)
            if G.delay_due(pair, st, t, 0.0):
                taken += 1
                pair.holds_any = True
        assert 3 <= taken <= 6, (uptime, taken)


def test_a_pair_from_before_the_rate_is_made_whole():
    """A pair kept across a hot reload lacks the rate's fields: `delay_pair`
    gives them back, so the delay keeps drawing."""
    from types import SimpleNamespace

    from hyperspace.render import Renderer

    old = SimpleNamespace(read=None, write=None, holds=False, wrote=False, idle=0)
    r = Renderer.__new__(Renderer)
    r.__dict__["_delays"] = {"delay": old}
    got = r.delay_pair("delay")
    assert got is old and got.since == 0 and got.phase == 0.0 and not got.holds_any
