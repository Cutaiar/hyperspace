"""The DualSense / Edge report format (pads/sony.py) against the spec's
vectors (docs/plans/assets/42-controllers/sony-hid.md §8): real bytes for
the calibration and the BT feature CRC, computed ones for input framing
and the output CRCs."""

import struct

import pytest

from hyperspace.pads import models, sony

# §8: the hid-tools DualSense calibration dump (USB form, no CRC)
CALIBRATION = bytes.fromhex(
    "05ffff f2ff 0400 9d22 5edd 9222 52dd ba22 51dd 1c02 1c02 fb1f 05e0 831f 99df 0720 fcdf"
    " 0500 0000 0000".replace(" ", ""))
# §8: firmware info, its last four bytes a real BT feature CRC (seed 0xA3)
FIRMWARE = bytes.fromhex(
    "20 41 75 67 20 31 38 20 32 30 32 30 30 36 3a 32 30 3a 32 39 03 00 04 00 13 03 00 00"
    " 1e 00 00 01 41 0a 00 00 00 00 00 00 00 00 00 00 04 02 00 00 2a 00 01 00 06 00 01 00"
    " 06 00 00 00 98 d8 b3 b7".replace(" ", ""))


def usb_report(**set_bytes) -> bytearray:
    """A USB 0x01 report with the sticks centred, the hat released and
    both touch points up; `set_bytes` {payload offset: value}."""
    r = bytearray(64)
    r[0] = 0x01
    p = memoryview(r)[1:]
    p[0:4] = b"\x80\x80\x80\x80"
    p[7] = 0x08
    p[32] = 0x80
    p[36] = 0x80
    for k, v in set_bytes.items():
        p[int(k[1:])] = v
    return r


def bt_report(payload: bytes, tag: int = 0x01) -> bytes:
    r = bytearray(78)
    r[0], r[1] = 0x31, tag
    r[2:2 + len(payload)] = payload[:72]
    struct.pack_into("<I", r, 74, sony.crc32(sony.BT_INPUT_SEED, r[:74]))
    return bytes(r)


def test_the_spec_vectors_crc():
    # §8: the Edge right-back-button BT report, the reset-LEDs and lightbar outputs
    r = bt_report(bytes(usb_report(p9=0x80))[1:])
    assert r[74:] == bytes.fromhex("43701135")
    assert sony.bt_crc_ok(r)
    reset = sony.output_report(sony.Effects(), bluetooth=True, seq=0, first=True)
    assert reset[41] == 0x02 and reset[44] == 0x02 and reset[74:] == bytes.fromhex("43e63136")
    blue = bytearray(78)
    blue[0], blue[1], blue[2], blue[4], blue[49] = 0x31, 0x10, 0x10, 0x04, 0x80
    assert sony.crc32(sony.BT_OUTPUT_SEED, blue[:74]) == 0x4CEA2342
    assert len(FIRMWARE) == 64 and sony.bt_crc_ok(FIRMWARE, sony.BT_FEATURE_SEED)


def test_usb_and_bluetooth_decode_the_same_payload():
    usb = usb_report(p9=0x80)
    a = sony.decode(usb)
    b = sony.decode(bt_report(bytes(usb)[1:]))
    assert a.kind == sony.USB_IN and b.kind == sony.BT_IN
    for f in (a, b):
        assert f.buttons[models.RP] == 1 and sum(f.buttons) == 1     # the Edge's right back button
        assert f.hat == 0 and not f.touches[0].down and not f.touches[1].down
        assert all(abs(v) < 0.01 for v in f.axes[:4]) and f.axes[4:] == [-1.0, -1.0]


def test_every_button_lands_in_the_pads_vocabulary():
    cases = {(7, 0x10): "X", (7, 0x20): "A", (7, 0x40): "B", (7, 0x80): "Y",
             (8, 0x01): "LB", (8, 0x02): "RB", (8, 0x10): "VIEW", (8, 0x20): "MENU",
             (8, 0x40): "LSTICK", (8, 0x80): "RSTICK", (9, 0x01): "GUIDE", (9, 0x02): "TOUCH",
             (9, 0x04): "SHARE", (9, 0x10): "LFN", (9, 0x20): "RFN", (9, 0x40): "LP",
             (9, 0x80): "RP"}
    for (byte, bit), name in cases.items():
        r = usb_report()
        r[1 + byte] |= bit
        f = sony.decode(r)
        assert [i for i, v in enumerate(f.buttons) if v] == [models.CANON[name]], name
    # the digital L2 / R2 bits carry nothing (the axes do)
    r = usb_report(p8=0x0C)
    assert not any(sony.decode(r).buttons)


def test_the_hat_sticks_and_triggers():
    bits = [sony.decode(usb_report(p7=n)).hat for n in range(9)]
    assert bits == [1, 3, 2, 6, 4, 12, 8, 9, 0]
    f = sony.decode(usb_report(p0=0, p1=0, p2=255, p3=255, p4=255, p5=0))
    assert f.axes[0] == -1.0 and f.axes[1] == -1.0        # left / up: −1, as GLFW
    assert f.axes[2] == 1.0 and f.axes[3] == 1.0
    assert f.axes[4] == 1.0 and f.axes[5] == -1.0         # a trigger rests at −1


def test_touch_points_sensors_and_battery():
    r = usb_report()
    p = memoryview(r)[1:]
    # finger 5 at (1919, 1079): x 12 bits, y 12 bits
    x, y = 1919, 1079
    p[32:36] = bytes([5, x & 0xFF, ((x >> 8) & 0x0F) | ((y & 0x0F) << 4), y >> 4])
    struct.pack_into("<3h", p, 15, 100, -200, 300)
    struct.pack_into("<3h", p, 21, 0, 8192, -50)
    p[52] = 0x17                                            # charging, level 7
    f = sony.decode(r)
    t = f.touches[0]
    assert t.down and (t.id, t.x, t.y) == (5, 1919, 1079) and not f.touches[1].down
    assert f.gyro == (100, -200, 300) and f.accel == (0, 8192, -50)
    assert (f.battery, f.charging) == (7, 1)


def test_bluetooth_simple_and_rejects():
    simple = bytes([0x01, 0x00, 0x80, 0x80, 0xFF, 0x28, 0x01, 0x02, 0x40, 0x00])
    f = sony.decode(simple)
    assert f.kind == sony.BT_SIMPLE and not f.full
    on = {n for n, i in models.CANON.items() if f.buttons[i]}
    assert on == {"A", "LB", "TOUCH"} and f.hat == 0      # 0x28: the hat released, the cross
    assert f.axes[0] == -1.0 and f.axes[3] == 1.0
    # a 0x01 report padded to 78 over Bluetooth is still the simple one (SDL)
    padded = simple + bytes(68)
    assert sony.decode(padded, bluetooth=True).kind == sony.BT_SIMPLE
    # a bad CRC, a microphone report, an unknown id and a short read: nothing
    good = bt_report(bytes(usb_report())[1:])
    assert sony.decode(good[:-1] + bytes([good[-1] ^ 1])) is None
    assert sony.decode(bt_report(bytes(usb_report())[1:], tag=0x02)) is None
    assert sony.decode(bytes([0x09] + [0] * 63)) is None
    assert sony.decode(b"\x01\x80") is None and sony.decode(b"") is None


def test_calibration_matches_linux_selftest_and_rejects_nonsense():
    c = sony.calibration(CALIBRATION)
    assert not c.nominal
    assert [round(s, 6) for _, s in c.gyro] == [0.060924, 0.060921, 0.06078]
    assert [b for b, _ in c.accel] == [0.0, -114.0, 2.0]
    assert [round(2 / s) for _, s in c.accel] == [16374, 16362, 16395]
    assert c.accel_g((8187, 8192 - 114, 2))[0] == pytest.approx(1.0, abs=1e-3)
    # nothing believable: the nominal scales
    assert sony.calibration(b"\x05" + bytes(40)).nominal
    assert sony.calibration(b"\x06" + CALIBRATION[1:]).nominal
    nominal = sony.Calibration()
    assert nominal.gyro_dps((16, 0, -16)) == (1.0, 0.0, -1.0)
    assert sony.update_version(FIRMWARE) == 0x0204


def test_trigger_effects_are_the_official_forms():
    off = sony.trigger_block(sony.Trigger())
    assert off == bytes([0x05]) + bytes(10)
    assert sony.trigger_block(sony.Trigger("resist", strength=0.01)) == off   # rounds to 0: off
    full = sony.trigger_block(sony.Trigger("resist", start=0.0, strength=1.0))
    assert full[0] == 0x21 and struct.unpack_from("<H", full, 1)[0] == 0x3FF
    assert struct.unpack_from("<I", full, 3)[0] == sum(7 << (3 * z) for z in range(10))
    half = sony.trigger_block(sony.Trigger("resist", start=0.5, strength=0.5))
    mask = struct.unpack_from("<H", half, 1)[0]
    assert mask == sum(1 << z for z in range(4, 10))       # zones from position round(4.5) = 4
    pulse = sony.trigger_block(sony.Trigger("pulse", start=0.0, strength=1.0, freq=30))
    assert pulse[0] == 0x26 and pulse[9] == 30
    for block in (off, full, half, pulse):
        assert len(block) == 11 and block[0] not in (0xFC, 0xFD, 0xFE)


def test_output_reports_carry_the_effects():
    e = sony.Effects(light=(10, 20, 30), players=sony.player_bits(2), mic=1,
                     rumble_low=1.0, rumble_high=0.5,
                     right=sony.Trigger("resist", 0.15, 1.0))
    usb = sony.output_report(e, bluetooth=False, usb_len=64)
    assert len(usb) == 64 and usb[0] == 0x02
    c = usb[1:]
    assert c[sony.C_FLAGS0] & sony.F0_HAPTICS and c[sony.C_FLAGS2] & sony.F2_RUMBLE_V2
    assert (c[sony.C_RUMBLE_LOW], c[sony.C_RUMBLE_HIGH]) == (255, 128)
    assert tuple(c[sony.C_RGB:sony.C_RGB + 3]) == (10, 20, 30)
    assert c[sony.C_PLAYERS] == 0x0A | sony.PLAYERS_INSTANT and c[sony.C_MIC_LED] == 1
    assert c[sony.C_TRIGGER_RIGHT] == 0x21 and c[sony.C_TRIGGER_LEFT] == 0x05
    v1 = sony.output_report(e, bluetooth=False, rumble_v2=False, usb_len=48)
    assert len(v1) == 48 and v1[1] & sony.F0_RUMBLE_V1 and not v1[1 + sony.C_FLAGS2] & 0x04
    bt = sony.output_report(e, bluetooth=True, seq=3)
    assert len(bt) == 78 and bt[1] == 0x30 and bt[2] == 0x10 and bt[3:50] == c[:47]
    assert sony.bt_crc_ok(bt, sony.BT_OUTPUT_SEED)
    assert [sony.player_bits(n) for n in range(6)] == [0, 0x04, 0x0A, 0x15, 0x1B, 0x1F]
    assert e.key() == sony.Effects(**e.__dict__).key()
