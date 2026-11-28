"""Any number of backdrops.

`backdrop` is declared by a wire, as the frame's own; `backdrop.<n>` by its
entry (`{"kind": "backdrop", "instance": n}`), its alpha `backdrop.<n>.alpha`
(`params.declare_backdrops`, read as `Frame.backdrops`). A second backdrop
draws as the first does at the same alpha; the picker and the starter add the
next one; a patch's backdrop spawns into a host that has one as the next one.
"""

from __future__ import annotations

import numpy as np
import pytest
from test_graph_edit import wired_rig, wired_wires

from hyperspace import graph as G
from hyperspace import graphview, params, patches
from hyperspace.patches import Host, spawn
from hyperspace.view import BackdropState, ViewState


def _section(b: str, *extra: dict) -> dict:
    nodes = [] if b == "backdrop" else [{"kind": "backdrop", "instance": int(b.split(".")[1])}]
    return {"frame": "wired", "nodes": nodes, "wires": [
        {"from": "pattern", "to": "shape.faces"}, {"from": "shape", "to": "scene.geometry"},
        {"from": "scene", "to": f"{b}.scene"}, {"from": "pattern", "to": f"{b}.image"},
        {"from": b, "to": "output.all.image"}, *extra]}


# ---------------------------------------------------------------- the section

def test_a_second_backdrop_is_declared_by_its_entry():
    spec = G.read_graph(_section("backdrop.2"))
    assert spec.backdrops == (G.BackdropAt(2),) and spec.notes == ()
    assert G.BackdropAt(2).to_json() == {"kind": "backdrop", "instance": 2}
    assert G.BackdropAt(2).name == "backdrop.2" and G.backdrop_name(1) == "backdrop"
    assert G.wire_node_kind("backdrop.2", wired=True) == "backdrop"
    assert G.entry_declares("backdrop", 2) and not G.entry_declares("backdrop", 1)


def test_a_wire_to_an_undeclared_backdrop_is_refused_in_words():
    doc = _section("backdrop.2")
    doc["nodes"] = []
    spec = G.read_graph(doc)
    assert any('no backdrop.2 node in this graph (add one: {"kind": "backdrop", '
               '"instance": 2})' in n for n in spec.notes)


@pytest.mark.parametrize("n", [0, -1, True, "2"])
def test_a_backdrops_instance_is_a_whole_number_from_1(n):
    with pytest.raises(G.GraphError):
        G.read_graph({"frame": "wired", "nodes": [{"kind": "backdrop", "instance": n}]})


# ---------------------------------------------------------------- the draw

@pytest.mark.parametrize("alpha", [1.0, 0.4, 0.0])
def test_a_second_backdrop_draws_as_the_first_at_its_own_alpha(alpha):
    from hyperspace.render import render_offscreen
    one = render_offscreen(ViewState(faces=True, pattern=1, backdrop_alpha=alpha), 160, 100,
                           wiring=G.read_graph(_section("backdrop")).wiring())
    two = render_offscreen(ViewState(faces=True, pattern=1, backdrop_alpha=0.9,
                                     backdrops={"backdrop.2": BackdropState(alpha=alpha)}),
                           160, 100, wiring=G.read_graph(_section("backdrop.2")).wiring())
    assert np.array_equal(one, two)


def test_two_backdrops_build_side_by_side_each_its_own_composite():
    spec = G.read_graph({"frame": "wired", "nodes": [{"kind": "backdrop", "instance": 2}],
                         "wires": [
        {"from": "shape", "to": "scene.geometry"},
        {"from": "scene", "to": "backdrop.scene"}, {"from": "pattern", "to": "backdrop.image"},
        {"from": "scene", "to": "backdrop.2.scene"}, {"from": "channel.a", "to": "backdrop.2.image"},
        {"from": "backdrop", "to": "output.all.image"}, {"from": "backdrop.2", "to": "output.2.image"}]})
    assert spec.notes == ()
    from test_graph_masks import _views
    g = G.build_graph(_views(), spec.wiring())
    assert {"backdrop", "backdrop.2"} <= set(g.nodes)
    two = g.nodes["backdrop.2"]           # (a channel straight in: the first's path, its own node)
    assert isinstance(two, G.Composite) and two.under_alpha_of is None
    assert g.nodes["channel.a(backdrop.2)"].alpha_of == "backdrop.2"
    spec = G.read_graph(_section("backdrop.2"))       # (any other picture: the alpha on the lay)
    assert G.build_graph(_views(), spec.wiring()).nodes["backdrop.2"].under_alpha_of == "backdrop.2"


def test_the_alpha_resolver_reads_the_view_field_or_the_backdrops_state():
    class F:
        s = ViewState(backdrop_alpha=0.25, backdrops={"backdrop.3": BackdropState(alpha=2.0)})

        @property
        def backdrops(self):
            return self.s.backdrops
    assert G.alpha_of(F(), "backdrop_alpha") == 0.25
    assert G.alpha_of(F(), "backdrop.3") == 1.0            # (held to 0…1)
    assert G.alpha_of(F(), "backdrop.4") == 1.0            # (none declared: opaque)


# ---------------------------------------------------------------- the params

def test_declare_backdrops_comes_and_goes_and_keeps_the_first():
    from types import SimpleNamespace as NS

    from hyperspace.analysis import Analyser
    from hyperspace.analyzer import Analyzer
    from hyperspace.control import Control
    chain = Analyzer(Analyser())
    view = ViewState()
    reg = params.build_registry(view, Control(chain), NS(chain=chain))
    assert "backdrop.alpha" in reg and reg.backdrop_state is view.backdrops
    got = params.declare_backdrops(reg, ["backdrop", "backdrop.2", "backdrop.3"])
    assert sorted(got) == ["backdrop.2.alpha", "backdrop.3.alpha"]
    assert reg["backdrop.2.alpha"].group == "backdrop" and "backdrop" in params.PATCH_GROUPS
    reg["backdrop.2.alpha"].set(0.3)
    assert view.backdrops["backdrop.2"].alpha == 0.3
    assert params.declare_backdrops(reg, ["backdrop", "backdrop.2"]) == ["backdrop.3.alpha"]
    assert "backdrop.alpha" in reg and "backdrop.3" not in view.backdrops
    assert params.declare_backdrops(reg, ["backdrop.2"]) == []           # (nothing moved)
    assert params.is_backdrop_id("backdrop.2.alpha") and params.is_backdrop_id("backdrop.12.alpha")
    assert not params.is_backdrop_id("backdrop.alpha") and not params.is_backdrop_id("backdrop.1.alpha")


def test_a_backdrops_alpha_is_on_its_node():
    rule = graphview.OWNERS["backdrop"]
    assert rule("backdrop.alpha", None) == "backdrop"
    assert rule("backdrop.2.alpha", None) == "backdrop.2"


# ---------------------------------------------------------------- GRAPH

def test_the_picker_adds_the_next_backdrop_and_its_alpha_lands(tmp_path):
    rig, e, _ = wired_rig(tmp_path, {"frame": "wired", "nodes": [{"kind": "backdrop"}]})
    assert "backdrop" not in graphview.picked(e)
    assert e.add_node("backdrop") is None and e.added == "backdrop.2"
    assert "backdrop.2.alpha" in rig.reg
    assert e.add_node("backdrop") is None and e.added == "backdrop.3"
    assert e.drop_node("render:backdrop.2") is None
    spec = rig.loaded_patch.graph.spec
    assert [b.name for b in spec.backdrops] == ["backdrop", "backdrop.3"]
    assert "backdrop.2.alpha" not in rig.reg and "backdrop.3.alpha" in rig.reg


def test_a_deleted_second_backdrop_joins_its_scene_on(tmp_path):
    rig, e, _ = wired_rig(tmp_path, _section("backdrop.2"))
    assert e.drop_node("render:backdrop.2") is None
    assert ("scene", "output.all.image") in wired_wires(rig)


# ---------------------------------------------------------------- patches

def test_a_patchs_backdrop_spawns_as_the_next_one():
    doc = {"schema": patches.SCHEMA, "name": "under", "nodes": [{"kind": "backdrop"}],
           "values": {"backdrop.alpha": 0.3}}
    assert patches.check(doc) == []
    landing = spawn(doc, Host(names=frozenset({"backdrop"})))
    assert landing.taken == () and landing.refusal is None
    assert landing.renames["backdrop"] == "backdrop.2"
    assert {"kind": "backdrop", "instance": 2} in [dict(n) for n in landing.nodes]
    assert landing.values == {"backdrop.2.alpha": 0.3}
    assert "backdrop" not in patches.ONE_PER_FRAME


def test_a_second_backdrop_goes_onto_a_cable_from_the_cable_menu(tmp_path):
    rig, e, _ = wired_rig(tmp_path, _section("backdrop"))
    assert e.insert_node(("backdrop", "output.all.image"), "backdrop") is None
    got = wired_wires(rig)
    assert ("backdrop", "backdrop.2.scene") in got and ("backdrop.2", "output.all.image") in got
    assert rig.loaded_patch.graph.spec.backdrops == (G.BackdropAt(2),)   # (the first by its wires)


# ---------------------------------------------------------------- a keyed channel under it

@pytest.mark.parametrize("b", ["backdrop", "backdrop.2"])
def test_every_backdrop_reads_a_keyed_channel_as_the_first_does(b):
    """A channel straight into a later backdrop takes the
    first's path — its own channel node, keyed and keeping its alpha, the
    backdrop adding the scene's coverage over its holes."""
    from test_black_is_clear import _built
    nodes = [{"kind": "backdrop"} if b == "backdrop" else {"kind": "backdrop", "instance": 2}]
    wires = (("shape", "scene.geometry"), ("scene", f"{b}.scene"),
             ("channel.a", f"{b}.image"), (b, "output.all.image"))
    g = _built(["channel.a"], wires, nodes)
    (media,) = [n for n in g.order if isinstance(n, G.MediaNode)]
    assert media.alpha_of == ("backdrop_alpha" if b == "backdrop" else b)
    assert media.keyed == "channel.a" and media.keeps_alpha
    (back,) = [n for n in g.order if isinstance(n, G.Composite)]
    assert back.name == b and back.keeps_alpha and back.under_alpha_of is None


@pytest.mark.parametrize("keyed", [True, False])
def test_a_keyed_channel_under_a_later_backdrop_draws_as_under_the_first(ctx, keyed):
    """A keyed black-and-white channel under each backdrop,
    the backdrop laid over solid blue — the black holes show the blue under a
    later backdrop as under the first."""
    from test_black_is_clear import Still, _media, _renderer, _section
    from test_media_render import _draw, _rgba

    from hyperspace import view
    from hyperspace.graphmigrate import wired_wiring
    pics = []
    for b in ("backdrop", "backdrop.2"):
        m = _media(a=Still(_rgba(16, 9, (0, 0, 0), (255, 255, 255))),
                   c=Still(_rgba(16, 9, (0, 0, 255))))
        for c in "ac":
            m.channels[c].fit = 2
        r = _renderer(ctx, m)
        nodes = [{"kind": "composite"},
                 {"kind": "backdrop"} if b == "backdrop" else {"kind": "backdrop", "instance": 2}]
        wires = (("channel.a", f"{b}.image"), (b, "composite.over"),
                 ("channel.c", "composite.under"), ("composite", "output.all.image"))
        doc = _section(["channel.a"] if keyed else None, wires, nodes)
        r.wiring = wired_wiring(G.read_graph(doc).wiring())
        s = view.ViewState(lines=False, points=False, faces=False,
                           backdrops={"backdrop.2": BackdropState()})
        (pic,) = _draw(ctx, r, s, size=(96, 64), frames=2)
        pics.append(pic)
    assert np.array_equal(pics[0], pics[1])
    blue = (pics[1][..., 2] > 200) & (pics[1][..., 0] < 60)
    assert bool(blue.mean() > 0.3) is keyed, blue.mean()   # (unkeyed: the black covers)


def test_node_mode_lists_only_its_own_backdrops_params():
    """The first backdrop's params never take a later
    backdrop's (`param_ids`, node mode's rows), its key's neither — nor any
    numbered kind's first its later instances' (`fx.acid` / `fx.acid.2`)."""
    from hyperspace.params import Registry, declare_keys
    reg = Registry()
    for pid in ("backdrop.alpha", "backdrop.2.alpha", "fx.acid.mix", "fx.acid.2.mix",
                "matte.key", "matte.2.key"):
        reg.continuous(pid, pid, lambda: 0.0, lambda v: None, lo=0.0, hi=1.0, group="t")
    declare_keys(reg, ["backdrop", "backdrop.2"])
    one = graphview.param_ids(reg, "render:backdrop")
    two = graphview.param_ids(reg, "render:backdrop.2")
    assert "backdrop.alpha" in one and not [p for p in one if p.startswith(("backdrop.2", "key.backdrop.2"))]
    assert "backdrop.2.alpha" in two and any(p.startswith("key.backdrop.2.") for p in two)
    assert "backdrop.alpha" not in two
    assert graphview.param_ids(reg, "render:acid") == ["fx.acid.mix"]
    assert graphview.param_ids(reg, "render:matte") == ["matte.key"]


def test_two_backdrops_on_one_channel_keep_their_own_alphas(ctx):
    """One channel under two backdrops at different partial
    alphas, laid one over the other — each keeps its own fit (a target per
    backdrop, `Renderer._media_fit`'s `scope`), so the frame is the one with
    the second backdrop reading an identical copy of the channel instead."""
    from test_black_is_clear import Still, _media, _renderer, _section
    from test_media_render import Switches, View, _draw, _fbo, _rgba

    from hyperspace import view
    from hyperspace.graphmigrate import wired_wiring
    pics = []
    for second in ("channel.a", "channel.b"):
        m = _media(a=Still(_rgba(16, 9, (255, 255, 255))), b=Still(_rgba(16, 9, (255, 255, 255))))
        for c in "ab":
            m.channels[c].fit = 2
        r = _renderer(ctx, m)
        nodes = [{"kind": "composite"}, {"kind": "backdrop"}, {"kind": "backdrop", "instance": 2}]
        # (the order: backdrop.2 alone on All outputs, fitted first; then
        # output 2 fits the first backdrop and repaints backdrop.2 over it)
        wires = (("channel.a", "backdrop.image"), (second, "backdrop.2.image"),
                 ("backdrop.2", "output.all.image"),
                 ("backdrop", "composite.under"), ("backdrop.2", "composite.over"),
                 ("composite", "output.2.image"))
        r.wiring = wired_wiring(G.read_graph(_section(None, wires, nodes)).wiring())
        s = view.ViewState(lines=False, points=False, faces=False, backdrop_alpha=0.75,
                           backdrops={"backdrop.2": BackdropState(alpha=0.25)})
        vs = [View(Switches(), (96, 64), target=_fbo(ctx, 96, 64)) for _ in range(2)]
        pics.append(_draw(ctx, r, s, size=(96, 64), views=vs, frames=2))
    for one, two in zip(*pics, strict=True):
        assert np.array_equal(one, two)
    # backdrop.2 at its own 0.25 on output 2 (it lies opaque over its ground):
    # white × 0.25, never the first's 0.75 (191, the shared fit, before the fix)
    assert abs(int(pics[0][1][..., 0].mean()) - 64) <= 1

