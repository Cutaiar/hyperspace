"""The hid road (pads/hid.py) and a Sony pad through gamepad.Pad and the
pad device — fake hidapi devices, no controller and no threads."""

import json
import math
import struct
from types import SimpleNamespace as NS

import pytest
from test_pads_sony import CALIBRATION, FIRMWARE, bt_report, usb_report

import hyperspace.gamepad as gp
from hyperspace import devices
from hyperspace.pads import hid, models, sony

EDGE = {"path": b"edge-1", "vendor_id": 0x054C, "product_id": 0x0DF2, "serial_number": "e1",
        "usage_page": 1, "usage": 5, "bus_type": 1}
DUALSENSE_BT = {"path": b"ds-1", "vendor_id": 0x054C, "product_id": 0x0CE6,
                "usage_page": 1, "usage": 5, "bus_type": 2}


class FakeDev:
    """A hidapi device: reports to read, features to answer, writes kept."""

    def __init__(self, reports=(), features=None, refuse=()):
        self.reports = list(reports)
        self.features = features if features is not None else {0x05: CALIBRATION, 0x20: FIRMWARE}
        self.writes: list[bytes] = []
        self.refuse = set(refuse)        # USB output lengths that raise

    def read(self, n, timeout=0):
        return list(self.reports.pop(0)[:n]) if self.reports else []

    def get_feature_report(self, rid, n):
        return list(self.features.get(rid, b""))

    def write(self, data):
        if len(data) in self.refuse:
            raise OSError("refused")
        self.writes.append(bytes(data))
        return len(data)

    def close(self):
        pass


def stepped(info, dev) -> hid.HidPad:
    """A reader whose thread is not started: the test steps it."""
    r = hid.HidPad(info, start=False, opener=lambda i: dev)
    r._calibrate(dev)
    return r


def test_the_reader_calibrates_learns_its_link_and_decodes_once_a_frame():
    dev = FakeDev()
    r = stepped(EDGE, dev)
    assert not r.calibration.nominal and r.update_version == 0x0204 and r.rumble_v2   # an Edge
    assert r.transport == "" and r.latest() is None
    r._take(bytes(usb_report(p9=0x40)))
    assert r.transport == "usb"
    f = r.latest()
    assert f.buttons[models.LP] == 1 and r.latest() is f      # decoded once per new report
    bt = stepped(DUALSENSE_BT, FakeDev())
    bt._take(bt_report(bytes(usb_report())[1:]))
    assert bt.transport == "bluetooth" and bt.latest().kind == sony.BT_IN
    assert not bt.rumble_v2 and bt.tags == {1}               # a DualSense at update 0x0204


def test_a_report_is_kept_whatever_hidapi_said_of_the_bus():
    """hidapi's bus_type sets the link before any report: a USB report must
    still be kept (a probe run against a fake pad found them all dropped)."""
    for info, report in ((EDGE, bytes(usb_report(p9=0x40))),
                         (DUALSENSE_BT, bt_report(bytes(usb_report(p9=0x40))[1:]))):
        r = stepped(info, FakeDev())
        r.transport = "bluetooth" if hid._bt_hint(info) else "usb"   # as `_run` sets it
        r._take(report)
        assert r.reports == 1 and r.latest().buttons[models.LP] == 1


def test_outputs_go_out_on_change_after_the_take_over():
    dev = FakeDev()
    r = stepped(EDGE, dev)
    r._take(bytes(usb_report()))
    r._write(dev)
    assert dev.writes == []                                  # nothing asked yet
    e = sony.Effects(light=(255, 0, 0))
    r.send(e)
    r._write(dev)
    first, report = dev.writes
    assert first[1 + sony.C_FLAGS2] == sony.F2_LIGHT_SETUP and first[1 + sony.C_LIGHT_SETUP] == 2
    assert len(report) == 64 and tuple(report[1 + sony.C_RGB:1 + sony.C_RGB + 3]) == (255, 0, 0)
    r.send(sony.Effects(light=(255, 0, 0)))
    r._sent_t = 0.0
    r._write(dev)
    assert len(dev.writes) == 2                              # the same effects: no write


def test_usb_output_length_is_learned_and_bluetooth_is_framed():
    dev = FakeDev(refuse={64})
    r = stepped(EDGE, dev)
    r._take(bytes(usb_report()))
    r.send(sony.Effects())
    r._write(dev)
    assert r.usb_len == 63 and {len(w) for w in dev.writes} == {63}
    bdev = FakeDev()
    b = stepped(DUALSENSE_BT, bdev)
    b._take(bt_report(bytes(usb_report())[1:]))
    b.send(sony.Effects(rumble_low=1.0))
    b._write(bdev)
    take, out = bdev.writes
    assert len(out) == 78 and sony.bt_crc_ok(out, sony.BT_OUTPUT_SEED)
    assert out[1] >> 4 == (take[1] >> 4) + 1                  # the sequence counts up
    assert out[3 + sony.C_FLAGS0] & sony.F0_RUMBLE_V1        # a DualSense below 0x0215: v1


def test_the_hub_lends_pads_by_controller_in_list_order():
    found = [EDGE, DUALSENSE_BT]
    hub = hid.HidHub(start=False, enumerate_=lambda v, p: found, opener=lambda i: FakeDev(),
                     start_readers=False)
    hub.scan()
    assert len(hub.readers) == 2
    for r in hub.readers.values():
        r.transport = "usb"
    a, b, c = object(), object(), object()
    assert hub.take(a, "dualsense").model.id == "dualsense"
    assert hub.take(b, "any").model.id == "edge"
    assert hub.take(c, "edge") is None                       # the Edge is b's
    assert hub.take(b, "any").model.id == "edge"             # kept while held
    hub.release(b)
    assert hub.take(c, "054c:0df2").model.id == "edge"
    assert hub.holds(0x054C, 0x0DF2)
    found.remove(EDGE)                                       # unplugged
    hub.scan()
    assert hub.take(c, "edge") is None and not hub.holds(0x054C, 0x0DF2)
    # only the gamepad interface, one record per path
    assert [d["path"] for d in hid.sony_devices(
        lambda v, p: [EDGE, EDGE, {**EDGE, "path": b"kb", "usage": 6},
                      {**EDGE, "path": b"x", "product_id": 0x1234}])] == [b"edge-1"]


def test_a_tape_records_and_reads_back(tmp_path):
    path = tmp_path / "edge.jsonl"
    rec = hid.Recorder(path, "edge", "usb")
    rec.write(bytes(usb_report()), t=0.0)
    rec.note("press the right back button")
    rec.write(bytes(usb_report(p9=0x80)), t=0.5)
    rec.close()
    lines = [json.loads(x) for x in path.read_text().splitlines()]
    assert lines[0] == {"tape": hid.TAPE_SCHEMA, "model": "edge", "transport": "usb"}
    clock = [100.0]
    tape = hid.TapePad(path, clock=lambda: clock[0])
    assert tape.model.id == "edge" and tape.length == 0.5
    assert not tape.latest().buttons[models.RP]
    clock[0] += 0.6
    assert tape.latest().buttons[models.RP]
    clock[0] += 0.5                                          # looped
    assert not tape.latest().buttons[models.RP]
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"tape": "something/else"}) + "\n")
    with pytest.raises(ValueError):
        hid.TapePad(bad)


# ---- through the Pad and the device ----

class FakeReader:
    """What `Pad` reads from the hub: a model, a link, the latest frame."""

    road = "hid"

    def __init__(self, model="edge", transport="usb"):
        self.model = models.MODELS[model]
        self.transport = transport
        self.calibration = sony.calibration(CALIBRATION)
        self.report = bytes(usb_report())
        self.sent: list = []

    def latest(self):
        return sony.decode(self.report, bluetooth=self.transport == "bluetooth")

    def send(self, effects):
        self.sent.append(effects)


def sony_pad(monkeypatch, reader, controller="any"):
    """A Pad on the hid road: no GLFW joystick, `reader` lent."""
    monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: False)
    pad = gp.Pad(hid=True, controller=controller)
    pad._hid_reader = lambda: reader
    return pad


def test_a_sony_pad_reads_as_the_pads_vocabulary_with_touch_and_motion(monkeypatch):
    r = FakeReader()
    pad = sony_pad(monkeypatch, r)
    pad.poll(1 / 60)
    assert pad.on and pad.source == "hid" and pad.model.id == "edge" and pad.link == "usb"
    assert pad.lanes()[:6] == [pytest.approx(0.5, abs=0.01)] * 4 + [0.0, 0.0]
    assert set(pad.buttons_named) >= {"A", "TOUCH", "LP", "RP", "LFN", "RFN"}
    r.report = bytes(usb_report(p7=0x28, p9=0x40))         # the cross, the left back button
    pad.poll(1 / 60)
    assert pad.pressed(gp.A) and pad.pressed(gp.LP)
    touch = dict(zip(gp.gesture.TOUCH_LANES, pad.touch_lanes(), strict=True))
    assert touch["down"] == 0.0
    rep = usb_report()
    x, y = 960, 540
    memoryview(rep)[33:37] = bytes([3, x & 0xFF, (x >> 8) | ((y & 0x0F) << 4), y >> 4])
    struct.pack_into("<3h", rep, 22, -4096, 7094, 0)        # right side down 30° (½ g on −x)
    r.report = bytes(rep)
    for _ in range(90):
        pad.poll(1 / 60)
    touch = dict(zip(gp.gesture.TOUCH_LANES, pad.touch_lanes(), strict=True))
    assert touch["x"] == pytest.approx(0.5, abs=0.01) and touch["down"] == 1.0
    motion = dict(zip(gp.gesture.MOTION_LANES, pad.motion_lanes(), strict=True))
    assert motion["roll"] > 0.7                              # tipped right
    pad.send_effects(sony.Effects(light=(1, 2, 3)))
    assert r.sent[-1].light == (1, 2, 3)


def test_an_xbox_pad_has_no_extras_and_a_simple_report_none(monkeypatch):
    fake = NS(present=True, buttons=[0] * 20, hats=[0], axes=[0.0] * 4 + [-1.0, -1.0])
    monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: j == 0)
    monkeypatch.setattr(gp.glfw, "get_joystick_buttons", lambda j: (fake.buttons, 20))
    monkeypatch.setattr(gp.glfw, "get_joystick_hats", lambda j: (fake.hats, 1))
    monkeypatch.setattr(gp.glfw, "get_joystick_axes", lambda j: (fake.axes, 6))
    pad = gp.Pad()
    pad.poll()
    assert pad.source == "glfw" and pad.touch_lanes() is None and pad.motion_lanes() is None
    assert set(pad.buttons_named) == set(gp.BUTTONS)
    simple = FakeReader("dualsense", "bluetooth")
    simple.report = bytes([0x01, 0x80, 0x80, 0x80, 0x80, 0x08, 0, 0, 0, 0])
    p2 = sony_pad(monkeypatch, simple)
    p2.poll(1 / 60)
    assert p2.on and p2.touch_lanes() is None and p2.motion_lanes() is None


def test_glfw_reads_a_sony_pad_through_its_own_map_and_respects_the_controller(monkeypatch):
    guids = {0: "030000004c050000f20d000000010000", 1: "030000005e040000130b000009050000"}
    raw = [0] * 19
    raw[1] = 1                                               # cross, in GLFW's Sony order
    raw[13] = 1                                              # the touchpad click
    monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: j in guids)
    monkeypatch.setattr(gp.glfw, "get_joystick_guid", lambda j: guids[j])
    monkeypatch.setattr(gp.glfw, "get_joystick_buttons", lambda j: (raw, len(raw)))
    monkeypatch.setattr(gp.glfw, "get_joystick_hats", lambda j: ([0], 1))
    axes = [0.0, 0.0, 0.0, -1.0, 1.0, 0.5]                   # LX LY RX L2 R2 RY
    monkeypatch.setattr(gp.glfw, "get_joystick_axes", lambda j: (axes, 6))
    monkeypatch.setattr(gp.Pad, "_hub", lambda self, make=True: None)   # no hidapi
    sony_only = gp.Pad(hid=True, controller="sony")
    sony_only.poll()
    assert sony_only.jid == 0 and sony_only.model.id == "edge"
    assert sony_only.down(gp.A) and sony_only.down(gp.TOUCH)
    assert sony_only.axes == [0.0, 0.0, 0.0, 0.5, -1.0, 1.0]  # RY, then L2 rests, R2 full
    xbox_only = gp.Pad(hid=True, controller="xbox")
    xbox_only.poll()
    assert xbox_only.jid == 1


def test_the_pad_device_feeds_touch_and_motion_lists_ports_and_sends_identity(monkeypatch):
    r = FakeReader()
    dev = devices.PadDevice("edge", {"controller": "edge", "light": "#ff0080", "player": 2})
    assert {p.address for p in dev.sources} >= {"pad:LP", "touch:pinch", "motion:shake"}
    assert [p.address for p in dev.sinks][:2] == ["edge:0", "edge:1"]     # before it is on
    dev.io = sony_pad(monkeypatch, r)
    dev.io.poll(1 / 60)
    router = NS(names={}, labels={}, rests={}, lane_kinds={}, gates={}, fed={})
    router.feed = lambda sc, v: router.fed.__setitem__(sc, v)
    dev._feed_extras(router, dev.io, "")
    assert router.names["touch"]["pinch"] == 6 and router.lane_kinds["motion"][6] == "trigger"
    assert router.gates["touch"] == [(2, "touch down"), (5, "second touch down")]
    assert len(router.fed["touch"]) == 9 and len(router.fed["motion"]) == 8
    dev.ctx.table = NS(sinks=lambda role: [])
    dev.send(NS(), None)
    e = r.sent[-1]
    assert e.light == (255, 0, 128) and e.players == sony.player_bits(2)
    assert e.rumble_low == 0 and e.right.mode == "off"
    xbox = devices.PadDevice("pad", {"controller": "xbox"})
    assert xbox.schemes == ("axis", "pair", "pad", "hat") and xbox.sinks == ()


def test_sink_rows_become_effects():
    ident = ((0, 0, 255), 1)
    e = devices.pad_effects({}, ident)
    assert e.light == (0, 0, 255) and e.players == 0x04
    ch = devices.SINK_CHANNEL
    e = devices.pad_effects({ch["light.hue"]: 0.0, ch["light.level"]: 0.5, ch["rumble.low"]: 1.0,
                             ch["trigger.right"]: 1.0, ch["players"]: 0.6, ch["mic"]: 1.0}, ident)
    assert e.light == (128, 0, 0)                            # red at half level
    assert e.rumble_low == 1.0 and e.right.mode == "resist" and e.right.strength == 1.0
    assert e.players == 0b111 and e.mic == 1
    assert devices.pad_effects({ch["light.white"]: 1.0}, ident).light == (255, 255, 255)
    assert devices.pad_effects({ch["rumble.high"]: float("nan")}, ident).rumble_high == 0.0


class Armed:
    """A Learn armed for "pad", keeping what it lands."""

    learning = "view.bright"

    def __init__(self):
        self.got: list = []

    def target_for(self, pid):
        return NS(modulatable=True)

    def accepts(self, source):
        return source.partition(":")[0].partition("@")[0] in ("pad", "hat", "axis", "touch",
                                                              "motion")

    def learn_pad_button(self, source):
        self.got.append(("button", source))

    def learn_source(self, source, centred=False):
        self.got.append((source, centred))


def test_learn_pad_lands_the_edges_buttons_a_drag_a_pinch_and_a_tilt(monkeypatch):
    r = FakeReader()
    pad = sony_pad(monkeypatch, r)
    pad.poll(1 / 60)
    r.report = bytes(usb_report(p9=0x80))                   # the right back button
    pad.poll(1 / 60)
    learn = Armed()
    assert gp.learn_from(pad, learn, role="edge")
    assert learn.got == [("button", "pad@edge:RP")]
    # a finger dragged across lands touch:x
    learn = Armed()
    for k in range(12):
        rep = usb_report()
        x = 400 + 100 * k
        memoryview(rep)[33:37] = bytes([4, x & 0xFF, (x >> 8) | (0 << 4), 540 >> 4])
        r.report = bytes(rep)
        pad.poll(1 / 60)
        gp.learn_from(pad, learn)
        if learn.got:
            break
    assert learn.got == [("touch:x", False)]
    # tipped right lands motion:roll, centred
    learn = Armed()
    rep = usb_report()
    struct.pack_into("<3h", rep, 22, -6000, 5000, 0)
    r.report = bytes(rep)
    for _ in range(90):
        pad.poll(1 / 60)
    gp.learn_from(pad, learn)
    assert learn.got == [("motion:roll", True)]


def test_a_pad_entry_with_a_tape_plays_it(tmp_path, monkeypatch):
    monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: True)    # a tape wins over GLFW
    path = tmp_path / "t.jsonl"
    rec = hid.Recorder(path, "edge", "usb")
    rec.write(bytes(usb_report(p9=0x80)), t=0.0)
    rec.close()
    pad = gp.Pad(tape=str(path))
    pad.poll(1 / 60)
    assert pad.source == "tape" and pad.jid is None and pad.model.id == "edge"
    assert pad.down(gp.RP) and pad.touch_lanes() is not None
    pad.close()
    missing = gp.Pad(tape=str(tmp_path / "nope.jsonl"))
    missing.poll()
    assert not missing.on and "tape" in missing.tape_note


# ---- the review's findings (2026-11-01), each as the test that would have caught it ----

EDGE_GUID = "030000004c050000f20d000000010000"
XBOX_GUID = "030000005e040000130b000009050000"


def glfw_sees(monkeypatch, guids: dict[int, str]):
    """GLFW's raw API over joysticks with these GUIDs, all at rest."""
    monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: j in guids)
    monkeypatch.setattr(gp.glfw, "get_joystick_guid", lambda j: guids[j])
    monkeypatch.setattr(gp.glfw, "get_joystick_buttons", lambda j: ([0] * 19, 19))
    monkeypatch.setattr(gp.glfw, "get_joystick_hats", lambda j: ([0], 1))
    monkeypatch.setattr(gp.glfw, "get_joystick_axes", lambda j: ([0.0] * 4 + [-1.0, -1.0], 6))


def claims_with_edge(found=(EDGE,)):
    """The registry's shared claims, its hub over a fake hidapi seeing `found`."""
    claims = gp.Claims()
    claims.hub = hid.HidHub(start=False, enumerate_=lambda v, p: list(found),
                            opener=lambda i: FakeDev(), start_readers=False)
    claims.hub.scan()
    for r in claims.hub.readers.values():
        r._take(bytes(usb_report(p7=0x28)))          # reporting: the cross held
    return claims


def test_hid_reads_the_edge_even_when_glfw_sees_it_too(monkeypatch):
    """macOS shows the Edge to GLFW over USB and Bluetooth: the hid road
    must win, and no other entry may read the same pad through GLFW."""
    glfw_sees(monkeypatch, {0: EDGE_GUID})
    claims = claims_with_edge()
    one, two = gp.Pad(hid=True), gp.Pad(hid=True)
    one.attach(claims, "pad")
    two.attach(claims, "p2")
    for p in (one, two):
        p.poll(1 / 60)
    assert one.source == "hid" and one.jid is None and one.touch_lanes() is not None
    assert not two.on and two.jid is None, (two.source, two.jid, two._may_read(0))   # the same Edge, not twice


def test_a_pad_on_a_joystick_keeps_it_when_an_edge_arrives(monkeypatch):
    glfw_sees(monkeypatch, {0: XBOX_GUID})
    claims = claims_with_edge(found=())
    one, two = gp.Pad(hid=True), gp.Pad(hid=True)
    one.attach(claims, "pad")
    two.attach(claims, "p2")
    for p in (one, two):
        p.poll(1 / 60)
    assert one.source == "glfw" and not two.on
    claims.hub.enumerate_ = lambda v, p: [EDGE]           # the Edge plugged in mid-show
    claims.hub.scan()
    for r in claims.hub.readers.values():
        r._take(bytes(usb_report()))
    for p in (one, two):
        p.poll(1 / 60)
    assert one.source == "glfw" and one.jid == 0          # nobody moved
    assert two.source == "hid" and two.model.id == "edge"


def test_an_xbox_only_entry_opens_no_sony_pad(monkeypatch):
    monkeypatch.setattr(hid, "available", lambda: True)
    pad = gp.Pad(hid=True, controller="xbox")
    assert pad._hub() is None and pad.__dict__.get("_own_hub") is None


def test_the_suite_never_reaches_a_real_controller():
    """conftest's `_no_real_hid`: a registry's pad entry polls with no hub."""
    reg = devices.DeviceRegistry([{"role": "pad", "kind": "gamepad", "enabled": True,
                                   "usb": False, "hid": True, "controller": "any"}])
    reg.open_all()
    pad = reg.adapter("gamepad")
    pad.poll(1 / 60)
    assert pad.claims.hub is None and pad.claims.no_hid
    reg.close()


def test_a_refused_report_keeps_the_last_frame_so_nothing_fires_again():
    r = stepped(DUALSENSE_BT, FakeDev())
    held = bt_report(bytes(usb_report(p7=0x28))[1:])
    r._take(held)
    f = r.latest()
    assert f.buttons[gp.A]
    r._take(bt_report(bytes(usb_report())[1:], tag=0x02))       # a microphone report
    assert r.latest() is f
    bad = bytearray(held)
    bad[-1] ^= 0xFF
    r._take(bytes(bad))                                          # a bad CRC
    assert r.latest() is f


def test_learn_counts_a_tilt_from_where_the_pad_was_held(monkeypatch):
    r = FakeReader()
    rep = usb_report()
    t = math.radians(25)
    struct.pack_into("<3h", rep, 22, 0, int(8192 * math.cos(t)), -int(8192 * math.sin(t)))
    r.report = bytes(rep)
    pad = sony_pad(monkeypatch, r)
    for _ in range(90):
        pad.poll(1 / 60)                                  # held at 25°, far edge up
    learn = Armed()
    learn.armed_n = 1
    for _ in range(5):
        gp.learn_from(pad, learn)
    assert learn.got == []                                # a held pad lands nothing
    t = math.radians(55)
    struct.pack_into("<3h", rep, 22, 0, int(8192 * math.cos(t)), -int(8192 * math.sin(t)))
    r.report = bytes(rep)
    for _ in range(90):
        pad.poll(1 / 60)
    gp.learn_from(pad, learn)
    assert learn.got == [("motion:pitch", True)]          # 30° further does


def test_hid_off_still_reads_a_sony_pad_through_its_own_map(monkeypatch):
    glfw_sees(monkeypatch, {0: EDGE_GUID})
    raw = [0] * 19
    raw[1] = 1                                            # cross, in GLFW's Sony order
    monkeypatch.setattr(gp.glfw, "get_joystick_buttons", lambda j: (raw, 19))
    monkeypatch.setattr(gp.glfw, "get_joystick_axes",
                        lambda j: ([0.0, 0.0, 0.0, -1.0, -1.0, 0.0], 6))
    pad = gp.Pad(hid=False)
    pad.poll()
    assert pad.model.id == "edge" and pad.down(gp.A) and not pad.down(gp.B)
    assert pad.lanes()[3] == pytest.approx(0.5)           # RY rests: no camera drift


def test_a_bad_tape_is_said_once_and_a_cut_line_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: False)
    path = tmp_path / "cut.jsonl"
    rec = hid.Recorder(path, "edge", "usb")
    rec.write(bytes(usb_report(p9=0x80)), t=0.0)
    rec.close()
    with path.open("a") as f:
        f.write('{"t": 1.0, "r": "0180')                 # cut mid-line
    pad = gp.Pad(tape=str(path))
    pad.poll(1 / 60)
    assert pad.on and pad.down(gp.RP)
    made = []
    real = hid.TapePad
    monkeypatch.setattr(hid, "TapePad", lambda *a, **k: made.append(1) or real(*a, **k))
    gone = gp.Pad(tape=str(tmp_path / "missing.jsonl"))
    for _ in range(5):
        gone.poll(1 / 60)
    assert len(made) == 1 and not gone.on and "tape" in gone.tape_note


def test_the_libusb_road_honours_controller():
    claims = gp.Claims()
    edge, x360 = gp.Pad(usb=True, controller="edge"), gp.Pad(usb=True, controller="x360")
    edge.attach(claims, "pad")
    x360.attach(claims, "p2")
    assert claims.lend() is x360


def test_outputs_go_quiet_when_the_reader_stops():
    import time as _time

    class Slow(FakeDev):
        def read(self, n, timeout=0):
            _time.sleep(0.002)
            return list(usb_report()) if timeout else []
    dev = Slow()
    r = hid.HidPad(EDGE, opener=lambda i: dev)
    r.send(sony.Effects(light=(9, 9, 9), rumble_low=1.0, right=sony.Trigger("resist", 0.1, 1.0)))
    deadline = _time.monotonic() + 2
    while len(dev.writes) < 2 and _time.monotonic() < deadline:
        _time.sleep(0.01)
    r.close()
    r._thread.join(1)
    last = dev.writes[-1][1:]
    assert last[sony.C_RUMBLE_LOW] == 0 and last[sony.C_TRIGGER_RIGHT] == sony.T_OFF
    assert tuple(last[sony.C_RGB:sony.C_RGB + 3]) == (9, 9, 9)


def test_the_old_gamepad_table_checks_plan_42s_keys(tmp_path):
    from hyperspace import config
    p = tmp_path / "config.toml"
    p.write_text('[gamepad]\nhid = "false"\ncontroller = "wiimote"\nplayer = 9\n')
    cfg = config.load(p)
    (pad,) = [e for e in config.devices(cfg) if e["kind"] == "gamepad"]
    assert pad["hid"] is True and pad["controller"] == "any" and "player" not in pad
    notes = " ".join(cfg.get("notes", []))
    assert "hid = 'false'" in notes and "wiimote" in notes and "player = 9" in notes


def test_a_refused_open_says_why_on_the_system_line(monkeypatch):
    monkeypatch.setattr(gp.glfw, "joystick_present", lambda j: False)

    class Refusing(FakeDev):
        pass

    def refuse(info):
        raise OSError("open failed")
    claims = gp.Claims()
    claims.hub = hid.HidHub(start=False, enumerate_=lambda v, p: [EDGE], opener=refuse,
                            start_readers=False)
    claims.hub.scan()
    r = next(iter(claims.hub.readers.values()))
    r._run()                                              # the open fails, the reader dies
    claims.hub.scan()
    dev = devices.PadDevice("pad", {"controller": "edge"})
    dev.io = gp.Pad(hid=True, controller="edge")
    dev.io.attach(claims, "pad")
    dev.io.poll(1 / 60)
    assert "open failed" in dev.last
