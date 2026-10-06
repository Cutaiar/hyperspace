#!/usr/bin/env python3
"""Hide, rename and the trash, headless and as pictures (plan 19 WP4).

Each run builds a fresh temp home like the owner's
(`tests/conftest.py::build_owner_home`: `mine` and a copy of `party`, three
presets of yours, one file already in the trash). `tools/undo_demo.py`
sets `HYPERSPACE_HOME` to it before anything reads it, so this cannot
touch ~/Hyperspace.

  uv run python tools/trash_demo.py
      docs/plans/assets/19-presets-and-the-desk/files-demo.txt: the folder
      listing before and after each of: hide and unhide, a rename that
      updates two shows (and what landed in trash/), a refused rename, a
      delete, a restore to a taken name, an empty.

  uv run python tools/trash_demo.py --shots
      preset-list.png, trash.png and bank-dangling.png beside it: the
      preset list popup (×, rename, show hidden, trash ▸), the trash popup
      armed, and a slot whose preset is in the trash with its hover. Drawn
      in a **hidden** GLFW window at the control size over the headless
      objects (`dot_demo.Shooter`) and driven by real mouse events — not
      the app, no render window.
"""

# ruff: noqa: I001 — undo_demo is imported first, on purpose (see dot_demo.py)
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import undo_demo as demo

from conftest import build_owner_home, tree

from hyperspace import ui_presets
from hyperspace.library import LibraryError

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "19-presets-and-the-desk"
say = demo.say


def listing(home: Path, *folders: str) -> None:
    """The home's files (less the machine's), with a short hash each."""
    for p in sorted(home.rglob("*")):
        rel = p.relative_to(home).as_posix()
        if not p.is_file() or rel.startswith(("weights/", "stall.log", "windows.json")):
            continue
        if folders and not rel.startswith(folders):
            continue
        sha = hashlib.sha256(p.read_bytes()).hexdigest()[:10]
        say(f"      {rel:<50} {p.stat().st_size:>6} B  {sha}")


def diff(before: dict, after: dict) -> None:
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    for k in changed:
        what = "new" if k not in before else "gone" if k not in after else "rewritten"
        say(f"      {what:<9} {k}")
    if not changed:
        say("      (nothing on disk changed)")


def step(r, title: str, fn) -> None:
    home = demo.HOME
    say(title)
    before = tree(home)
    lib = r.lib
    was = dict(lib.said)
    try:
        fn()
    except LibraryError as e:
        say(f"   refused: {e}")
    if lib.said.get("status", 0) != was.get("status", 0):
        say(f"   footer · status: {lib.status}")
    if lib.said.get("warning", 0) != was.get("warning", 0):
        say(f"   footer · warning: {lib.warning}")
    say("   what changed on disk:")
    diff(before, tree(home))
    say()


def transcript(out: Path) -> None:
    home = build_owner_home(demo.HOME)
    r = demo.boot()
    lib, pr = r.lib, r.lib.project
    lib.warning = ""
    say("Plan 19 WP4 — hide, rename and the trash. Headless, on a temp home built like the")
    say("owner's (tools/trash_demo.py; <home> is that temp folder, never ~/Hyperspace).")
    say()
    say("0. The home as it starts (less weights/, stall.log, windows.json):")
    listing(home)
    say()
    step(r, "1. × on a factory preset (TRIP): hidden — only hidden.json is written", lambda: (
        lib.hide("presets", "TRIP")))
    say(f"   hidden.json: {json.loads((home / 'hidden.json').read_text())}")
    say(f"   in the list: {'TRIP' in lib.list('presets')}   with hidden: "
        f"{'TRIP' in lib.list('presets', hidden=True)}")
    pr.load_slot(4)
    say(f"   F5 pressed → loaded {lib.current('presets')}")
    say()
    step(r, "   unhide TRIP", lambda: lib.unhide("presets", "TRIP"))
    # both shows name NIGHT TWO on a slot and as "starts on"
    pr.load("party", startup=False)
    pr.put_slot(5, "NIGHT TWO")
    pr.startup = "NIGHT TWO"
    pr.write()
    pr.load("mine", startup=False)
    pr.startup = "NIGHT TWO"
    pr.write()
    pr.load_slot(1)
    lib.poll()
    say("2. A rename that updates two shows. Set up: `party` (your copy) has NIGHT TWO on F6")
    say("   and both shows start on it; `mine` is open with NIGHT TWO loaded from F2.")
    for s in ("mine", "party"):
        d = json.loads((home / "projects" / f"{s}.hyp.json").read_text())
        say(f"   {s}.hyp.json  bank {d['bank']}  startup {d['startup']!r}")
    step(r, "   rename NIGHT TWO → SUNRISE", lambda: lib.rename("presets", "NIGHT TWO", "SUNRISE"))
    for s in ("mine", "party"):
        d = json.loads((home / "projects" / f"{s}.hyp.json").read_text())
        say(f"   {s}.hyp.json  bank {d['bank']}  startup {d['startup']!r}")
    say(f"   loaded: {lib.current('presets')}   lit: F{pr.active + 1}   show dirty: "
        f"{pr.is_dirty()}")
    say("   trash/ now:")
    listing(home, "trash/")
    say()
    step(r, "3. A refused rename: NIGHT ONE → TRIP (a factory preset's name)",
         lambda: lib.rename("presets", "NIGHT ONE", "TRIP"))
    step(r, "   …and renaming a factory preset: TRIP → MY TRIP",
         lambda: lib.rename("presets", "TRIP", "MY TRIP"))
    step(r, "4. × on your own preset (NIGHT THREE, on F3): to the trash; the slot keeps its name",
         lambda: lib.delete("presets", "NIGHT THREE"))
    say(f"   F3 still names: {pr.bank[2]!r}   pressing it:")
    pr.load_slot(2)
    say(f"   footer · warning: {lib.warning}")
    say()
    (item,) = [t for t in lib.trash() if t.name == "NIGHT ONE"]
    say("5. Restore to a taken name: the copy of NIGHT ONE the home already had in its trash")
    say(f"   (NIGHT ONE is still in presets/): {item.path.name}  ({item.when})")
    step(r, "   restore it", lambda: lib.restore_trash(item))
    say(f"   presets/night-one.json untouched; the copy came back as "
        f"{json.loads((home / 'presets' / 'night-one-2.json').read_text())['name']!r}")
    say()
    say("6. Empty the trash: what it lists, newest first —")
    for t in lib.trash():
        say(f"      {t.group:<9} {t.name:<14} {t.when:<13} {t.path.name}")
    step(r, "   empty (the panel asks twice; here the call itself)", lib.empty_trash)
    say("   the home at the end:")
    listing(home)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(demo.lines) + "\n")
    print(f"\nwrote {out}")


def shots() -> None:
    from dot_demo import Shooter

    build_owner_home(demo.HOME)
    r = demo.boot()
    lib = r.lib
    lib.warning = ""
    # a picture's worth: yours renamed to the top of the list, two factory
    # presets hidden, the trash holding a few files, F3's preset in the trash
    lib.rename("presets", "NIGHT TWO", "AFTERGLOW")
    lib.hide("presets", "BIG BLUE WAVE")
    lib.hide("presets", "EMBER ORBIT")
    lib.delete("presets", "NIGHT THREE")
    lib.load("presets", "AFTERGLOW")
    shot = Shooter(r)
    st = ui_presets._state(shot.panel)
    pad = 10

    def box(rects: dict) -> tuple:
        xs = [v for rc in rects.values() for v in (rc[0], rc[2])]
        ys = [v for rc in rects.values() for v in (rc[1], rc[3])]
        return (min(xs) - pad, min(ys) - 34, max(xs) + pad, max(ys) + pad)

    try:
        shot.draw(6)
        # bank-dangling: F3 names NIGHT THREE, which is in the trash; hovered
        f3 = st["rects"]["preset.2"]
        shot.draw(4, mouse=((f3[0] + f3[2]) / 2, (f3[1] + f3[3]) / 2))
        print(f"dangling slots: {st['dangling']}")
        b0, b1 = st["rects"]["preset.0"], st["rects"]["preset.23"]
        OUT.mkdir(parents=True, exist_ok=True)
        # from the window's left edge: the hover runs out over the rail
        shot.crop((max(0, b0[0] - 230), b0[1] - 30, b1[2] + 12, b1[3] + 60)).save(
            OUT / "bank-dangling.png", optimize=True)
        print(f"wrote {OUT / 'bank-dangling.png'}")
        # the preset list, "show hidden" on
        shot.draw(2, mouse=(5, 5))
        shot.click(st["rects"]["strip.presets.name"])
        shot.draw(2)
        shot.click(st["list"]["rects"]["show_hidden"])
        shot.draw(4, mouse=(5, 5))
        print(f"list rows: {st['list']['rows'][:6]}  foot: {st['list']['foot']}")
        # the rows past twelve are scrolled out of the child: frame what shows
        rows = st["list"]["rects"]["rows"]
        seen = {k: v for k, v in st["list"]["rects"].items()
                if not k.startswith(("row.", "×.", "rename.", "unhide.")) or v[3] <= rows[3]}
        shot.crop(box(seen)).save(OUT / "preset-list.png", optimize=True)
        print(f"wrote {OUT / 'preset-list.png'}")
        # the trash, "empty trash…" armed
        shot.click(st["list"]["rects"]["trash"])
        shot.draw(2)
        shot.click(st["trash_view"]["rects"]["empty"])
        r0 = st["trash_view"]["rects"]["rows"]
        shot.draw(2, mouse=(r0[2] + 200, r0[1]))      # off the chip: no hover over the rows
        print(f"trash rows: {st['trash_view']['rows']}  empty: {st['trash_view']['empty']!r}")
        shot.crop(box(st["trash_view"]["rects"])).save(OUT / "trash.png", optimize=True)
        print(f"wrote {OUT / 'trash.png'}")
        assert all(p.exists() for p in (t.path for t in lib.trash())), "nothing emptied"
    finally:
        shot.close()


def main() -> None:
    if "--shots" in sys.argv[1:]:
        shots()
        return
    transcript(OUT / "files-demo.txt")


if __name__ == "__main__":
    main()
