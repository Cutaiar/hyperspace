"""Plan 87 — black is clear on any picture node: the graph section's `keys`
(`GraphSpec.keys`, `Wiring.keys`), each keyed node built through a `KeyNode`
(`masks.KEY_FS`) — a channel keyed in its own fit pass (`media_tex.FIT_FS`) —
its knobs `key.<node>.*` declared while it is keyed (`params.declare_keys`);
GRAPH's node menu and the MEDIA page switch it (`graphview.render_key`); and
`screen` on the composite (`graph.BLENDS`, `Renderer.lay`).

The GL half draws through the real passes on a standalone context (skips
without one) and holds them to a numpy oracle; the channel's off pass to the
bytes of the pass from before the plan."""

from __future__ import annotations

import json

import numpy as np
import pytest
from test_media_render import Still, _media

from hyperspace import glsl, graphview, masks, media_tex, view
from hyperspace import graph as G
from hyperspace.params import KEY_GROUP, Kind, Registry, declare_keys, is_key_id, key_ids

KNOBS = ("level", "soft", "measure", "feather", "keep", "invert", "ramp")

# the fit pass as it was before plan 87, word for word: a channel nothing
# keys must be its bytes (every saved look, every golden)
FIT_BEFORE = """
#version 330
in vec2 v_uv;
uniform sampler2D u_src;
uniform vec2 u_scale;      // frame uv → picture uv, about the centre (fit_scale)
uniform int u_flip;        // the texture's first row is the picture's top (an upload)
uniform float u_alpha;
out vec4 f_color;
void main() {
    vec2 uv = 0.5 + (v_uv - 0.5) * u_scale;
    if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) {
        f_color = vec4(0.0);
        return;
    }
    if (u_flip != 0) uv.y = 1.0 - uv.y;
    vec4 c = texture(u_src, uv);
    f_color = vec4(c.rgb * c.a, c.a) * u_alpha;
}
"""


def _section(keys=None, wires=(("scene", "output.all.image"),), nodes=()):
    d = {"frame": "wired", "nodes": list(nodes),
         "wires": [{"from": a, "to": b} for a, b in wires]}
    if keys is not None:
        d["keys"] = keys
    return d


# ---------------------------------------------------------------- no GL

def test_every_key_pass_shares_one_ramp():
    assert glsl.KEY_RAMP in media_tex.FIT_FS and glsl.KEY_RAMP in masks.KEY_FS
    assert view.KEY_MEASURES == ("peak", "luma")


def test_the_section_says_which_nodes_are_keyed():
    """`keys` read sorted and once, written last and only when there are any
    (a section with none is the bytes it was), carried into the wiring."""
    plain = G.read_graph(_section())
    assert plain.keys == () and "keys" not in plain.to_json()
    spec = G.read_graph(_section(["scene", "channel.a", "scene"]))
    assert spec.keys == ("channel.a", "scene") and spec.notes == ()
    assert list(spec.to_json()) == ["frame", "nodes", "wires", "keys"]
    assert spec.to_json()["keys"] == ["channel.a", "scene"]
    assert G.read_graph(spec.to_json()) == spec
    assert spec.wiring().keys == ("channel.a", "scene")
    with pytest.raises(G.GraphError, match="keys is not a list"):
        G.read_graph(_section("scene"))
    old = G.read_graph({"nodes": [], "keys": ["scene"]})       # an unwired section keys nothing
    assert old.keys == () and old.notes


def test_the_knobs_are_declared_while_a_node_is_keyed():
    r = Registry()
    got = declare_keys(r, ["scene", "acid.2"])
    assert set(got) == set(key_ids("scene")) | set(key_ids("acid.2"))
    assert key_ids("scene") == [f"key.scene.{k}" for k in KNOBS]
    level, soft, measure, feather, keep, invert, ramp = (r[i] for i in key_ids("scene"))
    assert ramp.choices == ["smooth", "linear"] and ramp.value == 0     # (plan 90 H1)
    assert all(p.group == KEY_GROUP and p.persist and p.modulatable
               for p in (level, soft, measure, feather, keep, invert))
    assert (level.value, soft.value, feather.value) == (0.02, 0.1, 0.0)
    assert measure.choices == ["peak", "luma"] and measure.value == 0
    assert keep.kind is Kind.TOGGLE and keep.value is True and invert.value is False
    level.set(0.3)
    assert r.key_state["scene"].level == 0.3
    declare_keys(r, ["scene"])                            # acid.2 no longer keyed: gone
    assert not any(i in r for i in key_ids("acid.2")) and "acid.2" not in r.key_state
    assert r["key.scene.level"].value == 0.3             # the one kept keeps its value
    assert is_key_id("key.channel.a.soft") and is_key_id("key.hands.2.layer.invert")
    assert not is_key_id("media.a.key") and not is_key_id("key.scene.colour")


def test_which_nodes_can_be_keyed():
    for name in ("scene", "channel.a", "acid.2", "composite", "switch", "delay", "dream",
                 "cut", "lookback", "pattern", "backdrop", "resize", "hands.layer"):
        assert graphview.keyable(name), name
    for name in ("shape", "hands", "matte", "output.1", G.ALL_OUTPUTS, "", None):
        assert not graphview.keyable(name), name


def test_screen_is_appended_to_the_blends():
    """Appended, never inserted; a composite saves it and reads it back."""
    assert G.BLENDS == ("over", "add", "depth", "screen")
    c = G.CompositeAt(2, "screen")
    assert c.to_json() == {"kind": "composite", "instance": 2, "blend": "screen"}
    assert G.NODE_KINDS["composite"](c.to_json()) == c
    assert G.blend_words("screen") == "screened" and G.blend_words("add") == "added"
    assert G.blend_words("depth") == "depth-aware" and G.blend_words("over") == ""


# ---------------------------------------------------------------- the build

def _built(keys, wires, nodes=(), effects=()):
    from hyperspace.outputs import Switches, View
    spec = G.read_graph(_section(keys, wires, nodes))
    return G.build_graph([View(Switches(), (64, 48))], spec.wiring(), effects=effects)


def test_a_keyed_node_is_read_through_its_key_by_every_consumer():
    """The scene keyed: one `KeyNode` after it, and what read the scene reads
    the key; nothing keyed builds no `KeyNode` at all (the graph as it was)."""
    wires = (("shape", "scene.geometry"), ("scene", "composite.under"),
             ("channel.a", "composite.over"), ("composite", "output.all.image"))
    plain = _built(None, wires, [{"kind": "composite"}])
    assert not any(isinstance(n, G.KeyNode) for n in plain.order)
    g = _built(["scene"], wires, [{"kind": "composite"}])
    keys = [n for n in g.order if isinstance(n, G.KeyNode)]
    assert [k.name for k in keys] == ["scene(key)"] and keys[0].of == "scene"
    assert isinstance(keys[0].inputs["image"], G.Scene)
    comp = next(n for n in g.order if isinstance(n, G.Composite) and n.name == "composite")
    assert comp.inputs["under"] is keys[0]


def test_a_keyed_channel_is_keyed_in_its_own_fit_pass():
    wires = (("channel.a", "output.all.image"),)
    g = _built(["channel.a"], wires)
    media = [n for n in g.order if isinstance(n, G.MediaNode)]
    assert [m.keyed for m in media] == ["channel.a"]
    assert not any(isinstance(n, G.KeyNode) for n in g.order)
    assert [m.keyed for m in _built(None, wires).order if isinstance(m, G.MediaNode)] == [None]


def test_a_channel_straight_into_the_backdrop_is_keyed_too():
    """Review of #479: the backdrop's own channel node (made apart from the
    channel's, the backdrop's fader in its fit pass) is keyed when the
    channel is, and keeps its alpha over the ground."""
    wires = (("shape", "scene.geometry"), ("scene", "backdrop.scene"),
             ("channel.a", "backdrop.image"), ("backdrop", "output.all.image"))
    g = _built(["channel.a"], wires, [{"kind": "backdrop"}])
    (media,) = [n for n in g.order if isinstance(n, G.MediaNode)]
    assert media.alpha_of == "backdrop_alpha" and media.keyed == "channel.a"
    assert media.keeps_alpha
    (plain,) = [n for n in _built(None, wires, [{"kind": "backdrop"}]).order
                if isinstance(n, G.MediaNode)]
    assert plain.keyed is None and not plain.keeps_alpha


def test_a_keyed_effect_keeps_its_aux():
    """Review of #479: Blend keyed still reads its aux picture."""
    wires = (("scene", "blend.image"), ("channel.a", "blend.aux"),
             ("blend", "output.all.image"))
    nodes = [{"kind": "effect", "file": "blend"}]
    for keys in (None, ["blend"]):
        g = _built(keys, wires, nodes, effects=("blend",))
        (blend,) = [n for n in g.order if isinstance(n, G.Effect)]
        assert isinstance(blend.inputs[G.AUX], G.MediaNode), keys


def test_a_keyed_chain_still_mutes_its_hands():
    """Review of #479: a hands layer laid over the scene by a composite into
    one output, the composite (then the layer) keyed — the output's hands
    mute still reaches the composite, as unkeyed."""
    from hyperspace.outputs import Switches, View
    wires = (("hands", "hands.layer.hands"), ("shape", "scene.geometry"),
             ("scene", "composite.under"), ("hands.layer", "composite.over"),
             ("composite", "output.1.image"))
    nodes = [{"kind": "composite"}, {"kind": "layer"}]
    for keys in (None, ["composite"], ["hands.layer"], ["composite", "hands.layer"]):
        spec = G.read_graph(_section(keys, wires, nodes))
        g = G.build_graph([View(Switches(), (64, 48))], spec.wiring())
        (comp,) = [n for n in g.order if isinstance(n, G.Composite)]
        assert comp.mute_hands == (0,), keys


def test_a_keyed_node_saved_as_a_patch_spawns_keyed():
    """Review of #479: save as patch carries a keyed member and its knobs,
    renamed, and a spawn lands them keyed in the host."""
    from hyperspace.patches import Host, read, spawn
    from hyperspace.routing import Bindings
    doc = _section(["composite.2"], (("scene", "composite.2.under"),
                                     ("composite.2", "output.all.image")),
                   [{"kind": "composite", "instance": 2}])
    spec = G.read_graph(doc)
    values = {"key.composite.2.level": 0.25, "key.composite.2.keep": False, "view.bright": 1}
    got, refused = patches_lift(spec, Bindings([]), values, {}, ["render:composite.2"])
    assert refused == [] and got["keys"] == ["composite"]
    assert got["values"] == {"key.composite.keep": False, "key.composite.level": 0.25}
    assert read(got).keys == ("composite",)
    landing = spawn(got, Host(names=frozenset({"composite", "scene"})))
    assert landing.keys == ("composite.2",)
    assert landing.values == {"key.composite.2.keep": False, "key.composite.2.level": 0.25}
    plain, _ = patches_lift(G.read_graph(_section(None, (("scene", "composite.2.under"),),
                                                  [{"kind": "composite", "instance": 2}])),
                            Bindings([]), {}, {}, ["render:composite.2"])
    assert "keys" not in plain and read(plain).keys == ()


def patches_lift(*a):
    from hyperspace import patches
    return patches.lift(*a)


def test_the_selection_shows_a_keyed_nodes_knobs(tmp_path):
    """Review of #479: a keyed scene's and a keyed effect's knobs are on
    their own canvas nodes (`graphview.OWNERS`), and no node of their own
    appears for them."""
    from test_ui_shell import build_rig, frame

    from hyperspace import ui_graph

    with build_rig(tmp_path) as r:
        panel = r.panel
        panel.library.loaded_patch.new((0.0, 0.0))
        e = ui_graph.render_edit(panel)
        assert e.insert_effect(("scene", "output.all.image"), "fade") is None
        assert e.set_key("scene", True) is None and e.set_key("fade", True) is None
        for _ in range(2):
            frame(panel, "graph")
        view = ui_graph._state(panel)["view"]
        for node in ("scene", "fade"):
            ports = {p.param for p in view.node(f"render:{node}").ports if p.param}
            assert set(key_ids(node)) <= ports, node
        assert not any(n.id == "group:key" for n in view.nodes)


def test_a_keyed_picture_through_a_switch_keeps_its_alpha():
    """Review of #479 (second pass): a keyed channel picked by a switch into
    Fade laid over another picture keeps its alpha (a switch paints its pick
    straight in); not laid over, it paints as ever."""
    nodes = [{"kind": "switch"}, {"kind": "composite"}, {"kind": "effect", "file": "fade"}]
    over = (("channel.a", "switch.in1"), ("switch", "fade.image"), ("fade", "composite.over"),
            ("channel.b", "composite.under"), ("composite", "output.all.image"))
    g = _built(["channel.a"], over, nodes, effects=("fade",))
    (a,) = [n for n in g.order if isinstance(n, G.MediaNode) and n.channel == "a"]
    assert a.keyed == "channel.a" and a.keeps_alpha
    straight = (("channel.a", "switch.in1"), ("switch", "output.all.image"))
    g = _built(["channel.a"], straight, [{"kind": "switch"}])
    (a,) = [n for n in g.order if isinstance(n, G.MediaNode)]
    assert a.keyed == "channel.a" and not a.keeps_alpha


def test_a_keyed_backdrop_lays_its_scene_with_coverage():
    """Review of #479 (second pass): the backdrop over a keyed channel lays
    its scene adding the scene's coverage over the channel's clear holes;
    an unkeyed backdrop lays it as it always did."""
    wires = (("shape", "scene.geometry"), ("scene", "backdrop.scene"),
             ("channel.a", "backdrop.image"), ("backdrop", "output.all.image"))
    for keys, want in ((["channel.a"], True), (None, False)):
        g = _built(keys, wires, [{"kind": "backdrop"}])
        (back,) = [n for n in g.order if isinstance(n, G.Composite)]
        assert back.keeps_alpha is want, keys


def test_an_effects_key_toggles_are_checkboxes(monkeypatch):
    """Review of #479 (second pass): under an effect's strip, keep colour and
    invert are drawn as checkboxes (`ui_graph._param_row`), never sliders —
    a slider's write refuses a toggle."""
    from types import SimpleNamespace

    from hyperspace import ui, ui_graph
    from hyperspace.params import Registry
    reg = Registry()
    declare_keys(reg, ["fade"])
    drawn: list[tuple[str, str]] = []
    panel = SimpleNamespace(
        reg=reg, _real=lambda p: p,
        _row=lambda pid, **k: drawn.append(("row", pid)),
        _check=lambda pid, **k: drawn.append(("check", pid)),
        _label_cell=lambda *a, **k: None, _ctx_label=lambda *a, **k: None)
    monkeypatch.setattr(ui_graph.imgui, "separator", lambda: None)
    monkeypatch.setattr(ui, "_micro", lambda *a, **k: None)
    ports = [SimpleNamespace(id=f"pin:{pid}", param=pid) for pid in key_ids("fade")]
    ports.append(SimpleNamespace(id="pin:fx.fade.level", param=None))     # not a key knob
    ui_graph._key_rows(panel, SimpleNamespace(ports=ports))
    kinds = {pid: how for how, pid in drawn}
    assert kinds["key.fade.keep"] == kinds["key.fade.invert"] == "check"
    assert kinds["key.fade.level"] == kinds["key.fade.measure"] == "row"


def test_the_keyed_walk_through_switches_asks_each_switch_once(monkeypatch):
    """Review of #479 (third pass): a keyed channel into seven stages of
    eight-input switches, each stage feeding every input of the next — the
    walk asks each switch once (a path search asked the last 8⁶ times)."""
    nodes, wires = [], []
    src = "channel.a"
    for k in range(1, 8):
        sw = "switch" if k == 1 else f"switch.{k}"
        nodes.append({"kind": "switch"} if k == 1 else {"kind": "switch", "instance": k})
        wires += [(src, f"{sw}.in{i}") for i in range(1, 9)]
        src = sw
    wires.append((src, "output.all.image"))
    asked: dict[str, int] = {}
    real = G._Build.laid_over

    def counted(self, name, seen=frozenset()):
        if not seen:
            asked[name] = asked.get(name, 0) + 1
        return real(self, name, seen)

    monkeypatch.setattr(G._Build, "laid_over", counted)
    g = _built(["channel.a"], tuple(wires), nodes)
    (a,) = [n for n in g.order if isinstance(n, G.MediaNode)]
    assert a.keyed == "channel.a" and not a.keeps_alpha
    assert max(asked.values()) <= 2 and len(asked) <= 10, asked


def test_an_opaque_pick_over_a_keyed_under_covers_its_holes(ctx):
    """Review of #479 (third pass): keyed channel A under a composite and on a
    switch into its over, the switch picking solid red B; that composite over
    solid blue C. Red covers A's clear holes (the over adds its coverage),
    so no blue bleeds through: red, never magenta."""
    from test_media_render import _draw, _rgba

    from hyperspace.graphmigrate import wired_wiring
    half = _rgba(16, 9, (0, 0, 0), (255, 255, 255))           # black top, white bottom
    m = _media(a=Still(half), b=Still(_rgba(16, 9, (255, 0, 0))),
               c=Still(_rgba(16, 9, (0, 0, 255))))
    for c in "abc":
        m.channels[c].fit = 2
    r = _renderer(ctx, m)
    nodes = [{"kind": "composite"}, {"kind": "composite", "instance": 2}, {"kind": "switch"}]
    wires = (("channel.a", "composite.under"), ("channel.a", "switch.in1"),
             ("channel.b", "switch.in2"), ("switch", "composite.over"),
             ("composite", "composite.2.over"), ("channel.c", "composite.2.under"),
             ("composite.2", "output.all.image"))
    r.wiring = wired_wiring(G.read_graph(_section(["channel.a"], wires, nodes)).wiring())
    s = view.ViewState(lines=False, points=False, faces=False, switch={"switch": 2})
    (pic,) = _draw(ctx, r, s, size=(96, 64), frames=2)
    red = (pic[..., 0] > 200) & (pic[..., 1] < 60) & (pic[..., 2] < 60)
    assert red.mean() > 0.95, red.mean()


# ---------------------------------------------------------------- the patch

@pytest.fixture()
def edit_rig(tmp_path):
    from test_graph_wires import _edit_rig
    from test_loadable import put

    from hyperspace.library import LOADABLE
    rig, stub, edit, pushed = _edit_rig(tmp_path)
    put(rig.home, "Plain", graph=_section(None, (("shape", "scene.geometry"),
                                                ("scene", "output.all.image"))))
    rig.lib.load(LOADABLE, "Plain")
    return rig, stub, edit, pushed


def test_the_node_menu_keys_a_node_in_one_undo_step(edit_rig):
    """`set_key` puts the node in the section's keys and its knobs appear;
    the knobs save with the patch, and a load of the save lands them; off
    again, they go. A node that makes no picture is refused in words."""
    from test_media_loadable import save_text
    rig, stub, edit, pushed = edit_rig
    assert edit.set_key("scene", True) is None
    assert rig.loaded_patch.graph.spec.keys == ("scene",) and len(pushed) == 1
    assert stub.wiring.keys == ("scene",)
    assert all(i in rig.reg for i in key_ids("scene"))
    assert graphview.keyed(edit, "scene") and "black is clear" in edit.said
    rig.reg["key.scene.level"].set(0.25)
    doc = json.loads(save_text(rig, "keyed"))
    assert doc["graph"]["keys"] == ["scene"] and doc["values"]["key.scene.level"] == 0.25
    assert edit.set_key("scene", False) is None
    assert "keys" not in rig.loaded_patch.document("x")["graph"]
    assert not any(i in rig.reg for i in key_ids("scene"))
    assert rig.loaded_patch.load_doc(doc) == [] and rig.loaded_patch.notes == []
    assert rig.reg["key.scene.level"].value == 0.25
    assert edit.set_key("shape", True) == graphview.KEY_NO_PICTURE.format(name="shape")


def test_a_patch_from_before_keys_nothing_and_saves_the_same(edit_rig):
    """No `keys`, no key knob, no note; the save writes no `keys` and no
    `key.*` value — the file a build before this one wrote."""
    from test_media_loadable import save_text
    rig, *_ = edit_rig
    doc = json.loads(save_text(rig, "plain"))
    assert "keys" not in doc["graph"] and not any(is_key_id(k) for k in doc["values"])
    assert not any(p.group == KEY_GROUP for p in rig.reg)


# ---------------------------------------------------------------- the panel

def test_the_node_menu_has_black_is_clear_on_a_picture_node(tmp_path):
    """GRAPH's node menu (`ui_graph.render_node_menu`): **black is clear** on
    a picture node, unchecked; picked, the node is keyed (one undo step) and
    the row is checked; absent on a geometry."""
    from test_ui_shell import build_rig, frame

    from hyperspace import ui_graph, ui_menu

    with build_rig(tmp_path) as r:
        panel = r.panel
        panel.library.loaded_patch.new((0.0, 0.0))
        frame(panel, "graph")
        view = ui_graph._state(panel)["view"]

        def rows(node):
            m = ui_menu.Menu("t.menu")
            ui_graph.render_node_menu(panel, view.node(node), m)
            return m, {row.label: row for row in m.walk() if row.kind == ui_menu.ITEM}

        m, items = rows("render:scene")
        row = items[ui_graph.KEY_ITEM]
        assert row.checked is False
        assert m.pick(row.id)
        assert panel.library.loaded_patch.graph.spec.keys == ("scene",)
        assert "key.scene.level" in r.reg
        frame(panel, "graph")
        view = ui_graph._state(panel)["view"]
        _, items = rows("render:scene")
        assert items[ui_graph.KEY_ITEM].checked is True
        _, items = rows("render:shape")
        assert ui_graph.KEY_ITEM not in items


@pytest.mark.parametrize("layout", ["band", "min", "default"])
def test_black_is_clear_on_the_media_page_by_the_mouse(tmp_path, monkeypatch, layout):
    """MEDIA, channel A, driven by control id (tests/ui_driver.py): the switch
    is drawn and the knobs are not; a click keys `channel.a` in the graph (the
    same edit as GRAPH's menu) and its knobs appear, none past the pane's
    right edge at any width; a typed level lands; a second click un-keys it."""
    from test_ui_pane import _focus_rig, _spills, _st
    from test_ui_shell import build_rig

    from hyperspace.ui import PAGE_KEYS

    knobs = [i for i in key_ids("channel.a") if not i.endswith((".keep", ".invert"))]
    with build_rig(tmp_path) as r:
        d = _focus_rig(r, monkeypatch, layout)
        r.reg["ui.page"].set(PAGE_KEYS.index("media"))
        d.run(d.wait(4))
        assert "media.a.key" in d.rects and not any(k in d.rects for k in knobs)
        d.run(d.click("media.a.key"), d.park(), d.wait(2))
        assert r.panel.library.loaded_patch.graph.spec.keys == ("channel.a",)
        assert all(k in d.rects for k in knobs), sorted(k for k in knobs if k not in d.rects)
        assert not _spills(d, _st(r)), sorted(_spills(d, _st(r)))
        d.run(d.enter("key.channel.a.level", 0.1))
        assert r.reg["key.channel.a.level"].value == pytest.approx(0.1)
        d.run(d.click("media.a.key"), d.park(), d.wait(2))
        assert r.panel.library.loaded_patch.graph.spec.keys == ()
        assert not any(k in d.rects for k in knobs)


# ---------------------------------------------------------------- GL

moderngl = pytest.importorskip("moderngl")

W, H = 16, 8


def _still() -> np.ndarray:
    """A W×H still, top row first: a grey ramp across the top half (0 to
    255), a colour per column below it (pure blue, red, dark green …), and
    a PNG's own alpha falling across the bottom rows."""
    px = np.zeros((H, W, 4), np.uint8)
    px[..., 3] = 255
    ramp = np.array([0, 1, 3, 5, 8, 13, 20, 26, 31, 40, 64, 96, 128, 180, 230, 255], np.uint8)
    px[: H // 2, :, :3] = ramp[None, :, None]
    cols = np.array([(0, 0, 255), (255, 0, 0), (0, 20, 0), (10, 10, 40), (200, 180, 20),
                     (3, 2, 1), (0, 0, 0), (60, 0, 60)] * 2, np.uint8)
    px[H // 2:, :, :3] = cols[None, :, :]
    px[-2:, :, 3] = np.linspace(0, 255, W).astype(np.uint8)[None, :]
    return px


def _oracle(px: np.ndarray, *, measure=0, level=0.02, soft=0.1, keep=True, invert=False,
            alpha=1.0, premultiplied=False) -> np.ndarray:
    """What a key pass makes of `px`, as floats 0–255 (rows as given):
    straight in (a channel's texture) or premultiplied in (a picture node's)."""
    c = px.astype(np.float64) / 255.0
    a = c[..., 3:]
    rgb = (np.where(a > 0, c[..., :3] / np.maximum(a, 1e-9), 0.0).clip(0, 1)
           if premultiplied else c[..., :3])
    m = (rgb @ np.array([0.2126, 0.7152, 0.0722]) if measure == 1 else rgb.max(-1))[..., None]
    if soft > 0:
        t = np.clip((m - level) / soft, 0.0, 1.0)
        k = t * t * (3 - 2 * t)
    else:
        k = (m > level).astype(np.float64)
    if invert:
        k = 1.0 - k
    cover = a * k
    out_rgb = rgb * (a if keep and not invert else cover)
    return np.concatenate([out_rgb, cover], -1) * alpha * 255.0


def _renderer(ctx, media):
    from test_media_render import _renderer as make
    return make(ctx, media, wires=[G.Wire("media.a", "output.1.image")])


def _fit(r, size=(W, H), alpha=1.0, key=None) -> np.ndarray:
    """Channel a fitted (stretch) at `size`, read back rows top first, as ints."""
    r._media_frame_now().clear()
    tex = r._media_fit("a", size, alpha, key=key)
    assert r.ctx.error == "GL_NO_ERROR"
    raw = np.frombuffer(tex.read(), np.uint8).reshape(size[1], size[0], 4)
    return raw[::-1].astype(int)


CASES = [
    {},                                                   # the ask's defaults
    {"measure": 1},                                       # luma: pure blue goes
    {"level": 0.2, "soft": 0.0},                          # a hard edge
    {"level": 0.0, "soft": 1.0},                          # the widest ramp
    {"keep": False},                                      # colour goes with alpha
    {"invert": True},                                     # white is clear
    {"invert": True, "keep": False},
]


@pytest.mark.parametrize("kw", CASES)
def test_a_keyed_channel_matches_its_oracle(ctx, kw):
    """Through the real fit pass, within a step of 8-bit rounding — pure
    black always clear, the source's own alpha kept under the key."""
    m = _media(a=Still(_still()))
    m.channels["a"].fit = 2                               # stretch: 1:1 at W×H
    r = _renderer(ctx, m)
    got = _fit(r, key=media_tex.Key(**kw))
    assert np.abs(got - _oracle(_still(), **kw)).max() <= 1.5
    if not kw.get("invert"):
        assert (got[: H // 2, 0] == 0).all()
    half = _fit(r, alpha=0.5, key=media_tex.Key(**kw))      # the backdrop's fader on top
    assert np.abs(half - _oracle(_still(), alpha=0.5, **kw)).max() <= 1.5


def test_a_channel_nothing_keys_is_the_pass_from_before_byte_for_byte(ctx):
    """No key (every patch before plan 87): exactly what the pass before
    wrote, on a random still with its own alpha, at an opacity, in each fit."""
    from hyperspace.glsl import QUAD_VS
    from hyperspace.media_tex import fit_scale

    rng = np.random.default_rng(66)
    m = _media(a=Still(rng.integers(0, 256, (23, 37, 4), dtype=np.uint8)))
    r = _renderer(ctx, m)
    prog = ctx.program(vertex_shader=QUAD_VS, fragment_shader=FIT_BEFORE)
    vao = ctx.vertex_array(prog, [])
    size = (48, 40)
    out = ctx.texture(size, 4)
    fbo = ctx.framebuffer(color_attachments=[out])
    for fit in range(3):
        for alpha in (1.0, 0.37):
            m.channels["a"].fit = fit
            got = _fit(r, size, alpha)
            src = r.media_texture("a")
            fbo.use()
            ctx.viewport = (0, 0, *size)
            ctx.disable(moderngl.BLEND)
            src.use(location=0)
            prog["u_src"].value = 0
            prog["u_scale"].value = fit_scale(fit, tuple(src.size), size)
            prog["u_flip"].value = 1
            prog["u_alpha"].value = alpha
            vao.render(moderngl.TRIANGLES, vertices=3)
            ctx.enable(moderngl.BLEND)
            before = np.frombuffer(out.read(), np.uint8).reshape(size[1], size[0], 4)[::-1]
            assert (got == before.astype(int)).all(), (fit, alpha)


def _passes(ctx):
    from hyperspace.render import Renderer
    r = Renderer(ctx)
    return r, r.mask_passes()


def _premultiplied(px: np.ndarray) -> np.ndarray:
    a = px[..., 3:].astype(np.float64) / 255.0
    out = px.copy()
    out[..., :3] = (px[..., :3] * a + 0.5).astype(np.uint8)
    return out


@pytest.mark.parametrize("kw", CASES)
def test_any_picture_keyed_matches_its_oracle(ctx, kw):
    """`MaskPasses.key` (what a `KeyNode` runs) on a premultiplied picture:
    the same ramp on its straight colour, the colour kept or taken down."""
    _, mp = _passes(ctx)
    pre = _premultiplied(_still())
    src = ctx.texture((W, H), 4, pre.tobytes())
    out = mp.key(src, "t", (W, H), media_tex.Key(**kw))
    got = np.frombuffer(out.read(), np.uint8).reshape(H, W, 4).astype(int)
    want = _oracle(pre, premultiplied=True, **kw)
    assert np.abs(got - want).max() <= 2.5, np.abs(got - want).max()


def test_the_feather_blurs_the_alpha_alone_and_only_when_asked(ctx):
    """Feather 0 runs no blur; above 0 the ramp is blurred and the clear edge
    is softer, the colour (kept) untouched — for a picture and a channel."""
    px = np.zeros((32, 32, 4), np.uint8)
    px[..., 3] = 255
    px[:, 16:, :3] = 200                          # black left, grey right
    _, mp = _passes(ctx)
    calls = []
    real = mp.feather
    mp.feather = lambda *a, **k: calls.append(a) or real(*a, **k)
    src = ctx.texture((32, 32), 4, px.tobytes())

    def keyed(feather):
        out = mp.key(src, "t", (32, 32), media_tex.Key(feather=feather))
        return np.frombuffer(out.read(), np.uint8).reshape(32, 32, 4).astype(int)

    hard = keyed(0.0)
    assert calls == [] and hard[8, 15, 3] == 0 and hard[8, 16, 3] == 255
    soft = keyed(4.0)
    assert len(calls) == 1 and calls[0][2] == 4.0
    assert 0 < soft[8, 15, 3] < 255 and 0 < soft[8, 16, 3] < 255
    assert soft[8, 0, 3] == 0 and soft[8, 31, 3] == 255
    assert (soft[:, 16:, :3] == 200).all()
    m = _media(a=Still(px))
    m.channels["a"].fit = 2
    rr = _renderer(ctx, m)
    ch = _fit(rr, (32, 32), key=media_tex.Key(feather=4.0))
    assert 0 < ch[8, 15, 3] < 255 and (ch[:, 16:, :3] == 200).all()


def test_the_feather_does_not_eat_a_channels_edge_at_the_letterbox(ctx):
    px = np.full((8, 32, 4), 200, np.uint8)
    px[..., 3] = 255
    m = _media(a=Still(px))
    m.channels["a"].fit = 1                       # contain: letterboxed
    got = _fit(_renderer(ctx, m), (32, 32), key=media_tex.Key(feather=6.0))
    inside = got[got[..., 3] > 0]
    assert len(inside) and (inside[..., 3] == 255).all()


def test_a_keyed_effect_lets_the_scene_through_its_black(ctx):
    """Not a channel: the test card (opaque, with black between its lines)
    composited over the scene. Unkeyed it covers the shape; keyed, the shape
    shows where the card is black — the whole draw, through `KeyNode`."""
    from test_media_render import _draw, _shape

    from hyperspace.graphmigrate import wired_wiring
    r = _renderer(ctx, None)
    st = r.fx.state
    st.values["testcard"].update(on=True, mix=1.0)
    assert not r.fx.compile_all()
    nodes = [{"kind": "composite"}, {"kind": "effect", "file": "testcard"}]
    wires = (("shape", "scene.geometry"), ("scene", "composite.under"),
             ("scene", "testcard.image"), ("testcard", "composite.over"),
             ("composite", "output.all.image"))

    def drawn(keys):
        r.wiring = wired_wiring(G.read_graph(_section(keys, wires, nodes)).wiring())
        (pic,) = _draw(ctx, r, _shape(), size=(96, 64), frames=2)
        return pic

    def shape_pixels(pic):        # the shape's white-ish edges and faces, not the card's
        return int(((pic[..., :3] > 40).all(-1) & (pic[..., :3].std(-1) < 30)).sum())

    covered = drawn(None)
    clear = drawn(["testcard"])
    assert "testcard(key)" in [n.name for n in r._graph.order]
    assert (clear != covered).any()
    assert shape_pixels(clear) > shape_pixels(covered), (shape_pixels(clear),
                                                         shape_pixels(covered))


def _lay(ctx, blend: str, under, over, opaque: bool) -> np.ndarray:
    from hyperspace.render import Renderer

    r = Renderer(ctx)
    size = (4, 1)
    tex = ctx.texture(size, 4, np.array(over, np.uint8).tobytes())
    dst = ctx.texture(size, 4, np.array(under, np.uint8).tobytes())
    fbo = ctx.framebuffer(color_attachments=[dst])
    assert r.lay(tex, fbo, (0, 0, *size), blend=blend, alpha=1.0, opaque=opaque)
    return np.frombuffer(dst.read(), np.uint8).reshape(4, 4).astype(int)


def test_a_screen_lay_is_premultiplied_screen(ctx):
    """`src + dst·(1 − src)` per colour channel; alpha as over on a see-through
    ground, left as it is on an opaque one. Black adds nothing; white stays
    white; nothing passes 255."""
    under = [(100, 150, 200, 255), (100, 150, 200, 255), (255, 255, 255, 255), (60, 0, 0, 128)]
    over = [(0, 0, 0, 0), (128, 64, 255, 255), (255, 255, 255, 255), (100, 100, 100, 128)]
    for opaque in (False, True):
        got = _lay(ctx, "screen", under, over, opaque)
        u, o = np.array(under, float) / 255, np.array(over, float) / 255
        rgb = o[:, :3] + u[:, :3] * (1 - o[:, :3])
        a = u[:, 3] if opaque else o[:, 3] + u[:, 3] * (1 - o[:, 3])
        want = np.concatenate([rgb, a[:, None]], -1) * 255
        assert np.abs(got - want).max() <= 1.5, opaque
    added = _lay(ctx, "add", under, over, True)
    assert added[1, 2] == 255 and _lay(ctx, "screen", under, over, True)[1, 2] == 255
    assert _lay(ctx, "screen", under, over, True)[1, 0] < added[1, 0]


def test_a_keyed_picture_keeps_its_alpha_through_an_effect(ctx):
    """Review of #479: a keyed Test card through Fade (level 1, which keeps
    alpha) laid over a red channel on an opaque window: the channel shows
    where the card is black — the key is not made opaque when the card is
    painted into Fade's input."""
    from test_media_render import _draw, _rgba

    from hyperspace.graphmigrate import wired_wiring
    r = _renderer(ctx, _media(a=Still(_rgba(16, 9))))
    r.media.channels["a"].fit = 2
    for f in ("testcard", "fade"):
        r.fx.state.values[f].update(on=True, mix=1.0)
    assert not r.fx.compile_all()
    nodes = [{"kind": "composite"}, {"kind": "effect", "file": "testcard"},
             {"kind": "effect", "file": "fade"}]
    wires = (("channel.a", "composite.under"), ("channel.a", "testcard.image"),
             ("testcard", "fade.image"), ("fade", "composite.over"),
             ("composite", "output.all.image"))

    def red(keys):
        r.wiring = wired_wiring(G.read_graph(_section(keys, wires, nodes)).wiring())
        # (level 0.2: the card's dark-grey ground, ~0.08, all clear)
        s = view.ViewState(lines=False, points=False, faces=False,
                           keys={"testcard": view.KeyState(level=0.2)})
        (pic,) = _draw(ctx, r, s, size=(96, 64), frames=2)
        return ((pic[..., 0] > 200) & (pic[..., 1] < 60) & (pic[..., 2] < 60)).mean()

    assert red(None) < 0.05                       # the card covers the channel
    assert red(["testcard"]) > 0.3                # keyed: the channel shows through

