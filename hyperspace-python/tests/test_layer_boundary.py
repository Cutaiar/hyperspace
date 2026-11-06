"""The two layers, mechanically (the owner, 2026-11-04, fourth round: "two layers of
granularity and no others", which "must be completely consolidated and orthogonal, so that
neither can leak into the other"; register rows 746, 747).

Three holds: every param is in exactly one layer, over the boot registry and the app's added
groups; `preset.*`, `deck.chase`, `totem.*` and `poi.*` are meta and still one per `Deck`, so
no patch's row reaches them while a person's rows still do; and the patch layer's modules
reach the meta controller's only through `SURFACE`, the list below.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from test_loadable import put
from test_meta_rule import _with
from test_midi import note, push
from test_on_off_air import _bank, _state
from test_on_off_air import rig as air_rig  # noqa: F401 — two decks and the desk
from test_pad_learn import ScriptedPad
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import (
    apc40,
    app,
    gamepad,
    graphview,
    hands,
    patches,
    playlist,
    poi,
    routing,
    totem,
    ui_routing,
    undo,
)
from hyperspace.overlay import Output
from hyperspace.params import (
    META_PARTS,
    PARTS,
    PER_DECK_META,
    PER_DECK_META_GROUPS,
    SHARED_META_IDS,
    SHARED_META_KEYS,
    Kind,
    MetaRegistry,
    Param,
    is_meta_id,
    is_per_deck_meta_id,
    part_of,
    part_of_id,
)
from hyperspace.routing import (
    MOD_OPS,
    Binding,
    Bindings,
    Macro,
    base_refusal,
    is_meta_row,
    meta_refusal,
)

PKG = Path(app.__file__).resolve().parent
SHIFT_UP = "global"
# a real button of the APC's that no factory row reserves: track 1's clip stop
CH, N = 0, apc40.N_CLIPSTOP
BUTTON = f"note:{CH}:{N}"


@pytest.fixture()
def rig(air_rig):  # noqa: F811
    """Two decks and the desk, with the groups only `app.main` adds, as it adds them."""
    r = air_rig
    settings = hands.HandSettings.from_config({})
    hands.register(r.one.reg, settings)
    if "output.monitor" not in r.one.reg:
        Output(None, None).register(r.one.reg)
    totem.register(r.one.reg, totem.TotemState())
    poi.register(r.one.reg, poi.PoiState(), {})
    app._share_experiments(r.one.reg, r.two.reg, poi_cfg={})
    playlist.register(r.one.reg, playlist.Playing(r.meta, r.lib))
    return r


# ------------------------------------------------------------ exactly one layer

def layer_of(p) -> str | None:
    """The layer `p` is in; None: in neither, a bug."""
    part = part_of(p)
    return "meta" if part in META_PARTS else "patch" if part == "patch" else None


def layer_faults(reg) -> list[str]:
    """Every param of `reg` not in exactly one layer, in words."""
    out = []
    for p in reg:
        claims = [name for name, groups in PARTS.items() if p.group in groups]
        if p.id in SHARED_META_IDS or p.id.rpartition(".")[2] in SHARED_META_KEYS.get(p.group, ()):
            claims = ["shared_meta"]        # (asked first: `part_of_id`)
        if len(claims) != 1:
            out.append(f"{p.id}: group {p.group!r} is in {claims or 'neither layer'}")
        elif layer_of(p) is None:
            out.append(f"{p.id}: in no layer")
        elif part_of(p) != part_of_id(p.id):
            out.append(f"{p.id}: by the param {part_of(p)}, by the id {part_of_id(p.id)}")
    return out


def test_no_group_is_in_two_parts_and_every_part_is_in_one_layer():
    seen: dict[str, str] = {}
    for name, groups in PARTS.items():
        for g in groups:
            assert g not in seen, f"{g} is in {seen[g]} and {name}"
            seen[g] = name
    assert {*META_PARTS, "patch"} == set(PARTS), "two layers and no others"


def test_every_param_of_the_app_is_in_exactly_one_layer(rig):
    """Both decks' registries, with `hands`, `output`, the dial, `totem` and `poi`."""
    for d in (rig.one, rig.two):
        assert not layer_faults(d.reg)
    assert any(p.group == "fx" for p in rig.one.reg)
    assert {"hands", "output", "desk", "totem", "poi", "deck", "preset"} <= {
        p.group for p in rig.one.reg}
    # the dial's readings: in the patch layer, one per `Deck`, and each deck's own
    for d in (rig.one, rig.two):
        assert layer_of(d.reg["pad.dial.left"]) == "patch"
        assert layer_of(d.reg["pad.dial.right"]) == "patch"
        assert layer_of(d.reg["pad.dial.swap"]) == "patch"
    assert rig.one.reg["pad.dial.left"] is not rig.two.reg["pad.dial.left"]


def test_every_param_of_the_panels_registry_is_in_exactly_one_layer(shell_rig):  # noqa: F811
    """The panel's own `ui.*` and the outputs' switches."""
    assert not layer_faults(shell_rig.reg)
    assert any(p.group == "ui" for p in shell_rig.reg)
    assert any(p.id.startswith("output.") for p in shell_rig.reg)


def test_the_test_fails_on_neither_and_on_both(monkeypatch):
    """The fault is the point of the test, so it is exercised: a param in no group, and
    a group added to a second part."""
    assert layer_faults([Param("nowhere.x", "x", Kind.TOGGLE, group="nowhere")])
    assert layer_faults([Param("x", "x", Kind.TOGGLE, group=None)])
    p = Param("view.x", "x", Kind.TOGGLE, group="view")
    assert not layer_faults([p])
    monkeypatch.setitem(PARTS, "shared_meta", (*PARTS["shared_meta"], "view"))
    assert layer_faults([p])


DECLARERS = {"continuous", "enum", "toggle", "trigger", "text", "Param"}


def _strings_of(tree: ast.Module) -> dict[str, str]:
    """`NAME = "text"` anywhere in a module: what a `group=NAME` can resolve to."""
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) \
                and isinstance(n.value.value, str):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = n.value.value
    return out


def declared_groups() -> set[str]:
    """Every group a declaration names in the package's source, for those no fixture
    reaches: a node that exists only once a graph names it, a device that is not here."""
    named: dict[str, str] = {}
    trees = {f: ast.parse(f.read_text()) for f in sorted(PKG.rglob("*.py"))}
    for tree in trees.values():
        for k, v in _strings_of(tree).items():
            if k.endswith("GROUP"):
                named.setdefault(k, v)
    out = set()
    for tree in trees.values():
        local = {**named, **_strings_of(tree)}
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            name = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
            if name not in DECLARERS:
                continue
            for k in n.keywords:
                if k.arg != "group":
                    continue
                if isinstance(k.value, ast.Constant) and isinstance(k.value.value, str):
                    out.add(k.value.value)
                elif isinstance(k.value, ast.Name) and k.value.id in local:
                    out.add(local[k.value.id])
    return out


def test_every_group_the_source_declares_is_in_a_part():
    """The app's added groups by source, the sweep's grep made a test: a new group in
    neither layer fails here even if no fixture builds it."""
    groups = declared_groups()
    assert {"totem", "poi", "deck", "preset", "output", "hands", "switch"} <= groups
    every = {g for gs in PARTS.values() for g in gs}
    assert not groups - every, sorted(groups - every)


# ------------------------------------------------------------ meta, one per `Deck`

def per_deck(reg) -> list[Param]:
    return [p for p in reg if part_of(p) == PER_DECK_META]


def test_the_sweep_names_what_was_in_neither(rig):
    """Row 746's list: what `part_of` called None until now, by group."""
    groups = {p.group for p in per_deck(rig.one.reg)}
    assert groups == set(PER_DECK_META_GROUPS)
    assert sum(p.group == "preset" for p in rig.one.reg) == 23
    assert [p.id for p in rig.one.reg if p.group == "deck"] == ["deck.chase"]
    assert all(layer_of(p) == "meta" and is_meta_id(p.id) for p in per_deck(rig.one.reg))


def test_they_stay_one_object_per_deck_and_a_shared_param_stays_one(rig):
    one, two = rig.one.reg, rig.two.reg
    assert {p.id for p in per_deck(one)} == {p.id for p in per_deck(two)}
    for p in per_deck(one):
        assert p is not two[p.id], p.id
        assert p.id not in one.meta_reg
    assert one["master.gain"] is two["master.gain"]


def test_none_is_saved_and_no_stack_watches_one(rig):
    """No file changes: neither a snapshot nor undo sees the class."""
    assert not [p.id for p in per_deck(rig.one.reg) if p.persist]
    assert not [p.id for p in per_deck(rig.one.reg) if undo.watched(p)]
    snap = rig.one.reg.snapshot()
    assert not [k for k in snap if is_per_deck_meta_id(k)]
    assert rig.one.reg.snapshot(part=PER_DECK_META) == {}


def test_the_shared_registry_refuses_one():
    meta_reg = MetaRegistry()
    with pytest.raises(ValueError, match="closes over one deck"):
        meta_reg.add(Param("deck.x", "x", Kind.TOGGLE, group="deck"))


def test_an_id_this_build_lacks_is_still_classed():
    assert is_meta_id("preset.a.new.verb") and is_per_deck_meta_id("poi.a.new.dial")
    assert meta_refusal("preset.a.new.verb") is not None
    assert not is_meta_id(None) and not is_meta_id("")


def test_the_refusal_is_the_layer_over_every_param(rig):
    """Every param of a deck: refused exactly when it is meta. No list of ids."""
    for p in rig.one.reg:
        assert (meta_refusal(p.id) is not None) == (layer_of(p) == "meta"), p.id


ROWS = ["preset.next", "preset.select", "preset.save.0", "preset.save_new", "preset.home",
        "deck.chase", "totem.on", "totem.reset", "poi.on", "poi.length", "poi.reset"]


@pytest.mark.parametrize("pid", ROWS)
def test_no_patch_row_reaches_one_by_any_door(pid):
    t = Bindings()
    for row in (Binding("note:0:60", pid, "toggle", layer="preset"),
                *(Binding("seq:0", pid, op, 1.0) for op in MOD_OPS),
                Binding("hand:left.y", pid, "push", 0.5, enabled=False)):
        assert not is_meta_row(row)
        assert "no patch's row" in routing.meta_row_refusal(row)
        with pytest.raises(ValueError):       # (`deck.chase`: the held rule says first)
            t.add(row)
        with pytest.raises(ValueError):
            t.bind(row, write=False)
    assert t.set_desk([Binding("note:0:60", pid, "toggle")]) and not t.desk()
    assert base_refusal(pid) is not None


@pytest.mark.parametrize("carrier", [0, 1], ids=["on air carries", "off air carries"])
def test_a_saved_row_on_a_totem_or_a_poi_drops_with_a_note_and_presses_nothing(rig, carrier):
    """The new reach of the class: a desk row on a saved row, and a route, and a value."""
    d = (rig.one, rig.two)[carrier]
    targets = ["totem.on", "poi.on", "deck.chase", "poi.length"]
    put(rig.lib.home, "CARRIES",
        desk=[{"source": f"note:8:{k}", "target": t,
               "op": "momentary" if t == "deck.chase" else "toggle"}
              for k, t in enumerate(targets)],
        routes=[{"source": f"seq:{k}", "target": t, "op": "push", "value": 1.0}
                for k, t in enumerate(targets)],
        values={"totem.on": True, "poi.length": 2.0})
    d.loaded_patch.load("CARRIES")
    assert d.loaded_patch.current == "CARRIES"
    assert not [b for b in d.table.bindings if b.target in targets and not is_meta_row(b)]
    for t in targets:
        assert any(n.startswith("dropped note:8:") and f"→ {t}" in n and "no patch's row" in n
                   for n in d.loaded_patch.notes), t
        assert any(n.startswith("dropped seq:") and t in n for n in d.loaded_patch.notes), t
    assert d.reg["totem.on"].value is False
    rig.meta.pointer("apc40").deck = d
    length = d.reg["poi.length"].value
    push(rig.r, *(note(k, channel=8) for k in range(len(targets))))
    assert d.reg["totem.on"].value is False and d.reg["poi.on"].value is False
    assert d.reg["poi.length"].value == length and d.reg["deck.chase"].value is False


def test_a_file_saved_after_it_holds_none_of_them(rig):
    """"Drop the row with a note; a later save removes it" (MR1), as for any meta row."""
    d = rig.one
    path = put(rig.lib.home, "CARRIES", desk=[{"source": "note:8:0", "target": "totem.on",
                                               "op": "toggle"}])
    d.loaded_patch.load("CARRIES")
    d.loaded_patch.save_as("CARRIES")
    doc = json.loads(path.read_text())
    assert not [r for r in (*doc["desk"], *doc["routes"]) if is_meta_id(r["target"])]


def test_the_graph_offers_no_port_on_one(rig):
    """Row 746: `graphview`'s params node lists what a route may land on, the layer's rule."""
    d = rig.one
    view = graphview.build(Bindings(), d.reg)    # (no rows: a row's own target gets a port)
    ids = {p.param for n in view.nodes for p in n.ports if p.param}
    assert "view.speed" in ids
    assert not [pid for pid in ids if is_meta_id(pid)]


# ------------------------------------------------------------ the person's rows stay

@pytest.mark.parametrize("row", [
    Binding("note:0:61", "preset.next", "toggle"),
    Binding("note:0:62", "preset.save.0", "hold", layer=SHIFT_UP),
    Binding("key:F9", "preset.load.0", "fire"),
    Binding("key:SHIFT+F9", "preset.save.0", "fire"),
    Binding("pad:A", "preset.next", "fire"),
    Binding("pad@edge:MENU", "preset.save_new", "hold"),
    Binding("pad:VIEW", "deck.chase", "momentary"),
    Binding("pad:X", "totem.on", "toggle"),
    Binding("hat:UP", "poi.on", "toggle"),
    Binding("key:T", "totem.reset", "fire"),
])
def test_the_meta_rows_road_stays_open(row):
    assert is_meta_row(row) and routing.meta_row_refusal(row) is None
    assert Bindings().add(row) is row


def test_every_factory_row_on_the_class_is_the_meta_controllers():
    rows = [b for b in Bindings.factory().bindings if is_per_deck_meta_id(b.target)]
    assert {b.target for b in rows} >= {"preset.select", "preset.load.0", "preset.save.0",
                                        "preset.home", "deck.chase"}
    assert all(is_meta_row(b) for b in rows)


def test_shift_f_keys_save_by_the_real_road(rig):
    import glfw

    project = rig.one.loaded_patch.lib.project
    _bank(rig, "party-wake", "party-tumble")
    rig.one.loaded_patch.load("party-wake")
    path = rig.lib.path_of("presets", project.bank[0])
    was = json.loads(path.read_text())["values"]["view.bright"]
    rig.one.reg["view.bright"].set(was + 0.25)
    rig.r.router.keys(NS(pressed=lambda code: code == glfw.KEY_F1, shift=lambda: True))
    assert json.loads(path.read_text())["values"]["view.bright"] == was + 0.25


def test_a_pad_learn_on_a_load_still_lands_and_loads_off_air(rig):
    """Learn pad: a person's row, in `bindings.json`, which reaches both decks."""
    _bank(rig, "party-wake", "party-tumble")
    d = rig.one
    assert ui_routing.pad_target(d.reg["preset.load.1"])
    theirs = _state(d)
    d.learn.arm("preset.load.1", "pad")
    assert d.learn.learn_pad_button("pad:A")
    row = next(b for b in d.table.bindings if b.source == "pad:A")
    assert row.target == "preset.load.1" and is_meta_row(row)
    assert any(b is row for b in rig.two.table.bindings)
    doc = json.loads(d.table.path.read_text())
    assert any(r["source"] == "pad:A" and r["target"] == "preset.load.1" for r in doc["bindings"])
    pad = ScriptedPad()
    pad.frame(held={gamepad.A})
    d.router.pad(pad, now=1.0)
    assert rig.two.loaded_patch.current == "TUMBLE" and _state(d) == theirs


# ------------------------------------------------------------ review of #388

def _learned(d, pid, source=BUTTON, profile=apc40):
    d.learn.arm(pid, "desk")
    return d.learn.learn_control(source, profile)


@pytest.mark.parametrize("pid", ROWS)
def test_a_desk_learn_on_the_class_is_refused_and_says_where_the_road_is(rig, pid):
    """Row 755: built and removed. "No new Learn road is needed for now: a preset's Learn desk
    on a meta param stays refused" (the owner, seventh round). Nothing moves, on disk either."""
    d = rig.one
    rows = list(d.table.bindings)
    file = d.table.path.read_bytes() if d.table.path.exists() else None
    assert not _learned(d, pid)
    assert "no patch's row" in d.learn.last and "Learn pad" in d.learn.last
    assert d.learn.learning is None, "armed for the desk, so the learn is over"
    assert len(d.table.bindings) == len(rows) and all(a is b for a, b in zip(d.table.bindings, rows))
    assert (d.table.path.read_bytes() if d.table.path.exists() else None) == file


@pytest.mark.parametrize("pid", ROWS)
def test_neither_the_menu_nor_hover_to_map_offers_the_class(rig, pid):
    from hyperspace.ui import Panel

    assert not ui_routing.desk_target(rig.one.reg[pid]) and not Panel._desk_target(rig.one.reg[pid])
    d = rig.one
    d.learn.pick(BUTTON)
    assert not d.learn.map_picked(pid, apc40)
    assert "Learn pad" in d.learn.last and not [b for b in d.table.bindings if b.source == BUTTON]


def test_a_bare_arm_still_waits_for_a_pad_button(rig):
    d = rig.one
    d.learn.arm("preset.next")
    assert not d.learn.learn_control(BUTTON, apc40)
    assert d.learn.learning == "preset.next"
    assert d.learn.learn_pad_button("pad:A")


def test_the_tuned_meta_params_refuse_without_the_road_words(rig):
    d = rig.one
    assert not _learned(d, "master.gain")
    assert "meta controller" in d.learn.last and "Learn pad" not in d.learn.last


@pytest.mark.parametrize("pid", ["deck.chase", "totem.on", "poi.length", "preset.next"])
def test_finding_1_a_macros_subscriber_on_the_class_is_a_meta_sub(pid):
    """`Macro.meta_subs`, so `patches.check` and `tools/meta_routes.py` see it (row 744)."""
    base = Macro.from_json({"subs": [{"base": pid}]})
    depth = Macro.from_json({"subs": [{"depth": {"source": "lfo:0", "target": pid}}]})
    assert base.meta_subs() == [pid] and depth.meta_subs() == [pid]
    assert any("no patch's row" in w for w in patches.check(_with(macros={
        "macro.3": {"subs": [{"base": pid}]}})))


@pytest.mark.parametrize("pid", ["deck.chase", "totem.on", "poi.on", "poi.length"])
def test_finding_3_a_patch_with_a_row_on_the_class_is_refused_whole(pid):
    """Row 744's rule reaches the class. Read-only count, 2026-11-06: 0 of the Drive's 110
    loadable patches and 8 patches hold such a row, so nothing is lost."""
    route = {"source": "lfo:0", "target": pid, "op": "push", "value": 0.2}
    assert any("no patch's row" in w for w in patches.check(_with(routes=[route])))


def test_finding_2_a_load_lets_a_glide_on_the_class_arrive(tmp_path):
    """A person's knob on a per-deck meta param: a load moves no such param, so its glide
    goes on, as `output.xfade`'s does (tests/test_desk.py). A load stops only a patch's."""
    from test_midi import cc
    from test_undo import boot, frames

    r = boot(tmp_path / "home")
    r.midi.clock = lambda: r.t
    if "poi.length" not in r.reg:
        poi.register(r.reg, poi.PoiState(), {})
    reg, slews = r.reg, r.midi._slews
    reg["desk.slew"].set(routing.SLEW_MAX_S)
    n = apc40.TRACK_KNOBS[0]
    r.table.add(Binding(f"cc:0:{n}", "poi.length", "abs"))     # invariant, as a file may hold
    p = reg["poi.length"]
    p.set_norm(0.0)
    r.inp.queue.append(cc(n, 0))
    frames(r, 20)
    r.inp.queue.append(cc(n, 127))
    frames(r, 3)
    assert "poi.length" in slews
    mid = p.norm
    r.loaded_patch.load("TRIP")
    frames(r)
    assert "poi.length" in slews and p.norm > mid
    frames(r, 20)
    assert p.norm == pytest.approx(1.0) and not slews


# ------------------------------------------------------------ the import wall

def _mods(*names: str) -> set[str]:
    return set(names)


# what a patch is made of, and what draws one
PATCH_MODULES = _mods(
    "patches", "loadable", "nodemode", "graph", "graphmigrate", "modgraph", "modifiers", "modbank",
    "lfo", "envelope", "sequencer", "patterns", "fx", "ghost", "lookback", "masks", "view",
    "field", "geometry", "glsl", "motion", "tapers", "palettecompat", "render", "media_tex",
    "segment", "dream", "media")
# what is set for a performance or an install
META_MODULES = _mods(
    "deck", "playlist", "players", "pointer", "app", "devices", "control", "config", "placement",
    "hotreload", "watchdog", "midi", "apc40", "generic", "gamepad", "pads", "hands", "bridge",
    "osc", "totem", "poi", "poi_guide", "overlay", "audio", "analysis", "analyzer", "bands",
    "tempo", "seq_page", "replay", "pinch")
# one module holding both layers' classes, which an import cannot tell apart. The list is the
# finding, not a licence: splitting them is the structure audit's (draft #273), and until then
# `META_NAMES` below stands guard over what a patch module takes from them
BOTH_LAYERS = _mods("params", "routing", "routing_sources", "library", "undo", "learn",
                    "outputs", "groupwords")
# above both: the panel and the headless tools, which may read either
ABOVE = _mods("ui", "graphview", "headless", "offline")

# The named surface: every way a patch module reaches a module of the meta controller's today,
# (module, what it imports, the names) and why. A new crossing fails the wall until it is named
# here, in review's sight
SURFACE = {
    ("nodemode", "players"): ({"NUMBERS"}, "a patch names a player, never a device (the glossary)"),
    ("ghost", "hands.core"): ({"SIDES", "PALM_W", "default_range"},
                              "the shape of a hand: constants, read while drawing one"),
    ("loadable", "apc40"): ({"*"}, "an old file's desk rows, spelled as the factory's (`_cc`)"),
    ("dream", "config"): ({"DEFAULTS"}, "the dream's model paths; lazily, on its worker"),
    ("media.live", "devices"): ({"*"}, "a live source is a device kind (`Port`)"),
    ("loadable", "graphview"): ({"*"}, "LISTED, should not cross: a new look's chain, the panel's model"),
    ("render", "poi"): ({"*"}, "LISTED, should not cross: the guide's state, an experiment's"),
    ("render", "poi_guide"): ({"PoiGuide"}, "LISTED, should not cross: drawn over the outputs"),
}
# The meta controller's names inside `BOTH_LAYERS`, and who may import them
META_NAMES = ("SHARED_META_", "PER_DECK_", "META_", "MetaRegistry", "MetaTable", "MetaMarks",
              "DeckProject", "is_shared_meta_", "is_meta_", "is_per_deck_", "meta_", "push_meta",
              "install_meta")
SURFACE_NAMES = {
    "loadable": {"SHARED_META_GROUPS": "which groups a file's values may not hold",
               "is_meta_id": "a route's row goes on to the referee, in its words",
               "meta_row_refusal": "a save filters a row no load would land"},
    "patches": {"meta_refusal": "a patch file naming a meta param is refused (row 744)"},
    "nodemode": {"meta_refusal": "a node's meta params fill no degree of freedom"},
}
# …and the handles at run time. (`Project.session` goes with the shows, in plan 57 §5.)
META_ATTRS = {"meta", "decks", "meta_stack", "push_meta", "players", "session", "meta_reg", "meta_table"}
SURFACE_ATTRS = {
    ("loadable", "project.session"): "seeds a landing group's params from the open show",
    ("dream", "w.meta"): "not ours: a model file's download record",
    ("segment", "w.meta"): "not ours: a model file's download record",
}


def _module_name(f: Path) -> str:
    return str(f.relative_to(PKG))[:-3].replace("/", ".").removesuffix(".__init__")


def _home(mod: str) -> str | None:
    """The classified name `mod` falls under (`media.live` under `media`; `ui_graph`
    under `ui`), or None when it is in no list."""
    head = mod.split(".")[0]
    if head.startswith("ui_"):
        head = "ui"
    every = PATCH_MODULES | META_MODULES | BOTH_LAYERS | ABOVE
    return head if head in every else None


def _modules() -> list[str]:
    return [m for m in map(_module_name, sorted(PKG.rglob("*.py"))) if m != "__init__"]


def _imports(f: Path, mod: str):
    """(module imported, [names]) for each relative import of `f`, lazy ones too; `from . import
    x` is `x`, with "*" as its names, since what is used of it is an attribute."""
    pkg = mod.split(".")[:-1]
    if f.name == "__init__.py":
        pkg = mod.split(".")
    for n in ast.walk(ast.parse(f.read_text())):
        if isinstance(n, ast.ImportFrom) and n.level > 0:
            base = pkg[: len(pkg) - (n.level - 1)]
            if n.module:
                yield ".".join([*base, n.module]), [a.name for a in n.names]
            else:
                for a in n.names:
                    yield ".".join([*base, a.name]), ["*"]


def test_every_module_is_on_the_wall():
    """A new module says which side it is on, or fails here."""
    assert not [m for m in _modules() if _home(m) is None]


def test_no_module_is_on_two_sides():
    sides = (PATCH_MODULES, META_MODULES, BOTH_LAYERS, ABOVE)
    assert sum(map(len, sides)) == len(set().union(*sides))


def _crossings() -> dict[tuple[str, str], set[str]]:
    out: dict[tuple[str, str], set[str]] = {}
    for f in sorted(PKG.rglob("*.py")):
        mod = _module_name(f)
        if _home(mod) not in PATCH_MODULES:
            continue
        for imported, names in _imports(f, mod):
            if _home(imported) in META_MODULES or _home(imported) in ABOVE:
                out.setdefault((mod, imported), set()).update(names)
    return out


def test_a_patch_module_reaches_the_meta_controller_only_through_the_surface():
    """Fails on a crossing not listed, and on a listed one that has gone, so the list
    stays what crosses today. `ABOVE` is walled too: no patch module imports the panel."""
    got = _crossings()
    assert set(got) == set(SURFACE), set(got) ^ set(SURFACE)
    for key, names in got.items():
        allowed, why = SURFACE[key]
        assert why and ("*" in allowed or names <= allowed), (key, names)


def test_a_patch_module_takes_only_the_listed_meta_names_from_a_module_of_both():
    got: dict[str, set[str]] = {}
    for f in sorted(PKG.rglob("*.py")):
        mod = _module_name(f)
        if _home(mod) not in PATCH_MODULES:
            continue
        for imported, names in _imports(f, mod):
            if _home(imported) in BOTH_LAYERS:
                hit = {n for n in names if n.startswith(META_NAMES)}
                if hit:
                    got.setdefault(mod, set()).update(hit)
    assert got == {m: set(names) for m, names in SURFACE_NAMES.items()}


def test_a_patch_module_holds_no_other_handle_on_the_meta_controller():
    """The handles an import does not show: the attribute named, by receiver."""
    got = set()
    for f in sorted(PKG.rglob("*.py")):
        mod = _module_name(f)
        if _home(mod) not in PATCH_MODULES:
            continue
        for n in ast.walk(ast.parse(f.read_text())):
            if isinstance(n, ast.Attribute) and n.attr in META_ATTRS:
                got.add((mod.split(".")[0], ast.unparse(n)))
    assert got == set(SURFACE_ATTRS), got ^ set(SURFACE_ATTRS)
