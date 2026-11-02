"""The Joy-Con codec (pads/nintendo.py) and a Joy-Con through the hid road,
gamepad.Pad and the pad device (plan 43) — fake hidapi devices, no
controller and no threads. The bytes follow dekuNukem's notes; the first
real ones are in test_pads_joycon_real.py."""

import math
import struct
from types import SimpleNamespace as NS

import hyperspace.gamepad as gp
from hyperspace import devices
from hyperspace.pads import gesture, hid, models, nintendo, sony

JOYCON_L = {"path": b"jc-l", "vendor_id": 0x057E, "product_id": 0x2006, "serial_number": "aa",
            "usage_page": 1, "usage": 5, "bus_type": 2}
JOYCON_R = {**JOYCON_L, "path": b"jc-r", "product_id": 0x2007}
PROCON = {**JOYCON_L, "path": b"pro", "product_id": 0x2009}
NAMES = {i: n for n, i in models.CANON.items()}


def pack3(a: int, b: int) -> bytes:
    """Two 12-bit values in three bytes, as the sticks and the flash pack them."""
    return bytes((a & 0xFF, ((a >> 8) & 0x0F) | ((b & 0x0F) << 4), (b >> 4) & 0xFF))


def full_report(b3=0, b4=0, b5=0, lstick=(2048, 2048), rstick=(2048, 2048), battery=0x80,
                accel=(0, 0, 4096), gyro=(0, 0, 0), timer=7) -> bytes:
    r = bytearray(49)
    r[0], r[1], r[2] = nintendo.REPORT_FULL, timer, battery
    r[3], r[4], r[5] = b3, b4, b5
    r[6:9] = pack3(*lstick)
    r[9:12] = pack3(*rstick)
    for k in range(3):
        struct.pack_into("<6h", r, 13 + 12 * k, *accel, *gyro)
    return bytes(r)


def spi_reply(addr: int, data: bytes) -> bytes:
    r = bytearray(49)
    r[0], r[13], r[14] = nintendo.REPORT_REPLY, nintendo.SPI_ACK, nintendo.SUB_SPI_READ
    struct.pack_into("<IB", r, 15, addr, len(data))
    r[20:20 + len(data)] = data
    return bytes(r)


# a left stick's factory record: above (1500, 1400), centre (2000, 2100), below (1300, 1600)
L_FACTORY = pack3(1500, 1400) + pack3(2000, 2100) + pack3(1300, 1600)
# an IMU record: accel origin (10, -20, 30) sens 16384; gyro origin (5, -5, 0) sens 13371
IMU = struct.pack("<12h", 10, -20, 30, 16384, 16384, 16384, 5, -5, 0, 13371, 13371, 13371)


class FakeJoyCon:
    """A Joy-Con over hidapi: silent until the mode is set, answers SPI
    reads from `flash`, then streams `reports`."""

    def __init__(self, flash=None, reports=(), answer=True):
        self.flash = flash if flash is not None else {
            nintendo.SPI_STICK_L_FACTORY: L_FACTORY, nintendo.SPI_IMU_FACTORY: IMU}
        self.queue: list[bytes] = []
        self.reports = list(reports)
        self.writes: list[bytes] = []
        self.mode = None
        self.answer = answer

    def read(self, n, timeout=0):
        if self.queue:
            return list(self.queue.pop(0)[:n])
        if self.mode == nintendo.FULL_MODE and self.reports:
            return list(self.reports.pop(0)[:n])
        return []

    def write(self, data):
        d = bytes(data)
        self.writes.append(d)
        if d[0] != nintendo.OUT_ID:
            return len(d)
        cmd, args = d[10], d[11:]
        if cmd == nintendo.SUB_MODE:
            self.mode = args[0]
        elif cmd == nintendo.SUB_SPI_READ and self.answer:
            addr, n = struct.unpack_from("<IB", args, 0)
            data = self.flash.get(addr, b"\xff" * n)
            self.queue.append(spi_reply(addr, bytes(data[:n]).ljust(n, b"\xff")))
        return len(d)

    def get_feature_report(self, rid, n):
        return []

    def close(self):
        pass


def stepped(info, dev) -> hid.HidPad:
    r = hid.HidPad(info, start=False, opener=lambda i: dev)
    r._calibrate(dev)
    return r


# ---- decoding ----

def test_the_l_joycons_buttons_land_by_position():
    held = {}
    for byte, bit, name in nintendo._L_BUTTONS:
        f = nintendo.decode(full_report(**{f"b{byte}": bit}), "l")
        held[name] = [NAMES[i] for i, v in enumerate(f.buttons) if v]
    assert held["A"] == ["A"] and held["Y"] == ["Y"]            # ↓ and ↑
    assert held["LP"] == ["LP"] and held["RP"] == ["RP"]        # SL and SR, the back pair
    assert held["VIEW"] == ["VIEW"] and held["SHARE"] == ["SHARE"] and held["LSTICK"] == ["LSTICK"]
    zl = nintendo.decode(full_report(b5=0x80), "l")
    assert zl.axes[gp.AX_LT] == 1.0 and zl.axes[gp.AX_RT] == -1.0 and not any(zl.buttons)
    assert nintendo.decode(full_report(), "l").hat == 0        # no D-pad on a Joy-Con


def test_the_r_joycons_stick_is_the_left_stick_and_the_pro_has_the_whole_face():
    f = nintendo.decode(full_report(rstick=(2048 + 700, 2048 + 700)), "r")
    assert f.axes[gp.AX_LX] > 0.4 and f.axes[gp.AX_LY] < -0.4   # right and up (GLFW's up is −)
    assert f.axes[gp.AX_RX] == 0.0
    zr = nintendo.decode(full_report(b3=0x80), "r")
    assert zr.axes[gp.AX_RT] == 1.0
    home = nintendo.decode(full_report(b4=0x10), "r")
    assert [NAMES[i] for i, v in enumerate(home.buttons) if v] == ["GUIDE"]
    pro = nintendo.decode(full_report(b5=0x02 | 0x04, rstick=(2048 + 700, 2048)), "pro")
    assert pro.hat == 1 | 2 and pro.axes[gp.AX_RX] > 0.4


def test_the_newest_of_the_three_sensor_samples_is_read_and_the_battery_scales():
    r = bytearray(full_report(accel=(1, 2, 3), gyro=(4, 5, 6)))
    struct.pack_into("<6h", r, 13 + 24, 7, 8, 9, 10, 11, 12)    # the last sample differs
    f = nintendo.decode(bytes(r), "l")
    assert f.accel == (7, 8, 9) and f.gyro == (10, 11, 12) and f.full and f.kind == sony.BT_IN
    assert len(nintendo.imu_samples(bytes(r))) == 3
    # byte 2's high nibble: 8 full … 2 critical, its low bit charging (0x4e
    # read "low" on a real Joy-Con (L), 2026-11-02)
    assert nintendo.decode(full_report(battery=0x90), "l").charging == 1
    assert nintendo.decode(full_report(battery=0x81), "l").charging == 0
    assert nintendo.decode(full_report(battery=0x80), "l").battery == 10
    assert nintendo.decode(full_report(battery=0x4E), "l").battery == 5
    assert nintendo.decode(spi_reply(0x6020, b"\x00"), "l") is None    # a reply is no frame
    simple = nintendo.decode(bytes([0x3F, 0x02, 0x00, 0x08]), "l")
    assert simple is not None and not simple.full and simple.buttons[models.CANON["A"]] == 1


# ---- calibration ----

def test_the_flash_calibrates_the_stick_and_the_sensors():
    cal = nintendo.calibration({nintendo.SPI_STICK_L_FACTORY: L_FACTORY,
                                nintendo.SPI_IMU_FACTORY: IMU}, "l")
    assert not cal.nominal and not cal.user_stick
    assert cal.left == nintendo.StickCal(2000, 2100, 1500, 1300, 1400, 1600)
    assert cal.left.norm(2000, 2100) == (0.0, 0.0)
    assert cal.left.norm(3500, 2100 - 800) == (1.0, -0.5)        # full right, half down
    assert cal.left.norm(0, 9999) == (-1.0, 1.0)
    g = cal.accel_g((10 + 4096, -20, 30 + 4096))
    assert abs(g[0] - 1.0) < 0.01 and abs(g[1]) < 1e-9 and abs(g[2] - 1.0) < 0.01
    dps = cal.gyro_dps((5 + 100, -5, 0))
    assert abs(dps[0] - 100 * 936 / (13371 - 5)) < 1e-6 and dps[1] == 0.0


def test_the_users_record_wins_and_a_bad_one_falls_back():
    user = nintendo.USER_MAGIC + pack3(1000, 1000) + pack3(1800, 1900) + pack3(1000, 1000)
    cal = nintendo.calibration({nintendo.SPI_STICK_L_FACTORY: L_FACTORY,
                                nintendo.SPI_STICK_L_USER: user}, "l")
    assert cal.user_stick and cal.left.cx == 1800
    blank = nintendo.calibration({nintendo.SPI_STICK_L_FACTORY: L_FACTORY,
                                  nintendo.SPI_STICK_L_USER: b"\xff" * 11}, "l")
    assert not blank.user_stick and blank.left.cx == 2000
    assert nintendo.calibration({}, "l").nominal
    off = struct.pack("<12h", 0, 0, 0, 100, 100, 100, 0, 0, 0, 13371, 13371, 13371)
    assert nintendo.imu_cal(off) is None                           # a scale 160× off: not believed
    assert nintendo.stick_cal(b"\xff" * 9, "l") is None
    # the right stick's record is laid out centre, below, above
    r = nintendo.stick_cal(pack3(2000, 2100) + pack3(1300, 1600) + pack3(1500, 1400), "r")
    assert r == nintendo.StickCal(2000, 2100, 1500, 1300, 1400, 1600)


def test_a_resting_stick_becomes_its_own_centre_but_not_a_held_one():
    cal = nintendo.calibration({nintendo.SPI_STICK_L_FACTORY: L_FACTORY}, "l")
    drifted = [(2000 + 120, 2100 - 80)] * 30                       # drift: 0.08 right, 0.05 down
    c = nintendo.recentre(cal, "l", drifted)
    assert c.left.cx == 2120 and c.left.cy == 2020 and c.left.x_above == 1500
    assert c.left.norm(2120, 2020) == (0.0, 0.0)
    held = [(2000 + 1000, 2100)] * 30                              # a thumb on it
    assert nintendo.recentre(cal, "l", held) is cal
    wobbling = [(2000 + (k % 2) * 300, 2100) for k in range(30)]
    assert nintendo.recentre(cal, "l", wobbling) is cal
    assert nintendo.recentre(cal, "l", []) is cal
    rc = nintendo.calibration({nintendo.SPI_STICK_R_FACTORY:
                               pack3(2000, 2100) + pack3(1300, 1600) + pack3(1500, 1400)}, "r")
    assert nintendo.recentre(rc, "r", [(2050, 2050)] * 30).right.cx == 2050


# ---- output ----

def test_rumble_and_the_player_lights_encode_as_the_notes_say():
    assert nintendo.rumble_bytes(0.0, 0.0) == nintendo.RUMBLE_NEUTRAL
    full = nintendo.rumble_bytes(1.0, 1.0)
    assert full[1] == 0xC8 + 0x01 and full[2:] == bytes((0x40, 0x72))     # the notes' maxima
    half = nintendo.rumble_bytes(0.5, 0.0)
    assert 0x01 < half[1] < 0xC9 and half[2:] == bytes((0x40, 0x40))
    assert nintendo._amp_code(0.0) == 0 and nintendo._amp_code(0.05) > 0
    assert nintendo._amp_code(0.23) <= nintendo._amp_code(0.231)       # monotone across the seams
    assert nintendo._amp_code(0.12) <= nintendo._amp_code(0.121)
    assert nintendo.player_leds(sony.player_bits(1)) == 0b0001
    assert nintendo.player_leds(sony.player_bits(3)) == 0b0111
    assert nintendo.player_leds(0x1F) == 0b1111 and nintendo.player_leds(0) == 0
    seqs = iter(range(3, 20))
    (out,) = nintendo.output_reports(sony.Effects(players=sony.player_bits(2), rumble_low=0.8),
                                     lambda: next(seqs))
    assert out[0] == 0x01 and out[1] == 3 and out[10] == nintendo.SUB_LEDS and out[11] == 0b0011
    assert out[2:6] == out[6:10] == nintendo.rumble_bytes(0.0, 0.8)
    assert nintendo.rumbling(sony.Effects(rumble_low=0.8)) and not nintendo.rumbling(sony.Effects())
    assert nintendo.subcommand(16, 0x40, b"\x01")[1] == 0            # the counter wraps at 16


# ---- the road ----

def test_the_reader_sets_the_pad_up_reads_the_flash_and_recentres():
    rest = [full_report(lstick=(2000 + 100, 2100 - 50))] * 40
    dev = FakeJoyCon(reports=rest)
    r = stepped(JOYCON_L, dev)
    cmds = [w[10] for w in dev.writes if w[0] == nintendo.OUT_ID]
    assert cmds[:3] == [nintendo.SUB_MODE, nintendo.SUB_IMU, nintendo.SUB_VIBRATION]
    assert dev.mode == nintendo.FULL_MODE and cmds.count(nintendo.SUB_SPI_READ) >= 4
    assert set(r.flash) >= {nintendo.SPI_STICK_L_FACTORY, nintendo.SPI_IMU_FACTORY}
    assert not r.calibration.nominal and r.recentred and r.calibration.left.cx == 2100
    assert r.transport == "bluetooth" and r.reports >= 30 and r.axis_map is nintendo.AXIS_MAP
    r._take(full_report(lstick=(2100, 2050)))
    f = r.latest()
    assert f is not None and f.axes[:2] == [0.0, 0.0]                  # the drift reads 0
    assert r.note == ""


def test_a_silent_flash_leaves_the_nominal_calibration_and_the_pad_still_reads():
    dev = FakeJoyCon(answer=False, reports=[full_report()] * 5)
    r = stepped(JOYCON_L, dev)
    assert r.calibration.nominal and "flash" in r.note
    r._take(full_report(lstick=(2048 + 700, 2048)))
    assert r.latest().axes[gp.AX_LX] == 0.5


def test_outputs_go_out_on_change_and_rumble_is_refreshed_while_on():
    dev = FakeJoyCon(reports=[full_report()] * 40)
    r = stepped(JOYCON_L, dev)
    dev.writes.clear()
    r._take(full_report())
    r._write(dev)
    assert dev.writes == []
    r.send(sony.Effects(players=sony.player_bits(1)))
    r._write(dev)
    assert len(dev.writes) == 1 and dev.writes[0][10] == nintendo.SUB_LEDS
    r._sent_t = 0.0
    r.send(sony.Effects(players=sony.player_bits(1)))
    r._write(dev)
    assert len(dev.writes) == 1                                       # the same, no rumble: no write
    r.send(sony.Effects(players=sony.player_bits(1), rumble_high=0.5))
    r._sent_t = 0.0
    r._write(dev)
    r._sent_t -= nintendo.RUMBLE_REFRESH_S
    r._write(dev)
    assert len(dev.writes) == 3 and dev.writes[-1][2:6] == nintendo.rumble_bytes(0.5, 0.0)
    r._neutral(dev)
    assert dev.writes[-1][2:6] == nintendo.RUMBLE_NEUTRAL and dev.writes[-1][11] == 0b0001


def test_the_hub_lends_a_joycon_to_an_entry_that_may_take_it():
    found = [JOYCON_L, JOYCON_R]
    hub = hid.HidHub(start=False, enumerate_=lambda vid, pid: [d for d in found
                                                                if d["vendor_id"] == vid],
                     opener=lambda i: FakeJoyCon(), start_readers=False)
    hub.scan()
    assert {r.model.id for r in hub.readers.values()} == {"joycon-l", "joycon-r"}
    xbox_only, right, any_ = NS(), NS(), NS()
    assert hub.take(xbox_only, "xbox") is None
    assert hub.take(right, "joycon-r").model.id == "joycon-r"
    assert hub.take(any_, "nintendo").model.id == "joycon-l"
    assert models.may_be_hid("joycon-l") and models.may_be_hid("057e:2006")
    assert models.may_be_hid("nintendo") and not models.may_be_hid("xbox")
    assert hid.pad_devices(lambda vid, pid: [d for d in found if d["vendor_id"] == vid]) == found


def test_a_joycon_tape_reads_back_with_the_last_frame_standing_over_a_reply(tmp_path):
    rec = hid.Recorder(tmp_path / "jc.jsonl", "joycon-l", "bluetooth")
    rec.write(full_report(b5=0x01), t=0.0)
    rec.write(spi_reply(0x6020, b"\x00"), t=0.1)
    rec.write(full_report(), t=0.2)
    rec.close()
    now = [0.05]
    tape = hid.TapePad(tmp_path / "jc.jsonl", clock=lambda: now[0])
    assert tape.model.id == "joycon-l" and tape.nintendo and tape.kind == "l"
    assert tape.latest().buttons[models.CANON["A"]] == 1
    now[0] = 0.15
    assert tape.latest().buttons[models.CANON["A"]] == 1           # the reply: the frame stands
    now[0] = 0.25
    assert tape.latest().buttons[models.CANON["A"]] == 0


# ---- the pad and its device ----

def joycon_pad(reports=None) -> tuple[gp.Pad, hid.HidPad]:
    dev = FakeJoyCon(reports=reports if reports is not None else [full_report()] * 40)
    reader = stepped(JOYCON_L, dev)
    pad = gp.Pad(hid=True, controller="joycon-l")
    pad.claims = gp.Claims()
    pad.claims.hub = hid.HidHub(start=False, enumerate_=lambda v, p: [], start_readers=False)
    pad.claims.hub.readers[JOYCON_L["path"]] = reader
    pad.attach(pad.claims, role="joy")
    return pad, reader


def test_the_pad_reads_a_joycon_as_one_stick_and_its_motion_through_its_own_axes():
    pad, reader = joycon_pad()
    # the Joy-Con flat on its back: the chip's z is +1 g, which is "up out of the face"
    reader._take(full_report(accel=(0, 0, 4096 + 30), lstick=(2000, 2100), b5=0x02))
    pad.poll(dt=0.016)
    assert pad.on and pad.source == "hid" and pad.model.id == "joycon-l"
    assert pad.down(gp.Y) and pad.has("motion") and not pad.has("touch")
    assert set(pad.buttons_named) == {"A", "B", "X", "Y", "LB", "VIEW", "SHARE", "LSTICK", "LP", "RP"}
    assert pad.touch_lanes() is None
    lanes = dict(zip(gesture.MOTION_LANES, pad.motion_lanes(), strict=True))
    assert abs(lanes["roll"] - 0.5) < 0.02 and abs(lanes["pitch"] - 0.5) < 0.02
    # the shoulder end lifted: up now has a part along the chip's +x, which
    # the map reads as away from the player (−z) — the far edge up: pitch high
    for _ in range(80):
        reader._take(full_report(accel=(2900, 0, 2900), timer=_ & 0xFF))
        pad.poll(dt=0.05)
    lanes = dict(zip(gesture.MOTION_LANES, pad.motion_lanes(), strict=True))
    assert lanes["pitch"] > 0.65 and abs(lanes["roll"] - 0.5) < 0.05
    assert all(math.isfinite(v) for v in pad.lanes())


def test_the_pad_device_shows_a_joycons_ports_and_its_two_outputs_only():
    pad, reader = joycon_pad()
    reader._take(full_report())
    pad.poll(dt=0.016)
    ctx = NS(pads=pad.claims, table=None)
    dev = devices.PadDevice("joy", {"controller": "joycon-l"}, ctx)
    dev.io = pad
    names = {(p.scheme, p.name) for p in dev.sources}
    assert ("axis", "LX") in names and ("axis", "LT") in names
    assert ("axis", "RX") not in names and ("axis", "RT") not in names
    assert ("pad", "A") in names and ("pad", "LP") in names and ("pad", "MENU") not in names
    assert not any(s == "hat" for s, _ in names)
    assert ("motion", "shake") in names and not any(s == "touch" for s, _ in names)
    sinks = {p.name for p in dev.sinks}
    assert sinks == {str(devices.SINK_CHANNEL[k]) for k in ("rumble.low", "rumble.high", "players")}
    schemes, _feeds = devices.PadDevice.schemes_for({"controller": "joycon-l"})
    assert "motion" in schemes and "touch" in schemes
    assert "motion" not in devices.PadDevice.schemes_for({"controller": "xbox"})[0]


def test_the_on_screen_layout_draws_only_what_a_joycon_has():
    layout = gp.layout_for(models.MODELS["joycon-l"])
    sources = {c.source for c in layout}
    assert "axis:LX" in sources and "axis:RX" not in sources
    assert "pad:A" in sources and "pad:RSTICK" not in sources and "hat:UP" not in sources
    assert "pad:LP" in sources and "motion:roll" in sources and "pad:TOUCH" not in sources
    glyphs = {c.source: c.glyph for c in layout}
    assert glyphs["pad:A"] == "↓" and glyphs["pad:LP"] == "SL" and glyphs["axis:LT"] == "ZL"
    assert len(gp.layout_for(models.MODELS["procon"])) > len(layout)
    assert models.MODELS["edge"].has_control("RX") and not models.MODELS["joycon-r"].has_control("LB")
