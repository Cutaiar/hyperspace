#!/usr/bin/env python3
"""Save-as on the desk, shown headless (plan 15 WP4, decision 29).

The APC40's clip-stop row is one SAVE AS bar: any of its eight buttons
held 0.6 s saves the live state as a **new** preset, named from the
loaded one, into the next empty bank slot, whose pad blinks. A tap does
nothing; the desk never overwrites. This builds the app's objects the
way `tools/undo_demo.py` does — no window, a `MidiIO` over fake ports,
its clock the demo's own — and prints a transcript: a slot cleared, a
tap, a hold with every LED velocity the desk is sent and when, the
footer's line, the files in `<home>/presets`, a second hold onto a full
bank, two buttons held at once, the new slot's pad loading it, the
PRESETS page's "put preset here…" and "clear slot" calls, and a Learn
the bar refuses.

It always runs on a fresh temp home of its own (`undo_demo` sets
`HYPERSPACE_HOME` on import, before anything reads it, and seeds it with
the test corpus: the party show and its presets): it cannot touch
~/Hyperspace.

  uv run python tools/save_as_demo.py [--out docs/plans/assets/15-safety-net/save-as-demo.txt]

(The `--shot` of the PRESETS page's slot menu went with the page's bank
pills, 2026-10-28: the bank is the desk's now.)
"""

# ruff: noqa: I001 — undo_demo is imported first, on purpose: it sets
# HYPERSPACE_HOME to a temp home and points pyGLFW at imgui_bundle's libglfw
# before anything loads glfw
from __future__ import annotations

import json
import sys
from pathlib import Path

import undo_demo as demo
from undo_demo import frames, say, settle, stack

import mido

from hyperspace import apc40, midi
from hyperspace.library import PRESETS

STOP, PAD = apc40.N_CLIPSTOP, apc40.N_CLIP[0]


def note(n: int, vel: int = 127, channel: int = 0) -> mido.Message:
    return mido.Message("note_on" if vel else "note_off", channel=channel, note=n, velocity=vel)


def down(r, n: int, *channels: int) -> None:
    for ch in channels:
        r.ports.queue.append(note(n, channel=ch))
    frames(r)


def up(r, n: int, *channels: int) -> None:
    for ch in channels:
        r.ports.queue.append(note(n, 0, channel=ch))
    frames(r)


def tap(r, n: int, channel: int = 0) -> None:
    down(r, n, channel)
    up(r, n, channel)


def wait(r, seconds: float) -> None:
    frames(r, round(seconds / demo.DT))


def where(r) -> str:
    lib, bright = r.lib, r.reg["view.bright"]
    return (f"preset {lib.current(PRESETS)}{' •' if lib.is_dirty(PRESETS) else ''}, "
            f"{bright.label} {bright.fmt(bright.base)}")


def bank(r) -> str:
    pr = r.lib.project
    return "  ".join(f"F{k + 1} {n or '—'}{'*' if k == pr.active else ''}"
                     for k, n in enumerate(pr.bank))


def files(r) -> str:
    return ", ".join(sorted(p.name for p in (demo.HOME / "presets").glob("*.json"))) or "(none)"


def leds(r, since: int, t0: float) -> None:
    """Every LED message the desk was sent for the bar and the preset row
    since `since`, with the time since `t0`: the bar as one line when its
    eight buttons got the same velocity in the same poll."""
    by_time: dict[float, dict[tuple[int, int], int]] = {}
    for at, m in r.log[since:]:
        if m.type == "note_on" and m.note in (STOP, PAD):
            by_time.setdefault(round(at - t0, 2), {})[(m.note, m.channel)] = m.velocity
    if not by_time:
        say("      (no LED message)")
    for at, sent in by_time.items():
        parts = []
        bar = {v for (n, _ch), v in sent.items() if n == STOP}
        if len(bar) == 1 and sum(n == STOP for n, _ch in sent) == 8:
            parts.append(f"bar G6·1–8 → {bar.pop()}")
        else:
            parts += [f"G6·{ch + 1} → {v}" for (n, ch), v in sent.items() if n == STOP]
        parts += [f"pad G1·{ch + 1} → {v}" for (n, ch), v in sent.items() if n == PAD]
        say(f"      {at:5.2f} s   " + "   ".join(parts))


def footer(r) -> str:
    """The line the footer's message slot would show: the library's
    warning if it was the later one said, else its status."""
    lib = r.lib
    return f"·  {lib.warning or lib.status}"


def main() -> None:
    r = demo.boot()
    lib, proj, table = r.lib, r.lib.project, r.router.table
    r.midi.clock = lambda: r.t                        # the hold's clock: the demo's frames
    r.log = []                                        # (time, message) the desk was sent
    send = r.ports.send
    r.ports.send = lambda m: (r.log.append((r.t, m)), send(m))[1]
    show = demo.HOME / "projects" / "party.hyp.json"

    say("Hyperspace — save-as on the desk, headless (tools/save_as_demo.py; plan 15 WP4, "
        "decision 29)")
    say(f"home folder: {demo.HOME}  (a temp folder made by this script)")
    frames(r, 5)
    rows = [b for b in table.midi() if b.op == "hold"]
    say(f"show: {proj.name}   preset: {lib.current(PRESETS)}   "
        f"hold {midi.HOLD_S} s, blink {midi.BLINK_S} s")
    say(f"the bar: {len(rows)} rows, {r.midi.control_name(rows[0])} … "
        f"{r.midi.control_name(rows[-1])}  →  {rows[0].target}  op {rows[0].op}  "
        f"layer {rows[0].layer} (None: invariant)")
    say(f"bank: {bank(r)}   (* the loaded one)")
    say(f"<home>/presets: {files(r)}")
    say("LED velocities: 0 off · 1 on · 2 blink (a plain button); the clip grid: 1 green · "
        "2 green blink")

    say()
    say('1. "clear slot" on F6 (the PRESETS page\'s menu item calls Project.clear_slot)')
    proj.clear_slot(5)
    say(f"    footer: {footer(r)}")
    say(f"    bank: {bank(r)}")
    say(f"    the show's file now holds: {json.loads(show.read_text())['bank']}")
    say(f"    ACID is still a preset: {'ACID' in lib.list(PRESETS)}   <home>/presets: {files(r)}")

    say()
    say("2. TRIP (pad G1·5), an edit, then a tap on the bar: pressed 0.3 s, let go")
    tap(r, PAD, channel=4)
    settle(r)
    bright = r.reg["view.bright"]
    bright.set(bright.base * 0.5)
    settle(r)
    say(f"    before: {where(r)}")
    mark, t0 = len(r.log), r.t
    down(r, STOP, 3)
    wait(r, 0.3)
    up(r, STOP, 3)
    wait(r, 2.0)
    say("    LEDs (time since the press):")
    leds(r, mark, t0)
    say(f"    after:  {where(r)}   <home>/presets: {files(r)}")

    say()
    say("3. A hold: G6·4 down and kept down")
    mark, t0 = len(r.log), r.t
    down(r, STOP, 3)
    wait(r, 0.5)
    say(f"    at {r.t - t0:.2f} s: {where(r)}")
    wait(r, 0.2)
    say(f"    at {r.t - t0:.2f} s: {where(r)}")
    say(f"    footer: {footer(r)}")
    wait(r, 0.5)
    up(r, STOP, 3)
    say(f"    let go at {r.t - t0:.2f} s")
    wait(r, 2.0)
    say("    LEDs (time since the press):")
    leds(r, mark, t0)
    say(f"    bank: {bank(r)}")
    say(f"    the show's file now holds: {json.loads(show.read_text())['bank']}")
    say(f"    <home>/presets: {files(r)}")
    doc = json.loads((demo.HOME / "presets" / "trip-2.json").read_text())
    say(f"    trip-2.json: name {doc['name']!r}, view.bright {doc['values']['view.bright']:g} "
        f"(the edit); TRIP itself is untouched: "
        f"{lib.read(PRESETS, 'TRIP')['values']['view.bright']:g}")
    stack(r)

    say()
    say("4. A second hold, the bank now full")
    mark, t0 = len(r.log), r.t
    down(r, STOP, 0)
    wait(r, 0.7)
    up(r, STOP, 0)
    wait(r, 2.0)
    say(f"    {where(r)}")
    say(f"    footer: {footer(r)}")
    say("    LEDs (time since the press):")
    leds(r, mark, t0)
    say(f"    bank: {bank(r)}")
    say(f"    <home>/presets: {files(r)}")

    say()
    say("5. Two buttons held (a hand across G6·2 and G6·3, the second 0.2 s later), "
        "both kept down 3 s")
    before = len(list((demo.HOME / "presets").glob("*.json")))
    down(r, STOP, 1)
    wait(r, 0.2)
    down(r, STOP, 2)
    wait(r, 3.0)
    up(r, STOP, 1, 2)
    wait(r, 1.0)
    after = len(list((demo.HOME / "presets").glob("*.json")))
    say(f"    {where(r)}   new files: {after - before}")
    say(f"    footer: {footer(r)}")
    say(f"    <home>/presets: {files(r)}")

    say()
    say("6. The new slot's pad: G1·1 (TUMBLE), then G1·6")
    tap(r, PAD, channel=0)
    settle(r)
    say(f"    G1·1: {where(r)}")
    mark, t0 = len(r.log), r.t
    tap(r, PAD, channel=5)
    settle(r)
    say(f"    G1·6: {where(r)}")
    say("    LEDs (time since the press):")
    leds(r, mark, t0)
    say(f"    bank: {bank(r)}")

    say()
    say("7. A preset put on a slot and a slot cleared (Project.put_slot / clear_slot)")
    was = files(r)
    proj.put_slot(1, "TRIP 3")
    say(f"    put TRIP 3 on F2:  footer: {footer(r)}")
    say(f"    bank: {bank(r)}")
    proj.clear_slot(6)
    say(f"    clear F7:          footer: {footer(r)}")
    say(f"    bank: {bank(r)}")
    proj.put_slot(6, "NOPE")
    say(f"    put NOPE on F7:    footer: {footer(r)}")
    lib.warning = ""
    say(f"    the show's file now holds: {json.loads(show.read_text())['bank']}")
    say(f"    no preset file moved: {files(r) == was}   a trash folder: "
        f"{(demo.HOME / 'trash').exists()}")
    mark, t0 = len(r.log), r.t
    down(r, STOP, 7)
    wait(r, 0.7)
    up(r, STOP, 7)
    wait(r, 2.0)
    say(f"    a hold, F7 free:   footer: {footer(r)}")
    say(f"    bank: {bank(r)}")

    say()
    say("8. A Learn armed on a param, then a button of the bar held: refused (invariant, D6)")
    count = len(list((demo.HOME / "presets").glob("*.json")))
    r.learn.arm("view.depth4")
    down(r, STOP, 4)
    wait(r, 1.0)
    up(r, STOP, 4)
    say(f"    learn says:  {r.learn.last}")
    say(f"    new files: {len(list((demo.HOME / 'presets').glob('*.json'))) - count}")
    notes = table.set_desk([*table.desk(), {"source": rows[0].source, "target": "view.points",
                                            "op": "toggle"}], load=False)
    say(f"    a preset's desk row on it: {notes[0]}")
    settle(r)
    stack(r)

    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(demo.lines) + "\n")


if __name__ == "__main__":
    main()
