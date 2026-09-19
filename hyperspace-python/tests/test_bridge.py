"""Plan-07 WP4c: the DAW bridge — lanes out, external lanes in, no ports.

The wire first (14-bit encode/decode round trip in both encodings, the
lane value mapping), then the outbound gate (rate limit, change gating,
room), the inbound decoder (pairs in either order, MSB alone, pitch
bend), a loopback through two bridges, and `ext:` routes modulating a
param end to end. Fake ports as in test_midi.
"""

import sys
from types import SimpleNamespace

import mido
import numpy as np
import pytest

from hyperspace import config
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer, legacy_layout
from hyperspace.bands import CEIL, default_params
from hyperspace.bridge import FULL, Bridge, Decoder, capacity, encode, quantize
from hyperspace.control import Control
from hyperspace.midi import Ports
from hyperspace.params import build_registry
from hyperspace.render import ViewState
from hyperspace.routing import Binding, Bindings, Router


class FakeIn:
    def __init__(self):
        self.queue = []

    def iter_pending(self):
        q, self.queue = self.queue, []
        return iter(q)


class FakeOut:
    def __init__(self):
        self.sent = []

    def send(self, msg):
        self.sent.append(msg)


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def rig():
    chain = Analyzer(Analyser(48_000.0), default_params(), layout=legacy_layout())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain, on=True)
    view = ViewState()
    reg = build_registry(view, control, audio, None)
    return SimpleNamespace(reg=reg, view=view, control=control, chain=chain)


def bridge(reg, clock=None, **cfg):
    """A bridge on fake ports; `cfg` overrides the [bridge] defaults."""
    inp, out = FakeIn(), FakeOut()
    b = Bridge(reg, cfg, inp=inp, out=out, clock=clock or Clock())
    return b, inp, out


def pw(channel, v):
    return mido.Message("pitchwheel", channel=channel, pitch=v - 8192)


def cc(control, value, channel=0):
    return mido.Message("control_change", channel=channel, control=control, value=value)


# ---------------------------------------------------------------- the wire

@pytest.mark.parametrize("encoding", ["pitch", "cc14"])
@pytest.mark.parametrize("v", [0, 1, 127, 128, 8191, 8192, 16382, 16383])
def test_fourteen_bit_round_trip(encoding, v):
    d = Decoder(16, 0, 16)
    for msg in encode(v, 3, encoding, 0, 16):
        d.feed(msg)
    assert d.values[3] * FULL == pytest.approx(v)
    assert d.live


def test_cc14_pair_is_msb_then_lsb_on_the_pair_channel():
    msb, lsb = encode(0x1F55, 2, "cc14", 4, 16)
    assert (msb.control, msb.value, msb.channel) == (18, 0x1F55 >> 7, 4)
    assert (lsb.control, lsb.value, lsb.channel) == (18 + 32, 0x1F55 & 0x7F, 4)


def test_pitch_lane_is_its_own_channel():
    (m,) = encode(16383, 5, "pitch", 3, 16)
    assert (m.type, m.channel, m.pitch) == ("pitchwheel", 8, 8191)
    (m,) = encode(0, 0, "pitch", 0, 16)
    assert m.pitch == -8192


def test_quantize_clamps_and_rounds():
    assert quantize(0.0) == 0 and quantize(1.0) == FULL
    assert quantize(1.7) == FULL and quantize(-0.2) == 0
    assert quantize(0.5) == 8192      # round(8191.5): banker's, to even


def test_capacity():
    assert capacity("pitch", 0, 16) == 16 and capacity("pitch", 14, 0) == 2
    assert capacity("cc14", 0, 16) == 16 and capacity("cc14", 0, 0) == 32


# ---------------------------------------------------------------- lanes out

def test_lane_value_mapping_is_routing_dot_py_s():
    """u = lane / CEIL, as Router.modulate reads a lane; the asymptote is full."""
    r = rig()
    b, _, out = bridge(r.reg)
    r.chain.out[:] = 0.0
    r.chain.out[0], r.chain.out[1] = CEIL, 1.0
    b.step(r.chain)
    by_ch = {m.channel: m.pitch + 8192 for m in out.sent}
    assert by_ch[0] == FULL
    assert by_ch[1] == round(FULL / CEIL)
    assert by_ch[2] == 0 and len(by_ch) == r.chain.n


def test_idle_lanes_go_silent_and_a_change_goes_out():
    r = rig()
    b, _, out = bridge(r.reg)
    r.chain.out[:] = 1.0
    b.step(r.chain)
    n = len(out.sent)
    assert n == r.chain.n
    for _ in range(50):
        b.step(r.chain)
    assert len(out.sent) == n                 # nothing moved, nothing sent
    r.chain.out[2] = 2.0
    b.clock.t += 1.0
    b.step(r.chain)
    assert len(out.sent) == n + 1 and out.sent[-1].channel == 2


def test_rate_limit_holds_the_latest_value():
    r = rig()
    clk = Clock()
    b, _, out = bridge(r.reg, clk, rate=100, send=["lane:0"])
    for k in range(200):                      # a lane sweeping at 1 kHz
        r.chain.out[0] = k / 200 * CEIL
        b.step(r.chain)
        clk.t += 0.001
    # 200 ms at 100 Hz: 20 windows (+ the first frame)
    assert 20 <= len(out.sent) <= 21
    # the last message carries the value at its send time, never an older one
    sent_at = [m.pitch + 8192 for m in out.sent]
    assert sent_at == sorted(sent_at)
    # a change that lands inside a window goes out when the window ends
    r.chain.out[0] = 0.0
    b.step(r.chain)                           # blocked: too soon
    clk.t += 0.02
    b.step(r.chain)
    assert out.sent[-1].pitch + 8192 == 0


def test_rate_zero_sends_every_frame_it_changes():
    r = rig()
    b, _, out = bridge(r.reg, rate=0, send=["lane:0"])
    for k in range(10):
        r.chain.out[0] = k * 0.1
        b.step(r.chain)
    assert len(out.sent) == 10


def test_param_lanes_carry_the_effective_norm():
    r = rig()
    b, _, out = bridge(r.reg, send=["lane:0", "param:view.bright", "param:view.rotate"])
    r.chain.out[:] = 0.0
    p = r.reg["view.bright"]
    p.set_norm(0.25)
    b.step(r.chain)
    by_ch = {m.channel: m.pitch + 8192 for m in out.sent}
    assert by_ch[1] == quantize(p.eff_norm) == round(0.25 * FULL)
    assert by_ch[2] == FULL                   # a toggle's norm: 1 while on
    p.modulate(0.5)                           # a lane rides on the base
    r.reg.apply()
    b.clock.t += 1.0
    b.step(r.chain)
    assert out.sent[-1].channel == 1 and out.sent[-1].pitch + 8192 == quantize(0.75)


def test_cc14_encoding_out():
    r = rig()
    b, _, out = bridge(r.reg, encoding="cc14", channel=2, cc=20, send=["lane:1"])
    r.chain.out[1] = CEIL / 2
    b.step(r.chain)
    v = quantize(0.5)
    assert [(m.channel, m.control, m.value) for m in out.sent] == [
        (2, 20, v >> 7), (2, 52, v & 0x7F)]


def test_slots_past_the_room_are_dropped():
    r = rig()
    b, _, out = bridge(r.reg, channel=14)     # pitch: two channels left
    r.chain.out[:] = 1.0
    b.step(r.chain)
    assert sorted(m.channel for m in out.sent) == [14, 15]
    b2, _, out2 = bridge(r.reg, encoding="cc14", cc=30, send=["lane:*", "param:view.bright"])
    b2.step(r.chain)
    assert sorted(m.control for m in out2.sent) == [30, 31, 62, 63]


def test_no_analyzer_sends_zeros_once():
    r = rig()
    b, _, out = bridge(r.reg)
    r.chain.out[:] = 1.0
    b.step(r.chain)
    out.sent.clear()
    b.clock.t += 1.0
    b.step(None)
    assert len(out.sent) == r.chain.n and all(m.pitch == -8192 for m in out.sent)
    b.clock.t += 1.0
    b.step(None)
    assert len(out.sent) == r.chain.n


def test_bands_added_at_runtime_get_lanes():
    r = rig()
    b, _, out = bridge(r.reg)
    r.chain.out[:] = 1.0
    b.step(r.chain)
    n = r.chain.n
    r.chain.add_band()
    r.chain.out[:] = 1.0
    b.clock.t += 1.0
    b.step(r.chain)
    assert max(m.channel for m in out.sent) == n


def test_bad_config_is_refused():
    r = rig()
    with pytest.raises(ValueError):
        Bridge(r.reg, {"encoding": "osc"}, inp=FakeIn(), out=FakeOut())
    with pytest.raises(ValueError):
        Bridge(r.reg, {"cc": 40}, inp=FakeIn(), out=FakeOut())


# ---------------------------------------------------------------- lanes in

def test_pairs_land_in_either_order_and_msb_alone():
    d = Decoder(16, 0, 16)
    v = 0x2A5F
    d.feed(cc(16 + 32, v & 0x7F))             # LSB first
    d.feed(cc(16, v >> 7))
    assert d.values[0] * FULL == pytest.approx(v)
    d.feed(cc(17, 100))                       # a 7-bit sender: MSB only
    assert d.values[1] * FULL == pytest.approx(100 << 7)
    assert d.feed(cc(16, 1, channel=3)) is None            # wrong channel
    assert d.feed(cc(5, 1)) is None                        # outside the block
    assert d.feed(mido.Message("note_on", note=1)) is None


def test_both_forms_land_on_the_same_lane():
    d = Decoder(16, 2, 8)
    assert d.feed(pw(2 + 4, 1000)) == 4
    assert d.feed(cc(8 + 4, 3, channel=2)) == 4
    assert d.feed(cc(8 + 4 + 32, 3, channel=2)) == 4
    assert d.feed(pw(1, 5)) is None           # below the first channel
    assert d.values[4] * FULL == pytest.approx((3 << 7) | 3)


def test_ext_route_modulates_a_param_end_to_end():
    r = rig()
    router = Router(r.reg, Bindings([Binding("ext:0", "view.bright", "mod", 0.2)]))
    p = r.reg["view.bright"]
    p.set_norm(0.5)
    base = p.norm
    b, inp, _ = bridge(r.reg)
    b.step(None, router)                      # nothing in: not a source yet
    router.modulate(None)
    r.reg.apply()
    assert not p.modulated
    inp.queue.append(pw(0, FULL))
    b.step(None, router)
    router.modulate(None)
    r.reg.apply()
    assert p.eff_norm == pytest.approx(base + 0.2, abs=1e-9)
    b.step(None, router)                      # held between messages
    router.modulate(None)
    r.reg.apply()
    assert p.eff_norm == pytest.approx(base + 0.2, abs=1e-9)
    inp.queue.append(pw(0, quantize(0.5)))
    b.step(None, router)
    router.modulate(None)
    r.reg.apply()
    assert p.eff_norm == pytest.approx(base + 0.1, abs=1e-4)


def test_lost_input_lets_the_rows_go():
    r = rig()
    router = Router(r.reg, Bindings([Binding("ext:0", "view.bright", "mod", 0.2)]))
    b, inp, _ = bridge(r.reg)
    inp.queue.append(pw(0, FULL))
    b.step(None, router)
    assert router.feeds["ext"] is not None
    b.ports.inp = None                        # the port vanished
    b.step(None, router)
    assert router.feeds["ext"] is None


def test_loopback_reconstructs_a_ramp_to_fourteen_bits():
    """Bridge A's lanes → bridge B's ext vector, both encodings."""
    for encoding in ("pitch", "cc14"):
        ra, rb = rig(), rig()
        a, _, a_out = bridge(ra.reg, rate=0, encoding=encoding)
        bb, b_in, _ = bridge(rb.reg, encoding=encoding)
        router = Router(rb.reg, Bindings())
        for k in range(100):
            ra.chain.out[:] = np.linspace(0, CEIL, ra.chain.n) * k / 99
            a.step(ra.chain)
            b_in.queue.extend(a_out.sent)
            a_out.sent.clear()
            bb.step(None, router)
            want = ra.chain.out / CEIL
            assert np.allclose(router.feeds["ext"][: ra.chain.n], want, atol=0.5 / FULL)


# ---------------------------------------------------------------- ports

def test_reconnect_resends_every_lane(monkeypatch):
    r = rig()
    clk = Clock()
    b, _, out = bridge(r.reg, clk)
    r.chain.out[:] = 1.0
    b.step(r.chain)
    n = len(out.sent)
    b.ports.injected = False                  # pretend these were real ports
    b.ports.inp = b.ports.out = None          # …and they went away
    clk.t += 10.0
    monkeypatch.setattr(mido, "get_input_names", list)
    monkeypatch.setattr(mido, "get_output_names", lambda: ["IAC Driver Bus 1"])
    monkeypatch.setattr(mido, "open_output", lambda name: out)
    b.step(r.chain)
    assert b.on and b.name == "IAC Driver Bus 1"
    assert len(out.sent) == 2 * n


def test_ports_open_each_side_by_its_own_name(monkeypatch):
    fin, fout = FakeIn(), FakeOut()
    monkeypatch.setattr(mido, "get_input_names", lambda: ["IAC Driver Bus 2", "APC40"])
    monkeypatch.setattr(mido, "get_output_names", lambda: ["IAC Driver Bus 1", "APC40"])
    monkeypatch.setattr(mido, "open_input", lambda name: fin)
    monkeypatch.setattr(mido, "open_output", lambda name: fout)
    p = Ports("Bus 2", "Bus 1", clock=Clock())
    assert p.connect() and p.inp is fin and p.out is fout and p.name == "IAC Driver Bus 2"
    p = Ports(None, "Bus 1", clock=Clock())
    assert p.connect() and p.inp is None and p.out is fout
    p = Ports("nothing", "nowhere", clock=Clock())
    assert not p.connect() and not p.on


def test_a_dead_port_drops_both_and_retries_later(monkeypatch):
    class Dead:
        def send(self, msg):
            raise OSError("gone")

    clk = Clock()
    p = Ports("x", "x", clock=clk)
    p.inp, p.out = FakeIn(), Dead()
    p.send(cc(1, 1))
    assert not p.on and p.error.startswith("send:")
    monkeypatch.setattr(mido, "get_input_names", list)
    monkeypatch.setattr(mido, "get_output_names", list)
    assert not p.retry()                      # too soon
    clk.t += 5.0
    assert not p.retry() and not p.on         # due, but nothing there


# ---------------------------------------------------------------- the rule

def test_core_does_not_import_the_bridge():
    """BLUEPRINT §3.6: the bridge depends on the core, never the reverse."""
    import importlib

    sys.modules.pop("hyperspace.bridge", None)
    for m in ("hyperspace.params", "hyperspace.control", "hyperspace.analyzer",
              "hyperspace.routing", "hyperspace.render", "hyperspace.config"):
        importlib.import_module(m)
    assert "hyperspace.bridge" not in sys.modules


def test_bridge_is_off_by_default(tmp_path):
    cfg = config.load(tmp_path / "config.toml")
    assert cfg["bridge"]["enabled"] is False
    (tmp_path / "config.toml").write_text('[bridge]\nenabled = true\nin = "Bus 2"\n')
    cfg = config.load(tmp_path / "config.toml")
    assert cfg["bridge"]["enabled"] is True and cfg["bridge"]["in"] == "Bus 2"
    assert cfg["bridge"]["out"] == "IAC"      # defaults fill the rest
