# ruff: noqa: F811 — `rig` is test_midi's fixture, taken as each test's argument
"""The owner's APC40 findings of 2026-10-16, reproduced with the fake port.

The owner's session file is copied to tests/fixtures/desk-findings/ (its
MIDI rows are the factory map's session part, row for row). Every symptom
of the report — the activator row (G8) taking two presses to go off and
one to go on, the solo row (G9) that never goes dark while the rec-arm
row (G10) lights and darkens press by press, track select (G7) and
MASTER select that do nothing the app sees, QUANT (B10) dead — is what
the APC40 does in its **Generic mode** (0x40, Akai's protocol rev 1, the
"Mode 0 Button Type" column): ACTIVATOR, SOLO, RECORD ARM, PAN, SEND A–C
and the four left device buttons are toggles kept in the device (one
message a press: note-on when it turns on, note-off when it turns off),
TRACK SELECTION and MASTER send nothing, and the eight device buttons
(CLIP/TRACK … METRONOME) and knobs send on the channel of the track the
device itself selected. The app puts the device in Alternate Ableton mode
(0x42) when the port opens, where every button is momentary; a device
that fell back to Generic mode under a running app (it starts in Mode 0
whenever it powers up) was never put back.

`Apc40` below plays the device in either mode, from the protocol table:
the LED the host sent is the toggle's state, as on the owner's desk (the
only reading that gives the owner's two-presses-off, one-press-on).
"""

import json
import shutil
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace

import mido
import pytest
from test_midi import FakeIn, FakeOut, note, push, rig  # noqa: F401 — the fixture

from hyperspace import apc40, hands, lfo, tempo
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.library import Library
from hyperspace.midi import MidiIO
from hyperspace.overlay import Output
from hyperspace.params import build_registry
from hyperspace.preset import Presets
from hyperspace.routing import Binding, Router
from hyperspace.view import ViewState

OWNER = Path(__file__).parent / "fixtures" / "desk-findings" / "owner-bindings.json"
ACT, SOLO, ARM = apc40.N_ACTIVATOR, apc40.N_SOLO, apc40.N_ARM

# Akai's "Mode 0 Button Type" column: the toggles the device keeps itself,
# and the buttons that send nothing
MODE0_TOGGLE = {apc40.N_ARM, apc40.N_SOLO, apc40.N_ACTIVATOR, apc40.N_CLIPTRACK,
                apc40.N_DEVICE_ON, apc40.N_DEV_L, apc40.N_DEV_R, apc40.N_PAN,
                apc40.N_SEND_A, apc40.N_SEND_B, apc40.N_SEND_C}
MODE0_SILENT = {apc40.N_SELECT, apc40.N_MASTER_SEL}
BANKED = range(apc40.N_CLIPTRACK, apc40.N_METRO + 1)


class Apc40:
    """The device's side of the cable, in Generic (0x40) or Alternate
    Ableton (0x42) mode — the mode is the last intro SysEx the host sent
    after `mode` was forced (a power-up puts it in 0x40). A Mode-0 toggle
    flips its own state on a press and sends it; a light the host sends
    sets that state (the owner's desk: two presses off, one press on)."""

    def __init__(self, r, mode=apc40.MODE_GENERIC):
        self.r, self.mode, self.track = r, mode, 0
        self.state: dict = {}
        self._seen = 0
        self._follow()
        self.mode = mode

    def _follow(self):
        for m in self.r.out.sent[self._seen:]:
            if m.type == "sysex" and list(m.data)[:6] == [0x47, 0x7F, 0x73, 0x60, 0, 4]:
                self.mode = list(m.data)[6]
            elif m.type == "note_on":               # a light sent is the toggle's state
                self.state[(m.note, m.channel)] = m.velocity > 0
        self._seen = len(self.r.out.sent)

    def press(self, n, ch=0):
        self._follow()
        if self.mode != apc40.MODE_GENERIC:
            push(self.r, note(n, 127, ch), note(n, 0, ch))
        elif n in MODE0_SILENT:
            if n == apc40.N_SELECT:
                self.track = ch               # banks the device section, locally
        elif n in MODE0_TOGGLE:
            on = self.state[(n, ch)] = not self.state.get((n, ch), False)
            push(self.r, note(n, 127 if on else 0, ch))
        else:
            ch = self.track if n in BANKED else ch
            push(self.r, note(n, 127, ch), note(n, 0, ch))
        self._follow()


def owner_rig(tmp_path):
    """test_midi's rig on the owner's session file and a factory preset
    (its desk holds the activator row, as every factory preset's does)."""
    shutil.copy(OWNER, tmp_path / "bindings.json")
    chain = Analyzer(Analyser())
    control = Control(chain)
    audio = SimpleNamespace(chain=chain)
    view = ViewState()
    lib = Library(tmp_path)
    reg = build_registry(view, control, audio, lib.project)
    lib.attach(reg)
    reg.toggle("ui.panel", "Panel", lambda: True, lambda v: None)
    reg.toggle("ui.cheatsheet", "Sheet", lambda: True, lambda v: None)
    reg.trigger("audio.restart", "Restart", lambda: None)
    reg.trigger("audio.stop", "Stop", lambda: None)
    reg.toggle("audio.play", "Play", lambda: False, lambda v: None)
    Output(None, None).register(reg)
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    hands.register(reg, hands.HandSettings.from_config({}))
    inp, out = FakeIn(), FakeOut()
    t = [100.0]
    m = MidiIO(reg, path=tmp_path / "bindings.json", inp=inp, out=out, clock=lambda: t[0])
    presets = Presets(lib, reg, Router(reg, m.table))
    presets.load("party-tumble")
    m.poll()
    return SimpleNamespace(reg=reg, view=view, control=control, lib=lib, midi=m,
                           inp=inp, out=out, t=t)


def intros(r) -> list[int]:
    return [list(m.data)[6] for m in r.out.sent if m.type == "sysex"]


def test_the_owners_file_holds_the_factory_session_rows_and_nothing_else():
    """No stale, duplicated or conflicting row: every MIDI row of the
    owner's file is a factory map row (the session part); what the
    factory has beyond it is the preset layer, which lives in presets."""
    own = json.loads(OWNER.read_text())["bindings"]

    def key(r):
        return (r["source"], r["target"], r.get("op"), float(r.get("value", 1.0)),
                r.get("layer"))
    mine = {key(r) for r in own if r["source"].split(":")[0] in ("cc", "note")}
    factory = {key(r) for r in apc40.DEFAULT_MAP}
    assert mine <= factory
    assert {r[4] for r in factory - mine} == {"preset"}


def test_in_alternate_mode_the_activator_is_one_press_a_flip(tmp_path):
    r = owner_rig(tmp_path)
    dev = Apc40(r, mode=apc40.MODE_LIVE_ALT)
    xy = r.reg["view.plane.XY"]
    seen = []
    for _ in range(4):
        dev.press(ACT, 3)
        seen.append(xy.value)
    assert seen == [seen[0], not seen[0], seen[0], not seen[0]]


def test_a_desk_fallen_back_to_generic_mode_is_put_back(tmp_path):
    """The owner's G8: on, press, still on; press, off; press, on. A
    Generic-mode message the app can tell (a toggle's note-off with no
    press held, a second note-on with no release) re-sends the intro, and
    from then every press is one flip."""
    r = owner_rig(tmp_path)
    xy = r.reg["view.plane.XY"]
    xy.set(True)
    r.midi.poll()
    assert intros(r) == [apc40.MODE_LIVE_ALT]
    dev = Apc40(r)                          # the device power-cycled: Mode 0
    seen = []
    for _ in range(6):
        dev.press(ACT, 3)
        seen.append(xy.value)
    assert intros(r)[-1] == apc40.MODE_LIVE_ALT and len(intros(r)) == 2
    assert dev.mode == apc40.MODE_LIVE_ALT
    # after the first press (the one that told), each press flips it
    assert all(a != b for a, b in pairwise(seen[1:]))
    line = r.midi.desk_log.lines()
    assert any("Generic mode" in x for x in line)


def test_the_solo_row_steps_the_transfer_and_its_led_echoes_the_press(tmp_path):
    """G9 (band.{i}.fn, an enum on a toggle row: the next transfer): the
    LED is the press's echo — lit while held, dark at the release — not a
    light that once lit never goes out."""
    r = owner_rig(tmp_path)
    fn = r.reg["band.0.fn"]
    before = fn.value

    def led():
        v = [m.velocity for m in r.out.sent if m.type == "note_on"
             and m.note == SOLO and m.channel == 0]
        return v[-1]
    push(r, note(SOLO, 127, 0))
    assert led() == 1 and fn.value == (before + 1) % len(fn.names)
    push(r, note(SOLO, 0, 0))
    assert led() == 0


def test_quant_sent_on_a_banked_channel_still_steps_the_bank(tmp_path):
    """B10: in Generic mode QUANT comes on the channel of the track the
    device selected; it is read as the one button it is (channel 0 in
    Alternate mode) — and it tells the app the desk fell back."""
    r = owner_rig(tmp_path)
    bank = r.lib.project
    dev = Apc40(r)
    dev.press(apc40.N_SELECT, 2)            # nothing reaches the app: the device banks
    was = bank.active
    dev.press(apc40.N_QUANT)
    assert bank.active != was
    assert intros(r)[-1] == apc40.MODE_LIVE_ALT and len(intros(r)) == 2


def test_a_learn_on_a_toggle_button_is_no_sign_of_generic_mode(rig):
    """The release of a press a desk learn took is not a note-off with
    no press: it puts nothing back and does nothing."""
    rig.midi.learner.arm("view.points")
    push(rig, note(SOLO, 127, 2), note(SOLO, 0, 2))
    assert len(intros(rig)) == 1


def test_the_re_entry_is_rate_limited(tmp_path):
    r = owner_rig(tmp_path)
    for _ in range(3):
        push(r, note(ARM, 0, 1))            # three note-offs with no press
    assert len(intros(r)) == 2


@pytest.mark.parametrize("ch", [1, 7])
def test_a_device_knob_on_a_track_channel_tells_too(tmp_path, ch):
    r = owner_rig(tmp_path)
    push(r, mido.Message("control_change", channel=ch, control=0x10, value=5))
    assert len(intros(r)) == 2


def test_the_diagram_says_what_the_band_rows_and_the_corner_do(rig):
    from hyperspace import ui_desk
    reg = rig.reg
    text = ui_desk.text
    sub = reg["band.select"].names[0]
    assert text(reg, Binding("note:0:51", "band.select", "set", 0.0)) == f"band {sub}"
    fn = reg["band.0.fn"]
    assert text(reg, Binding("note:0:49", "band.0.fn", "toggle")) == \
        f"{fn.label}: next ({fn.text()})"
    assert text(reg, Binding("note:0:80", "overlay.on", "toggle")) == "Overlay (if config allows)"
    assert text(reg, Binding("note:0:87", "overlay.passthrough", "toggle")) == \
        "Click-through (overlay)"
    assert text(reg, Binding("note:0:81", "scene.reset_all", "toggle")) == \
        "Reset all bands (again: undo)"
    assert text(reg, Binding("note:0:63", "preset.next", "toggle")) == "Next bank preset"
