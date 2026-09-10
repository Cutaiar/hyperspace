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
"""

from __future__ import annotations

import mido

PORT_MATCH = "APC40"

DEVICE_KNOBS = range(0x10, 0x18)
TRACK_KNOBS = range(0x30, 0x38)
CC_FADER, CC_MASTER, CC_XFADE, CC_CUE = 0x07, 0x0E, 0x0F, 0x2F

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

def _cc(param, number, channel=None, *, ring=RING_VOLUME, **kw):
    b = {"param": param, "kind": "cc", "number": number, "channel": channel,
         "mode": "abs", "feedback": "ring" if ring else None, "ring": ring}
    b.update(kw)
    return b


def _note(param, number, channel=0, *, mode="trigger", on=1, **kw):
    b = {"param": param, "kind": "note", "number": number, "channel": channel,
         "mode": mode, "feedback": "led", "on": on, "off": 0}
    b.update(kw)
    return b


_KNOB_KEYS = ("trim", "exp", "trn", "pre", "post", "atk", "dec", "thr")
_BAND_PLANES = ("ZW", "XW", "YW", "XY", "XZ", "YZ")  # bands.BANDS[i].pl, SUB→AIR

DEFAULT_MAP: list[dict] = [
    # device knobs: the open band strip, in panel order
    *[_cc(f"band.sel.{k}", cc) for k, cc in zip(_KNOB_KEYS, DEVICE_KNOBS)],
    # track knobs: the view faders
    _cc("view.bright", 0x30, 0), _cc("view.speed", 0x31, 0), _cc("view.instances", 0x32, 0),
    _cc("view.pattern_mix", 0x33, 0), _cc("view.inst_amp", 0x34, 0),
    _cc("view.inst_rate", 0x35, 0), _cc("view.bmp_alpha", 0x36, 0), _cc("camera.zoom", 0x37, 0),
    # faders: per-band output drive on 1–6, master dynamics and trim on 7–8
    *[_cc(f"band.{i}.post", CC_FADER, i, ring=0) for i in range(6)],
    _cc("master.dyn", CC_FADER, 6, ring=0), _cc("master.trim", CC_FADER, 7, ring=0),
    _cc("master.gain", CC_MASTER, 0, ring=0),
    # crossfader: the video behind (left) ↔ black ground (right) in overlay mode
    _cc("overlay.bg", CC_XFADE, 0, ring=0),
    _cc("view.shape", CC_CUE, 0, mode="rel", ring=0),
    # track buttons, one strip per band
    *[_note("band.select", N_SELECT, i, mode="set", value=i) for i in range(6)],
    *[_note(f"view.plane.{pl}", N_ACTIVATOR, i) for i, pl in enumerate(_BAND_PLANES)],
    *[_note(f"band.{i}.fn", N_SOLO, i) for i in range(6)],
    *[_note(f"band.{i}.reset", N_ARM, i) for i in range(6)],
    # clip grid: themes · scenes · grid motion · shapes
    *[_note("theme.select", N_CLIP[0], k, mode="set", value=k, on=GREEN) for k in range(8)],
    *[_note("scene.select", N_CLIP[1], k, mode="set", value=k, on=YELLOW) for k in range(8)],
    *[_note("scene.select", N_CLIP[2], k, mode="set", value=8 + k, on=YELLOW) for k in range(3)],
    *[_note("view.inst_motion", N_CLIP[2], 4 + k, mode="set", value=k, on=RED) for k in range(4)],
    *[_note("view.shape", N_CLIP[3], k, mode="set", value=k, on=GREEN) for k in range(8)],
    *[_note("view.shape", N_CLIP[4], k, mode="set", value=8 + k, on=GREEN) for k in range(8)],
    # scene launch column: render toggles and the view reset
    _note("view.points", N_SCENE[0]), _note("view.lines", N_SCENE[1]),
    _note("view.faces", N_SCENE[2]), _note("view.rotate", N_SCENE[3]),
    _note("camera.reset", N_SCENE[4]),
    _note("scene.reset_all", N_STOP_ALL),
    # transport and the rest
    _note("audio.play", N_PLAY), _note("audio.stop", N_STOP), _note("audio.mic", N_REC),
    _note("theme.next", N_TAP), _note("view.shape", N_NUDGE_P, mode="step", value=1),
    _note("view.shape", N_NUDGE_M, mode="step", value=-1),
    _note("view.bright", N_UP, mode="step", value=3),
    _note("view.bright", N_DOWN, mode="step", value=-3),
    _note("band.select", N_RIGHT, mode="step", value=1),
    _note("band.select", N_LEFT, mode="step", value=-1),
    _note("ui.panel", N_DEVICE_ON), _note("ui.cheatsheet", N_DETAIL),
    _note("audio.restart", N_CLIPTRACK),
    # overlay: master-select floats the render over the screen, pan sends
    # clicks through to what is underneath (the panel stops being clickable)
    _note("overlay.on", N_MASTER_SEL), _note("overlay.passthrough", N_PAN),
]
