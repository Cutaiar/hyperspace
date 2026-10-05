#!/usr/bin/env python3
"""Three of plan 16 WP7's four small fixes, shown headless.

1. A footer line said twice shows twice (an empty F-key, home on a show
   that names no "starts on").
2. A performer's round-off lights no dirty dot; one detent does.
4. `[output] monitor = "left"` (or a screen that is not there) is −1 and
   a note, not a dead launch.

(The third fix — the desk diagram's one-frame jump when `/` first brings
the cheat sheet up — is a picture, held by
`tests/test_ui_desk.py::test_the_desk_does_not_jump_when_the_sheet_comes_up`.)

"Before" is the old rule applied to the same state, in this script: a
plain assignment of the line, an exact comparison of the signature,
`int()` on the raw config value. "After" is the app's own code.

It builds the app's objects the way `tools/undo_demo.py` does — no
window, synthetic hands — on a fresh temp home of its own (`undo_demo`
sets `HYPERSPACE_HOME` on import, before anything reads it): it cannot
touch ~/Hyperspace.

  uv run python tools/followups_demo.py [--out docs/plans/assets/16-paper-cuts/followups-demo.txt]
"""

# ruff: noqa: I001 — undo_demo is imported first, on purpose: it sets
# HYPERSPACE_HOME to a temp home before anything reads it
from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import undo_demo as demo
from undo_demo import frames, say

from fake_hands import hand

from hyperspace import config, placement, ui
from hyperspace.library import PRESETS


def footer(panel, now: float) -> str:
    """What the control window's footer shows at `now` (`Panel._message`)."""
    text, warn = ui.Panel._message(panel, now)
    return f'"{text}"{" (warning colour)" if warn else ""}' if text else "nothing"


def moving(t):
    return (hand("right", at=(120 * math.sin(t * 2.3), 220 + 110 * math.sin(t * 1.7),
                              90 * math.sin(t * 3.1))),
            hand("left", at=(-140 + 60 * math.sin(t * 1.9), 200 + 90 * math.cos(t * 1.3),
                             40 * math.sin(t * 2.0))))


def lines_twice(r) -> None:
    lib, proj, reg = r.lib, r.lib.project, r.reg
    panel = SimpleNamespace(undo=r.undo, library=lib)
    t = 1000.0
    footer(panel, t)                                   # the first look only remembers
    say("1. A footer line said twice (the footer keeps a line for "
        f"{ui.MESSAGE_S:g} s; each press is {ui.MESSAGE_S + 1:g} s after the last)")
    proj.bank[2] = None
    was, proj.startup = proj.startup, None
    for what, trigger in (("F3 on an empty slot", "preset.load.2"),
                          ('Home, the show naming no "starts on"', "preset.home")):
        say(f"   {what}")
        reg[trigger].fire()
        line = lib.warning
        say(f"     the line:      {line}")
        # before: the old code assigned the line; the same words were no news
        lib.warning = ""
        t += ui.MESSAGE_S + 1
        footer(panel, t)
        lib.warning = line
        first = footer(panel, t)
        t += ui.MESSAGE_S + 1
        footer(panel, t)
        lib.warning = line
        say(f"     before  press 1: {first}")
        say(f"             press 2: {footer(panel, t)}")
        # after: the app's own call
        for k in (1, 2):
            t += ui.MESSAGE_S + 1
            footer(panel, t)
            reg[trigger].fire()
            say(f"     {'after ' if k == 1 else '      '}  press {k}: {footer(panel, t)}")
    said = dict(lib.said)
    for _ in range(600):                               # ten seconds at 60 fps
        t += 1 / 60
        lib.warning = line                             # the same words, every frame
        footer(panel, t)
    say("   the same words assigned every frame for 10 s (no `say`): the footer shows "
        f"{footer(panel, t)}; counted {lib.said['warning'] - said['warning']} times")
    proj.startup = was
    lib.warning = ""


def round_off(r) -> None:
    lib, reg = r.lib, r.reg
    say()
    say("2. The preset's dirty dot after two hands have been through the box")
    say("   (each factory preset loaded, 2 s of hands on its own routes, the hands gone)")
    shown = 0
    names = lib.list(PRESETS)
    for name in names:
        lib.load(PRESETS, name)
        frames(r, 5)
        ref = lib._loaded[PRESETS]
        frames(r, 120, hands_at=moving)
        frames(r, 40)
        sig = lib._kinds[PRESETS].signature()
        moved = {k: (ref[0][k], v) for k, v in sig[0].items() if v != ref[0][k]}
        if not moved:
            continue
        shown += 1
        say(f"   {name}: {len(moved)} base(s) no longer equal to the file's")
        for pid, (a, b) in sorted(moved.items())[:3]:
            say(f"     {pid}: {a!r} -> {b!r}   (shown as {reg[pid].fmt(a)} and "
                f"{reg[pid].fmt(b)})")
        say(f"     before  (signature != reference):    {'unsaved •' if sig != ref else 'clean'}")
        say(f"     after   (Library.is_dirty):          "
            f"{'unsaved •' if lib.is_dirty(PRESETS) else 'clean'}")
        pid = min(moved)
        group = pid.split(".")[0]
        say(f"     the {group.upper()} page's module dot:         "
            f"{'unsaved •' if lib.is_dirty(group) else 'clean'}")
        p = reg[pid]
        was = p.base
        p.step(1 if p.position() < p.steps else -1)
        say(f"     one detent of {pid} ({p.fmt(was)} -> {p.fmt(p.base)}):  "
            f"{'unsaved •' if lib.is_dirty(PRESETS) else 'clean'}")
    say(f"   {shown} of {len(names)} factory presets had a base moved by these hands; "
        f"every other one read clean before and after")


def screens_note(home: Path) -> None:
    say()
    say('3. `[output] monitor` in config.toml that is not a usable screen index')
    two = [placement.Screen("Built-in Retina Display", 0, 33, 1728, 1010),
           placement.Screen("DELL U2720Q", 1728, 0, 1920, 1080)]
    say("   screens: 0 = Built-in Retina Display, 1 = DELL U2720Q")
    path = home / "config.toml"
    for text in ('monitor = "left"', "monitor = 7", "control_monitor = 2.5\nmonitor = 1"):
        path.write_text(f"[output]\n{text}\n")
        say(f"   config.toml:  [output] {text.replace(chr(10), ' · ')}")
        raw = config.tomllib.loads(path.read_text())["output"].get("monitor", -1)
        try:
            before = f"Output.monitor = {int(raw)}"
            if int(raw) >= len(two):
                before += "  (a screen that is not there, kept)"
        except ValueError as e:
            before = f"the launch stops — ValueError: {e}"
        say(f"     before: {before}")
        cfg = config.load(path)
        oc = cfg["output"]
        notes = list(cfg.get("notes", []))
        for kind, key, size in (("render", "monitor", (1280, 820)),
                                ("control", "control_monitor", (960, 900))):
            rect, note = placement.place(kind, size, two, oc[key], None)
            notes += [note] if note else []
            oc[key] = placement.index(oc[key], len(two))       # as app._windows leaves it
            say(f"     after:  {key} = {oc[key]}; the {kind} window opens at "
                f"({rect[0]}, {rect[1]})")
        for note in notes:
            say(f"     SYSTEM page note: {note}")
        if not notes:
            say("     no note")
    path.unlink()


def main() -> None:
    r = demo.boot()
    say("Hyperspace — plan 16 WP7's follow-ups, headless (tools/followups_demo.py)")
    say(f"home folder: {demo.HOME}  (a temp folder made by this script)")
    frames(r, 5)
    say(f"show: {r.lib.project.name}   preset: {r.lib.current(PRESETS)}")
    say()
    lines_twice(r)
    round_off(r)
    screens_note(demo.HOME)
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(demo.lines) + "\n")


if __name__ == "__main__":
    main()
