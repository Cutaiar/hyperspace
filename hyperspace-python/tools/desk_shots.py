#!/usr/bin/env python3
"""The desk, big and clickable, as PNGs and a transcript (plan 17 WP4).

Not the app: a **hidden** GLFW window at the control size (960 × 900)
with the real Panel over the headless objects `tools/undo_demo.py`
builds — a MidiIO over fake ports, no render window, no audio device, no
tracker — on a fresh temp home of its own (`tools/label_menu_shot.py`'s
`Hidden`). TRIP is loaded. Every click is an imgui mouse event fed at the
rect the desk or the widget was drawn at: nothing here has a real mouse.

  uv run python tools/desk_shots.py            # the four pictures
  uv run python tools/desk_shots.py big        # → desk-big.png         the panel hidden, the preset layer
  uv run python tools/desk_shots.py global     # → desk-big-global.png  the same under SHIFT
  uv run python tools/desk_shots.py picked     # → desk-picked.png      D3 picked, VIEW dimmed, the footer's line
  uv run python tools/desk_shots.py goto       # → routing-goto.png     ROUTING scrolled to D3's line, framed
  uv run python tools/desk_shots.py map [--out docs/plans/assets/17-learn-and-the-desk/desk-map.txt]
                                               # the transcript: pick, map, undo, the refusals, the timeout

Pictures land in docs/plans/assets/17-learn-and-the-desk/. `map` runs
alone (it edits the table the pictures are taken of).
"""

# ruff: noqa: I001 — label_menu_shot (and through it undo_demo) is imported
# first, on purpose: it sets HYPERSPACE_HOME to a temp home and points pyGLFW
# at imgui_bundle's libglfw before anything loads glfw
from __future__ import annotations

import sys
import time
from pathlib import Path

from label_menu_shot import Hidden, demo

from imgui_bundle import imgui

from hyperspace import apc40, ui, ui_desk, ui_routing
from hyperspace.ui import PAGE_KEYS, Panel

PRESET = "TRIP"


def control(glyph: str) -> apc40.Control:
    return next(c for c in apc40.LAYOUT if c.glyph == glyph)


def centre(rect) -> tuple[float, float]:
    return (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2


def boot() -> Hidden:
    h = Hidden("desk shots")
    h.r.lib.load("presets", PRESET)
    h.page("view")
    h.draw(6)
    return h


def widgets(h: Hidden) -> dict[str, tuple]:
    """Where each param's widget is drawn: {id: its item rect}, kept up to
    date as `Panel._ctx` is called on it."""
    rects: dict[str, tuple] = {}
    real = Panel._ctx

    def ctx(self, a, key="", extra=None):
        lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
        rects[a.id] = (lo.x, lo.y, hi.x, hi.y)
        return real(self, a, key, extra)
    Panel._ctx = ctx
    h.draw(2)
    return rects


def click_desk(h: Hidden, glyph: str) -> tuple[float, float]:
    """A left click fed at the control's cell on the drawn desk."""
    spot = centre(ui_desk.rect(h.panel, control(glyph)))
    h.click(*spot)
    return spot


# ---------------------------------------------------------------- the pictures

def big(h: Hidden) -> None:
    """The panel hidden: the desk is the whole control window, every lit
    control named, on the preset layer."""
    h.panel.reg["ui.panel"].set(False)
    h.r.router.table.set_layer("preset")
    h.draw(6)
    st = ui_desk._state(h.panel)
    print(f"wrote {h.save('desk-big.png')}  (unit {st['unit'][0]:.0f} × {st['unit'][1]:.0f} px, "
          f"{len(st['labels'])} labels)")
    h.panel.reg["ui.panel"].set(True)


def glob(h: Hidden) -> None:
    """The same under SHIFT: the global layer's names, the preset's controls dark."""
    h.panel.reg["ui.panel"].set(False)
    h.r.router.table.set_layer("global")
    h.draw(6)
    st = ui_desk._state(h.panel)
    print(f"wrote {h.save('desk-big-global.png')}  ({len(st['labels'])} labels)")
    h.r.router.table.set_layer("preset")
    h.panel.reg["ui.panel"].set(True)


def picked(h: Hidden) -> None:
    """The panel open, D3 picked by a click on the desk: its red frame,
    the VIEW page dimmed, the mouse over Speed (the widget a click would
    map: framed), the footer's line."""
    h.page("view")
    h.draw(6)
    rects = widgets(h)
    click_desk(h, "D3")
    if h.r.learn.control != control("D3").source:
        raise SystemExit("the click on D3 picked nothing")
    h.mouse, h.cross = centre(rects["view.speed"]), True
    h.draw(6)
    print(f"wrote {h.save('desk-picked.png')}  (picked {h.r.learn.control}; page dimmed: "
          f"{ui_desk.picking(h.panel) is not None})")
    h.cross = False
    ui_desk.let_go(h.panel)
    h.mouse = (4.0, 4.0)
    h.draw(2)


def goto(h: Hidden) -> None:
    """ROUTING open, D3 clicked on the desk: the rows scrolled to D3's
    line, framed; ROUTING is not dimmed."""
    h.page("routing")
    h.draw(6)
    click_desk(h, "D3")
    h.mouse = (4.0, 4.0)
    h.draw(6)
    st = ui_routing._state(h.panel)
    print(f"wrote {h.save('routing-goto.png')}  (lines framed: {st['marked']}; goto pending: "
          f"{st['goto']})")
    ui_desk.let_go(h.panel)
    h.draw(2)


# ---------------------------------------------------------------- the transcript

class _Clock:
    """`time`, with a `monotonic` the transcript can move forward (the
    timeout is not waited for)."""

    def __init__(self):
        self.skew = 0.0

    def monotonic(self) -> float:
        return time.monotonic() + self.skew

    def __getattr__(self, name):
        return getattr(time, name)


def transcript(h: Hidden) -> None:
    say, r, panel = demo.say, h.r, h.panel
    table, lrn, reg = r.router.table, r.learn, r.reg
    clock = _Clock()
    ui.time = ui_desk.time = clock
    footer: list[str] = []
    colored = imgui.text_colored

    def text_colored(col, s):
        if s.startswith("·  "):
            footer.append(s)
        return colored(col, s)
    imgui.text_colored = text_colored

    def draw(n: int = 3) -> None:
        footer.clear()
        h.draw(n - 1)
        footer.clear()
        h.draw(1)

    def foot() -> str:
        return footer[0] if footer else "(nothing)"

    def rows(*sources: str) -> str:
        out = []
        for src in sources:
            probe = type(table.desk()[0])(src, "", "abs")
            hit = [b for b in table.desk() if b.overlaps(probe)]
            out.append(f"{apc40.glyph(src)} → {hit[0].target if hit else 'dark'}")
        return ", ".join(out)

    def state() -> None:
        c = ui_desk.picked(panel)
        say(f"    Learn.control        {lrn.control}")
        if c is not None:
            say(f"    desk header          {ui_desk.pick_line(panel, table, c)[0]}")
        say(f"    footer (as drawn)    {foot()}")
        say(f"    page {PAGE_KEYS[panel.page]:<8} dimmed  {ui_desk.picking(panel) is not None}")

    say("desk-map — click a control, then a param (plan 17 WP4)")
    say("A hidden 960 × 900 window, the real Panel, a temp home, TRIP loaded, a MidiIO over fake")
    say("ports (nothing plugged in). Every click below is an imgui mouse event fed at the rect the")
    say("control or the widget was drawn at. No real mouse, no APC40. \"footer (as drawn)\" is the")
    say("footer's line cut to the room it has in the 540 px panel; the whole of it is on its hover.")
    say()
    h.page("view")
    draw(6)
    rects = widgets(h)
    disk = table.path.read_bytes() if table.path.exists() else None

    say("1. Click D3 on the desk (page VIEW open)")
    say(f"    before               {rows('cc:*:18', 'cc:0:49')}")
    spot = click_desk(h, "D3")
    draw()
    say(f"    click at             ({spot[0]:.0f}, {spot[1]:.0f})")
    state()
    say(f"    ROUTING goto         {ui_routing._state(panel)['goto']}  (waits: ROUTING is not open; "
        "the page was not changed)")
    say()

    say("2. Click Speed's fader on the dimmed page")
    speed = reg["view.speed"].base
    h.click(*centre(rects["view.speed"]))
    draw()
    say(f"    rows now             {rows('cc:*:18', 'cc:0:49')}")
    say(f"    message              {lrn.last}")
    say(f"    Speed moved          {reg['view.speed'].base != speed}  (the widget was disabled)")
    state()
    say(f"    preset dirty         {r.lib.is_dirty('presets')}   bindings.json written: "
        f"{(table.path.read_bytes() if table.path.exists() else None) != disk}")
    demo.settle(r)
    demo.stack(r)
    demo.press(r, "Z", "CONTROL")
    say(f"    rows after one undo  {rows('cc:*:18', 'cc:0:49')}")
    say()

    say("3. Click a fader, S3 (invariant, D6): picked for the look only")
    click_desk(h, "S3")
    draw()
    state()
    before = [b.to_json() for b in table.bindings]
    say(f"    Learn.map_picked('view.speed') → {lrn.map_picked('view.speed', apc40)}")
    say(f"    refusal              {lrn.last}")
    say(f"    table changed        {[b.to_json() for b in table.bindings] != before}")
    ui_desk.let_go(panel)
    say()

    say("4. SHIFT latched (the global layer up, D5): click K1")
    table.set_layer("global")
    draw()
    click_desk(h, "K1")
    draw()
    state()
    say(f"    Learn.map_picked('view.depth4') → {lrn.map_picked('view.depth4', apc40)}")
    say(f"    refusal              {lrn.last}")
    say(f"    table changed        {[b.to_json() for b in table.bindings] != before}")
    ui_desk.let_go(panel)
    table.set_layer("preset")
    draw()
    say()

    say('5. "Learn desk" armed on 4D depth, completed by a click on D7')
    lrn.arm("view.depth4", "desk")
    clock.skew += ui.MESSAGE_S + 1          # (the lines said above have had their time)
    draw()
    say(f"    the learn waits for  {panel._learn_hint()}")
    say(f"    footer (as drawn)    {foot()}")
    say(f"    before               {rows('cc:*:22')}")
    click_desk(h, "D7")
    draw()
    say(f"    rows now             {rows('cc:*:22')}")
    say(f"    message              {lrn.last}")
    say(f"    Learn.learning       {lrn.learning}   Learn.control {lrn.control}")
    demo.settle(r)
    demo.stack(r)
    say()

    say(f"6. The timeout: a pick lets go by itself after {ui_desk.PICK_S:.0f} s with no click")
    clock.skew += ui.MESSAGE_S + 1
    click_desk(h, "D4")
    h.mouse = (4.0, 4.0)
    draw(1)
    state()
    clock.skew += 12.0
    draw(1)
    say(f"    +12 s (clock moved)  {foot()}")
    clock.skew += 8.0
    draw(1)
    draw(1)
    say("    +8 s more")
    state()


SHOTS = {"big": big, "global": glob, "picked": picked, "goto": goto}


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--out"
            and (sys.argv.index(a) == 0 or sys.argv[sys.argv.index(a) - 1] != "--out")]
    which = args or list(SHOTS)
    h = boot()
    try:
        if which == ["map"]:
            transcript(h)
            if "--out" in sys.argv:
                out = Path(sys.argv[sys.argv.index("--out") + 1])
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text("\n".join(demo.lines) + "\n")
            return
        for name in which:
            SHOTS[name](h)
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
