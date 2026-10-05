#!/usr/bin/env python3
"""Where the windows open at launch, shown headless (plan 16 WP4).

Walks the plan's case table with fake screens — no window, no GLFW, no
library home — and prints where each window opens and the note the launch
would put on stderr and the SYSTEM page: first launch, remembered, the
projector unplugged, a nonsense file, the config beating the file, a
config screen that is not there, and what a quit writes.

It calls `hyperspace.placement` only, and the one file it writes goes to a
temp folder of its own: it cannot touch ~/Hyperspace.

  uv run python tools/placement_demo.py [--out docs/plans/assets/16-paper-cuts/placement-demo.txt]

`--out` rewrites the file down to the line that starts with MARK and keeps
what follows it (the hand-pasted transcript of the real launches).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from hyperspace import placement
from hyperspace.placement import Screen, place

RENDER = (1280, 820)       # app.RENDER_SIZE
CONTROL = (960, 900)       # app.CONTROL_SIZE
LAPTOP = Screen("Built-in Retina Display", 0, 33, 1728, 1010)
PROJECTOR = Screen("DELL U2720Q", 1728, 0, 1920, 1080)
MARK = "==== real launches"

lines: list[str] = []


def say(text: str = "") -> None:
    lines.append(text)
    print(text)


def on(rect, scr) -> str:
    cx, cy = rect[0] + rect[2] / 2, rect[1] + rect[3] / 2
    for i, s in enumerate(scr):
        if s.x <= cx < s.x + s.w and s.y <= cy < s.y + s.h:
            return f"screen {i} ({s.name})"
    return "no screen"


def launch(title: str, scr, *, monitor=-1, control_monitor=-1, seen=None) -> None:
    """One launch, as app._windows asks it."""
    seen = seen or {}
    say(f"-- {title}")
    say("   screens: " + "; ".join(
        f"{i} = {s.name} {s.w}×{s.h} at ({s.x}, {s.y})" for i, s in enumerate(scr)))
    say(f"   config:  [output] monitor = {monitor!r}, control_monitor = {control_monitor!r}")
    renders = seen.get("render") or [None]
    for kind, size, mon, entry in (("render", RENDER, monitor, renders[0]),
                                   ("control", CONTROL, control_monitor, seen.get("control"))):
        say(f"   file:    {kind} = {json.dumps(entry) if entry is not None else 'nothing'}")
        (x, y, w, h), note = place(kind, size, scr, mon, entry)
        say(f"   {kind:<8} opens at ({x}, {y}), {w}×{h}, on {on((x, y, w, h), scr)}")
        for n in filter(None, note.split("; ")):
            say(f"            note: {n}")
    say()


def main() -> None:
    both = [LAPTOP, PROJECTOR]
    say("Plan 16 WP4 — where the windows open at launch (tools/placement_demo.py)")
    say("Fake screens; hyperspace.placement only. Rects are x, y, w, h in screen coordinates.")
    say()

    launch("first launch: no file, default config, the laptop alone", [LAPTOP])

    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp)
        # a quit with the render dragged to the projector, the controls on the laptop
        placement.save(home, (300, 90, 900, 860), [(2000, 140, 1600, 900)], both)
        say("-- a quit, the render dragged onto the projector: <home>/windows.json")
        for ln in (home / placement.FILE).read_text().splitlines():
            say("   " + ln)
        say()
        seen = placement.load(home)

        launch("remembered: the same two screens, default config", both, seen=seen)
        launch("the projector unplugged", [LAPTOP], seen=seen)
        launch("config beats file: monitor = 0, the render was last on screen 1",
               both, monitor=0, seen=seen)
        launch("config and file agree: monitor = 1, the render was last on screen 1",
               both, monitor=1, seen=seen)
        launch("config pins the controls: control_monitor = 1, they were last on screen 0",
               both, control_monitor=1, seen=seen)
        launch("config screen missing: monitor = 2 with two screens",
               both, monitor=2, seen=seen)
        launch("config screen missing and no projector: monitor = 1 with one screen",
               [LAPTOP], monitor=1, seen=seen)

        # a quit with the controls minimised: their entry stays
        placement.save(home, None, [(2100, 200, 1280, 820)], both)
        kept = placement.load(home)
        say("-- a quit with the control window minimised: its entry is kept")
        say(f"   control = {json.dumps(kept['control'])}")
        say(f"   render  = {json.dumps(kept['render'])}")
        say()

        nonsense = {
            "a rect off every screen": {"schema": placement.SCHEMA,
                                        "control": {"x": -9000, "y": 50, "w": 960, "h": 900},
                                        "render": [{"x": 500, "y": 9000, "w": 1280, "h": 820}]},
            "entries that are not rects": {"schema": placement.SCHEMA, "control": "top right",
                                           "render": [{"x": "left", "y": None}]},
            "another schema": {"schema": "hyperspace.windows/9",
                               "render": [{"x": 2000, "y": 140, "w": 1600, "h": 900}]},
        }
        for title, doc in nonsense.items():
            (home / placement.FILE).write_text(json.dumps(doc))
            launch(f"nonsense file: {title}", both, seen=placement.load(home))
        (home / placement.FILE).write_text("{ this is not json")
        launch("nonsense file: not JSON", both, seen=placement.load(home))

        say("-- an unwritable home: the quit goes on, only the memory is lost")
        placement.save(home / "no-such-folder", (300, 90, 900, 860), [(2000, 140, 1600, 900)], both)
        say("   save() returned; stderr got: \"placement: could not write <home>/windows.json "
            "(…) — the windows' positions are not remembered\"")
        say()

    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        tail = ""
        if out.exists() and MARK in out.read_text():
            tail = MARK + out.read_text().split(MARK, 1)[1]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n" + tail)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
