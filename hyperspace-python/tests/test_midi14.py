"""14-bit CC rows, the listening learn, and Learn ▸ Player n (2026-11-07, the DDJ-FLX4).

A DJ controller's faders and knobs send MIDI 1.0's 14-bit pair (CC n, then CC
n + 32) and its jogs are relative encoders; the generic profile knows nothing of
the device, so Learn hears the control for a moment and writes the row the way
it spoke (`midi.heard_as`). The param menu's Learn is nested by player, each
listing the controllers that player holds (`Panel.player_learns`), which only that
controller completes (`learn.only_want`)."""

from types import SimpleNamespace as NS

import mido
import pytest
from test_midi import FakeIn, FakeOut, cc, rig  # noqa: F401 — the rig fixture

from hyperspace import learn, midi, ui
from hyperspace.midi import Binding, MidiIO, heard_as
from hyperspace.players import Players
from hyperspace.routing import ABS14

# ---------------------------------------------------------------- heard_as


@pytest.mark.parametrize("msgs, want", [
    ([(0, 19, 64), (0, 51, 3)], (0, 19, ABS14)),                      # MSB, then its LSB
    ([(0, 51, 3), (0, 19, 64), (0, 51, 9)], (0, 19, ABS14)),          # an LSB first
    ([(1, 33, 65), (1, 33, 65), (1, 33, 66)], (1, 33, "rel64")),      # a jog: +1 again
    ([(1, 33, 63), (1, 33, 63)], (1, 33, "rel64")),
    ([(0, 16, 1), (0, 16, 1), (0, 16, 2)], (0, 16, "rel")),           # two's complement
    ([(0, 16, 127), (0, 16, 127)], (0, 16, "rel")),
    ([(0, 7, 60), (0, 7, 61), (0, 7, 62)], (0, 7, "abs")),            # a knob never repeats
    ([(0, 7, 90)], (0, 7, "abs")),                                    # one message: abs
    ([(0, 7, 100), (0, 7, 100)], (0, 7, "abs")),                      # repeated, far from 0/64
    ([(0, 19, 64), (1, 51, 3)], (0, 19, "abs")),                      # an LSB on another channel
    ([(0, 40, 64), (0, 72, 3)], (0, 40, "abs")),                      # CC 40 has no LSB
])
def test_heard_as(msgs, want):
    assert heard_as(msgs) == want


def test_abs14_is_a_known_op_and_reads_as_14_bit():
    b = Binding("cc:0:19", "view.depth4", ABS14)
    assert ABS14 in midi.ABS_OPS and b.describe() == "MIDI CC 19 ch1 14-bit"
    assert Binding.from_json(b.to_json()).op == ABS14


# ---------------------------------------------------------------- abs14 on the wire


def _abs14_rig(rig):  # noqa: F811
    """An abs14 row on CC 19 / 51 with no pickup, on a continuous param."""
    t = rig.midi.table
    pid = "view.inst_amp"
    t.add(Binding("cc:0:19", pid, ABS14, pickup=False))
    t.slew = 0.0
    return rig.reg[pid]


def push(r, *msgs):
    r.inp.queue.extend(msgs)
    r.midi.poll()


def test_an_msb_and_its_lsb_land_as_one_14_bit_value(rig):  # noqa: F811
    p = _abs14_rig(rig)
    push(rig, cc(19, 64), cc(51, 5))
    assert p.norm == pytest.approx(((64 << 7) | 5) / 16383, abs=1e-6)
    push(rig, cc(51, 100))                       # an LSB alone: with the MSB it has
    assert p.norm == pytest.approx(((64 << 7) | 100) / 16383, abs=1e-6)
    push(rig, cc(19, 10))                        # an MSB alone: at the poll's end
    assert p.norm == pytest.approx(((10 << 7) | 100) / 16383, abs=1e-6)


def test_the_msb_waits_for_its_lsb_so_no_value_in_between_is_written(rig):  # noqa: F811
    """From 0x06/0x7F up to 0x07/0x00: applied at the MSB with the old LSB it
    would visit 0x07/0x7F — 127 steps too far — for an instant."""
    p = _abs14_rig(rig)
    push(rig, cc(19, 6), cc(51, 127))
    seen = []
    real = p.set
    p.set = lambda v: (real(v), seen.append(p.norm))[0]
    push(rig, cc(19, 7), cc(51, 0))
    assert seen == [pytest.approx((7 << 7) / 16383, abs=1e-6)]


def test_the_lsb_of_a_14_bit_row_reaches_no_other_row(rig):  # noqa: F811
    p = _abs14_rig(rig)
    other = rig.reg["view.depth4"]
    rig.midi.table.add(Binding("cc:0:51", other.id, "abs", pickup=False))
    before = other.norm
    push(rig, cc(19, 64), cc(51, 127))
    assert other.norm == pytest.approx(before)
    assert p.norm == pytest.approx(((64 << 7) | 127) / 16383, abs=1e-6)


def test_a_14_bit_row_rests_between_detents_and_a_7_bit_row_does_not(rig):  # noqa: F811
    """16383 steps would round to the param's 100 detents (RAW_STEPS): an
    abs14 row rests at its value itself, glide or no glide; `abs` still
    lands on a detent, as ever."""
    p = _abs14_rig(rig)
    v = (64 << 7) | 5
    rig.midi.table.slew = 0.05                    # with smoothing: the glide lands there too
    now = [0.0]
    rig.midi.clock = lambda: now[0]
    push(rig, cc(19, 64), cc(51, 5))
    now[0] = 1.0
    rig.midi.poll()
    assert p.norm == pytest.approx(v / 16383, abs=1e-6)
    assert round(p.norm * 100) / 100 != pytest.approx(p.norm, abs=1e-6)   # not on a detent
    q = rig.reg["view.depth4"]
    rig.midi.table.add(Binding("cc:0:2", q.id, "abs", pickup=False))
    push(rig, cc(2, 77))
    now[0] = 2.0
    rig.midi.poll()
    assert q.norm == pytest.approx(round(77 / 127 * q.steps) / q.steps, abs=1e-6)


# ---------------------------------------------------------------- the listening learn


@pytest.fixture()
def flx(rig, tmp_path):  # noqa: F811
    """A generic desk (the FLX4 as the generic profile sees it) on the rig's
    registry and table, as a second role, with a clock the test moves."""
    rig.midi.table.midi_roles = ("apc40", "flx4")      # the APC40 is the first desk
    inp, out = FakeIn(), FakeOut()
    now = [0.0]
    io = MidiIO(rig.reg, rig.midi.table, port="DDJ-FLX4", profile="generic", inp=inp,
                out=out, learner=rig.midi.learner, role="flx4")
    io.clock = lambda: now[0]
    rig.midi.table.slew = 0.0

    def send(*msgs, at=None):
        if at is not None:
            now[0] = at
        inp.queue.extend(msgs)
        io.poll()
    return NS(io=io, send=send, out=out, lrn=rig.midi.learner, table=rig.midi.table,
              reg=rig.reg)


def _learned(f, pid):
    return [b for b in f.table.bindings if b.target == pid and b.device == "flx4"]


def test_a_fader_pair_learns_as_abs14_after_the_window(flx):
    f = flx
    f.lrn.arm("view.inst_amp", "desk")
    f.send(cc(19, 64), cc(51, 3), at=0.0)
    assert f.lrn.learning == "view.inst_amp" and not _learned(f, "view.inst_amp")   # still listening
    f.send(cc(19, 64), cc(51, 9), at=0.05)
    f.send(at=midi.LISTEN_S + 0.01)
    (b,) = _learned(f, "view.inst_amp")
    assert (b.source, b.op) == ("cc@flx4:0:19", ABS14)
    assert f.lrn.learning is None and "14-bit" in f.lrn.last
    assert f.out.sent == []                       # a generic desk is sent nothing


def test_a_jog_learns_as_rel64_and_steps(flx):
    f = flx
    f.lrn.arm("view.inst_amp", "desk")
    f.send(cc(33, 65, channel=1), cc(33, 65, channel=1), cc(33, 66, channel=1), at=0.0)
    f.send(at=midi.LISTEN_S + 0.01)
    (b,) = _learned(f, "view.inst_amp")
    assert (b.source, b.op) == ("cc@flx4:1:33", "rel64")
    p = f.reg["view.inst_amp"]
    before = p.value
    f.send(cc(33, 66, channel=1))
    assert p.value != before


def test_a_plain_knob_still_learns_abs(flx):
    f = flx
    f.lrn.arm("view.inst_amp", "desk")
    f.send(cc(7, 60), cc(7, 61), at=0.0)
    f.send(at=midi.LISTEN_S + 0.01)
    (b,) = _learned(f, "view.inst_amp")
    assert (b.source, b.op) == ("cc@flx4:0:7", "abs")


def test_a_learn_disarmed_while_listening_writes_nothing(flx):
    f = flx
    f.lrn.arm("view.inst_amp", "desk")
    f.send(cc(19, 64), cc(51, 3), at=0.0)
    f.lrn.arm(None)
    f.send(at=1.0)
    assert not _learned(f, "view.inst_amp")


def test_a_note_on_a_generic_desk_still_learns_at_once(flx):
    f = flx
    f.lrn.arm("view.points", "desk")
    f.send(mido.Message("note_on", channel=0, note=11, velocity=127), at=0.0)
    assert f.lrn.learning is None and _learned(f, "view.points")


def test_the_apc40_still_learns_a_cc_at_once(rig):  # noqa: F811
    lrn = rig.midi.learner
    lrn.arm("view.inst_amp", "desk")
    push(rig, cc(48, 70))
    assert lrn.learning is None


# ---------------------------------------------------------------- one controller's learn


class Dev(NS):
    pass


class Regs:
    def __init__(self, *devs):
        self.devs = list(devs)

    def get(self, role):
        return next((d for d in self.devs if d.role == role), None)

    def wants(self):
        return ()

    def __iter__(self):
        return iter(self.devs)


APC = Dev(role="apc40", kind="midi", entry={"profile": "apc40"}, status="connected",
          schemes=("cc", "note", "pitch"), feeds=())
FLX = Dev(role="ddj-flx4", kind="midi", entry={"profile": "generic", "port": "DDJ-FLX4"},
          status="connected", schemes=("cc@ddj-flx4", "note@ddj-flx4", "pitch@ddj-flx4"),
          feeds=())
PAD = Dev(role="xbox", kind="gamepad", entry={"controller": "xbox"}, status="lost",
          schemes=("pad", "hat", "axis"), feeds=("axis",), model=None)


def test_a_learn_for_one_controller_takes_only_its_own_sources(rig):  # noqa: F811
    lrn = learn.Learn(rig.reg, rig.midi.table, devices=Regs(APC, FLX, PAD))
    lrn.arm("view.inst_amp", learn.only_want("ddj-flx4"))
    assert lrn.accepts("cc@ddj-flx4:0:19") and lrn.accepts("note@ddj-flx4:0:11")
    assert not lrn.accepts("cc:0:19")            # the APC40's
    assert not lrn.accepts("pad:A")
    assert lrn.is_desk_want()
    lrn.arm("view.inst_amp", learn.only_want("apc40"))
    assert lrn.accepts("cc:0:48") and not lrn.accepts("cc@ddj-flx4:0:19")
    lrn.arm("view.inst_amp", learn.only_want("xbox"))
    assert lrn.accepts("pad:A") and lrn.accepts("axis:LX") and not lrn.accepts("cc:0:1")
    assert not lrn.is_desk_want()
    with pytest.raises(ValueError):
        lrn.arm("view.inst_amp", learn.only_want("nobody"))
    assert learn.only_want("ddj-flx4") not in lrn.wants()    # offered by player, not listed


def _panel(players):
    return NS(devices=Regs(APC, FLX, PAD), meta=NS(players=players),
              _desk_target=lambda a: True, _hand_sides=list)


def test_the_learn_menu_lists_each_players_controllers(rig):  # noqa: F811
    """Learn ▸ Learn Player n ▸ what that player holds: the FLX4 by its port's
    name under the player it was given to, a pad not connected drawn and not
    armable, a player who holds nothing with no items."""
    ps = Players()
    ps.tell(("apc40", "ddj-flx4", "xbox"), primaries=("apc40", "xbox"))
    ps.hold("ddj-flx4", 2)
    panel = _panel(ps)
    p = rig.reg["view.inst_amp"]
    items = {n: ui.Panel.player_learns(panel, p, p, n) for n in (1, 2, 3, 4)}
    assert len(items[1]) == 2 and items[1][0] == ("APC40", "@apc40")
    assert items[1][1][1] is None and items[1][1][0].endswith("not connected")
    assert items[2] == [("DDJ-FLX4", "@ddj-flx4")]      # its role is its name: said once
    assert items[3] == [] and items[4] == []


def test_the_hint_names_the_controller(rig):  # noqa: F811
    lrn = learn.Learn(rig.reg, rig.midi.table, devices=Regs(APC, FLX, PAD))
    lrn.arm("view.inst_amp", learn.only_want("ddj-flx4"))
    panel = NS(learn=lrn, midi=None, hands=None)
    hint = ui.Panel._learn_hint(panel)
    assert "DDJ-FLX4" in hint and "fader" in hint and "diagram" not in hint
