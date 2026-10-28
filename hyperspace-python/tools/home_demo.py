#!/usr/bin/env python3
"""Home, shown headless (plan 15 WP2, decision 27).

One press loads the preset the show starts on: the APC40's OVERDUB (B11),
the same on both desk layers, and the keyboard's Home key (fn ← on a
laptop). This builds the app's objects the way `tools/undo_demo.py` does
— no window, a `MidiIO` over fake ports, the key rows through
`Router.keys` — and prints a transcript: load TRIP, edit it, go home by
each road, the LED velocity the desk is sent, Ctrl+Z bringing the edited
TRIP back, a show that names no startup preset, and a Learn that OVERDUB
refuses.

It always runs on a fresh temp home of its own (`undo_demo` sets
`HYPERSPACE_HOME` on import, before anything reads it, and seeds it with
the test corpus: the party show, which starts on TUMBLE): it cannot touch
~/Hyperspace. Since 2026-10-28 nothing on the panel sets a show's startup
preset (the PRESETS page's "starts on" went with its bank pills), so the
`--shot` of that page is gone; the show file's `startup` still works.

  uv run python tools/home_demo.py [--out docs/plans/assets/15-safety-net/home-demo.txt]
"""

# ruff: noqa: I001 — undo_demo is imported first, on purpose: it sets
# HYPERSPACE_HOME to a temp home and points pyGLFW at imgui_bundle's libglfw
# before anything loads glfw
from __future__ import annotations

import sys
from pathlib import Path

import undo_demo as demo
from undo_demo import Keys, frames, say, settle, stack

import glfw
import mido

from hyperspace import apc40
from hyperspace.library import PRESETS

OVERDUB = apc40.N_OVERDUB


def note(n: int, vel: int = 127, channel: int = 0) -> mido.Message:
    return mido.Message("note_on" if vel else "note_off", channel=channel, note=n, velocity=vel)


def tap(r, n: int, channel: int = 0) -> None:
    """A button pressed and let go, a frame apart, through MidiIO."""
    r.ports.queue.append(note(n, channel=channel))
    frames(r)
    r.ports.queue.append(note(n, 0, channel=channel))
    frames(r)


def led(r) -> str:
    """The last LED velocity the desk was sent for OVERDUB."""
    sent = [m.velocity for m in r.ports.sent if m.type == "note_on" and m.note == OVERDUB]
    return f"{sent[-1]} ({'lit' if sent[-1] else 'dark'})" if sent else "nothing sent"


def where(r) -> str:
    bright = r.reg["view.bright"]
    lib = r.lib
    return (f"preset {lib.current(PRESETS)}{' •' if lib.is_dirty(PRESETS) else ''}, "
            f"{bright.label} {bright.fmt(bright.base)}, {len(r.router.table.routes())} routes, "
            f"layer {r.router.table.layer}")


def trip_edited(r) -> None:
    """F5's pad on the clip row (TRIP), then an unsaved edit."""
    tap(r, apc40.N_CLIP[0], channel=4)
    settle(r)
    bright = r.reg["view.bright"]
    bright.set(bright.base * 0.5)
    settle(r)
    r.undo.clear()
    say(f"    loaded and edited: {where(r)}")


def undo_key(r) -> None:
    frames(r, keys=Keys(glfw.KEY_Z, "CONTROL"))
    say(f"    Ctrl+Z            footer: ·  {r.undo.status}")
    say(f"    now:              {where(r)}")
    frames(r, 5)


def main() -> None:
    r = demo.boot()
    lib, proj, table = r.lib, r.lib.project, r.router.table
    say("Hyperspace — home, headless (tools/home_demo.py; plan 15 WP2, decision 27)")
    say(f"home folder: {demo.HOME}  (a temp folder made by this script)")
    frames(r, 5)
    (row,) = table.route("note", 0, OVERDUB)
    key = next(b for b in table.of("key") if b.target == "preset.home")
    say(f"show: {proj.name}   startup: {proj.startup}   preset: {lib.current(PRESETS)}")
    say(f"desk row: {r.midi.control_name(row)}  {row.source} -> {row.target}  op {row.op}  "
        f"layer {row.layer} (None: invariant)   key row: {key.source} -> {key.target}  "
        f"op {key.op}")
    say(f"OVERDUB's LED at power-up: velocity {led(r)}")

    say()
    say("1. TRIP, edited; then OVERDUB on the preset layer")
    trip_edited(r)
    tap(r, OVERDUB)
    say(f"    OVERDUB pressed:  {where(r)}")
    say(f"    OVERDUB's LED:    velocity {led(r)}")
    settle(r)
    stack(r)
    undo_key(r)

    say()
    say("2. SHIFT latched (the global layer), then OVERDUB: the same press")
    tap(r, apc40.N_SHIFT)
    say(f"    SHIFT latched:    {where(r)}")
    tap(r, OVERDUB)
    say(f"    OVERDUB pressed:  {where(r)}   (a load drops to the preset layer, D4)")
    settle(r)
    stack(r)
    undo_key(r)

    say()
    say("3. The Home key (fn ← on a laptop): the key:HOME row through Router.keys")
    frames(r, keys=Keys(glfw.KEY_HOME))
    say(f"    Home pressed:     {where(r)}")
    settle(r)
    stack(r)
    undo_key(r)

    say()
    say("4. A show that names no startup preset (set to none, in memory)")
    was, proj.startup = proj.startup, None
    frames(r, 2)
    say(f"    OVERDUB's LED:    velocity {led(r)}")
    r.ports.queue.append(note(OVERDUB))
    frames(r)
    say(f"    OVERDUB pressed:  {where(r)}")
    say(f"    library warning:  {lib.warning}")
    r.ports.queue.append(note(OVERDUB, 0))
    frames(r)
    settle(r)
    stack(r)
    proj.startup = was
    lib.warning = ""
    frames(r, 2)
    say(f"    startup {was} again; OVERDUB's LED: velocity {led(r)}")

    say()
    say("5. A Learn armed on a param, then OVERDUB: refused (invariant, D6)")
    r.learn.arm("view.depth4")
    r.ports.queue.append(note(OVERDUB))
    frames(r)
    r.ports.queue.append(note(OVERDUB, 0))
    frames(r)
    say(f"    learn says:       {r.learn.last}")
    say(f"    still:            {where(r)}")
    notes = table.set_desk([*table.desk(),
                            {"source": row.source, "target": "view.points", "op": "toggle"}],
                           load=False)
    say(f"    a preset's desk row on it: {notes[0]}")

    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(demo.lines) + "\n")


if __name__ == "__main__":
    main()
