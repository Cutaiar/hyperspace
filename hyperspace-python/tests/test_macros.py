"""One macro concept (plan 13 D10, §2.4; decision register rows 12, 12b).

A macro is a knob with subscribers: a base subscriber is a scene-setter
that follows the macro's *base* (`Router.follow_macros`), a depth
subscriber scales one route by the macro's *effective* value, last
frame's (`Router.modulate`). Polarity is per subscriber; a performer on
a macro moves its depth subscribers only; `scale: macro.N` migrates to a
depth subscriber and a `scale` on anything else is left alone (register
row 18, open).
"""

import json

import pytest
from conftest import CORPUS
from test_routing import rig

from hyperspace import routing
from hyperspace.routing import Binding, Bindings, Router, bindings_path


def depth_sub(source, target, lo=0.0, hi=1.0):
    return {"depth": {"source": source, "target": target}, "from": lo, "to": hi}


def frame(router, reg):
    """The frame's order from the macros on (app.frame)."""
    router.follow_macros()
    router.modulate()
    reg.apply()


def test_a_new_base_subscriber_runs_from_where_the_param_sits_to_the_end_of_its_fader():
    """Row 537 (the owner, 2026-10-28: "by default when you wire up a
    macro, the From and To parameters start at the same value so there's
    actually no range of motion"): `routing.base_sub` — what a macro's
    cable on GRAPH and ROUTING's "+ base" both add — runs from the param's
    fader position to 1, or to 0 when it already sits at 1; never
    from = to. On the knob the param moves at once."""
    r = rig()
    reg = r.reg
    router = Router(reg, Bindings())
    bright, speed, m = reg["view.bright"], reg["view.speed"], reg["macro.1"]
    bright.set_norm(0.3)
    speed.set_norm(1.0)
    subs = [routing.base_sub(bright), routing.base_sub(speed)]
    assert (subs[0].base, subs[0].lo, subs[0].hi) == ("view.bright", pytest.approx(0.3), 1.0)
    assert (subs[1].base, subs[1].lo, subs[1].hi) == ("view.speed", 1.0, 0.0)
    assert all(s.lo != s.hi for s in subs)
    router.table.macros["macro.1"] = routing.Macro("Test", subs)
    router.table.macros_serial += 1
    for v in (0.0, 0.5, 1.0):
        m.set_norm(v)
        frame(router, reg)
        assert bright.norm == pytest.approx(0.3 + 0.7 * v, abs=1e-9)
        assert speed.norm == pytest.approx(1.0 - v, abs=1e-9)


def test_base_subscribers_of_opposite_polarity_move_opposite_ways():
    r = rig()
    reg = r.reg
    router = Router(reg, Bindings())
    router.table.set_macros({"macro.1": {"label": "Heat", "subs": [
        {"base": "view.bright", "from": 0.0, "to": 0.6},
        {"base": "view.speed", "from": 0.8, "to": 0.3}]}})
    bright, speed, m = reg["view.bright"], reg["view.speed"], reg["macro.1"]
    seen = []
    for v in (0.0, 0.25, 0.5, 1.0):
        m.set_norm(v)
        frame(router, reg)
        seen.append((bright.norm, speed.norm))
        # along each param's own fader, no detent snapping
        assert bright.norm == pytest.approx(0.6 * m.norm, abs=1e-9)
        assert speed.norm == pytest.approx(0.8 - 0.5 * m.norm, abs=1e-9)
    assert [b for b, _ in seen] == sorted(b for b, _ in seen)                  # up …
    assert [s for _, s in seen] == sorted((s for _, s in seen), reverse=True)  # … and down
    # a base moved by hand stays until the macro's base moves again
    speed.set_norm(0.9)
    frame(router, reg)
    assert speed.norm == pytest.approx(0.9)
    assert router.table.macros_doc()["macro.1"]["label"] == "Heat"


def test_a_performer_on_a_macro_moves_only_its_depth_subscribers():
    """Row 12b: a hand owning macro.1 deepens the route its depth
    subscriber names — the same frame, from the macro's effective value
    (plan 28 N0, decision 7: the macro's node runs before the route) —
    and leaves its base subscribers alone; the knob moves those."""
    r = rig()
    reg = r.reg
    table = Bindings([Binding("lfo:0", "view.bright", "push", 0.5),
                      Binding("hand:0", "macro.1", "position")])
    table.set_macros({"macro.1": {"subs": [
        {"base": "view.speed", "from": 0.0, "to": 1.0},
        depth_sub("lfo:0", "view.bright")]}})
    router = Router(reg, table)
    m, bright, speed = reg["macro.1"], reg["view.bright"], reg["view.speed"]
    m.set_norm(0.2)
    bright.set_norm(0.4)
    router.feed("lfo", [1.0])
    router.rests["lfo"] = [0.5]
    router.feed("hand", [0.9])
    frame(router, reg)                           # the set_macros lands the bases
    assert speed.norm == pytest.approx(0.2)
    # this frame the route read the macro after the hand moved it: 0.9
    assert bright.eff_norm - bright.norm == pytest.approx(0.5 * 0.9 * 0.5, abs=1e-6)
    assert m.modulated and m.value == pytest.approx(0.9)
    frame(router, reg)                           # and the next: still 0.9, the hand's
    assert bright.eff_norm - bright.norm == pytest.approx(0.5 * 0.9 * 0.5, abs=1e-6)
    assert speed.norm == pytest.approx(0.2)      # the base subscriber never moved
    # the knob turns the macro's base under the hand: the base subscriber
    # follows it, the depth still rides the hand
    m.set_norm(0.7)
    frame(router, reg)
    assert speed.norm == pytest.approx(0.7)
    assert bright.eff_norm - bright.norm == pytest.approx(0.5 * 0.9 * 0.5, abs=1e-6)


def test_scale_on_a_macro_migrates_to_a_depth_subscriber(tmp_path):
    row = {"source": "lfo:1", "target": "fx.mix", "op": "push", "value": 0.3,
           "scale": "macro.1"}
    # the live file: read, noted, the depth subscriber made
    path = bindings_path(tmp_path)
    v2 = {"schema": routing.SCHEMA_V2, "profile": "apc40", "bindings": [row]}
    path.write_text(json.dumps(v2))
    t = Bindings.load(path, legacy_midi=None)
    assert t.bindings[0].scale is None
    assert t.macros_doc() == {"macro.1": {"subs": [depth_sub("lfo:1", "fx.mix")]}}
    assert any("depth subscriber of macro.1" in n for n in t.notes)
    # the route and its macro are a preset's (plan 13 WP5): the table
    # carries them as one, the same subscriber, the same depth (nothing
    # reads `carried` since the one-tier library of 2026-10-28 retired
    # plan 13 §6's migration; the next write leaves it out)
    made = t.carried
    assert made.macros == t.macros_doc() and "scale" not in json.dumps(made.routes)
    r = rig()
    router = Router(r.reg, Bindings())
    router.table.set_routes(Binding.from_json(d) for d in made.routes)
    router.table.set_macros(made.macros)
    assert router.table.routes()[0].scale is None
    assert router.table.macros_doc()["macro.1"]["subs"] == [depth_sub("lfo:1", "fx.mix")]
    reg, mix = r.reg, r.reg["fx.mix"]
    reg["macro.1"].set_norm(0.5)
    mix.set_norm(0.5)
    router.feed("lfo", [0.0, 1.0])
    router.rests["lfo"] = [0.5, 0.5]
    router.modulate()
    reg.apply()
    assert mix.eff_norm - mix.norm == pytest.approx(0.3 * 0.5 * 0.5, abs=1e-6)  # as × scale did
    # an identical subscriber already there is not doubled
    t2 = Bindings.from_json({"schema": routing.SCHEMA, "bindings": [row],
                             "macros": {"macro.1": {"subs": [depth_sub("lfo:1", "fx.mix")]}}})
    assert len(t2.macros["macro.1"].subs) == 1
    # the corpus's lfo-breathe (what the build shipped): its macro.1 is a subscriber
    lfo_breathe = json.loads((CORPUS / "presets" / "lfo-breathe.json").read_text())
    assert lfo_breathe["macros"]["macro.1"]["subs"][0] == depth_sub("lfo:1", "fx.mix")
    assert "scale" not in json.dumps(lfo_breathe["routes"])


def test_a_scale_on_a_session_param_is_left_alone():
    """Decision register row 18 (a): a route keeps a `scale` that names a
    session param — the drive fader reaches the rotation as `scale:
    master.gain` on the six legacy6 rate rows — and nothing migrates it."""
    row = {"source": "lane:0", "target": "rot.rate.ZW", "op": "push", "value": 0.0625,
           "scale": "master.gain"}
    t = Bindings.from_json({"schema": routing.SCHEMA_V2, "bindings": [row]})
    assert t.bindings[0].scale == "master.gain" and t.macros == {} and not t.changed
    legacy6 = json.loads((CORPUS / "presets" / "legacy6.json").read_text())
    assert sum(b.get("scale") == "master.gain" for b in legacy6["routes"]) == 6
    assert legacy6["macros"] == {}
    assert all(b.scale == "master.gain" for b in routing.legacy6_routes()
               if b.target.startswith("rot.rate."))


def test_a_scale_on_a_performance_param_is_refused_with_a_note(tmp_path):
    """Decision register row 18 (a): a `scale` naming a performance param
    (one a preset load could move under the route) is dropped with a note
    — in the live table and in a preset's load — the depth kept; a macro's
    becomes a depth subscriber and a session param's stays, as before."""
    rows = [{"source": "hand:1", "target": "view.bright", "op": "push", "value": 0.3,
             "scale": "view.speed"},                                  # performance: dropped
            {"source": "lfo:1", "target": "fx.mix", "op": "push", "value": 0.3,
             "scale": "macro.4"},                                     # a macro: a subscriber
            {"source": "lane:0", "target": "rot.rate.ZW", "op": "push", "value": 0.0625,
             "scale": "master.gain"}]                                 # session: kept
    # the live table
    t = Bindings.from_json({"schema": routing.SCHEMA, "bindings": rows})
    assert [b.scale for b in t.bindings] == [None, None, "master.gain"]
    assert t.bindings[0].value == 0.3 and t.changed
    assert any("dropped the scale view.speed of hand:1 → view.bright" in n and "18 (a)" in n
               for n in t.notes)
    assert t.macros_doc() == {"macro.4": {"subs": [depth_sub("lfo:1", "fx.mix")]}}
    # a preset's load
    from test_presets import boot, put
    r = boot(tmp_path)
    put(tmp_path, "SCALED", routes=rows, macros={})
    r.presets.load("SCALED")
    assert [b.scale for b in r.router.table.routes()] == [None, None, "master.gain"]
    assert any("dropped the scale view.speed" in n for n in r.presets.notes)
    assert r.router.table.macros_doc()["macro.4"]["subs"] == [depth_sub("lfo:1", "fx.mix")]
    # the ROUTING page's combo offers session params only
    from types import SimpleNamespace

    from hyperspace import ui_routing
    offered = {q.id for q in ui_routing._scales(SimpleNamespace(reg=r.reg), "rot.rate.ZW")}
    assert "master.gain" in offered and "view.speed" not in offered
    assert not any(pid.startswith("macro.") for pid in offered)
    assert all(routing.is_session_id(pid) for pid in offered)


def test_a_base_subscriber_on_a_session_param_is_dropped_with_a_note(tmp_path):
    """D9, review of PR #67: a base subscriber names a performance param —
    persisted, not an alias — never a session one, so a preset load never
    writes a session base through a macro. `set_macros` drops any other
    with a note (the load's notes, and the migration's); a depth subscriber
    on a route that performs a session param stays (decision 19 (a))."""
    from test_presets import boot, put

    r = boot(tmp_path)
    reg, table = r.reg, r.router.table
    bpm = reg["tempo.bpm"].value
    real = reg.real(reg["band.sel.trim"])
    trim = real.value
    macros = {"macro.1": {"label": "Mixed", "subs": [
        {"base": "tempo.bpm", "from": 1.0, "to": 1.0},               # session: dropped
        {"base": "band.sel.trim", "from": 1.0, "to": 1.0},           # an alias: dropped
        {"base": "view.bright", "from": 0.0, "to": 0.6},             # performance: kept
        depth_sub("hand:1", "master.gain", 0.0, 1.0)]}}              # a depth: kept
    routes = [{"source": "hand:1", "target": "master.gain", "op": "push", "value": 0.3}]
    put(tmp_path, "MIXED", routes=routes, macros=macros, values={"macro.1": 0.5})
    r.presets.load("MIXED")
    assert reg["tempo.bpm"].value == pytest.approx(bpm)              # never written
    assert real.value == pytest.approx(trim)
    assert reg["view.bright"].norm == pytest.approx(0.3, abs=1e-6)
    assert table.macros_doc()["macro.1"] == {"label": "Mixed", "subs": [
        {"base": "view.bright", "from": 0.0, "to": 0.6},
        depth_sub("hand:1", "master.gain")]}
    notes = r.presets.notes
    assert any("macro.1's base subscriber tempo.bpm" in n and "D9" in n for n in notes)
    assert any("macro.1's base subscriber band.sel.trim" in n for n in notes)
    # set_macros on its own: the same rule, by group prefix with no registry
    got = Bindings().set_macros({"macro.2": {"subs": [{"base": "master.gain"},
                                                       {"base": "fx.mix"}]}})
    assert len(got) == 1 and "master.gain" in got[0]


def test_a_depth_range_crossing_zero_flips_the_route():
    r = rig()
    reg = r.reg
    table = Bindings([Binding("lfo:0", "view.bright", "push", 0.4)])
    table.set_macros({"macro.3": {"subs": [depth_sub("lfo:0", "view.bright", -1.0, 1.0)]}})
    router = Router(reg, table)
    bright, m = reg["view.bright"], reg["macro.3"]
    bright.set_norm(0.5)
    router.feed("lfo", [1.0])
    router.rests["lfo"] = [0.5]
    offsets = []
    for v in (0.0, 0.5, 1.0):
        m.set_norm(v)
        frame(router, reg)
        offsets.append(bright.eff_norm - bright.norm)
    assert offsets[0] == pytest.approx(-0.4 * 0.5, abs=1e-6)     # full throw down
    assert offsets[1] == pytest.approx(0.0, abs=1e-6)            # the zero crossing
    assert offsets[2] == pytest.approx(0.4 * 0.5, abs=1e-6)      # full throw up


def test_a_depth_subscriber_follows_its_route_when_the_row_moves():
    """Review of PR #63: a subscriber names its route by (source, target),
    so re-pointing the row carries it along and removing the row drops it."""
    table = Bindings([Binding("lfo:1", "fx.mix", "push", 0.3)])
    table.set_macros({"macro.1": {"subs": [depth_sub("lfo:1", "fx.mix")]}})
    b = table.bindings[0]
    table.move_route(b, source="lfo:0")
    assert [s.depth for _, s in table.depth_subs(b)] == [("lfo:0", "fx.mix")]
    table.move_route(b, target="view.bright")
    assert table.macros["macro.1"].subs[0].depth == ("lfo:0", "view.bright")
    table.remove(b)
    assert table.macros_doc() == {}
