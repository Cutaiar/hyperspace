"""The HANDS page — the Ultraleap hands, live, and the setup that shapes them.

Top to bottom:

  hands  ◀ setup ▶ …       the library strip for the `hands` group: a
                           setup is every per-axis and global setting
  status                   tracker, each hand (● in the box, ◌ tracked
                           but outside it, ○ not seen), DAW port, the
                           last MIDI sent
  pinch                    the eight thumb-to-finger switches, each with
                           the live gap that closes it — the number to
                           watch when setting the threshold
  the box, from above      each palm as a dot (left white, right red),
                           its size the hand's height; the camera at the
                           centre. The interaction box (hands.json, set
                           by the sweep) is the inner rectangle; a hand
                           tracked but outside it is a hollow, dim ring —
                           it reads absent. Beside it a height gauge: a
                           tick per hand, a bracket for the box's y
  ghost hands              the switch; while on, Opacity and "more ▸"
                           (Mirror, Tethers, the ghost's notes), then
                           Style and Guide (see _ghost)
  the axes               one row each: the output y as a white bar,
                           where the hand is (the shaped target) as a
                           hairline, the rest value as a dim tick, the
                           MIDI out on the right. Click a row to edit it.
  the dance sources        a line per hand: five curls and the grab
                           switch (● closed, a fist; plan 24 C5), then
                           spread, energy, flick; a line for both: gap,
                           twist — small bars, hollow while they read
                           nothing; hover one for its address (plan 24 C4)
  the selected axis        its transfer (dead zone and curve over the
                           calibrated range) with the live point on it,
                           then invert · centred · dead zone · curve ·
                           attack · decay · on exit · rest · return ·
                           bounce · MIDI out. "mirror" copies the feel to
                           the same axis on the other hand; "solo" sends
                           only this axis to the DAW (for a DAW's learn).
  feel                     steadiness, response, catch, MIDI rate,
                           hysteresis, and the pinch thresholds — the
                           whole instrument
  calibrate                a timed sweep that writes the axes' ranges
                           and the interaction box; "reset ranges" puts
                           the ranges back and opens the box

Every control is a registry param (hands.register), so the widgets are
the panel's own and right-click → Learn works on them too.
"""

from __future__ import annotations

import itertools
import math

from imgui_bundle import imgui

from .. import ui
from ..ghost import MODES as GHOST_MODES
from .core import (
    BOX_AXES,
    BOX_MARGIN,
    DIGITS,
    FEATURES,
    GRAB_CLOSE,
    GRAB_OPEN,
    GROUP,
    PINCHES,
    SIDES,
    conflicts,
    fist,
    grab_name,
    mirror,
)
from .signal import shape

ROW_LABEL_W = 62.0
OUT_W = 100.0
BOX_H = 92.0
BOX_W = 190.0       # the switches sit beside it
GAUGE_W = 10.0      # the height gauge, inside the same BOX_W …
GAUGE_GAP = 6.0     # … this far right of the view from above
VIEW_X_MM = 260.0   # the view from above: x over ±this …
VIEW_Z_MM = 160.0   # … and z over ±this, at a fixed scale
GAUGE_MM = (80.0, 400.0)    # the gauge, bottom to top: the range a dot's size uses
OUTSIDE_ALPHA = 0.4
FACE_PAD = 12.0     # a box face is never drawn nearer the frame than this
PLOT_W = 96.0
GHOST_ALPHA_MIN = 100.0     # the opacity slider never narrower: "100%" and its grab
GHOST_NOTE_W = 360.0        # the ghost's "more" popup wraps its notes at this width
CAL_SECONDS = 20.0
LEFT = imgui.ImVec4(0.92, 0.92, 0.92, 1.0)


def _sel_param(panel):
    """`hands.select`, the selected axis the page and the desk's
    `hands.sel.*` knob share (core.register); None on a bare registry."""
    reg = getattr(panel, "reg", None)
    return reg.get(f"{GROUP}.select") if reg is not None else None


def _sel(panel, n: int) -> int:
    p = _sel_param(panel)
    k = int(p.value) if p is not None else getattr(panel, "_hands_sel", 0)
    return min(max(k, 0), n - 1)


def _select(panel, k: int) -> None:
    p = _sel_param(panel)
    if p is not None:
        p.set(k)
    panel._hands_sel = k


# ---- right-click menu: a param's hand bindings ----

def ctx_rows(panel, p, *, lines: bool = True, gate: bool = True) -> None:
    """The context menu's hand part: what hand axis drives this param
    (`lines`: a line per hand row, in the adapter's words) and the pinch
    that gates it (`gate`: the "Gate: … ▸" submenu). The menu draws the
    lines above its items and the gate among them, so it calls this twice.
    Removing the rows is the menu's one Unbind (`Learn.unbind`, plan 17
    WP1); a gate is not an unbind."""
    router = getattr(panel, "router", None)
    if router is None:
        return
    rows = [b for b in router.table.of("hand") if b.target == p.id]
    if lines:
        for b in rows:                  # in the adapter's words: "R height positions …"
            imgui.text(router.describe(b) + ("" if b.enabled else " (off)"))
    # routes are the loaded preset's (plan 13 §3.3): an edit here changes
    # the table and the preset's dirty dot, and writes no file
    if gate and rows:
        _gate_menu(router, rows)


def _gate_menu(router, rows) -> bool:
    """Pick the pinch that has to be held for these rows to act; the pick
    is written by name (``hand:right.pinch.index``, decision register row
    20), and a gate an older preset names by number shows as its switch."""
    gates = getattr(router, "gates", {}).get("hand") or []
    if not gates:
        return False
    cur = next((b.when for b in rows if b.when), None)
    lane = router.lane(cur)[1] if cur is not None else None
    shown = next((lb for src, lb in gates if src == lane), None)
    if not imgui.begin_menu(f"Gate: {shown or 'none'}"):
        return False
    hit = False
    if imgui.menu_item_simple("none", selected=cur is None) and cur is not None:
        for b in rows:
            b.when = None
        hit = True
    for src, lb in gates:
        addr = router.address("hand", src)
        if imgui.menu_item_simple(lb, selected=src == lane) and cur != addr:
            for b in rows:
                b.when = addr
            hit = True
    imgui.end_menu()
    return hit


# ---- the page ----

def page(panel, dt: float) -> None:
    settings = getattr(panel, "hand_settings", None)
    io = getattr(panel, "hands", None)
    panel._section("hands", GROUP if settings is not None else None)
    if settings is None:
        imgui.text_disabled("no hands setup — see [hands] in config.toml")
        return
    _status(io, getattr(panel, "config_notes", None) or ())
    _box(io)
    if _has_pinches(io):        # the switches beside the box: the page has
        imgui.same_line()       # to fit the control window
        _pinches(io)
    _ghost(panel)
    k = _axes(panel, io, settings)
    imgui.spacing()
    _editor(panel, io, settings, k)
    imgui.spacing()
    if imgui.collapsing_header("feel & calibration"):
        for pid in ("smooth", "response", "catch", "learn_depth", "rate", "steady",
                    "pinch_close", "pinch_open", "pinch_hold"):
            if f"{GROUP}.{pid}" in panel.reg:    # a setting newer than a hot-reloaded registry
                panel._row(f"{GROUP}.{pid}")
        _calibrate(io, settings, k)


GHOST_MORE = "more ▸"          # the chip that opens the ghost's popup
GHOST_MORE_WARN = "! more ▸"   # …while the popup holds a note to read
GHOST_POPUP = "##ghost.more"


def _ghost(panel) -> None:
    """The ghost hands' display (hyperspace/ghost.py) — the host's params,
    shown here because this is where the hands are looked at.

    Two lines while the ghost is on — the page has no room for a third
    (test_ui_shell): ``[x] Ghost hands  OPACITY [slider]  more ▸`` then
    ``STYLE [combo]  GUIDE [combo]``. "more ▸" opens a popup with the
    rig's settings (Mirror, and Tethers once a guide is on) and the
    ghost's notes; while there is a note the chip reads "! more ▸" in the
    warning colour and its hover says it. Each group goes on the line only
    when it fits beside what is there, so a narrower panel wraps it rather
    than drawing it over its neighbour. With the ghost off: the switch,
    and the ghost's error under it if it has one."""
    if "ghost.on" not in panel.reg:
        return
    reg = panel.reg
    on = bool(reg["ghost.on"].value)
    notes = ghost_notes(panel)
    sp = imgui.get_style().item_spacing.x
    right = imgui.get_cursor_screen_pos().x + imgui.get_content_region_avail().x
    panel._check("ghost.on")
    if not on:
        err = [t for t, warn in notes if warn]
        if err:             # a refused build says so with the ghost off too
            _note_line(err[0])
        return
    more = GHOST_MORE_WARN if notes else GHOST_MORE
    more_w = ui.chip_w(more)
    label_w = ui._micro_width("Opacity") + ui.LABEL_GAP
    if _beside(right, label_w + GHOST_ALPHA_MIN):
        imgui.same_line()
    # the slider takes the line's room the chip leaves, or the whole line
    # when the chip has to wrap under it
    x = imgui.get_cursor_screen_pos().x + label_w
    alpha_w = right - x - sp - more_w
    if alpha_w < GHOST_ALPHA_MIN:
        alpha_w = right - x
    panel._label_cell("Opacity", width=label_w)
    panel._slider("ghost.alpha", alpha_w)
    if _beside(right, more_w):
        imgui.same_line()
    _more_chip(panel, more, notes)
    for k, (pid, label) in enumerate((("ghost.style", "Style"), ("ghost.guide", "Guide"))):
        if pid not in reg:
            continue
        lw = ui._micro_width(label) + ui.LABEL_GAP
        cw = _combo_w(reg[pid].names)
        if k and _beside(right, lw + cw):
            imgui.same_line()
        panel._label_cell(label, width=lw)
        panel._combo(pid, cw)
    _more_popup(panel, notes)


def _beside(right: float, w: float) -> bool:
    """Does an item `w` px wide still fit on the line, after the last item
    and the spacing, before `right` (screen x)? Then `same_line()` it."""
    return imgui.get_item_rect_max().x + imgui.get_style().item_spacing.x + w <= right + 0.5


def _combo_w(names) -> float:
    """A combo just wide enough for its longest entry, whole: the text, the
    frame's padding either side and the arrow (one frame square)."""
    s = imgui.get_style()
    return (max(imgui.calc_text_size(n).x for n in names) + 2 * s.frame_padding.x
            + imgui.get_frame_height())


def _note_line(text: str) -> None:
    """One line in the warning colour, cut to the page's width with the
    whole text on hover: a line that ran on would be cut by the page."""
    shown = ui.fit_text(text, imgui.get_content_region_avail().x)
    imgui.text_colored(ui.WARN, shown)
    if shown != text and imgui.is_item_hovered():
        ui.tooltip(text)


def ghost_notes(panel) -> list[tuple[str, bool]]:
    """What the page has to say about the ghost, as (text, warn): why it
    could not build or draw (ghost.Ghost.error — a refused build stays
    until a reload, anything else until the ghost goes off), then, with
    the ghost on in screentop or HMD, that those modes' axes are reasoned,
    not seen (ghost.MODES: only desktop's are the hands/core.py table;
    hand check Q9). An unknown mode draws as desktop."""
    out = []
    err = getattr(getattr(getattr(panel, "renderer", None), "ghost", None), "error", "")
    if err:
        out.append((err, True))
    mode = ghost_mode(getattr(panel, "hands", None))
    if panel.reg["ghost.on"].value and mode in GHOST_MODES and mode != "desktop":
        note = (f"ghost axes for {mode} are unmeasured: left/right and up may be wrong"
                " — Mirror flips left for right")
        out.append((note, False))
    return out


def _more_chip(panel, label: str, notes) -> None:
    if ui.lit_chip(f"{label}##ghost.more", False, ui.WARN if notes else None):
        imgui.open_popup(GHOST_POPUP)
    if imgui.is_item_hovered():
        tip = "Mirror" + (" and Tethers" if "ghost.tethers" in panel.reg else "")
        ui.tooltip("\n".join([f"{tip}, and the ghost's notes.", *(t for t, _ in notes)]))


def _more_popup(panel, notes) -> None:
    """The rig's ghost settings and the ghost's notes, off "more ▸"."""
    if not imgui.begin_popup(GHOST_POPUP):
        return
    reg = panel.reg
    if "ghost.mirror" in reg:
        panel._check("ghost.mirror", "Mirror")
    if "ghost.tethers" in reg:
        guided = "ghost.guide" not in reg or bool(reg["ghost.guide"].value)
        imgui.begin_disabled(not guided)
        panel._check("ghost.tethers", "Tethers")
        imgui.end_disabled()
        if not guided:
            imgui.same_line()
            imgui.text_disabled("with a guide on")
    if notes:
        imgui.separator()
        imgui.push_text_wrap_pos(imgui.get_cursor_pos_x() + GHOST_NOTE_W)
        for text, warn in notes:
            if warn:
                imgui.text_colored(ui.WARN, text)
            else:
                imgui.text_disabled(text)
        imgui.pop_text_wrap_pos()
    imgui.end_popup()


def ghost_mode(io) -> str:
    """The tracking mode the ghost draws in (what `Ghost.poses` reads:
    the source's ``cfg["mode"]``, desktop without one), lower case."""
    return str((getattr(io, "cfg", None) or {}).get("mode", "desktop")).lower()


def _status(io, notes=()) -> None:
    if io is None:
        # a tracker that would not open says why (app._open_hands' note)
        why = next((n for n in notes if n.startswith("hands: ")), "")
        if why:
            imgui.text_colored(ui.WARN, why)
        else:
            imgui.text_disabled("tracker off — [hands] enabled = true in config.toml; "
                                "the setup still edits and saves")
        return
    port = io.out_name or "no DAW port"
    imgui.text_disabled(f"{io.status or '—'}  ·  {_ins(io)}  ·  {port}")
    if imgui.is_item_hovered():
        ui.tooltip("● in the box  ·  ◌ tracked, but outside the box: it reads "
                          "absent  ·  ○ not seen")
    # the DAW port is the hands-daw sink's (plan 27 B3): why it has none
    # comes through `HandsIO.carry`, beside the instrument's own error
    err = io.error or getattr(io, "daw_error", "")
    if err:
        imgui.text_colored(ui.WARN, err)
    elif io.last:
        imgui.text_disabled(f"last out  {io.last}")


def _ins(io) -> str:
    """Each hand's glyph for the status line: ● in the box, ◌ tracked
    but outside it (so absent to everything), ○ not seen."""
    out = getattr(io, "outside", None) or {}
    return " ".join(f"{s[0].upper()}{'●' if io.present[s] else '◌' if out.get(s) else '○'}"
                    for s in SIDES)


def _pinches(io) -> None:
    """The eight thumb-to-finger switches: lit as they close, each with
    the live gap that closed it. The number is the tuning instrument —
    watch how near a finger actually gets, then set Pinch close under
    it. Ring and pinky never come as close as index and middle."""
    if not _has_pinches(io):
        return
    close = io.settings.pinch_close
    imgui.begin_group()
    for s in SIDES:
        for r in range(0, len(PINCHES), 2):        # two switches a line, beside the box
            imgui.text_colored(ui.DIM, f"{s[0].upper()}" if r == 0 else " ")
            for f in PINCHES[r:r + 2]:
                on = io.gates[s][f].on
                d = (io.frame[s] or {}).get(f"pinch_{f}")
                near = d is not None and d < close * 1.35   # closing in on the threshold
                col = ui.RED if on else (ui.TEXT if near else ui.FAINT)
                imgui.same_line()
                imgui.text_colored(col, f"{f[:3]} {'●' if on else '○'}")
                imgui.same_line(0.0, 2.0)
                # the gap moves every frame: the readout face, so it can't jitter
                ui._readout("  —  " if d is None else f"{d:.2f}", col)
    imgui.end_group()


def _has_pinches(io) -> bool:
    return io is not None and bool(io.cfg.get("pinch_gates"))


def _mm(v: float) -> str:
    return f"{v:.0f}".replace("-", "−")


def _box_text(box) -> str:
    """The interaction box in words, for the tooltip and the calibrate
    block: "x −262…262 · y 72…402 · z open mm", or "" for no box."""
    if not box:
        return ""
    parts = [f"{c} open" if box.get(c) is None
             else f"{c} {_mm(box[c][0])}…{_mm(box[c][1])}" for c in BOX_AXES]
    return " · ".join(parts) + " mm"


def _box(io) -> None:
    """The box from above — x across, z down toward the performer — and
    a height gauge at its right, both inside the one BOX_W × BOX_H frame.

    The interaction box (`io.box`) is the inner rectangle and the gauge's
    bracket; an open coordinate draws no line. A hand in the box is its
    filled dot; one tracked but outside (`io.outside`) a hollow ring, dim,
    at its clamped position. No box: no rectangle and no bracket."""
    w = BOX_W - GAUGE_GAP - GAUGE_W                 # the view from above
    pos = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    x0, y0, x1, y1 = pos.x, pos.y, pos.x + w, pos.y + BOX_H
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x1, y1), ui.u32(ui.LINE))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dl.add_circle_filled(imgui.ImVec2(cx, cy), 2.5, ui.u32(ui.DIM))      # the camera
    g0, g1 = pos.x + BOX_W - GAUGE_W, pos.x + BOX_W                       # the gauge
    gx = (g0 + g1) / 2
    dl.add_rect(imgui.ImVec2(g0, y0), imgui.ImVec2(g1, y1), ui.u32(ui.LINE))

    def sx(mm: float, pad: float = 6.0) -> float:
        return min(max(cx + mm / VIEW_X_MM * (w / 2 - 6), x0 + pad), x1 - pad)

    def sz(mm: float, pad: float = 6.0) -> float:
        return min(max(cy + mm / VIEW_Z_MM * (BOX_H / 2 - 6), y0 + pad), y1 - pad)

    def high(mm: float) -> float:                   # a height over the gauge's range, 0–1
        return min(max((mm - GAUGE_MM[0]) / (GAUGE_MM[1] - GAUGE_MM[0]), 0.0), 1.0)

    def sy(mm: float) -> float:
        return y1 - 2 - high(mm) * (BOX_H - 4)

    box = getattr(io, "box", None) or {}
    bx, by, bz = (box.get(c) for c in BOX_AXES)
    dim = ui.u32(ui.DIM)
    # the box's faces: a pair of lines per bounded coordinate, each as
    # long as the other coordinate's bound (the whole view when it is open)
    # A box wider than the view's fixed scale has its faces clamped FACE_PAD
    # inside the frame, so there is still room to show a hand beyond them.
    zs = (sz(bz[0], FACE_PAD), sz(bz[1], FACE_PAD)) if bz else (y0 + 1, y1 - 1)
    xs = (sx(bx[0], FACE_PAD), sx(bx[1], FACE_PAD)) if bx else (x0 + 1, x1 - 1)

    def place(v: float, at: float, b, faces, out: bool) -> float:
        """A hand's clamped pixel, kept on its own side of a drawn face:
        inside one never past it, outside one clear of it."""
        if b is None:
            return at
        if not out:
            return min(max(at, faces[0]), faces[1])
        if v > b[1]:
            return max(at, faces[1] + 6.0)
        return min(at, faces[0] - 6.0) if v < b[0] else at
    if bx:
        for x in xs:
            dl.add_line(imgui.ImVec2(x, zs[0]), imgui.ImVec2(x, zs[1]), dim)
    if bz:
        for z in zs:
            dl.add_line(imgui.ImVec2(xs[0], z), imgui.ImVec2(xs[1], z), dim)
    if by:                                          # the box's height: a bracket
        lo, hi = sy(by[0]), sy(by[1])
        dl.add_line(imgui.ImVec2(gx, lo), imgui.ImVec2(gx, hi), dim)
        for y in (lo, hi):
            dl.add_line(imgui.ImVec2(g0 + 2, y), imgui.ImVec2(g1 - 2, y), dim)
    if io is not None:
        outside = getattr(io, "outside", None) or {}
        for side, col in (("left", LEFT), ("right", ui.RED)):
            f, out = io.frame[side], False
            if f is None:
                f, out = outside.get(side), True
            if f is None:
                continue
            px = place(f["x"], sx(f["x"]), bx, xs, out)
            py = place(f["z"], sz(f["z"]), bz, zs, out)
            r = 3.0 + 7.0 * high(f["y"])
            if out:                                 # tracked, outside the box: absent
                col = imgui.ImVec4(col.x, col.y, col.z, OUTSIDE_ALPHA)
                dl.add_circle(imgui.ImVec2(px, py), r, ui.u32(col), 0, 1.5)
            else:
                dl.add_circle_filled(imgui.ImVec2(px, py), r, ui.u32(col))
            ty = sy(f["y"])                         # its height on the gauge
            dl.add_line(imgui.ImVec2(g0 + 1, ty), imgui.ImVec2(g1 - 1, ty), ui.u32(col), 2.0)
    imgui.dummy(imgui.ImVec2(BOX_W, BOX_H))
    if imgui.is_item_hovered():
        said = _box_text(box)
        ui.tooltip("The box from above: the camera at the centre, the "
                          "performer at the bottom edge. A dot's size is the hand's "
                          "height, and the gauge at the right shows it "
                          f"({GAUGE_MM[0]:.0f}–{GAUGE_MM[1]:.0f} mm).\n"
                          + (f"box {said} — a hand outside it reads absent "
                             "(a hollow ring here)" if said
                             else "no box — calibrate to set one"))


def _axes(panel, io, settings) -> int:
    """One row per axis; returns the selected index."""
    k = _sel(panel, len(settings.axes))
    bad = conflicts(settings)
    h = imgui.get_text_line_height() + 2
    # the dance sources (plan 24 C4) take a column on the right of the
    # rows, so the page grows no taller: it has to fit the control window
    dance = io is not None and getattr(io, "dance", None) is not None
    right = DANCE_W if dance else 0.0
    top, avail = imgui.get_cursor_screen_pos(), imgui.get_content_region_avail().x
    # twelve rows have to share the page with the editor: tight spacing
    imgui.push_style_var(imgui.StyleVar_.item_spacing,
                         imgui.ImVec2(imgui.get_style().item_spacing.x, 2.0))
    for i, a in enumerate(settings.axes):
        if _axis_row(panel, io, i, a, i == k, h, a.name in bad, right):
            _select(panel, i)
            k = i
    if dance:
        end = imgui.get_cursor_screen_pos()
        imgui.set_cursor_screen_pos(imgui.ImVec2(top.x + avail - DANCE_W + DANCE_GAP, top.y))
        _dance(io, h)
        # back under both: the column (five lines) is taller than a short
        # `dofs` list, and what follows must not run into it. Then an
        # empty item, so the window's content size takes the cursor; it
        # adds one item spacing, which the cursor is set that much short of
        gap = imgui.get_style().item_spacing.y
        y = max(end.y, imgui.get_item_rect_max().y + gap)
        imgui.set_cursor_screen_pos(imgui.ImVec2(end.x, y - gap))
        imgui.dummy(imgui.ImVec2(0.0, 0.0))
    imgui.pop_style_var()
    return k


def _axis_row(panel, io, i: int, a, selected: bool, h: float, conflict: bool,
              right: float = 0.0) -> bool:
    """One axis: its name, the output bar with the hand's live point and the
    rest tick, and what goes to the DAW, `right` px short of the edge. True
    when it was clicked."""
    st = io.state[i] if io is not None else None
    here = io is not None and io.present[a.side]
    imgui.push_style_color(imgui.Col_.text, ui.RED if conflict else
                           (imgui.ImVec4(0.92, 0.92, 0.92, 1) if here else ui.DIM))
    hit = imgui.selectable(f"{a.label}##hax{i}", selected, 0, imgui.ImVec2(ROW_LABEL_W, h))[0]
    imgui.pop_style_color()
    imgui.same_line()
    bar_w = imgui.get_content_region_avail().x - OUT_W - right
    pos = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    bx0, by0, bx1, by1 = pos.x, pos.y + 3, pos.x + bar_w, pos.y + h - 3
    span = bx1 - bx0 - 2
    dl.add_rect(imgui.ImVec2(bx0, by0), imgui.ImVec2(bx1, by1), ui.u32(ui.LINE))
    if a.rest == "return":
        rx = bx0 + 1 + span * a.rest_value
        dl.add_line(imgui.ImVec2(rx, by1), imgui.ImVec2(rx, by1 + 2), ui.u32(ui.DIM))
    if st is not None and st.y is not None:
        # dim while the hand is away: the bar is then the DAW output
        # (spring or hold) and the routing lane reads NaN
        live = st.follow.live
        dl.add_rect_filled(imgui.ImVec2(bx0 + 1, by0 + 1),
                           imgui.ImVec2(bx0 + 1 + span * st.y, by1 - 1),
                           ui.u32(imgui.ImVec4(0.92, 0.92, 0.92, 0.85 if live else 0.35)))
    if st is not None and st.target is not None:
        tx = bx0 + 1 + span * st.target
        dl.add_line(imgui.ImVec2(tx, by0 - 1), imgui.ImVec2(tx, by1 + 1), ui.u32(ui.RED))
    imgui.dummy(imgui.ImVec2(bar_w, h))
    if imgui.is_item_hovered():
        y = "—" if st is None or st.y is None else f"{st.y:.3f}"
        if st is not None and st.y is not None and not st.follow.live:
            y += " (DAW only; lane —)"
        raw = "—" if st is None or st.raw is None else \
            f"{st.raw:.1f} {FEATURES[a.feature][0]}"
        ui.tooltip(f"{a.name}: out {y}  ·  hand {raw}")
    imgui.same_line()
    q = "" if st is None or st.q is None else f" {st.q}"
    imgui.text_disabled(_out_text(a) + q if a.out != "off" else "off")
    return hit


DANCE_BAR_W = 16.0     # one dance source's bar
DANCE_W = 220.0        # the dance column, right of the axis rows …
DANCE_GAP = 14.0       # … this much of it a gap


def _dance(io, h: float) -> None:
    """The dance sources (plan 24 C4), live, in a column beside the axes:
    per hand a row of the five curls (thumb … pinky) and the grab switch
    (C5: ● while the hand is a closed fist), and a row of spread, energy
    and flick; then a row for the two hands together — gap, twist.
    Each a small bar like an axis's output, hollow while it reads nothing
    (the hand away, no skeleton). Hover a bar for its address and value:
    what a ROUTING row names."""
    lay = io._layout()
    lanes, pair = io.lanes(), io.pair_lanes()
    imgui.begin_group()
    for s in SIDES:
        col = LEFT if io.present[s] else ui.DIM
        side = s[0].upper()
        rows = [(f"{side} curl", [(None, f"curl.{d}") for d in DIGITS]),
                (f"{side} spr", [(None, "spread"), ("en", "energy"), ("flk", "flick")])]
        for label, bars in rows:
            imgui.text_colored(col, label)
            for tag, kind in bars:
                if tag:
                    imgui.same_line(0.0, 6.0)
                    imgui.text_disabled(tag)
                imgui.same_line(0.0, 3.0)
                _dance_bar(f"hand:{s}.{kind}", lanes[lay.dance[(s, kind)]], h)
            if label.endswith("curl"):
                imgui.same_line(0.0, 6.0)
                _grab(io, s, lanes[lay.grab[s]])
    for k, name in enumerate(lay.pair_names):
        if k:
            imgui.same_line(0.0, 6.0)
        imgui.text_colored(ui.DIM, name)
        imgui.same_line(0.0, 3.0)
        _dance_bar(f"hands:{lay.pair_addresses[k]}", pair[k], h, centred=name == "twist")
    imgui.end_group()


def _grab(io, side: str, v: float) -> None:
    """One hand's grab switch: ● lit while closed, ○ open. Hover: the
    address, and how closed the hand is (`fist`, what the switch reads)
    against where it closes and lets go — the number to watch."""
    on = v >= 0.5
    imgui.text_colored(ui.RED if on else (ui.TEXT if io.present[side] else ui.FAINT),
                       f"grab {'●' if on else '○'}")
    if imgui.is_item_hovered():
        f = fist(io.dance[side].raw.get("curl"))
        level = "—" if f is None else f"{f:.2f}"
        ui.tooltip(f"hand:{grab_name(side)}: {'closed' if on else 'open'}  ·  "
                          f"fist {level} (closes ≥ {GRAB_CLOSE:.2f}, "
                          f"lets go < {GRAB_OPEN:.2f})")


def _dance_bar(address: str, v: float, h: float, *, centred: bool = False) -> None:
    """One source's value as a small bar; a centred one (the twist) with a
    tick at the middle. Hover: the address and the value."""
    pos = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    x0, y0, x1, y1 = pos.x, pos.y + 3, pos.x + DANCE_BAR_W, pos.y + h - 3
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x1, y1), ui.u32(ui.LINE))
    live = not math.isnan(v)
    if live:
        dl.add_rect_filled(imgui.ImVec2(x0 + 1, y0 + 1),
                           imgui.ImVec2(x0 + 1 + (DANCE_BAR_W - 2) * v, y1 - 1),
                           ui.u32(imgui.ImVec4(0.92, 0.92, 0.92, 0.85)))
    if centred:
        mx = x0 + DANCE_BAR_W / 2
        dl.add_line(imgui.ImVec2(mx, y1), imgui.ImVec2(mx, y1 + 2), ui.u32(ui.DIM))
    imgui.dummy(imgui.ImVec2(DANCE_BAR_W, h))
    if imgui.is_item_hovered():
        ui.tooltip(f"{address}: {v:.3f}" if live else f"{address}: —")


def _out_text(a) -> str:
    if a.out == "cc":
        return f"{a.channel}·cc{a.number}"
    if a.out == "cc14":
        return f"{a.channel}·cc{a.number}/{a.number + 32}"
    if a.out == "pitch":
        return f"{a.channel}·bend"
    return f"{a.channel}·press"


def _editor(panel, io, settings, k: int) -> None:
    a = settings.axes[k]
    p = f"{GROUP}.{a.name}"
    ui._micro(f"{a.side} · {a.feature} · {FEATURES[a.feature][0]}")
    imgui.separator()
    st = io.state[k] if io is not None else None
    _transfer(a, st)
    imgui.same_line()
    imgui.begin_group()                 # the feel knobs and the flags beside the
    if imgui.begin_table(f"##feel.{a.name}", 2,   # plot: the page has to fit the window
                         imgui.TableFlags_.sizing_stretch_same):
        for key, label in (("deadzone", "zone"), ("curve", "curve"),
                           ("attack", "attack"), ("decay", "decay")):
            imgui.table_next_column()
            panel.half(f"{p}.{key}", label, label_w=ROW_LABEL_W)
        imgui.end_table()
    panel._check(f"{p}.invert")
    imgui.same_line()
    panel._check(f"{p}.bipolar")
    imgui.same_line()
    if imgui.small_button("mirror"):
        mirror(settings, a.name)
    if imgui.is_item_hovered():
        ui.tooltip("Copy this axis's feel (not its MIDI out) to the same axis "
                          "on the other hand.")
    if io is not None:
        imgui.same_line()
        solo = io.solo == k
        imgui.push_style_color(imgui.Col_.text, ui.RED if solo else ui.DIM)
        if imgui.small_button("solo"):
            io.solo = None if solo else k
        imgui.pop_style_color()
        if imgui.is_item_hovered():
            ui.tooltip("Send only this axis to the DAW port — for a DAW's MIDI learn.")
    imgui.end_group()
    ui._micro("On exit")
    imgui.same_line(ui.LABEL_W)
    panel._combo(f"{p}.rest", 70)
    if a.rest == "return":
        imgui.same_line()
        panel._slider(f"{p}.rest_value")
        if imgui.begin_table(f"##spring.{a.name}", 2, imgui.TableFlags_.sizing_stretch_same):
            imgui.table_next_column()
            panel.half(f"{p}.return", label_w=ROW_LABEL_W)
            imgui.table_next_column()
            panel.half(f"{p}.bounce", label_w=ROW_LABEL_W)
            imgui.end_table()
    ui._micro("MIDI out")
    imgui.same_line(ui.LABEL_W)
    panel._combo(f"{p}.out", 70)
    if a.out != "off":
        imgui.same_line()
        panel._slider(f"{p}.channel", 58)
        if a.out in ("cc", "cc14"):
            imgui.same_line()
            panel._slider(f"{p}.number")
    why = conflicts(settings).get(a.name)
    if why:
        imgui.text_colored(ui.WARN, why)


def _transfer(a, st) -> None:
    """The static transfer u → shaped, with the hand's point on it."""
    pos = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    s = PLOT_W
    x0, y0 = pos.x, pos.y
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x0 + s, y0 + s), ui.u32(ui.LINE))
    dl.add_line(imgui.ImVec2(x0, y0 + s), imgui.ImVec2(x0 + s, y0), ui.u32(ui.LINE))
    n = 48
    pts = [imgui.ImVec2(x0 + s * j / n,
                        y0 + s * (1 - shape(j / n, bipolar=a.bipolar, deadzone=a.deadzone,
                                            c=a.curve)))
           for j in range(n + 1)]
    for p0, p1 in itertools.pairwise(pts):
        dl.add_line(p0, p1, ui.u32(imgui.ImVec4(0.92, 0.92, 0.92, 1)), 1.2)
    if st is not None and st.u is not None and st.target is not None:
        dl.add_circle_filled(imgui.ImVec2(x0 + s * st.u, y0 + s * (1 - st.target)), 3.0,
                             ui.u32(ui.RED))
    imgui.dummy(imgui.ImVec2(s, s))
    if imgui.is_item_hovered():
        ui.tooltip("Hand position across the calibrated range (→) against what "
                          "the axis outputs before attack/decay (↑). Dead zone and curve "
                          "shape it; the red dot is the hand now.")


def _calibrate(io, settings, k: int) -> None:
    imgui.separator()
    ui._micro("calibrate")
    if io is None:
        imgui.text_disabled("needs the tracker on")
        return
    left = io.calibrating
    if left > 0:
        imgui.text_colored(ui.RED, f"sweeping… {math.ceil(left)} s — every axis, end to end")
        if imgui.small_button("cancel"):
            io.cancel_calibration()
    else:
        if imgui.small_button(f"calibrate {CAL_SECONDS:.0f} s"):
            io.start_calibration(CAL_SECONDS)
        if imgui.is_item_hovered():
            ui.tooltip("For the next 20 s, move each hand through everything it "
                              "should reach. Each axis's range becomes what you covered "
                              "(2nd–98th percentile), saved to hands.json for this box, "
                              "and the box becomes what your palms covered plus "
                              f"{BOX_MARGIN:.0f} mm; a hand outside it reads absent.")
        imgui.same_line()
        if imgui.small_button("reset ranges"):
            io.reset_ranges()
        if imgui.is_item_hovered():
            ui.tooltip("Every axis's range back to its default, and the box "
                              "opened: a hand counts wherever the tracker sees it. "
                              "Another sweep sets both again.")
    st, a = io.state[k], settings.axes[k]
    imgui.text_disabled(f"{a.name}: {st.lo:.1f} … {st.hi:.1f} {FEATURES[a.feature][0]}")
    said = _box_text(getattr(io, "box", None))
    imgui.text_disabled(f"box {said}" if said else "box open")
    if io.cal_note:
        imgui.text_disabled(io.cal_note)
