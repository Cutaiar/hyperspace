"""Wave 3 P2: "replace the host's dream" as a row of the conflict sheet, and
the dream owning its own params.

- a spawn holding a dream into a host with one puts up the sheet: one press,
  one undo step, what the host's loses said in words; every other
  single-instance node stays refused;
- `dream.*` is drawn where the save has it: a look-back's knobs on the
  look-back, the rest on the dream, through `graphview.OWNERS`, a node's
  `node_params`, the pane's sections and `patches._param_rows`.
"""

from __future__ import annotations

import json

import pytest
from conftest import CORPUS
from test_graph_groups import files, state, watch, wires
from test_patches import parts
from test_patches_frame_kinds import cut, on_graph, put, rig, wake_doc  # noqa: F401
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import graph as G
from hyperspace import graphview, headless, params, patches, ui_graph, ui_lookback, ui_routing, undo
from hyperspace.patches import Host, spawn

KEY = patches.replace_key("dream")


def dreamy(rig, name="dreamy", **values) -> str:  # noqa: F811
    doc = cut(name)
    doc["values"] = {**doc["values"], **values}
    return put(rig, doc)


def rows_apart(st: tuple) -> tuple:
    """`state` with the table's rows in any order: an undo of a table holding
    both kinds gives each kind back whole, the desk's and the routes' apart."""
    return (*st[:4], sorted(st[4], key=lambda r: sorted(map(str, r.items()))), *st[5:])


def sheet_up(rig, slug, **kw):  # noqa: F811
    assert ui_graph.spawn(rig.panel, slug, (0.0, 0.0), **kw) is None
    got = ui_routing.sheet(rig.panel)
    assert got is not None
    return got


# ---------------------------------------------------------------- the leaf

def test_a_host_dream_is_replacing_not_a_refusal():
    landing = spawn(cut("dreamy"), Host.of(*parts(wake_doc())[:2]))
    assert landing.taken == landing.replacing == ("dream",)
    assert landing.refusal is None
    assert landing.unanswered(None) == patches.TAKEN_WORDS.format(name="dreamy", nodes="dream")
    assert landing.unanswered({KEY: "patch"}) is None


def test_the_other_single_instance_kinds_stay_refused_and_name_only_themselves():
    p = parts(wake_doc())
    whole, _ = patches.lift(*p, ["render:scene", "render:shape", "render:dream"])
    landing = spawn({**whole, "name": "x"}, Host.of(*p[:2]))
    assert landing.replacing == ("dream",)
    assert landing.refusal == patches.TAKEN_WORDS.format(name="x", nodes="scene, shape")


def test_only_the_dream_is_replaceable_for_now():
    assert patches.REPLACEABLE == ("dream",)
    assert set(patches.REPLACEABLE) <= set(patches.ONE_PER_FRAME)


def test_a_dream_on_the_preset_is_replaceable():
    spec, table = parts(wake_doc())[:2]
    landing = spawn(cut("dreamy"), Host.of(spec, table))
    assert landing.replacing == ("dream",) and landing.refusal is None


# ---------------------------------------------------------------- the sheet

def test_one_press_replaces_the_hosts_dream_as_one_undo_step(rig):  # noqa: F811
    """The ask, through the doors: the sheet says what the host's dream loses,
    Spawn lands the patch's in its place — one dream, the patch's values and
    wires, the look-back's knobs untouched, its host cables gone and the pins
    open (D2), its rows staying — and one ⌘Z puts all of it back."""
    on_graph(rig, "party-wake")
    slug = dreamy(rig, **{"dream.mix": 0.31, "dream.hue": 12.0})
    reg = rig.reg
    reg["dream.mix"].set_value(0.8)
    fade, echoes = reg["dream.fade"].base, reg["dream.echo_mix"].base
    host_wires = wires(rig)
    assert ("lookback", "dream.image") in host_wires and ("dream", "composite.over") in host_wires
    before, home = state(rig), files(rig.lib.home)
    u = watch(rig)
    try:
        n = len(u.stack)
        landing, choices = sheet_up(rig, slug)
        assert choices[KEY] == "patch"
        assert state(rig) == before and len(u.stack) == n        # nothing lands until the press
        assert landing.loses[0] == ("its wires: lookback → dream.image, "
                                    "dream → composite.over")
        assert any("setting" in line for line in landing.loses)
        said = ui_graph._state(rig.panel)["said"]
        assert said.startswith(ui_graph.SHEET_REPLACES.format(nodes="dream"))
        frame(rig.panel)
        assert ui_routing._state(rig.panel)["sheet"]

        assert ui_routing.settle_sheet(rig.panel, True) is None   # the one press
        assert ui_routing.sheet(rig.panel) is None and len(u.stack) == n + 1
        spec = rig.lib.presets.graph.spec
        assert [nm for nm in patches.spec_names(spec) if nm.startswith("dream")] == ["dream"]
        now = wires(rig)
        assert ("lookback", "dream.image") not in now
        assert ("dream", "composite.over") not in now
        assert ("dream", "composite.2.over") in now               # the patch's own wire
        assert reg["dream.mix"].base == pytest.approx(0.31)
        assert reg["dream.hue"].base == pytest.approx(12.0)
        assert reg["dream.fade"].base == fade                     # the look-back's: not the patch's
        assert reg["dream.echo_mix"].base == echoes
        group = rig.lib.presets.groups[-1]
        assert "render:dream" in group["nodes"]
        assert {p["id"] for p in graphview.open_ports(spec, group)} >= {"in"}
        head = ui_graph._state(rig.panel)["said"]
        assert "replaced this preset's dream: its wires: lookback → dream.image" in head
        assert files(rig.lib.home) == home                        # nothing written
        # its result drawn: the canvas holds the patch's dream, with its knobs
        frame(rig.panel, "graph")
        view = ui_graph._state(rig.panel)["view"]
        assert view.node("render:dream") is not None
        assert "dream.mix" in ports_of(view, "render:dream")

        u.undo()
        assert rows_apart(state(rig)) == rows_apart(before)
        assert reg["dream.mix"].base == pytest.approx(0.8)
        assert ("dream", "composite.over") in wires(rig)
    finally:
        undo.install(None)


def test_cancel_lands_nothing_and_keeps_the_hosts_dream(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    slug = dreamy(rig)
    before = state(rig)
    u = watch(rig)
    try:
        n = len(u.stack)
        sheet_up(rig, slug)
        assert ui_routing.settle_sheet(rig.panel, False) is None
        assert state(rig) == before and len(u.stack) == n
    finally:
        undo.install(None)


def test_keep_all_existing_does_not_answer_the_dream(rig):  # noqa: F811
    """The controls' rows are two-way; the node's is not: **keep all existing**
    leaves the replace asked, and lands the patch with the preset's rows."""
    on_graph(rig, "party-wake")
    slug = dreamy(rig)
    landing, _ = sheet_up(rig, slug)
    assert landing.conflicts                         # party-wake's own rows collide
    ui_routing.keep_all(rig.panel)
    choices = ui_routing.sheet(rig.panel)[1]
    assert choices[KEY] == "patch"
    assert all(choices[k] == "preset" for k in range(len(landing.conflicts)))
    assert ui_routing.settle_sheet(rig.panel, True) is None
    assert ("dream", "composite.over") not in wires(rig)


def macro_on_mix(rig):  # noqa: F811
    """A base subscriber of macro.1 on `dream.mix`, its range high."""
    table = rig.router.table
    doc = table.macros_doc()
    doc["macro.1"] = {"label": "", "subs": [{"base": "dream.mix", "from": 0.8, "to": 1.0}]}
    assert table.set_macros(doc, rig.reg) == []
    rig.router.follow_macros()


def test_a_macros_hold_on_a_replaced_param_goes_and_the_sheet_says_so(rig):  # noqa: F811
    """A base subscriber re-lands at the next `follow_macros` after a
    `set_macros`, so left in place it overwrites the patch's value: it lets go,
    under what the dream loses, and an undo puts it back."""
    on_graph(rig, "party-wake")
    slug = dreamy(rig, **{"dream.mix": 0.2})
    macro_on_mix(rig)
    u = watch(rig)
    try:
        landing, _ = sheet_up(rig, slug)
        assert any(line.startswith("macro.1's hold on") for line in landing.loses)
        assert ui_routing.settle_sheet(rig.panel, True) is None
        table = rig.router.table
        assert not [s for s in table.macros["macro.1"].subs if s.base == "dream.mix"]
        rig.reg["macro.1"].set_value(1.0)
        rig.router.follow_macros()
        rig.router.follow_macros(force=True)
        assert rig.reg["dream.mix"].base == pytest.approx(0.2)
        u.undo()
        assert [s.base for s in rig.router.table.macros["macro.1"].subs] == ["dream.mix"]
    finally:
        undo.install(None)


def test_a_macro_on_anything_else_keeps_its_hold(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    slug = dreamy(rig)
    table = rig.router.table
    doc = table.macros_doc()
    doc["macro.1"] = {"label": "", "subs": [{"base": "dream.fade", "from": 0.1, "to": 0.9}]}
    assert table.set_macros(doc, rig.reg) == []
    sheet_up(rig, slug)
    assert ui_routing.settle_sheet(rig.panel, True) is None
    assert [s.base for s in table.macros["macro.1"].subs] == ["dream.fade"]


def test_the_sheet_is_stale_when_another_preset_loads_under_it(rig):  # noqa: F811
    """The modal stops the panel, not a pad or a bank press: what it said was
    A's. Nothing of B is taken."""
    on_graph(rig, "party-wake")
    slug = dreamy(rig)
    landing, choices = sheet_up(rig, slug)
    assert landing.asked
    rig.lib.load("presets", "party-wake")
    before = state(rig)
    e = ui_graph.group_edit(rig.panel)
    name = landing.group["name"]
    assert e.spawn(landing, choices) == graphview.SPAWN_STALE.format(name=name)
    assert state(rig) == before
    rig.panel.spawn_question = None


def test_the_sheet_stands_while_a_frame_passes_and_a_knob_turns(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    slug = dreamy(rig)
    sheet_up(rig, slug)
    frame(rig.panel)
    rig.reg["dream.mix"].set_value(0.123)
    frame(rig.panel)
    assert ui_routing.settle_sheet(rig.panel, True) is None


def test_the_sheet_is_stale_when_a_wire_of_the_dream_moves_under_it(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    slug = dreamy(rig)
    landing, choices = sheet_up(rig, slug)
    e = ui_graph.group_edit(rig.panel)
    assert graphview.render_add(e, "effect", "acid") is None     # any landing: a new section
    name = landing.group["name"]
    assert e.spawn(landing, choices) == graphview.SPAWN_STALE.format(name=name)
    rig.panel.spawn_question = None


def test_the_replaced_values_read_what_the_node_owns_for_any_kind(rig):  # noqa: F811
    """The door for the other kinds: a shape's fresh values are by what it
    owns (`rot.*`, most of `view.*`), not a group of its name."""
    on_graph(rig, "party-wake")
    e = ui_graph.group_edit(rig.panel)
    got = e._replaced_values({}, ("shape",))
    assert "view.bright" in got and "view.pattern" not in got
    assert any(k.startswith("rot.") for k in got) or not any(
        p.id.startswith("rot.") and p.persist for p in rig.reg)
    assert all(patches.node_members(("shape",)).owns(k) for k in got)


def test_the_head_says_both_when_a_replace_and_controls_are_asked(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    slug = dreamy(rig)
    landing, _ = sheet_up(rig, slug)
    assert landing.conflicts
    said = ui_graph._state(rig.panel)["said"]
    assert ui_graph.SHEET_REPLACES.format(nodes="dream") in said
    assert "the preset already uses" in said


def test_the_drag_does_not_light_the_replaced_dreams_own_cable(rig, monkeypatch):  # noqa: F811
    """The hover judges as the drop does: the dream's own cable says why, a
    cable elsewhere lights."""
    on_graph(rig, "party-wake")
    slug = put(rig, cut("alone", ["render:dream"]))
    row = next(r for r in ui_graph.patch_list(rig.panel) if r["slug"] == slug)
    assert row["replaces"] == ("dream",)
    st = ui_graph._state(rig.panel)
    view = st["view"]
    st["patch_drag"] = slug
    monkeypatch.setattr(ui_graph.ed, "suspend", lambda: None)
    monkeypatch.setattr(ui_graph.ed, "resume", lambda: None)
    monkeypatch.setattr(ui_graph.ui, "tooltip", lambda *_: None)
    def near(ends):
        c = next(c for c in view.cables if c.kind == "render" and (c.ref.src, c.ref.dst) == ends)
        monkeypatch.setattr(graphview, "cable_near", lambda *a, **k: c)
        return c
    near(("dream", "composite.over"))
    ui_graph._drop_target(rig.panel, st, view)
    assert st["drop_cable"] is None
    assert st["drop_why"] == graphview.SPLICE_REPLACED.format(name="alone", node="dream")
    c = near(("composite", "output.all.image"))
    ui_graph._drop_target(rig.panel, st, view)
    assert st["drop_cable"] == c.id
    st["patch_drag"] = None


def test_rows_on_the_hosts_dream_stay_and_are_said(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    doc = cut("clean")
    doc["routes"], doc["desk"] = [], []
    slug = put(rig, doc)
    table = rig.router.table
    onto = [b for b in (*table.routes(), *table.desk()) if b.target == "dream.mix"]
    assert onto
    landing, _ = sheet_up(rig, slug)
    assert not landing.conflicts
    assert any("stay, and drive the patch's dream" in line for line in landing.keeps)
    assert not any("stay" in line for line in landing.loses)
    assert ui_routing.settle_sheet(rig.panel, True) is None
    left = [b for b in (*table.routes(), *table.desk()) if b.target == "dream.mix"]
    assert [b.source for b in left] == [b.source for b in onto]


def test_a_param_the_file_leaves_out_is_fresh_not_the_hosts(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    doc = cut("partial")
    doc["values"] = {k: v for k, v in doc["values"].items() if k != "dream.hue"}
    slug = put(rig, doc)
    rig.reg["dream.hue"].set_value(77.0)
    fresh = rig.lib.resolved("dream", {})["dream.hue"]
    sheet_up(rig, slug)
    assert ui_routing.settle_sheet(rig.panel, True) is None
    assert rig.reg["dream.hue"].base == pytest.approx(fresh)


def test_the_hosts_group_lets_the_dream_go_and_its_pins_with_it(rig):  # noqa: F811
    """A second spawn of the same patch replaces the first's dream: the first
    group keeps what else it holds, and no open pin on a node it lost."""
    on_graph(rig, "party-noita")
    slug = dreamy(rig)
    assert ui_graph.spawn(rig.panel, slug, (0.0, 0.0)) is None     # no dream here: straight on
    if ui_routing.sheet(rig.panel) is not None:
        ui_routing.settle_sheet(rig.panel, True)
    pre = rig.lib.presets
    first = pre.groups[-1]
    assert "render:dream" in first["nodes"]
    assert any(p.get("to", "").startswith("dream.") for p in first["ports"])
    landing, _ = sheet_up(rig, slug)
    assert f"its place in {first['name']}" in landing.loses
    held = [dict(g) for g in pre.groups]
    u = watch(rig)
    try:
        assert ui_routing.settle_sheet(rig.panel, True) is None
        one, two = pre.groups[-2:]
        assert one["id"] == first["id"] and "render:dream" not in one["nodes"]
        assert "render:dream" in two["nodes"]
        assert not any(p.get("to", "").startswith("dream.") for p in one["ports"])
        spec = pre.graph.spec
        assert all(not p.get("to", "").startswith("dream.")
                   for p in graphview.open_ports(spec, one))
        u.undo()
        assert [g["nodes"] for g in pre.groups] == [g["nodes"] for g in held]
    finally:
        undo.install(None)


def test_a_group_of_the_dream_alone_goes_with_it(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    slug = put(rig, cut("alone", ["render:dream"]))
    entry = ui_graph.group_nodes(rig.panel, ["render:dream"])
    assert entry["nodes"] == ["render:dream"]
    sheet_up(rig, slug)
    assert ui_routing.settle_sheet(rig.panel, True) is None
    assert [g["nodes"] for g in rig.lib.presets.groups] == [["render:dream"]]
    assert rig.lib.presets.groups[0]["id"] != entry["id"]


def test_wire_as_saved_puts_the_replacing_dream_on_the_hosts_picture(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    slug = put(rig, cut("alone", ["render:dream"]))
    sheet_up(rig, slug)
    assert ui_routing.settle_sheet(rig.panel, True) is None
    g = rig.lib.presets.groups[-1]
    assert ui_graph.wire_as_saved(rig.panel, g["id"]) is None
    assert {("lookback", "dream.image"), ("dream", "composite.over")} <= set(wires(rig))


def test_the_edit_lands_no_replace_nobody_asked_for(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    e = ui_graph.group_edit(rig.panel)
    landing = spawn(cut("dreamy"), Host.of(*rig.lib.presets.parts()[:2]))
    before = state(rig)
    assert e.spawn(landing) == landing.unanswered(None)
    assert state(rig) == before
    assert e.spawn(landing, {KEY: "patch"}) is None
    assert ("dream", "composite.over") not in wires(rig)


def test_a_splice_onto_the_replaced_dreams_own_cable_is_refused_before_the_sheet(rig):  # noqa: F811
    """The cable goes with the dream it is a cable of."""
    on_graph(rig, "party-wake")
    slug = put(rig, cut("alone", ["render:dream"]))
    before = state(rig)
    said = ui_graph.spawn(rig.panel, slug, (0.0, 0.0), splice=("dream", "composite.over"))
    assert said == graphview.SPLICE_REPLACED.format(name="alone", node="dream")
    assert ui_routing.sheet(rig.panel) is None and state(rig) == before


def test_a_splice_elsewhere_replaces_and_splices_in_one_step(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    slug = put(rig, cut("alone", ["render:dream"]))
    u = watch(rig)
    try:
        n = len(u.stack)
        sheet_up(rig, slug, splice=("composite", "output.all.image"))
        assert ui_routing.settle_sheet(rig.panel, True) is None
        assert len(u.stack) == n + 1
        now = wires(rig)
        assert ("composite", "dream.image") in now and ("dream", "output.all.image") in now
        assert ("lookback", "dream.image") not in now
    finally:
        undo.install(None)


# ---------------------------------------------------------------- whose params

def test_the_canvas_and_the_save_agree_on_dream_over_the_whole_registry(tmp_path):
    """Every `dream.*` param, `graphview.OWNERS` and `patches._param_rows`
    name the same node, a second look-back's knobs its own."""
    app = headless.make_app(tmp_path)
    rule = graphview.OWNERS["dream"]
    mem = patches._Members(("lookback", "lookback.2", "dream"))
    seen = 0
    for p in app.reg:
        if p.group == "dream" and not p.alias:
            seen += 1
            assert rule(p.id, None) == patches._owner(p.id, mem.param_rows, ()), p.id
    assert seen > 20
    assert rule("dream.2.fade", None) == "lookback.2"
    assert rule("dream.fade", None) == "lookback"
    assert rule("dream.mix", None) == "dream" and rule("dream.on", None) == "dream"


def ports_of(view, nid: str) -> set[str]:
    return {p.param for p in view.node(nid).ports if p.param}


def test_the_dream_node_draws_its_params_and_the_look_back_its(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    view = ui_graph._state(rig.panel)["view"]
    on_dream, on_look = ports_of(view, "render:dream"), ports_of(view, "render:lookback")
    assert {"dream.mix", "dream.hue", "dream.k"} <= on_dream
    assert {"dream.fade", "dream.echo_mix", "dream.darken"} <= on_look
    assert not {p for p in on_dream if params.is_lookback_knob(p)}
    assert not {p for p in on_look if not params.is_lookback_knob(p)}


def test_a_node_the_section_lacks_leaves_the_params_to_the_group_node(rig):  # noqa: F811
    """A look-back and no dream: the dream's rows sit on `group:dream`, as any
    param of a node the section does not name does; the look-back's stay."""
    on_graph(rig, "party-noita")
    spec = rig.lib.presets.graph.spec
    assert "dream" not in patches.spec_names(spec)
    view = ui_graph._state(rig.panel)["view"]
    if view.node("render:lookback") is not None:
        assert not {p for p in ports_of(view, "render:lookback")
                    if not params.is_lookback_knob(p)}
    assert "dream.mix" in ports_of(view, "group:dream")


def test_a_nodes_selected_params_are_its_own(rig):  # noqa: F811
    on_graph(rig, "party-wake")
    panel = rig.panel
    dream = ui_graph.node_params(panel, "render:dream")
    look = ui_graph.node_params(panel, "render:lookback")
    assert "dream.mix" in dream and "dream.on" in dream and "dream.fade" not in dream
    assert "dream.fade" in look and "dream.mix" not in look
    assert not set(dream) & set(look)
    assert set(dream) | set(look) >= {p.id for p in rig.reg
                                      if p.group == "dream" and not p.alias
                                      and p.id.count(".") == 1}


def test_the_panes_sections_are_the_same_split():
    for pid in ui_lookback.SECTIONS["look-back"]:
        assert graphview.OWNERS["dream"](pid, None) == "lookback", pid
    for pid in ui_lookback.SECTIONS["dream"]:
        assert graphview.OWNERS["dream"](pid, None) == "dream", pid


@pytest.mark.parametrize("name", ["party-wake", "party-noita"])
def test_a_saved_preset_is_unmoved_by_who_draws_its_params(rig, name):  # noqa: F811
    """Behaviour-neutral: the section and every `dream.*` value read back as
    the file has them, the row ids as they were."""
    path = CORPUS / "presets" / f"{name}.json"
    file = json.loads(path.read_text())
    on_graph(rig, name)
    for k, v in file.get("values", {}).items():
        if k.startswith("dream.") and k in rig.reg:
            assert rig.reg[k].base == pytest.approx(v), k
    assert G.read_graph(file["graph"]).to_json() == rig.lib.presets.graph.spec.to_json()
    got = {(b.source, b.target) for b in rig.router.table.routes()}
    assert {(r["source"], r["target"]) for r in file.get("routes", ())} <= got


def test_a_landing_from_before_a_hot_reload_still_refuses_or_lands(rig):  # noqa: F811
    """A sheet held across a reload holds the old class: no `replacing`, no
    `unanswered`, no AttributeError."""
    from types import SimpleNamespace
    on_graph(rig, "party-noita")
    e = ui_graph.group_edit(rig.panel)
    old = SimpleNamespace(group={"nodes": []}, modifiers=(), lfos=(), envs=())
    assert e._spawn_refusal(old) is None and e.replace_said(old) == ([], [])
