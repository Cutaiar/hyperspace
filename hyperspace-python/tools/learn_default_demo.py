#!/usr/bin/env python3
"""Plan 18 WP3 — what a hand Learn lands with, shown headless.

SYNTHETIC HANDS: no tracker and no window. The app's objects are built
the way `tools/undo_demo.py` builds them (its `boot`: library, registry,
router, presets, the one `Learn`, a `HandsIO` over a fake tracking source,
the `Undo`), and a palm is moved through the real `HandsIO` chain — the
default ranges and the default feel (One Euro, the 0.04 dead zone of a
centred axis, the catch), no interaction box. Each learn is armed the way
the right-click menu arms it ("Learn hand ▸ right") and completed by the
axis that moved, through `HandsIO._learn` → `Learn.learn_source`.

For each learned row a table: hand reading → the param's value, with the
row a learn landed **before** this package (`position`, depth 1) beside
the row it lands now. Both are measured, on a second set of the same
objects holding only that one row, the hand held at each reading for a
second and a half.

It always runs on a fresh temp home of its own (`undo_demo` sets
`HYPERSPACE_HOME` before anything reads it): it cannot touch ~/Hyperspace.

    uv run python tools/learn_default_demo.py \\
        [--out docs/plans/assets/18-hand-and-knob-feel/learn-default.txt]

It shows which rows land and what they do to the numbers. It does not
show how 0.25 feels under a real hand (hand checks N4–N6).
"""

# undo_demo sets HYPERSPACE_HOME to a temp home as it is imported, before
# anything here reads it
from __future__ import annotations

import dataclasses
import math
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import undo_demo as demo

from hyperspace.routing import Binding

say = demo.say
HOLD = 90            # frames a reading is held before the value is read


def palm(side: str = "right", *, y: float = 200.0, roll: float = 0.0, pitch: float = 0.0) -> NS:
    """A palm-only synthetic hand (what `hands.core.features` reads): the
    palm `y` mm above the camera, rolled thumb-up by `roll`° and pitched
    fingers-up by `pitch`°."""
    v3 = lambda x, yy, z: NS(x=x, y=yy, z=z)
    a = math.radians(-roll if side == "right" else roll)     # thumb up is + on both hands
    p = math.radians(pitch)
    return NS(type=NS(name=side.capitalize()), confidence=1.0, grab_strength=0.0,
              pinch_strength=0.0, grab_angle=0.0, pinch_distance=80.0,
              palm=NS(position=v3(-120.0 if side == "left" else 120.0, y, 0.0),
                      normal=v3(math.sin(a), -math.cos(a), 0.0),
                      direction=v3(0.0, math.sin(p), -math.cos(p)), width=0.0))


def stage(bases: dict[str, float]) -> NS:
    """The app's objects with the startup preset's own routes taken out
    (so every row below is one this script learned) and the bases set."""
    r = demo.boot()
    r.router.table.set_routes([])
    for pid, v in bases.items():
        r.reg[pid].set(v)
    demo.settle(r)
    r.undo.clear()
    return r


def hold(r, *hands_, n: int = HOLD) -> None:
    demo.frames(r, n, hands_at=lambda t: hands_)


def learn(r, pid: str, side: str, pose, also=()) -> None:
    """Arm `pid` for `side`'s hand, then move: `pose(k)` is that hand on
    frame k. `also` are hands that stay still in view."""
    hold(r, pose(0), *also, n=30)
    r.learn.arm(pid, f"hand:{side}")
    for k in range(1, 200):
        hold(r, pose(k), *also, n=1)
        if r.learn.learning is None:
            break
    say(f"    status line: {r.learn.last}")


def rows(r) -> None:
    routes = r.router.table.routes()
    say(f"    ROUTING ({len(routes)} row{'s' if len(routes) != 1 else ''}):")
    for b in routes:
        depth = f"{b.value:+.3g}" if b.op == "push" else f"{b.value:.3g}"
        rest = "" if b.op != "push" else f"rest {'the axis’s' if b.rest is None else b.rest}"
        say(f"      {b.source:<17} → {b.target:<12} {b.op:<8} depth {depth:<6} {rest:<15} "
            f"\"{r.router.describe(b)}\"")
    if not routes:
        say("      (none)")


def table(m, b: Binding, readings, unit: str) -> None:
    """`b`'s target against the hand's reading: the row before this
    package and the row as learned, each alone on the measuring rig `m`."""
    p = m.reg[b.target]
    base = p.fmt(p.base)
    before = Binding(b.source, b.target, "position", 1.0, when=b.when)
    after = dataclasses.replace(b)
    cols = []
    for row in (before, after):
        m.router.table.set_routes([row])
        vals = []
        for _, h in readings:
            hold(m, h)
            vals.append(p.fmt(p.value))
        hold(m)                                          # the hand leaves
        vals.append(p.fmt(p.value))
        cols.append(vals)
    m.router.table.set_routes([])
    name = lambda x: ("position, depth 1" if x.op == "position" else f"push {x.value:+.3g}")
    same = "   (the same row)" if before == after else ""
    say(f"    {b.target} (base {base}) against the hand, measured{same}:")
    say(f"      {'hand reads':<26} {'before: ' + name(before):>26} {'after: ' + name(after):>26}")
    for (label, _), was, now in zip([*readings, ("no hand", None)], *cols):
        say(f"      {label.replace('#', unit):<26} {was:>26} {now:>26}")


def main() -> None:
    bases = {"rot.rate.XY": 1.0, "view.bright": 2.0, "view.speed": 0.35}
    m = stage(bases)                 # the measuring rig, booted first: `r`'s undo is the live one
    r = stage(bases)
    reg = r.reg
    say("Hyperspace — a learn's default, headless (tools/learn_default_demo.py; plan 18 WP3)")
    say("SYNTHETIC HANDS through the real HandsIO chain (default ranges, default feel, no box):")
    say("nothing here was seen by a tracker, and nobody has felt these depths (hand checks N4–N6).")
    say(f"home: {demo.HOME}  (a temp folder made by this script)")
    say("The startup preset's own routes are taken out first, so every row is one learned here;")
    say("bases: " + ", ".join(f"{pid} {reg[pid].fmt(reg[pid].base)}" for pid in bases)
        + f"; hands.learn_depth {reg['hands.learn_depth'].text()}.")
    say("'before' is the row every learn landed until this package (position, depth 1), "
        "measured the same way.")

    # `#` is where `table` puts the unit
    roll = [(f"roll {d:+.0f}#", palm(roll=d)) for d in (-90, -18, -9, 0, 9, 18, 90)]
    roll[3] = ("roll 0# (level)", roll[3][1])
    high = lambda side: [(f"height {y:.0f}#", palm(side, y=y)) for y in (100, 125, 225, 350)]
    pitch = [(f"pitch {d:+.0f}#", palm(pitch=d)) for d in (-60, -18, 0, 18, 60)]
    pitch[2] = ("pitch 0# (level)", pitch[2][1])

    say()
    say("1. Learn hand ▸ right on rot.rate.XY, then roll the right hand "
        "(a centred axis, a range centred on zero)")
    learn(r, "rot.rate.XY", "right", lambda k: palm(roll=min(60.0, 2.0 * k)))
    rows(r)
    table(m, r.router.table.owner("rot.rate.XY"), roll, "°")

    say()
    say("2. Learn hand ▸ right on view.bright, then raise the right hand "
        "(a one-sided axis, a one-sided param: still the fader)")
    learn(r, "view.bright", "right", lambda k: palm(y=min(340.0, 200.0 + 4.0 * k)))
    rows(r)
    hi = high("right")
    hi[0] = ("height 100# (the bottom)", hi[0][1])
    table(m, r.router.table.owner("view.bright"), hi, " mm")

    say()
    say("3. Learn hand ▸ left on rot.rate.XY, then raise the left hand "
        "(a one-sided axis, a range centred on zero)")
    say("   The right roll already performs rot.rate.XY: one performer per parameter, "
        "so the learn is held for the prompt.")
    still = (palm("right"),)
    learn(r, "rot.rate.XY", "left", lambda k: palm("left", y=min(340.0, 200.0 + 4.0 * k)),
          also=still)
    new, cur = r.learn.pending
    say(f"    held: {new.source} {new.op} {new.value:+.3g}  against  {cur.source} — "
        "the table is untouched until the prompt answers")
    r.learn.resolve_pending(True)
    say("    Replace")
    say(f"    status line: {r.learn.last}")
    rows(r)
    hi = high("left")
    hi[0] = ("height 100# (the bottom)", hi[0][1])
    table(m, r.router.table.owner("rot.rate.XY"), hi, " mm")
    demo.settle(r)

    say()
    say("4. hands.learn_depth set to 0.1 (HANDS ▸ feel & calibration ▸ Learn depth), "
        "then Learn hand ▸ right on view.speed and tilt the fingers up")
    reg["hands.learn_depth"].set_value(0.1)
    learn(r, "view.speed", "right", lambda k: palm(pitch=min(50.0, 2.0 * k)))
    rows(r)
    say("    (the rows learned at 0.25 and at position 1 keep theirs: "
        "the depth is what the next learn lands with)")
    table(m, r.router.table.owner("view.speed"), pitch, "°")
    demo.settle(r)

    say()
    say("5. The same axis learned onto a second param: Learn hand ▸ right on camera.yaw, "
        "tilt the fingers up again")
    learn(r, "camera.yaw", "right", lambda k: palm(pitch=min(50.0, 2.0 * k)))
    rows(r)
    demo.settle(r)
    demo.stack(r)
    say("   Cmd+Z, once")
    demo.press(r, "Z", "SUPER")
    rows(r)
    demo.stack(r)

    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(demo.lines) + "\n")


if __name__ == "__main__":
    main()
