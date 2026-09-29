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
    # crossfader: the video behind (left) ↔ black ground (right) in overlay mode
    _cc("overlay.bg", CC_XFADE, 0, ring=0),
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
