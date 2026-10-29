"""The gamepad as a mappable controller: Learn pad (a button, the D-pad, a
stick or a trigger completes it), momentary / hold rows on pad buttons,
and the axes as the `axis` lanes a route can read."""

import json
from types import SimpleNamespace as NS

import pytest

import hyperspace.gamepad as gp
from hyperspace import midi, routing
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.learn import PUSH_DEPTH, Learn
from hyperspace.library import Library
from hyperspace.params import build_registry
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

def test_a_button_learns_a_session_row_by_the_params_kind(rig):
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


def test_a_stick_learns_a_push_route_into_the_preset(rig):
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


def test_the_factory_pad_walks_on_a_held_d_pad_and_b_x_back_are_harmless(rig):
    """2026-10-29, on the factory table: a brush of the d-pad's ← / →
    walks nothing, a hold of HOLD_S walks the list once per press; B / X
    toggle points and screen strokes, BACK undoes — none of them loads."""
    pad, r, reg = ScriptedPad(), rig.router, rig.reg
    walked, undone = [], []
    reg["preset.list.prev"].fire = lambda: walked.append(-1)
    reg["preset.list.next"].fire = lambda: walked.append(1)
    reg["edit.undo"].fire = lambda: undone.append(1)
    pad.frame(hat=gp.HAT_LEFT)                  # a brush
    r.pad(pad, now=1.0)
    pad.frame()
    r.pad(pad, now=1.1)
    assert walked == []
    pad.frame(hat=gp.HAT_RIGHT)                 # held
    r.pad(pad, now=2.0)
    pad.frame(hat=gp.HAT_RIGHT)
    r.pad(pad, now=2.0 + routing.HOLD_S)
    pad.frame(hat=gp.HAT_RIGHT)
    r.pad(pad, now=3.0 + routing.HOLD_S)
    pad.frame(hat=gp.HAT_LEFT)                  # let go, then ← held
    r.pad(pad, now=4.0)
    pad.frame(hat=gp.HAT_LEFT)
    r.pad(pad, now=4.1 + routing.HOLD_S)
    assert walked == [1, -1]
    points, strokes = reg["view.points"].value, reg["view.screen_strokes"].value
    for button in (gp.B, gp.X, gp.VIEW):
        pad.frame()
        r.pad(pad, now=5.0)
        pad.frame(held={button})
        r.pad(pad, now=5.0)
    assert reg["view.points"].value != points
    assert reg["view.screen_strokes"].value != strokes
    assert undone == [1] and walked == [1, -1]


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
    layout of 2026-10-14 — BACK's panel gone, START's sheet gone and its
    hold-to-save in its place (PAD_NEW_ROWS) — and on to 2026-10-29's
    where it moved again (X screen strokes, BACK undo); a row the owner
    learned onto a button stays; a second load changes nothing."""
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
    assert rows["pad:MENU"] == ("preset.save_new", "hold")   # the sheet's row gone
    assert rows["pad:VIEW"] == ("edit.undo", "fire")          # the panel's row gone
    assert rows["pad:LSTICK"] == ("camera.reset", "fire")
    assert rows["pad:RSTICK"] == ("rot.reset_w", "fire")
    assert rows["hat:UP"] == ("fx.wobble.freq", "step")
    assert sum("the pad layout of 2026-10-14" in n for n in t.notes) == 6
    assert sum("the pad layout of 2026-10-29" in n for n in t.notes) == 2
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
        assert rows["pad:MENU"] == ("preset.save_new", "hold")      # added, not held
        assert rows["pad:VIEW"] == ("edit.undo", "fire")            # added
        assert sum("the pad layout of 2026-10-14" in n for n in t.notes) == 1
        assert sum("the pad layout of 2026-10-29" in n for n in t.notes) == 3
        after = path.read_text()
        again = Bindings.load(path, legacy_midi=None)
        assert not again.notes and path.read_text() == after


def test_the_10_14_layout_moves_the_walk_onto_the_held_d_pad(tmp_path):
    """2026-10-29: the layout of 2026-10-14 (B / X walk the list, the
    d-pad's ← / → step the speed) moves the walk onto ← / → held, B / X
    onto points and screen strokes, and adds BACK's undo; a d-pad row the
    owner changed stays; a second load changes nothing."""
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
    assert rows["hat:LEFT"] == ("preset.list.prev", "hold", 1.0)
    assert rows["hat:RIGHT"] == ("view.speed", "step", 2.0)
    assert rows["pad:VIEW"] == ("edit.undo", "fire", 1.0)
    assert sum("the pad layout of 2026-10-29" in n for n in t.notes) == 4
    after = path.read_text()
    again = Bindings.load(path, legacy_midi=None)
    assert not again.notes and path.read_text() == after


def test_the_factory_pad_walks_the_list_held_and_the_desk_the_bank():
    """The factory rows: the d-pad's ← / → held on the list's triggers
    (a brush does nothing), B / X on points and screen strokes, the
    APC40's QUANT still on the bank's `preset.next`."""
    from hyperspace import apc40
    from hyperspace.routing import factory_desk, padmap

    pad = {b.source: (b.target, b.op) for b in padmap()}
    assert pad["hat:LEFT"] == ("preset.list.prev", "hold")
    assert pad["hat:RIGHT"] == ("preset.list.next", "hold")
    assert pad["pad:B"] == ("view.points", "toggle")
    assert pad["pad:X"] == ("view.screen_strokes", "toggle")
    assert any(b.source == f"note:0:{apc40.N_QUANT}" and b.target == "preset.next"
               for b in factory_desk())


def test_held_start_saves_a_new_preset_and_back_undoes(rig):
    """START carries the factory's hold-to-save and fires it once the
    button has been down HOLD_S; BACK undoes (2026-10-29)."""
    rows = {b.source: (b.target, b.op) for b in routing.padmap()}
    assert rows["pad:MENU"] == ("preset.save_new", "hold")
    assert rows["pad:VIEW"] == ("edit.undo", "fire")
    pad, r = ScriptedPad(), rig.router
    saved = []
    rig.reg["preset.save_new"].fire = lambda: saved.append(1)
    rig.table.add(Binding("pad:MENU", "preset.save_new", "hold"))
    pad.frame(held={gp.MENU})
    r.pad(pad, now=1.0)
    pad.frame(held={gp.MENU})
    r.pad(pad, now=1.0 + routing.HOLD_S)
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
    assert lrn.wants() == ("desk", "pad", "p2")
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
