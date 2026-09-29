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
    subscriber names — a frame later, from the macro's effective value —
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
    # this frame the route read the macro before the hand moved it: 0.2
    assert bright.eff_norm - bright.norm == pytest.approx(0.5 * 0.2 * 0.5, abs=1e-6)
    assert m.modulated and m.value == pytest.approx(0.9)
    frame(router, reg)                           # next frame: 0.9, the hand's
    assert bright.eff_norm - bright.norm == pytest.approx(0.5 * 0.9 * 0.5, abs=1e-6)
    assert speed.norm == pytest.approx(0.2)      # the base subscriber never moved
    # the knob turns the macro's base under the hand: the base subscriber
    # follows it, the depth still rides the hand
    m.set_norm(0.7)
    frame(router, reg)
    assert speed.norm == pytest.approx(0.7)
    assert bright.eff_norm - bright.norm == pytest.approx(0.5 * 0.9 * 0.5, abs=1e-6)


def test_scale_on_a_macro_migrates_to_a_depth_subscriber(tmp_path, capsys):
    row = {"source": "lfo:1", "target": "fx.mix", "op": "push", "value": 0.3,
           "scale": "macro.1"}
    # the live file: moved, noted, backed up and written back once
    path = bindings_path(tmp_path)
    v2 = {"schema": routing.SCHEMA_V2, "profile": "apc40", "bindings": [row]}
    path.write_text(json.dumps(v2))
    t = Bindings.load(path, legacy_midi=None)
    assert t.bindings[0].scale is None
    assert t.macros_doc() == {"macro.1": {"subs": [depth_sub("lfo:1", "fx.mix")]}}
    assert any("depth subscriber of macro.1" in n for n in t.notes)
    assert "kept as bindings.json.bak-v2" in capsys.readouterr().err
    doc = json.loads(path.read_text())
    assert doc["macros"] == t.macros_doc() and "scale" not in json.dumps(doc["bindings"])
    again = Bindings.load(path, legacy_midi=None)
    assert again.to_json() == t.to_json() and not again.changed
    # a routing preset: through apply_doc, the same subscriber, the same depth
    r = rig()
    router = Router(r.reg, Bindings())
    router.apply_doc({"schema": routing.SCHEMA_V2, "bindings": [row]})
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
    # the factory file is regenerated: lfo-breathe's macro.1 is a subscriber
    lfo_breathe = json.loads((routing.FACTORY_DIR / "lfo-breathe.json").read_text())
    assert lfo_breathe["macros"]["macro.1"]["subs"] == [depth_sub("lfo:1", "fx.mix")]
    assert "scale" not in json.dumps(lfo_breathe["bindings"])


def test_a_scale_on_a_session_param_is_left_alone():
    """Decision register row 18 is open: the drive fader reaches the
    rotation as `scale: master.gain`, and nothing migrates it."""
    row = {"source": "lane:0", "target": "rot.rate.ZW", "op": "push", "value": 0.0625,
           "scale": "master.gain"}
    t = Bindings.from_json({"schema": routing.SCHEMA_V2, "bindings": [row]})
    assert t.bindings[0].scale == "master.gain" and t.macros == {} and not t.changed
    legacy6 = json.loads((routing.FACTORY_DIR / "legacy6.json").read_text())
    assert sum(b.get("scale") == "master.gain" for b in legacy6["bindings"]) == 6
    assert "macros" not in legacy6
    assert all(b.scale == "master.gain" for b in routing.legacy6_routes()
               if b.target.startswith("rot.rate."))


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
