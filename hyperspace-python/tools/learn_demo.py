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
  learn    plan 17 WP2: the menu's Learn desk / Learn hand ▸ left / right;
           the session's two wrong-hand cases replayed with a bare learn
           and with "Learn hand ▸ left"; a knob bump during a hand learn
           doing its own job; a fader and SHIFT working through a desk
           learn; the global layer refusing and leaving it armed — with
           the footer's line at each step.

It always runs on a fresh temp home of its own (`undo_demo` sets
`HYPERSPACE_HOME` before anything reads it): it cannot touch ~/Hyperspace.

  uv run python tools/learn_demo.py unbind [--out docs/plans/assets/17-learn-and-the-desk/unbind-demo.txt]
"""

# ruff: noqa: I001 — undo_demo is imported first, on purpose: it sets
# HYPERSPACE_HOME to a temp home before anything reads it
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import undo_demo as demo

import pytest
from imgui_bundle import imgui, implot
from test_ui_shell import menu as read_menu

from hyperspace import learn, undo
from hyperspace.library import PRESETS
from hyperspace.params import Kind
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


def footer(r, panel) -> str:
    """The footer's message slot as the panel draws it now (one frame of
    the open page; the panel's clock is the demo's), with its colour."""
    from hyperspace import ui

    ui.time = SimpleNamespace(monotonic=lambda: r.t)         # MESSAGE_S in the demo's time
    names = {(round(c.x, 3), round(c.y, 3)): n
             for n, c in (("red", ui.RED), ("warning", ui.WARN), ("faint", ui.FAINT))}
    seen: list[str] = []
    real = imgui.text_colored

    def text_colored(col, s):
        if s.startswith("·  ") and not s.startswith("·  dim"):
            seen.append(f"{s}   [{names.get((round(col.x, 3), round(col.y, 3)), '?')}]")
        return real(col, s)
    imgui.text_colored = text_colored
    try:
        imgui.new_frame()
        panel.draw(demo.DT, 60.0)
        imgui.end_frame()
    finally:
        imgui.text_colored = real
    return seen[0] if seen else "(empty)"


def step(r, panel, what: str, *msgs, hands=None, n: int = 1) -> None:
    """One thing happens (desk messages, or hands in view), then the footer."""
    r.ports.queue.extend(msgs)
    for _ in range(n):
        if hands is not None:
            r.tracker.put(*hands)
        demo.frames(r)
    say(f"  {what}")
    say(f"      footer: {footer(r, panel)}")


def hand_cases(r, panel, pid: str) -> None:
    """Plan 17 §1 row 1's two measured cases (tests/test_hands.py builds
    the frames): replayed with a bare learn — any source, as every learn
    was before — and with "Learn hand ▸ left"."""
    from test_hands import _wrong_hand_cases

    lrn, table = r.learn, r.router.table
    for name, frames in _wrong_hand_cases().items():
        say(f"  case: the left hand rolls on purpose while {name}")
        for label, want in (("a bare Learn, as before", None), ("Learn hand ▸ left", "hand:left")):
            for _ in range(40):                              # both hands out, the box empty
                r.tracker.put()
                demo.frames(r)
            for _ in range(20):                              # the left hand, still, in the box
                r.tracker.put(frames[0][0])
                demo.frames(r)
            lrn.arm(pid, want)
            armed = footer(r, panel)
            at = None
            for k, (left, right) in enumerate(frames + [frames[-1]] * 60):
                r.tracker.put(*[h for h in (left, right) if h is not None])
                demo.frames(r)
                if lrn.learning is None:
                    at = k
                    break
            row = next(iter(table.routes_to(pid)), None)
            say(f"    {label:<24} armed:  {armed}")
            say(f"    {'':<24} frame {at}: {lrn.last}")
            say(f"    {'':<24} the route: {row.source if row else None}")
            lrn.unbind(pid, desk=False)                      # clear it for the next run
            demo.settle(r)
            footer(r, panel)                                 # …and let the footer forget it
            r.t += 5.0
        say()


def learn_demo() -> None:
    import mido

    from hyperspace import apc40

    r = demo.boot()
    panel = panel_over(r)
    demo.frames(r, 5)
    r.undo.clear()
    lrn, table, reg = r.learn, r.router.table, r.reg
    # a param nothing performs and no knob maps in this preset, and the page that draws it
    pid, page = next(
        (p.id, k) for g, k in (("view", "view"), ("view", "faces"), ("camera", "camera"),
                               ("fx", "fx")) for p in reg.group(g)
        if p.kind is Kind.CONTINUOUS and p.modulatable and not learn.bound(table, p.id)[0] and not table.routes_to(p.id)
        and read_menu(panel, pytest.MonkeyPatch(), p.id, k)[0])

    def cc(n, v, ch=0):
        return mido.Message("control_change", channel=ch, control=n, value=v)

    def note(n, v=127):
        return mido.Message("note_on" if v else "note_off", note=n, velocity=v)

    def at(p):
        return round(p.norm * 127)
    say("Plan 17 WP2 — a learn that cannot pick the wrong source (headless: no window, no "
        "device, no camera;")
    say("the desk's messages are put on fake ports, the hands are synthetic, the menu and the "
        "footer are read as text)")
    say(f"home: <home>  ·  preset: {r.lib.current(PRESETS)}")
    say()
    say("1. The menu")
    show_menu(r, panel, pid, page)
    say()
    say("2. The session's wrong hand — the two measured cases, each replayed twice")
    hand_cases(r, panel, pid)
    say("3. A knob bump during a hand learn does its own job")
    bright = reg["view.bright"]
    desk = [b.to_json() for b in table.desk()]
    lrn.arm(pid, "hand:left")
    step(r, panel, f"right-click {reg[pid].label} → Learn hand ▸ left", hands=())
    b0 = bright.text()
    step(r, panel, "turn K1 (track knob 1)", cc(0x30, at(bright)), cc(0x30, at(bright) - 30))
    say(f"      Brightness {b0} → {bright.text()}  ·  still armed: {lrn.learning} / {lrn.want}"
        f"  ·  desk rows changed: {[b.to_json() for b in table.desk()] != desk}")
    lrn.arm(None)
    step(r, panel, "click the footer's line (Learn.arm(None))")
    say()
    say("4. A fader and SHIFT work through a desk learn; the global layer refuses and it "
        "stays armed")
    lrn.arm(pid, "desk")
    step(r, panel, f"right-click {reg[pid].label} → Learn desk")
    post = reg["band.2.post"]
    p0 = post.text()
    step(r, panel, "move S3 (track fader 3)", cc(apc40.CC_FADER, at(post), 2),
         cc(apc40.CC_FADER, min(127, at(post) + 25), 2))
    say(f"      {post.label} (band 3) {p0} → {post.text()}  ·  still armed: {lrn.learning}")
    step(r, panel, "press SHIFT", note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))
    say(f"      layer: {table.layer}  ·  still armed: {lrn.learning}")
    step(r, panel, "turn K1 (track knob 1)", cc(0x30, 64))
    say(f"      refused: {lrn.refused}  ·  still armed: {lrn.learning}  ·  desk rows changed: "
        f"{[b.to_json() for b in table.desk()] != desk}")
    r.t += 4.5
    step(r, panel, "4.5 s later")
    step(r, panel, "press SHIFT again", note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))
    say(f"      layer: {table.layer}  ·  still armed: {lrn.learning}")
    step(r, panel, "turn D5 (device knob 5)", cc(0x14, 64))
    row = next(b for b in table.desk() if b.target == pid)
    say(f"      the row: {row.source} → {row.target}  op {row.op}  layer {row.layer}  "
        f"feedback {row.feedback}  ·  armed: {lrn.learning}")
    demo.settle(r)
    demo.stack(r)
    ctrl_z(r)
    say(f"      desk rows as before the learn: {[b.to_json() for b in table.desk()] == desk}")
    say()
    say("5. With no MIDI adapter (panel.midi = None): Learn desk is still offered; until the "
        "on-screen desk")
    say("   takes clicks (plan 17 WP4) nothing can complete it, and the line says so")
    panel.midi = None
    r.t += 5.0
    lrn.arm(pid, "desk")
    step(r, panel, f"right-click {reg[pid].label} → Learn desk")
    lrn.arm(None)


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "unbind"
    {"unbind": unbind_demo, "learn": learn_demo}[which]()
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(demo.lines) + "\n")


if __name__ == "__main__":
    main()
