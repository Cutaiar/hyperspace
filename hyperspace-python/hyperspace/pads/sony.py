"""The DualSense and DualSense Edge report format (plan 42), bytes ↔ values.

Everything here was written from published sources before a controller
was in hand — SDL's ``SDL_hidapi_ps5.c``, Linux's ``hid-playstation.c``,
hid-tools' descriptors — pinned with line numbers in
``docs/plans/assets/42-controllers/sony-hid.md``. Where the sources
disagree, or only hardware can say, the constant is named and the
probe (``tools/hid_probe.py``) settles it.

**Input** (`decode`). Three reports, told apart by id and length:

  USB      0x01, 64 bytes; the payload starts at byte 1
  BT full  0x31, 78 bytes; byte 1 a sequence tag, the payload at byte 2,
           a CRC32 over ``0xA1`` + the first 74 bytes in the last four
  BT simple 0x01, 10 bytes — what a pad sends over Bluetooth until a
           feature report is read; sticks, triggers, face and shoulder
           buttons only

One payload layout serves USB and BT full (`_full`). Every control
lands in the pad's vocabulary (models.CANON): the cross is ``A``, the
Create button ``VIEW``, the mic button ``SHARE``, the Edge's back
buttons ``LP`` / ``RP`` and its Fn buttons ``LFN`` / ``RFN``; the hat
becomes GLFW's bitmask, the axes GLFW's ±1 (a stick up −1, a trigger
resting at −1), so `gamepad.Pad` reads a Sony pad exactly as it reads an
Xbox one.

**Output** (`output_report`). One `Effects` — light bar, player LEDs,
mic LED, the two rumble motors, each trigger's resistance — becomes one
report: USB 0x02 (64 bytes), BT 0x31 (78 bytes, its sequence tag and
CRC32 over ``0xA2`` + the report).

A leaf: the standard library and models.py only.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

from .models import CANON, N_CANON

USB_IN, BT_IN, BT_SIMPLE = "usb", "bt", "bt-simple"
USB_REPORT_ID, BT_REPORT_ID = 0x01, 0x31
USB_IN_LEN, BT_IN_LEN, BT_SIMPLE_LEN = 64, 78, 10
IN_LEN = BT_IN_LEN            # a read's room (the longest report), as every codec names it
USB_OUT_ID, BT_OUT_ID = 0x02, 0x31
USB_OUT_LEN, BT_OUT_LEN = 64, 78
CALIBRATION_ID, CALIBRATION_LEN = 0x05, 41     # also what switches BT to the full report
BT_INPUT_SEED, BT_OUTPUT_SEED, BT_FEATURE_SEED = 0xA1, 0xA2, 0xA3
# byte 1's low nibble on a BT input report: 1 is input (0 let through — the
# sources never show it, and dropping every report would be worse); 2 is
# the microphone's, never decoded (spec §2.1, the reviewed Linux patch)
BT_INPUT_TAGS = (0, 1)

FIRMWARE_ID, FIRMWARE_LEN = 0x20, 64            # the update version: which rumble mode
FEATURE_READ_LEN = 64                           # hidapi reads a feature into this
# the touchpad's resolution: Linux's 1920 × 1080 (SDL says 1070 high; an
# Edge's corners read 0–1919 × 0–1079, 2026-11-02)
TOUCH_W, TOUCH_H = 1920, 1080
# the sensors' raw scales when no calibration was read (SDL's fallback,
# spec §4.1): about 16 counts per deg/s and 8192 per g. Linux's 1024 and
# 8192 are its output units, not the sensors'
GYRO_PER_DEG_S = 16.0
ACCEL_PER_G = 8192.0
CALIBRATION_SLACK = 0.5      # a calibration more than this far off nominal is not believed
BIAS_MAX = 1024              # …nor one with a gyro bias past this (SDL)

# the hat's 0–7 (up, clockwise) as GLFW's bits: up 1, right 2, down 4, left 8
_HAT = (1, 1 | 2, 2, 2 | 4, 4, 4 | 8, 8, 8 | 1)

# (payload byte, bit) → canonical button, the face and the shoulders, then
# the PS row; the Edge's four sit in the PS row's high bits (Linux 115-119)
_BUTTONS = (
    (7, 0x10, "X"), (7, 0x20, "A"), (7, 0x40, "B"), (7, 0x80, "Y"),
    (8, 0x01, "LB"), (8, 0x02, "RB"), (8, 0x10, "VIEW"), (8, 0x20, "MENU"),
    (8, 0x40, "LSTICK"), (8, 0x80, "RSTICK"),
    (9, 0x01, "GUIDE"), (9, 0x02, "TOUCH"), (9, 0x04, "SHARE"),
    (9, 0x10, "LFN"), (9, 0x20, "RFN"), (9, 0x40, "LP"), (9, 0x80, "RP"),
)
_BUTTON_IDX = tuple((byte, bit, CANON[name]) for byte, bit, name in _BUTTONS)


@dataclass
class Touch:
    """One touchpad contact: `down` while the finger is on, `id` the
    pad's count for this contact (it changes when a new finger lands),
    `x`, `y` in touchpad units (0 at the top-left)."""

    down: bool = False
    id: int = 0
    x: int = 0
    y: int = 0


@dataclass
class Frame:
    """One decoded input report in the pad's vocabulary."""

    kind: str                              # USB_IN, BT_IN or BT_SIMPLE
    buttons: list[int]                     # N_CANON long, by models.CANON
    hat: int                               # GLFW's bitmask
    axes: list[float]                      # LX LY RX RY LT RT, GLFW's ±1
    touches: tuple[Touch, Touch] = (Touch(), Touch())
    gyro: tuple[int, int, int] = (0, 0, 0)     # raw, the sensor's x, y, z
    accel: tuple[int, int, int] = (0, 0, 0)
    sensor_time: int = 0                   # µs-ish counter (wraps), BT and USB full only
    seq: int = 0                           # the report's counter
    battery: int = -1                      # 0–10 (×10 %); −1 unknown
    charging: int = -1                     # the status nibble: 0 discharging, 1 charging, 2 full
    raw_buttons: bytes = b""               # payload bytes 7–10 as sent, for the probe
    raw_sticks: tuple = ()                 # a Joy-Con's 12-bit (x, y) per stick (plan 43's lab)

    @property
    def full(self) -> bool:
        """Does this report carry the touchpad and the motion sensors?"""
        return self.kind != BT_SIMPLE


def _stick(v: int) -> float:
    """A stick byte (0x80 centre, 0 up / left) as GLFW's −1…+1."""
    return max(-1.0, min(1.0, (v - 127.5) / 127.5))


def _trigger(v: int) -> float:
    """A trigger byte (0 rest, 255 full) as GLFW's −1 rest … +1 full."""
    return v / 127.5 - 1.0


def _touch(b: bytes) -> Touch:
    return Touch(down=not (b[0] & 0x80), id=b[0] & 0x7F,
                 x=b[1] | ((b[2] & 0x0F) << 8), y=(b[2] >> 4) | (b[3] << 4))


def _buttons(p: bytes) -> list[int]:
    out = [0] * N_CANON
    for byte, bit, i in _BUTTON_IDX:
        if p[byte] & bit:
            out[i] = 1
    return out


def _full(kind: str, p: bytes) -> Frame:
    """The USB / BT full payload (Linux's struct dualsense_input_report)."""
    hat_n = p[7] & 0x0F
    gyro = struct.unpack_from("<3h", p, 15)
    accel = struct.unpack_from("<3h", p, 21)
    (ts,) = struct.unpack_from("<I", p, 27)
    status = p[52] if len(p) > 52 else 0
    return Frame(
        kind=kind, buttons=_buttons(p), hat=_HAT[hat_n] if hat_n < 8 else 0,
        axes=[_stick(p[0]), _stick(p[1]), _stick(p[2]), _stick(p[3]),
              _trigger(p[4]), _trigger(p[5])],
        touches=(_touch(p[32:36]), _touch(p[36:40])),
        gyro=gyro, accel=accel, sensor_time=ts, seq=p[6],
        battery=min(10, status & 0x0F), charging=(status >> 4) & 0x0F,
        raw_buttons=bytes(p[7:11]))


def _simple(r: bytes) -> Frame:
    """The BT simple report: sticks 1–4, hat and face 5, shoulders 6,
    PS / touchpad click 7, triggers 8–9 (SDL 72-81). No sensors, no
    touch, no Edge buttons."""
    p = bytes(r[1:])
    shaped = bytearray(10)
    shaped[7], shaped[8], shaped[9] = p[4], p[5], p[6] & 0x03
    hat_n = p[4] & 0x0F
    return Frame(
        kind=BT_SIMPLE, buttons=_buttons(bytes(shaped)), hat=_HAT[hat_n] if hat_n < 8 else 0,
        axes=[_stick(p[0]), _stick(p[1]), _stick(p[2]), _stick(p[3]),
              _trigger(p[7]), _trigger(p[8])],
        raw_buttons=bytes(p[4:7]))


def crc32(seed: int, data: bytes) -> int:
    """The DualSense's Bluetooth CRC: zlib's CRC32 over the one-byte
    `seed` (0xA1 input, 0xA2 output, 0xA3 feature) then `data`."""
    return zlib.crc32(bytes([seed]) + bytes(data)) & 0xFFFFFFFF


def bt_crc_ok(report: bytes, seed: int = BT_INPUT_SEED) -> bool:
    """Does a Bluetooth report's trailing CRC32 (little-endian) match?"""
    if len(report) < 5:
        return False
    (want,) = struct.unpack_from("<I", report, len(report) - 4)
    return crc32(seed, report[:-4]) == want


def decode(report, check_crc: bool = True, bluetooth: bool | None = None) -> Frame | None:
    """One input report (the bytes hidapi's `read` returns, report id
    first) as a `Frame`, or None for anything else — another report id,
    a short read, a Bluetooth report whose CRC fails (`check_crc`).
    `bluetooth` True: a report 0x01 is the simple one whatever its length
    (SDL also meets it padded to 78 bytes, spec §2.1)."""
    r = bytes(report)
    if not r:
        return None
    if r[0] == USB_REPORT_ID and len(r) >= USB_IN_LEN and not bluetooth:
        return _full(USB_IN, r[1:])
    if r[0] == BT_REPORT_ID and len(r) >= BT_IN_LEN:
        if check_crc and not bt_crc_ok(r[:BT_IN_LEN]):
            return None
        if (r[1] & 0x0F) not in BT_INPUT_TAGS:
            return None                # a microphone report (tag 2), not input (spec §2.1)
        return _full(BT_IN, r[2:])
    if r[0] == USB_REPORT_ID and BT_SIMPLE_LEN <= len(r) and (bluetooth or len(r) < USB_IN_LEN):
        return _simple(r)
    return None


# ---- the motion sensors' calibration (feature report 0x05) ----

@dataclass(frozen=True)
class Calibration:
    """Per-axis (bias, scale) turning raw sensor counts into deg/s
    (gyro) and g (accel). `nominal` when no feature report was read."""

    gyro: tuple[tuple[float, float], ...] = ((0.0, 1 / GYRO_PER_DEG_S),) * 3
    accel: tuple[tuple[float, float], ...] = ((0.0, 1 / ACCEL_PER_G),) * 3
    nominal: bool = True

    def gyro_dps(self, raw) -> tuple[float, float, float]:
        return tuple((v - b) * s for v, (b, s) in zip(raw, self.gyro, strict=True))

    def accel_g(self, raw) -> tuple[float, float, float]:
        return tuple((v - b) * s for v, (b, s) in zip(raw, self.accel, strict=True))


def calibration(report) -> Calibration:
    """Feature report 0x05 as a `Calibration` (spec §4.1): gyro pitch /
    yaw / roll biases, each axis's plus and minus readings, the speed plus
    and minus, the accel plus and minus, all s16 LE from byte 1. deg/s =
    (raw − bias) × (speed+ + speed−) / (plus − minus), as SDL (Linux leaves
    the bias out — under 1 deg/s); g = (raw − (plus − span // 2)) × 2 /
    span. A report too short, a zero denominator, a bias past `BIAS_MAX` or
    a scale more than `CALIBRATION_SLACK` off nominal — SDL's checks —
    gives the nominal calibration instead."""
    r = bytes(report)
    if len(r) < 35 or r[0] != CALIBRATION_ID:
        return Calibration()
    v = struct.unpack_from("<17h", r, 1)
    bias = v[0:3]
    plus = (v[3], v[5], v[7])
    minus = (v[4], v[6], v[8])
    speed_2x = v[9] + v[10]
    acc_plus = (v[11], v[13], v[15])
    acc_minus = (v[12], v[14], v[16])

    def believable(scale: float, nominal: float) -> bool:
        return abs(scale / nominal - 1.0) <= CALIBRATION_SLACK
    gyro, accel = [], []
    for b, p, m in zip(bias, plus, minus, strict=True):
        den = p - m
        if den == 0 or abs(b) > BIAS_MAX:
            return Calibration()
        scale = speed_2x / den
        if not believable(scale, 1 / GYRO_PER_DEG_S):
            return Calibration()
        gyro.append((float(b), scale))
    for p, m in zip(acc_plus, acc_minus, strict=True):
        span = p - m
        if span == 0:
            return Calibration()
        scale = 2.0 / span
        if not believable(scale, 1 / ACCEL_PER_G):
            return Calibration()
        accel.append((float(p - int(span / 2)), scale))
    return Calibration(tuple(gyro), tuple(accel), nominal=False)


def update_version(report) -> int:
    """Feature report 0x20's update version (u16 LE at byte 44, spec
    §4.3), 0 when the report is not one."""
    r = bytes(report)
    if len(r) < 46 or r[0] != FIRMWARE_ID:
        return 0
    return struct.unpack_from("<H", r, 44)[0]


# ---- output ----

# the five player LEDs (bit 0 the left one) for players 1–5, as Linux lights
# them (hid-playstation.c, dualsense_set_player_leds); 0: none lit
PLAYER_BITS = (0, 0x04, 0x0A, 0x15, 0x1B, 0x1F)


def player_bits(player: int) -> int:
    """The player LEDs that say "player `player`" (0–5)."""
    return PLAYER_BITS[player] if 0 <= player < len(PLAYER_BITS) else 0


@dataclass
class Trigger:
    """One trigger's resistance, as the pad's effect block takes it.
    `mode` "off", "resist" (a uniform pushback from `start` of the travel,
    strength 0–1) or "pulse" (a vibration of `strength` at `freq` Hz
    from `start`). Everything else the firmware can do stays out until
    a hand at the pad has felt it (plan 42 D8)."""

    mode: str = "off"
    start: float = 0.0
    strength: float = 0.0
    freq: float = 0.0


@dataclass
class Effects:
    """What the pad should be showing and doing, all at once — one output
    report. `light` (r, g, b) 0–255, `players` the five player LEDs as a
    bitmask (bit 0 left), `mic` 0 off, 1 on, 2 pulsing; `rumble_low` the
    left, heavy motor, `rumble_high` the right, light one, 0–1;
    `left` / `right` the triggers."""

    light: tuple[int, int, int] = (0, 0, 64)
    brightness: int = 0                  # 0 high, 1 mid, 2 low (the player LEDs)
    players: int = 0
    mic: int = 0
    rumble_low: float = 0.0
    rumble_high: float = 0.0
    left: Trigger = field(default_factory=Trigger)
    right: Trigger = field(default_factory=Trigger)

    def key(self) -> tuple:
        """What a write would change — equal keys, nothing to send."""
        def t(x: Trigger) -> tuple:
            return (x.mode, round(x.start, 3), round(x.strength, 3), round(x.freq, 1))
        return (tuple(self.light), self.brightness, self.players, self.mic,
                round(self.rumble_low, 3), round(self.rumble_high, 3),
                t(self.left), t(self.right))


# the 47-byte effects block (spec §5.2), offsets from its start
C_FLAGS0, C_FLAGS1, C_RUMBLE_HIGH, C_RUMBLE_LOW = 0, 1, 2, 3
C_MIC_LED = 8
C_TRIGGER_RIGHT, C_TRIGGER_LEFT = 10, 21
C_FLAGS2 = 38
C_LIGHT_SETUP, C_BRIGHTNESS, C_PLAYERS, C_RGB = 41, 42, 43, 44
BLOCK_LEN = 47
# flags0: rumble (v1 emulation, haptics select), each trigger's effect
F0_RUMBLE_V1, F0_HAPTICS, F0_RIGHT_TRIGGER, F0_LEFT_TRIGGER = 0x01, 0x02, 0x04, 0x08
# flags1: the mic LED, the light bar's colour, reset the LEDs, the player LEDs
F1_MIC_LED, F1_LIGHT, F1_RESET_LEDS, F1_PLAYERS = 0x01, 0x04, 0x08, 0x10
# flags2: the LED brightness, the light bar setup, rumble v2
F2_BRIGHTNESS, F2_LIGHT_SETUP, F2_RUMBLE_V2 = 0x01, 0x02, 0x04
LIGHT_OUT = 0x02             # the light bar setup that hands the LEDs to the host (Linux)
PLAYERS_INSTANT = 0x20       # player LEDs change at once, not fading
RUMBLE_V2_VERSION = 0x0215   # a DualSense at or past this update takes rumble v2 (Linux)
# the USB output report's length: the descriptor's (DualSense 48, Edge 64 —
# macOS took an Edge's 64 at once, 2026-11-02); `HidPad` falls back through
# the others if a pad refuses one
USB_OUT_LENS = {"dualsense": (48, 64, 63), "edge": (64, 63, 48)}
TRIGGER_ZONES = 10

# trigger effect modes (spec §6): the official ones only — never 0xFC–0xFE
T_OFF, T_FEEDBACK, T_VIBRATION = 0x05, 0x21, 0x26


def trigger_block(t: Trigger) -> bytes:
    """One trigger's 11-byte effect (spec §6, Nielk1's single forms):
    "resist" → Feedback 0x21, zones from `start` to the end at `strength`
    (1–8); "pulse" → Vibration 0x26, the same zones at that amplitude and
    `freq` Hz; anything else, or a strength that rounds to 0, → Off."""
    out = bytearray(11)
    level = round(min(1.0, max(0.0, t.strength)) * 8)
    if t.mode not in ("resist", "pulse") or level == 0:
        out[0] = T_OFF
        return bytes(out)
    pos = min(TRIGGER_ZONES - 1, max(0, round(min(1.0, max(0.0, t.start)) * 9)))
    mask = 0
    forces = 0
    for zone in range(pos, TRIGGER_ZONES):
        mask |= 1 << zone
        forces |= (level - 1) << (3 * zone)
    if t.mode == "pulse":
        freq = round(min(255.0, max(1.0, t.freq or 1.0)))
        out[0] = T_VIBRATION
        struct.pack_into("<HI", out, 1, mask, forces)
        out[9] = freq
        return bytes(out)
    out[0] = T_FEEDBACK
    struct.pack_into("<HI", out, 1, mask, forces)
    return bytes(out)


def effects_block(e: Effects, *, rumble_v2: bool = True, first: bool = False,
                  reset_leds: bool = False) -> bytes:
    """The 47-byte block every output report carries (spec §5.2). `first`
    is the take-over Linux sends once at connect — the light bar's setup
    set to "out", so the host's colours stick — and nothing else;
    `reset_leds` adds SDL's reset (flags1 0x08) to an ordinary block."""
    b = bytearray(BLOCK_LEN)
    if first:
        b[C_FLAGS2] = F2_LIGHT_SETUP
        b[C_LIGHT_SETUP] = LIGHT_OUT
        return bytes(b)
    b[C_FLAGS0] = F0_HAPTICS | F0_RIGHT_TRIGGER | F0_LEFT_TRIGGER | (0 if rumble_v2 else F0_RUMBLE_V1)
    b[C_FLAGS1] = F1_MIC_LED | F1_LIGHT | F1_PLAYERS | (F1_RESET_LEDS if reset_leds else 0)
    b[C_FLAGS2] = F2_BRIGHTNESS | (F2_RUMBLE_V2 if rumble_v2 else 0)
    b[C_RUMBLE_HIGH] = round(min(1.0, max(0.0, e.rumble_high)) * 255)
    b[C_RUMBLE_LOW] = round(min(1.0, max(0.0, e.rumble_low)) * 255)
    b[C_MIC_LED] = min(2, max(0, int(e.mic)))
    b[C_TRIGGER_RIGHT:C_TRIGGER_RIGHT + 11] = trigger_block(e.right)
    b[C_TRIGGER_LEFT:C_TRIGGER_LEFT + 11] = trigger_block(e.left)
    b[C_BRIGHTNESS] = min(2, max(0, int(e.brightness)))
    b[C_PLAYERS] = (int(e.players) & 0x1F) | PLAYERS_INSTANT
    b[C_RGB:C_RGB + 3] = bytes(min(255, max(0, int(c))) for c in e.light)
    return bytes(b)


def output_report(e: Effects, *, bluetooth: bool, seq: int = 0, first: bool = False,
                  rumble_v2: bool = True, usb_len: int = USB_OUT_LEN,
                  reset_leds: bool = False) -> bytes:
    """One output report for `hid.write` (spec §5.1). USB: 0x02, the block,
    zeros to `usb_len`. Bluetooth: 0x31, the sequence in byte 1's high
    nibble, the 0x10 tag, the block, zeros, the CRC32 over 0xA2 + bytes
    0–73 in the last four."""
    block = effects_block(e, rumble_v2=rumble_v2, first=first, reset_leds=reset_leds)
    if not bluetooth:
        r = bytearray(max(usb_len, 1 + BLOCK_LEN))
        r[0] = USB_OUT_ID
        r[1:1 + BLOCK_LEN] = block
        return bytes(r)
    r = bytearray(BT_OUT_LEN)
    r[0] = BT_OUT_ID
    r[1] = (seq & 0x0F) << 4
    r[2] = 0x10
    r[3:3 + BLOCK_LEN] = block
    struct.pack_into("<I", r, BT_OUT_LEN - 4, crc32(BT_OUTPUT_SEED, r[:BT_OUT_LEN - 4]))
    return bytes(r)


# ---- the road's surface (pads/hid.py calls these on every codec; plan 46) ----

def accepts(r: bytes, reader) -> str | None:
    """Is `r` an input report the road keeps — and over which link? A BT
    report (0x31), or a 0x01 that is short or on a Bluetooth bus, is the
    Bluetooth link (its tag noted for the probe); a full 0x01 is USB;
    anything else is dropped."""
    if r[0] == BT_REPORT_ID or (r[0] == USB_REPORT_ID and (
            len(r) < USB_IN_LEN or reader.bt_hint)):
        if r[0] == BT_REPORT_ID and len(r) > 1:
            reader.tags.add(r[1] & 0x0F)
        return "bluetooth"
    if r[0] == USB_REPORT_ID:
        return "usb"
    return None


def decode_frame(raw: bytes, reader) -> Frame | None:
    """`decode` for the reader (or tape) holding this pad."""
    return decode(raw, bluetooth=reader.bt_hint)


def gyro_of(raw: bytes, reader) -> tuple[tuple[int, int, int], ...] | None:
    """The raw gyro samples of one report, oldest first — the reader's
    thread integrates them every report without decoding the rest — or
    None for a report `decode_frame` refuses or that has no sensors (a
    simple report, a microphone report, a bad CRC)."""
    r = raw
    if not r:
        return None
    if r[0] == USB_REPORT_ID and len(r) >= USB_IN_LEN and not reader.bt_hint:
        return (struct.unpack_from("<3h", r, 1 + 15),)
    if r[0] == BT_REPORT_ID and len(r) >= BT_IN_LEN:
        if not bt_crc_ok(r[:BT_IN_LEN]) or (r[1] & 0x0F) not in BT_INPUT_TAGS:
            return None
        return (struct.unpack_from("<3h", r, 2 + 15),)
    return None


SENSOR_TICK_S = 1 / 3e6        # the sensor timestamp's unit, 0.33 µs (Linux hid-playstation)


def report_clock(raw: bytes) -> tuple[int, int, float]:
    """The report's own clock — (count, wrap, seconds a count): the full
    report's sensor timestamp — for a report `gyro_of` took."""
    off = (1 if raw[0] == USB_REPORT_ID else 2) + 27
    return struct.unpack_from("<I", raw, off)[0], 1 << 32, SENSOR_TICK_S


def setup(dev, reader) -> None:
    """Feature 0x05 — the motion calibration, and over Bluetooth the
    switch to the full report — then 0x20, the firmware's update version
    (which rumble mode a DualSense takes). SDL and Linux read both at
    connect (spec §2.4, §4)."""
    got = dev.get_feature_report(CALIBRATION_ID, FEATURE_READ_LEN)
    if got:
        reader.calibration = calibration(bytes(got))
    got = dev.get_feature_report(FIRMWARE_ID, FEATURE_READ_LEN)
    if got:
        reader.update_version = update_version(bytes(got))


def write(dev, reader, want: Effects, now: float) -> bool:
    """What `want` needs sent now: nothing while it equals what was last
    sent (False); else, the first time, Linux's take-over (the light
    bar's setup to "out", so the host's colours stick — spec §5.3, enough
    on macOS over USB and Bluetooth, a real Edge 2026-11-02), then the
    output report, through the reader's `_send` (which learns the USB
    length)."""
    if want.key() == reader._sent_key:
        return False
    if reader._sent_key is None:
        reader._send(dev, output_report(Effects(), bluetooth=reader.bluetooth,
                                        seq=reader._next_seq(), first=True,
                                        usb_len=reader._usb_len()), first=True)
    reader._send(dev, output_report(want, bluetooth=reader.bluetooth, seq=reader._next_seq(),
                                    rumble_v2=reader.rumble_v2, usb_len=reader._usb_len()))
    return True


def calm(dev, reader, want: Effects) -> None:
    """On the way out: rumble stopped and the triggers freed (the light
    keeps its colour), so nothing goes on shaking or pushing back."""
    quiet = Effects(light=want.light, players=want.players, brightness=want.brightness)
    reader._send(dev, output_report(quiet, bluetooth=reader.bluetooth, seq=reader._next_seq(),
                                    rumble_v2=reader.rumble_v2, usb_len=reader._usb_len()))
