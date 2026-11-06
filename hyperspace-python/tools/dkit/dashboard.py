"""The dkit primitives composed into the Hyperspace dashboard, in Dear ImGui.

This is the demo the kit exists for: the same surface as
prototypes/dashboard/, drawn with nothing but the helpers in draw.py, on the
project's own stack, headless.

    HYPERSPACE_HOME=$(mktemp -d) uv run python tools/dkit/dashboard.py \
        --out /tmp/dkit --theme dark

Layout follows the house pattern (ui_players.lay_out, ui_players.py:122-176):
a pure function of width that returns every rectangle, with no imgui in it, so
it can be reasoned about and tested without a GL context. Drawing is a second
pass over those rects.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import glfw
import numpy as np
import OpenGL.GL as GL
from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import draw as D          # noqa: E402
import gradient as G      # noqa: E402
import box as B           # noqa: E402
import interact as I      # noqa: E402
import menu as M          # noqa: E402
import tokens as T        # noqa: E402
from ease import Anim     # noqa: E402

SHAPES = json.loads(
    (HERE / "../../../prototypes/dashboard/src/data/shapes.json")
    .resolve().read_text()
)

# BANDS, mirroring hyperspace/bands.py: each frequency band drives one plane.
BANDS = [("SUB", "ZW", 20, 60, 1), ("BASS", "XW", 60, 160, 1),
         ("MIDB", "YW", 160, 400, -1), ("MID", "XY", 400, 1200, -1),
         ("UPR", "XZ", 1200, 4000, 1), ("AIR", "YZ", 4000, 14000, -1)]
CEIL = 2.6

ROW_MENU = [
    M.Item("open", "Open in catalog", icon="eye"),
    M.Item("copy", "Copy Schl\u00e4fli", icon="copy", shortcut="\u2318C"),
    M.Item("pin", "Pin to scene", icon="layers"),
    M.sep(),
    M.heading("Danger"),
    M.Item("remove", "Remove from view", icon="trash-2",
           variant="destructive"),
]

NAV = [("Overview", "gauge"), ("Catalog", "shapes"), ("Scenes", "layers"),
       ("Analyzer", "activity"), ("Routing", "waves")]
SOURCES = [("Audio in", "music"), ("Solids", "box"), ("Compounds", "boxes"),
           ("Effects", "sparkles")]
TABS = ["All", "4-polytopes", "Regular", "Stars", "Solids"]
FILTERS = [
    lambda s: True,
    lambda s: s["dims"] == 4,
    lambda s: s["family"] == "Regular polytopes",
    lambda s: s["family"].startswith("Star"),
    lambda s: s["family"].endswith("solids"),
]


def filtered(tab: int) -> list:
    return [s for s in SHAPES if FILTERS[tab](s)]

STATS = [
    ("Shapes in catalog", "101", "+43", True, "Catalog complete",
     "61 four-dimensional, 40 three-dimensional"),
    ("Frame rate", "59.6 fps", "-0.4", False, "Holding the vsync budget",
     "16.8 ms mean frame, 2.1 ms headroom"),
    ("Rotation planes", "6 / 6", "all live", True, "Every plane driven",
     "XY · XZ · YZ · XW · YW · ZW"),
    ("Analyzer load", "4.5%", "+0.3%", True, "FFT under budget",
     "2048-point window at 60 Hz"),
]


def ticks(n=180, seed=0x4d21):
    """The same seeded stand-in for a live analyzer frame the React side uses."""
    rnd = np.random.default_rng(seed)
    out, state = [], [0.4] * len(BANDS)
    for _ in range(n):
        row = []
        for k in range(len(BANDS)):
            inertia = 0.82 - k * 0.07
            state[k] = state[k] * inertia + rnd.random() * (1 - k * 0.09) * (1 - inertia)
            row.append(state[k] * CEIL)
        out.append(row)
    return out


# --------------------------------------------------------------------------
# layout: a pure function of size, no imgui
# --------------------------------------------------------------------------

@dataclass
class Rects:
    sidebar: tuple = (0, 0, 0, 0)
    nav: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    header: tuple = (0, 0, 0, 0)
    stats: list = field(default_factory=list)
    bands_card: tuple = (0, 0, 0, 0)
    facets: list = field(default_factory=list)
    routing_card: tuple = (0, 0, 0, 0)
    routing_rows: list = field(default_factory=list)
    table_tabs: tuple = (0, 0, 0, 0)
    table_rows: list = field(default_factory=list)
    table_head: tuple = (0, 0, 0, 0)
    cols: list = field(default_factory=list)


COL_PAD = 14      # a right-aligned cell stops short of the next column
SIDEBAR_W = 240
HEADER_H = 48
GUT = 24
CARD_GAP = 16


def lay_out(w: int, h: int, n_rows: int | None = None) -> Rects:
    r = Rects()
    r.sidebar = (0, 0, SIDEBAR_W, h)

    y = 16 + 56
    for i, _ in enumerate(NAV):
        r.nav.append((8, y + i * 34, SIDEBAR_W - 16, 32))
    y2 = y + len(NAV) * 34 + 28
    for i, _ in enumerate(SOURCES):
        r.sources.append((8, y2 + i * 34, SIDEBAR_W - 16, 32))

    cx = SIDEBAR_W
    cw = w - SIDEBAR_W
    r.header = (cx, 0, cw, HEADER_H)

    inner_x = cx + GUT
    inner_w = cw - 2 * GUT
    y = HEADER_H + GUT

    r.stats = [b.as_tuple() for b in B.flex(
        B.Rect(inner_x, y, inner_w, 136),
        [B.Item(0, 136, grow=1) for _ in range(4)], gap=CARD_GAP)]
    y += 136 + CARD_GAP

    r.bands_card = (inner_x, y, inner_w, 258)
    fy = y + 84
    for row in range(2):
        r.facets.extend(b.as_tuple() for b in B.flex(
            B.Rect(inner_x + 20, fy + row * 86, inner_w - 40, 60),
            [B.Item(0, 60, grow=1) for _ in range(3)], gap=24))
    y += 258 + CARD_GAP

    r.routing_card = (inner_x, y, inner_w, 196)
    ry = y + 56
    for i in range(6):
        r.routing_rows.append((inner_x + 20, ry + i * 22, inner_w - 40, 18))
    y += 196 + CARD_GAP

    r.table_tabs = (inner_x, y, 0, 32)
    y += 32 + 12
    r.table_head = (inner_x, y, inner_w, 36)
    y += 36
    if n_rows is None:                      # fill whatever height is left
        n_rows = max(1, int((h - y - GUT) // 34))
    for i in range(n_rows):
        r.table_rows.append((inner_x, y + i * 34, inner_w, 34))

    # Shape | Kind | Schlafli | Dim | Cells | Family — weights, and flex
    # resolves them. The old version hand-summed six fractions that had to
    # add to 1.0, which is a constraint nothing checked.
    weights = [22, 28, 13, 6, 8, 20]
    r.cols = [(b.x, b.w) for b in B.flex(
        B.Rect(inner_x, y, inner_w, 1),
        [B.Item(0, 1, grow=w) for w in weights], pad=(0, 12, 0, 12))]
    return r


# --------------------------------------------------------------------------
# drawing
# --------------------------------------------------------------------------

def _dot(dl, cx, cy, col, rad=3.0):
    dl.add_circle_filled(imgui.ImVec2(cx + rad, cy), rad, D._u32(col))


def paint(ui: I.Ui, r: Rects, w, h, series, state):
    dl, faces, theme, grad_tex = ui.dl, ui.faces, ui.theme, ui.grad_tex
    bgc = T.rgba("background", theme=theme)
    D.fill(dl, 0, 0, w, h, bgc)

    # ---- sidebar ----------------------------------------------------------
    D.fill(dl, *r.sidebar[:2], r.sidebar[2], r.sidebar[3], T.rgba("sidebar", theme=theme))
    D.fill(dl, SIDEBAR_W - 1, 0, 1, h, T.rgba("border", theme=theme))

    D.fill(dl, 12, 16, 32, 32, T.rgba("primary", theme=theme), D.RADII["md"])
    D.label(dl, 24, 16, "H", faces, "semibold", 16,
            T.rgba("primary-foreground", theme=theme), baseline_box=32)
    D.label(dl, 54, 14, "Hyperspace", faces, "semibold", 14,
            T.rgba("foreground", theme=theme), baseline_box=18)
    D.label(dl, 54, 31, "4D polytope visualizer", faces, "regular", 12,
            T.rgba("muted-foreground", theme=theme), baseline_box=14)

    for i, ((name, ic), rect) in enumerate(zip(NAV, r.nav)):
        if I.sidebar_item(ui, f"nav.{i}", *rect, name, icon=ic,
                          active=(i == state["nav"])).clicked:
            state["nav"] = i
    D.label(dl, 18, r.sources[0][1] - 22, "Sources", faces, "medium", 12,
            T.rgba("muted-foreground", theme=theme), baseline_box=16)
    for i, ((name, ic), rect) in enumerate(zip(SOURCES, r.sources)):
        I.sidebar_item(ui, f"src.{i}", *rect, name, icon=ic)

    # ---- header -----------------------------------------------------------
    hx, hy, hw, hh = r.header
    D.fill(dl, hx, hy + hh - 1, hw, 1, T.rgba("border", theme=theme))
    D.label(dl, hx + GUT, hy, "Overview", faces, "medium", 16,
            T.rgba("foreground", theme=theme), baseline_box=hh)
    bw = D.text_w("Overview", faces, "medium", 16)
    bx = hx + GUT + bw + 12
    D.box(dl, bx, hy + (hh - 20) / 2, 86, 20,
          border_col=T.rgba("border", theme=theme), radius=T.RADII["4xl"])
    _dot(dl, bx + 8, hy + hh / 2, (0.20, 0.83, 0.60, 1.0), 3.0)
    D.label(dl, bx + 20, hy + (hh - 20) / 2, "Rendering", faces, "medium", 12,
            T.rgba("foreground", theme=theme), baseline_box=20)
    I.button(ui, "hdr.github", hx + hw - GUT - 72, hy + (hh - 32) / 2, 72, 32,
             "GitHub", variant="ghost")

    # ---- stat cards -------------------------------------------------------
    for (title, value, delta, up, head, detail), rect in zip(STATS, r.stats):
        x, y, cw, ch = rect
        D.card(dl, {"x": x, "y": y, "w": cw, "h": ch, "variant": "gradient"},
               theme, grad_tex)
        D.label(dl, x + 20, y + 16, title, faces, "regular", 14,
                T.rgba("muted-foreground", theme=theme), baseline_box=20)
        D.label(dl, x + 20, y + 38, value, faces, "semibold", 30,
                T.rgba("foreground", theme=theme), baseline_box=36, tabular=True)
        # shadcn's badge: gap-1 (4), px-2 (8) but pl-1.5 (6) with a leading
        # icon, and [&>svg]:size-3 (12). Measured, not guessed - the hand
        # offsets this replaces put the label a pixel inside the icon.
        f = B.Flow(gap=4).icon("trending-up" if up else "trending-down", 12)
        D.flow_text(f, delta, faces, "medium", 12, tabular=True)
        pill_w = f.width() + 6 + 8
        pill = B.Rect(x + cw - 20 - pill_w, y + 14, pill_w, 20)
        D.box(dl, *pill.as_tuple(),
              border_col=T.rgba("border", theme=theme), radius=T.RADII["4xl"])
        D.draw_flow(dl, f.place(pill.pad(0, 8, 0, 6), "start"), faces,
                    T.rgba("foreground", theme=theme))
        g = B.Flow(gap=6)
        D.flow_text(g, head, faces, "medium", 14)
        g.icon("trending-up" if up else "trending-down", 15)
        D.draw_flow(dl, g.place(B.Rect(x + 20, y + ch - 52, cw - 40, 20),
                                "start"), faces,
                    T.rgba("foreground", theme=theme))
        D.label(dl, x + 20, y + ch - 32, detail, faces, "regular", 13,
                T.rgba("muted-foreground", theme=theme), baseline_box=18,
                max_w=cw - 40)

    # ---- band levels ------------------------------------------------------
    x, y, cw, ch = r.bands_card
    D.card(dl, {"x": x, "y": y, "w": cw, "h": ch, "variant": "plain"}, theme, None)
    D.label(dl, x + 20, y + 14, "Band levels", faces, "medium", 16,
            T.rgba("foreground", theme=theme), baseline_box=20)
    D.label(dl, x + 20, y + 34, "Each frequency band drives one rotation plane",
            faces, "regular", 13, T.rgba("muted-foreground", theme=theme),
            baseline_box=18)
    ink = T.rgba("foreground", theme=theme)
    for i, (rect, (name, plane, *_)) in enumerate(zip(r.facets, BANDS)):
        fx, fy, fw, fh = rect
        D.label(dl, fx, fy - 18, name, faces, "medium", 12, ink, baseline_box=14)
        nw = D.text_w(name, faces, "medium", 12)
        D.label(dl, fx + nw + 6, fy - 18, plane, faces, "regular", 12,
                T.rgba("muted-foreground", theme=theme), baseline_box=14)
        vals = [t[i] for t in series]
        D.label(dl, fx, fy - 18, f"{vals[-1]:.2f}", faces, "regular", 12,
                T.rgba("muted-foreground", theme=theme), align="right",
                box_w=fw, baseline_box=14, tabular=True)
        D.fill(dl, fx, fy + fh, fw, 1, T.rgba("border", theme=theme))
        D.sparkline(dl, fx, fy, fw, fh, vals, ink, lo=0.0, hi=CEIL)

    # ---- plane routing ----------------------------------------------------
    x, y, cw, ch = r.routing_card
    D.card(dl, {"x": x, "y": y, "w": cw, "h": ch, "variant": "plain"}, theme, None)
    D.label(dl, x + 20, y + 14, "Plane routing", faces, "medium", 16, ink,
            baseline_box=20)
    D.label(dl, x + 20, y + 34, "Band to rotation plane, with the latest level",
            faces, "regular", 13, T.rgba("muted-foreground", theme=theme),
            baseline_box=18)
    last = series[-1]
    for i, (rect, (name, plane, lo, hi, direction)) in enumerate(zip(r.routing_rows, BANDS)):
        rx, ry, rw, rh = rect
        D.label(dl, rx, ry, name, faces, "medium", 12, ink, baseline_box=rh)
        D.box(dl, rx + 48, ry, 34, rh, fill_col=T.rgba("secondary", theme=theme),
              radius=T.RADII["4xl"])
        D.label(dl, rx + 48, ry, plane, faces, "medium", 11, ink,
                align="center", box_w=34, baseline_box=rh)
        bar_x = rx + 94
        bar_w = rw - 94 - 190
        D.meter(dl, bar_x, ry + rh / 2 - 4, bar_w, 8, last[i] / CEIL, theme)
        D.label(dl, rx + rw - 186, ry, f"{lo}–{hi} Hz", faces, "regular", 12,
                T.rgba("muted-foreground", theme=theme), align="right",
                box_w=110, baseline_box=rh, tabular=True)
        D.label(dl, rx + rw - 60, ry, f"{'+' if direction > 0 else '−'}{last[i]:.2f}",
                faces, "regular", 12, ink, align="right", box_w=60, baseline_box=rh,
                tabular=True)

    # ---- table ------------------------------------------------------------
    tx, ty, _, th = r.table_tabs
    picked, _tabs_w = I.tabs(ui, "tab", tx, ty, th, TABS, state["tab"])
    if picked is not None:
        state["tab"] = picked
    rows = filtered(state["tab"])
    shown = min(len(r.table_rows), len(rows))
    D.label(dl, tx, ty, f"Showing {shown} of {len(rows)}", faces, "regular", 13,
            T.rgba("muted-foreground", theme=theme), align="right",
            box_w=r.table_head[2], baseline_box=th, tabular=True)

    hx, hy, hw, hh = r.table_head
    D.fill(dl, hx, hy, hw, hh, T.rgba("muted", theme=theme), 0.0)
    D.fill(dl, hx, hy + hh - 1, hw, 1, T.rgba("border", theme=theme))
    heads = ["Shape", "Kind", "Schläfli", "Dim", "Cells", "Family"]
    aligns = ["left", "left", "left", "center", "right", "left"]
    for (cxp, cwid), head, al in zip(r.cols, heads, aligns):
        D.label(dl, cxp, hy, head, faces, "medium", 13, ink, align=al,
                box_w=cwid - (COL_PAD if al == "right" else 0), baseline_box=hh)

    for ri, (row, rect) in enumerate(zip(rows[:shown], r.table_rows)):
        rx, ry, rw, rh = rect
        hovered = I.row(ui, f"row.{ri}", rx, ry, rw, rh).hot
        # the kebab reveals on row hover and stays while its menu is open.
        # row_action submits it every frame regardless - see its docstring for
        # why gating submission on the hover makes it unclickable.
        mkey = f"rowmenu.{ri}"
        kb = B.Rect(rx + rw - 30, ry + (rh - 26) / 2, 26, 26)
        if I.row_action(ui, f"kebab.{ri}", kb.x, kb.y, kb.w,
                        "ellipsis-vertical", hovered,
                        pinned=imgui.is_popup_open(mkey), glyph=15).clicked:
            imgui.open_popup(mkey)
        # hangs off the kebab, not off the mouse
        picked = M.popup(ui, mkey, ROW_MENU, anchor=kb)
        if picked:
            state["said"] = f"{picked} \u00b7 {row['name']}"
        D.fill(dl, rx, ry + rh - 1, rw, 1, T.rgba("border", theme=theme))
        cells = [row["name"], row["kind"], row["schlafli"] or "—",
                 f"{row['dims']}D",
                 str(row["cells"]) if row["cells"] else "—", None]
        for (cxp, cwid), val, al in zip(r.cols, cells, aligns):
            if val is None:
                bw2 = D.text_w(row["family"], faces, "medium", 12) + 16
                D.box(dl, cxp, ry + (rh - 20) / 2, bw2, 20,
                      border_col=T.rgba("border", theme=theme),
                      radius=T.RADII["4xl"])
                D.label(dl, cxp, ry + (rh - 20) / 2, row["family"], faces,
                        "medium", 12, ink, align="center", box_w=bw2,
                        baseline_box=20)
            else:
                col = ink if al != "left" or val == row["name"] else \
                    T.rgba("muted-foreground", theme=theme)
                variant = "medium" if val == row["name"] else "regular"
                D.label(dl, cxp, ry, val, faces, variant, 13, col, align=al,
                        box_w=cwid - (COL_PAD if al == "right" else 0),
                        baseline_box=rh, max_w=cwid - COL_PAD,
                        tabular=al != "left")


WIN_FLAGS = (imgui.WindowFlags_.no_title_bar | imgui.WindowFlags_.no_resize
             | imgui.WindowFlags_.no_move | imgui.WindowFlags_.no_scrollbar
             | imgui.WindowFlags_.no_scroll_with_mouse
             | imgui.WindowFlags_.no_collapse
             | imgui.WindowFlags_.no_bring_to_front_on_focus
             | imgui.WindowFlags_.no_background)


def _boot(theme_name, w, h, *, visible: bool, retina: bool = False):
    """A window, a context, the fonts and the gradient ramp.

    `retina` is the difference between looking at this and measuring it.
    Screenshot paths want 1:1 pixels so the framebuffer matches the spec
    rects, which on macOS means asking for a non-Retina framebuffer. A window
    a person actually looks at wants the opposite: forcing 1:1 there makes
    macOS upscale a logical-resolution image, and it looks grainy.
    """
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    for hint, v in ((glfw.CONTEXT_VERSION_MAJOR, 3), (glfw.CONTEXT_VERSION_MINOR, 3),
                    (glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE),
                    (glfw.OPENGL_FORWARD_COMPAT, True), (glfw.VISIBLE, visible),
                    (glfw.SAMPLES, 0),
                    (glfw.COCOA_RETINA_FRAMEBUFFER, retina)):
        glfw.window_hint(hint, v)
    win = glfw.create_window(w, h, "Hyperspace \u00b7 dkit", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the window")
    glfw.make_context_current(win)
    imgui.create_context()
    impl = GlfwRenderer(win)
    io = imgui.get_io()
    ww, _ = glfw.get_window_size(win)
    fw, _ = glfw.get_framebuffer_size(win)
    density = (fw / ww) if ww else 1.0
    # glyphs are rasterized at the display's real pixel density; without this
    # they are cut at logical size and scaled up, which is the other half of
    # looking grainy on a Retina screen
    faces = D.load_faces(io, HERE, density)
    LL = T.LIGHT_L if theme_name == "light" else T.DARK_L
    grad = G.upload_1d(G.ramp_oklab(*G.card_gradient(LL), n=256))
    return win, impl, io, faces, grad


def _draw(ui_box, rects, w, h, series, state, bgc):
    """One frame, inside the full-window imgui window. Returns the Ui.

    w/h are LOGICAL points. The caller owns the GL viewport, which is in
    framebuffer pixels and is not the same thing on a Retina display.
    """
    GL.glClearColor(bgc[0], bgc[1], bgc[2], 1.0)
    GL.glClear(GL.GL_COLOR_BUFFER_BIT)
    imgui.set_next_window_pos(imgui.ImVec2(0, 0))
    imgui.set_next_window_size(imgui.ImVec2(w, h))
    imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(0, 0))
    imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
    imgui.begin("##dkit", None, WIN_FLAGS)
    # a real window's list, not the background list: replay.keep
    # (hyperspace/replay.py:91) only carries the page window's own list into
    # the canvas tap
    ui_box.dl = imgui.get_window_draw_list()
    paint(ui_box, rects, w, h, series, state)
    imgui.end()
    imgui.pop_style_var(2)
    return ui_box


def live(theme_name: str, w: int, h: int) -> None:
    """Open the dashboard and run it until the window is closed.

    A real event loop with real timing, so the 150ms transitions run off the
    clock rather than off a scripted dt. Resizing re-lays-out; the table
    grows and shrinks with the window.
    """
    import time
    win, impl, io, faces, grad = _boot(theme_name, w, h, visible=True,
                                       retina=True)
    glfw.swap_interval(1)
    # without this Escape does not dismiss a popup - see render()
    io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard
    theme = T.LIGHT if theme_name == "light" else T.DARK
    bgc = T.rgba("background", theme=theme)
    series = ticks()
    state = {"tab": 0, "nav": 0}
    ui = I.Ui(None, faces, theme, Anim(), grad)
    rects, last_size = None, None
    prev = time.perf_counter()

    while not glfw.window_should_close(win):
        glfw.poll_events()
        impl.process_inputs()
        now = time.perf_counter()
        dt = min(now - prev, 0.05)          # a stall must not jump the easing
        prev = now
        # layout in LOGICAL points (what imgui draws in); the GL viewport in
        # pixels (what the framebuffer is). On a Retina screen they differ by
        # 2x and conflating them halves every rect.
        lw, lh = glfw.get_window_size(win)
        fw, fh = glfw.get_framebuffer_size(win)
        if lw <= 0 or lh <= 0 or fw <= 0 or fh <= 0:
            continue
        if (lw, lh) != last_size:
            rects, last_size = lay_out(lw, lh), (lw, lh)
        imgui.new_frame()
        GL.glViewport(0, 0, fw, fh)
        _draw(ui, rects, lw, lh, series, state, bgc)
        imgui.render()
        impl.render(imgui.get_draw_data())
        ui.frame_done(dt)
        glfw.swap_buffers(win)

    impl.shutdown()
    glfw.terminate()


def render(theme_name: str, w: int, h: int, *, script=None, dt=1 / 60.0,
           keys=None):
    """Draw the dashboard, optionally stepping a script of mouse positions.

    `script` is a list of (x, y) or (x, y, down) — one per frame — so a hover
    or a click can be driven headlessly. Returns a list of frames (the last
    one only, if no script was given).
    """
    theme = T.LIGHT if theme_name == "light" else T.DARK
    if not glfw.init():
        raise SystemExit("GLFW failed to initialise (no display?)")
    for hint, v in ((glfw.CONTEXT_VERSION_MAJOR, 3), (glfw.CONTEXT_VERSION_MINOR, 3),
                    (glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE),
                    (glfw.OPENGL_FORWARD_COMPAT, True), (glfw.VISIBLE, False),
                    (glfw.SAMPLES, 0),
                    # 1:1 pixels on a Retina Mac too, or the framebuffer comes
                    # back at 2x and every rect in the spec is half the size it
                    # claims. No-op off macOS.
                    (glfw.COCOA_RETINA_FRAMEBUFFER, False)):
        glfw.window_hint(hint, v)
    win = glfw.create_window(w, h, "dkit dashboard", None, None)
    if not win:
        glfw.terminate()
        raise SystemExit("could not create the hidden window")
    glfw.make_context_current(win)
    ctx = imgui.create_context()
    impl = GlfwRenderer(win)

    io = imgui.get_io()
    faces = D.load_faces(io, HERE)

    LL = T.LIGHT_L if theme_name == "light" else T.DARK_L
    grad_tex = G.upload_1d(G.ramp_oklab(*G.card_gradient(LL), n=256))
    series = ticks()
    rects = lay_out(w, h)
    bgc = T.rgba("background", theme=theme)
    anim = Anim()
    state = {"tab": 0, "nav": 0}
    render.last_state = state           # so a caller can read what the script did

    # two warm-up frames settle the backend and the font atlas, and let the
    # animation store see every widget once before anything is scripted
    steps = [None, None] + list(script or [None])
    # keys is [(frame_index_within_script, imgui.Key)] - pressed and released
    # on that frame, for checking things ImGui owns, like Escape dismissal
    keymap = {}
    for at, k in (keys or []):
        keymap.setdefault(at + 2, []).append(k)
    # ImGui routes Escape (and every other key) through its nav system, which
    # is OFF by default - so without this a menu cannot be dismissed with the
    # keyboard at all. tests/ui_driver.py:172 turns it on for the same reason.
    io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard
    frames = []
    for i, mouse in enumerate(steps):
        glfw.poll_events()
        impl.process_inputs()
        if mouse is not None:
            io.add_mouse_pos_event(float(mouse[0]), float(mouse[1]))
            if len(mouse) > 2:            # (x, y, down) drives the button too
                io.add_mouse_button_event(0, bool(mouse[2]))
        for k in keymap.get(i, ()):
            io.add_key_event(k, True)
            io.add_key_event(k, False)
        imgui.new_frame()
        GL.glClearColor(bgc[0], bgc[1], bgc[2], 1.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        imgui.set_next_window_pos(imgui.ImVec2(0, 0))
        imgui.set_next_window_size(imgui.ImVec2(w, h))
        imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(0, 0))
        imgui.push_style_var(imgui.StyleVar_.window_border_size, 0.0)
        imgui.begin("##dkit", None, WIN_FLAGS)
        # a real window's list, not the background list: replay.keep
        # (hyperspace/replay.py:91) only carries the page window's own list
        # into the canvas tap
        ui = I.Ui(imgui.get_window_draw_list(), faces, theme, anim, grad_tex)
        paint(ui, rects, w, h, series, state)
        imgui.end()
        imgui.pop_style_var(2)

        imgui.render()
        impl.render(imgui.get_draw_data())
        GL.glFinish()
        ui.frame_done(dt)

        if i >= 2:
            fw, fh = glfw.get_framebuffer_size(win)
            raw = GL.glReadPixels(0, 0, fw, fh, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
            px = np.frombuffer(raw, np.uint8).reshape(fh, fw, 3)[::-1]
            if not px.any():
                raise SystemExit("the hidden window read back black")
            frames.append(px.copy())

    impl.shutdown()
    imgui.destroy_context(ctx)      # or the next render() inherits this state
    glfw.terminate()
    return frames


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/dkit")
    ap.add_argument("--theme", default="dark", choices=("light", "dark"))
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1100)
    ap.add_argument("--hover", action="store_true",
                    help="emit a frame sequence of a hover easing in and out")
    ap.add_argument("--live", action="store_true",
                    help="open a window and run it until you close it")
    a = ap.parse_args()
    if a.live:
        live(a.theme, a.width, a.height)
        return
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.hover:
        # walk the pointer onto a sidebar item, hold it there, then leave:
        # enough frames either side to show the 150ms ease settle
        tx, ty, tw, th = lay_out(a.width, a.height).nav[2]
        spot = (tx + tw / 2, ty + th / 2)
        away = (a.width - 40, a.height - 40)
        script = [away] * 2 + [spot] * 14 + [away] * 14
        frames = render(a.theme, a.width, a.height, script=script)
        for i, px in enumerate(frames):
            Image.fromarray(px).save(out / f"hover-{a.theme}-{i:03d}.png")
        print(f"wrote {len(frames)} frames to {out}/hover-{a.theme}-*.png")
        return
    px = render(a.theme, a.width, a.height)[-1]
    dest = out / f"dashboard-{a.theme}.png"
    Image.fromarray(px).save(dest)
    print(f"wrote {dest}  {px.shape[1]}x{px.shape[0]}")


if __name__ == "__main__":
    main()
