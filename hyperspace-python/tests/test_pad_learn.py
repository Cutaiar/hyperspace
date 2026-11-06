"""The gamepad as a mappable controller: Learn pad (a button, the D-pad, a
stick or a trigger completes it), momentary / hold rows on pad buttons,
and the axes as the `axis` lanes a route can read."""

import json
from types import SimpleNamespace as NS

import pytest

import hyperspace.gamepad as gp
from hyperspace import apc40, midi, routing, tempo, totem
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.learn import PUSH_DEPTH, Learn
from hyperspace.library import Library
from hyperspace.pads.models import MODELS
from hyperspace.params import CHASE_PARAM, build_registry
from hyperspace.render import ViewState
from hyperspace.routing import Binding, Bindings, Router


class ScriptedPad(gp.Pad):
    """A real Pad whose frames are scripted: `frame` sets what is held now."""

    def __init__(self):
        super().__init__()
        self.source = "usb"

    def frame(self, held=(), hat=0, axes=None) -> None:
        self.prev_buttons, self.prev_hat = self.buttons, self.hat
        self.buttons = [1 if i in held else 0 for i in range(gp.N_BUTTONS)]
        self.hat = hat
        self.axes = list(axes) if axes is not None else [0.0, 0.0, 0.0, 0.0, -1.0, -1.0]


@pytest.fixture()
def rig(tmp_path):
    chain = Analyzer(Analyser())
    control = Control(chain)
    lib = Library(tmp_path)
    reg = build_registry(ViewState(), control, NS(chain=chain), lib.project)
    table = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)
    router = Router(reg, table)
    return NS(reg=reg, table=table, router=router, path=tmp_path / "bindings.json",
              learn=Learn(reg, table, lane=router.lane))


def on_file(path) -> list[dict]:
    return json.loads(path.read_text())["bindings"]


# ---- the pad itself ----

def test_lanes_rest_and_travel():
    pad = ScriptedPad()
    pad.frame()
    assert pad.lanes()[:6] == [0.5, 0.5, 0.5, 0.5, 0.0, 0.0]
    assert pad.lanes() == list(gp.LANE_RESTS)
    pad.frame(axes=[1.0, -1.0, -1.0, 1.0, 1.0, -1.0])   # left stick right and up
    assert pad.lanes()[:6] == [1.0, 1.0, 0.0, 0.0, 1.0, 0.0]


def test_the_share_button_is_named_and_free(rig):
    """A pad with a Share button reports it at 15 (2026-10-15). It carries
    no factory row — Learn pad puts anything on it — and the
    name has to exist for the learn to land at all."""
    pad, lrn = ScriptedPad(), rig.learn
    assert gp.BUTTONS["SHARE"] == 15 and gp.SHARE < gp.N_BUTTONS
    assert not [b for b in routing.padmap() if b.source == "pad:SHARE"]
    pad.frame()
    lrn.arm("view.points", "pad")
    pad.frame(held={gp.SHARE})
    assert gp.learn_from(pad, lrn) is True
    rows = [(b.target, b.op) for b in rig.table.bindings if b.source == "pad:SHARE"]
    assert rows == [("view.points", "toggle")]


def test_release_edges():
    pad = ScriptedPad()
    pad.frame(held={gp.A}, hat=gp.HAT_UP)
    pad.frame()
    assert pad.released(gp.A) and pad.hat_released(gp.HAT_UP)
    pad.frame()
    assert not pad.released(gp.A) and not pad.hat_released(gp.HAT_UP)


# ---- Learn pad ----

def test_a_button_learns_a_meta_row_by_the_params_kind(rig):
    pad, lrn = ScriptedPad(), rig.learn
    for pid, src, held, hat, op, value in (
            ("view.faces", "pad:Y", {gp.Y}, 0, "toggle", 0.0),
            ("camera.reset", "pad:LB", {gp.LB}, 0, "fire", 0.0),
            ("view.shape", "pad:RB", {gp.RB}, 0, "toggle", 0.0),
            ("view.bright", "hat:DOWN", (), gp.HAT_DOWN, "step", -1.0),
            ("view.inst_amp", "pad:GUIDE", {gp.GUIDE}, 0, "step", 1.0)):
        pad.frame()
        lrn.arm(pid, "pad")
        pad.frame(held=held, hat=hat)
        assert gp.learn_from(pad, lrn) is True
        rows = [b for b in rig.table.bindings if b.source == src]
        assert [(b.target, b.op, b.value) for b in rows] == [(pid, op, value)], pid
        assert lrn.learning is None and f"learned {pid}" in lrn.last and not lrn.refused
    written = {(d["source"], d["target"]) for d in on_file(rig.path)}
    assert ("pad:Y", "view.faces") in written and ("hat:DOWN", "view.bright") in written


def test_a_button_learn_replaces_the_buttons_row_and_keeps_the_params_others(rig):
    pad, lrn, t = ScriptedPad(), rig.learn, rig.table
    assert any(b.source == "pad:A" and b.target == "view.faces" for b in t.bindings)
    assert any(b.source == "pad:Y" and b.target == "view.lines" for b in t.bindings)
    lrn.arm("view.lines", "pad")
    pad.frame()
    pad.frame(held={gp.A})
    gp.learn_from(pad, lrn)
    on_a = [b for b in t.bindings if b.source == "pad:A"]
    assert [(b.target, b.op) for b in on_a] == [("view.lines", "toggle")]
    assert "view.faces let go" in lrn.last
    assert any(b.source == "pad:Y" and b.target == "view.lines" for b in t.bindings)


def test_the_learning_press_does_not_fire_the_old_row(rig):
    pad, lrn = ScriptedPad(), rig.learn
    faces = rig.reg["view.faces"].value
    lrn.arm("view.points", "pad")
    pad.frame()
    pad.frame(held={gp.A})              # pad:A is view.faces's in the factory table
    learned = gp.learn_from(pad, lrn)
    rig.router.pad(pad, buttons=not learned)
    assert rig.reg["view.faces"].value == faces


def test_a_stick_learns_a_push_route_into_the_loadable(rig):
    pad, lrn, t = ScriptedPad(), rig.learn, rig.table
    lrn.arm("camera.yaw", "pad")
    pad.frame(axes=[0.3, 0, 0, 0, -1, -1])          # inside LEARN_TRAVEL: nothing yet
    assert gp.learn_from(pad, lrn) is False and lrn.learning == "camera.yaw"
    pad.frame(axes=[1.0, 0, 0, 0, -1, -1])
    gp.learn_from(pad, lrn)
    b = t.owner("camera.yaw")
    assert (b.source, b.op, b.value) == ("axis:LX", "push", PUSH_DEPTH)
    assert not any(d.get("source") == "axis:LX" for d in on_file(rig.path)) \
        if rig.path.exists() else True             # a route is the preset's, not the session's


def test_a_trigger_on_a_one_sided_fader_is_its_position(rig):
    pad, lrn = ScriptedPad(), rig.learn
    lrn.arm("view.inst_amp", "pad")
    pad.frame(axes=[0, 0, 0, 0, -1, 1.0])
    gp.learn_from(pad, lrn)
    b = rig.table.owner("view.inst_amp")
    assert (b.source, b.op, b.value) == ("axis:RT", "position", 1.0)


def test_a_desk_learn_ignores_the_pad(rig):
    pad, lrn = ScriptedPad(), rig.learn
    lrn.arm("view.faces", "desk")
    pad.frame()
    pad.frame(held={gp.A}, axes=[1.0, 0, 0, 0, -1, -1])
    assert gp.learn_from(pad, lrn) is False
    assert lrn.learning == "view.faces"


# ---- the router: the axis lanes, momentary and hold ----

def test_a_routed_axis_drives_its_param_and_is_claimed(rig):
    pad, r = ScriptedPad(), rig.router
    rig.table.add(Binding("axis:RT", "view.inst_amp", "position", 1.0))
    gp.publish(r)                       # the pad names its axes (plan 27 B2: not the router)
    assert r.claimed("axis") == {gp.AX_RT}
    pad.frame(axes=[0, 0, 0, 0, -1, 1.0])
    r.pad(pad)
    assert list(r.feeds["axis"][:6]) == [0.5, 0.5, 0.5, 0.5, 0.0, 1.0]
    assert r.describe(rig.table.owner("view.inst_amp")).startswith("right trigger")
    r.modulate()
    rig.reg.apply()
    amp = rig.reg["view.inst_amp"]
    assert amp.value == pytest.approx(amp.hi)
    pad.source = None                   # unplugged: the lanes go dark
    r.pad(pad)
    assert r.feeds["axis"] is None


def test_momentary_holds_a_toggle_while_the_button_is_down(rig):
    pad, r = ScriptedPad(), rig.router
    rig.table.add(Binding("pad:GUIDE", "view.faces", "momentary"))
    faces = rig.reg["view.faces"]
    faces.set(False)
    pad.frame(held={gp.GUIDE})
    r.pad(pad)
    assert faces.value
    pad.frame(held={gp.GUIDE})
    r.pad(pad)
    assert faces.value
    pad.frame()
    r.pad(pad)
    assert not faces.value


def test_hold_fires_once_after_hold_s(rig):
    pad, r = ScriptedPad(), rig.router
    fired = []
    rig.reg["camera.reset"].fire = lambda: fired.append(1)
    rig.table.add(Binding("hat:RIGHT", "camera.reset", "hold"))
    pad.frame(hat=gp.HAT_RIGHT)
    r.pad(pad, now=10.0)
    pad.frame(hat=gp.HAT_RIGHT)
    r.pad(pad, now=10.0 + routing.HOLD_S / 2)
    assert not fired
    pad.frame(hat=gp.HAT_RIGHT)
    r.pad(pad, now=10.0 + routing.HOLD_S)
    pad.frame(hat=gp.HAT_RIGHT)
    r.pad(pad, now=11.0 + routing.HOLD_S)
    assert fired == [1]                 # once per press
    pad.frame()
    r.pad(pad, now=12.0)
    pad.frame(hat=gp.HAT_RIGHT)         # a short tap: nothing
    r.pad(pad, now=13.0)
    pad.frame()
    r.pad(pad, now=13.1)
    assert fired == [1]


def test_no_factory_pad_row_loads_a_loadable_or_taps_the_tempo(rig):
    """2026-11-04, the owner: no swapping presets from a controller, and tap
    tempo not a default on every controller. On the factory table neither the
    d-pad's ← / → nor B, X and BACK walk or tap, however long they are held;
    the APC keeps TAP TEMPO and the keyboard (not a controller) B."""
    pad, r, reg = ScriptedPad(), rig.router, rig.reg
    tempo.register(reg, tempo.Clock())
    walked, tapped = [], []
    reg["preset.list.prev"].fire = lambda: walked.append(-1)
    reg["preset.list.next"].fire = lambda: walked.append(1)
    reg["tempo.tap"].fire = lambda: tapped.append(1)
    for hat in (gp.HAT_LEFT, gp.HAT_RIGHT):
        pad.frame(hat=hat)
        r.pad(pad, now=1.0)
        pad.frame(hat=hat)
        r.pad(pad, now=2.0 + routing.HOLD_S)
    points, strokes = reg["view.points"].value, reg["view.screen_strokes"].value
    for button in (gp.B, gp.X, gp.VIEW):
        pad.frame()
        r.pad(pad, now=5.0)
        pad.frame(held={button})
        r.pad(pad, now=5.0)
    assert reg["view.points"].value != points
    assert reg["view.screen_strokes"].value != strokes
    assert tapped == [] and walked == []
    targets = {b.target for b in routing.padmap()}
    assert "tempo.tap" not in targets
    assert not {t for t in targets if t.startswith("preset.") and t != "preset.save_new"}
    rows = {(b.source, b.target) for b in Bindings.factory().bindings}
    assert ("key:B", "tempo.tap") in rows                       # not a controller: stays
    assert (f"note:0:{apc40.N_TAP}", "tempo.tap") in rows       # it lives on the APC
    assert sum(b.target == "tempo.tap" for b in Bindings.factory().bindings) == 2   # no Edge row


def test_the_hold_times_agree():
    assert routing.HOLD_S == midi.HOLD_S


def test_a_stick_never_ends_a_learn_on_a_setting_it_cannot_drive(rig):
    """Not modulatable (a rig or show setting): a nudged stick is not
    asked, the learn stays armed, and a button still takes it."""
    pad, lrn = ScriptedPad(), rig.learn
    p = next(p for p in rig.reg if not p.modulatable and p.kind.name in ("TOGGLE", "TRIGGER"))
    lrn.arm(p.id, "pad")
    pad.frame(axes=[1.0, 0, 0, 0, -1, -1])
    assert gp.learn_from(pad, lrn) is False
    assert lrn.learning == p.id and not lrn.refused and rig.table.owner(p.id) is None
    pad.frame(held={gp.GUIDE})
    assert gp.learn_from(pad, lrn) is True
    assert any(b.source == "pad:GUIDE" and b.target == p.id for b in rig.table.bindings)


# ---- the factory layout (2026-10-14) ----

def test_an_older_files_pad_rows_move_to_the_new_layout_and_the_owners_stay(tmp_path):
    """The old factory pad rows (A rotate, X points, Y faces, START the
    sheet, BACK the panel, the right-stick click the camera) move to the
    layout of 2026-10-14 — START's sheet gone — on to 2026-10-29's where it
    moved again (X screen strokes), and BACK's holds the chase (2026-11-04); a
    row the owner learned onto a button stays; a second load changes nothing."""
    old = [Binding("pad:A", "view.rotate", "toggle"), Binding("pad:X", "view.points", "toggle"),
           Binding("pad:Y", "view.faces", "toggle"), Binding("pad:MENU", "ui.cheatsheet", "toggle"),
           Binding("pad:VIEW", "ui.panel", "toggle"),
           Binding("pad:LSTICK", "camera.reset", "fire"),
           Binding("pad:RSTICK", "camera.reset", "fire"),
           Binding("hat:UP", "fx.wobble.freq", "step")]          # the owner's own
    path = tmp_path / "bindings.json"
    Bindings(old, path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    rows = {b.source: (b.target, b.op) for b in t.of("pad", "hat")}
    assert rows["pad:A"] == ("view.faces", "toggle")
    assert rows["pad:X"] == ("view.screen_strokes", "toggle")   # straight to the newest
    assert rows["pad:Y"] == ("view.lines", "toggle")
    assert "pad:MENU" not in rows                            # the sheet's row gone
    assert rows["pad:VIEW"] == ("deck.chase", "momentary")    # the panel's row moved
    assert rows["pad:LSTICK"] == ("camera.reset", "fire")
    assert rows["pad:RSTICK"] == ("rot.reset_w", "fire")
    assert rows["hat:UP"] == ("fx.wobble.freq", "step")
    assert sum("the pad layout of 2026-10-14" in n for n in t.notes) == 4
    assert sum("the pad layout of 2026-10-29" in n for n in t.notes) == 1
    assert sum("the pad layout of 2026-11-04" in n for n in t.notes) == 1
    after = path.read_text()
    again = Bindings.load(path, legacy_midi=None)
    assert not again.notes and path.read_text() == after


def test_the_pads_bank_rows_move_straight_to_the_newest_layout(tmp_path):
    """B / X's factory rows on the bank (`preset.next` / `prev`, and B's
    `theme.next` from before plan 13) move to points and screen strokes,
    noted;
    the same targets on another button or op — the owner's — stay, and the
    APC40's QUANT keeps the bank; a second load changes nothing."""
    for b_row in (Binding("pad:B", "preset.next", "fire"),
                  Binding("pad:B", "theme.next", "fire")):
        old = [b_row, Binding("pad:X", "preset.prev", "fire"),
               Binding("pad:LB", "preset.next", "fire"),            # the owner's
               Binding("pad:RB", "preset.prev", "hold")]            # the owner's
        path = tmp_path / "bindings.json"
        Bindings(old, path=path).write()
        t = Bindings.load(path, legacy_midi=None)
        rows = {b.source: (b.target, b.op) for b in t.of("pad", "hat")}
        assert rows["pad:B"] == ("view.points", "toggle")
        assert rows["pad:X"] == ("view.screen_strokes", "toggle")
        assert rows["pad:LB"] == ("preset.next", "fire")
        assert rows["pad:RB"] == ("preset.prev", "hold")
        assert "pad:MENU" not in rows                               # never added
        assert "pad:VIEW" not in rows                               # never added
        assert sum("the pad layout of 2026-10-14" in n for n in t.notes) == 0
        assert sum("the pad layout of 2026-10-29" in n for n in t.notes) == 2
        after = path.read_text()
        again = Bindings.load(path, legacy_midi=None)
        assert not again.notes and path.read_text() == after


def test_the_10_14_layout_goes_straight_to_the_newest(tmp_path):
    """The layout of 2026-10-14 (B / X walk the list, the d-pad's ← / → step
    the speed): B / X onto points and screen strokes, and ← / → free, not via
    the walk of 2026-10-29, which one load would have left behind for a second
    to remove. A d-pad row the owner changed stays; a second load changes
    nothing."""
    old = [Binding("pad:B", "preset.list.next", "fire"),
           Binding("pad:X", "preset.list.prev", "fire"),
           Binding("hat:LEFT", "view.speed", "step", -4),
           Binding("hat:RIGHT", "view.speed", "step", 2),           # the owner's
           Binding("pad:MENU", "preset.save_new", "hold")]
    path = tmp_path / "bindings.json"
    Bindings(old, path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    rows = {b.source: (b.target, b.op, b.value) for b in t.of("pad", "hat")}
    assert rows["pad:B"] == ("view.points", "toggle", 1.0)
    assert rows["pad:X"] == ("view.screen_strokes", "toggle", 1.0)
    assert "hat:LEFT" not in rows
    assert rows["hat:RIGHT"] == ("view.speed", "step", 2.0)
    assert "pad:MENU" not in rows
    assert sum("the pad layout of 2026-10-29" in n for n in t.notes) == 2
    assert sum("the pad layout of 2026-11-04" in n for n in t.notes) == 2
    after = path.read_text()
    again = Bindings.load(path, legacy_midi=None)
    assert not again.notes and path.read_text() == after


def test_the_factory_pad_walks_nothing_and_the_desk_the_bank():
    """The factory rows: B / X on points and screen strokes, ← / → on nothing
    (the owner, 2026-11-04), the APC40's QUANT still on the bank's
    `preset.next`."""
    from hyperspace.routing import factory_desk, padmap

    pad = {b.source: (b.target, b.op) for b in padmap()}
    assert "hat:LEFT" not in pad and "hat:RIGHT" not in pad
    assert pad["pad:B"] == ("view.points", "toggle")
    assert pad["pad:X"] == ("view.screen_strokes", "toggle")
    assert any(b.source == f"note:0:{apc40.N_QUANT}" and b.target == "preset.next"
               for b in factory_desk())


def test_back_chases_and_start_is_free_on_the_generic_rows(rig):
    """2026-11-04: hold-to-save is the Edge's only. The generic rows have
    nothing on START, and holding it does nothing; BACK holds the base chase."""
    rows = {b.source: (b.target, b.op) for b in routing.padmap()}
    assert "pad:MENU" not in rows
    assert rows["pad:VIEW"] == ("deck.chase", "momentary")
    pad, r = ScriptedPad(), rig.router
    saved = []
    rig.reg["preset.save_new"].fire = lambda: saved.append(1)
    pad.frame(held={gp.MENU})
    r.pad(pad, now=1.0)
    pad.frame(held={gp.MENU})
    r.pad(pad, now=1.0 + routing.HOLD_S)
    assert saved == []


def test_held_start_on_a_row_saves_once_after_hold_s(rig):
    """The row hold-to-save is, on whichever pad has it."""
    pad, r = ScriptedPad(), rig.router
    saved = []
    rig.reg["preset.save_new"].fire = lambda: saved.append(1)
    rig.table.add(Binding("pad:MENU", "preset.save_new", "hold"))
    pad.frame(held={gp.MENU})
    r.pad(pad, now=1.0)
    pad.frame(held={gp.MENU})
    r.pad(pad, now=1.0 + routing.HOLD_S)
    assert saved == [1]


@pytest.mark.parametrize("edge_is_primary", [True, False], ids=["primary", "second"])
def test_an_edge_entry_keeps_hold_to_save_on_a_qualified_row_alone(rig, edge_is_primary):
    """Until a model can carry rows (register row 724): an entry `role = "edge"`,
    `controller = "edge"`, and one row `pad@edge:MENU`. Only that entry's pad hears
    it, primary or not; no load moves it; the other pad's START does nothing."""
    rig.table.add(Binding("pad@edge:MENU", "preset.save_new", "hold"))
    rig.table.write()
    t = Bindings.load(rig.path, legacy_midi=None)
    assert [b.target for b in t.of("pad") if b.source == "pad@edge:MENU"] == ["preset.save_new"]
    assert not [n for n in t.notes if "MENU" in n]
    table, r = rig.table, rig.router
    table.primaries = {"pad": "edge" if edge_is_primary else "pad"}
    saved = []
    rig.reg["preset.save_new"].fire = lambda: saved.append(1)
    edge_role = "" if edge_is_primary else "edge"
    other_role = "p2" if edge_is_primary else ""
    def held(role, base):
        pad = ScriptedPad()
        pad.frame(held={gp.MENU})
        r.pad(pad, now=base, role=role)
        pad.frame(held={gp.MENU})
        r.pad(pad, now=base + routing.HOLD_S, role=role)
    held(other_role, 1.0)
    assert saved == []
    held(edge_role, 3.0)
    assert saved == [1]


def test_the_right_stick_click_resets_the_4d_spin(rig):
    """`rot.reset_w` (the right-stick click): the W planes' rates and
    angles to 0; the other three planes keep theirs."""
    import math

    reg = rig.reg
    view = reg["camera.reset"]                 # (present: the left click's twin)
    assert view is not None
    for name in ("XY", "XZ", "YZ", "XW", "YW", "ZW"):
        reg[f"rot.rate.{name}"].set(3.0)
        reg[f"rot.phase.{name}"].set(1.0)
    pad, r = ScriptedPad(), rig.router
    pad.frame(held={gp.RSTICK})
    r.pad(pad)
    for name in ("XW", "YW", "ZW"):
        assert reg[f"rot.rate.{name}"].value == 0.0
        assert reg[f"rot.phase.{name}"].value == 0.0
    for name in ("XY", "XZ", "YZ"):
        assert reg[f"rot.rate.{name}"].value == 3.0
        assert math.isclose(reg[f"rot.phase.{name}"].value, 1.0)


# ---- a second pad (plan 27 B6) ----

def test_learn_on_a_second_pad_writes_its_qualified_rows(rig):
    """Learn pad completes on whichever pad moves; a second pad's rows
    carry its role (``pad@p2:A``, ``axis@p2:LX``), the primary's stay
    unqualified."""
    two, lrn, t = ScriptedPad(), rig.learn, rig.table
    lrn.arm("view.points", "pad")
    two.frame()
    two.frame(held={gp.A})
    assert gp.learn_from(two, lrn, role="p2") is True
    assert [(b.source, b.op) for b in t.bindings if b.target == "view.points"
            and b.source.startswith("pad@")] == [("pad@p2:A", "toggle")]
    assert any(d.get("source") == "pad@p2:A" for d in on_file(rig.path))   # the session's
    assert any(b.source == "pad:A" for b in t.bindings)                   # the primary's stays
    lrn.arm("camera.yaw", "pad")
    two.frame(axes=[1.0, 0, 0, 0, -1, -1])
    gp.learn_from(two, lrn, role="p2")
    b = t.owner("camera.yaw")
    assert (b.source, b.op, b.value) == ("axis@p2:LX", "push", PUSH_DEPTH)
    lrn.arm("view.inst_amp", "pad")
    two.frame(hat=gp.HAT_DOWN)
    assert gp.learn_from(two, lrn, role="p2") is True
    b = next(b for b in t.bindings if b.target == "view.inst_amp" and b.source.startswith("hat"))
    assert (b.source, b.op, b.value) == ("hat@p2:DOWN", "step", -1.0)    # DOWN steps down


def test_two_pads_drive_their_own_routes(rig):
    """A route from `axis@p2:LX` moves its param while `axis:LX` (the
    primary) is untouched, and the reverse; the primary's camera job
    counts only its own axes as routed."""
    one, two, r, t = ScriptedPad(), ScriptedPad(), rig.router, rig.table
    t.add(Binding("axis@p2:RT", "view.inst_amp", "position", 1.0))
    t.add(Binding("axis:RT", "rot.rate.XY", "position", 1.0))
    amp, rate = rig.reg["view.inst_amp"], rig.reg["rot.rate.XY"]
    one.frame()
    two.frame(axes=[0, 0, 0, 0, -1, 1.0])               # p2's right trigger, all the way
    r.pad(one)
    r.pad(two, role="p2")
    r.modulate()
    rig.reg.apply()
    assert amp.value == pytest.approx(amp.hi) and rate.value < rate.hi
    assert r.claimed("axis") == {gp.AX_RT} and r.claimed("axis@p2") == {gp.AX_RT}
    one.frame(axes=[0, 0, 0, 0, -1, 1.0])
    two.frame()
    r.pad(one)
    r.pad(two, role="p2")
    r.modulate()
    rig.reg.apply()
    assert rate.value == pytest.approx(rate.hi) and amp.value < amp.hi


def test_the_camera_job_is_the_primary_pads_only(rig, monkeypatch):
    """Defaults author no look (decision 24): a second pad's unrouted
    sticks do nothing; the primary's still orbit."""
    from hyperspace import devices

    ctx = devices.Context(reg=rig.reg, table=rig.table)
    one, two = ScriptedPad(), ScriptedPad()
    d1 = devices.PadDevice("pad", ctx=ctx, io=one)
    d2 = devices.PadDevice("p2", ctx=ctx, io=two)
    d2.qualifier = "p2"
    yaw = rig.reg["camera.yaw"]
    y0 = yaw.base
    one.frame()
    two.frame(axes=[1.0, 0, 0, 0, -1, -1])
    for d in (d1, d2):
        d._dt = 1 / 60                                   # (no poll: the pads are scripted)
        d.act(rig.router)
    assert yaw.base == y0                                # p2's stick: no camera job
    assert float(rig.router.feeds["axis@p2"][0]) == pytest.approx(1.0)
    one.frame(axes=[1.0, 0, 0, 0, -1, -1])
    for d in (d1, d2):
        d._dt = 1 / 60                                   # (no poll: the pads are scripted)
        d.act(rig.router)
    assert yaw.base > y0                                 # the primary's orbits


def test_learn_p2_completes_only_from_the_second_pad(rig):
    """"Learn p2" (the second pad's own want): a press on the primary does
    not complete it; a press on p2 writes `pad@p2:A`."""
    from hyperspace import devices

    lrn, t = rig.learn, rig.table
    one, two = ScriptedPad(), ScriptedPad()
    lrn.devices = devices.DeviceRegistry(devices=[
        devices.PadDevice("pad", io=one), _second(devices.PadDevice("p2", io=two))])
    assert lrn.wants() == ("desk", "pad", "pair", "pair (spring)", "p2")
    lrn.arm("view.points", "p2")
    one.frame()
    one.frame(held={gp.A})
    assert gp.learn_from(one, lrn) is False and lrn.learning == "view.points"
    two.frame()
    two.frame(held={gp.A})
    assert gp.learn_from(two, lrn, role="p2") is True
    assert [b.source for b in t.bindings if b.target == "view.points"
            and b.source.startswith("pad@")] == ["pad@p2:A"]
    assert lrn.accepts("pad@p2:A") is False                 # (it landed: nothing armed)
    lrn.arm("view.points", "p2")
    assert lrn.accepts("pad@p2:B") and lrn.accepts("axis@p2:LX")
    assert not lrn.accepts("pad:B") and not lrn.accepts("axis:LX")


def _second(d):
    d.qualifier = d.role
    return d


# ---- BACK holds the base chase (register row 723, the owner, 2026-11-04) ----

THE_LAST_LAYOUT = [Binding("pad:VIEW", "tempo.tap", "fire"),     # as the factory wrote them
                   Binding("hat:LEFT", "preset.list.prev", "hold"),
                   Binding("hat:RIGHT", "preset.list.next", "hold"),
                   Binding("pad:MENU", "preset.save_new", "hold"),
                   Binding("hat:UP", "view.bright", "step", 3)]


def test_the_new_row_reaches_an_existing_bindings_json_once(tmp_path, capsys):
    """A file on the layout of 2026-10-29: BACK's factory row moves to the
    chase, ← / → go, the file is copied beside itself first and written back,
    and the next load finds nothing to do and leaves no second copy. Not a
    schema move: the file's schema stays."""
    path = tmp_path / "bindings.json"
    Bindings(THE_LAST_LAYOUT, path=path).write()
    before, schema = path.read_text(), json.loads(path.read_text())["schema"]
    t = Bindings.load(path, legacy_midi=None)
    rows = {b.source: (b.target, b.op) for b in t.of("pad", "hat")}
    assert rows["pad:VIEW"] == (CHASE_PARAM, "momentary")
    assert "hat:LEFT" not in rows and "hat:RIGHT" not in rows and "pad:MENU" not in rows
    assert rows["hat:UP"] == ("view.bright", "step")
    assert ("removed pad:MENU → preset.save_new (the pad layout of 2026-11-04: "
            "the button is free)") in t.notes
    assert "remapped pad:VIEW: tempo.tap → deck.chase (the pad layout of 2026-11-04)" in t.notes
    assert ("removed hat:LEFT → preset.list.prev (the pad layout of 2026-11-04: "
            "the button is free)") in t.notes
    baks = list(tmp_path.glob("bindings.json.bak-*"))
    assert len(baks) == 1 and baks[0].read_text() == before
    written = json.loads(path.read_text())
    assert written["schema"] == schema
    assert {"source": "pad:VIEW", "target": CHASE_PARAM, "op": "momentary"} in written["bindings"]
    capsys.readouterr()
    after = path.read_text()
    again = Bindings.load(path, legacy_midi=None)
    assert not again.notes and path.read_text() == after
    assert list(tmp_path.glob("bindings.json.bak-*")) == baks


def test_a_deleted_chase_row_stays_deleted(tmp_path):
    """No pad row is added to a file: one with nothing on BACK or START is one
    where the owner took it off, and the next load does not put it back."""
    path = tmp_path / "bindings.json"
    Bindings(THE_LAST_LAYOUT, path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    t.remove(next(b for b in t.bindings if b.source == "pad:VIEW"))
    t.write()
    for _ in range(2):
        again = Bindings.load(path, legacy_midi=None)
        assert not any(b.source in ("pad:VIEW", "pad:MENU") for b in again.bindings)
        assert not again.notes


def test_a_qualified_row_on_back_is_the_owners(tmp_path):
    """The factory has never written a qualified row, and at load the table
    does not know which role is primary (`Bindings.primaries` comes later), so
    `pad@…` and `hat@…` rows are the owner's, whatever they say, and stay."""
    mine = [Binding("pad@pad:VIEW", "tempo.tap", "fire"),
            Binding("hat@pad:LEFT", "preset.list.prev", "hold"),
            Binding("pad@p2:VIEW", "view.lines", "toggle")]
    path = tmp_path / "bindings.json"
    Bindings(mine, path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    rows = {b.source: b.target for b in t.of("pad", "hat")}
    assert {b.source for b in mine} <= set(rows) and "pad:VIEW" not in rows
    assert not any(b.target == CHASE_PARAM for b in t.bindings)


@pytest.mark.parametrize("mine", [
    Binding("pad:VIEW", "view.lines", "toggle"),
    Binding("pad:VIEW", "tempo.tap", "toggle"),          # the same param, another op
    Binding("pad:VIEW", "tempo.tap", "fire", 0.0),       # as Learn pad writes it
], ids=["another-param", "another-op", "learned"])
def test_a_row_the_owner_put_on_back_is_left_alone(tmp_path, mine):
    """A row that is not the old factory row, tempo.tap learned by hand
    among them, stays, and this pad has no chase until it is Learned."""
    path = tmp_path / "bindings.json"
    Bindings([mine, Binding("pad:MENU", "preset.save_new", "hold")], path=path).write()
    t = Bindings.load(path, legacy_midi=None)
    rows = [b for b in t.of("pad") if b.source == "pad:VIEW"]
    assert [(b.target, b.op, b.value) for b in rows] == [(mine.target, mine.op, mine.value)]
    assert not any(b.target == CHASE_PARAM for b in t.bindings)
    assert not [n for n in t.notes if "pad:VIEW" in n]


def test_a_d_pad_row_the_owner_changed_stays(tmp_path):
    """Exact rows only: the list on ← by Learn pad (fire), or on another
    button, is the owner's, and survives as many loads as it likes."""
    mine = [Binding("hat:LEFT", "preset.list.prev", "fire", 0.0),
            Binding("hat:RIGHT", "camera.reset", "hold"),
            Binding("pad:MENU", "preset.save_new", "hold", 0.0),
            Binding("pad:LP", "preset.list.next", "hold"),
            Binding("hat:DOWN", "preset.list.next", "hold"),
            Binding("hat:UP", "preset.list.prev", "hold", 0.0)]      # value 0: not the old row
    path = tmp_path / "bindings.json"
    Bindings(mine, path=path).write()
    for _ in range(2):
        t = Bindings.load(path, legacy_midi=None)
        rows = {b.source: (b.target, b.op) for b in t.of("pad", "hat")}
        assert rows["hat:LEFT"] == ("preset.list.prev", "fire")
        assert rows["hat:RIGHT"] == ("camera.reset", "hold")
        assert rows["pad:MENU"] == ("preset.save_new", "hold")
        assert rows["pad:LP"] == ("preset.list.next", "hold")
        assert rows["hat:DOWN"] == ("preset.list.next", "hold")
        assert rows["hat:UP"] == ("preset.list.prev", "hold")
    # and the exact old row, by whatever hand, is the old row: the file can't say whose
    Bindings([Binding("hat:RIGHT", "preset.list.next", "hold"),
              Binding("hat:LEFT", "preset.list.prev", "hold", 0.0)], path=path).write()
    rows = {b.source: b.target for b in Bindings.load(path, legacy_midi=None).of("hat")}
    assert "hat:RIGHT" not in rows and rows["hat:LEFT"] == "preset.list.prev"


@pytest.mark.parametrize("pid,source", [("preset.list.next", "hat:RIGHT"),
                                        ("preset.list.prev", "hat:LEFT"),
                                        ("tempo.tap", "pad:VIEW"),
                                        ("tempo.tap", "pad:LP")])
def test_learn_can_put_them_back_and_a_reload_leaves_them(rig, pid, source):
    """They left the factory rows, not the registry: Learn pad lands them,
    and the row it writes is not the factory's, so no later load takes it."""
    tempo.register(rig.reg, tempo.Clock())
    rig.learn.arm(pid)
    assert rig.learn.learn_pad_button(source)
    t = Bindings.load(rig.path, legacy_midi=None)
    assert [(b.target, b.op) for b in t.of("pad", "hat") if b.source == source] == [(pid, "fire")]
    assert not [n for n in t.notes if source in n]


def test_back_held_chases_and_the_release_lets_go(rig):
    pad, r = ScriptedPad(), rig.router
    pad.frame(held={gp.VIEW})
    r.pad(pad, now=0.0)
    assert rig.reg.chasing
    pad.frame(held={gp.VIEW})
    r.pad(pad, now=1.0)
    assert rig.reg.chasing, "held, not a press that ends"
    pad.frame()
    r.pad(pad, now=1.1)
    assert not rig.reg.chasing


def test_a_sleeping_pad_lets_go_of_back(rig):
    pad, r = ScriptedPad(), rig.router
    pad.frame(held={gp.VIEW})
    r.pad(pad, now=0.0)
    assert rig.reg.chasing
    pad.source = None                           # asleep with the button down
    r.pad(pad, now=0.1)
    assert not rig.reg.chasing


def test_back_under_the_totem_still_chases(rig):
    """VIEW is outside what the totem holds off (A B X Y and the d-pad's ↓)."""
    assert "pad:VIEW" not in totem.SKIP
    pad, r = ScriptedPad(), rig.router
    pad.frame(held={gp.VIEW})
    r.pad(pad, now=0.0, skip=totem.SKIP)
    assert rig.reg.chasing
    pad.frame()
    r.pad(pad, now=0.1, skip=totem.SKIP)
    assert not rig.reg.chasing


def test_every_pad_has_back_but_the_right_joycon():
    """The row is on every model's face but a Joy-Con (R)'s, where it is dead and
    harmless. A Joy-Con's chase is its own: L on the left, R on the right, in #365's
    layout, which also gives − and capture to the totem (row 724)."""
    without = {m.id for m in MODELS.values() if not m.has_control("VIEW")}
    assert without == {"joycon-r"}
    assert MODELS["joycon-l"].glyphs["VIEW"] == "−"
    assert MODELS["joycon-l"].glyphs["LB"] == "L" and MODELS["joycon-r"].glyphs["RB"] == "R"


def test_the_totem_skipping_a_learned_row_leaves_backs_press_alone(rig):
    """A skip lets go only of what the skipped button holds: with `pad:A` on
    the chase too and A in the totem's SKIP, BACK still works."""
    rig.table.add(Binding("pad:A", CHASE_PARAM, "momentary"))
    pad, r = ScriptedPad(), rig.router
    for now in (0.0, 0.1):
        pad.frame(held={gp.VIEW})
        r.pad(pad, now=now, skip=totem.SKIP)
        assert rig.reg.chasing, "BACK held under a skip on another row"
    pad.frame()
    r.pad(pad, now=0.2, skip=totem.SKIP)
    assert not rig.reg.chasing
    # and A's own press, taken by the skip when it starts, is let go
    pad.frame(held={gp.A})
    r.pad(pad, now=0.3)
    assert rig.reg.chasing
    pad.frame(held={gp.A})
    r.pad(pad, now=0.4, skip=totem.SKIP)
    assert not rig.reg.chasing


def test_two_buttons_on_the_chase_hold_it_until_the_last_lets_go(rig):
    rig.table.add(Binding("pad:Y", CHASE_PARAM, "momentary"))
    pad, r = ScriptedPad(), rig.router
    pad.frame(held={gp.VIEW})
    r.pad(pad, now=0.0)
    pad.frame(held={gp.VIEW, gp.Y})
    r.pad(pad, now=0.1)
    pad.frame(held={gp.VIEW})                   # a brush of Y
    r.pad(pad, now=0.2)
    assert rig.reg.chasing
    pad.frame()
    r.pad(pad, now=0.3)
    assert not rig.reg.chasing


def test_a_row_removed_under_a_held_button_lets_go(rig):
    pad, r = ScriptedPad(), rig.router
    pad.frame(held={gp.VIEW})
    r.pad(pad, now=0.0)
    assert rig.reg.chasing
    rig.table.remove(next(b for b in rig.table.bindings if b.source == "pad:VIEW"))
    pad.frame(held={gp.VIEW})
    r.pad(pad, now=0.1)
    assert not rig.reg.chasing


def test_a_release_this_pad_did_not_press_touches_nothing(rig):
    """The press went to a learn (`buttons=False`): its release is not a let-go
    of a chase held from elsewhere."""
    rig.reg[CHASE_PARAM].set(True)
    pad, r = ScriptedPad(), rig.router
    pad.frame(held={gp.VIEW})
    r.pad(pad, now=0.0, buttons=False)
    pad.frame()
    r.pad(pad, now=0.1)
    assert rig.reg.chasing
    rig.reg[CHASE_PARAM].set(False)


def test_closing_the_pad_device_lets_go_of_back(rig):
    """A pad device closed with BACK down (config.toml saved, the entry gone):
    no `act` follows, so `close` itself lets go. Second-pad rows likewise."""
    from hyperspace import devices

    pad = ScriptedPad()
    pad.frame(held={gp.VIEW})
    d = devices.PadDevice("pad", None, devices.Context(reg=rig.reg), io=pad)
    d.act(rig.router)
    assert rig.reg.chasing
    d.close()
    assert not rig.reg.chasing and d.io is None
    # a device that never acted closes as ever
    devices.PadDevice("pad", None, devices.Context(reg=rig.reg), io=ScriptedPad()).close()


def test_a_pad_device_closed_lets_go_even_if_the_router_throws(rig):
    from hyperspace import devices

    d = devices.PadDevice("pad", None, devices.Context(reg=rig.reg), io=ScriptedPad())
    closed = []
    d.io.close = lambda: closed.append(1)
    d._router = NS(pad_lost=lambda _role: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        d.close()
    assert closed == [1] and d.io is None
