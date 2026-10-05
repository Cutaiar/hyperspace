"""Ultraleap hands: features, the analog chain, MIDI out, learn, setups — fake hands, no SDK."""

import itertools
import json
import math
import os
import re
from types import SimpleNamespace as NS

import numpy as np
import pytest

from hyperspace import hands
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.hands import HandSettings, HandsIO, features
from hyperspace.hands import signal as hs
from hyperspace.learn import Learn
from hyperspace.library import Library
from hyperspace.midi import MidiIO
from hyperspace.params import Registry, build_registry
from hyperspace.routing import Binding, Bindings, Router
from hyperspace.view import ViewState

DT = 1 / 60


def v3(x, y, z):
    return NS(x=x, y=y, z=z)


def hand(side="right", pos=(0.0, 200.0, 0.0), normal=(0.0, -1.0, 0.0),
         direction=(0.0, 0.0, -1.0), grab=0.0, pinch=0.0, conf=1.0,
         tips=None, palm_w=0.0):
    """A palm-only hand unless `tips` gives the four thumb-to-finger gaps
    in mm (index, middle, ring, pinky), which builds the digits too."""
    h = NS(type=NS(name=side.capitalize()), confidence=conf,
           grab_strength=grab, pinch_strength=pinch, grab_angle=grab * math.pi,
           pinch_distance=80.0,
           palm=NS(position=v3(*pos), normal=v3(*normal), direction=v3(*direction),
                   width=palm_w))
    if tips is not None:
        digit = lambda x: NS(distal=NS(next_joint=v3(x, 0.0, 0.0)))
        h.thumb = digit(0.0)
        for f, mm in zip(hands.PINCHES, tips):
            setattr(h, f, digit(mm))
    return h


def tilt(rad):
    """A right palm pitched up by rad."""
    return (0.0, math.sin(rad), -math.cos(rad))


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class FakeSource:
    """latest() like LeapSource; `put` is one tracking frame."""

    def __init__(self, clock):
        self.clock = clock
        self.seq, self.hands = 0, {}
        self.status, self.on = "tracking", True

    def put(self, *hs_):
        self.seq += 1
        self.hands = {h.type.name.lower(): (features(h), h.confidence) for h in hs_}

    def latest(self):
        return self.seq, self.clock(), self.hands


class FakeOut:
    name = "fake"

    def __init__(self):
        self.sent = []

    def send(self, m):
        self.sent.append(m)


def rig(tmp_path=None, **cfg):
    """A HandsIO over fake hands, a fake clock and pass-through smoothing:
    no filter, no catch, instant dynamics — each test turns on what it checks."""
    settings = HandSettings.from_config(cfg)
    settings.smooth, settings.response, settings.catch_s, settings.rate = 1e6, 0.0, 0.0, 0
    settings.pinch_hold = 0.0          # debounce has its own tests
    for a in settings.axes:
        a.deadzone, a.rest = 0.0, "hold"
    clock = Clock()
    src = FakeSource(clock)
    io = HandsIO(settings, cfg, source=src, out=FakeOut(), clock=clock,
                 cal_path=None if tmp_path is None else tmp_path / "hands.json")
    return NS(io=io, src=src, clock=clock, s=settings)


def run(r, frames=1, *hs_, learn=None, router=None, fresh=True):
    """`frames` render frames; a new tracking frame on each when `fresh`."""
    out = []
    for _ in range(frames):
        r.clock.t += DT
        if fresh:
            r.src.put(*hs_)
        out += r.io.poll(DT, learn, router)
    return out


def ax(r, name):
    return r.io.axis(name)


# ---------------------------------------------------------------- features

def test_neutral_palm_reads_zero_rotation():
    f = features(hand())
    assert f["roll"] == pytest.approx(0) and f["pitch"] == pytest.approx(0)
    assert f["yaw"] == pytest.approx(0)
    assert (f["x"], f["y"], f["z"]) == (0.0, 200.0, 0.0)


@pytest.mark.parametrize("side,thumb_up_normal,outward", [
    ("right", (-1.0, 0.0, 0.0), (1.0, 0.0, -1.0)),
    ("left", (1.0, 0.0, 0.0), (-1.0, 0.0, -1.0)),
])
def test_rotations_are_mirrored_between_hands(side, thumb_up_normal, outward):
    """Thumb-up roll and fingers-outward yaw increase on both hands."""
    assert features(hand(side, normal=thumb_up_normal))["roll"] == pytest.approx(90)
    d = np.array(outward) / np.linalg.norm(outward)
    assert features(hand(side, direction=tuple(d)))["yaw"] == pytest.approx(45)


def test_fingers_up_is_positive_pitch():
    assert features(hand(direction=tilt(0.5)))["pitch"] == pytest.approx(math.degrees(0.5))


# ---------------------------------------------------------------- shape

def test_linear_shape_is_the_identity():
    for u in np.linspace(0, 1, 11):
        assert hs.shape(u, bipolar=True, deadzone=0, c=0) == pytest.approx(u)
        assert hs.shape(u, bipolar=False, deadzone=0, c=0) == pytest.approx(u)


def test_centred_dead_zone_is_flat_at_neutral_and_keeps_the_throw():
    f = lambda u: hs.shape(u, bipolar=True, deadzone=0.2, c=0)
    assert f(0.5) == f(0.55) == f(0.45) == 0.5          # |d| = 0.1 < 0.2
    assert f(0.0) == 0.0 and f(1.0) == 1.0              # the ends still reach
    assert f(0.8) > 0.5 > f(0.2)


def test_unipolar_dead_zone_sits_at_the_bottom():
    f = lambda u: hs.shape(u, bipolar=False, deadzone=0.1, c=0)
    assert f(0.05) == 0.0 and f(0.1) == 0.0 and f(1.0) == 1.0
    assert f(0.55) == pytest.approx(0.5)


def test_curve_is_symmetric_and_monotonic_about_centre():
    f = lambda u: hs.shape(u, bipolar=True, deadzone=0, c=0.7)
    xs = np.linspace(0, 1, 101)
    ys = [f(x) for x in xs]
    assert all(b >= a for a, b in itertools.pairwise(ys))
    for x in xs:
        assert f(x) - 0.5 == pytest.approx(0.5 - f(1 - x), abs=1e-12)
    assert abs(f(0.6) - 0.5) < 0.1                    # + curve: fine near neutral


# ---------------------------------------------------------------- dynamics

def test_attack_and_decay_are_separate_time_constants():
    y = 0.0
    for _ in range(60):                                 # 1 s at attack 1 s: 1 − 1/e
        y = hs.slew(y, 1.0, DT, attack=1.0, decay=0.1)
    assert y == pytest.approx(1 - math.exp(-1), abs=1e-6)
    for _ in range(6):                                  # 0.1 s at decay 0.1 s
        y = hs.slew(y, 0.0, DT, attack=1.0, decay=0.1)
    assert y == pytest.approx((1 - math.exp(-1)) * math.exp(-1), abs=1e-6)
    assert hs.slew(0.2, 0.9, DT, 0.0, 0.0) == 0.9       # 0 is instant


def test_spring_settles_in_time_and_bounce_overshoots():
    y, v, peak = 1.0, 0.0, 1.0
    for _ in range(30):                                  # 0.5 s settle, no bounce
        y, v = hs.spring(y, v, 0.0, DT, 0.5, 0.0)
        peak = min(peak, y)
    assert abs(y) < 0.03 and peak > -1e-3               # there, and never past
    y, v, low = 1.0, 0.0, 1.0
    for _ in range(60):
        y, v = hs.spring(y, v, 0.0, DT, 0.5, 0.8)
        low = min(low, y)
    assert low < -0.1                                    # it rang through rest


def test_spring_is_stable_on_a_long_frame():
    y, _ = hs.spring(1.0, 0.0, 0.0, 0.05, 0.05, 1.0)
    assert math.isfinite(y) and abs(y) < 2


def test_follower_catches_a_returning_hand_instead_of_jumping():
    f = hs.Follower()
    kw = {"attack": 0, "decay": 0, "catch_s": 0.2, "rest": "hold", "rest_value": 0.5,
          "return_s": 0.5, "bounce": 0}
    assert f.step(DT, 0.2, **kw) == 0.2                 # first sight: where the hand is
    f.step(DT, None, **kw)                               # gone: hold
    assert f.y == 0.2
    y = f.step(DT, 0.9, **kw)                            # back, far away
    assert 0.2 < y < 0.5
    for _ in range(20):
        y = f.step(DT, 0.9, **kw)
    assert y == pytest.approx(0.9, abs=0.01) and f.mode == f.FOLLOW


# ---------------------------------------------------------------- MIDI encoding

def test_quantize_holds_at_a_step_boundary():
    last, edge = 64, 64.5 / 127
    for wobble in (-0.2, 0.2, -0.1, 0.3):
        last = hs.quantize(edge + wobble / 127, last, 0.35)
        assert last == 64
    assert hs.quantize(65.0 / 127, last, 0.35) == 65
    assert hs.quantize(1.0, None, 3, 16383) == 16383


def test_encodings():
    m = hs.encode("cc14", 15, 5, 0x1234)
    assert [(x.control, x.value) for x in m] == [(5, 0x1234 >> 7), (37, 0x1234 & 0x7F)]
    assert hs.encode("pitch", 3, 0, 8192)[0].pitch == 0
    assert hs.encode("pitch", 3, 0, 16383)[0].pitch == 8191
    p = hs.encode("pressure", 2, 0, 99)[0]
    assert (p.type, p.channel, p.value) == ("aftertouch", 2, 99)
    assert hs.encode("off", 0, 0, 1) == []
    assert hs.valid("cc14", 40) and not hs.valid("cc14", 31) and not hs.valid("cc", 127)


# ---------------------------------------------------------------- settings

def test_default_layout_left_then_right():
    s = HandSettings.from_config({"dofs": ["x", "y", "grab"], "cc": 102})
    assert [(a.name, a.channel, a.number) for a in s.axes] == [
        ("left.x", 16, 102), ("left.y", 16, 103), ("left.grab", 16, 104),
        ("right.x", 16, 105), ("right.y", 16, 106), ("right.grab", 16, 107)]
    assert [a.bipolar for a in s.axes[:3]] == [True, False, False]


def test_bad_layouts_are_refused():
    with pytest.raises(ValueError, match="unknown"):
        HandSettings.from_config({"dofs": ["x", "wiggle"]})
    with pytest.raises(ValueError, match="past 127"):
        HandSettings.from_config({"cc": 120})


def test_conflicts_name_clashing_outputs():
    s = HandSettings.from_config({})
    a, b = s.axes[0], s.axes[1]
    a.out, a.number = "cc14", 40
    assert "0–31" in hands.conflicts(s)[a.name]
    a.out, a.number, a.channel = "cc14", 4, 16
    b.out, b.number, b.channel = "cc", 36, 16                # a's LSB
    assert "left.x" in hands.conflicts(s)[b.name]
    a.out = b.out = "pitch"
    assert hands.conflicts(s)[b.name]                        # one bend per channel
    b.channel = 15
    assert hands.conflicts(s) == {}


def test_mirror_copies_the_feel_not_the_output():
    s = HandSettings.from_config({})
    src = s.axes[3]                                          # left.roll
    src.curve, src.attack, src.rest, src.number = 0.6, 0.3, "hold", 1
    dst = hands.mirror(s, "left.roll")
    assert dst.name == "right.roll"
    assert (dst.curve, dst.attack, dst.rest) == (0.6, 0.3, "hold") and dst.number != 1


def test_setup_is_registry_params_that_round_trip():
    s = HandSettings.from_config({})
    reg = Registry()
    hands.register(reg, s)
    hands.register(reg, s)                                   # idempotent
    ps = reg.group("hands")
    # 8 settings, 13 per axis, and the selection with its alias (plan 13 WP3)
    assert len(ps) == 8 + 12 * 13 + 2 and not any(p.modulatable for p in ps)
    snap = reg.snapshot("hands")
    reg["hands.right.pitch.curve"].set_value(-0.5)
    reg["hands.right.pitch.rest"].set(0)
    reg["hands.right.pitch.out"].set(hs.OUTS.index("pitch"))
    reg["hands.smooth"].set_value(3.0)
    a = s.axes[10]
    assert (a.curve, a.rest, a.out, s.smooth) == (-0.5, "hold", "pitch", 3.0)
    reg.restore(snap)
    assert (a.curve, a.rest, a.out, s.smooth) == (0.0, "return", "cc", 1.0)


def test_a_setup_saves_and_loads_through_the_library(tmp_path):
    chain = Analyzer(Analyser())
    reg = build_registry(ViewState(), Control(chain), NS(chain=chain))
    s = HandSettings.from_config({})
    hands.register(reg, s)
    lib = Library(tmp_path)
    lib.attach(reg)
    assert "hands" in lib.groups()
    s.axes[0].curve = 0.4
    lib.save_as("hands", "Soft")
    s.axes[0].curve = 0.0
    lib.load("hands", "Soft")
    assert s.axes[0].curve == pytest.approx(0.4)


# ---------------------------------------------------------------- the adapter

def test_entering_sends_presence_then_the_axes():
    r = rig()
    msgs = run(r, 1, hand("right", pos=(220.0, 350.0, 0.0)))
    assert (msgs[0].type, msgs[0].note, msgs[0].channel) == ("note_on", 121, 15)
    ccs = {m.control: m.value for m in msgs if m.type == "control_change"}
    assert set(ccs) == set(range(108, 114))          # only the right hand's six
    assert ccs[108] == 127 and ccs[109] == 127       # x, y at the top of their ranges
    assert ccs[111] == 64                            # roll 0 sits mid-range
    assert r.io.out.sent == msgs


def test_a_still_hand_sends_nothing():
    r = rig()
    run(r, 1, hand())
    assert run(r, 5, hand()) == []
    assert run(r, 3, fresh=False) == []              # no new tracking frame: hold
    msgs = run(r, 1, hand(pos=(0.0, 300.0, 0.0)))
    assert [(m.control, m.value) for m in msgs] == [(109, round(200 / 250 * 127))]


def test_leaving_springs_to_rest_and_hold_stays():
    r = rig()
    k = ax(r, "right.pitch")
    a = r.s.axes[k]
    a.rest, a.rest_value, a.return_s, a.bounce = "return", 0.5, 0.3, 0.0
    run(r, 1, hand(direction=tilt(0.9)))             # pitched well up
    y0 = r.io.state[k].y
    msgs = run(r, 3)                                  # hand gone
    assert ("note_off", 121) in [(m.type, getattr(m, "note", None)) for m in msgs]
    assert 0.5 < r.io.state[k].y < y0                 # on its way home, not jumped
    run(r, 30)
    assert r.io.state[k].y == pytest.approx(0.5, abs=0.01)
    assert r.io.state[k].q == 64                      # and the DAW heard it land
    held = r.io.state[ax(r, "right.y")]
    assert held.y == pytest.approx((200 - 100) / 250)  # a hold axis didn't move


def test_rate_limit_caps_messages_and_the_last_value_lands():
    r = rig()
    r.s.rate = 10                                     # 10/s: one per 6 frames at 60 fps
    k = ax(r, "right.y")
    sent = []
    for j in range(60):                               # a 1 s sweep up
        sent += [m for m in run(r, 1, hand(pos=(0.0, 100 + 250 * j / 59, 0.0)))
                 if m.type == "control_change" and m.control == 109]
    assert 9 <= len(sent) <= 11
    run(r, 12, hand(pos=(0.0, 350.0, 0.0)))
    assert r.io.state[k].q == 127


def test_output_kinds_reach_the_port():
    r = rig()
    ax_ = r.s.axes
    ax_[ax(r, "right.x")].out, ax_[ax(r, "right.x")].number = "cc14", 1
    ax_[ax(r, "right.y")].out, ax_[ax(r, "right.y")].channel = "pitch", 2
    ax_[ax(r, "right.z")].out, ax_[ax(r, "right.z")].channel = "pressure", 3
    for name in ("right.roll", "right.pitch", "right.yaw"):
        ax_[ax(r, name)].out = "off"
    msgs = run(r, 1, hand(pos=(100.0, 225.0, 100.0)))[1:]      # past the presence note
    kinds = sorted((m.type, m.channel) for m in msgs)
    assert kinds == [("aftertouch", 2), ("control_change", 15), ("control_change", 15),
                     ("pitchwheel", 1)]
    bend = next(m for m in msgs if m.type == "pitchwheel")
    assert bend.pitch == pytest.approx(0, abs=2)                  # y mid-range: centred


def test_solo_lets_one_axis_through():
    r = rig()
    r.io.solo = ax(r, "right.z")
    assert [m.control for m in run(r, 1, hand(pos=(10.0, 150.0, 40.0)))] == [110]


def test_low_confidence_counts_as_absent():
    r = rig(min_confidence=0.5)
    assert run(r, 1, hand(conf=0.2)) == [] and not r.io.present["right"]


def test_lanes_carry_outputs_then_presence_then_pinches():
    r = rig()
    run(r, 1, hand())
    lanes = r.io.lanes()
    # 12 axes, 2 presence, 8 pinch switches
    assert len(lanes) == 22 and r.io.lane_names[12:14] == ["L in", "R in"]
    assert all(math.isnan(u) for u in lanes[:6]) and lanes[12:14] == [0.0, 1.0]
    assert lanes[14:] == [0.0] * 8          # a palm-only hand pinches nothing
    assert r.io.lane_names[14:16] == ["L ind", "L mid"]


# ---------------------------------------------------------------- calibration

def test_calibration_sweep_sets_and_saves_ranges(tmp_path):
    r = rig(tmp_path)
    r.io.start_calibration(1.0)
    for j in range(70):
        run(r, 1, hand(pos=(0.0, 150 + 100 * (j % 35) / 34, 0.0)))
    assert not r.io.calibrating and "calibrated" in r.io.cal_note
    st = r.io.state[ax(r, "right.y")]
    assert st.lo == pytest.approx(150, abs=8) and st.hi == pytest.approx(250, abs=8)
    saved = json.loads((tmp_path / "hands.json").read_text())["axes"]
    assert saved["right.y"]["hi"] == pytest.approx(st.hi, abs=1e-3)
    assert saved["left.y"] == {"lo": 100.0, "hi": 350.0}     # never reached: default
    again = rig(tmp_path)
    assert again.io.state[ax(again, "right.y")].hi == pytest.approx(st.hi, abs=1e-3)
    again.io.reset_ranges()
    assert again.io.state[ax(again, "right.y")].hi == 350.0


# ---------------------------------------------------------------- through the table

@pytest.fixture()
def app(tmp_path):
    return make_app(tmp_path)


def make_app(tmp_path):
    """The host's half the hands meet: registry, table, Learn, MIDI, router."""
    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    lib = Library(tmp_path)
    reg = build_registry(view, control, NS(chain=chain), lib.project)
    table = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)

    class Quiet:
        def iter_pending(self):
            return iter(())

    router = Router(reg, table)
    learn = Learn(reg, table, lane=router.lane)          # as app.main builds it
    midi = MidiIO(reg, table, inp=Quiet(), out=FakeOut(), learner=learn)
    return NS(reg=reg, view=view, learn=learn, midi=midi, router=router, table=table)


def _frame(app):
    """The rest of app.py's frame after hands.poll fed the lanes."""
    app.router.modulate()
    app.reg.apply()


def test_learn_takes_the_axis_that_moved_as_a_position_route(app):
    r = rig()
    run(r, 1, hand(), learn=app.learn, router=app.router)
    app.learn.arm("view.inst_amp")
    for k in range(1, 8):                    # x jitters a little, pitch moves a lot
        run(r, 1, hand(pos=(2.0 * k, 200.0, 0.0), direction=tilt(0.12 * k)),
            learn=app.learn, router=app.router)
    assert app.learn.learning is None and app.learn.pending is None
    rows = [b for b in app.table.of("hand") if b.target == "view.inst_amp"]
    assert [(b.source, b.op, b.value, b.when) for b in rows] == [
        ("hand:right.pitch", "position", 1.0, None)]
    assert app.table.owner("view.inst_amp") is rows[0]
    assert "learned view.inst_amp" in app.learn.last
    # the hand is the fader — in floats, off its 100 detents — through the
    # Router like every route; the base is what the panel set
    run(r, 1, hand(direction=tilt(math.radians(13.0))), learn=app.learn, router=app.router)
    _frame(app)
    p = app.reg["view.inst_amp"]
    u = (13.0 + 60) / 120
    assert p.eff_norm == pytest.approx(u, abs=1e-4)   # the filter at 1 MHz: all but exact
    assert abs(p.eff_norm * p.steps - round(p.eff_norm * p.steps)) > 1e-3
    assert p.norm == pytest.approx(0.25) and p.modulated
    # into the loaded preset: the table has it, bindings.json does not
    # (plan 13 §3.3 — a save of the preset writes it)
    on_disk = Bindings.load(app.table.path, legacy_midi=None)
    assert on_disk.owner("view.inst_amp") is None


def test_a_panel_edit_moves_the_return_value_under_a_hand(app):
    """The panel (or a knob) sets the base; the hand positions on top of
    it; the base is what shows when the hand leaves."""
    r = rig()
    app.table.add(Binding("hand:7", "view.inst_amp", "position"))   # right.y
    run(r, 1, hand(), router=app.router)
    _frame(app)
    p = app.reg["view.inst_amp"]
    assert p.eff_norm == pytest.approx(0.4, abs=1e-4)                # y 200 of 100–350
    p.set_norm(0.9)
    run(r, 3, hand(), router=app.router)
    _frame(app)
    assert p.norm == pytest.approx(0.9) and p.eff_norm == pytest.approx(0.4, abs=1e-4)
    run(r, 1, hand(pos=(0.0, 300.0, 0.0)), router=app.router)
    _frame(app)
    assert p.eff_norm == pytest.approx(0.8, abs=1e-4) and p.norm == pytest.approx(0.9)
    run(r, 1, router=app.router)                    # the hand leaves; the camera stays on
    _frame(app)
    assert r.src.on and not p.modulated and p.norm == pytest.approx(0.9)
    assert p.eff_norm == pytest.approx(0.9)


def test_a_hand_leaving_the_box_releases_its_position_row(app):
    """Audit B1: with the tracker on, the frame the hand is absent its
    axes read NaN, the row calls nothing, and apply() writes the base
    back — the return spring shapes only the DAW output."""
    r = rig()
    k = ax(r, "right.y")
    a = r.s.axes[k]
    a.rest, a.rest_value, a.return_s, a.bounce = "return", 0.0, 0.3, 0.0
    app.table.add(Binding(f"hand:{k}", "view.inst_amp", "position"))
    p = app.reg["view.inst_amp"]
    base = p.norm
    run(r, 1, hand(pos=(0.0, 300.0, 0.0)), router=app.router)
    _frame(app)
    assert p.modulated and p.eff_norm == pytest.approx(0.8, abs=1e-4)
    calls = []
    p_mod = p.modulate
    p.modulate = lambda off: (calls.append(off), p_mod(off))
    run(r, 1, router=app.router)                    # gone, tracker still on
    assert r.src.on and math.isnan(app.router.feeds["hand"][k])
    _frame(app)
    assert calls == [] and not p.modulated
    assert p.eff_norm == pytest.approx(base) and p.norm == pytest.approx(base)
    # the DAW path still springs home from where the hand was
    st = r.io.state[k]
    assert 0.0 < st.y < 0.8
    run(r, 30, router=app.router)
    _frame(app)
    assert st.y == pytest.approx(0.0, abs=0.01) and st.q == 0
    assert calls == [] and p.eff_norm == pytest.approx(base)


def test_a_returning_hand_glides_its_row_back_on_through_the_catch(app):
    """Away, the row is released (the spring is DAW-only); back, the catch
    is live and glides the param from where the spring left it onto the hand."""
    r = rig()
    r.s.catch_s = 0.2
    k = ax(r, "right.y")
    a = r.s.axes[k]
    a.rest, a.rest_value, a.return_s = "return", 0.0, 0.1
    app.table.add(Binding(f"hand:{k}", "view.inst_amp", "position"))
    p = app.reg["view.inst_amp"]
    base = p.norm
    run(r, 1, hand(pos=(0.0, 300.0, 0.0)), router=app.router)
    run(r, 20, router=app.router)                   # away: home at 0
    _frame(app)
    st = r.io.state[k]
    assert st.y == pytest.approx(0.0, abs=0.01) and not p.modulated
    assert p.eff_norm == pytest.approx(base)
    run(r, 1, hand(pos=(0.0, 300.0, 0.0)), router=app.router)   # back, far away
    _frame(app)
    # the catch is live: the row takes the param back at once and glides
    # it onto the hand, so a one-frame tracking dropout costs one frame
    assert 0.0 < st.y < 0.8 and st.follow.mode == st.follow.CATCH and st.follow.live
    assert app.router.feeds["hand"][k] == pytest.approx(st.y) and p.modulated
    assert p.eff_norm == pytest.approx(st.y, abs=1e-4)
    run(r, 20, hand(pos=(0.0, 300.0, 0.0)), router=app.router)
    _frame(app)
    assert st.follow.mode == st.follow.FOLLOW and p.eff_norm == pytest.approx(0.8, abs=1e-3)


def test_the_tracker_going_dark_feeds_none_and_releases_every_row(app):
    r = rig()
    k = ax(r, "right.y")
    app.table.add(Binding(f"hand:{k}", "view.inst_amp", "position"))
    p = app.reg["view.inst_amp"]
    base = p.norm
    run(r, 1, hand(pos=(0.0, 300.0, 0.0)), router=app.router)
    _frame(app)
    assert p.modulated
    r.src.on = False                                 # the camera goes
    run(r, 1, hand(pos=(0.0, 300.0, 0.0)), router=app.router)
    assert app.router.feeds.get("hand") is None
    _frame(app)
    assert not p.modulated and p.eff_norm == pytest.approx(base)


def test_a_return_spring_never_completes_a_learn(app):
    """Learn armed, hand pulled out: the spring moves the DAW output a long
    way, but a learn measures the hand, so nothing is bound."""
    r = rig()
    k = ax(r, "right.y")
    a = r.s.axes[k]
    a.rest, a.rest_value, a.return_s = "return", 0.0, 0.1
    run(r, 1, hand(pos=(0.0, 300.0, 0.0)), learn=app.learn, router=app.router)
    app.learn.arm("view.inst_amp")
    run(r, 1, hand(pos=(0.0, 300.0, 0.0)), learn=app.learn, router=app.router)
    run(r, 30, learn=app.learn, router=app.router)     # gone; y springs 0.8 → 0
    assert r.io.state[k].y == pytest.approx(0.0, abs=0.01)
    assert app.learn.learning == "view.inst_amp" and app.table.owner("view.inst_amp") is None


def test_hold_shapes_the_daw_output_but_never_latches_a_row(app):
    """Audit N6: `rest = hold` keeps the last value on the DAW port; the
    routing row still lets go, so the param returns to its base."""
    r = rig()                                        # every axis rests on hold
    k = ax(r, "right.y")
    app.table.add(Binding(f"hand:{k}", "view.inst_amp", "position"))
    p = app.reg["view.inst_amp"]
    base = p.norm
    run(r, 1, hand(pos=(0.0, 300.0, 0.0)), router=app.router)
    _frame(app)
    assert p.eff_norm == pytest.approx(0.8, abs=1e-4)
    st = r.io.state[k]
    q = st.q
    run(r, 5, router=app.router)
    _frame(app)
    assert st.y == pytest.approx(0.8, abs=1e-4) and st.q == q     # held for the DAW
    assert not st.follow.live and not p.modulated
    assert p.eff_norm == pytest.approx(base)


def test_a_learn_on_a_performed_param_is_held_for_the_prompt(app):
    """Learn onto a param another hand row performs: the row is not written
    over it and not lost — it waits in `pending` for Replace / Keep."""
    t, m = app.table, app.learn
    old = t.add(Binding("hand:3", "view.inst_amp", "position"))
    t.add(Binding("hand:3", "view.bright", "push", 0.5))             # one hand, two params
    m.arm("view.inst_amp")
    m.learn_source("hand:7", when="hand:18")
    assert m.learning is None
    new, existing = m.pending
    assert existing is old and (new.source, new.op, new.when) == ("hand:7", "position", "hand:18")
    assert t.owner("view.inst_amp") is old and "replace?" in m.last
    assert m.resolve_pending(False) is None                          # Keep
    assert m.pending is None and t.owner("view.inst_amp") is old and "kept" in m.last
    t.add(Binding("hand:7", "view.speed", "position"))               # hand:7's old param
    m.arm("view.inst_amp")
    m.learn_source("hand:7")
    new = m.resolve_pending(True)                                    # Replace
    assert new is t.owner("view.inst_amp") and new.source == "hand:7"
    assert old not in t.bindings and "learned view.inst_amp" in m.last
    assert not t.routes_to("view.speed")                             # hand:7 moved here
    assert t.routes_to("view.bright")                                # the other row stays
    assert Bindings.load(t.path, legacy_midi=None).owner("view.inst_amp") is None  # no file
    assert m.resolve_pending(True) is None                           # nothing pending


def test_a_hand_learn_needs_no_midi_adapter(tmp_path):
    """Audit B3: Learn is the host's, not the MIDI adapter's. With no
    MidiIO anywhere — `[midi] enabled = false`, or the adapter failed to
    open — right-click → Learn, move a hand, and the row lands."""
    chain = Analyzer(Analyser())
    reg = build_registry(ViewState(), Control(chain), NS(chain=chain), Library(tmp_path).project)
    table = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)
    learn, router = Learn(reg, table), Router(reg, table)
    r = rig()
    run(r, 1, hand(), learn=learn, router=router)
    learn.arm("view.inst_amp")
    for k in range(1, 8):
        run(r, 1, hand(pos=(2.0 * k, 200.0, 0.0), direction=tilt(0.12 * k)),
            learn=learn, router=router)
    b = table.owner("view.inst_amp")
    assert (b.source, b.op) == ("hand:right.pitch", "position")
    assert learn.learning is None and "learned view.inst_amp" in learn.last
    assert Bindings.load(table.path, legacy_midi=None).owner("view.inst_amp") is None  # the preset's
    run(r, 1, hand(direction=tilt(math.radians(13.0))), learn=learn, router=router)
    router.modulate()
    reg.apply()
    assert reg["view.inst_amp"].eff_norm == pytest.approx((13.0 + 60) / 120, abs=1e-4)


def test_a_held_learn_is_not_fired_again_by_the_hands(app):
    """The hands adapter keys off `learn.learning`, which is cleared before
    the referee's answer is known: while the prompt is up, moving hands
    learn nothing more; arming a new learn forgets the held one."""
    r = rig()
    t, m = app.table, app.learn
    old = t.add(Binding("hand:3", "view.inst_amp", "position"))
    run(r, 1, hand(), learn=m, router=app.router)
    m.arm("view.inst_amp")
    for k in range(1, 8):                                            # R pitch wins the learn
        run(r, 1, hand(pos=(2.0 * k, 200.0, 0.0), direction=tilt(0.12 * k)),
            learn=m, router=app.router)
    assert m.learning is None and m.pending is not None
    held = m.pending
    for k in range(8, 20):                                           # keeps moving: nothing
        run(r, 1, hand(pos=(2.0 * k, 200.0, 0.0), direction=tilt(0.12 * k)),
            learn=m, router=app.router)
    assert m.pending is held and t.owner("view.inst_amp") is old
    assert [b.target for b in t.of("hand")] == ["view.inst_amp"]
    m.arm("view.speed")                                            # a new learn: forgotten
    assert m.pending is None and m.learning == "view.speed"


def test_hand_lanes_modulate(app):
    r = rig()
    p = app.reg["view.inst_amp"]
    base = p.norm
    row = app.table.add(Binding("hand:6", "view.inst_amp", "push", 0.5))   # right.x
    run(r, 1, hand(pos=(220.0, 200.0, 0.0)), router=app.router)
    assert app.router.labels["hand"][6] == "R x"
    app.router.modulate()
    app.reg.apply()
    # x is centred: the axis rests at 0.5, so a hand at the far right pushes
    # half the depth; a row with a rest of its own pushes from there instead
    assert p.eff_norm == pytest.approx(min(base + 0.25, 1.0), abs=1e-9)
    row.rest = 0.0
    app.router.modulate()
    app.reg.apply()
    assert p.eff_norm == pytest.approx(min(base + 0.5, 1.0), abs=1e-9)


# ---------------------------------------------------------------- the page

def test_hands_page_draws_live_and_offline(tmp_path):
    from imgui_bundle import imgui

    from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

    ctx = imgui.create_context()
    try:
        io_ = imgui.get_io()
        io_.display_size = imgui.ImVec2(820, 820)
        io_.backend_flags |= imgui.BackendFlags_.renderer_has_textures
        apply_style()
        load_fonts()
        chain = Analyzer(Analyser())
        control = Control(chain)
        audio = NS(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
        view = ViewState()
        lib = Library(tmp_path, period=0.0)
        reg = build_registry(view, control, audio, lib.project)
        r = rig()
        hands.register(reg, r.s)
        lib.attach(reg)
        panel = Panel(control, audio, view, bank=lib.project, registry=reg, library=lib)
        panel.hand_settings = r.s
        reg["ui.page"].set(PAGE_KEYS.index("hands"))

        def frame():
            imgui.new_frame()
            panel.draw(DT, 60.0)
            imgui.end_frame()

        frame()                                       # tracker off: the setup still draws
        panel.hands = r.io
        run(r, 2, hand("left"), hand("right", direction=tilt(0.3)))
        r.io.start_calibration(5.0)
        for k in range(len(r.s.axes)):
            reg["hands.select"].set(k)
            r.s.axes[k].out = hs.OUTS[k % len(hs.OUTS)]
            r.s.axes[k].rest = hs.RESTS[k % 2]
            frame()
        r.s.axes[0].out, r.s.axes[0].number = "cc14", 99   # a conflict draws its warning
        reg["hands.select"].set(0)
        frame()
    finally:
        imgui.destroy_context(ctx)


# ------------------------------------------------------------- pinch switches

def test_pinch_ratios_are_palm_relative():
    """The same gesture on a big and a small hand reads the same."""
    small = features(hand(tips=(10.0, 20.0, 30.0, 40.0), palm_w=80.0))
    big = features(hand(tips=(20.0, 40.0, 60.0, 80.0), palm_w=160.0))
    for f in hands.PINCHES:
        assert small[f"pinch_{f}"] == pytest.approx(big[f"pinch_{f}"])
    assert small["pinch_index"] == pytest.approx(0.125)
    assert small["pinch_pinky"] == pytest.approx(0.5)


def test_pinch_ratios_fall_back_to_a_nominal_palm():
    f = features(hand(tips=(17.0, 0.0, 0.0, 0.0)))     # width 0: use PALM_W
    assert f["pinch_index"] == pytest.approx(17.0 / hands.PALM_W)


def test_a_palm_only_hand_reports_no_pinches():
    """The SDK-less namespaces older tests build must still work."""
    assert hands.pinches(hand()) == {}
    assert "pinch_index" not in features(hand())


def test_pinch_gate_needs_the_wider_gap_to_let_go():
    g, t = hands.Gate(), 0.0
    step = lambda d: g.step(d, t, close=0.3, open_=0.5, hold=0.0)
    assert not step(0.4)          # above close: still open
    assert step(0.25)             # closes
    assert step(0.4)              # between the two: hysteresis holds it shut
    assert not step(0.55)         # past release


def test_pinch_gate_debounces_a_single_noisy_frame():
    g = hands.Gate()
    close = {"close": 0.3, "open_": 0.5, "hold": 0.05}
    assert not g.step(0.1, 0.00, **close)     # edge starts timing
    assert not g.step(0.1, 0.02, **close)     # not held long enough
    assert g.step(0.1, 0.06, **close)         # held: it counts
    # one stray open frame is ignored
    assert g.step(0.9, 0.07, **close)


def test_pinches_drive_lanes_and_notes():
    r = rig()
    open_hand = lambda: hand(tips=(60.0, 60.0, 60.0, 60.0), palm_w=100.0)
    # thumb to index only
    pinched = lambda: hand(tips=(10.0, 60.0, 60.0, 60.0), palm_w=100.0)
    run(r, 2, open_hand())
    assert r.io.lanes()[14:] == [0.0] * 8
    msgs = run(r, 2, pinched())
    on = [m for m in msgs if m.type == "note_on"]
    assert len(on) == 1 and on[0].note == 104          # right index = 100 + 4
    assert r.io.gates["right"]["index"].on
    assert r.io.lanes()[18] == 1.0                     # R ind: 14 + 4
    off = [m for m in run(r, 2, open_hand()) if m.type == "note_off"]
    assert len(off) == 1 and off[0].note == 104
    assert not r.io.gates["right"]["index"].on


def test_a_hand_that_leaves_releases_its_pinches():
    r = rig()
    msgs = run(r, 2, hand(tips=(10.0, 10.0, 60.0, 60.0), palm_w=100.0))
    on = sorted(m.note for m in msgs if m.type == "note_on")
    assert on == [104, 105, 121]          # index, middle, and the presence note
    off = [m for m in run(r, 2) if m.type == "note_off"]   # no hands at all
    assert sorted(m.note for m in off) == [104, 105, 121]  # index, middle, presence
    assert r.io.lanes()[14:] == [0.0] * 8


def test_pinch_gates_can_be_turned_off():
    r = rig(pinch_gates=False)
    msgs = run(r, 2, hand(tips=(10.0, 10.0, 10.0, 10.0), palm_w=100.0))
    assert not any(m.note >= 100 and m.note < 120 for m in msgs if m.type == "note_on")
    assert r.io.lanes()[14:] == [0.0] * 8


def test_pinch_ratios_can_be_axes_too():
    r = rig(dofs=["x", "pinch_index"])
    run(r, 2, hand(tips=(10.0, 60.0, 60.0, 60.0), palm_w=100.0))
    y = r.io.state[r.io.axis("right.pinch_index")].y
    assert y is not None and y < 0.2          # a closed pinch sits near the bottom


@pytest.mark.parametrize("cfg,why", [
    ({"pinch_note": 125}, "past 127"),
    ({"pinch_note": 118}, "collide"),      # 118–125 straddles presence 120–121
])
def test_bad_pinch_notes_are_refused(cfg, why):
    with pytest.raises(ValueError, match=why):
        HandSettings.from_config(cfg)


def test_pinch_notes_may_sit_where_presence_is_off():
    HandSettings.from_config({"pinch_note": 118, "presence": False})


# ------------------------------------------------- a pinch gating an axis

def test_a_pinch_gates_the_axis_so_one_move_means_two_things(app):
    """The point of the switches: pinched hand-up-down positions the param,
    open hand-up-down leaves it alone, and letting go returns it to the
    base — the hand grabs, and gives back (plan 09: hands never yield, and
    a position row springs back when the gate opens)."""
    r = rig()
    gate = 14 + 4                                   # R index, after 12 axes + 2 presence
    app.table.add(Binding("hand:7", "view.inst_amp", "position",     # right.y
                          when=f"hand:{gate}"))
    p = app.reg["view.inst_amp"]
    p.set_norm(0.5)
    wide = {"tips": (60.0, 60.0, 60.0, 60.0), "palm_w": 100.0}
    shut = {"tips": (10.0, 60.0, 60.0, 60.0), "palm_w": 100.0}

    # open hand, moving: the param does not budge
    run(r, 2, hand(pos=(0.0, 300.0, 0.0), **wide), router=app.router)
    _frame(app)
    assert p.norm == pytest.approx(0.5) and not p.modulated

    # pinched, the same height: now it follows
    run(r, 2, hand(pos=(0.0, 300.0, 0.0), **shut), router=app.router)
    _frame(app)
    assert p.eff_norm == pytest.approx(0.8, abs=1e-4) and p.norm == pytest.approx(0.5)

    # still pinched, moving: it tracks
    run(r, 2, hand(pos=(0.0, 200.0, 0.0), **shut), router=app.router)
    _frame(app)
    assert p.eff_norm == pytest.approx(0.4, abs=1e-4)

    # let go and keep moving: back to what the panel says
    run(r, 2, hand(pos=(0.0, 350.0, 0.0), **wide), router=app.router)
    _frame(app)
    assert not p.modulated and p.norm == pytest.approx(0.5)


def test_an_ungated_row_is_untouched_by_the_switches(app):
    r = rig()
    app.table.add(Binding("hand:7", "view.inst_amp", "position"))
    run(r, 2, hand(pos=(0.0, 300.0, 0.0), tips=(60.0,) * 4, palm_w=100.0),
        router=app.router)
    _frame(app)
    assert app.reg["view.inst_amp"].eff_norm == pytest.approx(0.8, abs=1e-4)


def test_a_gate_whose_source_is_dark_holds_the_row_shut(app):
    """No hands at all: the gate must not read as open."""
    r = rig()
    app.table.add(Binding("hand:7", "view.inst_amp", "position", when="hand:18"))
    p = app.reg["view.inst_amp"]
    p.set_norm(0.5)
    run(r, 2, router=app.router)                 # nothing in view
    _frame(app)
    assert p.norm == pytest.approx(0.5) and not p.modulated


def test_learning_while_pinched_gates_the_row_on_that_pinch(app):
    """Pinch, learn, move: the row remembers the thumb as well as the axis."""
    r = rig()
    shut = {"tips": (10.0, 60.0, 60.0, 60.0), "palm_w": 100.0}
    run(r, 1, hand(**shut), learn=app.learn, router=app.router)
    app.learn.arm("view.inst_amp")
    for k in range(1, 8):
        run(r, 1, hand(pos=(2.0 * k, 200.0, 0.0), direction=tilt(0.12 * k), **shut),
            learn=app.learn, router=app.router)
    rows = [b for b in app.table.of("hand") if b.target == "view.inst_amp"]
    assert len(rows) == 1
    assert rows[0].when == "hand:right.pinch.index"


def test_a_hand_learn_writes_the_axis_by_name_on_any_dofs(app):
    """Decision register row 20: a learn writes `hand:<name>` — the same
    row whatever lane the axis sits on — so a preset saved on this rig
    plays on one whose `[hands] dofs` list is ordered differently."""
    r = rig(dofs=["yaw", "pitch"])                  # right pitch is lane 3 here, not 10
    shut = {"tips": (10.0, 60.0, 60.0, 60.0), "palm_w": 100.0}
    run(r, 1, hand(**shut), learn=app.learn, router=app.router)
    app.learn.arm("view.inst_amp")
    for k in range(1, 8):
        run(r, 1, hand(direction=tilt(0.12 * k), **shut), learn=app.learn, router=app.router)
    b = app.table.owner("view.inst_amp")
    assert (b.source, b.when) == ("hand:right.pitch", "hand:right.pinch.index")
    assert app.router.lane(b.source) == ("hand", r.io.axis("right.pitch")) == ("hand", 3)
    assert app.router.describe(b) == "R pitch positions while R ind"


def test_learning_with_an_open_hand_leaves_the_row_ungated(app):
    r = rig()
    wide = {"tips": (60.0, 60.0, 60.0, 60.0), "palm_w": 100.0}
    run(r, 1, hand(**wide), learn=app.learn, router=app.router)
    app.learn.arm("view.inst_amp")
    for k in range(1, 8):
        run(r, 1, hand(pos=(2.0 * k, 200.0, 0.0), direction=tilt(0.12 * k), **wide),
            learn=app.learn, router=app.router)
    rows = [b for b in app.table.of("hand") if b.target == "view.inst_amp"]
    assert len(rows) == 1 and rows[0].when is None


def test_the_learning_hand_chooses_its_own_thumb(app):
    """Both hands pinching: the gate comes from the hand that moved."""
    r = rig()
    shut = {"tips": (10.0, 60.0, 60.0, 60.0), "palm_w": 100.0}
    both = lambda k=0: (hand("left", pos=(-110.0, 200.0, 0.0), **shut),
                        hand("right", pos=(2.0 * k, 200.0, 0.0),
                             direction=tilt(0.12 * k), **shut))
    run(r, 1, *both(), learn=app.learn, router=app.router)
    app.learn.arm("view.inst_amp")
    for k in range(1, 8):
        run(r, 1, *both(k), learn=app.learn, router=app.router)
    rows = [b for b in app.table.of("hand") if b.target == "view.inst_amp"]
    assert rows[0].when == "hand:right.pinch.index"


def test_the_adapter_publishes_its_switches_as_gates(app):
    """The routing UI offers gates without importing anything hands."""
    r = rig()
    run(r, 1, hand(), router=app.router)
    gates = app.router.gates["hand"]
    assert len(gates) == 8
    assert gates[0] == (r.io.gate_lane("left", "index"), "L ind")
    assert gates[-1] == (r.io.gate_lane("right", "pinky"), "R pin")
    # every published gate names a real lane
    lanes = r.io.lanes()
    assert all(0 <= i < len(lanes) for i, _ in gates)
    # and where each lane rests — the axis's *configured* rest value (0.5
    # for a centred axis, 0 for height by default), the switches at 0 — so
    # a push row centred on it never sees a phantom push from an absent hand
    rests = app.router.rests["hand"]
    assert len(rests) == len(lanes)
    assert rests[:len(r.s.axes)] == [a.rest_value for a in r.s.axes]
    assert rests[r.io.axis("left.x")] == 0.5 and rests[r.io.axis("left.y")] == 0.0
    assert rests[len(r.s.axes):] == [0.0] * 10
    r.s.axes[r.io.axis("left.y")].rest_value = 0.2                     # the setup says so
    run(r, 1, hand(), router=app.router)
    assert app.router.rests["hand"][r.io.axis("left.y")] == 0.2
    assert app.router.rest_of(f"hand:{r.io.axis('right.roll')}") == 0.5


# ------------------------------------------------- one rig table (audit N1)

def test_one_defaults_table_for_the_rig(tmp_path):
    """config.load fills the [hands] section from hands.DEFAULTS (config has
    no table of its own), and a bare AxisSettings is the axis from_config
    builds — no second table of defaults anywhere."""
    from hyperspace import config
    from hyperspace.hands import AxisSettings

    assert "hands" not in config.DEFAULTS                 # no table of its own
    (tmp_path / "config.toml").write_text("[hands]\nenabled = true\n")
    cfg = config.load(tmp_path / "config.toml")["hands"]
    assert set(cfg) == set(hands.DEFAULTS) and cfg["enabled"] is True
    assert cfg["calibration"] == str(tmp_path / "hands.json")
    cfg["dofs"].append("grab")                             # a copy: the table is untouched
    assert hands.DEFAULTS["dofs"] == hands.core.DEFAULT_DOFS and "grab" not in hands.core.DEFAULT_DOFS
    filled = hands.core.rig({"dofs": ["x"]})
    filled["dofs"].append("y")
    assert hands.DEFAULTS["dofs"][:2] == ["x", "y"] and len(hands.DEFAULTS["dofs"]) == 6
    s = HandSettings.from_config()
    for a in s.axes:
        bare = AxisSettings(a.side, a.feature, number=a.number)
        assert bare == a, a.name
    roll, y = AxisSettings("right", "roll"), AxisSettings("left", "y")
    assert (roll.bipolar, roll.deadzone, roll.rest_value) == (True, 0.04, 0.5)
    assert (y.bipolar, y.deadzone, y.rest_value) == (False, 0.0, 0.0)
    assert (y.channel, y.number) == (hands.DEFAULTS["channel"], hands.DEFAULTS["cc"])
    # an explicit shape is kept
    assert AxisSettings("left", "y", bipolar=True).rest_value == 0.5


# --------------------------------------------- one layout, published once (N2)

class FakeRouter:
    def __init__(self):
        self.fed = []
        self.labels, self.gates, self.rests, self.names = {}, {}, {}, {}

    def feed(self, scheme, vec):
        self.fed.append((scheme, vec))


def test_the_layout_is_one_object_published_once_and_rests_on_change():
    r = rig()
    router = FakeRouter()
    run(r, 1, hand(), router=router)
    lay = r.io.layout
    assert router.labels["hand"] is lay.names and router.gates["hand"] is lay.gates
    assert router.names["hand"] is lay.index                 # name → lane (row 20)
    assert r.io.lane_names is lay.names
    # every lane has one address name: the axes as dofs spells them, the
    # presence lanes, the switches
    assert lay.addresses == hands.addresses(r.s.axes) == hands.default_addresses()
    assert lay.index == {n: i for i, n in enumerate(lay.addresses)} and len(lay.index) == 22
    assert lay.index["right.roll"] == ax(r, "right.roll")
    assert lay.index["left.present"] == lay.presence["left"]
    assert lay.index["right.pinch.index"] == r.io.gate_lane("right", "index")
    assert [r.io.address(i) for i in (0, 11, 13, 21)] == [
        "hand:left.x", "hand:right.yaw", "hand:right.present", "hand:right.pinch.pinky"]
    rests = router.rests["hand"]
    assert len(lay.names) == len(rests) == len(r.io.lanes()) == lay.n == 22
    # the index maps agree with the vector lanes() fills
    lanes = r.io.lanes()
    assert lanes[lay.presence["right"]] == 1.0 and lanes[lay.presence["left"]] == 0.0
    assert all(lay.gate[(s, f)] == r.io.gate_lane(s, f) for s in hands.SIDES
               for f in hands.PINCHES)
    assert lay.gates == [(lay.gate[(s, f)], lay.names[lay.gate[(s, f)]])
                         for s in hands.SIDES for f in hands.PINCHES]
    run(r, 3, hand(), router=router)
    # nothing republished while nothing changed: the same objects
    assert router.labels["hand"] is lay.names and router.rests["hand"] is rests
    assert router.names["hand"] is lay.index
    assert len(router.fed) == 4                       # feed is every frame
    r.s.axes[ax(r, "left.y")].rest_value = 0.3        # the setup moved a rest
    run(r, 1, hand(), router=router)
    assert router.rests["hand"] is not rests
    assert router.rests["hand"][ax(r, "left.y")] == 0.3
    # a router that lost the layout (a fresh one) gets it again
    fresh = FakeRouter()
    run(r, 1, hand(), router=fresh)
    assert fresh.labels["hand"] is lay.names and fresh.rests["hand"] == router.rests["hand"]
    assert fresh.names["hand"] is lay.index
    # a router with no `names` (one that resolves none) still gets the rest
    bare = FakeRouter()
    del bare.names
    run(r, 1, hand(), router=bare)
    assert bare.labels["hand"] is lay.names and not hasattr(bare, "names")
    # a Layout from before a hot reload (no address map) is rebuilt at publish
    old = r.io.layout
    object.__setattr__(r.io, "layout", NS(names=old.names, gates=old.gates, n=old.n,
                                          n_axes=old.n_axes, presence=old.presence,
                                          gate=old.gate))
    again = FakeRouter()
    run(r, 1, hand(), router=again)
    assert again.names["hand"] == old.index and r.io.layout.addresses == old.addresses


# ----------------------------------------- the DAW port comes back (N4)

class FlakyOut:
    name = "Fake DAW"

    def __init__(self):
        self.sent, self.broken, self.closed = [], False, False

    def send(self, m):
        if self.broken:
            raise OSError("port yanked")
        self.sent.append(m)

    def close(self):
        self.closed = True


class Backend:
    """mido's output side as the tests see it: a port list and an opener."""

    def __init__(self, names):
        self.names, self.opened, self.fail = list(names), [], False

    def get_output_names(self):
        return list(self.names)

    def open_output(self, name, virtual=False):
        if self.fail:
            raise RuntimeError("no backend")
        self.opened.append((name, virtual))
        return FlakyOut()


def daw_rig(monkeypatch, names):
    from hyperspace.hands import core

    be = Backend(names)
    monkeypatch.setattr(core.mido, "get_output_names", be.get_output_names)
    monkeypatch.setattr(core.mido, "open_output", be.open_output)
    settings = HandSettings.from_config({"out": "fake daw"})
    settings.catch_s, settings.rate, settings.pinch_hold = 0.0, 0, 0.0
    clock = Clock()
    src = FakeSource(clock)
    io = HandsIO(settings, {"out": "fake daw"}, source=src, clock=clock)
    return NS(io=io, src=src, clock=clock, s=settings, be=be)


def notes(msgs, kind="note_on"):
    return [m.note for m in msgs if m.type == kind]


def test_a_lost_daw_port_is_looked_for_again_and_the_daw_resynced(monkeypatch, capsys):
    from hyperspace.hands import core

    r = daw_rig(monkeypatch, ["Fake DAW 1"])
    io, be, clock = r.io, r.be, r.clock
    assert be.opened == [("Fake DAW 1", False)] and io.out_name == "Fake DAW" and io.error == ""
    pinched = hand(tips=(10.0, 80.0, 80.0, 80.0), palm_w=100.0)   # R index closed
    run(r, 1, pinched)
    port = io.out
    assert 120 + 1 in notes(port.sent) and 100 + 4 in notes(port.sent)   # presence, R ind
    assert io.last                                                       # something went out
    last = io.last
    # the DAW goes away: the port fails, is closed, and nothing is said to have been sent
    port.broken = True
    be.names = []
    run(r, 1, hand(pos=(50.0, 300.0, 0.0), tips=(10.0, 80.0, 80.0, 80.0), palm_w=100.0))
    assert io.out is None and io.error.startswith("send: port yanked")
    assert port.closed and io.last == last
    # a retry while the DAW is still gone makes no virtual port in its place
    clock.t += core.RECONNECT_S
    run(r, 1, hand(pos=(60.0, 310.0, 0.0), tips=(10.0, 80.0, 80.0, 80.0), palm_w=100.0))
    assert io.out is None and io.error == "out 'fake daw': no such port" and len(be.opened) == 1
    # the DAW is back: the port reopens, the notes that are on go out again,
    # and every axis resends its value rather than waiting for a change
    be.names = ["Fake DAW 1"]
    clock.t += core.RECONNECT_S
    run(r, 1, hand(pos=(60.0, 310.0, 0.0), tips=(10.0, 80.0, 80.0, 80.0), palm_w=100.0))
    assert io.out is not None and io.out is not port and be.opened[-1] == ("Fake DAW 1", False)
    assert io.error == ""
    assert notes(io.out.sent)[:2] == [121, 104]                          # presence, R index
    ccs = [m for m in io.out.sent if m.type == "control_change"]
    assert {m.control for m in ccs} >= {a.number for a in r.s.axes if a.side == "right"}
    # the backend refusing: said once on stderr, retried every interval
    be.fail = True
    io.out.broken = True
    run(r, 1, hand(pos=(80.0, 330.0, 0.0)))
    for _ in range(3):
        clock.t += core.RECONNECT_S
        run(r, 1, hand(pos=(90.0, 330.0, 0.0)))
    assert io.out is None and io.error == "out 'fake daw': no backend"
    assert capsys.readouterr().err.count("no backend") == 1
    be.fail = False
    clock.t += core.RECONNECT_S
    run(r, 1, hand(pos=(99.0, 330.0, 0.0)))
    assert io.out is not None and io.error == ""


def test_a_virtual_port_is_made_again_when_it_fails(monkeypatch):
    from hyperspace.hands import core

    r = daw_rig(monkeypatch, [])                       # nothing to join: a virtual port
    io, be, clock = r.io, r.be, r.clock
    assert be.opened == [("fake daw", True)] and io.error == ""
    run(r, 1, hand())
    io.out.broken = True
    run(r, 1, hand(pos=(50.0, 300.0, 0.0)))
    assert io.out is None
    clock.t += core.RECONNECT_S
    run(r, 1, hand(pos=(60.0, 300.0, 0.0)))
    assert io.out is not None and be.opened[-1] == ("fake daw", True) and io.error == ""


def test_an_injected_port_is_the_callers_and_never_reopened():
    r = rig()
    run(r, 1, hand())
    out = r.io.out
    out.send = lambda m: (_ for _ in ()).throw(OSError("gone"))
    run(r, 1, hand(pos=(50.0, 300.0, 0.0)))
    assert r.io.out is None and r.io.error.startswith("send: gone")
    r.clock.t += 10.0
    run(r, 1, hand(pos=(60.0, 300.0, 0.0)))
    assert r.io.out is None and r.io.out_name == ""


# ---------------------------------------------------------------- the interaction box (plan 18 WP1)

BOX = {"x": (-200.0, 200.0), "y": (80.0, 400.0), "z": (-150.0, 150.0)}
# a calibration file as a build before plan 18 wrote it — and not in this
# build's own formatting, so "the bytes are the same" proves nothing rewrote it
OLD_FILE = ('{"schema": "hyperspace.hands/1",\n'
            '   "axes": {"right.y": {"lo": 150.0, "hi": 250.0},'
            ' "left.x": {"lo": -214.2, "hi": 18.5}}}\n')


class SkelSource(FakeSource):
    """A FakeSource that also hands out a skeleton per hand (`snapshot`)."""

    def snapshot(self):
        return self.seq, self.clock(), self.hands, {s: {"palm": s} for s in self.hands}


def boxed(tmp_path=None, box=BOX, **cfg):
    r = rig(tmp_path, **cfg)
    r.io.box = dict(box) if box is not None else None
    return r


def pct(vals):
    """The sweep's own rule: the 2nd and 98th percentile."""
    v = sorted(vals)
    return v[int(0.02 * (len(v) - 1))], v[int(0.98 * (len(v) - 1))]


def tri(j, n):
    return (j % n) / (n - 1)


def wide(j, side="right"):
    """A hand sweeping x 20…200, y 120…320, z −90…90 mm, out of step."""
    return hand(side, pos=(20.0 + 180.0 * tri(j, 20), 120.0 + 200.0 * tri(j, 15),
                           -90.0 + 180.0 * tri(j, 12)))


def sweep(r, path, seconds=1.0):
    """A whole calibration sweep of `path(j)` → hands; the palms it saw."""
    r.io.start_calibration(seconds)
    seen, j = [], 0
    while r.io._cal is not None:
        assert j < 1000
        hs_ = path(j)
        hs_ = hs_ if isinstance(hs_, tuple) else (hs_,)
        seen += [(h.palm.position.x, h.palm.position.y, h.palm.position.z) for h in hs_]
        run(r, 1, *hs_)
        j += 1
    return seen


def same(a, b):
    return len(a) == len(b) and all((math.isnan(x) and math.isnan(y)) or x == y
                                    for x, y in zip(a, b))


def test_no_box_is_todays_presence():
    """No box (the default): a palm far outside every range is present and
    reads 1.0, as before plan 18 — and a box that holds everything changes
    no lane and no message, to the float."""
    r = rig()
    assert r.io.box is None and r.io.outside == {"left": None, "right": None}
    run(r, 2, hand(pos=(600.0, 900.0, 500.0)))
    assert r.io.present == {"left": False, "right": True}
    lanes = r.io.lanes()
    assert [lanes[ax(r, f"right.{c}")] for c in "xyz"] == [1.0, 1.0, 1.0]
    assert r.io.outside["right"] is None and r.io.frame["right"]["x"] == 600.0
    a, b = rig(), boxed(box={c: (-1e6, 1e6) for c in "xyz"})
    for q in (a, b):
        q.s.smooth, q.s.response, q.s.catch_s = 1.0, 4.0, 0.15     # the real filter and catch
    for j in range(90):
        hs_ = [] if 30 <= j < 40 else [                      # ten frames away, then back
            hand("left", pos=(-300.0 + 9.0 * j, 60.0 + 5.0 * j, 200.0 - 4.0 * j),
                 tips=(10.0 + j, 80.0, 80.0, 80.0), palm_w=85.0),
            hand("right", pos=(700.0 - 11.0 * j, 950.0 - 9.0 * j, -400.0 + 7.0 * j),
                 direction=tilt(0.01 * j))]
        assert run(a, 1, *hs_) == run(b, 1, *hs_)
        assert same(a.io.lanes(), b.io.lanes()) and a.io.present == b.io.present
        assert a.io.frame == b.io.frame and b.io.outside == {"left": None, "right": None}


def test_a_hand_outside_the_box_reads_absent_everywhere():
    r = boxed()
    r.src = r.io.source = SkelSource(r.clock)
    pinched = {"tips": (10.0, 80.0, 80.0, 80.0), "palm_w": 85.0}
    msgs = run(r, 2, hand(pos=(100.0, 200.0, 0.0), **pinched))
    assert r.io.present["right"] and r.io.gates["right"]["index"].on
    assert "right" in r.io.skeleton and r.io.outside["right"] is None
    assert {(m.type, m.note) for m in msgs if m.type == "note_on"} == {
        ("note_on", 121), ("note_on", 104)}
    k = ax(r, "right.y")
    assert r.io.lanes()[k] == pytest.approx(0.4)
    msgs = run(r, 1, hand(pos=(300.0, 200.0, 0.0), **pinched))     # tracked, 100 mm past a face
    lanes = r.io.lanes()
    assert all(math.isnan(u) for u in lanes[:12])                   # every axis lets go
    assert lanes[r.io.layout.presence["right"]] == 0.0
    assert lanes[r.io.gate_lane("right", "index")] == 0.0
    assert not r.io.present["right"] and not r.io.gates["right"]["index"].on
    assert {(m.type, m.note) for m in msgs} == {("note_off", 121), ("note_off", 104)}
    assert r.io.skeleton == {} and r.io.frame["right"] is None
    assert r.io.outside["right"]["x"] == 300.0 and r.io.outside["left"] is None
    run(r, 1)                                                        # and gone altogether
    assert r.io.outside == {"left": None, "right": None}


def test_a_hand_outside_the_box_releases_its_rows_and_the_base_returns(app):
    """B1 with the box as the cause: the frame the palm is past a face —
    still tracked — a position row and a push row both call nothing and
    apply() writes the bases back."""
    r = boxed()
    ky, kx = ax(r, "right.y"), ax(r, "right.x")
    app.table.add(Binding(f"hand:{ky}", "view.inst_amp", "position"))
    app.table.add(Binding(f"hand:{kx}", "view.speed", "push", 0.5))
    p, q = app.reg["view.inst_amp"], app.reg["view.speed"]
    bases = p.norm, q.norm
    run(r, 1, hand(pos=(180.0, 300.0, 0.0)), router=app.router)
    _frame(app)
    assert p.modulated and p.eff_norm == pytest.approx(0.8, abs=1e-4)
    assert q.modulated and q.eff_norm != pytest.approx(bases[1])
    calls = []
    for prm in (p, q):
        real = prm.modulate
        prm.modulate = lambda off, real=real: (calls.append(off), real(off))
    run(r, 1, hand(pos=(260.0, 300.0, 0.0)), router=app.router)    # out through the x face
    assert r.src.on and r.io.outside["right"] is not None
    assert math.isnan(app.router.feeds["hand"][ky]) and math.isnan(app.router.feeds["hand"][kx])
    _frame(app)
    assert calls == [] and not p.modulated and not q.modulated
    assert (p.eff_norm, q.eff_norm) == pytest.approx(bases)
    assert (p.norm, q.norm) == pytest.approx(bases)


def test_the_boxs_edge_has_hysteresis():
    r = boxed()
    at = lambda x: run(r, 1, hand(pos=(x, 200.0, 0.0)))
    at(190.0)
    assert r.io.present["right"]
    flips = []
    for j in range(40):                              # ±5 mm about the face at 200
        flips += at(195.0 if j % 2 else 205.0)
        assert r.io.present["right"] and r.io.outside["right"] is None
    assert [m for m in flips if m.type in ("note_on", "note_off")] == []
    at(200.0 + hands.core.BOX_EDGE - 0.5)
    assert r.io.present["right"]                     # still in, just short of the edge
    at(200.0 + hands.core.BOX_EDGE + 0.5)
    assert not r.io.present["right"] and r.io.outside["right"] is not None
    for j in range(40):                              # out: hovering past the face stays out
        at(200.5 if j % 2 else 210.0)
        assert not r.io.present["right"]
    at(199.5)                                        # in only inside the face
    assert r.io.present["right"] and r.io.outside["right"] is None
    # every face, and both directions of each
    for c, (lo, hi) in BOX.items():
        for face, sign in ((lo, -1.0), (hi, 1.0)):
            pos = {"x": 0.0, "y": 200.0, "z": 0.0}
            f = lambda d, c=c, face=face, sign=sign, pos=pos: {**pos, c: face + sign * d}
            assert hands.core.inside(BOX, f(0.0)) and not hands.core.inside(BOX, f(0.1))
            assert hands.core.inside(BOX, f(hands.core.BOX_EDGE), hands.core.BOX_EDGE)
            assert not hands.core.inside(BOX, f(hands.core.BOX_EDGE + 0.1), hands.core.BOX_EDGE)


def test_a_hand_re_entering_the_box_is_caught_not_jumped(app):
    """Out through a face and back: the Follower catches the hand as it
    catches one the tracker lost — live on the first frame back, gliding."""
    r = boxed()
    r.s.catch_s = 0.2
    k = ax(r, "right.y")
    a = r.s.axes[k]
    a.rest, a.rest_value, a.return_s = "return", 0.0, 0.1
    app.table.add(Binding(f"hand:{k}", "view.inst_amp", "position"))
    p = app.reg["view.inst_amp"]
    base = p.norm
    run(r, 1, hand(pos=(0.0, 300.0, 0.0)), router=app.router)
    run(r, 20, hand(pos=(300.0, 300.0, 0.0)), router=app.router)   # tracked, outside: home at 0
    _frame(app)
    st = r.io.state[k]
    assert st.y == pytest.approx(0.0, abs=0.01) and not st.follow.live
    assert not p.modulated and p.eff_norm == pytest.approx(base)
    run(r, 1, hand(pos=(150.0, 300.0, 0.0)), router=app.router)    # back inside
    _frame(app)
    assert st.follow.mode == st.follow.CATCH and st.follow.live and 0.0 < st.y < 0.8
    assert app.router.feeds["hand"][k] == pytest.approx(st.y) and p.modulated
    assert p.eff_norm == pytest.approx(st.y, abs=1e-4)
    ys = [st.y]
    for _ in range(20):
        run(r, 1, hand(pos=(150.0, 300.0, 0.0)), router=app.router)
        ys.append(st.y)
    _frame(app)
    assert ys == sorted(ys) and max(b - a for a, b in itertools.pairwise(ys)) < 0.2
    assert st.follow.mode == st.follow.FOLLOW and p.eff_norm == pytest.approx(0.8, abs=1e-3)


def test_an_open_coordinate_bounds_nothing(tmp_path):
    (tmp_path / "hands.json").write_text(json.dumps({
        "schema": "hyperspace.hands/2", "axes": {},
        "box": {"x": [-200, 200], "y": None, "z": [-150, 150]}}))
    r = rig(tmp_path)
    assert r.io.box == {"x": (-200.0, 200.0), "y": None, "z": (-150.0, 150.0)}
    for y in (-50.0, 5.0, 900.0, 5000.0):
        run(r, 1, hand(pos=(0.0, y, 0.0)))
        assert r.io.present["right"], y
    run(r, 1, hand(pos=(0.0, 900.0, 200.0)))         # the bounded ones still bound
    assert not r.io.present["right"] and r.io.outside["right"]["z"] == 200.0


def test_the_sweep_sets_the_box_with_its_margin_and_a_symmetric_x(tmp_path):
    r = rig(tmp_path)
    seen = sweep(r, wide)                             # the right hand only
    xs, ys, zs = (pct([p[k] for p in seen]) for k in range(3))
    m = hands.core.BOX_MARGIN
    assert r.io.box == {"x": (-(xs[1] + m), xs[1] + m),          # symmetric about the camera
                        "y": (ys[0] - m, ys[1] + m), "z": (zs[0] - m, zs[1] + m)}
    assert xs[1] > 190 and ys[0] < 130 and zs[1] > 80            # the sweep was the wide one
    bx, by, bz = (r.io.box[c] for c in "xyz")
    assert r.io.cal_note.startswith("calibrated 3 axes, 9 not reached · box "
                                    f"{bx[1] - bx[0]:.0f} × {by[1] - by[0]:.0f} × "
                                    f"{bz[1] - bz[0]:.0f} mm")
    saved = json.loads((tmp_path / "hands.json").read_text())
    assert saved["schema"] == "hyperspace.hands/2"
    assert saved["box"]["x"] == [round(-(xs[1] + m), 3), round(xs[1] + m, 3)]
    # the other hand, never swept, is inside on its own side
    run(r, 1, hand("left", pos=(-xs[1], 200.0, 0.0)), hand("right", pos=(xs[1], ys[1], zs[0])))
    assert r.io.present == {"left": True, "right": True}
    # and a hand at an axis's end stop is still in: the box ends a margin past it
    st = r.io.state[ax(r, "right.x")]
    assert st.hi == pytest.approx(xs[1]) and r.io.lanes()[ax(r, "right.x")] == pytest.approx(1.0)


def test_a_coordinate_not_swept_is_left_open(tmp_path):
    r = rig(tmp_path)
    sweep(r, lambda j: hand(pos=(60.0 + 40.0 * tri(j, 9), 120.0 + 200.0 * tri(j, 15),
                                 -90.0 + 180.0 * tri(j, 12))))    # 40 mm sideways: a slot
    assert r.io.box["x"] is None and r.io.box["y"] is not None and r.io.box["z"] is not None
    assert r.io.cal_note.endswith("box: x open (not swept)")
    run(r, 1, hand(pos=(900.0, 200.0, 0.0)))
    assert r.io.present["right"]                      # x bounds nothing
    sweep(r, lambda j: hand(pos=(0.0, 150.0 + 100.0 * tri(j, 35), 0.0)))   # nothing wide enough
    assert r.io.box is None and r.io.cal_note.endswith("box: open (not swept)")
    assert json.loads((tmp_path / "hands.json").read_text())["box"] is None
    # a sweep that saw no hand leaves the box as it was
    r.io.box = dict(BOX)
    sweep(r, lambda j: ())
    assert r.io.box == BOX and "box left as it was" in r.io.cal_note


def test_the_box_is_not_applied_during_a_sweep(tmp_path):
    tight = {"x": (-50.0, 50.0), "y": (150.0, 250.0), "z": (-50.0, 50.0)}
    r = boxed(tmp_path, tight)
    run(r, 1, wide(19))
    assert not r.io.present["right"]                  # x 200: well outside the tight box
    r.io.start_calibration(1.0)
    j = 0
    while r.io._cal is not None:
        run(r, 1, wide(j))
        if r.io._cal is not None:
            assert r.io.present["right"] and r.io.outside["right"] is None, j
        j += 1
    for c in "xyz":
        assert r.io.box[c][0] < tight[c][0] and r.io.box[c][1] > tight[c][1]
    run(r, 1, wide(19))
    assert r.io.present["right"]


def test_the_palm_is_sampled_whatever_the_dofs(tmp_path):
    r = rig(tmp_path, dofs=["roll", "pitch"])
    assert not {a.feature for a in r.io.axes} & {"x", "y", "z"}
    seen = sweep(r, wide)
    assert r.io.box is not None and all(r.io.box[c] is not None for c in "xyz")
    assert r.io.box["y"] == (pct([p[1] for p in seen])[0] - hands.core.BOX_MARGIN,
                             pct([p[1] for p in seen])[1] + hands.core.BOX_MARGIN)
    run(r, 1, hand(pos=(0.0, 900.0, 0.0)))
    assert not r.io.present["right"]


def test_reset_ranges_opens_the_box(tmp_path):
    r = rig(tmp_path)
    sweep(r, wide)
    assert r.io.box is not None and json.loads((tmp_path / "hands.json").read_text())["box"]
    r.io.reset_ranges()
    assert r.io.box is None and r.io.cal_note == "ranges back to the defaults, box open"
    saved = json.loads((tmp_path / "hands.json").read_text())
    assert "box" in saved and saved["box"] is None
    run(r, 1, hand(pos=(600.0, 900.0, 500.0)))
    assert r.io.present["right"]
    assert rig(tmp_path).io.box is None


def test_an_old_hands_json_reads_as_before_and_is_not_rewritten_at_load(tmp_path, capsys):
    path = tmp_path / "hands.json"
    path.write_text(OLD_FILE)
    then = 1_600_000_000 * 10**9
    os.utime(path, ns=(then, then))
    r = rig(tmp_path)
    assert r.io.box is None
    st = r.io.state[ax(r, "right.y")]
    assert (st.lo, st.hi) == (150.0, 250.0)
    assert (r.io.state[ax(r, "left.x")].lo, r.io.state[ax(r, "left.x")].hi) == (-214.2, 18.5)
    assert (r.io.state[ax(r, "right.x")].lo, r.io.state[ax(r, "right.x")].hi) == (-20.0, 220.0)
    for j in range(60):
        run(r, 1, hand(pos=(600.0 - j, 900.0, 500.0)), hand("left"))
    assert r.io.present == {"left": True, "right": True}             # no bounds
    assert path.read_text() == OLD_FILE and path.stat().st_mtime_ns == then
    assert [p.name for p in tmp_path.iterdir()] == ["hands.json"]    # and no copy made
    assert capsys.readouterr().err == ""


def test_the_first_rewrite_of_an_old_file_keeps_a_backup(tmp_path):
    path, bak = tmp_path / "hands.json", tmp_path / "hands.json.bak-v1"
    path.write_text(OLD_FILE)
    r = rig(tmp_path)
    sweep(r, wide)                                    # the first save of this build
    assert bak.read_text() == OLD_FILE
    assert json.loads(path.read_text())["schema"] == "hyperspace.hands/2"
    assert "the old file kept as hands.json.bak-v1" in r.io.cal_note
    sweep(r, wide)                                    # a /2 file now: no second copy
    r.io.reset_ranges()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["hands.json", "hands.json.bak-v1"]
    assert bak.read_text() == OLD_FILE and "kept" not in r.io.cal_note
    # a name already taken — an older backup, the owner's own copy — is never overwritten
    path.write_text(OLD_FILE.replace("150.0", "151.0"))
    rig(tmp_path).io.reset_ranges()
    assert bak.read_text() == OLD_FILE
    more = [p for p in tmp_path.iterdir() if p.name.startswith("hands.json.bak-v1-")]
    assert len(more) == 1 and more[0].read_text() == OLD_FILE.replace("150.0", "151.0")
    assert re.fullmatch(r"hands\.json\.bak-v1-\d{8}-\d{6}", more[0].name)
    path.write_text("not json at all")                # a third in the same second: still kept
    rig(tmp_path).io.reset_ranges()
    baks = {p.name: p.read_text() for p in tmp_path.iterdir() if ".bak-" in p.name}
    assert len(baks) == 3 and "not json at all" in baks.values()
    assert json.loads(path.read_text())["box"] is None
    # no file yet: nothing to keep
    fresh = tmp_path / "fresh"
    rig(fresh).io.reset_ranges()
    assert [p.name for p in fresh.iterdir()] == ["hands.json"]


def test_a_backup_that_cannot_be_made_never_stops_the_save(tmp_path, monkeypatch):
    path = tmp_path / "hands.json"
    path.write_text(OLD_FILE)
    r = rig(tmp_path)

    def refuse(*a, **k):
        raise PermissionError("read-only folder")

    monkeypatch.setattr(hands.core, "_keep", refuse)
    sweep(r, wide)
    saved = json.loads(path.read_text())
    assert saved["schema"] == "hyperspace.hands/2" and saved["box"] is not None
    assert "no backup of the old file: read-only folder" in r.io.cal_note
    assert "calibrated" in r.io.cal_note
    assert [p.name for p in tmp_path.iterdir()] == ["hands.json"]


def test_a_malformed_box_opens_and_says_so(tmp_path, capsys):
    path = tmp_path / "hands.json"

    def load(box):
        path.write_text(json.dumps({"schema": "hyperspace.hands/2", "axes": {}, "box": box}))
        capsys.readouterr()
        r = rig(tmp_path)
        return r, capsys.readouterr().err.splitlines()

    r, said = load({"x": [5, 1], "y": "tall", "z": [-150, 150]})
    assert r.io.box == {"x": None, "y": None, "z": (-150.0, 150.0)}
    assert len(said) == 2 and said[0].startswith("hands: hands.json: box.x:")
    assert said[1].startswith("hands: hands.json: box.y:")
    run(r, 1, hand(pos=(900.0, 900.0, 0.0)))
    assert r.io.present["right"]                      # the bad coordinates bound nothing
    run(r, 1, hand(pos=(900.0, 900.0, 300.0)))
    assert not r.io.present["right"]                  # the good one still does
    r, said = load({"x": [-200, 200], "y": [80, 400]})              # a missing pair
    assert r.io.box == {"x": (-200.0, 200.0), "y": (80.0, 400.0), "z": None}
    assert len(said) == 1 and said[0].startswith("hands: hands.json: box.z:")
    for bad in ([1, 2, 3], [1], [True, 5], [None, 5], ["1", "2"], [3, 3], {"lo": 1, "hi": 2},
                [float("nan"), 5], [0, float("inf")]):
        r, said = load({"x": bad, "y": None, "z": None})
        assert r.io.box is None and len(said) == 1, bad
        run(r, 1, hand(pos=(900.0, 900.0, 900.0)))
        assert r.io.present["right"], bad
    for bad in ("shut", [1, 2], 7):                   # no object at all: no box
        r, said = load(bad)
        assert r.io.box is None and len(said) == 1 and "box:" in said[0], bad
    r, said = load(None)
    assert r.io.box is None and said == []
    r, said = load({"x": None, "y": None, "z": None})
    assert r.io.box is None and said == []


def test_the_box_round_trips_through_the_file(tmp_path):
    r = rig(tmp_path)
    sweep(r, wide)
    again = rig(tmp_path)
    assert again.io.box == {c: tuple(round(n, 3) for n in r.io.box[c]) for c in "xyz"}
    r.io.box = {"x": (-262.0, 262.0), "y": None, "z": (-148.1234567, 131.0)}
    r.io.save_ranges()
    assert rig(tmp_path).io.box == {"x": (-262.0, 262.0), "y": None, "z": (-148.123, 131.0)}
    saved = json.loads((tmp_path / "hands.json").read_text())
    assert saved["box"] == {"x": [-262.0, 262.0], "y": None, "z": [-148.123, 131.0]}
    assert saved["axes"]["right.y"]["hi"] == pytest.approx(r.io.state[ax(r, "right.y")].hi,
                                                           abs=1e-3)
    assert hands.core.load_box(None) is None and hands.core.load_box(tmp_path / "no") is None


def test_two_still_hands_held_apart_are_not_a_sweep(tmp_path):
    """Each hand's own travel is what makes a coordinate swept: two hands
    200 mm apart that never move sideways leave x open, not a slot."""
    r = rig(tmp_path)
    sweep(r, lambda j: (hand("left", pos=(-100.0, 120.0 + 200.0 * tri(j, 15), 0.0)),
                        hand("right", pos=(100.0, 320.0 - 200.0 * tri(j, 15), 60.0))))
    assert r.io.box["x"] is None and r.io.box["z"] is None and r.io.box["y"] is not None
    run(r, 1, hand("left", pos=(-190.0, 200.0, 0.0)), hand("right", pos=(190.0, 200.0, 60.0)))
    assert r.io.present == {"left": True, "right": True}


def test_a_dip_in_confidence_does_not_evict_a_hand_in_the_edge_band():
    """The Schmitt state is the palm's, not presence's: a hand 10 mm past
    a face (in, by the edge) that the confidence floor drops for a frame
    is in again the next, without moving."""
    r = boxed(min_confidence=0.1)
    at = lambda x, conf=1.0: run(r, 1, hand(pos=(x, 200.0, 0.0), conf=conf))
    at(190.0)
    at(210.0)
    assert r.io.present["right"]
    at(210.0, conf=0.05)
    assert not r.io.present["right"] and r.io.outside["right"] is None   # the floor's, not the box's
    at(210.0)
    assert r.io.present["right"]
    run(r, 1)                                         # no hand at all: the state is forgotten
    at(210.0)
    assert not r.io.present["right"] and r.io.outside["right"] is not None


def test_a_save_that_fails_does_not_copy_the_old_file_again(tmp_path, monkeypatch):
    path = tmp_path / "hands.json"
    path.write_text(OLD_FILE)
    r = rig(tmp_path)

    def refuse(*a, **k):
        raise PermissionError("read-only file")

    monkeypatch.setattr(hands.core, "save_calibration", refuse)
    for _ in range(3):
        r.io.reset_ranges()
        assert r.io.cal_note == "save: read-only file"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["hands.json", "hands.json.bak-v1"]
    assert path.read_text() == OLD_FILE == (tmp_path / "hands.json.bak-v1").read_text()


def test_a_frame_without_a_whole_palm_is_no_sample():
    r = rig()
    r.io.start_calibration(1.0)
    r.clock.t += DT
    r.src.seq += 1
    f = features(hand())
    r.src.hands = {"right": ({k: v for k, v in f.items() if k != "z"} | {"y": math.nan}, 1.0),
                   "left": ({**features(hand("left")), "x": math.inf}, 1.0)}
    r.io.settings.axes[:] = [a for a in r.io.axes if a.feature == "roll"]
    r.io.state[:] = r.io.state[:2]
    r.io.poll(DT)
    assert r.io._palm == []


def test_hands_page_draws_the_box_and_a_hand_outside_it(tmp_path):
    from imgui_bundle import imgui

    from hyperspace.hands import panel as hp
    from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

    ctx = imgui.create_context()
    try:
        io_ = imgui.get_io()
        io_.display_size = imgui.ImVec2(820, 820)
        io_.backend_flags |= imgui.BackendFlags_.renderer_has_textures
        apply_style()
        load_fonts()
        chain = Analyzer(Analyser())
        control = Control(chain)
        audio = NS(chain=chain, on=False, mode="", error="", label="", sr=48000.0)
        view = ViewState()
        lib = Library(tmp_path, period=0.0)
        reg = build_registry(view, control, audio, lib.project)
        r = boxed()
        hands.register(reg, r.s)
        lib.attach(reg)
        panel = Panel(control, audio, view, bank=lib.project, registry=reg, library=lib)
        panel.hand_settings = r.s
        reg["ui.page"].set(PAGE_KEYS.index("hands"))
        said = []
        real, header = imgui.text_disabled, imgui.collapsing_header
        imgui.text_disabled = lambda t: (said.append(t), real(t))[1]
        # "feel & calibration" open, so the calibrate block's box line draws
        imgui.collapsing_header = lambda *a, **k: (header(*a, **k), True)[1]

        def frame():
            said.clear()
            imgui.new_frame()
            panel.draw(DT, 60.0)
            imgui.end_frame()

        try:
            frame()                                   # no tracker
            assert not any("L" in s and "R" in s and "●" in s for s in said)
            panel.hands = r.io
            run(r, 2, hand("left", pos=(-100.0, 200.0, 0.0)),
                hand("right", pos=(300.0, 380.0, 60.0)))             # the right one outside
            assert r.io.present == {"left": True, "right": False} and r.io.outside["right"]
            frame()
            assert hp._ins(r.io) == "L● R◌" and any("L● R◌" in s for s in said)
            assert any(s.startswith("box x −200…200 · y 80…400 · z −150…150 mm") for s in said)
            r.io.box = {"x": None, "y": (80.0, 400.0), "z": (-150.0, 150.0)}   # an open coordinate
            frame()
            assert any(s.startswith("box x open · y 80…400") for s in said)
            r.io.box = {"x": (-900.0, 900.0), "y": None, "z": None}  # wider than the view: clamped
            frame()
            run(r, 1)                                 # nobody there
            frame()
            assert hp._ins(r.io) == "L○ R○"
            r.io.box = None                           # no box: today's view
            run(r, 1, hand("left"), hand("right"))
            frame()
            assert hp._ins(r.io) == "L● R●" and "box open" in said
            del r.io.box, r.io.outside                # a HandsIO from before a hot reload
            frame()
        finally:
            imgui.text_disabled, imgui.collapsing_header = real, header
        assert hp._box_text(None) == "" and hp._box_text({}) == ""
        assert (hp.BOX_W, hp.BOX_H) == (190.0, 92.0)  # the frame keeps its size
    finally:
        imgui.destroy_context(ctx)


# ------------------------------------- plan 17 WP2: a learn listens to one source

def rolled(deg):
    """A palm normal rolled by `deg` about the fingers' axis."""
    a = math.radians(deg)
    return (math.sin(a), -math.cos(a), 0.0)


def _wrong_hand_cases():
    """Plan 17 §1 row 1's two measured cases, as frames of (left, right)
    hands (None: not in view). In both the left hand is the one meant and
    the right hand travels further."""
    # 1. the left hand rolls slowly on purpose while the right hand — the
    #    one that armed the learn with the mouse — travels in from the edge
    entering = [(hand("left", pos=(-120.0, 200.0, 0.0), normal=rolled(2.0 * k)),
                 None if k < 2 else hand("right", pos=(330.0 - 25.0 * k, 200.0, 0.0)))
                for k in range(40)]
    # 2. both hands in the box: the left rolls 29° — and then goes on, a
    #    roll needs 45° to win — while the right drops 150 mm
    dropping = [(hand("left", pos=(-120.0, 200.0, 0.0), normal=rolled(min(2.9 * k, 60.0))),
                 hand("right", pos=(120.0, 320.0 - min(15.0 * k, 150.0), 0.0)))
                for k in range(40)]
    return {"the right hand travels in": entering, "the right hand drops": dropping}


def _play(r, app, frames) -> int | None:
    """Feed the frames; the frame number at which the learn completed."""
    for k, (left, right) in enumerate(frames):
        run(r, 1, *[h for h in (left, right) if h is not None],
            learn=app.learn, router=app.router)
        if app.learn.learning is None:
            return k
    return None


def test_a_hand_learn_listens_to_one_hand(tmp_path):
    """The session's "the Leap assigned a learn to the wrong hand" (plan 17
    §1 row 1). A bare learn takes whichever axis of either hand travelled
    furthest: in both cases that is the right hand's. Armed with
    "hand:left" only the left hand's axes can win — the left roll is
    learned, however far the right hand goes — and armed "hand:right" the
    same movement lands the right hand's axis."""
    for n, (name, frames) in enumerate(_wrong_hand_cases().items()):
        won = {}
        for want in (None, "hand:left", "hand:right"):
            app, r = make_app(tmp_path / f"{n}{want}"), rig()
            run(r, 1, frames[0][0], learn=app.learn, router=app.router)
            app.learn.arm("view.inst_amp", want)
            at = _play(r, app, frames)
            assert at is not None, (name, want)
            (row,) = app.table.routes_to("view.inst_amp")
            won[want] = (row.source, at)
            assert app.learn.want is None and f"learned view.inst_amp ← {row.describe()}" \
                in app.learn.last
        assert won[None][0].startswith("hand:right."), (name, won)       # the wrong hand
        assert won["hand:left"][0] == "hand:left.roll", (name, won)
        assert won["hand:right"][0] == won[None][0], (name, won)
        assert won["hand:left"][1] > won[None][1]            # …which got there first


def test_the_hands_never_complete_a_desk_learn(app):
    """Armed "desk", a hand sweeps every axis through its whole range:
    still armed, no row, no question — and no baseline kept, so a later
    hand learn starts fresh."""
    r = rig()
    run(r, 1, hand(), learn=app.learn, router=app.router)
    app.learn.arm("view.inst_amp", "desk")
    for k in range(40):
        s = math.sin(k / 6.0)
        for side in ("left", "right"):
            run(r, 1, hand(side, pos=(200.0 * s, 250.0 + 150.0 * s, 150.0 * s),
                           normal=rolled(50.0 * s), direction=tilt(0.8 * s), grab=abs(s)),
                learn=app.learn, router=app.router)
    assert app.learn.learning == "view.inst_amp" and app.learn.want == "desk"
    assert app.learn.pending is None and not app.table.of("hand")
    assert r.io._learn_base is None


def test_a_rearm_starts_a_fresh_baseline(app):
    """The baseline is the learn's own (keyed by the param and the want):
    arm A, move 0.2, arm B, move 0.1 more — 0.3 since A was armed, 0.1
    since B — and nothing is learned; the same hand re-armed for the same
    param with another want starts fresh too."""
    r = rig()
    k = ax(r, "right.y")
    lo, hi = r.io.state[k].lo, r.io.state[k].hi
    y = lambda u: (0.0, lo + u * (hi - lo), 0.0)
    run(r, 1, hand(pos=y(0.3)), learn=app.learn, router=app.router)
    app.learn.arm("view.inst_amp", "hand:right")
    run(r, 2, hand(pos=y(0.3)), learn=app.learn, router=app.router)
    run(r, 1, hand(pos=y(0.5)), learn=app.learn, router=app.router)   # 0.2: not enough
    assert app.learn.learning == "view.inst_amp"
    app.learn.arm("view.speed", "hand:right")
    run(r, 1, hand(pos=y(0.6)), learn=app.learn, router=app.router)   # the new baseline
    run(r, 1, hand(pos=y(0.6)), learn=app.learn, router=app.router)   # 0.1 since B: no
    assert app.learn.learning == "view.speed" and not app.table.of("hand")
    app.learn.arm(None)                                      # cancelled and armed again, the
    app.learn.arm("view.speed", "hand:right")                # same, between two polls: fresh
    run(r, 1, hand(pos=y(0.7)), learn=app.learn, router=app.router)   # its baseline
    assert app.learn.learning == "view.speed" and not app.table.of("hand")
    run(r, 1, hand(pos=y(0.6)), learn=app.learn, router=app.router)
    app.learn.arm("view.speed")                              # the same param, another want
    run(r, 1, hand(pos=y(0.8)), learn=app.learn, router=app.router)   # its baseline
    assert app.learn.learning == "view.speed" and not app.table.of("hand")
    run(r, 1, hand(pos=y(0.5)), learn=app.learn, router=app.router)   # 0.3 from it: learned
    assert app.learn.learning is None
    assert [b.source for b in app.table.routes_to("view.speed")] == ["hand:right.y"]
