"""Ultraleap hands: features, the analog chain, MIDI out, learn, setups — fake hands, no SDK."""

import itertools
import json
import math
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
from hyperspace.midi import MidiIO, MidiMap
from hyperspace.params import Registry, build_registry
from hyperspace.render import ViewState
from hyperspace.routing import Binding, Bindings, Router

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
    assert len(ps) == 8 + 12 * 13 and not any(p.modulatable for p in ps)
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
    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    lib = Library(tmp_path)
    reg = build_registry(view, control, NS(chain=chain), lib.project)
    table = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)

    class Quiet:
        def iter_pending(self):
            return iter(())

    learn = Learn(reg, table)
    midi = MidiIO(reg, MidiMap(table=table), inp=Quiet(), out=FakeOut(), learner=learn)
    return NS(reg=reg, view=view, learn=learn, midi=midi, router=Router(reg, table), table=table)


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
        (f"hand:{ax(r, 'right.pitch')}", "position", 1.0, None)]
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
    # and it is in the file
    on_disk = Bindings.load(app.table.path, legacy_midi=None)
    assert on_disk.owner("view.inst_amp").source == rows[0].source


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
    assert Bindings.load(t.path, legacy_midi=None).owner("view.inst_amp").source == "hand:7"
    assert m.resolve_pending(True) is None                           # nothing pending


def test_a_hand_learn_needs_no_midi_adapter(tmp_path):
    """Audit B3: Learn is the host's, not the MIDI adapter's. With no
    MidiIO anywhere — `[midi] enabled = false`, or the adapter failed to
    open — right-click → Learn, move a hand, and the row lands."""
    chain = Chain(Analyser())
    reg = build_registry(ViewState(), Control(chain), NS(chain=chain), Library(tmp_path).bank)
    table = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)
    learn, router = Learn(reg, table), Router(reg, table)
    r = rig()
    run(r, 1, hand(), learn=learn, router=router)
    learn.arm("view.inst_amp")
    for k in range(1, 8):
        run(r, 1, hand(pos=(2.0 * k, 200.0, 0.0), direction=tilt(0.12 * k)),
            learn=learn, router=router)
    b = table.owner("view.inst_amp")
    assert (b.source, b.op) == (f"hand:{ax(r, 'right.pitch')}", "position")
    assert learn.learning is None and "learned view.inst_amp" in learn.last
    assert Bindings.load(table.path, legacy_midi=None).owner("view.inst_amp") == b
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
        panel = Panel(control, audio, view, themes=lib.project, registry=reg, library=lib)
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
            panel._hands_sel = k
            r.s.axes[k].out = hs.OUTS[k % len(hs.OUTS)]
            r.s.axes[k].rest = hs.RESTS[k % 2]
            frame()
        r.s.axes[0].out, r.s.axes[0].number = "cc14", 99   # a conflict draws its warning
        panel._hands_sel = 0
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
    assert rows[0].when == f"hand:{r.io.gate_lane('right', 'index')}"


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
    assert rows[0].when == f"hand:{r.io.gate_lane('right', 'index')}"


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
