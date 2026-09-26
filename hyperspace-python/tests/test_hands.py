"""Ultraleap hands → MIDI: features, smoothing, quantizing, learn — fake hands, no SDK."""

import math
from types import SimpleNamespace as NS

import numpy as np
import pytest

from hyperspace import hands
from hyperspace.analysis import Analyser
from hyperspace.bands import Chain
from hyperspace.control import Control
from hyperspace.hands import HandsIO, OneEuro, features, make_axes, quantize
from hyperspace.library import Library
from hyperspace.midi import MidiIO, MidiMap
from hyperspace.params import build_registry
from hyperspace.render import ViewState
from hyperspace.routing import Binding, Bindings, Router


def v3(x, y, z):
    return NS(x=x, y=y, z=z)


def hand(side="right", pos=(0.0, 200.0, 0.0), normal=(0.0, -1.0, 0.0),
         direction=(0.0, 0.0, -1.0), grab=0.0, pinch=0.0, conf=1.0):
    return NS(type=NS(name=side.capitalize()), confidence=conf,
              grab_strength=grab, pinch_strength=pinch, grab_angle=grab * math.pi,
              pinch_distance=80.0,
              palm=NS(position=v3(*pos), normal=v3(*normal), direction=v3(*direction)))


class FakeSource:
    """latest() like LeapSource; `put` is one tracking frame."""

    def __init__(self):
        self.seq, self.t, self.hands = 0, 0.0, {}
        self.status, self.on = "tracking", True

    def put(self, *hs, dt=1 / 90):
        self.seq += 1
        self.t += dt
        self.hands = {}
        for h in hs:
            side = h.type.name.lower()
            self.hands[side] = (features(h), h.confidence)

    def latest(self):
        return self.seq, self.t, self.hands


class FakeOut:
    def __init__(self):
        self.sent = []

    def send(self, m):
        self.sent.append(m)


def io(**cfg):
    src = FakeSource()
    # no smoothing unless a test asks: values land exactly
    cfg = {"min_cutoff": 1e6, "beta": 0.0, **cfg}
    return HandsIO(cfg, source=src, out=FakeOut()), src


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
    d = (0.0, math.sin(0.5), -math.cos(0.5))
    assert features(hand(direction=d))["pitch"] == pytest.approx(math.degrees(0.5))


def test_grab_angle_in_degrees():
    assert features(hand(grab=0.5))["grab_angle"] == pytest.approx(90)


# ---------------------------------------------------------------- the axes

def test_cc_layout_left_then_right():
    axes = make_axes({"dofs": ["x", "y", "grab"], "cc": 102})
    assert [(a.name, a.cc) for a in axes] == [
        ("left.x", 102), ("left.y", 103), ("left.grab", 104),
        ("right.x", 105), ("right.y", 106), ("right.grab", 107)]


def test_bad_layouts_are_refused():
    with pytest.raises(ValueError, match="unknown"):
        make_axes({"dofs": ["x", "wiggle"]})
    with pytest.raises(ValueError, match="past 127"):
        make_axes({"cc": 120})


def test_calibration_overrides_defaults(tmp_path):
    axes = make_axes({}, {"right.y": {"lo": 50, "hi": 150, "invert": True}})
    a = axes[[x.name for x in axes].index("right.y")]
    assert (a.lo, a.hi, a.invert) == (50, 150, True)
    assert a.norm(50) == 1.0 and a.norm(150) == 0.0
    path = tmp_path / "hands.json"
    hands.save_calibration(path, axes)
    again = make_axes({}, hands.load_calibration(path))
    assert [(x.lo, x.hi, x.invert) for x in again] == [(x.lo, x.hi, x.invert) for x in axes]


# ---------------------------------------------------------------- quantize / filter

def test_quantize_spans_the_midi_scale():
    assert quantize(0.0, None, 0.35) == 0 and quantize(1.0, None, 0.35) == 127
    assert quantize(0.5, None, 0.35) == 64


def test_quantize_holds_at_a_step_boundary():
    last = 64
    edge = 64.5 / 127                          # exactly between 64 and 65
    for wobble in (-0.2, 0.2, -0.1, 0.3):      # noise straddling the boundary
        last = quantize(edge + wobble / 127, last, 0.35)
        assert last == 64
    assert quantize(65.0 / 127, last, 0.35) == 65   # a real move gets through


def test_one_euro_quiets_a_still_hand_and_follows_a_moving_one():
    rng = np.random.default_rng(0)
    f = OneEuro(1.0, 4.0)
    still = [f(0.5 + rng.normal(0, 0.01), k / 90) for k in range(180)]
    assert np.std(still[90:]) < 0.01 / 3       # jitter well under the raw noise
    f.reset()
    track = [f(k / 90, k / 90) for k in range(90)]  # a sweep of 1 u/s
    assert track[-1] == pytest.approx(89 / 90, abs=0.05)


# ---------------------------------------------------------------- the adapter

def test_hand_entering_sends_presence_then_its_ccs():
    h, src = io()
    src.put(hand("right", pos=(220.0, 350.0, 0.0)))   # right hand at x, y maxima
    msgs = h.poll()
    assert (msgs[0].type, msgs[0].note, msgs[0].channel) == ("note_on", 121, 15)
    ccs = {m.control: m.value for m in msgs if m.type == "control_change"}
    assert set(ccs) == set(range(108, 114))          # only the right hand's six
    assert ccs[108] == 127 and ccs[109] == 127       # x, y at the top of their ranges
    assert ccs[111] == 64                            # roll 0 sits mid-range
    assert h.out.sent == msgs


def test_only_changes_are_sent_and_a_repeated_frame_is_held():
    h, src = io()
    src.put(hand())
    h.poll()
    assert h.poll() == []                     # same frame again: nothing
    src.put(hand())
    assert h.poll() == []                     # new frame, same pose: nothing
    src.put(hand(pos=(0.0, 300.0, 0.0)))
    assert [(m.control, m.value) for m in h.poll()] == [(109, round(200 / 250 * 127))]


def test_leaving_holds_the_ccs_darkens_the_lanes_and_notes_off():
    h, src = io()
    src.put(hand("left"), hand("right"))
    h.poll()
    src.put(hand("right"))
    msgs = h.poll()
    assert [(m.type, m.note) for m in msgs] == [("note_off", 120)]
    lanes = h.lanes()
    assert all(math.isnan(u) for u in lanes[:6]) and not any(map(math.isnan, lanes[6:]))


def test_low_confidence_counts_as_absent():
    h, src = io(min_confidence=0.5)
    src.put(hand(conf=0.2))
    assert h.poll() == [] and not h.present["right"]


def test_solo_lets_one_axis_through():
    h, src = io()
    h.solo = h.axis("right.z")
    src.put(hand(pos=(10.0, 150.0, 40.0)))
    assert [m.control for m in h.poll()] == [110]


# ---------------------------------------------------------------- through the table

@pytest.fixture()
def rig(tmp_path):
    chain = Chain(Analyser())
    control = Control(chain)
    view = ViewState()
    lib = Library(tmp_path)
    reg = build_registry(view, control, NS(chain=chain), lib.bank)
    table = Bindings.load(tmp_path / "bindings.json", legacy_midi=None)
    midi = MidiIO(reg, MidiMap(table=table), inp=_Quiet(), out=FakeOut())
    return NS(reg=reg, view=view, midi=midi, router=Router(reg, table))


class _Quiet:
    def iter_pending(self):
        return iter(())


def test_learn_takes_the_axis_that_moved_and_skips_pickup(rig):
    h, src = io()
    src.put(hand())
    h.poll(rig.midi, rig.router)
    rig.midi.learn("view.inst_amp")
    # everything jitters a little, pitch moves a lot: pitch is learned
    for k in range(1, 8):
        d = (0.0, math.sin(0.12 * k), -math.cos(0.12 * k))
        src.put(hand(pos=(2.0 * k, 200.0, 0.0), direction=d))
        h.poll(rig.midi, rig.router)
    b = rig.midi.binding_for("view.inst_amp")
    assert b is not None and b.source == "cc:15:112" and b.op == "abs"
    assert b.pickup is False and b.feedback is None      # no APC ring, no pickup
    # and now the hand drives it straight away
    src.put(hand(direction=(0.0, math.sin(-1.0), -math.cos(-1.0))))   # pitch −57°
    h.poll(rig.midi, rig.router)
    p = rig.reg["view.inst_amp"]
    # cc 3 of 127 (pitch −57° on ±60°), to the param's own step
    assert p.norm == pytest.approx(round((-57.2958 + 60) / 120 * 127) / 127, abs=0.01)


def test_hand_lanes_modulate_and_let_go_when_the_hand_leaves(rig):
    h, src = io()
    p = rig.reg["view.inst_amp"]
    base = p.norm
    rig.router.table.add(Binding("hand:6", "view.inst_amp", "mod", 0.5))   # right.x
    src.put(hand(pos=(220.0, 200.0, 0.0)))                  # u = 1
    h.poll(rig.midi, rig.router)
    assert rig.router.labels["hand"][6] == "R x"
    rig.router.modulate()
    rig.reg.apply()
    assert p.eff_norm == pytest.approx(min(base + 0.5, 1.0), abs=1e-9)
    src.put()                                              # hand gone
    h.poll(rig.midi, rig.router)
    rig.router.modulate()
    rig.reg.apply()
    assert p.eff_norm == pytest.approx(base, abs=1e-9)
