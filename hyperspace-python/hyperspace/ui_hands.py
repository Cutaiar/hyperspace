"""The HANDS page — the Ultraleap hands, live, and the setup that shapes them.

Top to bottom:

  hands  ◀ setup ▶ …       the library strip for the `hands` group: a
                           setup is every per-axis and global setting
  status                   tracker, DAW port, the last MIDI sent
  the box, from above      each palm as a dot (left white, right red),
                           its size the hand's height; the camera at the
                           centre
  twelve axes              one row each: the output y as a white bar,
                           where the hand is (the shaped target) as a
                           hairline, the rest value as a dim tick, the
                           MIDI out on the right. Click a row to edit it.
  the selected axis        its transfer (dead zone and curve over the
                           calibrated range) with the live point on it,
                           then invert · centred · dead zone · curve ·
                           attack · decay · on exit · rest · return ·
                           bounce · MIDI out. "mirror" copies the feel to
                           the same axis on the other hand; "solo" sends
                           only this axis to the DAW (for a DAW's learn).
  feel                     steadiness, response, catch, MIDI rate,
                           hysteresis — the whole instrument
  calibrate                a timed sweep that writes the box's ranges

Every control is a registry param (hands.register), so the widgets are
the panel's own and right-click → Learn works on them too.
"""

from __future__ import annotations

import itertools
import math

from imgui_bundle import imgui

from . import ui
from .hand_signal import shape
from .hands import FEATURES, GROUP, SIDES, conflicts, mirror

ROW_LABEL_W = 62.0
OUT_W = 100.0
BOX_H = 92.0
PLOT_W = 96.0
CAL_SECONDS = 20.0
LEFT = imgui.ImVec4(0.92, 0.92, 0.92, 1.0)
DIM_LINE = imgui.ImVec4(0.25, 0.25, 0.25, 1.0)


def _u32(c):
    return imgui.color_convert_float4_to_u32(c)


def _sel(panel, n: int) -> int:
    k = getattr(panel, "_hands_sel", 0)
    return min(max(k, 0), n - 1)


# ---- right-click menu: a param's hand bindings ----

def ctx_rows(panel, p) -> None:
    """The context menu's hand part: what hand axis drives this param."""
    router = getattr(panel, "router", None)
    if router is None:
        return
    names = getattr(router, "labels", {}).get("hand") or []
    rows = [b for b in router.table.of("hand") if b.op == "abs" and b.target == p.id]
    for b in rows:
        i = b.index
        imgui.text(f"hand {names[i] if 0 <= i < len(names) else i}")
    if rows and imgui.menu_item_simple("Unbind hand"):
        for b in rows:                  # the abs rows only: its routes stay
            router.table.remove(b)
        router.table.write()


# ---- the page ----

def page(panel, dt: float) -> None:
    settings = getattr(panel, "hand_settings", None)
    io = getattr(panel, "hands", None)
    panel._section("hands", GROUP if settings is not None else None)
    if settings is None:
        imgui.text_disabled("no hands setup — see [hands] in config.toml")
        return
    _status(io)
    _box(io)
    k = _axes(panel, io, settings)
    imgui.spacing()
    _editor(panel, io, settings, k)
    imgui.spacing()
    if imgui.collapsing_header("feel & calibration"):
        for pid in ("smooth", "response", "catch", "rate", "steady"):
            panel._row(f"{GROUP}.{pid}")
        _calibrate(io, settings, k)


def _status(io) -> None:
    if io is None:
        imgui.text_disabled("tracker off — [hands] enabled = true in config.toml; "
                            "the setup still edits and saves")
        return
    ins = " ".join(f"{s[0].upper()}{'●' if io.present[s] else '○'}" for s in SIDES)
    port = io.out_name or "no DAW port"
    imgui.text_disabled(f"{io.status or '—'}  ·  {ins}  ·  {port}")
    if io.error:
        imgui.text_colored(ui.WARN, io.error)
    elif io.last:
        imgui.text_disabled(f"last out  {io.last}")


def _box(io) -> None:
    """The box from above: x across, z down toward the performer."""
    w = imgui.get_content_region_avail().x
    pos = imgui.get_cursor_screen_pos()
    dl = imgui.get_window_draw_list()
    x0, y0, x1, y1 = pos.x, pos.y, pos.x + w, pos.y + BOX_H
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x1, y1), _u32(DIM_LINE))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dl.add_circle_filled(imgui.ImVec2(cx, cy), 2.5, _u32(ui.DIM))      # the camera
    if io is not None:
        for side, col in (("left", LEFT), ("right", ui.RED)):
            f = io.frame[side]
            if f is None:
                continue
            px = cx + f["x"] / 260.0 * (w / 2 - 6)
            py = cy + f["z"] / 160.0 * (BOX_H / 2 - 6)
            px, py = min(max(px, x0 + 6), x1 - 6), min(max(py, y0 + 6), y1 - 6)
            r = 3.0 + 7.0 * min(max((f["y"] - 80.0) / 320.0, 0.0), 1.0)
            dl.add_circle_filled(imgui.ImVec2(px, py), r, _u32(col))
    imgui.dummy(imgui.ImVec2(w, BOX_H))
    if imgui.is_item_hovered():
        imgui.set_tooltip("The box from above: the camera at the centre, the "
                          "performer at the bottom edge. A dot's size is the hand's height.")


def _axes(panel, io, settings) -> int:
    """One row per axis; returns the selected index."""
    k = _sel(panel, len(settings.axes))
    bad = conflicts(settings)
    h = imgui.get_text_line_height() + 2
    for i, a in enumerate(settings.axes):
        st = io.state[i] if io is not None else None
        here = io is not None and io.present[a.side]
        imgui.push_style_color(imgui.Col_.text, ui.RED if a.name in bad else
                               (imgui.ImVec4(0.92, 0.92, 0.92, 1) if here else ui.DIM))
        if imgui.selectable(f"{a.label}##hax{i}", i == k, 0,
                            imgui.ImVec2(ROW_LABEL_W, h))[0]:
            panel._hands_sel = k = i
        imgui.pop_style_color()
        imgui.same_line()
        bar_w = imgui.get_content_region_avail().x - OUT_W
        pos = imgui.get_cursor_screen_pos()
        dl = imgui.get_window_draw_list()
        bx0, by0, bx1, by1 = pos.x, pos.y + 3, pos.x + bar_w, pos.y + h - 3
        span = bx1 - bx0 - 2
        dl.add_rect(imgui.ImVec2(bx0, by0), imgui.ImVec2(bx1, by1), _u32(DIM_LINE))
        if a.rest == "return":
            rx = bx0 + 1 + span * a.rest_value
            dl.add_line(imgui.ImVec2(rx, by1), imgui.ImVec2(rx, by1 + 2), _u32(ui.DIM))
        if st is not None and st.y is not None:
            dl.add_rect_filled(imgui.ImVec2(bx0 + 1, by0 + 1),
                               imgui.ImVec2(bx0 + 1 + span * st.y, by1 - 1),
                               _u32(imgui.ImVec4(0.92, 0.92, 0.92, 0.85 if here else 0.35)))
        if st is not None and st.target is not None:
            tx = bx0 + 1 + span * st.target
            dl.add_line(imgui.ImVec2(tx, by0 - 1), imgui.ImVec2(tx, by1 + 1), _u32(ui.RED))
        imgui.dummy(imgui.ImVec2(bar_w, h))
        if imgui.is_item_hovered():
            y = "—" if st is None or st.y is None else f"{st.y:.3f}"
            raw = "—" if st is None or st.raw is None else \
                f"{st.raw:.1f} {FEATURES[a.feature][0]}"
            imgui.set_tooltip(f"{a.name}: out {y}  ·  hand {raw}")
        imgui.same_line()
        q = "" if st is None or st.q is None else f" {st.q}"
        imgui.text_disabled(_out_text(a) + q if a.out != "off" else "off")
    return k


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
    imgui.begin_group()
    panel._check(f"{p}.invert")
    panel._check(f"{p}.bipolar")
    if imgui.small_button("mirror"):
        mirror(settings, a.name)
    if imgui.is_item_hovered():
        imgui.set_tooltip("Copy this axis's feel (not its MIDI out) to the same axis "
                          "on the other hand.")
    if io is not None:
        solo = io.solo == k
        imgui.push_style_color(imgui.Col_.text, ui.RED if solo else ui.DIM)
        if imgui.small_button("solo"):
            io.solo = None if solo else k
        imgui.pop_style_color()
        if imgui.is_item_hovered():
            imgui.set_tooltip("Send only this axis to the DAW port — for a DAW's MIDI learn.")
    imgui.end_group()
    for key in ("deadzone", "curve", "attack", "decay"):
        panel._row(f"{p}.{key}")
    ui._micro("On exit")
    imgui.same_line(ui.LABEL_W)
    panel._combo(f"{p}.rest", 70)
    if a.rest == "return":
        imgui.same_line()
        panel._slider(f"{p}.rest_value")
        panel._row(f"{p}.return")
        panel._row(f"{p}.bounce")
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
    dl.add_rect(imgui.ImVec2(x0, y0), imgui.ImVec2(x0 + s, y0 + s), _u32(DIM_LINE))
    dl.add_line(imgui.ImVec2(x0, y0 + s), imgui.ImVec2(x0 + s, y0), _u32(DIM_LINE))
    n = 48
    pts = [imgui.ImVec2(x0 + s * j / n,
                        y0 + s * (1 - shape(j / n, bipolar=a.bipolar, deadzone=a.deadzone,
                                            c=a.curve)))
           for j in range(n + 1)]
    for p0, p1 in itertools.pairwise(pts):
        dl.add_line(p0, p1, _u32(imgui.ImVec4(0.92, 0.92, 0.92, 1)), 1.2)
    if st is not None and st.u is not None and st.target is not None:
        dl.add_circle_filled(imgui.ImVec2(x0 + s * st.u, y0 + s * (1 - st.target)), 3.0,
                             _u32(ui.RED))
    imgui.dummy(imgui.ImVec2(s, s))
    if imgui.is_item_hovered():
        imgui.set_tooltip("Hand position across the calibrated range (→) against what "
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
            imgui.set_tooltip("For the next 20 s, move each hand through everything it "
                              "should reach. Each axis's range becomes what you covered "
                              "(2nd–98th percentile), saved to hands.json for this box.")
        imgui.same_line()
        if imgui.small_button("reset ranges"):
            io.reset_ranges()
    st, a = io.state[k], settings.axes[k]
    imgui.text_disabled(f"{a.name}: {st.lo:.1f} … {st.hi:.1f} {FEATURES[a.feature][0]}")
    if io.cal_note:
        imgui.text_disabled(io.cal_note)
