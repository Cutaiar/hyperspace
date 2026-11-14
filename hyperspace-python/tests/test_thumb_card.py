"""An effect's thumbnail switched to the test card: the "card" chip on an
effect node of the GRAPH page (`ui_graph.toggle_card`) shows, in place of the
picture the effect made, the test card put through that one effect
(`render.card_through`, `graphview.CARD_PIC`).

Held here: the outputs are the same bytes with the card wanted or not, and
the Test card effect's own values are as they were; an effect that is off
shows the card straight; the card is drawn again only when it changed; and
the page asks for the card only for a node whose chip is lit, and offers the
chip only on effects."""

from __future__ import annotations

import numpy as np
from test_thumbnails import SIZE, S, _px, _renderer, _views, party
from test_ui_shell import rig as shell_rig

from hyperspace import graphview, render, ui_graph

rig = shell_rig


def _thumb(r, name: str) -> np.ndarray:
    tex = r.thumbs.get(name)
    assert tex is not None
    w, h = tex.size
    return np.frombuffer(tex.read(), np.uint8).reshape(h, w, 4).copy()


def test_the_outputs_are_the_same_bytes_with_the_card_wanted(ctx):
    plain, carded = _renderer(ctx), _renderer(ctx)
    pv, cv = _views(ctx), _views(ctx)
    before = dict(carded.fx.state.values["testcard"])
    for k in range(3):
        t = 2.0 + k / 60
        plain.draw_outputs(S, *SIZE, 1.0, pv, t_now=t)
        carded.thumbs.want({"kaleido": graphview.CARD_PIC, "scene": "picture"})
        carded.draw_outputs(S, *SIZE, 1.0, cv, t_now=t)
        assert ctx.error == "GL_NO_ERROR" and not carded.thumbs.error
        for a, b in zip(pv, cv, strict=True):
            assert np.array_equal(_px(a.target), _px(b.target)), k
        assert plain.stats["effects"] == carded.stats["effects"]
    assert carded.fx.state.values["testcard"] == before        # the graph's Test card: untouched
    assert carded.thumbs.count == 2


def test_the_card_thumbnail_is_the_card_through_the_effect_not_its_picture(ctx):
    r, views = _renderer(ctx), _views(ctx)
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    r.thumbs.want({"kaleido": "picture"})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.1)
    picture = _thumb(r, "kaleido")
    r.thumbs.want({"kaleido": graphview.CARD_PIC})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.2)
    through = _thumb(r, "kaleido")
    assert not r.thumbs.error
    assert (through[..., 3] == 255).all()
    assert np.abs(through.astype(int) - picture).mean() > 8      # another picture altogether
    # switched off, the effect passes its picture through: the card as it is,
    # its heavy cross through the centre and its colour bars at the foot
    r.fx.state.values["kaleido"]["on"] = False
    r.thumbs.want({"kaleido": graphview.CARD_PIC})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.3)
    card = _thumb(r, "kaleido").astype(int)
    assert np.abs(card - through).mean() > 4                     # the kaleidoscope did something
    h, w = card.shape[:2]
    assert card[h * 3 // 4, w // 2 - 1:w // 2 + 1, :3].max() > 200      # the cross
    foot = card[2, :, :3]                                        # row 2: the frame's foot (y up)
    assert (foot.max(-1) - foot.min(-1)).min() > 80              # every bar a colour


def test_the_card_needs_no_test_card_in_the_graph(ctx):
    """A landed graph's state holds only the effects it names
    (`FxState.hold`): the card is drawn from the file all the same, at the
    file's defaults, and a Test card the graph does hold sets its knobs."""
    r, views = _renderer(ctx), _views(ctx)
    r.fx.state.hold({"kaleido"})
    assert "testcard" not in r.fx.state.specs
    r.fx.state.values["kaleido"]["on"] = False                   # the card as it is
    r.thumbs.want({"kaleido": graphview.CARD_PIC})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    assert not r.thumbs.error and r.thumbs.count == 1
    default = _thumb(r, "kaleido").astype(int)
    assert default[..., :3].max() > 200 and "testcard" not in r.fx.state.specs
    r.fx.state.hold({"kaleido", "testcard"})
    r.fx.state.values["testcard"].update(grid=3.0, ground=0.5)
    r.thumbs.want({"kaleido": graphview.CARD_PIC})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.1)
    held = _thumb(r, "kaleido").astype(int)
    assert held[..., 1].mean() > default[..., 1].mean() + 15     # the grey ground came up


def test_the_card_is_drawn_again_only_when_it_changed(ctx, monkeypatch):
    r, views = _renderer(ctx), _views(ctx)
    ran: list[str] = []
    real = render.FxChain.run_one

    def counting(self, name, *a, **kw):
        ran.append(name)
        return real(self, name, *a, **kw)

    monkeypatch.setattr(render.FxChain, "run_one", counting)
    for k in range(3):
        r.thumbs.want({"kaleido": graphview.CARD_PIC})
        r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0 + k / 60)
    assert ran.count("testcard") == 1
    r.fx.state.values["testcard"]["grid"] = 6.0                  # a knob of the Test card's
    r.thumbs.want({"kaleido": graphview.CARD_PIC})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.1)
    assert ran.count("testcard") == 2
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.2)              # not wanted: not run
    assert ran.count("testcard") == 2


def test_a_node_that_is_no_effect_has_no_card(ctx):
    r, views = _renderer(ctx), _views(ctx)
    r.thumbs.want({"scene": graphview.CARD_PIC, "composite": graphview.CARD_PIC})
    r.draw_outputs(S, *SIZE, 1.0, views, t_now=2.0)
    assert r.thumbs.count == 0 and not r.thumbs.error


# ---------------------------------------------------------------- the page

def test_the_chip_switches_an_effects_thumbnail_and_no_other_nodes(rig):
    st = party(rig)
    view = st["view"]
    st["seen_rect"] = ((-1e9, -1e9), (1e9, 1e9))
    st["patch_only"] = False
    st["hide"] = ui_graph.hidden_ids(st, view)
    where = lambda nid: ((0.0, 0.0), (10.0, 10.0))
    # (the corpus patch leaves its effects with nothing in or out here, so
    # they are drawn only once revealed, as a node fresh from the picker is)
    st.setdefault("revealed", set()).update(n.id for n in view.nodes if ui_graph.has_card(n))
    drawn = [n for n in view.nodes if n.thumb is not None and ui_graph.drawn_node(st, n)
             and not ui_graph.by_preview(n)]
    effects = [n for n in drawn if ui_graph.has_card(n)]
    others = [n for n in drawn if not ui_graph.has_card(n)]
    assert effects and others
    assert all(graphview.kind_of(n.id.partition(":")[2]) in graphview.CARD_KINDS
               for n in effects)
    assert graphview.CARD_PIC not in ui_graph.thumb_wants(st, view, where).values()
    fx = effects[0]
    assert ui_graph.toggle_card(st, fx) is True and ui_graph.card_shown(st, fx)
    got = ui_graph.thumb_wants(st, view, where)
    assert got[ui_graph.thumb_name(fx)] == graphview.CARD_PIC
    assert [k for k, how in got.items() if how == graphview.CARD_PIC] == [ui_graph.thumb_name(fx)]
    assert "showing the test card" in ui_graph.thumb_tip(st, fx)
    # a scene, a channel, an output: no chip, and a toggle does nothing
    for n in others:
        assert ui_graph.toggle_card(st, n) is False and not ui_graph.card_shown(st, n)
    assert ui_graph.toggle_card(st, fx) is False                 # and back to its picture
    assert graphview.CARD_PIC not in ui_graph.thumb_wants(st, view, where).values()
    assert "showing the test card" not in ui_graph.thumb_tip(st, fx)


def test_the_chip_sits_in_the_thumbnails_top_right_corner():
    a, b = ui_graph.chip_rect((100.0, 50.0), width=200.0)
    assert b[0] == 300.0 - ui_graph.CHIP_IN and a[1] == 50.0 + ui_graph.CHIP_IN
    assert (b[0] - a[0], b[1] - a[1]) == (ui_graph.CHIP_W, ui_graph.CHIP_H)
    assert ui_graph.in_rect((a[0] + 1, a[1] + 1), (a, b))
    assert not ui_graph.in_rect((a[0] - 1, a[1] + 1), (a, b))
    assert not ui_graph.in_rect((b[0], b[1]), (a, b))
