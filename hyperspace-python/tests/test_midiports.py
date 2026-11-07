"""Looking for MIDI ports (audit R15, register row 791): CoreMIDI's refusal stays
a sentence and never reaches RtMidi, whose answer to it is an abort."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import mido
import pytest

from hyperspace import bridge, midi, midiports
from hyperspace.midiports import REFUSED_RETRY_S, port_names

HERE = Path(__file__).resolve().parent.parent / "hyperspace"
REFUSED = -10844            # kMIDIServerStartErr, as one such answer


class Clock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture()
def refused(monkeypatch):
    """CoreMIDI says no; anything that would reach RtMidi fails the test (there it
    would abort the process). The count of what was asked of CoreMIDI."""
    asked = []

    def create() -> int:
        asked.append(1)
        return REFUSED

    def reached(*a, **k):
        pytest.fail("reached RtMidi while CoreMIDI refuses")
    monkeypatch.setattr(midiports, "_create_client", create)
    for fn in ("get_input_names", "get_output_names", "open_input", "open_output"):
        monkeypatch.setattr(mido, fn, reached)
    return asked


def test_a_refused_client_is_a_sentence_and_rtmidi_is_never_reached(refused):
    seen = port_names()
    assert seen.inputs == [] and seen.outputs == []
    assert seen.why == f"CoreMIDI refused a client ({REFUSED})"


def test_a_refused_client_is_asked_for_again_slowly_however_often_it_is_called(refused, monkeypatch):
    clock = Clock()
    for _ in range(60):                     # a panel, once a second
        port_names(clock)
        clock.t += 1.0
    assert len(refused) == 1 + 60 // int(REFUSED_RETRY_S) - (60 % int(REFUSED_RETRY_S) == 0)
    # CoreMIDI comes back: the next ask lands, and it is never asked again
    monkeypatch.setattr(midiports, "_create_client", lambda: 0)
    monkeypatch.setattr(mido, "get_input_names", lambda: ["desk"])
    monkeypatch.setattr(mido, "get_output_names", lambda: ["desk out"])
    clock.t += REFUSED_RETRY_S
    assert port_names(clock) == (["desk"], ["desk out"], "")
    monkeypatch.setattr(midiports, "_create_client", lambda: pytest.fail("asked twice"))
    assert port_names(clock) == (["desk"], ["desk out"], "")


def test_yes_is_asked_for_once_and_every_look_lists_afresh(monkeypatch):
    """Hot plug: no look is kept, so a port plugged in shows at the next one."""
    asked, names = [], ["one"]
    monkeypatch.setattr(midiports, "_create_client", lambda: asked.append(1) or 0)
    monkeypatch.setattr(mido, "get_input_names", lambda: list(names))
    assert port_names().inputs == ["one"]
    names.append("two")
    assert port_names().inputs == ["one", "two"]
    assert len(asked) == 1


def test_no_client_framework_is_no_midi_and_no_crash(monkeypatch):
    def gone():
        raise OSError("no CoreMIDI")
    monkeypatch.setattr(midiports, "_create_client", gone)
    assert port_names().why == "OSError: no CoreMIDI"


def test_a_broken_backend_is_a_sentence_too(monkeypatch):
    def boom():
        raise RuntimeError("no MIDI backend")
    monkeypatch.setattr(mido, "get_input_names", boom)
    assert port_names() == ([], [], "RuntimeError: no MIDI backend")


def test_a_port_going_away_lists_as_none_and_is_left_out(monkeypatch):
    """RtMidi names an endpoint it is losing None (seen on the Mac): `find_port` lowers
    every name it is handed."""
    monkeypatch.setattr(mido, "get_input_names", lambda: [None, "desk"])
    monkeypatch.setattr(mido, "get_output_names", lambda: [None])
    assert port_names() == (["desk"], [], "")


def test_ports_open_nothing_while_coremidi_refuses_and_say_why(refused):
    p = midi.Ports("desk", "desk", clock=Clock())
    assert not p.connect() and not p.on
    assert p.error == f"CoreMIDI refused a client ({REFUSED})"


def test_the_bridges_out_port_opens_nothing_and_makes_no_virtual_port(refused):
    assert bridge._open_out("Hands") == (None, f"out 'Hands': CoreMIDI refused a client ({REFUSED})", False)


def test_only_midiports_lists_ports_and_only_two_modules_open_one():
    """A new caller of mido's lists or a new open would go round the gate; the one
    thing the first RtMidi object can do is abort. (tools/midi_probe.py is a separate
    process run by hand: its abort costs nothing.)"""
    lists, opens = set(), set()
    for path in HERE.rglob("*.py"):
        text = path.read_text()
        name = path.relative_to(HERE).as_posix()
        if re.search(r"\bmido\.get_\w+_names\b|^\s*(import|from) rtmidi|\brtmidi\.Midi", text, re.MULTILINE):
            lists.add(name)
        if re.search(r"\bmido\.open_\w+\(", text):
            opens.add(name)
    assert lists == {"midiports.py"}
    assert opens == {"midi.py", "bridge.py"}


@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("sandbox-exec"), reason="a Mac's CoreMIDI")
def test_a_real_refusal_is_a_sentence_and_the_process_lives():
    """The real thing, in a process of its own: a sandbox keeps it from the MIDI server, so
    CoreMIDI truly refuses and no port of this machine is reached. Bare RtMidi dies here
    (exit 134, by hand on 2026-11-06); a change to either side shows up as this failing."""
    deny = '(version 1)(allow default)(deny mach-lookup (global-name-regex #"midi"))'
    code = "from hyperspace.midiports import port_names as p; s = p(); print(s.why); print(s.inputs)"
    got = subprocess.run(["sandbox-exec", "-p", deny, sys.executable, "-c", code], text=True,
                         capture_output=True, timeout=60, cwd=HERE.parent, check=False)
    if "sandbox_apply" in got.stderr:
        pytest.skip("already in a sandbox: " + got.stderr[:80])
    assert got.returncode == 0, got.stderr
    assert "CoreMIDI refused a client" in got.stdout and "[]" in got.stdout
