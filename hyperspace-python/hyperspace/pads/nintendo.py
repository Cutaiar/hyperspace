"""The Joy-Con (and Pro Controller) report format (plan 43), bytes ↔ values.

Written from the community's reverse engineering (dekuNukem's
``Nintendo_Switch_Reverse_Engineering``: ``bluetooth_hid_notes.md``,
``spi_flash_notes.md``, ``imu_sensor_notes.md``, ``rumble_data_table.md``),
Linux's ``hid-nintendo.c`` and SDL's ``SDL_hidapi_switch.c`` — and checked
against a real Joy-Con (L) over Bluetooth on macOS (2026-11-02): silent
until asked, then report 0x30 at about 62 a second, the sensors on once
subcommand 0x40 says so. Where only hardware can say, the constant is
named and the probe (``tools/hid_probe.py``) settles it.

**Input** (`decode`). Over Bluetooth a Joy-Con sends nothing until the
host sets its input mode; `setup` asks for 0x30, the standard full
report (49 bytes: a timer, the battery, three button bytes, both sticks
as packed 12-bit pairs, and three six-axis samples 5 ms apart). A 0x21
is a subcommand's reply (the same buttons and sticks, then the answer:
`setup` reads the calibration out of the SPI flash through it); a 0x3F
is the simple report a Joy-Con sends before the mode is set — face
buttons only. Every control lands in the pad's vocabulary
(models.CANON) **by position for one Joy-Con held like a Wii Remote**:
its one stick is the left stick, the (L)'s arrows are the face (↓ is
``A``, → ``B``, ← ``X``, ↑ ``Y``), SL / SR are the back pair ``LP`` /
``RP``, L / ZL (or R / ZR) are ``LB`` + ``axis:LT`` (``RB`` + ``RT``),
− / + / capture / HOME are ``VIEW`` / ``MENU`` / ``SHARE`` / ``GUIDE``.
The Pro Controller is the whole face: its D-pad is the hat.

**Calibration** (`Calibration`). The stick's centre and its reach each
way come from the flash (the factory's, or the user's where the Switch
wrote one — the drift fix a Joy-Con most needs); the sensors' origin and
sensitivity likewise. `recentre` then takes the stick's resting reading
at connect as its centre when it is near enough to be at rest, so a
drifted stick reads 0 in the hand that holds it still.

**Output** (`output_reports`). Rumble as the Joy-Con's HD rumble (a low
band and a high band, each a frequency and an amplitude, four bytes a
side) and the four player lights, from the same `sony.Effects` every
pad's sink rows make (`devices.pad_effects`): its light bar, trigger and
mic channels mean nothing here and are left out. The pad keeps rumbling
only while the host keeps saying so (`RUMBLE_REFRESH_S`, as Linux).

A leaf: the standard library, models.py, gesture.py and sony.py's
`Frame` / `Touch` / `Effects` (the one vocabulary) only.
"""

from __future__ import annotations

import math
import struct
import time
from dataclasses import dataclass

from .gesture import AxisMap
from .models import CANON, N_CANON
from .sony import BT_IN, BT_SIMPLE, Effects, Frame

IN_LEN = 64                   # a read's room: 0x30 and 0x21 are 49 bytes
REPORT_FULL = 0x30            # the standard full report, ~60 a second
REPORT_REPLY = 0x21           # a subcommand's reply (buttons and sticks, no sensors)
REPORT_SIMPLE = 0x3F          # before the mode is set: buttons only
REPORT_LEN = 49
OUT_ID = 0x01                 # rumble + a subcommand
RUMBLE_ID = 0x10              # rumble alone
# subcommands (bluetooth_hid_notes.md)
SUB_INFO, SUB_MODE, SUB_SPI_READ, SUB_LEDS = 0x02, 0x03, 0x10, 0x30
SUB_IMU, SUB_IMU_SENS, SUB_VIBRATION = 0x40, 0x41, 0x48
FULL_MODE = 0x30
SPI_ACK = 0x90
SPI_MAX = 0x1D
REPLY_TIMEOUT_S = 0.6         # how long `setup` waits for one SPI answer
SETUP_TRIES = 2
RUMBLE_REFRESH_S = 0.05       # resend rumble this often while it is on (hid-nintendo's period)
RUMBLE_NEUTRAL = bytes((0x00, 0x01, 0x40, 0x40))     # 320 Hz and 160 Hz at nothing
RUMBLE_LOW_HZ, RUMBLE_HIGH_HZ = 160.0, 320.0         # the two bands the sinks drive
RUMBLE_AMP_MAX = 1.0
HIGH_BAND_MIN_HZ = 80.0       # the high band's lowest code (0x60)
ACK = 0x80                    # a 0x21 reply's ack byte has this bit set

# ---- the SPI flash (spi_flash_notes.md) ----
SPI_STICK_L_FACTORY, SPI_STICK_R_FACTORY = 0x603D, 0x6046     # 9 bytes each
SPI_STICK_L_USER, SPI_STICK_R_USER = 0x8010, 0x801B           # 2 magic bytes + 9
SPI_IMU_FACTORY, SPI_IMU_USER = 0x6020, 0x8026                # 24; 2 magic + 24
USER_MAGIC = b"\xb2\xa1"
# a stick's nominal 12-bit centre and reach when no calibration was read
STICK_CENTRE, STICK_REACH = 2048, 1400
# the sensors' nominal scales (±8 g, ±2000 deg/s): counts per g and per deg/s
ACCEL_PER_G = 4096.0
GYRO_PER_DEG_S = 13371.0 / 936.0
CALIBRATION_SLACK = 0.5       # a scale more than this far off nominal is not believed
RECENTRE_MAX = 0.3            # a stick resting this far from centre (±1) is taken as its centre
RECENTRE_SPREAD = 0.1         # …if it moved less than this meanwhile (else a hand is on it)

# the sensors' axes as the chip reports them (imu_sensor_notes.md): x along
# the long axis toward the shoulder (L / ZL, R / ZR) end, y across it, z up
# out of the face. Held like a Wii Remote the shoulder end points away, so
# the pad's x (right) is −y, its y (up out of the face) z, its z (toward the
# player) −x — **checked on a Joy-Con (L)** (the probe's tilt step,
# 2026-11-02: the proposed map equalled this one). The (R)'s chip sits the
# other way up on its board: Linux's hid-nintendo negates its y and z, so its
# map is the (L)'s with those two signs flipped — **unverified**, no (R) in
# hand. The Pro Controller's axes are the (L)'s (no flip in Linux or SDL) —
# **unverified**. `axis_map_for(kind)`; the probe's tilt step says.
_L_MAP = AxisMap(accel=((1, -1.0), (2, 1.0), (0, -1.0)), gyro=((1, -1.0), (2, 1.0), (0, -1.0)))
_R_MAP = AxisMap(accel=((1, 1.0), (2, -1.0), (0, -1.0)), gyro=((1, 1.0), (2, -1.0), (0, -1.0)))
AXIS_MAPS = {"l": _L_MAP, "r": _R_MAP, "pro": _L_MAP}
AXIS_MAP = _L_MAP             # the one hand-checked map (the tests, the probe)
VERIFIED_MAPS = frozenset({"l"})


def axis_map_for(kind: str) -> AxisMap:
    """The sensors' axes for a kind of pad ("l", "r", "pro")."""
    return AXIS_MAPS.get(kind, _L_MAP)

# (report byte, bit) → canonical button, per kind of pad. Byte 3 is the
# right half, 4 the middle, 5 the left half (bluetooth_hid_notes.md §0x30)
_L_BUTTONS = (
    (5, 0x01, "A"), (5, 0x02, "Y"), (5, 0x04, "B"), (5, 0x08, "X"),      # ↓ ↑ → ←
    (5, 0x10, "RP"), (5, 0x20, "LP"), (5, 0x40, "LB"),                   # SR SL L
    (4, 0x01, "VIEW"), (4, 0x20, "SHARE"), (4, 0x08, "LSTICK"),          # − capture L3
)
_R_BUTTONS = (
    (3, 0x01, "Y"), (3, 0x02, "X"), (3, 0x04, "B"), (3, 0x08, "A"),
    (3, 0x10, "RP"), (3, 0x20, "LP"), (3, 0x40, "RB"),                   # SR SL R
    (4, 0x02, "MENU"), (4, 0x10, "GUIDE"), (4, 0x04, "LSTICK"),          # + HOME R3 (the one stick)
)
_PRO_BUTTONS = (
    (3, 0x01, "Y"), (3, 0x02, "X"), (3, 0x04, "B"), (3, 0x08, "A"), (3, 0x40, "RB"),
    (5, 0x40, "LB"),
    (4, 0x01, "VIEW"), (4, 0x02, "MENU"), (4, 0x04, "RSTICK"), (4, 0x08, "LSTICK"),
    (4, 0x10, "GUIDE"), (4, 0x20, "SHARE"),
)
# the digital triggers: (byte, bit) → axis index (LT 4, RT 5)
_L_TRIGGER, _R_TRIGGER = ((5, 0x80, 4),), ((3, 0x80, 5),)
_PRO_TRIGGERS = ((5, 0x80, 4), (3, 0x80, 5))
# the Pro's D-pad: (bit of byte 5) → GLFW's hat bits (up 1, right 2, down 4, left 8)
_PRO_HAT = ((0x02, 1), (0x04, 2), (0x01, 4), (0x08, 8))
# the simple report's byte 1 (before the mode is set): the (L)'s arrows /
# the (R)'s face, SL, SR; byte 2: − / +, the stick's click, HOME, capture
_SIMPLE_L = ((1, 0x01, "X"), (1, 0x02, "A"), (1, 0x04, "Y"), (1, 0x08, "B"),
             (1, 0x10, "LP"), (1, 0x20, "RP"), (2, 0x01, "VIEW"), (2, 0x04, "LSTICK"),
             (2, 0x20, "SHARE"), (2, 0x40, "LB"))
_SIMPLE_R = ((1, 0x01, "A"), (1, 0x02, "X"), (1, 0x04, "B"), (1, 0x08, "Y"),
             (1, 0x10, "LP"), (1, 0x20, "RP"), (2, 0x01, "MENU"), (2, 0x04, "LSTICK"),
             (2, 0x10, "GUIDE"), (2, 0x40, "RB"))


def kind_of(model_id: str) -> str:
    """"l", "r" or "pro" for a Nintendo model id."""
    if model_id == "joycon-r":
        return "r"
    if model_id == "procon":
        return "pro"
    return "l"


# per kind of pad: its button table, its digital triggers, which raw stick
# reads as the left stick (0 the left one, 1 the right), whether the right
# stick reads too, whether byte 5's D-pad bits are the hat, the simple
# report's table
_KINDS = {
    "l": (_L_BUTTONS, _L_TRIGGER, 0, False, False, _SIMPLE_L),
    "r": (_R_BUTTONS, _R_TRIGGER, 1, False, False, _SIMPLE_R),      # its one stick is the left stick
    "pro": (_PRO_BUTTONS, _PRO_TRIGGERS, 0, True, True, _SIMPLE_L),
}


def _pair(b: bytes) -> tuple[int, int]:
    """Two 12-bit values packed in three bytes (a stick, a calibration pair)."""
    return b[0] | ((b[1] & 0x0F) << 8), (b[1] >> 4) | (b[2] << 4)


# ---- calibration ----

@dataclass(frozen=True)
class StickCal:
    """One stick's centre and its reach each way, in raw 12-bit counts."""

    cx: int = STICK_CENTRE
    cy: int = STICK_CENTRE
    x_above: int = STICK_REACH
    x_below: int = STICK_REACH
    y_above: int = STICK_REACH
    y_below: int = STICK_REACH

    def norm(self, raw_x: int, raw_y: int) -> tuple[float, float]:
        """(x, y) in ±1: right and up positive, as the chip's axes run."""
        def one(v: int, c: int, above: int, below: int) -> float:
            d = v - c
            reach = above if d >= 0 else below
            if reach <= 0:
                return 0.0
            return max(-1.0, min(1.0, d / reach))
        return one(raw_x, self.cx, self.x_above, self.x_below), one(
            raw_y, self.cy, self.y_above, self.y_below)


@dataclass(frozen=True)
class Calibration:
    """What the flash said: each stick (`left`, `right`), the sensors'
    per-axis (origin, scale) into g and deg/s. `nominal` when nothing was
    read (a tape, a pad that would not answer)."""

    left: StickCal = StickCal()
    right: StickCal = StickCal()
    gyro: tuple[tuple[float, float], ...] = ((0.0, 1 / GYRO_PER_DEG_S),) * 3
    accel: tuple[tuple[float, float], ...] = ((0.0, 1 / ACCEL_PER_G),) * 3
    nominal: bool = True
    user_stick: bool = False       # a stick calibration the Switch wrote was used

    def gyro_dps(self, raw) -> tuple[float, float, float]:
        return tuple((v - b) * s for v, (b, s) in zip(raw, self.gyro, strict=True))

    def accel_g(self, raw) -> tuple[float, float, float]:
        return tuple((v - b) * s for v, (b, s) in zip(raw, self.accel, strict=True))


def stick_cal(data: bytes, side: str) -> StickCal | None:
    """Nine calibration bytes as a `StickCal`: the left stick's are
    [x, y above the centre] [centre] [below]; the right's [centre]
    [below] [above] (spi_flash_notes.md). None for a blank or short
    record."""
    d = bytes(data)
    if len(d) < 9 or d[:9] in (b"\xff" * 9, b"\x00" * 9):
        return None
    a, b, c = _pair(d[0:3]), _pair(d[3:6]), _pair(d[6:9])
    if side == "l":
        (xa, ya), (cx, cy), (xb, yb) = a, b, c
    else:
        (cx, cy), (xb, yb), (xa, ya) = a, b, c
    if min(xa, ya, xb, yb) <= 0:
        return None
    return StickCal(cx, cy, xa, xb, ya, yb)


def imu_cal(data: bytes) -> tuple[tuple, tuple] | None:
    """24 calibration bytes — the accel's origin and sensitivity, the gyro's
    origin and sensitivity, each three s16 LE — as (gyro, accel) per-axis
    (origin, scale): g = (raw − origin) × 4 / (sens − origin), deg/s =
    (raw − origin) × 936 / (sens − origin) (imu_sensor_notes.md). None
    when blank, short, or a scale too far off nominal to believe."""
    d = bytes(data)
    if len(d) < 24 or d[:24] in (b"\xff" * 24, b"\x00" * 24):
        return None
    v = struct.unpack_from("<12h", d, 0)
    acc_origin, acc_sens, gyro_origin, gyro_sens = v[0:3], v[3:6], v[6:9], v[9:12]

    def believable(scale: float, nominal: float) -> bool:
        return abs(scale / nominal - 1.0) <= CALIBRATION_SLACK
    accel, gyro = [], []
    for o, s in zip(acc_origin, acc_sens, strict=True):
        den = s - o
        if den == 0 or not believable(4.0 / den, 1 / ACCEL_PER_G):
            return None
        accel.append((float(o), 4.0 / den))
    for o, s in zip(gyro_origin, gyro_sens, strict=True):
        den = s - o
        if den == 0 or not believable(936.0 / den, 1 / GYRO_PER_DEG_S):
            return None
        gyro.append((float(o), 936.0 / den))
    return tuple(gyro), tuple(accel)


def calibration(records: dict[int, bytes], kind: str) -> Calibration:
    """A `Calibration` from the flash records `setup` read (address →
    bytes): the user's stick record where its magic is there, else the
    factory's; the user's sensor record likewise."""
    def user(addr: int, n: int) -> bytes | None:
        d = records.get(addr)
        if d is not None and len(d) >= 2 + n and d[:2] == USER_MAGIC:
            return d[2:2 + n]
        return None
    left, right, used_user = StickCal(), StickCal(), False
    nominal = True
    for side, fac, usr in (("l", SPI_STICK_L_FACTORY, SPI_STICK_L_USER),
                           ("r", SPI_STICK_R_FACTORY, SPI_STICK_R_USER)):
        if kind != "pro" and side != kind:
            continue
        got = None
        u = user(usr, 9)
        if u is not None:
            got = stick_cal(u, side)
            used_user = used_user or got is not None
        if got is None and records.get(fac) is not None:
            got = stick_cal(records[fac], side)
        if got is not None:
            nominal = False
            if side == "l":
                left = got
            else:
                right = got
    gyro, accel = Calibration().gyro, Calibration().accel
    sensors = None
    u = user(SPI_IMU_USER, 24)
    if u is not None:
        sensors = imu_cal(u)
    if sensors is None and records.get(SPI_IMU_FACTORY) is not None:
        sensors = imu_cal(records[SPI_IMU_FACTORY])
    if sensors is not None:
        gyro, accel = sensors
        nominal = False
    return Calibration(left, right, gyro, accel, nominal=nominal, user_stick=used_user)


def recentre(cal: Calibration, kind: str, rest: list[tuple[int, int]]) -> Calibration:
    """The stick's own resting reading taken as its centre — the drift a
    Joy-Con is known for, read off the pad in the hand that holds it
    still. `rest` is raw (x, y) pairs from the first reports: when they
    all sit within `RECENTRE_MAX` of the calibrated centre and spread
    less than `RECENTRE_SPREAD` (nobody is on the stick), the mean
    becomes the centre; else the calibration stands."""
    if not rest:
        return cal
    stick = cal.right if kind == "r" else cal.left
    xs = [stick.norm(x, y) for x, y in rest]
    if (max(abs(v) for p in xs for v in p) > RECENTRE_MAX
            or max(max(p[i] for p in xs) - min(p[i] for p in xs) for i in (0, 1)) > RECENTRE_SPREAD):
        return cal
    cx = round(sum(x for x, _ in rest) / len(rest))
    cy = round(sum(y for _, y in rest) / len(rest))
    moved = StickCal(cx, cy, stick.x_above, stick.x_below, stick.y_above, stick.y_below)
    if kind == "r":
        return Calibration(cal.left, moved, cal.gyro, cal.accel, cal.nominal, cal.user_stick)
    return Calibration(moved, cal.right, cal.gyro, cal.accel, cal.nominal, cal.user_stick)


# ---- input ----

def _battery(status: int) -> tuple[int, int]:
    """Byte 2's high nibble: 8 full, 6 medium, 4 low, 2 critical, 0 empty,
    bit 0 charging — as (0–10, charging 0 / 1)."""
    level = (status >> 4) & 0x0E
    return min(10, round(level / 8 * 10)), (status >> 4) & 0x01


def _buttons(r: bytes, table) -> list[int]:
    out = [0] * N_CANON
    for byte, bit, name in table:
        if r[byte] & bit:
            out[CANON[name]] = 1
    return out


def raw_sticks(r: bytes) -> tuple[tuple[int, int], tuple[int, int]]:
    """Both sticks' raw 12-bit (x, y) from a 0x30 / 0x21 report."""
    return _pair(r[6:9]), _pair(r[9:12])


def decode(report, kind: str = "l", calibration: Calibration | None = None,
           bluetooth: bool | None = None) -> Frame | None:
    """One input report (as hidapi's `read` returns it, id first) as a
    `Frame` in the pad's vocabulary, or None for anything else — a
    subcommand's reply, a short read. `kind` is which pad (`kind_of`);
    `calibration` turns the sticks' counts into ±1 (nominal without)."""
    r = bytes(report)
    if not r:
        return None
    cal = calibration or Calibration()
    table, triggers, left_is, both, has_hat, simple = _KINDS.get(kind, _KINDS["l"])
    if r[0] == REPORT_FULL and len(r) >= REPORT_LEN:
        buttons = _buttons(r, table)
        axes = [0.0, 0.0, 0.0, 0.0, -1.0, -1.0]
        for byte, bit, i in triggers:
            if r[byte] & bit:
                axes[i] = 1.0
        sticks = raw_sticks(r)
        cals = (cal.left, cal.right)
        x, y = cals[left_is].norm(*sticks[left_is])
        axes[0], axes[1] = x, -y                              # GLFW's up is −
        if both:
            x, y = cal.right.norm(*sticks[1])
            axes[2], axes[3] = x, -y
        hat = 0
        if has_hat:
            for bit, h in _PRO_HAT:
                if r[5] & bit:
                    hat |= h
        # the newest of the three samples (the last; 5 ms apart)
        ax, ay, az, gx, gy, gz = struct.unpack_from("<6h", r, 13 + 24)
        battery, charging = _battery(r[2])
        return Frame(kind=BT_IN, buttons=buttons, hat=hat, axes=axes,
                     gyro=(gx, gy, gz), accel=(ax, ay, az), sensor_time=0, seq=r[1],
                     battery=battery, charging=charging, raw_buttons=bytes(r[3:6]),
                     raw_sticks=sticks)
    if r[0] == REPORT_SIMPLE and len(r) >= 4:
        return Frame(kind=BT_SIMPLE, buttons=_buttons(r, simple), hat=0,
                     axes=[0.0, 0.0, 0.0, 0.0, -1.0, -1.0],
                     battery=-1, charging=-1, raw_buttons=bytes(r[1:3]))
    return None


def imu_samples(report) -> list[tuple[tuple[int, int, int], tuple[int, int, int]]]:
    """All three (accel, gyro) raw samples of a 0x30 report, oldest first
    — for the probe and the tests; the app reads the newest."""
    r = bytes(report)
    if len(r) < REPORT_LEN or r[0] != REPORT_FULL:
        return []
    out = []
    for k in range(3):
        ax, ay, az, gx, gy, gz = struct.unpack_from("<6h", r, 13 + 12 * k)
        out.append(((ax, ay, az), (gx, gy, gz)))
    return out


# ---- output ----

def _amp_code(amp: float) -> int:
    """An amplitude 0–1 as the rumble's encoded amplitude 0–100
    (rumble_data_table.md: the high band's byte is twice this, the low
    band's word this halved over 0x40)."""
    a = max(0.0, min(RUMBLE_AMP_MAX, float(amp)))
    if a <= 0.0:
        return 0
    if a > 0.23:
        return min(100, round(math.log2(a * 8.7) * 32))
    if a > 0.12:
        return round(math.log2(a * 17) * 16)
    return max(1, round(a / 0.12 * 16))


def _freq_code(hz: float) -> int:
    """A frequency as the rumble's encoded frequency (40.875–1252.5 Hz)."""
    f = max(40.875, min(1252.5, float(hz)))
    return round(math.log2(f / 10.0) * 32)


def rumble_bytes(high_amp: float, low_amp: float, high_hz: float = RUMBLE_HIGH_HZ,
                 low_hz: float = RUMBLE_LOW_HZ) -> bytes:
    """One side's four HD-rumble bytes: the high band's frequency and
    amplitude in the first two, the low band's in the last two
    (rumble_data_table.md). Both amplitudes 0 is `RUMBLE_NEUTRAL`. The
    high band's code starts at 0x60 (80 Hz): a lower `high_hz` is held
    there, so the amplitude byte is never corrupted by a negative code."""
    hf = max(0, _freq_code(max(HIGH_BAND_MIN_HZ, high_hz)) - 0x60) * 4
    hf_amp = _amp_code(high_amp) * 2
    lf = _freq_code(low_hz) - 0x40
    lf_amp = _amp_code(low_amp) // 2 + 0x40
    return bytes(((hf & 0xFF), (hf_amp + (hf >> 8)) & 0xFF,
                  (lf + (lf_amp >> 8)) & 0xFF, lf_amp & 0xFF))


def player_leds(players: int) -> int:
    """The Joy-Con's four lights from the pad vocabulary's five-light mask
    (`sony.player_bits`, a meter's ``(1 << n) − 1``): as many lit from
    the left as the mask has bits, up to four."""
    n = min(4, (int(players) & 0x1F).bit_count())
    return (1 << n) - 1


def subcommand(seq: int, cmd: int, args: bytes = b"", rumble: bytes | None = None) -> bytes:
    """Output report 0x01: the packet counter (0–15), eight rumble bytes
    (neutral unless given), the subcommand and its arguments."""
    r = rumble if rumble is not None else RUMBLE_NEUTRAL * 2
    return bytes([OUT_ID, seq & 0x0F]) + bytes(r[:8]).ljust(8, b"\x00") + bytes([cmd]) + bytes(args)


def rumble_report(seq: int, left: bytes, right: bytes) -> bytes:
    """Output report 0x10: rumble alone, both sides."""
    return bytes([RUMBLE_ID, seq & 0x0F]) + bytes(left[:4]) + bytes(right[:4])


def spi_read_args(addr: int, n: int) -> bytes:
    return struct.pack("<IB", addr, n)


def spi_reply(report, addr: int, n: int) -> bytes | None:
    """The data of a 0x21 reply to the SPI read of `addr` / `n`, or None
    when `report` is not that reply (another report, another address)."""
    r = bytes(report)
    if len(r) < 20 + n or r[0] != REPORT_REPLY or r[14] != SUB_SPI_READ:
        return None
    if r[13] != SPI_ACK or struct.unpack_from("<IB", r, 15) != (addr, n):
        return None
    return r[20:20 + n]


def rumbling(e: Effects) -> bool:
    return _amp_code(e.rumble_high) > 0 or _amp_code(e.rumble_low) > 0


# ---- the road's surface (pads/hid.py calls these on every codec) ----

def accepts(r: bytes, reader) -> str | None:
    """Is `r` an input report the road keeps — and over which link? A
    Joy-Con's full report, a subcommand's reply (kept, so the pad never
    reads stale while the flash answers), the simple one; Bluetooth unless
    hidapi said USB."""
    if r[0] not in (REPORT_FULL, REPORT_REPLY, REPORT_SIMPLE):
        return None
    return "usb" if reader.bt_hint is False else "bluetooth"


def decode_frame(raw: bytes, reader) -> Frame | None:
    """`decode` for the reader (or tape) holding this pad."""
    return decode(raw, reader.kind, reader.calibration)


def write(dev, reader, want: Effects, now: float) -> bool:
    """What `want` needs sent now, or nothing (False). Rumble rides the
    reply-free 0x10 report — on change, and again every
    `RUMBLE_REFRESH_S` while it is on, since a Joy-Con stops otherwise (as
    Linux); the player lights are a 0x30 subcommand (which the pad answers
    with a 0x21) only when they change. The light bar, the triggers and
    the mic have no Joy-Con meaning."""
    key = want.key()
    refresh = rumbling(want) and now - reader._sent_t >= RUMBLE_REFRESH_S
    if key == reader._sent_key and not refresh:
        return False
    side = rumble_bytes(want.rumble_high, want.rumble_low)
    dev.write(rumble_report(reader._next_seq(), side, side))
    leds = player_leds(want.players) & 0x0F
    if leds != reader.__dict__.get("_sent_leds"):
        dev.write(subcommand(reader._next_seq(), SUB_LEDS, bytes([leds]), side + side))
        reader._sent_leds = leds
    return True


def calm(dev, reader, want: Effects) -> None:
    """On the way out: the rumble stopped (the lights stay as they are —
    no subcommand, no reply)."""
    dev.write(rumble_report(reader._next_seq(), RUMBLE_NEUTRAL, RUMBLE_NEUTRAL))


def output_reports(e: Effects, next_seq, kind: str = "l") -> list[bytes]:
    """`Effects` as the reports a first send makes: the rumble (0x10) and
    the player lights (a 0x30 subcommand, its packet carrying the rumble
    too) — for a test or a tool; `write` is what the road sends."""
    side = rumble_bytes(e.rumble_high, e.rumble_low)
    return [rumble_report(next_seq(), side, side),
            subcommand(next_seq(), SUB_LEDS, bytes([player_leds(e.players) & 0x0F]), side + side)]


# ---- the connect sequence ----

SPI_READS = {
    "l": ((SPI_STICK_L_FACTORY, 9), (SPI_STICK_L_USER, 11)),
    "r": ((SPI_STICK_R_FACTORY, 9), (SPI_STICK_R_USER, 11)),
    "pro": ((SPI_STICK_L_FACTORY, 9), (SPI_STICK_L_USER, 11),
            (SPI_STICK_R_FACTORY, 9), (SPI_STICK_R_USER, 11)),
}
SPI_IMU_READS = ((SPI_IMU_FACTORY, 24), (SPI_IMU_USER, 26))
REST_REPORTS = 30            # reports the stick is watched at connect for `recentre`


def acked(report, cmd: int) -> bool:
    """Is `report` the pad's 0x21 reply acknowledging subcommand `cmd`?"""
    r = bytes(report)
    return len(r) >= 15 and r[0] == REPORT_REPLY and r[14] == cmd and bool(r[13] & ACK)


# the subcommands `setup` sends first, each waited for and retried
SETUP_SUBCOMMANDS = ((SUB_MODE, bytes([FULL_MODE]), "full report mode"),
                     (SUB_IMU, bytes([0x01]), "sensors on"),
                     (SUB_VIBRATION, bytes([0x01]), "rumble on"))


def setup(dev, reader, clock=time.monotonic) -> None:
    """What a Joy-Con needs before it is a pad: the full report mode, the
    sensors and rumble switched on — each waited for (its 0x21 ack) and
    sent again up to `SETUP_TRIES` times — the calibration read from the
    flash, and the stick's rest taken (`recentre`). `reader` is the
    `HidPad`: its `_take` keeps every input report seen meanwhile (none
    is lost), its `_next_seq` the packet counter, its `calibration` and
    `note` the results; what never acked is said in the note (a pad
    still in the simple report reads buttons only). Runs on the reader's
    thread."""
    kind = kind_of(reader.model.id)

    def send(cmd: int, args: bytes = b"") -> None:
        dev.write(subcommand(reader._next_seq(), cmd, args))

    def read_until(want, timeout: float):
        """Reports until `want(report)` answers, each handed to `_take`."""
        end = clock() + timeout
        while clock() < end:
            data = dev.read(IN_LEN, 50)
            if not data:
                continue
            r = bytes(data)
            reader._take(r)
            got = want(r)
            if got is not None and got is not False:
                return got
        return None

    def ask(cmd: int, args: bytes, want) -> object:
        """Send `cmd`, wait for what `want` recognises; `SETUP_TRIES` times."""
        for _ in range(SETUP_TRIES):
            send(cmd, args)
            got = read_until(want, REPLY_TIMEOUT_S)
            if got is not None:
                return got
        return None
    unacked = []
    for cmd, args, word in SETUP_SUBCOMMANDS:
        if ask(cmd, args, lambda r, c=cmd: acked(r, c) or None) is None:
            unacked.append(word)
    records: dict[int, bytes] = {}
    for addr, n in SPI_READS[kind] + SPI_IMU_READS:
        got = ask(SUB_SPI_READ, spi_read_args(addr, n), lambda r, a=addr, k=n: spi_reply(r, a, k))
        if got is not None:
            records[addr] = got
    reader.flash = records
    cal = calibration(records, kind)
    notes = []
    if unacked:
        notes.append("never acknowledged: " + ", ".join(unacked))
    if not records:
        notes.append("no answer from the flash: nominal calibration")
    reader.note = "; ".join(notes)
    # the stick at rest: the first reports' raw readings
    rest: list[tuple[int, int]] = []

    def stick(r: bytes):
        if r[0] == REPORT_FULL and len(r) >= REPORT_LEN:
            left, right = raw_sticks(r)
            rest.append(right if kind == "r" else left)
            return r if len(rest) >= REST_REPORTS else None
        return None
    read_until(stick, 1.0)
    reader.calibration = recentre(cal, kind, rest)
    reader.recentred = reader.calibration is not cal
