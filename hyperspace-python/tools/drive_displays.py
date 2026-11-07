"""tools/app_driver.py's script for SC2: one row per connected display, on the real app and this
Mac's real displays, at 320 and 240 px in the pane; a tick and a change of target on whichever
rows there are, with what they did read back from the scratch library. Each step's words go to
stderr; a step that doesn't do what it should stops the run.

    uv run python tools/app_driver.py tools/drive_displays.py --out <scratch>/run --every 20 \\
        --home <scratch>/home

The rows go in `<home>/displays.json`: its library, as the driver's home names no other. It
never reaches the real library. A home whose `displays.json` you wrote first is a launch from
those rows: a render on two displays, say. Loads go through `panel.library.load("presets", name)`.
"""

import json
import sys

from hyperspace import placement, ui_displays, ui_graph
from hyperspace.displays import CONTROL, FILE
from hyperspace.ui import PAGE_KEYS


def say(*words):
    print("drive_displays:", *words, file=sys.stderr)


def script(d, panel):
    run = panel.displays
    assert run is not None, "no rows: was this --laptop?"
    panel.library.load("presets", "party-tumble")
    panel.reg["ui.page"].set(PAGE_KEYS.index("output"))
    yield from d.wait(10)
    scr = run.screens()
    tags = placement.labels(scr)
    across = [tags[i] for i in placement.arranged(scr)]
    say("connected, across the desk:", across)
    say("opened:", run.opened)
    for sl in panel.outputs:
        say(sl.label, "display", repr(sl.display), "also", [a.display for a in sl.also],
            "flips", (sl.switches.flip_x, sl.switches.flip_y), "window", bool(sl.win),
            "missing", repr(sl.missing))
    for width in (320.0, 240.0):
        ui_graph._state(panel)["side_w"] = width
        yield from d.wait(6)
        for k in range(len(across)):
            x0, y0, x1, y1 = d.rect(f"display.{k}.target")
            say(f"at {width:.0f} px: row {k} ({across[k]}) target at x {x0:.0f}-{x1:.0f}, y {y0:.0f}-{y1:.0f}")
        yield from d.wait(25)            # a capture at this width
    ui_graph._state(panel)["side_w"] = 320.0
    yield from d.wait(6)

    # the first render row's ticks, each read back from what's open
    first = next((k for k, t in enumerate(across) if run.opened.get(t, "").startswith("output.")), None)
    if first is not None:
        tag = across[first]
        sl, also = run.window_on(tag)
        has = also if also is not None else sl.switches
        was = has.flip_x
        yield from d.click(f"display.{first}.flip_x")
        yield from d.park()
        yield from d.wait(3)
        assert has.flip_x is (not was), "the tick reaches the open window at once"
        say(f"{tag}: flip X {was} -> {has.flip_x}, on the window at once")
        yield from d.wait(25)
        yield from d.click(f"display.{first}.flip_x")
        yield from d.park()
        yield from d.wait(3)

    # the last row's target: nothing, then back. Nothing opens or closes
    last = len(across) - 1
    keep = run.store.current.get(across[last], {}).get("target", "")
    windows = len([w for w in (*(sl.win for sl in panel.outputs), *(a.win for sl in panel.outputs for a in sl.also)) if w])
    yield from d.pick(f"display.{last}.target", 0)
    yield from d.park()
    yield from d.wait(3)
    say(f"{across[last]}: target {keep!r} -> nothing;",
        "windows open", windows, "(no change, it waits:", ui_displays.ON_RESTART.strip(), ")")
    yield from d.wait(25)
    run.store.sync()
    doc = json.loads((run.store.root / FILE).read_text())
    assert doc["displays"].get(across[last], {}).get("target", "") == "", doc
    picks = [t for t, _ in ui_displays.choices(panel.outputs)]
    yield from d.pick(f"display.{last}.target", picks.index(keep))
    yield from d.park()
    yield from d.wait(3)
    run.store.sync()
    doc = json.loads((run.store.root / FILE).read_text())
    say("the file:", json.dumps(doc["displays"], sort_keys=True))
    assert sum(e.get("target") == CONTROL for e in doc["displays"].values()) <= 1
    say("notes:", [n for n in panel.config_notes if n.startswith("displays:")])
    say("done")
