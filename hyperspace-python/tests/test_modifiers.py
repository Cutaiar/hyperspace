"""Plan 28 N1 — modifier nodes, in the preset.

A modifier (`modifiers.Modifier`) reads one or two source lanes, has a few
params of its own (``mod.<n>.<p>``, group ``mod``, performance and
modulatable), and publishes one output lane, ``mod:<n>``, which a route
reads like any source. The preset holds them (``modifiers`` after
``routes``; decision 8); `bindings.json` never does. A desk template may
carry them, a preset's own overriding by id. ROUTING's MODIFIERS strip
builds them.

Each kind is proven on a scripted input; then the lane a route can
source, the preset / bindings split, a route onto a missing modifier, the
template override, the strip building "right hand energy, smoothed, times
band 0, into acid mix" through the page's own functions, an older preset
without the key, undo, and Learn. The presets are fixtures under
tests/fixtures/modifiers/, loaded through a scratch library; no preset in
hyperspace/library/ is touched.
"""

import json
import math
import shutil
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pytest
from imgui_bundle import imgui
from test_presets import boot
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture

from hyperspace import modifiers as M
from hyperspace import routing, ui_routing, undo
from hyperspace.bands import CEIL
from hyperspace.learn import Learn
from hyperspace.library import DESK
from hyperspace.modifiers import Modifier, ModState, step
from hyperspace.params import PERFORMANCE_GROUPS, part_of
from hyperspace.preset import MODIFIERS_KEY
from hyperspace.routing import Binding, Bindings, Router

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "modifiers"
DT = 1 / 60


def run(m: Modifier, xs, dt: float = DT, state: ModState | None = None) -> list[float]:
    """`m` stepped over a scripted input (one reading a frame; a pair per
    frame for a two-input kind)."""
    st = ModState() if state is None else state
    return [step(m, x if isinstance(x, tuple) else (x,), st, dt) for x in xs]


# ---------------------------------------------------------------- the kinds

def test_the_kinds_their_inputs_and_their_params():
    assert M.KINDS == ("curve", "scale", "smooth", "combine", "threshold", "delay")
    assert {k: [s.key for s in M.PARAMS[k]] for k in M.KINDS} == {
        "curve": ["shape", "invert"], "scale": ["mul", "offset", "clamp"],
        "smooth": ["attack", "release", "spring"], "combine": ["how", "balance"],
        "threshold": ["on", "off", "hold"], "delay": []}
    assert M.INPUTS["combine"] == 2 and all(M.INPUTS[k] == 1 for k in M.KINDS
                                            if k != "combine")
    assert Modifier("mod.1", "threshold").out == "trigger"
    assert {Modifier("mod.1", k).out for k in M.KINDS if k != "threshold"} == {"value"}
    with pytest.raises(ValueError):
        Modifier("mod.1", "wobble")
    with pytest.raises(ValueError):
        Modifier("fx.1", "curve")


def test_curve_is_linear_at_zero_bends_both_ways_and_inverts():
    xs = [0.0, 0.25, 0.5, 1.0]
    assert run(Modifier("mod.1", "curve"), xs) == xs
    slow = run(Modifier("mod.1", "curve", params={"shape": 1.0}), xs)
    assert slow == pytest.approx([0.0, 0.25 ** 4, 0.5 ** 4, 1.0])
    fast = run(Modifier("mod.1", "curve", params={"shape": -1.0}), xs)
    assert fast == pytest.approx([0.0, 0.25 ** 0.25, 0.5 ** 0.25, 1.0])
    inv = run(Modifier("mod.1", "curve", params={"invert": 1.0}), xs)
    assert inv == pytest.approx([1.0, 0.75, 0.5, 0.0])


def test_scale_multiplies_offsets_and_clamps_unless_told_not_to():
    m = Modifier("mod.1", "scale", params={"mul": 2.0, "offset": -0.25})
    assert run(m, [0.0, 0.25, 0.5, 1.0]) == [0.0, 0.25, 0.75, 1.0]
    m.params["clamp"] = 0.0
    assert run(m, [0.0, 1.0]) == [-0.25, 1.75]


def test_smooth_follows_with_its_attack_and_release():
    """A step up rises at the attack's time constant, a step down falls
    at the release's — `motion.follow` about 0; the first reading is
    taken as it is (no glide in from nothing)."""
    m = Modifier("mod.1", "smooth", params={"attack": 0.1, "release": 0.5})
    st = ModState()
    assert run(m, [0.0], state=st) == [0.0]
    up = run(m, [1.0] * 6, dt=0.1 / 6, state=st)      # one attack: 63 %
    assert up[-1] == pytest.approx(1 - math.exp(-1.0))
    top = up[-1]
    down = run(m, [0.0] * 30, dt=0.5 / 30, state=st)  # one release
    assert down[-1] == pytest.approx(top * math.exp(-1.0))
    # a zero attack arrives at once
    assert run(Modifier("mod.2", "smooth", params={"attack": 0.0}), [0.0, 1.0]) == [0.0, 1.0]


def test_smooth_with_spring_on_overshoots_and_settles():
    m = Modifier("mod.1", "smooth", params={"attack": 0.05, "spring": 1.0})
    ys = run(m, [0.0] + [1.0] * 240)
    assert max(ys) > 1.0                                 # it rings past the reading
    assert ys[-1] == pytest.approx(1.0, abs=1e-3)


def test_combine_mul_and_cross():
    def how(name, **kw):
        return Modifier("mod.1", "combine", params={"how": M.HOW.index(name), **kw})
    pairs = [(0.5, 0.5), (1.0, 0.25), (0.2, 0.8)]
    assert run(how("mul"), pairs) == pytest.approx([0.25, 0.25, 0.16])
    assert run(how("add"), pairs) == pytest.approx([1.0, 1.25, 1.0])
    assert run(how("min"), pairs) == [0.5, 0.25, 0.2]
    assert run(how("max"), pairs) == [0.5, 1.0, 0.8]
    assert run(how("cross", balance=0.0), pairs) == [0.5, 1.0, 0.2]
    assert run(how("cross", balance=1.0), pairs) == [0.5, 0.25, 0.8]
    assert run(how("cross", balance=0.25), [(0.0, 1.0)]) == [0.25]


def test_threshold_fires_once_on_the_rising_edge_and_holds():
    """1 on the rising edge through `on` for `hold` seconds, then 0; it
    fires again only after falling under `off` (the hysteresis)."""
    m = Modifier("mod.1", "threshold", params={"on": 0.6, "off": 0.4, "hold": 0.5})
    xs = [0.0, 0.7, 0.9, 0.8, 0.7, 0.5, 0.7, 0.3, 0.7, 0.7]
    #     rest edge  held held  0   above off  under  edge held
    assert run(m, xs, dt=0.25) == [0, 1, 1, 0, 0, 0, 0, 0, 1, 1]
    # a hold of 0: the edge's frame only
    m0 = Modifier("mod.2", "threshold", params={"hold": 0.0})
    assert run(m0, [0.0, 1.0, 1.0, 0.0, 1.0]) == [0, 1, 0, 0, 1]


def test_delay_is_one_frame_late():
    assert run(Modifier("mod.1", "delay"), [0.3, 0.6, 0.9, 0.1]) == [0.0, 0.3, 0.6, 0.9]


def test_the_entry_round_trips_and_names_its_enums_and_toggles():
    d = {"id": "mod.2", "kind": "combine", "in": ["mod:1", "lane:0"], "how": "mul"}
    m = Modifier.from_json(d)
    assert m.params == {"how": 1.0, "balance": 0.5}
    assert m.to_json() == {**d, "balance": 0.5}
    assert Modifier.from_json(m.to_json()).to_json() == m.to_json()
    s = Modifier.from_json({"id": "mod.4", "kind": "scale", "in": "lane:1", "clamp": False})
    assert s.inputs == ("lane:1",) and s.to_json()["clamp"] is False
    assert Modifier.from_json({"id": "mod.5", "kind": "combine"}).to_json()["in"] == [None, None]
    with pytest.raises(ValueError):
        Modifier.from_json({"id": "mod.6", "kind": "combine", "how": "divide"})


def test_ids_follow_the_naming_rule():
    assert M.next_id([]) == "mod.1"
    assert M.next_id(["mod.1", "mod.4"]) == "mod.5"
    assert M.id_of("mod:3") == "mod.3" and M.id_of("lane:3") is None
    assert M.number("mod.03") is None and M.number("mod.0") is None


# ---------------------------------------------------------------- the router

@pytest.fixture()
def rig(tmp_path):
    return boot(tmp_path)


def hands(router, energy: float | None) -> None:
    """A hands device's feed, as far as the right hand's energy goes."""
    if "hand" not in router.names:
        router.names["hand"] = {"right.energy": 0}
        router.labels["hand"] = ["R energy"]
    router.feed("hand", None if energy is None else [energy])


def analyzer(band0: float) -> NS:
    return NS(lanes=np.array([band0 * CEIL, 0.0, 0.0]))


def test_the_mod_group_is_performance_and_its_params_come_and_go(rig):
    reg, table = rig.reg, rig.router.table
    assert PERFORMANCE_GROUPS[-1] == "mod"
    m = table.add_modifier("smooth", ["hand:right.energy"], reg, release=0.6)
    assert m.id == "mod.1"
    ids = [p.id for p in reg.group("mod")]
    assert ids == ["mod.1.attack", "mod.1.release", "mod.1.spring"]
    p = reg["mod.1.release"]
    assert part_of(p) == "performance" and p.modulatable and p.value == 0.6
    p.set(1.2)
    assert table.modifier("mod.1").params["release"] == 1.2
    table.add_modifier("combine", (), reg)
    assert [p.id for p in reg.group("mod")][3:] == ["mod.2.how", "mod.2.balance"]
    assert reg["mod.1.release"].value == 1.2                 # the first kept its value
    table.remove_modifier("mod.1", reg)
    assert [p.id for p in reg.group("mod")] == ["mod.2.how", "mod.2.balance"]
    assert table.add_modifier("delay").id == "mod.3"        # one past the highest


def test_a_modifier_publishes_a_lane_a_route_can_source(rig):
    reg, router = rig.reg, rig.router
    table = router.table
    table.add_modifier("scale", ["lane:0"], reg, mul=2.0)
    table.add(Binding("mod:1", "view.bright", "position", 1.0))
    p = reg["view.bright"]
    router.modulate(analyzer(0.2))
    reg.apply()
    assert router.feeds["mod"][1] == pytest.approx(0.4)
    assert router.labels["mod"] == ["", "1 scale"] and router.rests["mod"] == [0.0, 0.0]
    assert router.lane_kinds["mod"] == ["value", "value"]
    assert "mod" in router.schemes()
    assert p.modulated and p.eff_norm == pytest.approx(0.4)
    assert router.describe(table.owner("view.bright")) == "1 scale positions"
    # its input not live: the node is dormant, the route lets go
    router.modulate(None)
    reg.apply()
    assert math.isnan(router.feeds["mod"][1]) and not p.modulated
    # the last modifier gone: the scheme is not offered at all
    table.remove_modifier("mod.1", reg)
    router.modulate(None)
    assert "mod" not in router.feeds and "mod" not in router.schemes()


def test_a_threshold_lane_is_a_trigger_and_a_gate(rig):
    reg, router = rig.reg, rig.router
    router.table.add_modifier("threshold", ["lane:0"], reg)
    router.modulate(analyzer(0.0))
    assert router.lane_kinds["mod"][1] == "trigger"
    assert router.gates["mod"] == [(1, "mod 1 threshold")]
    b = Binding("lane:1", "view.speed", "push", 0.5, when="mod:1")
    assert not router.gated(b)
    router.modulate(analyzer(0.9))
    assert router.feeds["mod"][1] == 1.0 and router.gated(b)


def test_a_modifier_reads_another_the_same_frame_whatever_its_id(rig):
    """In dependency order (plan 28 N0, decision 7; this pinned the id-order
    lag before): a modifier reading another — a lower id or a higher one —
    reads its output this frame."""
    reg, router = rig.reg, rig.router
    table = router.table
    table.add_modifier("scale", ["lane:0"], reg)              # mod.1 = band 0
    table.add_modifier("scale", ["mod:1"], reg, mul=0.5)      # mod.2 = mod.1 / 2
    table.add_modifier("scale", ["mod:4"], reg)               # mod.3 = mod.4, now
    table.add_modifier("scale", ["lane:0"], reg)              # mod.4 = band 0
    router.modulate(analyzer(0.4))
    vec = router.feeds["mod"]
    assert vec[1] == pytest.approx(0.4) and vec[2] == pytest.approx(0.2)
    assert vec[3] == pytest.approx(0.4)                       # mod.4 stepped first
    router.modulate(analyzer(0.8))
    assert router.feeds["mod"][3] == pytest.approx(0.8)


def test_a_modifiers_param_is_modulatable_by_a_route(rig):
    """A hand can drive a smooth's release: `mod.<n>.<p>` is a target."""
    reg, router = rig.reg, rig.router
    table = router.table
    table.add_modifier("scale", ["lane:0"], reg)
    table.add(Binding("lane:1", "mod.1.mul", "position", 1.0))
    router.modulate(NS(lanes=np.array([0.5 * CEIL, 0.5 * CEIL])))
    reg.apply()
    p = reg["mod.1.mul"]
    assert p.modulated and p.value == pytest.approx(0.0)      # the middle of −4…4
    assert table.modifiers_doc(reg)[0]["mul"] == 1.0           # the file keeps the base


# ---------------------------------------------------------------- the preset

def put(lib, *names: str, desk: str | None = None) -> None:
    (lib.home / "presets").mkdir(parents=True, exist_ok=True)
    for n in names:
        shutil.copy(FIXTURES / "presets" / f"{n}.json", lib.home / "presets" / f"{n}.json")
    if desk:
        (lib.home / DESK).mkdir(parents=True, exist_ok=True)
        shutil.copy(FIXTURES / "desk" / f"{desk}.json", lib.home / DESK / f"{desk}.json")


def test_modifiers_live_in_the_preset_and_never_in_bindings_json(rig):
    lib, reg, router, presets = rig.lib, rig.reg, rig.router, rig.presets
    table = router.table
    put(lib, "mod-energy")
    assert presets.load("mod-energy") == [] and presets.notes == []
    assert [m.id for m in table.modifiers] == ["mod.1", "mod.2"]
    assert reg["mod.1.release"].value == 0.6 and reg["mod.2.how"].value == 1
    # the session file: rows only — no modifier, no `mod.*` id anywhere
    text = json.dumps(table.to_json())
    assert "modifiers" not in table.to_json() and "mod." not in text and "mod:" not in text
    table.write()
    assert "mod" not in routing.bindings_path(lib.home).read_text().replace("mode", "")
    # the preset: the list after the routes, the params in their entries only
    doc = presets.document("MOD ENERGY")
    keys = list(doc)
    assert keys.index(MODIFIERS_KEY) == keys.index("routes") + 1
    want = json.loads((FIXTURES / "presets" / "mod-energy.json").read_text())[MODIFIERS_KEY]
    assert doc[MODIFIERS_KEY] == [Modifier.from_json(d).to_json() for d in want]
    assert not any(k.startswith("mod.") for k in doc["values"])   # loads on an older build
    assert not lib.is_dirty("presets")
    # an edit is the preset's: its dirty dot
    reg["mod.1.release"].set(1.0)
    assert lib.is_dirty("presets")
    assert presets.document("X")[MODIFIERS_KEY][0]["release"] == 1.0
    # a save, reloaded, is the same preset
    presets.save_as("MOD ENERGY 2")
    reg["mod.1.release"].set(0.2)
    presets.load("MOD ENERGY 2")
    assert reg["mod.1.release"].value == 1.0 and presets.notes == []
    # another preset with none: every modifier and its params gone
    put(lib, "mod-missing")
    presets.load("mod-missing")
    assert [m.kind for m in table.modifiers] == ["curve"] and "mod.1.release" not in reg


def test_a_route_onto_a_missing_modifier_is_dropped_with_a_note(rig):
    lib, presets, table = rig.lib, rig.presets, rig.router.table
    put(lib, "mod-missing")
    presets.load("mod-missing")
    assert [(b.source, b.target) for b in table.routes()] == [("mod:1", "view.speed")]
    assert presets.notes == ["dropped mod:3 → view.bright: no modifier mod.3"]
    # the file is left as it is
    assert len(json.loads((lib.home / "presets" / "mod-missing.json").read_text())["routes"]) == 2


def test_a_modifier_whose_input_the_rig_lacks_is_dormant(rig):
    """A hand the rig never feeds: the modifier stays, its lane is not
    live, the route on it moves nothing, and nothing is noted."""
    lib, reg, router, presets = rig.lib, rig.reg, rig.router, rig.presets
    put(lib, "mod-energy")
    presets.load("mod-energy")
    base = reg["fx.acid.mix"].norm
    for _ in range(3):
        router.modulate(analyzer(0.9))
        reg.apply()
    assert math.isnan(router.feeds["mod"][1]) and math.isnan(router.feeds["mod"][2])
    assert not reg["fx.acid.mix"].modulated and reg["fx.acid.mix"].norm == base
    assert [m.id for m in router.table.modifiers] == ["mod.1", "mod.2"]


def test_a_template_may_carry_modifiers_and_a_preset_overrides_by_id(rig):
    lib, reg, presets, table = rig.lib, rig.reg, rig.presets, rig.router.table
    put(lib, "mod-templated", desk="mod-rig")
    assert presets.load("mod-templated") == [] and presets.notes == []
    # the template's mod.1 overridden by the preset's (release 1.5), its
    # mod.3 kept, the preset's own mod.2 added; in id order
    assert [(m.id, m.kind) for m in table.modifiers] == [
        ("mod.1", "smooth"), ("mod.2", "scale"), ("mod.3", "threshold")]
    assert reg["mod.1.release"].value == 1.5 and reg["mod.3.hold"].value == 0.25
    # a save writes only what differs from the template's
    doc = presets.document("MOD TEMPLATED")
    assert [d["id"] for d in doc[MODIFIERS_KEY]] == ["mod.1", "mod.2"]
    # the preset's override taken back to the template's: not written at all
    reg["mod.1.release"].set(0.6)
    assert [d["id"] for d in presets.document("X")[MODIFIERS_KEY]] == ["mod.2"]
    # a fix to the template reaches the preset at its next load
    path = lib.home / DESK / "mod-rig.json"
    tdoc = json.loads(path.read_text())
    tdoc[MODIFIERS_KEY][1]["hold"] = 0.5
    path.write_text(json.dumps(tdoc))
    lib.poll(now=1e9)
    presets.load("mod-templated")
    assert reg["mod.3.hold"].value == 0.5


def test_an_older_preset_without_the_key_loads_as_before(rig):
    """Every factory preset has no `modifiers`: it loads with no note,
    holds none, and saves without the key — the same document as the
    base build's (no `mod.*` id among its values)."""
    lib, presets, table = rig.lib, rig.presets, rig.router.table
    for name in ("party-tumble", "lfo-breathe", "legacy6"):
        presets.load(name)
        assert presets.notes == [] and table.modifiers == ()
        doc = presets.document(name)
        assert MODIFIERS_KEY not in doc
        assert not any(k.startswith("mod.") for k in doc["values"])
        assert not lib.is_dirty("presets")
    # a modifier left by the last preset goes with any load
    put(lib, "mod-energy")
    presets.load("mod-energy")
    presets.load("party-tumble")
    assert table.modifiers == () and not rig.reg.group("mod")
    rig.router.modulate()
    assert "mod" not in rig.router.schemes()


def test_a_bad_modifier_entry_is_a_note_and_the_rest_load(rig):
    lib, presets, table = rig.lib, rig.presets, rig.router.table
    (lib.home / "presets").mkdir(parents=True, exist_ok=True)
    doc = json.loads((FIXTURES / "presets" / "mod-energy.json").read_text())
    doc["name"] = "MOD BAD"
    doc[MODIFIERS_KEY] = [{"id": "mod.1", "kind": "wobble"}, *doc[MODIFIERS_KEY][1:], "junk"]
    (lib.home / "presets" / "mod-bad.json").write_text(json.dumps(doc))
    presets.load("mod-bad")
    assert [m.id for m in table.modifiers] == ["mod.2"]
    assert any("wobble" in n for n in presets.notes)
    assert any("not an object" in n for n in presets.notes)


# ---------------------------------------------------------------- undo, learn

def test_adding_and_editing_a_modifier_are_undo_steps(rig):
    reg, table = rig.reg, rig.router.table
    u = undo.Undo(reg, table)
    table.add_modifier("smooth", ["lane:0"], reg)
    u.tick(1.0)
    u.tick(2.0)                                     # quiet: the step closes
    reg["mod.1.release"].set(1.0)
    u.tick(3.0)
    u.tick(4.0)
    assert len(u.stack) == 2
    assert u.undo() and reg["mod.1.release"].value == 0.35
    assert u.undo() and table.modifiers == () and not reg.group("mod")
    assert u.redo() and [m.kind for m in table.modifiers] == ["smooth"]


def test_learn_takes_a_mod_lane_as_a_continuous_source(rig):
    reg, table = rig.reg, rig.router.table
    learn = Learn(reg, table)
    learn.arm("view.bright")
    assert learn.accepts("mod:1")
    learn.learn_source("mod:1")
    assert table.owner("view.bright").source == "mod:1"
    learn.arm("view.speed", "desk")
    assert not learn.accepts("mod:1")


# ---------------------------------------------------------------- ROUTING

def panel_of(rig) -> NS:
    """What ROUTING's functions read off the panel."""
    return NS(reg=rig.reg, router=rig.router, midi=None, control=rig.control,
              audio=NS(chain=rig.chain, on=True))


def test_the_routing_page_builds_the_smoothed_energy_times_band_patch(rig):
    """"Right hand energy, smoothed, times band 0, into acid mix", from the
    MODIFIERS strip and the route list alone — and saved, it is the
    fixture's preset."""
    reg, router, presets = rig.reg, rig.router, rig.presets
    panel = panel_of(rig)
    router.table.set_routes([])                 # a preset with no routes yet
    hands(router, 0.0)
    offered = dict(ui_routing.modifier_sources(panel, router))
    assert "hand:right.energy" in offered and "lane:0" in offered
    smooth = ui_routing.add_modifier(panel, "smooth")
    ui_routing.set_modifier_input(panel, smooth.id, 0, "hand:right.energy")
    reg[f"{smooth.id}.release"].set(0.6)
    combine = ui_routing.add_modifier(panel, "combine")
    srcs = dict(ui_routing.modifier_sources(panel, router, combine.id))
    assert srcs["mod:1"] == "mod 1 smooth" and "mod:2" not in srcs   # never itself
    ui_routing.set_modifier_input(panel, combine.id, 0, "mod:1")
    ui_routing.set_modifier_input(panel, combine.id, 1, "lane:0")
    reg[f"{combine.id}.how"].set(M.HOW.index("mul"))
    router.modulate(analyzer(0.5))
    # the route list's source combo offers the modifier's lane
    assert dict(ui_routing._sources(panel, router))["mod:2"] == "mod 2 combine"
    b = ui_routing.add_route(panel, "fx.acid.mix", source="mod:2", depth=1.0, op="position")
    assert b is not None and router.table.owner("fx.acid.mix") is b
    # play it: the hand goes to full energy, band 0 at a half
    p = reg["fx.acid.mix"]
    seen = []
    for _ in range(30):
        hands(router, 1.0)
        router.modulate(analyzer(0.5), dt=DT)
        reg.apply()
        seen.append(p.eff_norm)
    smoothed = 1 - math.exp(-30 * DT / 0.05)
    assert seen[-1] == pytest.approx(0.5 * smoothed, abs=1e-3)
    assert seen == sorted(seen)                                  # it rose, smoothed
    assert ui_routing.modifier_output(router, "mod.2") == pytest.approx(seen[-1], abs=1e-6)
    # the hand leaves: the node is dormant and the acid's mix comes home
    hands(router, None)
    router.modulate(analyzer(0.5))
    reg.apply()
    assert ui_routing.modifier_output(router, "mod.2") is None and not p.modulated
    # saved, it is the fixture: the same modifiers, the same route
    doc = presets.document("MOD ENERGY")
    fix = json.loads((FIXTURES / "presets" / "mod-energy.json").read_text())
    assert doc[MODIFIERS_KEY] == [Modifier.from_json(d).to_json() for d in fix[MODIFIERS_KEY]]
    assert doc["routes"] == [Binding.from_json(r).to_json() for r in fix["routes"]]
    # the strip's × takes one away; the route on it stays, dormant
    ui_routing.remove_modifier(panel, "mod.2")
    assert [m.id for m in router.table.modifiers] == ["mod.1"]
    assert router.table.owner("fx.acid.mix") is b
    assert ui_routing.matches(panel, router, "smooth", *ui_routing.mod_hay(
        panel, router, router.table.modifier("mod.1")))


def test_the_modifiers_strip_draws_between_the_routes_and_the_desk(shell_rig, tmp_path,  # noqa: F811
                                                                   monkeypatch):
    """The strip on the real page: its title after the routes' and before
    the desk's, each modifier's kind, its live output, its params as the
    panel's own widgets — and every widget its own imgui id."""
    panel, reg = shell_rig.panel, shell_rig.reg
    table = Bindings.factory(path=routing.bindings_path(tmp_path))
    router = panel.router = Router(reg, table)
    ui_routing.add_modifier(panel, "smooth", ["lane:0"])
    ui_routing.add_modifier(panel, "combine", ["mod:1", "lane:1"])
    ui_routing.add_modifier(panel, "threshold", ["hand:9"])           # never fed: dormant
    router.modulate(NS(lanes=np.array([0.5 * CEIL, 0.5 * CEIL])))
    texts: list[str] = []
    ids: list[int] = []
    real_tc = imgui.text_colored
    real_td = imgui.text_disabled
    monkeypatch.setattr(imgui, "text_colored",
                        lambda c, s: (texts.append(s), real_tc(c, s))[1])
    monkeypatch.setattr(imgui, "text_disabled", lambda s: (texts.append(s), real_td(s))[1])
    for fn in ("button", "checkbox", "slider_float", "slider_int", "begin_combo"):
        real = getattr(imgui, fn)

        def rec(label, *a, _real=real, **k):
            ids.append(imgui.get_id(label))
            return _real(label, *a, **k)
        monkeypatch.setattr(imgui, fn, rec)
    frame(panel, "routing")
    texts.clear()
    ids.clear()
    frame(panel)
    assert texts.index("ROUTES") < texts.index("MODIFIERS") < texts.index("DESK  ·  PRESET LAYER")
    assert {"smooth", "combine", "threshold", "0.50", "1.00", "dormant"} <= set(texts)
    dup = {i for i in ids if ids.count(i) > 1}
    assert not dup, f"conflicting ids {sorted(dup)}"


def test_a_non_finite_output_drops_the_memory_and_the_next_reading_starts_afresh(rig):
    """A smooth fed ±inf once: its lane is not live that frame, and its
    follower is dropped, so the next finite reading is taken as it is —
    never NaN for ever after."""
    reg, router = rig.reg, rig.router
    router.table.add_modifier("smooth", ["ext:0"], reg)
    router.feed("ext", [0.2])
    router.modulate()
    assert router.feeds["mod"][1] == pytest.approx(0.2)
    router.feed("ext", [math.inf])
    router.modulate()
    assert math.isnan(router.feeds["mod"][1]) and "mod.1" not in router._mod_states
    router.feed("ext", [0.7])
    router.modulate()
    assert router.feeds["mod"][1] == pytest.approx(0.7)


def test_picking_an_input_replaces_the_modifier_whole_as_one_undo_step(rig):
    reg, table = rig.reg, rig.router.table
    panel = panel_of(rig)
    u = undo.Undo(reg, table)
    undo.install(u)
    try:
        m = ui_routing.add_modifier(panel, "scale", ["lane:0"], mul=2.0)
        u.tick(1.0)
        u.tick(2.0)
        ui_routing.set_modifier_input(panel, m.id, 0, "lane:1")
        u.tick(3.0)
        u.tick(4.0)
        new = table.modifier(m.id)
        assert new is not m and new.inputs == ("lane:1",) and m.inputs == ("lane:0",)
        assert reg[f"{m.id}.mul"].value == 2.0                    # its params kept
        assert len(u.stack) == 2 and u.stack[-1].label.startswith("modifier input")
        assert u.undo() and table.modifier(m.id).inputs == ("lane:0",)
    finally:
        undo.install(None)
