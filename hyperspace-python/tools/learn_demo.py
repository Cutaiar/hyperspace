#!/usr/bin/env python3
"""Learn and Unbind from the right-click menu, shown headless (plan 17).

Builds the app's objects the way `tools/undo_demo.py` does (its `boot`:
library, registry, router, presets, a Learn, a MidiIO over fake ports, a
HandsIO over synthetic hands, the startup preset, the Undo), puts the
control panel over them in a headless imgui context — no window — and
prints a transcript of what the menu draws and does. The menu is read the
way `tests/test_ui_shell.py::menu` reads it: the popup's `begin` is
answered for it, so nothing here is a real right-click.

  unbind   plan 17 WP1: a param with a knob, a hand route and an LFO
           route — the menu's lines, Unbind by kind and both, Ctrl+Z
           putting all of it back, a fader's param offering no Unbind —
           and the same again with no MIDI adapter on the panel.

It always runs on a fresh temp home of its own (`undo_demo` sets
`HYPERSPACE_HOME` before anything reads it): it cannot touch ~/Hyperspace.

  uv run python tools/learn_demo.py unbind [--out docs/plans/assets/17-learn-and-the-desk/unbind-demo.txt]
"""

# ruff: noqa: I001 — undo_demo is imported first, on purpose: it sets
# HYPERSPACE_HOME to a temp home before anything reads it
from __future__ import annotations

import sys
from pathlib import Path

import undo_demo as demo

import pytest
from imgui_bundle import imgui, implot
from test_ui_shell import menu as read_menu

from hyperspace import undo
from hyperspace.library import PRESETS
from hyperspace.routing import Binding
from hyperspace.ui import Panel, apply_style, load_fonts

say = demo.say


def panel_over(r) -> Panel:
    """The control panel over the booted objects, in a headless imgui
    context the size of the control window."""
    imgui.create_context()
    implot.create_context()
    io = imgui.get_io()
    io.display_size = imgui.ImVec2(960, 900)
    io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
    apply_style()
    load_fonts()
    panel = Panel(r.control, r.audio, r.view, bank=r.lib.project, registry=r.reg, library=r.lib)
    panel.clock, panel.lfos, panel.router, panel.learn = r.clock, r.lfos, r.router, r.learn
    panel.hands, panel.hand_settings, panel.output = r.hands_io, r.settings, r.output
    panel.midi, panel.undo = r.midi, r.undo
    return panel


def show_menu(r, panel, pid: str, page: str, click: str | None = None) -> list[str]:
    """Draw the menu of `pid` once and print it; `click` chooses an item."""
    patch = pytest.MonkeyPatch()
    lines, items = read_menu(panel, patch, pid, page, click=click)
    if click is None:
        say(f"  right-click {r.reg[pid].label} ({page.upper()} page):")
        for s in lines:
            say(f"      {s}")
        for i in items:                 # a submenu's items are listed for Unbind and Learn
            if "/" not in i or i.startswith(("Unbind/", "Learn")):
                say(f"    [ {'    ' if '/' in i else ''}{i.rsplit('/', 1)[-1]} ]")
    else:
        say(f"  click  {click.replace('/', ' ▸ ')}")
        say(f"      learn line: {r.learn.last}")
    return items


def rows_on(r, pid: str) -> str:
    t = r.router.table
    desk = [b for b in t.desk() if b.target == pid]
    return (f"{len(desk)} desk row{'s' * (len(desk) != 1)}, "
            f"{len(t.routes_to(pid))} route{'s' * (len(t.routes_to(pid)) != 1)}")


def ctrl_z(r) -> None:
    undo.undo()
    demo.frames(r, 3)
    say(f"  Ctrl+Z   footer: ·  {r.undo.status}")


def unbind_pass(r, panel, pid: str, fader: str) -> list[str]:
    """The whole Unbind walk on `pid`; returns what was printed."""
    start = len(demo.lines)
    t = r.router.table

    def state():
        return [(b.to_json(), b.layer) for b in t.bindings]
    was = state()
    on_disk = t.path.read_bytes() if t.path.exists() else None
    items = show_menu(r, panel, pid, "view")
    say()
    for kind in ("desk", "route", "both"):
        click = next(i for i in items if i.startswith(f"Unbind/{kind}"))
        show_menu(r, panel, pid, "view", click=click)
        wrote = (t.path.read_bytes() if t.path.exists() else None) != on_disk
        say(f"      now on {pid}: {rows_on(r, pid)}  ·  bindings.json written: {wrote}")
        demo.settle(r)
        demo.stack(r)
        if click.endswith("both"):
            show_menu(r, panel, pid, "view")
        ctrl_z(r)
        back = sorted(map(str, state())) == sorted(map(str, was))
        say(f"      now on {pid}: {rows_on(r, pid)}  ·  every row back: {back}")
        say()
    items = show_menu(r, panel, fader, "audio")
    say(f"      Unbind offered: {any(i.startswith('Unbind') for i in items)}")
    return demo.lines[start:]


def unbind_demo() -> None:
    r = demo.boot()
    panel = panel_over(r)
    demo.frames(r, 5)
    r.undo.clear()
    t = r.router.table
    # a param only a fader maps (invariant, the session's) with no route on it
    pid, fader = "view.speed", next(i for i in ("master.trim", "master.dyn", "master.gain")
                                    if not t.routes_to(i))
    say("Plan 17 WP1 — one Unbind (headless: no window, no device, no hand; the menu is read "
        "as text)")
    say(f"home: <home>  ·  preset: {r.lib.current(PRESETS)}  ·  "
        f"{len(t.routes())} routes, {len(t.desk())} desk rows")
    say()
    say(f"0. {pid} in this preset has a knob and a hand route; add an LFO route, switched off")
    say("   (one performer per parameter: a second enabled route would be the Replace / Keep "
        "prompt)")
    t.add(Binding("lfo:0", pid, "push", 0.3, enabled=False))
    demo.settle(r)
    r.undo.clear()
    say()
    say("1. With the MIDI adapter on the panel (panel.midi is a MidiIO over ports nobody is "
        "plugged into)")
    first = unbind_pass(r, panel, pid, fader)
    say()
    say("2. The same with no MIDI adapter (panel.midi = None, as with [midi] enabled = false)")
    panel.midi = None
    r.undo.clear()
    second = unbind_pass(r, panel, pid, fader)
    say()
    say(f"   the two transcripts are the same, line for line: {first == second}")


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "unbind"
    {"unbind": unbind_demo}[which]()
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(demo.lines) + "\n")


if __name__ == "__main__":
    main()
