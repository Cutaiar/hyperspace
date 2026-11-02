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

    def __init__(self, flash=None, reports=(), answer=True, deaf=()):
        self.flash = flash if flash is not None else {
            nintendo.SPI_STICK_L_FACTORY: L_FACTORY, nintendo.SPI_IMU_FACTORY: IMU}
        self.queue: list[bytes] = []
        self.reports = list(reports)
        self.writes: list[bytes] = []
        self.mode = None
        self.answer = answer            # False: the flash never answers
        self.deaf = dict(deaf)          # subcommand → how many sends it ignores before acking

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
        if self.deaf.get(cmd, 0) > 0:
            self.deaf[cmd] -= 1
            return len(d)
        if cmd == nintendo.SUB_SPI_READ:
            if self.answer:
                addr, n = struct.unpack_from("<IB", args, 0)
                data = self.flash.get(addr, b"\xff" * n)
                self.queue.append(spi_reply(addr, bytes(data[:n]).ljust(n, b"\xff")))
            return len(d)
        if cmd == nintendo.SUB_MODE:
            self.mode = args[0]
        ack = bytearray(49)
        ack[0], ack[13], ack[14] = nintendo.REPORT_REPLY, nintendo.ACK, cmd
        self.queue.append(bytes(ack))                 # every subcommand is acknowledged
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


def test_both_sides_read_the_face_by_position():
    """Held the same way, the (L)'s ↓ and the (R)'s B are the bottom button:
    both ``pad:A``; the (R)'s own letters stay as its glyphs."""
    def one(kind, **bits):
        f = nintendo.decode(full_report(**bits), kind)
        return [NAMES[i] for i, v in enumerate(f.buttons) if v]
    assert one("l", b5=0x01) == ["A"] and one("r", b3=0x04) == ["A"]      # ↓ and B: the bottom
    assert one("l", b5=0x04) == ["B"] and one("r", b3=0x08) == ["B"]      # → and A: the right
    assert one("l", b5=0x08) == ["X"] and one("r", b3=0x01) == ["X"]      # ← and Y: the left
    assert one("l", b5=0x02) == ["Y"] and one("r", b3=0x02) == ["Y"]      # ↑ and X: the top
    r = models.MODELS["joycon-r"]
    assert (models.glyph(r, "A", "A"), models.glyph(r, "B", "B"),
            models.glyph(r, "X", "X"), models.glyph(r, "Y", "Y")) == ("B", "A", "Y", "X")
    # the simple report before the mode is set: the same by position; the
    # (R)'s stick click is byte 2's 0x08 (0x04 is the left stick's)
    simple = nintendo.decode(bytes([0x3F, 0x04, 0x08, 0x08]), "r")
    assert [NAMES[i] for i, v in enumerate(simple.buttons) if v] == ["A", "LSTICK"]
    assert not nintendo.decode(bytes([0x3F, 0x00, 0x04, 0x08]), "r").buttons[models.CANON["LSTICK"]]
    assert nintendo.decode(bytes([0x3F, 0x00, 0x04, 0x08]), "l").buttons[models.CANON["LSTICK"]]


def test_the_low_band_keeps_its_half_step_and_its_ceiling():
    """An odd amplitude code's half-step is the 0x80 flag in the low band's
    first byte (rumble_data_table.md); the low band's frequency code stops
    at 0x7F."""
    odd = next(a for a in (0.30, 0.31, 0.32, 0.33, 0.34) if nintendo._amp_code(a) & 1)
    even = next(a for a in (0.30, 0.31, 0.32, 0.33, 0.34) if not nintendo._amp_code(a) & 1)
    b_odd, b_even = nintendo.rumble_bytes(0.0, odd), nintendo.rumble_bytes(0.0, even)
    assert b_odd[2] & 0x80 and not b_even[2] & 0x80
    assert b_odd[3] == (nintendo._amp_code(odd) >> 1) + 0x40
    assert (b_odd[2] & 0x7F) == (b_even[2] & 0x7F) == nintendo.RUMBLE_NEUTRAL[2]   # 160 Hz both
    assert b_odd[:2] == b_even[:2] == nintendo.RUMBLE_NEUTRAL[:2]              # the high band off
    high = nintendo.rumble_bytes(0.0, 1.0, low_hz=2000.0)
    assert (high[2] & 0x7F) <= 0x7F and high == nintendo.rumble_bytes(0.0, 1.0, low_hz=626.0)
    assert nintendo.rumble_bytes(0.0, 1.0, low_hz=5.0) == nintendo.rumble_bytes(0.0, 1.0, low_hz=40.875)


def test_a_recentred_stick_still_reaches_full_deflection():
    cal = nintendo.calibration({nintendo.SPI_STICK_L_FACTORY: L_FACTORY}, "l")
    c = nintendo.recentre(cal, "l", [(2000 + 120, 2100 - 80)] * 30)
    assert (c.left.cx, c.left.cy) == (2120, 2020)
    assert (c.left.x_above, c.left.x_below) == (1500 - 120, 1300 + 120)
    assert (c.left.y_above, c.left.y_below) == (1400 + 80, 1600 - 80)
    assert c.left.norm(2000 + 1500, 2100 + 1400) == (1.0, 1.0)      # the flash's extremes still ±1
    assert c.left.norm(2000 - 1300, 2100 - 1600) == (-1.0, -1.0)
    assert c.left.norm(2120, 2020) == (0.0, 0.0)


def test_a_nintendo_pad_is_never_seized_on_a_guess_about_its_bus():
    """Without hidapi's bus_type (before 0.14) the interface number tells
    USB (0 or more) from Bluetooth (−1); unknown both ways reads as USB."""
    no_bus_bt = {**JOYCON_L, "path": b"bt-old"}
    no_bus_bt.pop("bus_type")
    no_bus_bt["interface_number"] = -1
    no_bus_usb = {**no_bus_bt, "path": b"usb-old", "interface_number": 0}
    unknown = {**no_bus_bt, "path": b"unknown"}
    unknown.pop("interface_number")
    found = [no_bus_bt, no_bus_usb, unknown]
    assert hid.pad_devices(lambda vid, pid: [d for d in found if d["vendor_id"] == vid]) == [no_bus_bt]
    assert hid._on_usb(no_bus_usb) and not hid._on_usb(no_bus_bt) and hid._on_usb(unknown)
    assert not hid._on_usb(JOYCON_L) and hid._on_usb({**JOYCON_L, "bus_type": 1})


def test_closing_the_reader_cuts_a_connect_sequence_short():
    """A pad that never acknowledges would hold `setup` for ~12 s; close()
    ends it inside the hub's join, so a restart's new image finds the pad
    free."""
    import threading
    import time

    deaf = FakeJoyCon(deaf={nintendo.SUB_MODE: 99, nintendo.SUB_IMU: 99,
                            nintendo.SUB_VIBRATION: 99}, answer=False)
    r = hid.HidPad(JOYCON_L, start=False, opener=lambda i: deaf)
    t = threading.Thread(target=r._run, daemon=True)
    t0 = time.monotonic()
    t.start()
    time.sleep(0.05)
    r.close()
    t.join(0.5)
    assert not t.is_alive() and time.monotonic() - t0 < 0.6
    assert not r.alive
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
    assert c.left.cx == 2120 and c.left.cy == 2020 and c.left.x_above == 1500 - 120
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
    rum, out = nintendo.output_reports(sony.Effects(players=sony.player_bits(2), rumble_low=0.8),
                                       lambda: next(seqs))
    assert rum[0] == nintendo.RUMBLE_ID and rum[1] == 3 and rum[2:6] == rum[6:10]
    assert rum[2:6] == nintendo.rumble_bytes(0.0, 0.8)
    assert out[0] == 0x01 and out[1] == 4 and out[10] == nintendo.SUB_LEDS and out[11] == 0b0011
    assert out[2:6] == out[6:10] == nintendo.rumble_bytes(0.0, 0.8)
    assert nintendo.rumbling(sony.Effects(rumble_low=0.8)) and not nintendo.rumbling(sony.Effects())
    assert nintendo.subcommand(16, 0x40, b"\x01")[1] == 0            # the counter wraps at 16
    # the high band's code starts at 0x60 (80 Hz): a lower frequency is held there
    low = nintendo.rumble_bytes(0.5, 0.0, high_hz=60.0)
    assert low == nintendo.rumble_bytes(0.5, 0.0, high_hz=80.0)
    assert low[0] == 0 and low[1] == nintendo._amp_code(0.5) * 2    # the amplitude byte intact


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


def test_setup_waits_for_each_ack_and_says_what_never_answered():
    """Each setup subcommand is sent again until its 0x21 ack, up to
    SETUP_TRIES; one that never acks is named in the note (a mode that
    never took leaves the pad in the simple report, buttons only)."""
    dev = FakeJoyCon(reports=[full_report()] * 40, deaf={nintendo.SUB_MODE: 1})
    r = stepped(JOYCON_L, dev)
    modes = [w for w in dev.writes if w[0] == nintendo.OUT_ID and w[10] == nintendo.SUB_MODE]
    assert len(modes) == 2 and dev.mode == nintendo.FULL_MODE and r.note == ""
    deaf = FakeJoyCon(reports=[full_report()] * 40, deaf={nintendo.SUB_IMU: 99})
    r2 = stepped(JOYCON_L, deaf)
    imus = [w for w in deaf.writes if w[0] == nintendo.OUT_ID and w[10] == nintendo.SUB_IMU]
    assert len(imus) == nintendo.SETUP_TRIES and "sensors on" in r2.note
    assert not r2.calibration.nominal                      # the flash still answered
    assert nintendo.acked(deaf.queue[-1] if deaf.queue else b"", nintendo.SUB_IMU) is False
    ack = bytearray(49)
    ack[0], ack[13], ack[14] = nintendo.REPORT_REPLY, nintendo.ACK, nintendo.SUB_IMU
    assert nintendo.acked(bytes(ack), nintendo.SUB_IMU) and not nintendo.acked(bytes(ack), 0x03)


def test_the_sensors_axes_are_per_side_and_only_the_left_is_verified():
    assert nintendo.axis_map_for("l") is nintendo.AXIS_MAP
    assert nintendo.axis_map_for("pro") is nintendo.AXIS_MAP
    r_map = nintendo.axis_map_for("r")
    assert r_map != nintendo.AXIS_MAP
    # the (R)'s chip the other way up: its y and z signs flipped, x as the (L)'s
    for (il, sl), (ir, sr) in zip(nintendo.AXIS_MAP.accel, r_map.accel, strict=True):
        assert il == ir
        assert (sl == sr) == (il == 0)
    assert nintendo.VERIFIED_MAPS == {"l"}
    right = stepped(JOYCON_R, FakeJoyCon(flash={}, reports=[full_report()] * 40))
    assert right.axis_map is r_map
    assert gesture.axis_map_of(None, right) is r_map                             # none set: the reader's
    ident = gesture.AxisMap()
    assert gesture.axis_map_of(ident, right) is ident              # the identity, set on purpose, wins
    mine = gesture.AxisMap(accel=((2, 1.0), (1, 1.0), (0, 1.0)))
    assert gesture.axis_map_of(mine, right) is mine                              # a pad's override wins
    assert gesture.axis_map_of(None, NS()) == gesture.AxisMap()                  # a Sony reader: the default
    assert gp.Pad().axis_map is None                                             # nothing set on a new pad


def test_a_nintendo_pad_over_usb_is_left_to_glfw_until_the_handshake_is_built():
    usb_joycon = {**JOYCON_L, "path": b"jc-usb", "bus_type": 1}
    usb_edge = {"path": b"edge-usb", "vendor_id": 0x054C, "product_id": 0x0DF2, "usage_page": 1,
                "usage": 5, "bus_type": 1}
    found = [JOYCON_L, usb_joycon, usb_edge]
    got = hid.pad_devices(lambda vid, pid: [d for d in found if d["vendor_id"] == vid])
    assert got == [usb_edge, JOYCON_L]


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
    # the first send: the rumble (0x10, reply-free) and the lights (a 0x30 subcommand)
    assert [w[0] for w in dev.writes] == [nintendo.RUMBLE_ID, nintendo.OUT_ID]
    assert dev.writes[1][10] == nintendo.SUB_LEDS and dev.writes[1][11] == 0b0001
    r._sent_t = 0.0
    r.send(sony.Effects(players=sony.player_bits(1)))
    r._write(dev)
    assert len(dev.writes) == 2                                       # the same, no rumble: no write
    r.send(sony.Effects(players=sony.player_bits(1), rumble_high=0.5))
    r._sent_t = 0.0
    r._write(dev)
    r._sent_t -= nintendo.RUMBLE_REFRESH_S
    r._write(dev)
    # rumble on, then refreshed: 0x10 both times, never a subcommand (no 0x21
    # reply to push the newest input frame aside) while the lights stand
    assert [w[0] for w in dev.writes[2:]] == [nintendo.RUMBLE_ID, nintendo.RUMBLE_ID]
    assert dev.writes[-1][2:6] == nintendo.rumble_bytes(0.5, 0.0)
    r.send(sony.Effects(players=sony.player_bits(3), rumble_high=0.5))
    r._sent_t = 0.0
    r._write(dev)
    assert [w[0] for w in dev.writes[4:]] == [nintendo.RUMBLE_ID, nintendo.OUT_ID]   # lights changed
    assert dev.writes[-1][11] == 0b0111
    r._neutral(dev)
    assert dev.writes[-1][0] == nintendo.RUMBLE_ID and dev.writes[-1][2:6] == nintendo.RUMBLE_NEUTRAL


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


# ---- the pad window's readouts (plan 46: the Joy-Con drawn as itself) ----

def _drawn(view: str, pad, st=None):
    from hyperspace import ui_pad_lab, ui_pad_views
    pen = ui_pad_lab.Pen()
    ui_pad_lab.VIEWS[view](pen, ui_pad_views.read(pad), {} if st is None else st)
    return pen.hits


def test_the_reading_carries_a_joycons_calibration_and_sensors():
    from hyperspace import ui_pad_views
    pad, reader = joycon_pad([full_report(lstick=(2000 + 100, 2100 - 50))] * 40)
    reader._take(full_report(lstick=(2100, 2050), accel=(0, 0, 4096)))
    pad.poll(dt=0.016)
    pad.send_effects(sony.Effects(players=sony.player_bits(2), rumble_low=0.5))
    r = ui_pad_views.read(pad)
    assert r.nintendo and r.kind == "l" and not r.sony
    assert r.stick_raw == (2100, 2050) and r.stick_centre == (2100, 2050) and r.centre_from == "rest"
    (_gx, _gy, _gz), (ax, ay, az) = r.sensors
    assert abs(ay - 1.0) < 0.02 and abs(ax) < 0.02 and abs(az) < 0.02    # up out of the face
    assert not r.has_control("RX") and r.has_control("LX") and not r.has_control("UP")
    groups = dict(ui_pad_views._lane_rows(r))
    assert [s for s, *_ in groups["sticks"]] == ["axis:LX", "axis:LY"]
    assert [s for s, *_ in groups["triggers"]] == ["axis:LT"] and "d-pad" not in groups
    assert "pad:LP" in {s for s, *_ in groups["buttons"]} and "pad:MENU" not in {
        s for s, *_ in groups["buttons"]}
    assert groups["stick calibration"][2][0] == "centre (rest)"
    assert "sensors (pad axes)" in groups
    # the raw bars run over the calibration's reach (x_above 1500), as the LX row does
    reader._take(full_report(lstick=(2100 + 750, 2050), timer=9))
    pad.poll(dt=0.016)
    r2 = ui_pad_views.read(pad)
    groups2 = dict(ui_pad_views._lane_rows(r2))
    reach = reader.calibration.left.x_above                   # 1500 less the recentre's 100
    assert reach == 1400
    assert abs(groups2["stick calibration"][0][2] - (0.5 + 0.5 * 750 / reach)) < 1e-6
    # the LX row is the same reading after the app's deadzone rescale
    v = 750 / reach
    assert abs(r2.axes["LX"] - (0.5 + 0.5 * (v - gp.DEADZONE) / (1 - gp.DEADZONE))) < 1e-6
    assert [s for s, *_ in groups["out (sent now)"]] == ["players", "rumble heavy", "rumble light"]
    assert groups["out (sent now)"][0][2] == 0.5                       # two of four lights


def test_the_lab_draws_a_joycon_as_itself():
    from hyperspace import ui_pad_lab
    pad, reader = joycon_pad()
    reader._take(full_report(b5=0x01 | 0x20 | 0x80, accel=(0, 0, 4096)))   # ↓, SL, ZL
    pad.poll(dt=0.016)
    pad.send_effects(sony.Effects(players=sony.player_bits(1), rumble_high=0.4))
    for view in ("faithful", "cockpit"):
        hits = _drawn(view, pad)
        for x, y, w, h, source in hits:
            assert 0 <= x and x + w <= ui_pad_lab.DESIGN_W, (view, source)
            assert 0 <= y and y + h <= ui_pad_lab.DESIGN_H, (view, source)
        got = {h[4] for h in hits}
        assert {"pad:A", "pad:B", "pad:X", "pad:Y", "pad:LSTICK", "axis:LX", "axis:LY",
                "axis:LT", "pad:LB", "pad:LP", "pad:RP", "pad:VIEW", "pad:SHARE",
                "motion:roll"} <= got, (view, got)
        assert not got & {"pad:RSTICK", "axis:RX", "axis:RT", "pad:RB", "hat:UP", "pad:TOUCH",
                          "pad:MENU", "pad:GUIDE"}, (view, got)
    st = {}
    for _ in range(ui_pad_lab.TRAIL + 5):
        _drawn("cockpit", pad, st)
    assert [k for k, _t in st["events"]] == ["pad:A", "pad:LP"]
    # Faithful's six-axis scope: a trace per axis, kept on the panel, capped
    scope = {}
    for _ in range(ui_pad_lab.SCOPE_N + 7):
        _drawn("faithful", pad, scope)
    assert set(scope["scope"]) == {"ax", "ay", "az", "gx", "gy", "gz"}
    assert {len(t) for t in scope["scope"].values()} == {ui_pad_lab.SCOPE_N}
    assert abs(scope["scope"]["ay"][-1] - 1.0) < 0.05           # flat: +1 g out of the face
    # the (R): its face, R / ZR, + and HOME, the one stick still the left stick
    dev = FakeJoyCon(reports=[full_report(b3=0x04 | 0x80)] * 40)      # its B (the bottom), ZR
    reader = stepped(JOYCON_R, dev)
    pad = gp.Pad(hid=True, controller="joycon-r")
    pad.claims = gp.Claims()
    pad.claims.hub = hid.HidHub(start=False, enumerate_=lambda v, p: [], start_readers=False)
    pad.claims.hub.readers[JOYCON_R["path"]] = reader
    pad.attach(pad.claims, role="joy")
    reader._take(full_report(b3=0x04 | 0x80))
    pad.poll(dt=0.016)
    for view in ("faithful", "cockpit"):
        got = {h[4] for h in _drawn(view, pad)}
        assert {"pad:A", "axis:RT", "pad:RB", "pad:MENU", "pad:GUIDE", "pad:LSTICK",
                "axis:LX"} <= got, (view, got)
        assert not got & {"axis:LT", "pad:LB", "pad:VIEW", "pad:SHARE", "pad:RSTICK"}, (view, got)
