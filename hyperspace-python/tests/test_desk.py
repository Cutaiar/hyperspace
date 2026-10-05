# ruff: noqa: F811 — `rig` is test_midi's fixture, taken as each test's argument
"""The APC40's two layers under a latched SHIFT (plan 13 §3, D4–D8, D12).

Driven through `MidiIO` with fake ports, as tests/test_midi.py does (its
rig is reused): the latch and its LED, dispatch per layer with no
fall-through, the invariant controls, feedback that shows only the layer
that is up (an unmapped control dark), the knobs re-based by their rings
and the faders left to soft pickup, a desk replacement (what a preset
load does), the sorted default map and the one-time sort of an older
bindings file.
"""

import json

import pytest
from test_midi import FakeIn, FakeOut, cc, note, push, rig, shift  # noqa: F401 — the fixture

from hyperspace import apc40, routing
from hyperspace.midi import PICKUP_TOL
from hyperspace.routing import Binding, Bindings, bindings_path

SHIFT = apc40.N_SHIFT


def sent_notes(r, n, channel=0):
    return [m.velocity for m in r.out.sent
            if m.type == "note_on" and m.note == n and m.channel == channel]


def sent_cc(r, n, channel=0):
    return [m.value for m in r.out.sent
            if m.type == "control_change" and m.control == n and m.channel == channel]


def row(r, target, layer="any"):
    return next(b for b in r.midi.bindings
                if b.target == target and (layer == "any" or b.layer == layer))


# ------------------------------------------------------------------ SHIFT

def test_shift_latches_the_layer_and_lights_its_led(rig):
    t = rig.midi.table
    assert t.layer == "preset" and sent_notes(rig, SHIFT)[-1] == 0     # dark at power-up
    push(rig, note(SHIFT))
    assert t.layer == "global" and rig.reg["desk.shift"].value is True
    assert sent_notes(rig, SHIFT)[-1] == 1                             # lit while global
    push(rig, note(SHIFT, 0))                                          # the release: nothing
    assert t.layer == "global" and sent_notes(rig, SHIFT)[-1] == 1
    push(rig, note(SHIFT), note(SHIFT, 0))                             # the next press: back
    assert t.layer == "preset" and sent_notes(rig, SHIFT)[-1] == 0
    # the latch is a row like any other: invariant, on the table
    b = row(rig, routing.SHIFT_PARAM)
    assert (b.source, b.layer, b.feedback) == (routing.SHIFT_SOURCE, None, "led")
    rig.reg["desk.shift"].set(True)                                    # the param moves it too
    rig.midi.poll()
    assert t.layer == "global" and sent_notes(rig, SHIFT)[-1] == 1


def test_a_preset_load_drops_to_the_preset_layer(rig):
    t, reg = rig.midi.table, rig.reg
    shift(rig)
    assert t.layer == "global"
    notes = t.set_desk([{"source": "cc:*:16", "target": "view.speed", "op": "abs",
                         "feedback": "ring"}])
    assert notes == [] and t.layer == "preset"
    rig.midi.poll()
    assert sent_notes(rig, SHIFT)[-1] == 0
    # the desk is the new one: device knob 1 is the preset's, the old
    # preset-layer rows are gone, the global layer untouched
    assert [(b.source, b.target) for b in t.desk()] == [("cc:*:16", "view.speed")]
    push(rig, cc(0x10, 100))
    assert reg["view.speed"].norm == pytest.approx(100 / 127, abs=PICKUP_TOL)
    bright = reg["view.bright"].norm
    push(rig, cc(0x30, 3))                         # was view.bright's; this desk leaves it dark
    assert reg["view.bright"].norm == pytest.approx(bright)
    assert row(rig, "band.sel.trim", "global").source == "cc:*:16"


def test_shift_release_never_reevaluates_a_held_button(rig):
    """D12: the layer is read at the press. A momentary preset button held
    across a SHIFT press releases on the row it pressed, and the global
    row on the same button never hears the release."""
    t, view = rig.midi.table, rig.view
    n = apc40.N_SCENE[0]
    t.set_desk([Binding(f"note:0:{n}", "view.points", "momentary", feedback="led")])
    t.bindings.append(Binding(f"note:0:{n}", "view.lines", "momentary", feedback="led",
                              layer="global"))
    rig.midi.poll()
    view.points, view.lines = False, True
    push(rig, note(n))                            # pressed on the preset layer
    assert view.points is True
    push(rig, note(SHIFT))                        # SHIFT while the button is down
    assert t.layer == "global"
    push(rig, note(n, 0))                         # released on the global layer
    assert view.points is False and view.lines is True
    push(rig, note(SHIFT, 0))                     # SHIFT's own release does nothing
    assert t.layer == "global" and view.points is False and view.lines is True
    push(rig, note(n), note(n, 0))                # a press now is the global row's
    assert view.lines is False and view.points is False


# ------------------------------------------------------------ knobs, faders

def test_a_layer_switch_rebases_the_knobs_and_leaves_the_faders_to_pick_up(rig):
    reg = rig.reg
    smooth, bright, gain = reg["hands.smooth"], reg["view.bright"], reg["master.gain"]
    smooth.set_norm(0.2)
    bright.set_norm(0.7)
    gain.set_norm(0.5)
    rig.midi.poll()
    push(rig, cc(apc40.CC_MASTER, 64))            # the fader caught at its value
    fader = row(rig, "master.gain")
    assert fader.caught
    # SHIFT: track knob 1 is hand smoothing now — its ring is drawn and the
    # encoder re-based there, so the next turn continues from the ring
    rig.out.sent.clear()
    shift(rig)
    ring = round(smooth.norm * 127)
    assert sent_cc(rig, 0x30)[-1] == ring
    knob = row(rig, "hands.smooth")
    assert knob.caught and knob.last_hw == pytest.approx(ring / 127)
    push(rig, cc(0x30, ring + 10))
    assert smooth.norm == pytest.approx((ring + 10) / 127, abs=PICKUP_TOL)
    assert bright.norm == pytest.approx(0.7, abs=PICKUP_TOL)       # the preset row is inert
    # and back: brightness's ring, re-based, continues from 0.7
    rig.out.sent.clear()
    shift(rig)
    ring = round(bright.norm * 127)
    assert sent_cc(rig, 0x30)[-1] == ring
    push(rig, cc(0x30, ring - 20))
    assert bright.norm == pytest.approx((ring - 20) / 127, abs=PICKUP_TOL)
    # the fader: invariant, never re-based by a switch — still caught, and
    # a base moved behind it (a preset, the panel) still needs a pickup
    assert fader.caught
    push(rig, cc(apc40.CC_MASTER, 70))
    assert gain.norm == pytest.approx(70 / 127, abs=PICKUP_TOL)
    gain.set_norm(0.95)
    rig.midi.poll()
    push(rig, cc(apc40.CC_MASTER, 20))
    assert gain.norm == pytest.approx(0.95, abs=PICKUP_TOL)       # not caught: no jump
    assert apc40.RING_REBASES_KNOB                                # hand check 31's switch


def test_a_preset_load_clears_the_faders_catch(rig):
    t, reg = rig.midi.table, rig.reg
    post = reg["band.2.post"]
    post.set_norm(0.5)
    rig.midi.poll()
    push(rig, cc(apc40.CC_FADER, 64, channel=2))
    fader = row(rig, "band.2.post")
    assert fader.caught
    post.set_norm(0.9)            # the load moves the base under the fader …
    t.set_desk(t.desk())          # … and replaces the desk
    rig.midi.poll()
    assert not fader.caught
    assert all(b.caught for b in t.active() if b.feedback == "ring")   # the knobs re-based
    push(rig, cc(apc40.CC_FADER, 30, channel=2))  # far below the new base: nothing
    assert post.norm == pytest.approx(0.9, abs=PICKUP_TOL)
    push(rig, cc(apc40.CC_FADER, 127, channel=2))  # swept through it: caught
    assert post.norm == pytest.approx(1.0)


def test_the_crossfader_keeps_its_hold_across_a_preset_load(rig):
    """Plan 15 WP3, fork 19: a load clears a fader's catch only when its
    param is no longer where the adapter last put it. A preset never moves
    a session param (D9), so the crossfader — and MASTER — stay caught, and
    the next message moves the value from where it is, in either direction.
    The fader sits a little off the value (a MIDI step against the param's
    detent), on the far side from each move: a cleared catch would neither
    be within the tolerance nor cross, and the fader would be dead."""
    t, reg = rig.midi.table, rig.reg
    dim, gain = reg["output.dim"], reg["master.gain"]
    gain.set_norm(0.5)
    rig.midi.poll()
    push(rig, cc(apc40.CC_XFADE, 127), cc(apc40.CC_XFADE, 64), cc(apc40.CC_MASTER, 64))
    xf, master = row(rig, "output.dim"), row(rig, "master.gain")
    assert xf.caught and master.caught
    assert xf.last_hw > dim.norm == pytest.approx(0.5)      # the fader just above the value
    serial = t.desk_serial
    push(rig, note(apc40.N_CLIP[0], channel=2))             # a preset load, off the clip row
    assert rig.presets.active == 2 and t.desk_serial > serial
    assert xf.caught and master.caught                       # still held
    assert dim.norm == pytest.approx(0.5)                    # and the load did not move it
    push(rig, cc(apc40.CC_XFADE, 30))                        # down, away from the fader's side
    assert dim.norm == pytest.approx(30 / 127, abs=PICKUP_TOL)
    push(rig, cc(apc40.CC_XFADE, 62))
    assert xf.last_hw < dim.norm                             # now just below the value
    t.set_desk(t.desk())                                     # another load
    rig.midi.poll()
    assert xf.caught
    push(rig, cc(apc40.CC_XFADE, 100))                       # up
    assert dim.norm == pytest.approx(100 / 127, abs=PICKUP_TOL)
    push(rig, cc(apc40.CC_MASTER, 90))                       # MASTER held through both
    assert gain.norm == pytest.approx(90 / 127, abs=PICKUP_TOL)
    # a fader the adapter never wrote is not caught by a load …
    assert not row(rig, "master.trim").caught
    # … nor does one keep its hold when another control made the param's
    # last write (review of PR #81): the fader is not where the value is
    push(rig, cc(apc40.CC_XFADE, 100))
    assert xf.caught
    dim.set_norm(0.3)
    rig.midi._note_written(dim)                              # as a button row on it would
    t.set_desk(t.desk())
    rig.midi.poll()
    assert not xf.caught
    push(rig, cc(apc40.CC_XFADE, 101))
    assert dim.norm == pytest.approx(0.3)                    # no jump
    push(rig, cc(apc40.CC_XFADE, 20))                        # swept through: caught again
    assert xf.caught
    # … and the panel moving the dim behind the fader still re-arms pickup
    dim.set_norm(0.6)
    t.set_desk(t.desk())
    rig.midi.poll()
    assert not xf.caught
    push(rig, cc(apc40.CC_XFADE, 5))                         # the fader is below it: nothing
    assert dim.norm == pytest.approx(0.6)


def test_a_desk_edit_on_the_page_redraws_and_keeps_the_faders_catch(rig):
    """Review of PR #65: a desk row retargeted or removed on the ROUTING
    page redraws the desk, but it is not a load — no base moved, so every
    fader keeps its catch."""
    from hyperspace import ui_routing

    t, reg = rig.midi.table, rig.reg
    reg["band.2.post"].set_norm(0.5)
    rig.midi.poll()
    push(rig, cc(apc40.CC_FADER, 64, channel=2))
    fader = row(rig, "band.2.post")
    assert fader.caught
    knob = next(b for b in t.desk() if b.number == 0x30)
    rig.out.sent.clear()
    knob.target = "view.speed"
    ui_routing._desk_edited(t, knob)
    rig.midi.poll()
    assert fader.caught                                          # still caught
    assert sent_cc(rig, 0x30) == [round(reg["view.speed"].norm * 127)]   # redrawn
    push(rig, cc(apc40.CC_FADER, 30, channel=2))
    assert reg["band.2.post"].norm == pytest.approx(30 / 127, abs=PICKUP_TOL)


def test_a_control_that_loses_its_row_goes_dark(rig):
    """D8, review of PR #67: a control whose last row on the up layer goes
    is sent dark — by a preset load with a smaller desk, and by the ROUTING
    page's × — not left showing the old state while it does nothing."""
    from hyperspace import ui_routing

    t, view = rig.midi.table, rig.view
    points, knob6 = apc40.N_SCENE[0], 0x35         # view.points, view.inst_rate: preset-only
    view.points = True
    rig.midi.poll()
    assert sent_notes(rig, points)[-1] > 0                           # lit
    assert sent_cc(rig, knob6 + 8)[-1] != apc40.RING_OFF             # a ring style
    # a preset load whose desk leaves both unmapped
    rig.out.sent.clear()
    t.set_desk([{"source": f"note:0:{apc40.N_SCENE[2]}", "target": "view.faces",
                 "op": "toggle", "feedback": "led", "on": 1}])
    rig.midi.poll()
    assert sent_notes(rig, points) == [0]
    assert sent_cc(rig, knob6 + 8) == [apc40.RING_OFF]
    view.faces = True
    rig.midi.poll()
    faces = apc40.N_SCENE[2]
    assert sent_notes(rig, faces)[-1] == 1
    # the page's × on the one row left
    rig.out.sent.clear()
    t.remove(next(b for b in t.desk() if b.number == faces))
    ui_routing._desk_edited(t)
    rig.midi.poll()
    assert sent_notes(rig, faces) == [0]
    rig.out.sent.clear()
    rig.midi.poll()
    assert sent_notes(rig, faces) == []                              # and stays dark
    # an adapter from before `_shown` (a hot reload skips __init__) still draws
    del rig.midi._shown
    rig.midi.feedback()
    del rig.midi._shown
    rig.midi.redraw()                                                # re-sends: fills it
    assert rig.midi._shown


# --------------------------------------------------------- unmapped, invariant

def test_an_unmapped_control_is_dark_and_does_nothing(rig):
    reg = rig.reg
    # preset layer: the device knobs are free in the factory desk — their
    # rings off, their turns dead; the band scenes' clip row is dark
    styles = sent_cc(rig, 0x10 + 8)
    assert styles and styles[-1] == apc40.RING_OFF
    trim = reg["band.sel.trim"].norm
    push(rig, cc(0x10, 5), cc(0x10, 120))
    assert reg["band.sel.trim"].norm == pytest.approx(trim)
    assert sent_notes(rig, apc40.N_CLIP[1], channel=0)[-1] == 0
    scene = rig.control.scene
    push(rig, note(apc40.N_CLIP[1], channel=4))
    assert rig.control.scene == scene
    # global layer: track knobs 6–8 are free — dark and dead, no fall-through
    # to the preset's view faders
    rig.out.sent.clear()
    shift(rig)
    for k in (5, 6, 7):
        assert sent_cc(rig, 0x30 + k + 8) == [apc40.RING_OFF], k
    rate = reg["view.inst_rate"].norm
    push(rig, cc(0x35, 3), cc(0x35, 125))
    assert reg["view.inst_rate"].norm == pytest.approx(rate)
    # and the preset's buttons: dark under SHIFT, and a press does nothing
    assert sent_notes(rig, apc40.N_SCENE[2])[-1] == 0
    faces = rig.view.faces
    push(rig, note(apc40.N_SCENE[2]), note(apc40.N_SCENE[2], 0))
    assert rig.view.faces == faces


def test_invariant_controls_mean_one_thing_on_both_layers(rig):
    t, reg, clock = rig.midi.table, rig.reg, rig.clock
    t.bindings.append(Binding("cc:2:7", "view.speed", "abs", layer="global"))   # can't act
    speed = reg["view.speed"].norm
    for layer in ("preset", "global"):
        assert t.layer == layer
        for x in rig.midi.bindings:
            x.pickup = False
        v = 20 if layer == "preset" else 100
        push(rig, cc(apc40.CC_FADER, v, channel=2))
        assert reg["band.2.post"].norm == pytest.approx(v / 127, abs=PICKUP_TOL), layer
        assert reg["view.speed"].norm == pytest.approx(speed), layer
        clock.tick(10.0 * (layer == "global") + 1.0)
        push(rig, note(apc40.N_METRO), note(apc40.N_METRO, 0))            # the LFO trigger
        assert clock.t0 == pytest.approx(10.0 * (layer == "global") + 1.0), layer
        push(rig, note(apc40.N_SELECT, channel=3))
        assert rig.control.selb == 3, layer
        rig.control.selb = 0
        shift(rig)
    # the invariant set is the table's layer-None rows, and SHIFT
    assert t.is_invariant(Binding("note:0:98", "x", "toggle"))
    assert t.is_invariant(Binding("cc:5:7", "x", "abs"))
    assert not t.is_invariant(Binding("cc:0:48", "x", "abs"))


def test_a_desk_row_on_an_invariant_control_is_dropped_with_a_note(rig):
    t = rig.midi.table
    notes = t.set_desk([
        {"source": "cc:0:7", "target": "view.speed", "op": "abs"},          # fader 1
        {"source": f"note:0:{SHIFT}", "target": "view.faces", "op": "toggle"},  # SHIFT
        {"source": "key:Z", "target": "view.faces", "op": "toggle"},        # not the desk's
        {"source": "cc:0:16", "target": "view.speed", "op": "abs", "layer": "global"},
    ])
    assert len(notes) == 3
    assert "cc:0:7 → view.speed" in notes[0] and "invariant" in notes[0]
    assert f"note:0:{SHIFT}" in notes[1] and "invariant" in notes[1]
    assert "key:Z" in notes[2] and "not a desk control" in notes[2]
    assert [(b.source, b.layer) for b in t.desk()] == [("cc:0:16", "preset")]  # layer forced
    assert row(rig, "band.0.post").source == "cc:0:7"                          # untouched


# ---------------------------------------------------------- the sorted map

def _old_map() -> list[tuple[str, str]]:
    """apc40.DEFAULT_MAP before plan 13 — its 113 (source, target) pairs,
    frozen here so the sorting can be checked against it."""
    a = apc40
    knobs = ("trim", "exp", "trn", "pre", "post", "atk", "dec", "thr")
    planes = ("ZW", "XW", "YW", "XY", "XZ", "YZ")
    view = ("view.bright", "view.speed", "view.instances", "view.pattern_mix",
            "view.inst_amp", "view.inst_rate", "view.bmp_alpha", "camera.zoom")
    n = lambda num, ch=0: f"note:{ch}:{num}"
    return [
        *[(f"cc:*:{cc}", f"band.sel.{k}") for k, cc in zip(knobs, a.DEVICE_KNOBS)],
        *[(f"cc:0:{0x30 + i}", p) for i, p in enumerate(view)],
        *[(f"cc:{i}:{a.CC_FADER}", f"band.{i}.post") for i in range(6)],
        (f"cc:6:{a.CC_FADER}", "master.dyn"), (f"cc:7:{a.CC_FADER}", "master.trim"),
        (f"cc:0:{a.CC_MASTER}", "master.gain"),
        (f"cc:0:{a.CC_XFADE}", "output.dim"),            # overlay.bg before plan 15 WP3
        (f"cc:0:{a.CC_CUE}", "view.shape"),
        *[(n(a.N_SELECT, i), "band.select") for i in range(6)],
        *[(n(a.N_ACTIVATOR, i), f"view.plane.{pl}") for i, pl in enumerate(planes)],
        *[(n(a.N_SOLO, i), f"band.{i}.fn") for i in range(6)],
        *[(n(a.N_ARM, i), f"band.{i}.reset") for i in range(6)],
        *[(n(a.N_CLIP[0], k), "preset.select") for k in range(8)],   # theme.select before WP2
        *[(n(a.N_CLIP[1], k), "scene.select") for k in range(8)],
        *[(n(a.N_CLIP[2], k), "scene.select") for k in range(3)],
        *[(n(a.N_CLIP[2], 4 + k), "view.inst_motion") for k in range(4)],
        *[(n(a.N_CLIP[3], k), "view.shape") for k in range(8)],
        *[(n(a.N_CLIP[4], k), "view.shape") for k in range(8)],
        (n(a.N_SCENE[0]), "view.points"), (n(a.N_SCENE[1]), "view.lines"),
        (n(a.N_SCENE[2]), "view.faces"), (n(a.N_SCENE[3]), "view.rotate"),
        (n(a.N_SCENE[4]), "camera.reset"), (n(a.N_STOP_ALL), "scene.reset_all"),
        (n(a.N_PLAY), "audio.play"), (n(a.N_STOP), "audio.stop"), (n(a.N_REC), "audio.mic"),
        (n(a.N_TAP), "tempo.tap"), (n(a.N_NUDGE_P), "tempo.nudge"),
        (n(a.N_NUDGE_M), "tempo.nudge"), (n(a.N_METRO), "lfo.trigger"),
        (n(a.N_QUANT), "preset.next"), (n(a.N_UP), "view.bright"), (n(a.N_DOWN), "view.bright"),
        (n(a.N_RIGHT), "band.select"), (n(a.N_LEFT), "band.select"),
        (n(a.N_DEVICE_ON), "ui.panel"), (n(a.N_DETAIL), "ui.cheatsheet"),
        (n(a.N_CLIPTRACK), "audio.restart"), (n(a.N_MASTER_SEL), "overlay.on"),
        (n(a.N_PAN), "overlay.passthrough"),
    ]


def _layer_by_plan(source: str) -> str | None:
    """Plan 13 §3.2's three tables, as a rule over the control."""
    a = apc40
    kind, ch, num = source.split(":")
    num = int(num)
    if kind == "cc":
        if num in a.DEVICE_KNOBS:
            return "global"
        if num in a.TRACK_KNOBS or num == a.CC_CUE:
            return "preset"
        return None                                        # faders, MASTER, crossfader
    ch = int(ch)
    if num == a.N_CLIP[1] or (num == a.N_CLIP[2] and ch < 3):
        return "global"                                    # the band scenes
    if (num in (a.N_ACTIVATOR, *a.N_SCENE, a.N_UP, a.N_DOWN)
            or (num == a.N_CLIP[2] and ch >= 4)):
        return "preset"
    return None                                            # the invariant buttons


def test_the_default_map_is_sorted_as_plan_13_says():
    rows = [Binding.from_json(d) for d in apc40.DEFAULT_MAP]
    have = {(b.source, b.target): b.layer for b in rows}
    old = _old_map()
    assert len(old) == 113
    # plan 19 WP2: the sixteen shape pads of clip rows 4 and 5 are gone —
    # those pads are the bank's slots 9–24, invariant (the cue knob keeps
    # shape selection); the other 97 old rows are sorted as plan 13 says
    far = [f"note:{ch}:{n}" for n, ch in apc40.BANK_PADS[8:]]
    gone = [(s, "view.shape") for s in far]
    assert len(gone) == 16 and set(gone) < set(old) and not set(gone) & set(have)
    for pair in old:                                       # every old row left, sorted
        if pair in gone:
            continue
        assert pair in have, pair
        assert have[pair] == _layer_by_plan(pair[0]), pair
    new = [b for b in rows if (b.source, b.target) not in set(old)]
    # the new rows: SHIFT, invariant, and the global track knobs — which
    # are data, rows in the map: hand feel and BPM on 1–5, 6–8 free
    assert [(b.source, b.target, b.layer) for b in new] == [
        ("cc:0:48", "hands.smooth", "global"), ("cc:0:49", "hands.response", "global"),
        ("cc:0:50", "hands.catch", "global"), ("cc:0:51", "hands.sel.return", "global"),
        ("cc:0:52", "tempo.bpm", "global"),
        (routing.SHIFT_SOURCE, routing.SHIFT_PARAM, None),
        # clip rows 4 and 5: the bank's slots 9–24, invariant (plan 19 WP2)
        *[(s, "preset.select", None) for s in far],
        # the clip-stop row: one SAVE AS bar (plan 15 WP4)
        *[(f"note:{k}:{apc40.N_CLIPSTOP}", "preset.save_new", None) for k in range(8)],
        (f"note:0:{apc40.N_OVERDUB}", "preset.home", None)]   # home (plan 15 WP2)
    assert not [b for b in rows if b.layer == "global" and b.number in (0x35, 0x36, 0x37)
                and b.kind == "cc"]
    assert not [b for b in rows if b.layer == "preset" and b.kind == "cc"
                and b.number in apc40.DEVICE_KNOBS]
    # QUANT is invariant (plan 13 §3.2's note), and so is the preset row
    assert have[(f"note:0:{apc40.N_QUANT}", "preset.next")] is None
    assert {have[(f"note:{k}:{apc40.N_CLIP[0]}", "preset.select")] for k in range(8)} == {None}
    assert [(b.source, b.value) for b in rows if b.target == "preset.select"] == [
        (f"note:{ch}:{n}", float(k)) for k, (n, ch) in enumerate(apc40.BANK_PADS)]
    # the factory file carries the layers
    doc = json.loads(routing.FACTORY_FILE.read_text())
    assert {"source": "cc:0:52", "target": "tempo.bpm", "op": "abs", "feedback": "ring",
            "layer": "global"} in doc["bindings"]


def test_an_old_bindings_file_gets_its_layers_once_with_a_backup(tmp_path, capsys):
    path = bindings_path(tmp_path)
    hand = path.with_name("bindings.json.bak-mine")
    hand.write_text("mine")
    v2 = {"schema": routing.SCHEMA_V2, "profile": "apc40",      # every row: the preset layer too
          "bindings": [b.to_json() for b in Bindings.factory().bindings]}
    v2["schema"] = routing.SCHEMA_V2
    new = {"hands.smooth", "hands.response", "hands.catch", "hands.sel.return", "tempo.bpm",
           routing.SHIFT_PARAM}
    v2["bindings"] = [{k: v for k, v in b.items() if k != "layer"} for b in v2["bindings"]
                      if b["target"] not in new]
    v2["bindings"] += [
        {"source": "cc:0:7", "target": "view.speed", "op": "abs"},          # on fader 1
        {"source": "cc:0:87", "target": "view.inst_amp", "op": "abs"},      # a knob of mine
        {"source": f"note:0:{SHIFT}", "target": "view.points", "op": "toggle"},  # on SHIFT
    ]
    v2["bindings"] = [b for b in v2["bindings"]
                      if not (b["source"] == "cc:0:7" and b["target"] == "band.0.post")]
    path.write_text(json.dumps(v2))
    t = Bindings.load(path, legacy_midi=None)
    # the sort is in memory; the file, holding preset-layer rows, is the
    # first-launch migration's to rewrite (plan 13 WP5): it keeps them in
    # a preset first, then backs the file up and writes the session's part
    assert capsys.readouterr().err == "" and t.carried is not None
    from test_routing import migrate_home
    migrate_home(tmp_path, t)
    err = capsys.readouterr().err
    layer = {(b.source, b.target): b.layer for b in t.midi()}
    assert layer[("cc:*:16", "band.sel.trim")] == "global"        # identical: the factory's
    assert layer[("cc:0:48", "view.bright")] == "preset"
    assert layer[(f"note:0:{apc40.N_TAP}", "tempo.tap")] is None
    assert layer[("cc:0:7", "view.speed")] is None                # mine, on an invariant control
    assert layer[("cc:0:87", "view.inst_amp")] == "preset"        # mine, anywhere else
    for pid in new:                                               # the global rows and SHIFT added
        assert any(b.target == pid for b in t.midi()), pid
    # a row of mine on SHIFT's note would keep the latch off: dropped, noted
    # (review of PR #63), and SHIFT is the latch
    assert [b.target for b in t.dispatch("note", 0, SHIFT)] == [routing.SHIFT_PARAM]
    assert any("SHIFT is the desk's layer latch" in n for n in t.notes)
    assert "sorted" in err and "kept as bindings.json.bak-v2" in err
    assert json.loads(path.with_name("bindings.json.bak-v2").read_text()) == v2
    assert hand.read_text() == "mine"
    doc = json.loads(path.read_text())
    assert doc["schema"] == routing.SCHEMA and doc == t.to_json()
    # once: the second load finds a schema-3 file and says nothing
    again = Bindings.load(path, legacy_midi=None)
    assert again.to_json() == t.to_json() and not again.changed
    assert capsys.readouterr().err == ""
    assert sorted(p.name for p in tmp_path.glob("bindings.json.bak-*")) == [
        "bindings.json.bak-mine", "bindings.json.bak-v2"]


# ------------------------------------------------------ plan 15 WP1: undo

def test_undoing_a_desk_row_redraws_and_keeps_the_layer_and_the_faders_catch(tmp_path):
    """`Bindings.set_desk(load=False)`, what an undo's restore calls: the
    preset layer is replaced and the desk redrawn (`redraw_serial`), but
    nothing was loaded — `desk_serial` stays, the layer that is up stays
    up, and every fader keeps its catch (D7). `load=True`, the default, is
    still a preset load's: the layer drops and the catch is cleared."""
    from test_undo import boot, frames, settle

    from hyperspace import undo

    r = boot(tmp_path / "home")
    t, reg, u = r.table, r.reg, r.undo
    reg["band.2.post"].set_norm(0.5)
    frames(r)
    r.inp.queue.append(cc(apc40.CC_FADER, 64, channel=2))
    frames(r)
    fader = next(b for b in t.midi() if b.target == "band.2.post")
    assert fader.caught and fader.layer is None
    settle(r)
    u.clear()
    knob = next(b for b in t.desk() if b.kind == "cc" and b.feedback == "ring")
    was = [b.to_json() for b in t.desk()]
    undo.push("unmap a knob")                          # the ROUTING page's ×
    t.remove(knob)
    t.redraw_serial += 1
    settle(r)
    assert len(u.stack) == 1 and knob.control not in {b.control for b in t.active()}
    # SHIFT latched: the global layer is up when the undo comes
    r.inp.queue += [note(SHIFT), note(SHIFT, 0)]
    frames(r)
    assert t.layer == "global"
    serials = (t.desk_serial, t.layer_serial, t.redraw_serial)
    r.out.sent.clear()
    assert u.undo()
    assert [b.to_json() for b in t.desk()] == was
    assert (t.desk_serial, t.layer_serial) == serials[:2] and t.redraw_serial == serials[2] + 1
    assert t.layer == "global" and fader.caught
    frames(r)                                          # the adapter follows: a redraw…
    assert r.out.sent and t.layer == "global" and fader.caught      # …and nothing dropped
    r.inp.queue.append(cc(apc40.CC_FADER, 30, channel=2))
    frames(r)
    assert reg["band.2.post"].norm == pytest.approx(30 / 127, abs=PICKUP_TOL)   # still caught
    # back on the preset layer the restored knob is drawn again
    r.inp.queue += [note(SHIFT), note(SHIFT, 0)]
    r.out.sent.clear()
    frames(r)
    row = next(b for b in t.desk() if b.source == knob.source)
    assert sent_cc(r, row.number, row.channel or 0)[-1:] == [round(reg[row.target].norm * 127)]
    # the same rows through the default door are a load: the layer drops, and a
    # fader whose base the load moved loses its catch (plan 15 WP3's rule)
    r.inp.queue += [note(SHIFT), note(SHIFT, 0)]
    frames(r)
    assert t.layer == "global"
    reg["band.2.post"].set_norm(0.9)
    t.set_desk(t.desk())
    frames(r)
    assert t.layer == "preset" and t.desk_serial == serials[0] + 1 and not fader.caught
    # the dropping rules are the same under both: a row on an invariant control goes
    notes = t.set_desk([*t.desk(), Binding(fader.source, "view.bright", "abs")], load=False)
    assert len(notes) == 1 and "invariant" in notes[0]
    assert [b.to_json() for b in t.desk()] == was


# ------------------------------------------------------- plan 15 WP2: home

def test_overdub_is_home_on_both_layers_and_is_lit(rig):
    """Decision 27, D6 as the owner extended it: OVERDUB loads the show's
    "starts on" preset — one invariant row, the same press on either
    layer, which no preset's desk may map — and its LED is lit while the
    show names one, dark when it names none. Home is a load: it drops to
    the preset layer (D4)."""
    t, proj = rig.midi.table, rig.presets
    lib, n = proj.lib, apc40.N_OVERDUB
    (b,) = t.route("note", 0, n)
    assert (b.target, b.op, b.layer, b.feedback) == ("preset.home", "toggle", None, "led")
    assert t.is_invariant(Binding(b.source, "view.points", "toggle", layer="preset"))
    assert apc40.glyph(b.source) == "B11"
    assert proj.startup == "TUMBLE"
    rig.midi.poll()
    assert sent_notes(rig, n)[-1] == 1                              # lit: there is a home
    # the preset layer
    push(rig, note(apc40.N_CLIP[0], channel=4), note(apc40.N_CLIP[0], 0, channel=4))
    assert lib.current("presets") == "TRIP" and t.layer == "preset"
    push(rig, note(n), note(n, 0))
    assert lib.current("presets") == "TUMBLE" and proj.active == 0
    assert sent_notes(rig, n)[-1] == 1                              # still lit after the release
    # the global layer: the same press, and the load drops the layer
    push(rig, note(apc40.N_CLIP[0], channel=6), note(apc40.N_CLIP[0], 0, channel=6))
    assert lib.current("presets") == "MANDALA"
    shift(rig)
    assert t.layer == "global" and len(t.route("note", 0, n)) == 1
    push(rig, note(n), note(n, 0))
    assert lib.current("presets") == "TUMBLE" and t.layer == "preset"
    assert sent_notes(rig, SHIFT)[-1] == 0
    # no preset may map it: a desk row on OVERDUB is dropped with a note
    notes = t.set_desk([{"source": f"note:0:{n}", "target": "view.points", "op": "toggle",
                         "feedback": "led"}])
    said = f"dropped note:0:{n} → view.points: that control is invariant, the session's"
    assert notes == [f"{said} (plan 13 D6)"]
    assert [x.target for x in t.route("note", 0, n)] == ["preset.home"]
    # no "starts on": dark, and a press loads nothing and says so
    push(rig, note(apc40.N_CLIP[0], channel=4), note(apc40.N_CLIP[0], 0, channel=4))
    proj.startup = None
    rig.midi.poll()
    assert sent_notes(rig, n)[-1] == 0
    push(rig, note(n))
    assert lib.current("presets") == "TRIP" and lib.warning.startswith("home: this show names no")
    push(rig, note(n, 0))
    assert sent_notes(rig, n)[-1] == 0                              # the echo ends with the press
    proj.startup = "TUMBLE"
    rig.midi.poll()
    assert sent_notes(rig, n)[-1] == 1


# ------------------------------------------- plan 15 WP4: the SAVE AS bar

def test_the_clip_stop_row_is_invariant(rig):
    """Decision 29, D6 as the owner extended it: the eight clip-stop
    buttons are one SAVE AS bar — eight invariant `hold` rows on
    `preset.save_new`, the same on both layers, which no Learn takes and
    no preset's desk may map."""
    t, pr, m = rig.midi.table, rig.presets, rig.midi
    lib, n = pr.lib, apc40.N_CLIPSTOP
    now = [0.0]
    m.clock = lambda: now[0]

    def hold(channel):
        push(rig, note(n, channel=channel))
        now[0] += 0.7
        rig.midi.poll()                                      # held 0.7 s: it saves here
        push(rig, note(n, 0, channel=channel))
        now[0] += 5.0
        rig.midi.poll()

    for k in range(8):
        (b,) = t.route("note", k, n)
        assert (b.target, b.op, b.layer, b.feedback, b.on, b.off) \
            == ("preset.save_new", "hold", None, "led", 1, 0)
        assert t.is_invariant(Binding(b.source, "view.points", "toggle", layer="preset"))
        assert apc40.glyph(b.source) == f"G6·{k + 1}"
        assert b in t.active()
    assert "hold" in routing.OPS and "hold" not in routing.MOD_OPS
    # the preset layer, then the global one: the same hold, the same save
    push(rig, note(apc40.N_CLIP[0], channel=4), note(apc40.N_CLIP[0], 0, channel=4))
    assert lib.current("presets") == "TRIP" and t.layer == "preset"
    hold(0)
    assert lib.current("presets") == "TRIP 2"
    shift(rig)
    assert t.layer == "global" and len(t.dispatch("note", 3, n)) == 1
    assert all(b in t.active() for b in t.midi() if b.op == "hold")
    hold(3)
    assert lib.current("presets") == "TRIP 3"
    assert t.layer == "global"                               # a save is no load: the layer stays
    shift(rig)
    # no Learn takes it. Plan 17 fork 6: an invariant control is not a
    # candidate at all — a press while a learn is armed does its own job
    # (the hold saves) and the learn stays armed; and the road a click
    # takes (`Learn.learn_control`) refuses it, still armed, nothing bound
    rows = [(b.to_json(), b.layer) for b in t.bindings]
    m.learner.arm("view.depth4", "desk")
    hold(5)
    assert m.learner.learning == "view.depth4" and not m.learner.refused
    assert lib.current("presets") == "TRIP 4"
    assert [(b.to_json(), b.layer) for b in t.bindings] == rows
    assert not m.learner.learn_control(f"note:5:{n}", apc40)
    assert m.learner.learning == "view.depth4" and m.learner.refused
    assert m.learner.last == "G6·6 (clip stop 6) is invariant (the session's) — not learned"
    assert [(b.to_json(), b.layer) for b in t.bindings] == rows
    m.learner.arm(None)
    # no preset may map it: a desk row on any of the eight is dropped with a note
    notes = t.set_desk([{"source": f"note:{k}:{n}", "target": "view.points", "op": "toggle",
                         "feedback": "led"} for k in (0, 7)])
    assert notes == [f"dropped note:{k}:{n} → view.points: that control is invariant, the "
                     "session's (plan 13 D6)" for k in (0, 7)]
    assert all([x.target for x in t.route("note", k, n)] == ["preset.save_new"] for k in range(8))
    # no factory preset's desk names the row
    for name in lib.list("presets"):
        desk = lib.read("presets", name).get("desk") or []
        assert not [d for d in desk if d["source"].endswith(f":{n}")
                    and d["source"].startswith("note:")], name


# ------------------------------------------- plan 18 WP2: knob smoothing

def test_a_layer_switch_leaves_a_glide_to_finish(rig):
    """A glide belongs to the param, not to the control: SHIFT latched
    mid-glide redraws the desk for the global layer — the knob's ring now
    shows the global row's base — and the preset-layer param still arrives
    on its detent. Back on the preset layer its ring shows where it landed;
    a redraw during a glide shows the glide's target."""
    from test_midi import K_MIX, TICK, slew_rig

    reg, t = rig.reg, rig.midi.table
    mix, ret = reg["view.pattern_mix"], reg["hands.sel.return"]
    assert row(rig, "hands.sel.return", "global").number == K_MIX
    mix.set_norm(0.0)
    at = slew_rig(rig)
    at(TICK, cc(K_MIX, 127))
    at(2 * TICK)
    mid = mix.norm
    rig.out.sent.clear()
    at(3 * TICK, note(SHIFT), note(SHIFT, 0))       # the global layer, mid-glide
    assert t.layer == "global" and mid < mix.norm < 1.0 and mix.id in rig.midi._slews
    assert sent_cc(rig, K_MIX)[-1] == round(ret.norm * 127)       # the new layer's ring
    was = ret.norm
    for k in range(4, 9):
        at(k * TICK)
        assert mix.norm > mid
        mid = mix.norm
    at(9 * TICK)
    assert mix.norm == 1.0 and rig.midi._slews == {} and ret.norm == was
    rig.out.sent.clear()
    at(10 * TICK, note(SHIFT), note(SHIFT, 0))      # back: the ring shows where it landed
    assert t.layer == "preset" and sent_cc(rig, K_MIX)[-1] == 127
    # a redraw with a glide in flight draws the target, not the base on its way
    at(11 * TICK, cc(K_MIX, 0))
    rig.out.sent.clear()
    at(12 * TICK, note(SHIFT), note(SHIFT, 0))
    at(13 * TICK, note(SHIFT), note(SHIFT, 0))
    assert 0.0 < mix.norm < 1.0 and sent_cc(rig, K_MIX)[-1] == 0
    for k in range(14, 24):
        at(k * TICK)
    assert mix.norm == 0.0


def test_a_preset_load_stops_a_glide_on_a_performance_param_and_not_on_the_dim(tmp_path):
    """D2 and D9, mid-glide. A real preset load (the host's objects,
    tests/test_undo.py's boot): the knob's glide on a performance param is
    dropped and the load's value stands; the crossfader's glide on
    `output.dim`, a session param no preset moves, goes on arriving and
    the fader keeps its hold. A desk replacement that leaves the value
    where the glide last wrote it (the load's value happens to equal it)
    still ends the glide."""
    from test_undo import boot, frames

    r = boot(tmp_path / "home")
    r.midi.clock = lambda: r.t
    reg, t, slews = r.reg, r.table, r.midi._slews
    reg["desk.slew"].set(routing.SLEW_MAX_S)        # fifteen frames

    def knob():
        return next(b for b in t.active() if b.kind == "cc" and b.op == "abs"
                    and b.feedback == "ring" and b.layer == "preset"
                    and not reg[b.target].integer)

    dim = reg["output.dim"]
    xfade = next(b for b in t.midi() if b.target == "output.dim")
    r.inp.queue.append(cc(apc40.CC_XFADE, 127))     # brought up to full: caught
    frames(r, 20)
    assert xfade.caught and dim.value == 1.0 and not slews
    k = knob()
    p = reg[k.target]
    r.inp.queue += [cc(k.number, 0 if p.norm > 0.5 else 127, k.channel or 0),
                    cc(apc40.CC_XFADE, 0)]
    frames(r, 3)
    assert set(slews) == {p.id, "output.dim"}
    assert r.lib.current("presets") == "TUMBLE"
    r.presets.load("TRIP")                          # mid-glide
    loaded, dim_mid = p.base, dim.norm
    frames(r)
    assert set(slews) == {"output.dim"} and p.base == loaded and dim.norm < dim_mid
    frames(r, 20)
    assert p.base == loaded                         # the load's value stands
    assert dim.value == 0.0 and xfade.caught and not slews      # the dim arrived
    # a desk replacement that moves nothing: the glide ends where it is
    k = knob()
    p = reg[k.target]
    r.inp.queue.append(cc(k.number, 0 if p.norm > 0.5 else 127, k.channel or 0))
    frames(r, 3)
    assert set(slews) == {p.id}
    here = p.base
    t.set_desk(t.desk())
    frames(r, 20)
    assert not slews and p.base == here
    assert abs(p.norm - round(p.norm)) > 0.05       # it never went on to the knob's end


# ------------------------------------------- plan 19 WP2: rows 4–5 are the bank

def _far(k: int) -> tuple[int, int]:
    """(note, channel) of slot k's pad."""
    return apc40.BANK_PADS[k]


def test_rows_four_and_five_load_slots_nine_to_twenty_four_on_both_layers(rig):
    """Clip rows 4 and 5 are the bank's slots 9–24 (the owner, 2026-10-04):
    each of the sixteen pads loads its slot with SHIFT off and with SHIFT
    on — one meaning on both layers — and the load drops the desk to the
    preset layer (D4), as a pad of row 1 does. The desk's count is
    `apc40.BANK_PADS`, as long as the bank. An empty slot's pad loads
    nothing and says the slot is empty (D8), as row 1 does."""
    from hyperspace import library

    t, pr, lib = rig.midi.table, rig.presets, rig.presets.lib
    assert len(apc40.BANK_PADS) == library.SLOTS == len(pr.bank) == 24
    assert apc40.BANK_PADS[:8] == [(apc40.N_CLIP[0], k) for k in range(8)]
    assert apc40.BANK_PADS[8:16] == [(apc40.N_CLIP[3], k) for k in range(8)]
    assert apc40.BANK_PADS[16:] == [(apc40.N_CLIP[4], k) for k in range(8)]
    names = [n for n in lib.list("presets")][:16]
    assert len(set(names)) == 16
    for k, name in zip(range(8, 24), names):
        pr.put_slot(k, name)
    for under_shift in (False, True):
        for k, name in zip(range(8, 24), names):
            n, ch = _far(k)
            if under_shift:
                shift(rig)
                assert t.layer == "global"
            (b,) = t.dispatch("note", ch, n)                   # one row, whichever layer is up
            assert (b.target, b.op, b.value, b.layer) == ("preset.select", "set", float(k), None)
            push(rig, note(n, channel=ch), note(n, 0, channel=ch))
            assert (pr.active, lib.current("presets")) == (k, name), (k, under_shift)
            assert t.layer == "preset"                         # a load drops the layer (D4)
            assert apc40.glyph(b.source) == f"G{4 + (k - 8) // 8}·{(k - 8) % 8 + 1}"
    # an empty slot: dark, and a press says so and loads nothing
    pr.clear_slot(11)
    was = lib.current("presets")
    for under_shift in (False, True):
        if under_shift:
            shift(rig)
        n, ch = _far(11)
        push(rig, note(n, channel=ch), note(n, 0, channel=ch))
        assert lib.warning == "slot 12: an empty slot" and lib.current("presets") == was
        assert sent_notes(rig, n, ch)[-1] == 0
        lib.warning = ""
    # shape selection left these rows for the cue knob (relative, every shape)
    assert not [b for b in t.midi() if b.target == "view.shape" and b.kind == "note"]
    (cue,) = [b for b in t.midi() if b.target == "view.shape"]
    assert (cue.source, cue.op, cue.layer) == (f"cc:0:{apc40.CC_CUE}", "rel", "preset")


def test_the_bank_pads_are_invariant(rig):
    """D6, extended by the owner to clip rows 4 and 5: every bank pad is a
    row with no layer — active on both layers, never Learn's, never a
    preset's. A Learn on one is refused in the existing words (through a
    press, which does its own job, and through `learn_control`, a click's
    road); a preset's row on one is dropped with the existing note."""
    t, pr, m = rig.midi.table, rig.presets, rig.midi
    lib = pr.lib
    for k, (n, ch) in enumerate(apc40.BANK_PADS):
        (b,) = t.route("note", ch, n)
        assert (b.target, b.op, b.value, b.layer, b.feedback, b.on, b.off) \
            == ("preset.select", "set", float(k), None, "led", apc40.GREEN, 0)
        assert t.is_invariant(Binding(b.source, "view.points", "toggle", layer="preset"))
        assert b in t.active()
    shift(rig)
    assert all(b in t.active() for b in t.midi() if b.target == "preset.select")
    shift(rig)
    # no Learn takes one: a press while a learn is armed loads its slot and
    # the learn stays armed; `learn_control` refuses, nothing bound
    n, ch = _far(8)                                           # slot 9: TRACER in the party show
    rows = [(b.to_json(), b.layer) for b in t.midi() if b.layer != "preset"]
    m.learner.arm("view.depth4", "desk")
    push(rig, note(n, channel=ch), note(n, 0, channel=ch))
    assert lib.current("presets") == pr.bank[8] == "TRACER"
    assert m.learner.learning == "view.depth4" and not m.learner.refused
    for k, said in ((8, "G4·1 (clip 4·1)"), (15, "G4·8 (clip 4·8)"), (16, "G5·1 (clip 5·1)"),
                    (23, "G5·8 (clip 5·8)")):
        n, ch = _far(k)
        assert not m.learner.learn_control(f"note:{ch}:{n}", apc40)
        assert m.learner.refused and m.learner.learning == "view.depth4"
        assert m.learner.last == f"{said} is invariant (the session's) — not learned"
    m.learner.arm(None)
    # a pick-to-map on one is refused in the same words
    n, ch = _far(20)
    m.learner.pick(f"note:{ch}:{n}")
    assert not m.learner.map_picked("view.speed", apc40)
    assert m.learner.last == "G5·5 (clip 5·5) is invariant (the session's) — not learned"
    m.learner.pick(None)
    # no preset may map one: a desk row on any of them is dropped with the note
    # (a row that is not one of the sixteen old factory shape rows)
    want = [(k, _far(k)) for k in (8, 23)]
    notes = t.set_desk([{"source": f"note:{ch}:{n}", "target": "view.points", "op": "toggle",
                         "feedback": "led"} for _k, (n, ch) in want])
    assert notes == [f"dropped note:{ch}:{n} → view.points: that control is invariant, the "
                     "session's (plan 13 D6)" for _k, (n, ch) in want]
    assert [(b.to_json(), b.layer) for b in t.midi() if b.layer != "preset"] == rows
    # no factory preset's desk names a pad of rows 4 or 5
    for name in lib.list("presets"):
        desk = lib.read("presets", name).get("desk") or []
        assert not [d for d in desk if d["source"].startswith("note:")
                    and int(d["source"].rsplit(":", 1)[1]) in apc40.N_CLIP[3:]], name
