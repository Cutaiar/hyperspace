"""The effect picker (plan 65): GRAPH's "add an effect" as a grid of
pictures, in place of the nested effects ▸ submenu.

The right-click picker's **effects…** (and a picture cable's **insert ▸
effects…**) opens this dialog over the canvas: a search box and a tile per
effect file, each the test card through that effect at its defaults
(`previews.EffectPreviews`, made by the renderer at its frames' ends),
grouped by family (`previews.families`: the file's `@family`, else its
`@order` band — data, not a list here). Hovering a tile plays its loop and
says its tip at the foot; a click adds the effect exactly as the menu's row
did (`ui_graph` hands the action in: `add_render` unwired where the menu
opened, `insert_effect` spliced into the cable). Enter takes the first tile
the search leaves; Esc or a click outside closes it.

It is made for a trackpad on stage: big tiles (the whole tile is the click
target), the picture first, one short label each, and the words only for
the tile under the pointer. It is an ImGui popup, so the canvas under it is
swallowed by GRAPH's own guard (`ui_graph._menu_up`, #452): no hover words,
no click, no wheel reaches the canvas while it is open.

View state only: what is open, the search and the hovered tile live in the
page's state (`st[KEY]`), never in a file, never an undo step.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from types import SimpleNamespace as NS
from typing import Any

from imgui_bundle import imgui

from . import previews as pv
from . import ui
from .dkit.tokens import DARK, RADII, SPACE, rgba

KEY = "graph.effects"               # the popup's id, and the page state's key
SEARCH = "effects.search"           # the search box's id (after ##: the driver's handle)
TILE = "effects.pick.{}"            # a tile's id, by effect file
MENU_LABEL = "effects…"             # the menu row that opens it
SEARCH_HINT = "search effects"
FOOT_IDLE = "Hover an effect to see it move · click to add · Enter takes the first · Esc closes"
FOOT_INSERT = "Hover an effect to see it move · click to put it on the cable · Esc closes"
NO_MATCH = "No effect matches"
AUX_BADGE = "aux"   # on the tile of an effect that reads a second picture (`EffectSpec.aux`)

# a tile: the preview at its own size, one line of label under it
TILE_W, PIC_H = float(pv.PREVIEW_W), float(pv.PREVIEW_H)
LABEL_H = SPACE[8]                  # the label's line under the picture
TILE_H = PIC_H + LABEL_H
GAP = SPACE[3]                      # between tiles
PAD = SPACE[4]                      # the dialog's inset
EDGE = SPACE[12]                    # kept clear around the dialog, in the window
SEARCH_H = SPACE[10]                # the search box's height: a finger's, not a line's
FOOT_H = SPACE[12]                  # the tip's room at the foot (two lines)
MIN_H = 6 * SPACE[10]               # the dialog is never shorter (a short window)
MAX_COLS = 6
ROUND = RADII["lg"]
OUTLINE, OUTLINE_LIT = 1.0, 2.0     # a tile's outline, and the hovered one's
WHITE = (1.0, 1.0, 1.0, 1.0)        # the picture drawn as it is (no tint)
# the dialog's colours: dkit's dark tokens (the popover, a tile, its border, the hovered one's)
GROUND = rgba("popover", theme=DARK)
CARD = rgba("muted", theme=DARK)
BORDER = rgba("border", theme=DARK)
LIT = rgba("primary", theme=DARK)


# ---------------------------------------------------------------- state

def open_picker(st: dict, mode: str, at=None, cable: str | None = None) -> None:
    """Ask for the picker next frame: `mode` "add" (a node where the menu
    opened, canvas units `at`) or "insert" (spliced into render cable
    `cable`, put at `at`). The search starts empty."""
    st[KEY] = {"open": True, "mode": mode, "at": at, "cable": cable,
               "query": "", "hover": None, "since": None, "focus": True}


def state(st: dict) -> dict | None:
    """The picker's state while it is asked for or open, else None."""
    return st.get(KEY)


def specs_of(files: Iterable[str], known: dict | None) -> list[Any]:
    """An effect spec per file the menu would list (`files`): the file's
    own (`known`, the show's `FxState.files`) or, without one, its name as
    its label — a tile for every file the old submenu had a row for."""
    known = known or {}
    return [known.get(f) or NS(name=f, label=f, tip="", order=50, family="")
            for f in files]


def first_match(specs: list[Any], query: str):
    """The file Enter takes: the first tile the search leaves whose label
    answers it (a tip that mentions waves is not the Wave), else the first
    tile; None when it leaves none."""
    tiles = [s for _, group in pv.families(specs, query) for s in group]
    named = [s for s in tiles if pv.matches(NS(label=s.label), query)]
    return (named or tiles)[0].name if tiles else None


def columns(width: float) -> int:
    """How many tiles fit across `width` px of dialog body (1 … MAX_COLS)."""
    return max(1, min(MAX_COLS, int((width + GAP) // (TILE_W + GAP))))


# ---------------------------------------------------------------- drawing

def draw(st: dict, specs: list[Any], on_pick: Callable[[str], object],
         cache: Any = None, now: float | None = None) -> str | None:
    """The picker this frame, if asked for: opened on the first frame, drawn
    while open, its state dropped once closed. `on_pick(file)` adds the
    effect (the menu row's action); `cache` the renderer's previews (None:
    tiles with their names only, as in a test rig). Returns the file
    picked this frame, or None. Draw it where GRAPH draws its menus (the
    node editor suspended: screen pixels)."""
    s = state(st)
    if s is None:
        return None
    if s.pop("open", False):
        imgui.open_popup(KEY)
    if not imgui.is_popup_open(KEY):
        st.pop(KEY, None)                   # closed: Esc, a click outside, a pick
        return None
    now = time.monotonic() if now is None else now
    vp = imgui.get_main_viewport()
    cols = columns(vp.work_size.x - 2 * EDGE - 2 * PAD)
    w = cols * TILE_W + (cols - 1) * GAP + 2 * PAD + imgui.get_style().scrollbar_size
    h = max(MIN_H, vp.work_size.y - 2 * EDGE)
    imgui.set_next_window_pos(imgui.ImVec2(vp.work_pos.x + (vp.work_size.x - w) / 2,
                                           vp.work_pos.y + EDGE))
    imgui.set_next_window_size(imgui.ImVec2(w, h))
    imgui.push_style_color(imgui.Col_.popup_bg, imgui.ImVec4(*GROUND))
    imgui.push_style_color(imgui.Col_.border, imgui.ImVec4(*BORDER))
    imgui.push_style_var(imgui.StyleVar_.window_rounding, ROUND)
    imgui.push_style_var(imgui.StyleVar_.window_padding, imgui.ImVec2(PAD, PAD))
    picked = None
    flags = (imgui.WindowFlags_.no_move | imgui.WindowFlags_.no_saved_settings
             | imgui.WindowFlags_.no_scrollbar)
    if imgui.begin_popup(KEY, flags):
        s["up"] = True                      # (drawn this frame: what a test reads)
        picked = _body(s, specs, cache, now, h)
        if picked is None and imgui.is_key_pressed(imgui.Key.escape):
            imgui.close_current_popup()
        imgui.end_popup()
    imgui.pop_style_var(2)
    imgui.pop_style_color(2)
    if picked is not None:
        on_pick(picked)
    return picked


def _body(s: dict, specs: list[Any], cache, now: float, h: float) -> str | None:
    """The search, the tiles by family, the foot. Returns a picked file."""
    picked = None
    imgui.push_style_var(imgui.StyleVar_.frame_padding,
                         imgui.ImVec2(SPACE[3], (SEARCH_H - imgui.get_font_size()) / 2))
    imgui.push_style_var(imgui.StyleVar_.frame_rounding, RADII["md"])
    imgui.set_next_item_width(-1)
    if s.pop("focus", False):
        imgui.set_keyboard_focus_here()
    _, s["query"] = imgui.input_text_with_hint(f"##{SEARCH}", SEARCH_HINT, s["query"])
    imgui.pop_style_var(2)
    groups = pv.families(specs, s["query"])
    if imgui.is_key_pressed(imgui.Key.enter) or imgui.is_key_pressed(imgui.Key.keypad_enter):
        picked = first_match(specs, s["query"])
        if picked is not None:
            imgui.close_current_popup()
            return picked
    imgui.dummy(imgui.ImVec2(0, SPACE[1]))
    body_h = h - 2 * PAD - SEARCH_H - SPACE[1] - FOOT_H - 2 * imgui.get_style().item_spacing.y
    hover = None
    shown: list[str] = []
    if imgui.begin_child("##effects.tiles", imgui.ImVec2(0, max(body_h, TILE_H))):
        width = imgui.get_content_region_avail().x
        cols = columns(width)
        if not groups:
            imgui.text_colored(ui.FAINT, NO_MATCH)
        for family, group in groups:
            ui._micro(family)
            for i, spec in enumerate(group):
                if i % cols:
                    imgui.same_line(0, GAP)
                got, over = _tile(spec, cache, s.get("hover"), now)
                shown.append(spec.name)
                if over:
                    hover = spec.name
                if got:
                    picked = spec.name
            imgui.dummy(imgui.ImVec2(0, SPACE[2]))
    imgui.end_child()
    s["hover"] = hover
    _foot(s, specs, hover)
    if cache is not None:
        cache.want(shown, loop=hover)
    if picked is not None:
        imgui.close_current_popup()
    return picked


def _tile(spec, cache, hover: str | None, now: float) -> tuple[bool, bool]:
    """One tile: the whole of it the click target, the preview (its loop
    while hovered), the label under it. (clicked, hovered)."""
    p0 = imgui.get_cursor_screen_pos()
    clicked = imgui.invisible_button(f"##{TILE.format(spec.name)}",
                                     imgui.ImVec2(TILE_W, TILE_H))
    over = imgui.is_item_hovered()
    dl = imgui.get_window_draw_list()
    a = imgui.ImVec2(p0.x, p0.y)
    b = imgui.ImVec2(p0.x + TILE_W, p0.y + TILE_H)
    dl.add_rect_filled(a, b, ui.u32(imgui.ImVec4(*CARD)), RADII["md"])
    pic_b = imgui.ImVec2(p0.x + TILE_W, p0.y + PIC_H)
    got = cache.picture(spec.name, now if over else None) if cache is not None else None
    if got is not None:
        tex, uv0, uv1 = got
        dl.add_image_rounded(imgui.ImTextureRef(tex.glo), a, pic_b, imgui.ImVec2(*uv0),
                             imgui.ImVec2(*uv1), ui.u32(imgui.ImVec4(*WHITE)), RADII["md"],
                             imgui.ImDrawFlags_.round_corners_top)
    if getattr(spec, "aux", False):             # it reads its aux: a warm disc is wired in here
        bw = imgui.calc_text_size(AUX_BADGE)
        b0 = imgui.ImVec2(p0.x + TILE_W - bw.x - 3 * SPACE[1], p0.y + SPACE[1])
        b1 = imgui.ImVec2(p0.x + TILE_W - SPACE[1], p0.y + SPACE[1] + bw.y + SPACE[1])
        dl.add_rect_filled(b0, b1, ui.u32(imgui.ImVec4(*GROUND)), RADII["sm"])
        dl.add_text(imgui.ImVec2(b0.x + SPACE[1], b0.y + SPACE[0.5]), ui.u32(ui.TEXT), AUX_BADGE)
    label = ui.fit_text(spec.label, TILE_W - 2 * SPACE[2])
    tw = imgui.calc_text_size(label)
    dl.add_text(imgui.ImVec2(p0.x + (TILE_W - tw.x) / 2, p0.y + PIC_H + (LABEL_H - tw.y) / 2),
                ui.u32(ui.TEXT if over else ui.DIM), label)
    ring = imgui.ImVec4(*(LIT if over else BORDER))
    dl.add_rect(a, b, ui.u32(ring), RADII["md"], OUTLINE_LIT if over else OUTLINE)
    return clicked, over


def _foot(s: dict, specs: list[Any], hover: str | None) -> None:
    """The foot: the hovered effect's label and tip, else what to do."""
    spec = next((x for x in specs if x.name == hover), None) if hover else None
    imgui.push_text_wrap_pos(imgui.get_content_region_avail().x + imgui.get_cursor_pos_x())
    if spec is not None:
        imgui.text_colored(ui.TEXT, spec.label)
        if spec.tip:
            imgui.same_line()
            imgui.text_colored(ui.DIM, _first_sentence(spec.tip))

    else:
        imgui.text_colored(ui.FAINT, FOOT_INSERT if s.get("mode") == "insert" else FOOT_IDLE)
    imgui.pop_text_wrap_pos()


def _first_sentence(tip: str) -> str:
    """A tip's first sentence: the foot is two lines, read on stage."""
    head, dot, _ = tip.partition(". ")
    return head + ("." if dot else "")
