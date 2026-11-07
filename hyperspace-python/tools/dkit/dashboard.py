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
import comp_button as CB
import comp_combobox as CC
import comp_gallery as CG
import comp_context_menu as CX
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

NAV = [("Overview", "gauge"), ("Gallery", "boxes"), ("Catalog", "shapes"),
       ("Scenes", "layers"), ("Analyzer", "activity"), ("Routing", "waves")]
# Which nav row shows the contact sheet rather than the dashboard body.
# Named rather than written as a 1 at the branch, because the only thing
# worse than a magic number is a magic number that moves when somebody adds
# a nav item above it.
NAV_GALLERY = 1
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

# The Tier 1 controls' starting values, in one place so `live` and `render`
# cannot drift apart.
# The control rows' label column. A module constant because the interaction
# tests need to know where a control starts, and a number copied into them
# by hand is a number that goes stale the moment the layout moves - which is
# exactly what happened when this went from 92 to 74.
CTL_LABEL_W = 74.0

# A table row's height. One constant, because lay_out counts slots with it
# and paint places rows with it, and the two disagreeing is a whole class of
# bug.
ROW_H = 34.0

# Rows per column in the Controls card. Adding one grows the card on its own
# - intrinsic sizing - where before it would have needed the card's height
# edited to match.
CTL_ROWS = 6

# How many table rows the page carries. The PAGE scrolls, so this is a
# content decision rather than a function of the window.
N_TABLE_ROWS = 14


PLANES = ("XY", "XZ", "XW", "YZ", "YW", "ZW")

CTL_STATE = {
    "cutoff": 2400.0,
    "bypass": False,
    "plane": "XW",
    "name": "600-cell",
    "mix": 0.35,
    "win_lo": 0.25,
    "win": 0.70,
    "mute": True,
    "solo": False,
    "mode": "Locked",
    "tag": "bad id",
    "tip_frames": 0,
    "tip_now": False,
    "page_scroll": 0.0,
    "page_max": 0.0,
    "range": "Week",
    "ctx": "",
}


@dataclass
class Rects:
    sidebar: tuple = (0, 0, 0, 0)
    nav: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    header: tuple = (0, 0, 0, 0)
    stats: list = field(default_factory=list)
    # each stat card's four lines, so paint never re-derives them from the
    # card's height - see stat_card()
    stat_parts: list = field(default_factory=list)
    bands_card: tuple = (0, 0, 0, 0)
    facets: list = field(default_factory=list)
    routing_card: tuple = (0, 0, 0, 0)
    routing_rows: list = field(default_factory=list)
    controls_card: tuple = (0, 0, 0, 0)
    ctl_rows: list = field(default_factory=list)
    table_tabs: tuple = (0, 0, 0, 0)
    table_rows: list = field(default_factory=list)
    # the scrolling viewport the rows live in; table_rows are the slots
    # inside it at scroll 0
    table_view: tuple = (0, 0, 0, 0)
    # the body's natural height, which is what the page scrolls through
    body_h: float = 0.0
    table_head: tuple = (0, 0, 0, 0)
    cols: list = field(default_factory=list)


COL_PAD = 14      # a right-aligned cell stops short of the next column
SIDEBAR_W = 240
HEADER_H = 48
GUT = 24
CARD_GAP = 16


def lay_out(w: int, h: int, n_rows: int | None = None,
            body_dy: float = 0.0) -> Rects:
    """The whole page as a layout TREE, measured then placed.

    Every card's height here comes from what is in it. The old version typed
    them - the bands card was 258 because somebody measured a picture and
    wrote 258, the stat cards were 136 on three adjacent lines - so adding a
    row to a card did not make the card grow, it made the row land outside
    it, silently. `box.Node` + `box.lay` is the fix CSS calls `height: auto`:
    measure the tree bottom-up for what each subtree wants, place it
    top-down with what there is. 0.1 ms for this page, so it can run on
    every resize without a thought.

    The function still returns the same `Rects`, so paint and the tests see
    exactly the contract they saw before; only the numbers are derived now.
    """
    r = Rects()
    N = B.Node

    # ---- the two cards whose content IS a stack of rows -----------------
    CTL_ROW_H, ROW_GAP, N_BANDS = 24.0, T.SPACE[3], 6
    CARD_PAD = (T.CARD_PAD,) * 4

    def titled(*rows, key=None, gap=ROW_GAP, dir="column"):
        """A Card: its measured header, then its content. Auto height."""
        return N(dir="column", pad=CARD_PAD, gap=0.0, key=key, kids=(
            N(h=T.CARD_TITLE_H),
            N(h=T.CARD_TITLE_GAP),
            N(h=T.CARD_DESC_H),
            N(h=T.CARD_HEAD_GAP),
            N(dir=dir, gap=gap, kids=rows),
        ))

    routing = titled(*(N(h=CTL_ROW_H, key=("routing", i))
                       for i in range(N_BANDS)),
                     key="routing", )
    routing.grow, routing.basis = 1.0, 0.0
    # Two columns of five: live controls left, every state right.
    controls = titled(
        *(N(dir="column", gap=ROW_GAP, grow=1.0, basis=0.0,
            kids=tuple(N(h=CTL_ROW_H, key=("ctl", c * CTL_ROWS + i))
                       for i in range(CTL_ROWS)))
          for c in range(2)),
        key="controls", dir="row", gap=T.SPACE[6])
    controls.grow, controls.basis = 1.0, 0.0

    # ---- the cards whose content is drawn rather than stacked -----------
    # Their height is still a composition of named parts rather than one
    # number: a stat card is its label, its figure and its footnote; the
    # bands card is its header and two rows of facets.
    FACET_H, FACET_GAP = 60.0, T.SPACE[6] + 2.0

    def stat_card(i):
        """A stat card's four stacked lines, each keyed so PAINT reads them.

        This is the half that matters. Giving the card an auto height is no
        use if paint still works out where its contents go from the card's
        own height - the first version of this modelled the card as 20/30/16
        and got 114, paint kept drawing its last two lines at `ch - 52` and
        `ch - 32`, and the figure landed on top of the footnote. Layout and
        paint have to read the same rects or they drift the moment either
        moves. Modelled off what paint actually draws, the card comes back to
        136 - the number that used to be typed, now derived.
        """
        return N(grow=1.0, basis=0.0, dir="column", pad=CARD_PAD,
                 key=("stat", i), kids=(
                     N(h=20.0, key=("stat.title", i)),
                     N(h=T.SPACE[0.5]),
                     N(h=36.0, key=("stat.value", i)),
                     N(h=T.SPACE[2] + 2.0),
                     N(h=20.0, key=("stat.head", i)),
                     N(h=18.0, key=("stat.detail", i)),
                 ))

    bands = titled(
        *(N(dir="row", gap=T.SPACE[6],
            kids=tuple(N(h=FACET_H, grow=1.0, basis=0.0,
                         key=("facet", row * 3 + c))
                       for c in range(3)))
          for row in range(2)),
        key="bands", gap=FACET_GAP)

    # ---- the page -------------------------------------------------------
    page = N(dir="row", key="page", kids=(
        N(w=SIDEBAR_W, key="sidebar"),
        N(grow=1.0, dir="column", key="main", kids=(
            N(h=HEADER_H, key="header"),
            N(grow=1.0, dir="column", gap=CARD_GAP, key="body",
              pad=(GUT, GUT, GUT, GUT), kids=(
                N(dir="row", gap=CARD_GAP, key="stats",
                  kids=tuple(stat_card(i) for i in range(4))),
                bands,
                N(dir="row", gap=CARD_GAP, key="cards",
                  kids=(routing, controls)),
                N(h=32.0, key="tabs"),
                # The table is its NATURAL height - every row - and the PAGE
                # scrolls. It used to take whatever was left and scroll
                # inside itself, which on a window this tall left a viewport
                # one row deep: you could see a single clipped row and
                # nothing below it. Nested scrolling is the wrong answer
                # anyway; a dashboard scrolls as a page.
                N(dir="column", key="table", kids=(
                    N(h=36.0, key="head"),
                    N(h=float(n_rows if n_rows is not None else N_TABLE_ROWS)
                      * ROW_H, key="rows"),
                )),
            )),
        )),
    ))

    # The body is laid out at its own height, then SHIFTED by the scroll.
    # lay_out stays a pure function of (w, h, body_dy), so it is still
    # cacheable and still testable without imgui.
    B.measure_tree(page)
    body = next(k for k in page.kids[1].kids if k.key == "body")
    natural = body.mh
    at = B.lay(page, B.Rect(0, 0, w, max(float(h), HEADER_H + natural)))
    r.body_h = natural
    if body_dy:
        for k, v in at.items():
            if k not in ("page", "sidebar", "header", "main"):
                at[k] = B.Rect(v.x, v.y + body_dy, v.w, v.h)

    r.sidebar = at["sidebar"].as_tuple()
    r.header = at["header"].as_tuple()
    r.stats = [at[("stat", i)].as_tuple() for i in range(4)]
    r.stat_parts = [{k: at[(f"stat.{k}", i)].as_tuple()
                     for k in ("title", "value", "head", "detail")}
                    for i in range(4)]
    r.bands_card = at["bands"].as_tuple()
    r.facets = [at[("facet", i)].as_tuple() for i in range(6)]
    r.routing_card = at["routing"].as_tuple()
    r.routing_rows = [at[("routing", i)].as_tuple() for i in range(N_BANDS)]
    r.controls_card = at["controls"].as_tuple()
    r.ctl_rows = [at[("ctl", i)].as_tuple() for i in range(2 * CTL_ROWS)]

    tb = at["tabs"]
    r.table_tabs = (tb.x, tb.y, 0, tb.h)
    hd = at["head"]
    r.table_head = hd.as_tuple()

    # the sidebar's own stack, which never depended on content height
    ny = 16 + 56
    for i, _ in enumerate(NAV):
        r.nav.append((8, ny + i * 34, SIDEBAR_W - 16, 32))
    sy = ny + len(NAV) * 34 + 28
    for i, _ in enumerate(SOURCES):
        r.sources.append((8, sy + i * 34, SIDEBAR_W - 16, 32))

    rows = at["rows"]
    r.table_view = rows.as_tuple()
    if n_rows is None:
        n_rows = N_TABLE_ROWS
    for i in range(n_rows):
        r.table_rows.append((rows.x, rows.y + i * ROW_H, rows.w, ROW_H))

    # Shape | Kind | Schlafli | Dim | Cells | Family — weights, and flex
    # resolves them. The old version hand-summed six fractions that had to
    # add to 1.0, which is a constraint nothing checked.
    weights = [22, 28, 13, 6, 8, 20]
    r.cols = [(b.x, b.w) for b in B.flex(
        B.Rect(rows.x, rows.y, rows.w, 1),
        [B.Item(0, 1, grow=wt) for wt in weights], pad=(0, 12, 0, 12))]
    return r


# --------------------------------------------------------------------------
# drawing
# --------------------------------------------------------------------------

def card_head(dl, card, title, desc, faces, theme):
    """A Card's title and description, on the measured rhythm.

    16px of padding, a 22px title, a 4px gap, a 20px description - all from
    tokens, which read them off a real shadcn Card. Three cards were each
    writing `y + 14` and `y + 34` instead, which is a 20px gap where the
    component uses 4, and is why the headers read loose while the rows below
    them read tight.
    """
    x, y, _w, _h = card
    tx = x + T.CARD_PAD
    D.label(dl, tx, y + T.CARD_PAD, title, faces, "medium", 16,
            T.rgba("foreground", theme=theme), baseline_box=T.CARD_TITLE_H)
    if desc:
        D.label(dl, tx, y + T.CARD_PAD + T.CARD_TITLE_H + T.CARD_TITLE_GAP,
                desc, faces, "regular", 13,
                T.rgba("muted-foreground", theme=theme),
                baseline_box=T.CARD_DESC_H)


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
    # the header names the section the sidebar is on, rather than a typed
    # "Overview" that went on saying Overview from every other tab
    sect = NAV[state.get("nav", 0)][0]
    D.label(dl, hx + GUT, hy, sect, faces, "medium", 16,
            T.rgba("foreground", theme=theme), baseline_box=hh)
    bw = D.text_w(sect, faces, "medium", 16)
    bx = hx + GUT + bw + 12
    D.box(dl, bx, hy + (hh - 20) / 2, 86, 20,
          border_col=T.rgba("border", theme=theme), radius=T.RADII["4xl"])
    _dot(dl, bx + 8, hy + hh / 2, (0.20, 0.83, 0.60, 1.0), 3.0)
    D.label(dl, bx + 20, hy + (hh - 20) / 2, "Rendering", faces, "medium", 12,
            T.rgba("foreground", theme=theme), baseline_box=20)
    # The measured Button (comp_button), not the old three-variant stub: six
    # variants, a size-dependent radius, a per-variant hover and the +1px
    # press nudge. Sized from its own label rather than a typed 72.
    by = hy + (hh - 32) / 2
    gw, _gh = CB.button_size("default", "GitHub", faces)
    CB.ui_button(ui, "hdr.github", hx + hw - GUT - gw, by, gw, 32,
                 "GitHub", variant="ghost")
    # A ButtonGroup: one shared border column at each seam, outer corners
    # rounded and inner ones square. Measured first so it can be
    # right-aligned, rather than laid out twice.
    RANGES = ("Day", "Week", "Month")
    rgw, _rgh = CB.group_size(list(RANGES), faces, size="sm")
    picked, _gr = CB.ui_button_group(
        ui, "hdr.range", hx + hw - GUT - gw - T.SPACE[2] - rgw, by,
        list(RANGES), size="sm")
    if picked is not None:
        state["range"] = RANGES[picked]
    render.last_group_w, render.last_github_w = rgw, gw

    # ---- everything below the header scrolls as ONE page ------------------
    # Not the table on its own: at the window heights people actually use,
    # the content above left the table a viewport one row deep. A dashboard
    # scrolls as a page.
    bx, by = SIDEBAR_W, HEADER_H
    bw, bh = w - SIDEBAR_W, h - HEADER_H
    if state.get("nav") == NAV_GALLERY:
        # The contact sheet. Its height comes from its own content, which is
        # text-dependent and so cannot be worked out in `lay_out` (which has
        # no faces) - so it is planned here, before the scroll area opens,
        # and the same plan is handed to the paint. One call, so the scroll
        # range and what is on screen cannot disagree.
        gw = bw - 2 * GUT
        pre = CG.plan(gw, faces, ui.theme_name)
        with I.scroll_area(ui, "page", bx, by, bw, bh, pre[0] + 2 * GUT,
                           backdrop=T.rgba("background", theme=theme),
                           border=0.0) as view:
            CG.paint(ui, view.x + GUT, view.y + GUT, gw, state, pre=pre)
        state["page_scroll"], state["page_max"] = I.scrolled(ui, "page")
        return

    with I.scroll_area(ui, "page", bx, by, bw, bh, r.body_h,
                       backdrop=T.rgba("background", theme=theme),
                       border=0.0) as view:
        # re-lay-out at this frame's scroll, so there is no frame of lag
        rr = lay_out(w, h, body_dy=view.y - by)
        _body(ui, rr, w, h, series, state)
    state["page_scroll"], state["page_max"] = I.scrolled(ui, "page")
    return


def _body(ui, r, w, h, series, state):
    """Everything below the header. Drawn inside the page's scroll area, so
    `r` is already offset by the scroll and `ui.dl` is that area's list."""
    import menu as M
    dl, faces, theme, grad_tex = ui.dl, ui.faces, ui.theme, ui.grad_tex
    ink = T.rgba("foreground", theme=theme)

    # ---- stat cards -------------------------------------------------------
    for (title, value, delta, up, head, detail), rect, part in zip(
            STATS, r.stats, r.stat_parts):
        x, y, cw, ch = rect
        D.card(dl, {"x": x, "y": y, "w": cw, "h": ch, "variant": "gradient"},
               theme, grad_tex)
        tt = part["title"]
        D.label(dl, tt[0], tt[1], title, faces, "regular", 14,
                T.rgba("muted-foreground", theme=theme), baseline_box=tt[3])
        vv = part["value"]
        D.label(dl, vv[0], vv[1], value, faces, "semibold", 30,
                T.rgba("foreground", theme=theme), baseline_box=vv[3],
                tabular=True)
        # shadcn's badge: gap-1 (4), px-2 (8) but pl-1.5 (6) with a leading
        # icon, and [&>svg]:size-3 (12). Measured, not guessed - the hand
        # offsets this replaces put the label a pixel inside the icon.
        f = B.Flow(gap=4).icon("trending-up" if up else "trending-down", 12)
        D.flow_text(f, delta, faces, "medium", 12, tabular=True)
        pill_w = f.width() + 6 + 8
        pill = B.Rect(x + cw - T.CARD_PAD - pill_w, tt[1] - 2.0, pill_w, 20)
        D.box(dl, *pill.as_tuple(),
              border_col=T.rgba("border", theme=theme), radius=T.RADII["4xl"])
        D.draw_flow(dl, f.place(pill.pad(0, 8, 0, 6), "start"), faces,
                    T.rgba("foreground", theme=theme))
        g = B.Flow(gap=6)
        D.flow_text(g, head, faces, "medium", 14)
        g.icon("trending-up" if up else "trending-down", 15)
        hh = part["head"]
        D.draw_flow(dl, g.place(B.Rect(*hh), "start"), faces,
                    T.rgba("foreground", theme=theme))
        dd = part["detail"]
        D.label(dl, dd[0], dd[1], detail, faces, "regular", 13,
                T.rgba("muted-foreground", theme=theme), baseline_box=dd[3],
                max_w=dd[2])

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
    card_head(dl, r.routing_card, "Plane routing",
              "Band to rotation plane, with the latest level", faces, theme)
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

    # ---- Tier 1 controls --------------------------------------------------
    # Every one of these runs a real widget underneath (see interact.py), so
    # they drag, type, open and toggle for real - and stay reachable to
    # tests/ui_driver.py, which finds controls by the text after `##`.
    #
    # The right column is the STATES. They are here rather than only in the
    # gallery because the gallery is a contact sheet: it proves the chrome to
    # a pixel and shows you nothing about how a disabled control feels under
    # the pointer, or whether a two-thumb range drags the handle you meant.
    import menu as M
    x, y, cw, ch = r.controls_card
    D.card(dl, {"x": x, "y": y, "w": cw, "h": ch, "variant": "plain"}, theme, None)
    card_head(dl, r.controls_card, "Controls",
              "Tier 1 live on the left, every state on the right - "
              "Bypass disables them", faces, theme)
    muted = T.rgba("muted-foreground", theme=theme)

    def _row(i, name, dim=False):
        rx, ry, rw, rh = r.ctl_rows[i]
        D.label(dl, rx, ry, name, faces, "medium", 13,
                muted if dim else ink, baseline_box=rh,
                max_w=CTL_LABEL_W - T.SPACE[2])
        return rx + CTL_LABEL_W, ry, rw - CTL_LABEL_W, rh

    # --- left: the live controls ------------------------------------------
    # a continuous param: 292 of the registry's 427 are this shape
    sx, sy, sw, sh = _row(0, "Cutoff")
    _, state["cutoff"] = I.slider(
        ui, "ctl.cutoff", sx, sy, sw - 46, sh, state["cutoff"], 20.0, 20000.0,
        detents=(1000.0,), fmt="%.0f Hz")
    D.label(dl, sx + sw - 44, sy, f"{state['cutoff']:.0f}", faces, "regular",
            12, muted, align="right", box_w=44, baseline_box=sh, tabular=True)
    # the tooltip hangs off the slider's own rect and takes no hit target of
    # its own, so it cannot steal the hover from the control it describes
    shown = I.tooltip(ui, "ctl.cutoff.tip", (sx, sy, sw - 46, sh),
                      "Low-pass cutoff, 20 Hz - 20 kHz",
                      hovered=imgui.is_mouse_hovering_rect(
                          imgui.ImVec2(sx, sy),
                          imgui.ImVec2(sx + sw - 46, sy + sh)))
    # Counted rather than sampled from pixels. A tooltip floats OVER whatever
    # is above it - here the card's own description - so ink at a guessed
    # point cannot tell the two apart. The count also makes the flicker test
    # exact instead of inferred: if it blinks, the frames simply do not add
    # up.
    state["tip_frames"] = state.get("tip_frames", 0) + (1 if shown else 0)
    state["tip_now"] = shown

    # a toggle param: 47 of them. It GATES the rest, which is what a bypass
    # does - and it means the disabled chrome is something you can toggle and
    # watch ease rather than a dead row to look at. Every Tier 1 component
    # below takes `disabled` from it.
    wx, wy, _, wh = _row(1, "Bypass")
    _, state["bypass"] = I.switch(ui, "ctl.bypass", wx, wy + (wh - 18.4) / 2,
                                  state["bypass"])
    off = state["bypass"]

    # an enum param: 73 of them
    ex, ey, ew, _ = _row(2, "Plane")
    chosen, _open = I.select(
        ui, "ctl.plane", ex, ey, min(ew, 130.0), state["plane"],
        [M.Item(id=p, label=p, checked=(p == state["plane"])) for p in PLANES],
        disabled=off)
    if chosen:
        state["plane"] = chosen

    # a text param - a node rename, say
    ix, iy, iw, _ = _row(3, "Name")
    _, state["name"] = I.text_input(ui, "ctl.name", ix, iy, min(iw, 160.0),
                                    state["name"], placeholder="Node name",
                                    disabled=off)

    # a second continuous param, to show two sliders do not share state
    gx, gy, gw, gh = _row(4, "Mix")
    _, state["mix"] = I.slider(ui, "ctl.mix", gx, gy, gw - 46, gh,
                               state["mix"], 0.0, 1.0, detents=(0.5,),
                               fmt="%.2f", disabled=off)
    D.label(dl, gx + gw - 44, gy, f"{state['mix']:.2f}", faces, "regular", 12,
            muted, align="right", box_w=44, baseline_box=gh, tabular=True)

    # A Combobox: a filterable Select. With 600-900 live params this is the
    # shape the panel actually needs - typing beats scanning well before
    # then. Type in it to filter; the ranking is cmdk's own commandScore.
    kx, ky, kw, _ = _row(5, "Find")
    got, _o = CC.combobox(
        ui, "ctl.find", kx, ky, min(kw, 150.0), state["plane"],
        [CC.Item(id=p, label=p) for p in PLANES], disabled=off,
        search="Filter planes", empty="No such plane.")
    if got is not None:
        state["plane"] = got

    # --- right: every state the gallery diffs ------------------------------
    # a two-thumb range. Its two handles drag independently, which is the
    # half of the Radix law a still frame cannot show.
    rx2, ry2, rw2, rh2 = _row(6, "Window")
    _, state["win_lo"], state["win"] = I.range_slider(
        ui, "ctl.win", rx2, ry2, rw2 - 46, rh2,
        state["win_lo"], state["win"], 0.0, 1.0, disabled=off)
    D.label(dl, rx2 + rw2 - 44, ry2, f"{state['win_lo']:.2f}-{state['win']:.2f}",
            faces, "regular", 11, muted, align="right", box_w=44,
            baseline_box=rh2, tabular=True)

    # the small switch
    mx, my, _, mh = _row(7, "Mute")
    _, state["mute"] = I.switch(ui, "ctl.mute", mx, my + (mh - 14.0) / 2,
                                state["mute"], size="sm", disabled=off)
    # A Checkbox beside it, with its Label: the other shape of a toggle
    # param, and the one a row of independent flags reads best as. Placed
    # 24px past the small switch's track: the switch's stretched target
    # reaches 11px past its end and the checkbox's 11px before its box, so
    # 2px separate them and neither steals the other's clicks.
    # On a CARD, so the card is the backdrop its disabled state folds
    # against - the page's `background` would be the wrong colour here.
    sw_w = T.SWITCH_SIZES["sm"][0]
    _, state["solo"] = I.checkbox(
        ui, "ctl.solo", mx + sw_w + T.HIT_STRETCH[0] * 2,
        my + (mh - T.CHECKBOX["size"]) / 2, state["solo"], label="Solo",
        disabled=off, backdrop=T.rgba("card", theme=theme))

    # the small select - rounded-md (8) rather than rounded-lg (10)
    ox, oy, ow, _ = _row(8, "Mode")
    chosen2, _o2 = I.select(
        ui, "ctl.mode", ox, oy, min(ow, 130.0), state["mode"],
        [M.Item(id=m, label=m, checked=(m == state["mode"]))
         for m in ("Free", "Locked", "Follow")], size="sm", disabled=off)
    if chosen2:
        state["mode"] = chosen2

    # aria-invalid: a destructive border AND a 3px destructive ring
    tx2, ty2, tw2, _ = _row(9, "Tag")
    _, state["tag"] = I.text_input(ui, "ctl.tag", tx2, ty2, min(tw2, 160.0),
                                   state["tag"], invalid=True, disabled=off)

    # disabled: the whole element at opacity 50, composited as a GROUP - the
    # thing that cannot be done by scaling each layer's alpha
    dx, dy, dw, dh = _row(10, "Gain", dim=True)
    I.slider(ui, "ctl.gain", dx, dy, dw - 46, dh, 0.62, 0.0, 1.0,
             disabled=True, fmt="%.2f")
    D.label(dl, dx + dw - 44, dy, "0.62", faces, "regular", 12,
            T.rgba("muted-foreground", 0.5, theme=theme), align="right",
            box_w=44, baseline_box=dh, tabular=True)

    # The measured Button in a variant nothing else here shows. Sized from
    # its own label, and it carries the +1px press nudge.
    ax, ay, _aw, ah = _row(11, "Action")
    abw, _abh = CB.button_size("sm", "Delete node", faces)
    if CB.ui_button(ui, "ctl.delete", ax, ay + (ah - 28) / 2, abw, 28,
                    "Delete node", variant="destructive", size="sm",
                    disabled=off).clicked:
        state["said"] = "delete \u00b7 node"

    # ---- table ------------------------------------------------------------
    tx, ty, _, th = r.table_tabs
    picked, _tabs_w = I.tabs(ui, "tab", tx, ty, th, TABS, state["tab"])
    if picked is not None:
        state["tab"] = picked
    rows = filtered(state["tab"])
    # every row is in the table now; the viewport decides what is on screen
    D.label(dl, tx, ty, f"{len(rows)} shapes", faces, "regular", 13,
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

    # No inner scroll: the PAGE scrolls, and nesting one inside the other is
    # the wrong answer. The rows are drawn inline at their natural heights.
    vx, vy, vw, vh = r.table_view
    _table_rows(ui, rows, B.Rect(vx, vy, vw, vh), r, faces, theme, ink, state)


def _table_rows(ui, rows, view, r, faces, theme, ink, state):
    """The table's rows, drawn inline inside the page's scroll area.

    N_TABLE_ROWS of them, not all 101: the page carries a readable slice and
    the tabs filter it. Drawing every row would mean 101 invisible_buttons
    and 101 popup calls a frame for rows nobody can reach.
    """
    dl = ui.dl                      # the page scroll area's list
    aligns = ["left", "left", "left", "center", "right", "left"]
    for ri in range(min(N_TABLE_ROWS, len(rows))):
        row = rows[ri]
        rx, ry, rw, rh = view.x, view.y + ri * ROW_H, view.w, ROW_H
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
        # The same menu on a right-click anywhere in the row - which is the
        # gesture a node editor wants. `allow_overlap` is on by default, so
        # the row's target does not swallow the kebab's hover.
        got = CX.context_menu(ui, f"ctx.{ri}", (rx, ry, rw, rh), ROW_MENU)
        if got:
            state["ctx"] = f"{got} \u00b7 {row['name']}"
            state["said"] = state["ctx"]
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
    # One place where ImGui's stock focus rectangle and text selection are
    # replaced by the kit's. A popup opened inside `paint` is a separate
    # window but the style stack is global, so this covers those too.
    with I.chrome(ui_box):
        paint(ui_box, rects, w, h, series, state)
    imgui.end()
    imgui.pop_style_var(2)
    return ui_box


def wheel_probe(theme_name: str, w: int, h: int) -> None:
    """Open the dashboard and print every raw wheel delta the OS sends.

    This exists because the scroll constant is the one number in the kit
    that cannot be measured on this machine. The wheel has to be turned
    into pixels of finger travel, and how many units a trackpad produces per
    point is a property of the GLFW build and the platform - on macOS it
    comes out of `scrollingDeltaY` and a factor I have only ever recalled,
    never checked.

    Run it on the machine that can feel it, scroll once, and read three
    things off the output:

      * the MAGNITUDE of the deltas - one slow swipe of about 100 points
        tells you the units-per-point factor directly;
      * whether they are FRACTIONAL - any fractional delta means a
        pixel-precise device, which is what picks the precise rate;
      * whether they CONTINUE after your finger lifts - that is the OS's
        momentum phase, and its arrival is the whole of inertial scrolling.
        If the deltas stop dead when the finger does, GLFW is dropping the
        momentum events and no constant will bring the inertia back.

    `DKIT_SCROLL_PX=<n>` then dials the rate without an edit.
    """
    import time
    win, impl, io, faces, grad = _boot(theme_name, w, h, visible=True,
                                       retina=True)
    glfw.swap_interval(1)
    io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard
    theme = T.LIGHT if theme_name == "light" else T.DARK
    bgc = T.rgba("background", theme=theme)
    ui = I.Ui(None, faces, theme, Anim(), grad, theme_name=theme_name)
    state = dict(CTL_STATE, tab=0, nav=0)
    series = ticks()
    print("wheel probe: scroll, then let go. Ctrl+C to stop.")
    print(f"{'t (ms)':>8}  {'raw':>10}  {'kind':>9}  {'-> px':>8}")
    t0 = time.perf_counter()
    last = [None]

    def _log(dx, dy):
        now = (time.perf_counter() - t0) * 1000.0
        gap = "" if last[0] is None else f"  (+{now - last[0]:.0f}ms)"
        kind = "precise" if abs(dy - round(dy)) > 1e-4 else "whole"
        print(f"{now:8.0f}  {dy:10.4f}  {kind:>9}  "
              f"{I.wheel_px_per_unit() * dy:8.1f}{gap}", flush=True)
        last[0] = now

    # the ONLY place the wheel can be seen or scaled - see install_wheel
    I.install_wheel(win, impl, log=_log)
    try:
        rects, last_size = None, None
        prev = time.perf_counter()
        while not glfw.window_should_close(win):
            glfw.poll_events()
            impl.process_inputs()
            now2 = time.perf_counter()
            dt = min(now2 - prev, 0.05)
            prev = now2
            lw, lh = glfw.get_window_size(win)
            fw, fh = glfw.get_framebuffer_size(win)
            if lw <= 0 or lh <= 0:
                continue
            if (lw, lh) != last_size:
                rects, last_size = lay_out(lw, lh), (lw, lh)
            imgui.new_frame()
            I.note_wheel_step()
            GL.glViewport(0, 0, fw, fh)
            _draw(ui, rects, lw, lh, series, state, bgc)
            imgui.render()
            impl.render(imgui.get_draw_data())
            ui.frame_done(dt)
            glfw.swap_buffers(win)
    except KeyboardInterrupt:
        pass
    finally:
        impl.shutdown()
        imgui.destroy_context()
        glfw.terminate()


def live(theme_name: str, w: int, h: int) -> None:
    """Open the dashboard and run it until the window is closed.

    A real event loop with real timing, so the 150ms transitions run off the
    clock rather than off a scripted dt. Resizing re-lays-out; the table
    grows and shrinks with the window.

    Ctrl+C is a way to quit this, so it exits the way closing the window
    does rather than printing a traceback from wherever in GLFW the signal
    happened to land. The teardown is in a `finally` for the same reason it
    matters here more than most places: `glfw.terminate()` is what gives the
    window and its GL context back to the OS, and skipping it on the way out
    of an exception leaves them dangling.
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
    state = dict(CTL_STATE, tab=0, nav=0)
    ui = I.Ui(None, faces, theme, Anim(), grad, theme_name=theme_name)
    I.install_wheel(win, impl)
    prev = time.perf_counter()

    try:
        _loop(win, impl, ui, state, series, bgc, prev)
    finally:
        impl.shutdown()
        imgui.destroy_context()
        glfw.terminate()


def _loop(win, impl, ui, state, series, bgc, prev) -> None:
    """The live event loop. Split out of `live` only so the setup, the loop
    and the teardown each sit in one piece."""
    import time
    rects, last_size = None, None
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
        # Ctrl+C can land anywhere, and ImGui asserts "Forgot to call
        # Render()" if the process tears down with a frame half open - a
        # traceback about the wrong thing, on the way out. The frame is
        # closed first and the loop returns normally.
        # Ctrl+C can land anywhere, including INSIDE `new_frame()`. The
        # first version of this answered it with a bare `imgui.render()` in
        # the handler, which asserts "Forgot to call NewFrame()" when the
        # interrupt arrived before the frame was open - trading one wrong
        # traceback for another. `open_frame` says whether there is a frame
        # to abandon, and `end_frame` is the call that abandons one.
        open_frame = False
        try:
            imgui.new_frame()
            open_frame = True
            I.note_wheel_step()
            GL.glViewport(0, 0, fw, fh)
            _draw(ui, rects, lw, lh, series, state, bgc)
            imgui.render()
            open_frame = False
            impl.render(imgui.get_draw_data())
            ui.frame_done(dt)
            glfw.swap_buffers(win)
        except KeyboardInterrupt:
            if open_frame:
                try:
                    imgui.end_frame()
                except Exception:
                    pass
            return


def render(theme_name: str, w: int, h: int, *, script=None, dt=1 / 60.0,
           keys=None, keep: str = "all"):
    """Draw the dashboard, optionally stepping a script of mouse positions.

    `script` is a list of (x, y), (x, y, down), (x, y, down, wheel) or
    (x, y, down, wheel, right) — one per frame — so a hover, a click, a
    scroll or a RIGHT-click can be driven headlessly. The last is what a
    context menu needs.
    Returns a list of frames (the last one only, if no script was given).

    `keep="last"` keeps ONLY the final frame. A frame is w*h*4 bytes - 15 MB
    at 1440x2600 - so a sweep that drives a thousand of them accumulates
    twenty gigabytes and the kernel kills the worker. A test that only looks
    at the end should say so.
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
    state = dict(CTL_STATE, tab=0, nav=0)
    render.last_state = state           # so a caller can read what the script did

    # two warm-up frames settle the backend and the font atlas, and let the
    # animation store see every widget once before anything is scripted
    steps = [None, None] + list(script or [None])
    # keys is [(frame_index_within_script, imgui.Key | str)] - pressed and
    # released on that frame, for checking things ImGui owns, like Escape
    # dismissal. A str is a CHARACTER: input_text is fed by character events,
    # not key events, so a key alone never types anything into it.
    keymap = {}
    for at, k in (keys or []):
        keymap.setdefault(at + 2, []).append(k)
    # ImGui routes Escape (and every other key) through its nav system, which
    # is OFF by default - so without this a menu cannot be dismissed with the
    # keyboard at all. tests/ui_driver.py:172 turns it on for the same reason.
    io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard
    frames = []
    # The teardown is in a `finally` because a script that raises - a
    # component handed the wrong kind of item, an ImGui assert - would
    # otherwise leave this context and window alive, and every later
    # render() in the same process would assert "Forgot to call
    # Render()" instead of reporting its own problem. One real crash
    # then reads as a dozen unrelated ones, which is exactly how long
    # the Gallery's own crash took to find.
    try:
        for i, mouse in enumerate(steps):
            glfw.poll_events()
            impl.process_inputs()
            if mouse is not None:
                io.add_mouse_pos_event(float(mouse[0]), float(mouse[1]))
                if len(mouse) > 2:            # (x, y, down) drives the button too
                    io.add_mouse_button_event(0, bool(mouse[2]))
                if len(mouse) > 3:            # (x, y, down, wheel) drives scroll
                    io.add_mouse_wheel_event(0.0, float(mouse[3]))
                if len(mouse) > 4:            # ..., right) drives button 1
                    io.add_mouse_button_event(1, bool(mouse[4]))
            for k in keymap.get(i, ()):
                if isinstance(k, str):
                    for ch in k:
                        io.add_input_character(ord(ch))
                    continue
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
            ui = I.Ui(imgui.get_window_draw_list(), faces, theme, anim, grad_tex,
                      theme_name=theme_name)
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
                if keep == "last":
                    frames.clear()
                frames.append(px.copy())

    finally:
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
    ap.add_argument("--wheel-probe", action="store_true",
                    help="print every raw wheel delta the OS sends, to set "
                         "the scroll constant from data rather than memory")
    a = ap.parse_args()
    if a.wheel_probe:
        wheel_probe(a.theme, a.width, a.height)
        return
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
