#!/usr/bin/env python3
"""The interaction box, shown headless on synthetic hands (plan 18 WP1).

No camera and no real hand: the hands are `tests/fake_hands.py`'s, fed to
a `HandsIO` built the way `app.main` builds it, on the objects
`tools/undo_demo.py` boots (library, registry, router, Learn) — with no
window. It prints a transcript:

  1. a `hyperspace.hands/1` file from before the box loads with no
     bounds and is left byte for byte;
  2. a sweep sets the box and says so; the old file is kept beside the
     new one, once;
  3. a hand walks out through a face and back: presence, the lane, and a
     routed param letting go and being caught, frame by frame at the edge;
  4. a second sweep makes no second copy; "reset ranges" opens the box.

It always runs on a fresh temp home of its own (`undo_demo` sets
`HYPERSPACE_HOME` before anything reads it, and the calibration file's
path is taken from `config.load()`, as the app takes it): it cannot touch
~/Hyperspace.

  uv run python tools/box_demo.py [--out docs/plans/assets/18-hand-and-knob-feel/box-demo.txt]
"""

# undo_demo sets HYPERSPACE_HOME to a temp home as it is imported, before
# anything here reads it
from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

import undo_demo as demo
from fake_hands import hand

from hyperspace import config, hands
from hyperspace.hands import panel as hands_panel
from hyperspace.hands.core import BOX_EDGE, BOX_MARGIN
from hyperspace.routing import Binding

say = demo.say
# a calibration as a build before plan 18 saved it (schema 1, no box)
OLD_FILE = (
    '{\n "schema": "hyperspace.hands/1",\n "axes": {\n'
    '  "left.x": {"lo": -214.2, "hi": 18.5},\n  "left.y": {"lo": 112.0, "hi": 341.5},\n'
    '  "right.x": {"lo": -16.0, "hi": 209.75},\n  "right.y": {"lo": 108.25, "hi": 352.0}\n'
    ' }\n}\n')


def cal_path() -> Path:
    """Where the app keeps hands.json: `[hands] calibration`, resolved by
    config.load — and, here, checked to be inside this script's temp home."""
    path = Path(config.load()["hands"]["calibration"])
    if demo.HOME.resolve() not in path.resolve().parents:
        raise SystemExit(f"refusing to run: {path} is not under the temp home {demo.HOME}")
    return path


def open_hands(r) -> None:
    """A HandsIO as app._open_hands makes it, on the synthetic tracker."""
    r.hands_io = hands.HandsIO(r.settings, {"out": ""}, source=r.tracker,
                               clock=lambda: r.t, cal_path=cal_path())


def sweep_path(t: float) -> tuple:
    """Both hands through everything they should reach, as a sweep asks."""
    return (hand("left", "open", (-95.0 + 75.0 * math.sin(t * 2.1), 225.0 + 105.0 * math.sin(t * 1.3),
                                  95.0 * math.sin(t * 1.7))),
            hand("right", "open", (95.0 + 75.0 * math.sin(t * 1.9), 225.0 + 105.0 * math.sin(t * 1.1),
                                   95.0 * math.sin(t * 2.3))))


def sweep(r, seconds: float = 20.0) -> None:
    r.hands_io.start_calibration(seconds)
    while r.hands_io.calibrating or r.hands_io._cal is not None:
        demo.frames(r, hands_at=sweep_path)


def listing(path: Path) -> str:
    return ", ".join(sorted(p.name for p in path.parent.iterdir() if p.name.startswith(path.name)))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def box_set(r) -> dict:
    """Boot, load the old file, sweep: the state the screenshot starts from."""
    path = cal_path()
    path.write_text(OLD_FILE)
    open_hands(r)
    sweep(r)
    return r.hands_io.box


def main() -> None:
    r = demo.boot()
    path = cal_path()
    say("Hyperspace — the interaction box, headless (tools/box_demo.py; plan 18 WP1)")
    say("SYNTHETIC HANDS (tests/fake_hands.py), not the camera: nothing here was seen "
        "by a tracker.")
    say(f"home: {demo.HOME}  (a temp folder made by this script)")
    say(f"calibration file: {path}  ([hands] calibration, as the app resolves it)")

    say()
    say("1. An old hands.json (schema 1, no box) is loaded and left alone")
    path.write_text(OLD_FILE)
    before = path.read_bytes()
    stamp = path.stat().st_mtime_ns
    open_hands(r)
    io = r.hands_io
    far = lambda t: (hand("left", "open", (-100.0, 200.0, 0.0)),
                     hand("right", "open", (600.0, 900.0, 500.0)))
    demo.frames(r, 120, hands_at=far)
    st = io.state[io.axis("right.y")]
    say(f"    schema in the file: {OLD_FILE.split(chr(34))[3]}   box loaded: {io.box}")
    say(f"    right.y range from the file: {st.lo} … {st.hi} mm")
    say(f"    a right palm at (600, 900, 500) mm, far past every range: status {hands_panel._ins(io)}"
        f"   (in, as before this plan)")
    after = path.read_bytes()
    say(f"    after construction and 120 frames: sha256 {sha(before)} -> {sha(after)}, "
        f"{len(before)} -> {len(after)} bytes, bytes equal: {before == after}, "
        f"mtime unchanged: {path.stat().st_mtime_ns == stamp}")
    say(f"    files: {listing(path)}")

    say()
    say("2. A 20 s sweep of both hands sets the box (the HANDS page's calibrate button)")
    sweep(r)
    say(f"    note: {io.cal_note}")
    for c in "xyz":
        say(f"    box.{c}: " + ("open" if io.box[c] is None
                                else f"{io.box[c][0]:8.1f} … {io.box[c][1]:7.1f} mm"))
    say(f"    (the palms' 2nd–98th percentile plus {BOX_MARGIN:.0f} mm; x symmetric about the camera)")
    say(f"    files: {listing(path)}")
    bak = path.with_name(path.name + ".bak-v1")
    say(f"    {bak.name} equals the old file: {bak.read_bytes() == before}   "
        f"hands.json now starts: {path.read_text().splitlines()[1].strip()}")
    say("    the box as saved: " + " ".join(path.read_text().split('"box":')[1].split())[:-2])

    say()
    target = next(pid for pid in ("view.inst_amp", "view.depth4", "view.bright")
                  if r.router.table.owner(pid) is None)
    r.router.table.add(Binding("hand:right.y", target, "position"))
    p = r.reg[target]
    face = io.box["x"][1]
    say(f"3. The right hand walks out through the x face ({face:.1f} mm) and back, 4 mm a frame")
    say(f"    one row: hand:right.y positions {target}; its base is {p.fmt(p.base)}; "
        f"the hand is held at 300 mm high; catch {r.settings.catch_s * 1000:.0f} ms")
    say(f"    a hand that is in leaves {BOX_EDGE:.0f} mm past the face ({face + BOX_EDGE:.1f}); "
        f"one that is out comes in at the face")
    xs = [face - 30.0 + 4.0 * k for k in range(22)]
    xs = xs + xs[::-1]
    demo.frames(r, 30, hands_at=lambda t: (hand("right", "open", (xs[0], 300.0, 0.0)),))
    k_y = io.axis("right.y")
    say("      frame   palm x    status   lane right.y   " f"{target:<14}  row")
    rows = []
    for n, x in enumerate(xs):
        demo.frames(r, hands_at=lambda t, x=x: (hand("right", "open", (x, 300.0, 0.0)),))
        lane = io.lanes()[k_y]
        rows.append((n, x, hands_panel._ins(io), "NaN  " if math.isnan(lane) else f"{lane:.3f}",
                     p.fmt(p.value), "holds it" if p.modulated else "let go: the base",
                     io.present["right"]))
    edges = {n for n in range(1, len(rows)) if rows[n][6] != rows[n - 1][6]}
    shown = {0, len(rows) - 1} | {m for n in edges for m in range(n - 3, n + 6)}
    last = -1
    for n, x, ins, lane, val, row, _ in rows:
        if n not in shown:
            continue
        if n != last + 1:
            say("        …")
        last = n
        say(f"      {n:5d}  {x:7.1f}    {ins}    {lane:>8}       {val:<14}  {row}")

    say()
    say("4. Another sweep, then reset ranges")
    sweep(r)
    say(f"    note: {io.cal_note}")
    say(f"    files: {listing(path)}   (no second copy: the file was already schema 2)")
    say(f"    {bak.name} still equals the old file: {bak.read_bytes() == before}")
    io.reset_ranges()
    say(f"    reset ranges -> note: {io.cal_note}")
    say(f"    box in memory: {io.box}   in the file: "
        + " ".join(path.read_text().split('"box":')[1].split())[:-2])
    demo.frames(r, 2, hands_at=far)
    say(f"    the far right palm again: status {hands_panel._ins(io)}")
    say(f"    files: {listing(path)}")

    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(demo.lines) + "\n")


if __name__ == "__main__":
    main()
