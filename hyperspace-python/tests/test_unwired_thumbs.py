"""Plan 65 (3): an effect node whose picture reaches no output is never
built (`graph.reaches`, register row 349: "kept, drawn faint, never run"),
so it made no picture for its thumbnail. Its thumbnail is now its input —
else the test card — put through it at a thumbnail's size, at the frame's
end (`render.unwired_through`, `graphview.UNWIRED_PIC`).

Held here: the outputs are the same bytes with those thumbnails wanted, the
node stays unbuilt and unrun by the frame, the thumbnail is the effect's
work on its real input when the frame made that input and on the card
when not, at most `UNWIRED_PER_FRAME` are made a frame (round robin), and
the page asks for it only for a faint effect."""

from __future__ import annotations

import numpy as np
from test_thumbnails import SIZE, S, _px, _views, _wire
from test_ui_shell import rig as shell_rig

from hyperspace import graphview, render, ui_graph

rig = shell_rig

UNWIRED = graphview.UNWIRED_PIC


def _renderer(ctx, extra=()):
    """The scene through kaleido to output 1; `wave` fed by the scene and
    feeding nothing, `acid` fed by nothing: both unreached."""
    r = render.Renderer(ctx)
    # (the thumbnails' clock held still: on the wall clock, a frame slower than
    # `THUMB_DROP_S` — a loaded CI runner compiling six effects — drops the
    # names it just made at the frame's end, and the counts here go wrong)
    r.thumbs.clock = lambda: 0.0
    r.ghost.state.on = False
    for n in ("kaleido", "wave", "acid", *extra):
        r.fx.state.values[n].update(on=True, mix=1.0)
    assert not r.fx.compile_all()
    r.wiring = _wire(("shape", "scene.geometry"), ("scene", "kaleido.image"),
                     ("kaleido", "output.1.image"), ("scene", "wave.image"),
                     nodes=({"kind": "effect", "file": "kaleido"},
                            {"kind": "effect", "file": "wave"},
                            {"kind": "effect", "file": "acid"},
                            *({"kind": "effect", "file": n} for n in extra)))
    return r


def _thumb(r, name: str) -> np.ndarray:
    tex = r.thumbs.get(name)
    assert tex is not None, name
    w, h = tex.size
    return np.frombuffer(tex.read(), np.uint8).reshape(h, w, 4).astype(int)


def test_the_outputs_are_the_same_bytes_and_the_node_stays_unbuilt(ctx):
    plain, wanted = _renderer(ctx), _renderer(ctx)
    pv, wv = _views(ctx), _views(ctx)
    for k in range(3):
        t = 2.0 + k / 60
        plain.draw_outputs(S, *SIZE, 1.0, pv, t_now=t)
        wanted.thumbs.want({"wave": UNWIRED, "acid": UNWIRED, "scene": "picture"})
        wanted.draw_outputs(S, *SIZE, 1.0, wv, t_now=t)
        assert ctx.error == "GL_NO_ERROR" and not wanted.thumbs.error
        for a, b in zip(pv, wv, strict=True):
            assert np.array_equal(_px(a.target), _px(b.target)), k
        assert plain.stats["effects"] == wanted.stats["effects"]
        assert plain.stats["chain_runs"] == wanted.stats["chain_runs"]
    g = wanted._graph
    assert "wave" not in g.nodes and "acid" not in g.nodes          # never built
    assert "wave" not in wanted.stats["effects"] and "acid" not in wanted.stats["effects"]
    assert wanted.thumbs.count == 3


def test_its_input_through_it_when_the_frame_made_the_input_else_the_card(ctx):
    r, views = _renderer(ctx), _views(ctx)
    r.thumbs.want({"wave": UNWIRED, "acid": UNWIRED, "scene": "picture"})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    scene, wave, acid = _thumb(r, "scene"), _thumb(r, "wave"), _thumb(r, "acid")
    # wave: the scene through the wave (the scene's own colours, moved)
    r.fx.state.values["wave"]["on"] = False
    r.thumbs.want({"wave": UNWIRED})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    off = _thumb(r, "wave")
    assert off.shape[:2] == wave.shape[:2]
    small = scene[:: max(1, scene.shape[0] // off.shape[0])][: off.shape[0]]
    assert np.abs(off[..., :3].mean() - small[..., :3].mean()) < 25    # the scene, as it is
    assert np.abs(off - wave).mean() > 1                               # … and the wave moved it
    # acid: no input — the test card through it (the card's colour bars at its foot)
    foot = acid[2, :, :3]
    assert (foot.max(-1) - foot.min(-1)).max() > 80


def test_an_input_the_frame_did_not_make_gives_the_card(ctx):
    """`acid → wave` with acid itself unreached: acid made nothing, so wave
    shows the card through it, not black."""
    r = _renderer(ctx)
    r.wiring = _wire(("shape", "scene.geometry"), ("scene", "kaleido.image"),
                     ("kaleido", "output.1.image"), ("acid", "wave.image"),
                     nodes=({"kind": "effect", "file": "kaleido"},
                            {"kind": "effect", "file": "wave"},
                            {"kind": "effect", "file": "acid"}))
    r.thumbs.want({"wave": UNWIRED})
    r.draw_outputs(S, *SIZE, 1.0, _views(ctx), t_now=2.0)
    wave = _thumb(r, "wave")
    assert wave[..., :3].max() > 200 and (wave[..., 3] == 255).all()


def test_at_most_the_budget_a_frame_round_robin(ctx):
    extra = ("grain", "bloom", "glimmer", "prism")
    r, views = _renderer(ctx, extra), _views(ctx)
    names = ["wave", "acid", *extra]
    made: list[set[str]] = []
    for k in range(3):
        before = dict(r.thumbs.made_in)
        r.thumbs.want(dict.fromkeys(names, UNWIRED))
        r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0 + k / 60)
        made.append({n for n in names if r.thumbs.made_in.get(n) != before.get(n)})
    assert all(len(m) == render.UNWIRED_PER_FRAME for m in made)
    assert made[0] | made[1] == set(names)                # every one within two frames


# ---------------------------------------------------------------- the page

def test_the_page_asks_for_it_only_for_a_faint_effect(rig):
    from test_thumbnails import party
    from test_ui_shell import frame
    st = party(rig)
    # a wave from the picker: on no wire, faint, never built
    assert ui_graph.add_render(rig.panel, ui_graph.render_edit(rig.panel), "effect", "wave",
                               (0.0, 0.0)) is None
    frame(rig.panel, "graph")
    frame(rig.panel, "graph")
    view = st["view"]
    assert view.node("render:wave").faint
    st["seen_rect"] = ((-1e9, -1e9), (1e9, 1e9))
    st["patch_only"] = False
    st["hide"] = ui_graph.hidden_ids(st, view)
    st.setdefault("revealed", set()).update(n.id for n in view.nodes)
    where = lambda nid: ((0.0, 0.0), (10.0, 10.0))
    got = ui_graph.thumb_wants(st, view, where)
    faint = [n for n in view.nodes if n.faint and ui_graph.has_card(n)]
    lit = [n for n in view.nodes if not n.faint and ui_graph.has_card(n)
           and ui_graph.thumb_name(n) in got]
    assert faint and lit
    for n in faint:
        assert got[ui_graph.thumb_name(n)] == UNWIRED
        assert graphview.UNWIRED_WORDS in ui_graph.thumb_tip(st, n)
    for n in lit:
        assert got[ui_graph.thumb_name(n)] == graphview.PICTURE
    others = {ui_graph.thumb_name(n) for n in view.nodes if not (n.faint and ui_graph.has_card(n))}
    assert UNWIRED not in {how for name, how in got.items() if name in others}
    # the card chip still wins: lit, the card through it
    ui_graph.toggle_card(st, faint[0])
    assert ui_graph.thumb_wants(st, view, where)[ui_graph.thumb_name(faint[0])] == \
        graphview.CARD_PIC
