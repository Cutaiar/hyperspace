#!/usr/bin/env python3
"""A bank of twenty-four, shown headless and as pictures (plan 19 WP1).

Two things, each on a fresh temp home of its own built like the owner's
(`tests/conftest.py::build_owner_home`: a `mine` show and a copy of
`party` with eight-name banks, three presets saved before the bank grew)
— `HYPERSPACE_HOME` is set by `tools/undo_demo.py` before anything reads
it, so this cannot touch ~/Hyperspace:

  uv run python tools/bank_demo.py
      the transcript → docs/plans/assets/19-presets-and-the-desk/bank-24.txt:
      an eight-slot show opened (its file's bytes unchanged), save-as
      filling the F-keys' holes and then landing on slot 9 — the
      eight-slot file kept once as `.bak-v2-bank8` — the show file's
      `bank` before and after, a second far write that makes no second
      backup, and a backup that cannot be made refusing the write.

  uv run python tools/bank_demo.py --shots
      two PNGs of the PRESETS page beside it — `bank-24.png` and
      `bank-24-more.png` ("more" open) — drawn in a **hidden** GLFW window
      over the same headless objects: not the app, no render window, no
      MIDI port. What the page draws, not what a projector shows.
"""

# ruff: noqa: I001 — undo_demo is imported first, on purpose: it sets
# HYPERSPACE_HOME to a temp home and points pyGLFW at imgui_bundle's libglfw
# before anything loads glfw
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import undo_demo as demo

from conftest import build_owner_home

from hyperspace import library
from hyperspace.library import PRESETS

OUT = Path(__file__).resolve().parents[1] / "docs" / "plans" / "assets" / "19-presets-and-the-desk"
say = demo.say


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def bank_of(path: Path) -> list:
    return json.loads(path.read_text())["bank"]


def folder(path: Path) -> None:
    for p in sorted(path.iterdir()):
        say(f"      {p.name:<34} {p.stat().st_size:>6} bytes  sha {sha(p)}")


def footer(r, fn, *args) -> str:
    """Run `fn` and return the line the footer's message slot shows for it:
    the library line it said (`Library.said` counts each), a warning first."""
    lib = r.lib
    was = dict(lib.said)
    fn(*args)
    if lib.said.get("warning", 0) != was.get("warning", 0):
        return f"warning: {lib.warning}"
    if lib.said.get("status", 0) != was.get("status", 0):
        return f"status: {lib.status}"
    return "(nothing said)"


def transcript(out: Path) -> None:
    home = build_owner_home(demo.HOME)
    shows = home / "projects"
    mine = shows / "mine.hyp.json"
    say("Plan 19 WP1 — a bank of twenty-four. Headless, on a temp home built like the owner's")
    say("(tools/bank_demo.py; <home> is that temp folder, never ~/Hyperspace).")
    say()
    say("1. The home as the build before plan 19 left it: <home>/projects/")
    folder(shows)
    before = mine.read_bytes()
    stamp = mine.stat().st_mtime_ns
    say(f"   mine.hyp.json bank ({len(bank_of(mine))} entries): {bank_of(mine)}")
    say()
    say("2. Launch on it (the show opened last is `mine`), press F2, press Home.")
    r = demo.boot()
    lib, reg, pr = r.lib, r.reg, r.lib.project
    lib.warning = ""        # (this rig's registry has no `desk.slew`: its note is not the demo's)
    reg["preset.load.1"].fire()
    reg["preset.home"].fire()
    demo.frames(r, 30)
    lib.poll()
    say(f"   show: {pr.name}   slots in memory: {len(pr.bank)}   "
        f"filled: {sum(n is not None for n in pr.bank)}   show dirty: {pr.is_dirty()}")
    say(f"   loaded: {lib.current(PRESETS)}   lit slot: {library.slot_key(pr.active)}")
    say(f"   mine.hyp.json bytes unchanged: {mine.read_bytes() == before}   "
        f"mtime unchanged: {mine.stat().st_mtime_ns == stamp}   sha {sha(mine)}")
    say(f"   backups in the home: {sorted(p.name for p in home.rglob('*.bak-*')) or 'none'}")
    say()
    say("3. Two F-keys cleared (the slot menu's \"clear slot\"), then the desk's save-as,")
    say("   four times: the two holes first, then past the F-keys.")
    for k in (6, 7):
        line = footer(r, pr.clear_slot, k)
        say(f"   clear {library.slot_key(k)}                 footer · {line}")
    say(f"   mine.hyp.json bank ({len(bank_of(mine))} entries): {bank_of(mine)}")
    say(f"   backups: {sorted(p.name for p in shows.glob('*.bak-*')) or 'none'}   "
        "(a show that uses only slots 1–8 is written with eight entries)")
    eight = b""
    for _ in range(4):
        reg["view.bright"].set(reg["view.bright"].value * 1.03)
        was = sorted(p.name for p in shows.glob("*.bak-*"))
        if len(bank_of(mine)) == 8:
            eight = mine.read_bytes()                 # the last eight-slot file there was
        line = footer(r, reg["preset.save_new"].fire)
        demo.frames(r, 5)
        new = [n for n in sorted(p.name for p in shows.glob("*.bak-*")) if n not in was]
        say(f"   save-as                  footer · {line}"
            + (f"      ← new file: {new[0]}" if new else ""))
    say(f"   mine.hyp.json bank ({len(bank_of(mine))} entries): {bank_of(mine)}")
    bak = shows / "mine.hyp.json.bak-v2-bank8"
    say(f"   {bak.name} is the file as it was before that write, byte for byte: "
        f"{bak.read_bytes() == eight}   ({len(bank_of(bak))} entries: {bank_of(bak)})")
    say(f"   schema: {json.loads(mine.read_text())['schema']}   show dirty: {pr.is_dirty()}")
    say()
    say("4. A second far write — \"put preset here…\" on slot 20 — makes no second backup.")
    line = footer(r, pr.put_slot, 19, "WAKE")
    say(f"   put WAKE on slot 20      footer · {line}")
    say(f"   mine.hyp.json bank ({len(bank_of(mine))} entries): {bank_of(mine)}")
    say("   <home>/projects/")
    folder(shows)
    say()
    say("5. A backup that cannot be made refuses the write. The other show, `party`, still")
    say("   has its eight-slot file; <home>/projects is made read-only (chmod 555), as a")
    say("   full or locked disk would leave it.")
    pr.load("party")
    party = shows / "party.hyp.json"
    before = party.read_bytes()
    say(f"   show: {pr.name}   party.hyp.json bank ({len(bank_of(party))} entries)")
    os.chmod(shows, 0o555)
    try:
        line = footer(r, pr.put_slot, 11, "NIGHT TWO")
        say(f"   put NIGHT TWO on slot 12 footer · {line}")
        say(f"   under the bank on the page: {pr.bank_error}")
        say(f"   slot 12 in memory: {pr.bank[11]}   show dirty: {pr.is_dirty()}   "
            f"party.hyp.json bytes unchanged: {party.read_bytes() == before}")
        line = footer(r, reg["preset.save_new"].fire)
        say(f"   save-as                  footer · {line}")
        say(f"   slot 9 in memory: {pr.bank[8]}   the preset is in the list: "
            f"{lib.current(PRESETS) in lib.list(PRESETS)}   "
            f"party.hyp.json bytes unchanged: {party.read_bytes() == before}")
    finally:
        os.chmod(shows, 0o755)
    say("   the folder writable again:")
    line = footer(r, pr.put_slot, 11, "NIGHT TWO")
    say(f"   put NIGHT TWO on slot 12 footer · {line}")
    say(f"   party.hyp.json bank ({len(bank_of(party))} entries): {bank_of(party)}")
    say("   <home>/projects/")
    folder(shows)
    say()
    say("6. What an older build does with a long bank (fork 2's known cost): it reads")
    say(f"   bank[:8] = {bank_of(mine)[:8]}")
    say("   — slots 1–8, right — and its next write of that show leaves slots 9–24 out of")
    say("   the file. The presets' files are untouched; mine.hyp.json.bak-v2-bank8 is the")
    say("   file from before any far slot existed.")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(demo.lines) + "\n")
    print(f"\nwrote {out}")


def shots() -> None:
    import glfw
    import numpy as np
    from imgui_bundle import imgui, implot
    from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
    from OpenGL import GL
    from PIL import Image

    from hyperspace.app import CONTROL_SIZE
    from hyperspace.ui import PAGE_KEYS, Panel, apply_style, load_fonts

    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
    glfw.window_hint(glfw.VISIBLE, False)             # never shown
    win = glfw.create_window(*CONTROL_SIZE, "bank shot", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the hidden window")
    glfw.make_context_current(win)
    imgui.create_context()
    implot.create_context()
    apply_style()
    load_fonts()
    impl = GlfwRenderer(win)

    build_owner_home(demo.HOME)
    r = demo.boot()
    lib, reg, pr = r.lib, r.reg, r.lib.project
    # the owner's show with some far slots filled: four save-as from the
    # desk past the full F-keys, three presets put on row 5's slots
    reg["preset.load.4"].fire()                       # TRIP
    for _ in range(4):
        reg["view.bright"].set(reg["view.bright"].value * 1.03)
        reg["preset.save_new"].fire()
    for k, name in ((16, "TRACER"), (17, "BIG BLUE WAVE"), (21, "hands-orbit")):
        pr.put_slot(k, name)
    pr.load_slot(10)                                  # slot 11 loaded: lit
    lib.warning = ""        # (this rig's registry has no `desk.slew`: its note is not the demo's)
    panel = Panel(r.control, r.audio, r.view, bank=pr, registry=reg, library=lib)
    panel.clock, panel.lfos, panel.router, panel.learn = r.clock, r.lfos, r.router, r.learn
    panel.hands, panel.hand_settings, panel.output = r.hands_io, r.settings, r.output
    panel.midi, panel.undo = r.midi, r.undo
    panel.reg["ui.page"].set(PAGE_KEYS.index("presets"))
    more = {"open": False}
    real_header = imgui.collapsing_header

    def header(label, *a):
        if "more" in label:                           # the fold, opened or shut from here
            imgui.set_next_item_open(more["open"])
        return real_header(label, *a)
    imgui.collapsing_header = header

    scroll = {}
    real_page = Panel._page_presets

    def page(self, dt):
        real_page(self, dt)
        scroll["max"] = imgui.get_scroll_max_y()
    Panel._page_presets = page

    def draw(n: int = 8) -> None:
        for _ in range(n):
            demo.frames(r)
            glfw.poll_events()
            impl.process_inputs()
            imgui.new_frame()
            GL.glClearColor(0.0, 0.0, 0.0, 1.0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            panel.draw(demo.DT, 60.0)
            imgui.render()
            impl.render(imgui.get_draw_data())
            GL.glFinish()

    def shoot(name: str) -> None:
        w, h = glfw.get_framebuffer_size(win)
        raw = GL.glReadPixels(0, 0, w, h, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        px = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)[::-1]
        if not px.any():
            raise SystemExit("the hidden window read back black: no picture on this machine")
        OUT.mkdir(parents=True, exist_ok=True)
        Image.fromarray(px).save(OUT / name, optimize=True)
        print(f"wrote {OUT / name}  — {sum(n is not None for n in pr.bank)} of {len(pr.bank)} "
              f"slots filled, {library.slot_key(pr.active)} lit, page scroll range "
              f"{scroll.get('max')} px")

    try:
        draw(12)
        shoot("bank-24.png")
        more["open"] = True
        draw(12)
        shoot("bank-24-more.png")
    finally:
        imgui.collapsing_header = real_header
        Panel._page_presets = real_page
        impl.shutdown()
        glfw.terminate()


def main() -> None:
    if "--shots" in sys.argv[1:]:
        shots()
        return
    out = OUT / "bank-24.txt"
    if "--out" in sys.argv[1:]:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
    transcript(out)


if __name__ == "__main__":
    sys.exit(main())
