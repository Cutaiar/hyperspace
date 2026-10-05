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
blink. Every other button: 0 off · 1 on · 2 blink. Knob rings: the knob's
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
meaning on both layers — the faders, the preset row, SHIFT, the clock and
transport corner, the track buttons), ``"global"`` is the SHIFT layer
(the band strip on the device knobs, the hand feel and BPM on track knobs
1–5, the band scenes on clip rows 2–3), ``"preset"`` is the loaded
preset's own (the factory default below is what a fresh preset starts
with). A control with no row on the layer that is up is dark and does
nothing; midi.py dispatches and draws by those rules.

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
# speaks, whether or not DEFAULT_MAP below uses it (N_CLIPSTOP, N_DEV_L/R,
# N_OVERDUB, N_SEND_A/C, the *_BLINK velocities and RING_SINGLE /
# RING_PAN are unused today and kept as the reference for a hand-edited
# bindings.json or a later map).
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
    if kind == "note":
        grid = N_CLIP[0] <= number <= N_CLIP[-1]
        return {"feedback": "led", "on": GREEN if grid else 1, "off": 0}
    return None


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

DEFAULT_MAP: list[dict] = [
    # device knobs, global layer (SHIFT up): the open band strip, in panel order
    *[_cc(f"band.sel.{k}", cc, layer=G) for k, cc in zip(_KNOB_KEYS, DEVICE_KNOBS)],
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
    # faders (invariant): per-band output drive on 1–6, master dynamics and trim on 7–8
    *[_cc(f"band.{i}.post", CC_FADER, i, ring=0) for i in range(6)],
    _cc("master.dyn", CC_FADER, 6, ring=0), _cc("master.trim", CC_FADER, 7, ring=0),
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
    # clip grid: the preset bank (invariant) · scenes (global) · grid motion · shapes (preset)
    *[_note("preset.select", N_CLIP[0], k, op="set", value=k, on=GREEN) for k in range(8)],
    *[_note("scene.select", N_CLIP[1], k, op="set", value=k, on=YELLOW, layer=G)
      for k in range(8)],
    *[_note("scene.select", N_CLIP[2], k, op="set", value=8 + k, on=YELLOW, layer=G)
      for k in range(3)],
    *[_note("view.inst_motion", N_CLIP[2], 4 + k, op="set", value=k, on=RED, layer=P)
      for k in range(4)],
    *[_note("view.shape", N_CLIP[3], k, op="set", value=k, on=GREEN, layer=P) for k in range(8)],
    *[_note("view.shape", N_CLIP[4], k, op="set", value=8 + k, on=GREEN, layer=P)
      for k in range(8)],
    # scene launch column (preset): render toggles and the view reset
    _note("view.points", N_SCENE[0], layer=P), _note("view.lines", N_SCENE[1], layer=P),
    _note("view.faces", N_SCENE[2], layer=P), _note("view.rotate", N_SCENE[3], layer=P),
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
    _note("view.bright", N_UP, op="step", value=3, layer=P),
    _note("view.bright", N_DOWN, op="step", value=-3, layer=P),
    _note("band.select", N_RIGHT, op="step", value=1),
    _note("band.select", N_LEFT, op="step", value=-1),
    _note("ui.panel", N_DEVICE_ON), _note("ui.cheatsheet", N_DETAIL),
    _note("audio.restart", N_CLIPTRACK),
    # overlay: master-select floats the render over the screen, pan sends
    # clicks through to what is underneath (the panel stops being clickable)
    _note("overlay.on", N_MASTER_SEL), _note("overlay.passthrough", N_PAN),
]
