"""Akai APC40 (mk1) device profile — port name, power-up, LED rules, default map.

Numbers follow Akai's "APC40 Communications Protocol" (rev 1). Channels
are 0-based here; the eight track strips are channels 0–7.

Mode: on open the device is put in Alternate Ableton Live mode (0x42):
every button is momentary, no local banking, and every LED — button
colours and the knob rings — is host-controlled, which is what feedback
needs. On close it is returned to generic mode so it behaves as a plain
controller for the next program.

Controls (in):
  CC  0x10–0x17  device knobs 1–8 (channel = selected track in mode 0x41,
                 channel 0 in 0x42 — the map matches any channel)
  CC  0x30–0x37  track knobs 1–8            CC 0x07  track fader, ch = track
  CC  0x0E       master fader               CC 0x0F  crossfader
  CC  0x2F       cue level — relative, two's complement
  note 0x30–0x34 rec-arm · solo · activator · track select · clip stop, ch = track
  note 0x35–0x39 clip launch rows 1–5, ch = track
  note 0x51      stop all clips              note 0x52–0x56  scene launch 1–5
  note 0x5B–0x5D play · stop · rec           note 0x5E–0x61  up · down · right · left
  note 0x63–0x65 tap tempo · nudge + · nudge −
  note 0x3A–0x41 clip/track · device on/off · ← · → · detail · quant · overdub · metronome
  note 0x57–0x5A pan · send A · B · C        note 0x62  shift

LEDs (out): note velocity on the button's own note. Clip-launch grid:
0 off · 1 green · 2 green blink · 3 red · 4 red blink · 5 yellow · 6 yellow
blink. Every other button: 0 off · 1 on · 2 blink (`blink_of` turns a
row's "on" velocity into its blink; `filled_of` gives a clip pad's third
state — yellow, "something is here, not selected": a bank pad whose slot
holds a preset that is not the loaded one). Knob rings: the knob's
own CC carries the value; CC number + 8 sets the ring style
(0 off · 1 single · 2 volume · 3 pan).

The default map's transport corner is the clock (plan 09): TAP TEMPO taps
``tempo.tap``, NUDGE +/− step ``tempo.nudge`` by a hundredth of a beat,
METRONOME fires ``lfo.trigger`` — the global LFO trigger — and QUANT steps
the preset bank. METRONOME's LED blinks on the beat through the ordinary ``led``
feedback: one row, no second binding on the note. A trigger's LED is its
press echo unless the param carries a light of its own
(``Registry.trigger(lit=)``), and ``lfo.trigger`` is declared with the
clock's ``on_beat`` — so midi.py's `_lit` reads the beat off the param
and the row stays a plain trigger row that Learn can move like any other.

Two layers under a latched SHIFT (plan 13 §3). Every MIDI row carries a
``layer``: none is **invariant** (the session defines the control; one
meaning on both layers — the MASTER fader, the crossfader as the master dim,
the bank's twenty-four pads — clip row 1 and, since plan 19, clip rows 4
and 5 (`BANK_PADS`), each a tap to load and, on an empty slot, a hold to
save into it — SHIFT, the clock and transport corner, OVERDUB as home, the track buttons,
and since plan 24 C1 the render toggles on scene launch 1–4 and SAVE on
track 8's clip stop, which held turns a pad's tap into a save into its
slot), ``"global"`` is the
SHIFT layer
(the band strip on the device knobs, the hand feel and BPM on track knobs
1–5, the band scenes on clip rows 2–3, and since plan 24 C2 the bands'
post-drive, the master dynamics and trim on the track faders),
``"preset"`` is the loaded preset's own (the factory default below is
what a fresh preset starts with; since plan 24 C2 the track faders are a
preset's too, and the default gives them nothing). A control with no row
on the layer that is up is dark and does nothing; midi.py dispatches and draws by those rules.

The sequencer page (plan 31 §A, seq_page.py) is not a layer: while SEND A
(invariant) has it up, its rows shadow clip rows 1–5, the clip stops and
scene launch 1–5 on both layers, invariant rows included; the rest of the
desk is as it was. Its lights are `SHADE`'s.

The device and track knobs are endless encoders whose position the host
sets with the same CC that draws the ring (`RING_REBASES_KNOB`), so a
knob continues from its ring after a layer switch or a load and needs no
pickup; the faders are real pots and keep soft pickup.
"""

from __future__ import annotations

from dataclasses import dataclass

import mido

PORT_MATCH = "APC40"

DEVICE_KNOBS = range(0x10, 0x18)
TRACK_KNOBS = range(0x30, 0x38)
CC_FADER, CC_MASTER, CC_XFADE, CC_CUE = 0x07, 0x0E, 0x0F, 0x2F

# The protocol table: every note, ring mode and LED velocity the APC40 mk1
# speaks, whether or not DEFAULT_MAP below uses it (N_DEV_L/R, N_SEND_B/C,
# RING_SINGLE / RING_PAN and the red and yellow blinks by name are unused
# today and kept as the reference for a hand-edited bindings.json or a
# later map; a blink is sent through `blink_of`).
N_ARM, N_SOLO, N_ACTIVATOR, N_SELECT, N_CLIPSTOP = 0x30, 0x31, 0x32, 0x33, 0x34
N_CLIP = [0x35, 0x36, 0x37, 0x38, 0x39]          # rows 1–5
N_CLIPTRACK, N_DEVICE_ON, N_DEV_L, N_DEV_R = 0x3A, 0x3B, 0x3C, 0x3D
N_DETAIL, N_QUANT, N_OVERDUB, N_METRO = 0x3E, 0x3F, 0x40, 0x41
N_MASTER_SEL, N_STOP_ALL = 0x50, 0x51
N_SCENE = [0x52, 0x53, 0x54, 0x55, 0x56]
N_PAN, N_SEND_A, N_SEND_B, N_SEND_C = 0x57, 0x58, 0x59, 0x5A
N_PLAY, N_STOP, N_REC = 0x5B, 0x5C, 0x5D
N_UP, N_DOWN, N_RIGHT, N_LEFT = 0x5E, 0x5F, 0x60, 0x61
N_SHIFT, N_TAP, N_NUDGE_P, N_NUDGE_M = 0x62, 0x63, 0x64, 0x65

GREEN, GREEN_BLINK, RED, RED_BLINK, YELLOW, YELLOW_BLINK = 1, 2, 3, 4, 5, 6
RING_OFF, RING_SINGLE, RING_VOLUME, RING_PAN = 0, 1, 2, 3

MODE_GENERIC, MODE_LIVE, MODE_LIVE_ALT = 0x40, 0x41, 0x42


def _mode(mode: int) -> mido.Message:
    # F0 47 <dev 7F> 73 60 00 04 <mode> <host version: maj min fix> F7
    return mido.Message("sysex", data=[0x47, 0x7F, 0x73, 0x60, 0x00, 0x04, mode, 1, 0, 0])


def enter() -> list[mido.Message]:
    return [_mode(MODE_LIVE_ALT)]


def leave() -> list[mido.Message]:
    msgs = [mido.Message("note_on", channel=ch, note=n, velocity=0)
            for ch in range(8) for n in range(N_ARM, N_CLIP[-1] + 1)]
    msgs += [mido.Message("note_on", channel=0, note=n, velocity=0)
             for n in range(N_CLIPTRACK, N_NUDGE_M + 1)]
    msgs += [mido.Message("control_change", channel=0, control=n + 8, value=RING_OFF)
             for n in (*DEVICE_KNOBS, *TRACK_KNOBS)]
    return [*msgs, _mode(MODE_GENERIC)]


# A desk that fell back to Generic mode (2026-10-16, the owner's findings).
# The APC40 starts in Mode 0 whenever it powers up ("The unit defaults to
# Mode 0 on startup", Akai rev 1), and a power cycle under a running app
# can keep the port, so the intro `enter` sends at connect is not sent
# again. In Mode 0 ("Mode 0 Button Type", Akai's inbound table) ACTIVATOR,
# SOLO, RECORD ARM, CLIP/TRACK, DEVICE ON/OFF, ◀ ▶, PAN and SEND A–C are
# toggles the device keeps (one message a press: note-on turning on,
# note-off turning off; a light the host sends sets that state), TRACK
# SELECTION and MASTER send nothing, and the device knobs and the eight
# device buttons send on the channel of the track the device selected
# itself. In Mode 2 every button is momentary and those send on channel 0.
# `fell_back` names the messages Mode 2 never sends — midi.py then sends
# the intro again; `in_channel` reads a device button on any channel as
# the one button it is.
MODE0_TOGGLES = frozenset({N_ARM, N_SOLO, N_ACTIVATOR, N_CLIPTRACK, N_DEVICE_ON, N_DEV_L,
                           N_DEV_R, N_PAN, N_SEND_A, N_SEND_B, N_SEND_C})
DEVICE_BUTTONS = range(N_CLIPTRACK, N_METRO + 1)     # banked by track in Mode 0 only


def fell_back(kind: str, channel: int, number: int, on: bool, held: bool) -> bool:
    """Is this message one the device sends only in Generic mode? A device
    knob or device button on a channel other than 0, or on a Mode-0 toggle
    a note-off with no press held (a release of nothing) or a note-on while
    its last press is still held (a second press with no release). `held`:
    a press on this control is waiting for its release. A button held down
    across a launch or a reconnect reads as one too; the cost is one more
    intro, which changes nothing in Mode 2."""
    if kind == "cc":
        return number in DEVICE_KNOBS and channel != 0
    if kind != "note":
        return False
    if number in DEVICE_BUTTONS and channel != 0:
        return True
    return number in MODE0_TOGGLES and on == held


def in_channel(kind: str, channel: int, number: int) -> int:
    """The channel a message is read on: a device button's is 0, whatever
    track a Mode-0 device had selected (Mode 2 sends them on 0; the map's
    rows name 0). Everything else keeps its own."""
    return 0 if kind == "note" and number in DEVICE_BUTTONS else channel


# Hand check 31 — the one hardware assumption plan 13 D7 rests on: in mode
# 0x42 a ring CC sent to a device or track knob also re-bases the encoder,
# so its next turn continues from the value just drawn. midi.py catches a
# ring-feedback row at the value it sends when this is True; if the check
# fails, set it False and those knobs fall back to soft pickup like the
# faders — nothing else changes.
RING_REBASES_KNOB = True


def is_relative(cc: int) -> bool:
    return cc == CC_CUE


def ring_setup(channel: int, cc: int, style: int) -> list[mido.Message]:
    """Messages that put a knob's ring in a style (0 turns it off)."""
    if cc in DEVICE_KNOBS or cc in TRACK_KNOBS:
        return [mido.Message("control_change", channel=channel, control=cc + 8, value=style)]
    return []


def feedback_for(kind: str, channel: int, number: int) -> dict | None:
    """What feedback a learned control can show, if any."""
    if kind == "cc" and (number in DEVICE_KNOBS or number in TRACK_KNOBS):
        return {"feedback": "ring", "ring": RING_VOLUME}
    if kind == "cc" and number in (CC_FADER, CC_MASTER, CC_XFADE):
        return {"feedback": None, "ring": 0}      # a pot: no light, the map's fader row
    if kind == "note":
        grid = N_CLIP[0] <= number <= N_CLIP[-1]
        return {"feedback": "led", "on": GREEN if grid else 1, "off": 0}
    return None


def blink_of(number: int, on: int) -> int:
    """The velocity that blinks a button's LED, from the row's "on"
    velocity (the protocol table in the module docstring): on the clip
    grid the colour's blink is the colour + 1 (green 1 → 2, red 3 → 4,
    yellow 5 → 6); any other button has one blink, 2. Not hand-checked on
    the mk1 (plan 15, group K)."""
    return on + 1 if N_CLIP[0] <= number <= N_CLIP[-1] else 2


def filled_of(number: int, on: int) -> int | None:
    """The velocity for "something is here, not selected" (plan 19 WP2,
    fork 5: a bank pad whose slot holds a preset that is not the loaded
    one): YELLOW on the clip grid, None on any other button — it has no
    third state — and None for a row whose "on" is already yellow, which
    would then show filled and selected alike. Yellow at velocity 5 is
    Akai's table; how it reads beside green on the mk1 is not hand-checked
    (plan 19, check O2). Returning None here turns the third state off."""
    if N_CLIP[0] <= number <= N_CLIP[-1] and on not in (YELLOW, YELLOW_BLINK):
        return YELLOW
    return None


# The sequencer page's lights (plan 31 §A): a shade (routing.led_shade) →
# (its velocity on the clip grid, on any other button). "on" and "off" are
# the row's own `on` / `off`, and "held" is `filled_of`'s; these two are
# the page's: a step under the playhead (yellow), a step in a muted lane
# (red) — a scene button's muted lane blinks. Not hand-checked (group Z)
SHADE = {"hit": (YELLOW, 1), "muted": (RED, 2)}


def shade_of(number: int, shade: str) -> int | None:
    """The velocity for a page shade on this button (`SHADE`), or None for
    a shade the row's own `on` / `off` / `filled_of` draws."""
    v = SHADE.get(shade)
    if v is None:
        return None
    return v[0] if N_CLIP[0] <= number <= N_CLIP[-1] else v[1]


# Akai's names for the controls, for the panel ("track knob 3", "clip 4·2")
_NOTE_NAMES = {
    N_CLIPTRACK: "CLIP/TRACK", N_DEVICE_ON: "DEVICE ON/OFF", N_DEV_L: "device ◀",
    N_DEV_R: "device ▶", N_DETAIL: "DETAIL", N_QUANT: "QUANT", N_OVERDUB: "OVERDUB",
    N_METRO: "METRONOME", N_MASTER_SEL: "MASTER select", N_STOP_ALL: "STOP ALL CLIPS",
    N_PAN: "PAN", N_SEND_A: "SEND A", N_SEND_B: "SEND B", N_SEND_C: "SEND C",
    N_PLAY: "PLAY", N_STOP: "STOP", N_REC: "REC", N_UP: "▲", N_DOWN: "▼", N_RIGHT: "▶",
    N_LEFT: "◀", N_SHIFT: "SHIFT", N_TAP: "TAP TEMPO", N_NUDGE_P: "NUDGE +",
    N_NUDGE_M: "NUDGE −",
}
_TRACK_NOTES = {N_ARM: "rec-arm", N_SOLO: "solo", N_ACTIVATOR: "activator",
                N_SELECT: "track select", N_CLIPSTOP: "clip stop"}


def control_name(source: str) -> str | None:
    """Akai's name for the control a MIDI source names, or None when the
    source is not one of the APC40's ("cc:0:50" → "track knob 3",
    "note:1:56" → "clip 4·2", "note:0:98" → "SHIFT")."""
    kind, _, rest = source.partition(":")
    ch_s, _, num_s = rest.partition(":")
    try:
        num = int(num_s)
        ch = None if ch_s == "*" else int(ch_s)
    except ValueError:
        return None
    track = (ch or 0) + 1
    if kind == "cc":
        if num in DEVICE_KNOBS:
            return f"device knob {num - DEVICE_KNOBS[0] + 1}"
        if num in TRACK_KNOBS:
            return f"track knob {num - TRACK_KNOBS[0] + 1}"
        return {CC_FADER: f"track fader {track}", CC_MASTER: "MASTER fader",
                CC_XFADE: "crossfader", CC_CUE: "cue level"}.get(num)
    if kind == "note":
        if num in _TRACK_NOTES:
            return f"{_TRACK_NOTES[num]} {track}"
        if num in N_CLIP:
            return f"clip {N_CLIP.index(num) + 1}·{track}"
        if num in N_SCENE:
            return f"scene launch {N_SCENE.index(num) + 1}"
        return _NOTE_NAMES.get(num)
    return None


# ---------------------------------------------------------------- the layout
# Plan 14 WP7, decision 25 (a): every control the protocol names, where it
# sits on the device, and a short glyph the panel prints wherever a
# control is named (the ROUTING rows, Learn, the on-screen desk,
# ui_desk.py). Akai's names ("track knob 3") stay for the tooltips.
#
#   K1–K8   track knobs (top right, two rows of four)
#   D1–D8   device knobs (right, below the bank select)
#   S1–S8   track faders   SM master fader   X crossfader   C cue level
#   Gr·c    the button field, row r · column c: rows 1–5 clip launch,
#           6 clip stop, 7 track select, 8 activator, 9 solo, 10 rec-arm;
#           column 9 is scene launch 1–5 · STOP ALL · MASTER select
#   B1–B22  the other buttons: PAN, SEND A–C; the eight device buttons;
#           PLAY, STOP, REC; ▲ ▼ ▶ ◀; TAP TEMPO, NUDGE −, NUDGE +
#   ⇧       SHIFT
#
# Positions are in a unit grid (x right, y down) that draws like the
# mk1's face: the button field and the faders on the left, one unit a
# column; the knobs, the bank select, the transport corner and the
# crossfader on the right. The picture is hand check 45's to confirm.


@dataclass(frozen=True)
class Control:
    """One physical control: its MIDI source (``cc:*:16`` for a knob that
    sends on any channel, ``note:3:53`` for a per-track button on channel
    3), its kind (knob, fader, button, grid), its glyph, and where it sits
    (x, y, w, h in layout units)."""

    source: str
    kind: str
    glyph: str
    x: float
    y: float
    w: float
    h: float

    @property
    def name(self) -> str:
        """Akai's name for it ("device knob 3")."""
        return control_name(self.source) or self.source


FIELD_ROWS = [*N_CLIP, N_CLIPSTOP, N_SELECT, N_ACTIVATOR, N_SOLO, N_ARM]   # G1… G10
FIELD_Y = [0.0, 1.0, 2.0, 3.0, 4.0, 5.3, 6.4, 7.6, 8.6, 9.6]               # a gap under the clips
OTHER_BUTTONS = [N_PAN, N_SEND_A, N_SEND_B, N_SEND_C,                      # B1–B4
                 N_CLIPTRACK, N_DEVICE_ON, N_DEV_L, N_DEV_R,               # B5–B8
                 N_DETAIL, N_QUANT, N_OVERDUB, N_METRO,                    # B9–B12
                 N_PLAY, N_STOP, N_REC,                                    # B13–B15
                 N_UP, N_DOWN, N_RIGHT, N_LEFT,                            # B16–B19
                 N_TAP, N_NUDGE_M, N_NUDGE_P]                              # B20–B22
RIGHT = 9.7        # the right-hand section's left edge


def _layout() -> list[Control]:
    out: list[Control] = []
    # the button field: eight track columns and the master column
    for r, (note, y) in enumerate(zip(FIELD_ROWS, FIELD_Y), 1):
        for c in range(1, 9):
            out.append(Control(f"note:{c - 1}:{note}", "grid", f"G{r}·{c}", c - 1, y, 1, 1))
    for r, note in enumerate(N_SCENE, 1):
        out.append(Control(f"note:0:{note}", "grid", f"G{r}·9", 8.2, FIELD_Y[r - 1], 1, 1))
    out.append(Control(f"note:0:{N_STOP_ALL}", "grid", "G6·9", 8.2, FIELD_Y[5], 1, 1))
    out.append(Control(f"note:0:{N_MASTER_SEL}", "grid", "G7·9", 8.2, FIELD_Y[6], 1, 1))
    out.append(Control(f"cc:0:{CC_CUE}", "knob", "C", 8.2, 7.9, 1, 1.4))
    # the faders, under their strips; the master under the master column
    for c in range(1, 9):
        out.append(Control(f"cc:{c - 1}:{CC_FADER}", "fader", f"S{c}", c - 1, 10.9, 1, 3.6))
    out.append(Control(f"cc:0:{CC_MASTER}", "fader", "SM", 8.2, 10.9, 1, 3.6))
    # the right-hand section, top down
    b = {n: f"B{i}" for i, n in enumerate(OTHER_BUTTONS, 1)}
    for k, cc in enumerate(TRACK_KNOBS):
        out.append(Control(f"cc:0:{cc}", "knob", f"K{k + 1}",
                           RIGHT + k % 4, 1.1 * (k // 4), 1, 1.1))
    for k, n in enumerate((N_PAN, N_SEND_A, N_SEND_B, N_SEND_C)):
        out.append(Control(f"note:0:{n}", "button", b[n], RIGHT + k, 2.35, 1, 0.75))
    # the bank select as a cross; TAP and NUDGE beside it; SHIFT under them
    for n, dx, dy in ((N_UP, 0.6, 3.35), (N_LEFT, 0.0, 4.05), (N_RIGHT, 1.2, 4.05),
                      (N_DOWN, 0.6, 4.75)):
        out.append(Control(f"note:0:{n}", "button", b[n], RIGHT + dx, dy, 0.8, 0.7))
    out.append(Control(f"note:0:{N_TAP}", "button", b[N_TAP], RIGHT + 2.2, 3.35, 1.8, 0.7))
    out.append(Control(f"note:0:{N_NUDGE_M}", "button", b[N_NUDGE_M], RIGHT + 2.2, 4.05, 0.9, 0.7))
    out.append(Control(f"note:0:{N_NUDGE_P}", "button", b[N_NUDGE_P], RIGHT + 3.1, 4.05, 0.9, 0.7))
    out.append(Control(f"note:0:{N_SHIFT}", "button", "⇧", RIGHT + 2.2, 4.75, 1.8, 0.7))
    for k, cc in enumerate(DEVICE_KNOBS):
        out.append(Control(f"cc:*:{cc}", "knob", f"D{k + 1}",
                           RIGHT + k % 4, 5.65 + 1.1 * (k // 4), 1, 1.1))
    for k, n in enumerate(OTHER_BUTTONS[4:12]):
        out.append(Control(f"note:0:{n}", "button", b[n],
                           RIGHT + k % 4, 7.95 + 0.75 * (k // 4), 1, 0.75))
    for k, n in enumerate((N_PLAY, N_STOP, N_REC)):
        out.append(Control(f"note:0:{n}", "button", b[n], round(RIGHT + k * 4 / 3, 3), 9.6,
                           1.333, 0.75))
    out.append(Control(f"cc:0:{CC_XFADE}", "fader", "X", RIGHT, 13.5, 4, 1.0))
    return out


LAYOUT: list[Control] = _layout()
LAYOUT_W = max(c.x + c.w for c in LAYOUT)
LAYOUT_H = max(c.y + c.h for c in LAYOUT)
_BY_SOURCE = {c.source: c for c in LAYOUT}


def _parse(source: str) -> tuple[str, str, int] | None:
    kind, _, rest = source.partition(":")
    ch, _, num = rest.partition(":")
    try:
        return kind, ch, int(num)
    except ValueError:
        return None


def controls(source: str) -> list[Control]:
    """The layout's controls a MIDI source names: one for a one-channel
    row, one for an any-channel row on a knob that has one (``cc:*:48`` is
    K1), every track's for an any-channel row on a per-track control
    (``note:*:53`` is the whole first clip row); none for a source the
    APC40 does not send."""
    c = _BY_SOURCE.get(source)
    if c is not None:
        return [c]
    parsed = _parse(source)
    if parsed is None:
        return []
    kind, ch, num = parsed
    out = []
    for c in LAYOUT:
        k2, c2, n2 = _parse(c.source)
        if k2 == kind and n2 == num and (ch == "*" or c2 == "*" or c2 == ch):
            out.append(c)
    return out


def glyph(source: str) -> str | None:
    """The glyph of the control a MIDI source names ("cc:*:16" → "D1",
    "cc:0:16" → "D1", "note:3:53" → "G1·4"), None for a source the APC40
    does not send; an any-channel row on a per-track control names the
    row ("note:*:53" → "G1·*")."""
    cs = controls(source)
    if len(cs) == 1:
        return cs[0].glyph
    if not cs:
        return None
    g = cs[0].glyph
    return g.split("·")[0] + "·*" if "·" in g else g.rstrip("0123456789") + "*"


def named(source: str) -> str | None:
    """A control in the words a message uses: the glyph, then Akai's name
    ("D3 (device knob 3)"), or None when the APC40 has no such control."""
    cs = controls(source)
    if not cs:
        return None
    if len(cs) > 1:
        return f"{glyph(source)} (every track)"
    return f"{cs[0].glyph} ({cs[0].name})"


# ---------------------------------------------------------------- default map
# rows in routing.Binding's JSON form: {"source": "cc:<ch|*>:<n>" /
# "note:<ch>:<n>", "target": param id, "op", …}; channel None = any

def _src(kind, number, channel):
    return f"{kind}:{'*' if channel is None else channel}:{number}"


def _cc(param, number, channel=None, *, ring=RING_VOLUME, **kw):
    b = {"source": _src("cc", number, channel), "target": param, "op": "abs",
         "feedback": "ring" if ring else None, "ring": ring}
    b.update(kw)
    return b


def _note(param, number, channel=0, *, op="toggle", on=1, **kw):
    b = {"source": _src("note", number, channel), "target": param, "op": op,
         "feedback": "led", "on": on, "off": 0}
    b.update(kw)
    return b


_KNOB_KEYS = ("trim", "exp", "trn", "pre", "post", "atk", "dec", "thr")
_BAND_PLANES = ("ZW", "XW", "YW", "XY", "XZ", "YZ")  # bands.BANDS[i].pl, SUB→AIR

G, P = "global", "preset"    # the layers (plan 13 §3.2); no layer = invariant

# The bank's pads (plan 19 WP2): (note, channel) of slot k — clip row 1 is
# slots 1–8 (the F-keys' eight), rows 4 and 5 slots 9–24. Its length is the
# bank's size on the desk; a test pins it to library.SLOTS (this module
# imports nothing of the app's)
BANK_PADS: list[tuple[int, int]] = [
    *[(N_CLIP[0], k) for k in range(8)],             # row 1: slots 1–8
    *[(N_CLIP[3], k) for k in range(8)],             # row 4: slots 9–16
    *[(N_CLIP[4], k) for k in range(8)]]             # row 5: slots 17–24

# The fresh preset layer's device knobs (plan 19 WP3): D1–D4, the scene
# params not on K1–K8 that act on every preset whatever is switched on —
# the 4D perspective, the camera's two angles — and the face pattern (an
# enum on an absolute knob: it steps through the patterns). D5–D8 stay dark.
# A fresh preset, a file with no `desk` key and every scene-only factory
# preset get these; a preset with knobs of its own replaces all eight
# (preset.knob_desk)
SCENE = ("view.depth4", "camera.yaw", "camera.pitch", "view.pattern")

# The render toggles on scene launch 1–4 (plan 24 C1): invariant rows, so
# points, lines, faces and rotate do the same on both layers and their
# LEDs always show the live state. They were the preset layer's until
# then, and every preset saved before carries those four rows in its desk
# (routing.RETIRED_DESK_ROWS drops them quietly at load)
TOGGLES = ("view.points", "view.lines", "view.faces", "view.rotate")

# The desk's SAVE button (plan 24 C1, the owner's choice of 2026-10-14):
# (note, channel) of track 8's clip stop, free since PR #158
SAVE: tuple[int, int] = (N_CLIPSTOP, 7)

# The track faders S1–S8 (plan 24 C2, decision 17): the channel of track
# fader k + 1 is k. On the preset layer they are each preset's own targets,
# bound by its desk like the device knobs (`preset.track_fader`); no row in
# this map, so no default is inherited and a preset with no fader rows
# leaves them dark. Under SHIFT they are SHIFT_FADERS, the audio strip that
# was invariant on them until then
TRACK_FADERS = range(8)
SHIFT_FADERS = (*(f"band.{i}.post" for i in range(6)), "master.dyn", "master.trim")

DEFAULT_MAP: list[dict] = [
    # device knobs, global layer (SHIFT up): the open band strip, in panel order
    *[_cc(f"band.sel.{k}", cc, layer=G) for k, cc in zip(_KNOB_KEYS, DEVICE_KNOBS)],
    # device knobs 1–4, preset layer: SCENE (plan 19 WP3); 5–8 dark
    *[_cc(t, cc, layer=P) for t, cc in zip(SCENE, DEVICE_KNOBS)],
    # track knobs, preset layer: the view faders (a fresh preset's own eight)
    _cc("view.bright", 0x30, 0, layer=P), _cc("view.speed", 0x31, 0, layer=P),
    _cc("view.instances", 0x32, 0, layer=P), _cc("view.pattern_mix", 0x33, 0, layer=P),
    _cc("view.inst_amp", 0x34, 0, layer=P), _cc("view.inst_rate", 0x35, 0, layer=P),
    _cc("view.bmp_alpha", 0x36, 0, layer=P), _cc("camera.zoom", 0x37, 0, layer=P),
    # track knobs 1–5, global layer: the hand feel and the clock (decision
    # register row 9, a first cut — the list is these rows, nothing else
    # decides it); 6–8 are free, so dark and dead under SHIFT
    _cc("hands.smooth", 0x30, 0, layer=G), _cc("hands.response", 0x31, 0, layer=G),
    _cc("hands.catch", 0x32, 0, layer=G), _cc("hands.sel.return", 0x33, 0, layer=G),
    _cc("tempo.bpm", 0x34, 0, layer=G),
    # track faders S1–S8, global layer (SHIFT up; plan 24 C2, decision 17,
    # amending D6): per-band output drive on 1–6, master dynamics and trim
    # on 7–8 — the audio one latch away. On the preset layer the faders are
    # the loaded preset's (`TRACK_FADERS`): none here, so a fresh preset and
    # every factory one leaves them dark. Soft pickup across the latch (D7)
    *[_cc(t, CC_FADER, i, ring=0, layer=G) for i, t in enumerate(SHIFT_FADERS)],
    # MASTER (invariant): the audio drive, the same on both layers
    _cc("master.gain", CC_MASTER, 0, ring=0),
    # crossfader: the master dim (plan 15 WP3, decision 28) — black (left,
    # CC 0) ↔ full (right); invariant, soft pickup like every fader, so one
    # parked at the left does nothing until it is brought up to the value.
    # That CC 0 is the left end is not hand-checked (check 55)
    _cc("output.dim", CC_XFADE, 0, ring=0),
    _cc("view.shape", CC_CUE, 0, op="rel", ring=0, layer=P),
    # SHIFT latches the layer (routing's `desk.shift`); its LED is lit while
    # the global layer is up
    _note("desk.shift", N_SHIFT),
    # track buttons, one strip per band
    *[_note("band.select", N_SELECT, i, op="set", value=i) for i in range(6)],
    *[_note(f"view.plane.{pl}", N_ACTIVATOR, i, layer=P) for i, pl in enumerate(_BAND_PLANES)],
    *[_note(f"band.{i}.fn", N_SOLO, i) for i in range(6)],
    *[_note(f"band.{i}.reset", N_ARM, i) for i in range(6)],
    # clip grid: the preset bank on rows 1, 4 and 5 (invariant: no layer,
    # so one meaning on both layers, no Learn takes a pad, no preset maps
    # one — D6, extended by plan 19) · scenes (global) · grid motion
    # (preset). Shape selection left rows 4–5 for the cue knob above,
    # which reaches every shape
    *[_note("preset.select", n, ch, op="set", value=k, on=GREEN)
      for k, (n, ch) in enumerate(BANK_PADS)],
    # …and each bank pad held midi.HOLD_S on an empty slot saves the live
    # state there as a new preset — the same row: `preset.select` carries
    # the hold (`Param.held`, midi.py). A filled slot is never written
    # over: the press loads it. This replaced plan 15's clip-stop SAVE AS
    # bar (2026-10-09), and the clip-stop row was freed.
    # SAVE (plan 24 C1, the two-handed save): track 8's clip stop, held,
    # turns a bank pad's tap into a save into that pad's slot — an empty
    # one as the hold does, a filled one as a NEW preset the slot then
    # points at (`Param.save_into`, midi.py `_save_tap`). Invariant: the
    # same on both layers, as the pads are. Clip stops 1–7 stay free
    _note("desk.save", *SAVE, op="momentary"),
    *[_note("scene.select", N_CLIP[1], k, op="set", value=k, on=YELLOW, layer=G)
      for k in range(8)],
    *[_note("scene.select", N_CLIP[2], k, op="set", value=8 + k, on=YELLOW, layer=G)
      for k in range(3)],
    *[_note("view.inst_motion", N_CLIP[2], 4 + k, op="set", value=k, on=RED, layer=P)
      for k in range(4)],
    # scene launch column: the render toggles, invariant since plan 24 C1
    # (decision 18: the same on both layers, their LEDs the live state;
    # D6's list grows by four), and the view reset on the preset layer
    *[_note(pid, n) for pid, n in zip(TOGGLES, N_SCENE)],
    _note("camera.reset", N_SCENE[4], layer=P),
    _note("scene.reset_all", N_STOP_ALL),
    # transport and the rest
    _note("audio.play", N_PLAY), _note("audio.stop", N_STOP), _note("audio.mic", N_REC),
    # the clock (tempo.py, lfo.py): TAP TEMPO taps, NUDGE ± shifts the downbeat
    # by a hundredth of a beat, METRONOME is the global LFO trigger — its LED
    # blinks on the beat (the trigger param carries the light; see the docstring)
    _note("tempo.tap", N_TAP), _note("tempo.nudge", N_NUDGE_P, op="step", value=1),
    _note("tempo.nudge", N_NUDGE_M, op="step", value=-1),
    _note("lfo.trigger", N_METRO), _note("preset.next", N_QUANT),
    # OVERDUB is home (plan 15 WP2, decision 27): it loads the preset the
    # show's startup preset. No layer, so invariant — the same on both layers, no
    # Learn takes it, no preset maps it. Lit while the show names a
    # startup preset (the trigger param carries the light, as METRONOME's does)
    _note("preset.home", N_OVERDUB),
    _note("view.bright", N_UP, op="step", value=3, layer=P),
    _note("view.bright", N_DOWN, op="step", value=-3, layer=P),
    _note("band.select", N_RIGHT, op="step", value=1),
    _note("band.select", N_LEFT, op="step", value=-1),
    _note("ui.panel", N_DEVICE_ON), _note("ui.cheatsheet", N_DETAIL),
    _note("audio.restart", N_CLIPTRACK),
    # overlay: master-select floats the render over the screen, pan sends
    # clicks through to what is underneath (the panel stops being clickable)
    _note("overlay.on", N_MASTER_SEL), _note("overlay.passthrough", N_PAN),
    # SEND A latches the sequencer page (plan 31 §A, decision 7; seq_page.py):
    # invariant, lit while the page is up. The page's rows then shadow clip
    # rows 1–5, the clip stops and scene launch 1–5 — the bank, SAVE and
    # the render toggles come back when it is let go
    _note("seq.page", N_SEND_A),
]
