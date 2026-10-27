"""Band / EQ editor — the bands drawn over the live spectrogram (plan 07 WP5b).

The ANALYZER page's band section. An implot heat map of the analyzer's
spectrum history (analyzer.history(): the last HIST_S seconds, time
across, log frequency up, magnitude in dB as a black → white → red
ramp) with every band laid over it as a translucent horizontal band
between its edges and its weighting curve (band_curve) profiled along
the right edge — so a band's frequency extent reads against the signal
it listens to. The selected band is red with three drag handles: the
centre moves f, either edge lands where it is dragged and the other
stays (f and q both change, `drag_edge`); a left-drag box on the map
sets the selected band's f/q from its frequency extent (`fit_box`, the
time extent is ignored); a plain click selects the narrowest band under
it. Every write goes through the registry (band.{i}.f / .q), so it is
what a preset saves, what MIDI can learn, and ghosted (the base is the
handle, a red hairline marks the effective centre) while a lane rides it.

Cost: the history is 240 × 256 and implot's heat map is a quad per cell,
which was 3 ms and 246 k vertices a frame headless — too much for a 320
px plot whose cells would be a pixel. The map is max-pooled 2 × 2 to
120 × 128 (peaks survive, 0.8 ms, 62 k vertices); the plot geometry is
the pre-pool axis, so nothing else knows. The colormap is registered
with implot once, by name, and survives a hot reload.

Below the map: add / remove / move / select, then the selected band's
strip — transfer, curve and the ten faders in two columns, the same
band.sel.* aliases the shell drew. The pure geometry (fit_box,
drag_edge, clamp_fq) has no imgui in it and is tested directly.
"""

from __future__ import annotations

import math

import numpy as np
from imgui_bundle import imgui, implot

from . import ui
from .analyzer import F_HI, F_LO, HIST_S, Q_HI, Q_LO, centre_q, edges
from .bands import SHAPERS
from .params import Kind, Registry

PLOT_H = 136           # px; the page has to fit the control window with the meters and the strip
FN_W = 84              # px; the strip's shaper and curve combos
POOL = 2               # the heat map is max-pooled this much in both axes
PROFILE_W = 0.16       # the weighting curves' width along the right edge, of the plot
DB_LO, DB_HI = -90.0, -20.0   # the colour ramp's ends (u = 0 is −80 dB, u = 1 is −24)
CLICK_PX = 3.0         # a drag shorter than this is a click
MIN_OCT = 0.02         # a box (or an edge drag) narrower than this many octaves is a click
CMAP = "hyperspace"
# black ground through grey to white, red only for the top eighth — the
# peak zone, as the meters read it — so the map stays monochrome under
# the red of the selected band; implot spaces the stops evenly
RAMP = np.array([
    (0.0, 0.0, 0.0, 1.0), (0.10, 0.10, 0.10, 1.0), (0.24, 0.24, 0.24, 1.0),
    (0.42, 0.42, 0.42, 1.0), (0.62, 0.62, 0.62, 1.0), (0.82, 0.82, 0.82, 1.0),
    (0.96, 0.96, 0.96, 1.0), (1.0, 43 / 255, 43 / 255, 1.0),
], dtype=np.float32)
TICKS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
HINT = "BOX FITS  ·  LINES MOVE  ·  CLICK SELECTS"


# ------------------------------------------------------- pure geometry

def clamp_fq(f: float, q: float) -> tuple[float, float]:
    """Into the registry's ranges — what set_value would do, said up front."""
    return (min(max(f, F_LO), F_HI), min(max(q, Q_LO), Q_HI))


def fit_box(f0: float, f1: float) -> tuple[float, float]:
    """The (f, q) whose edges are the box's frequency extent, either order.
    A box narrower than MIN_OCT octaves is treated as a line: q pins at
    Q_HI. The result is clamped, so a box wider than Q_LO allows (about
    ten octaves) lands a band narrower than the box."""
    lo, hi = sorted((max(f0, 1e-3), max(f1, 1e-3)))
    if math.log2(hi / lo) < MIN_OCT:
        return clamp_fq(math.sqrt(lo * hi), Q_HI)
    return clamp_fq(*centre_q(lo, hi))


def drag_edge(lo: float, hi: float, which: str, f_new: float) -> tuple[float, float]:
    """One edge dragged to f_new, the other staying: the new (f, q).
    `which` is "lo" or "hi". An edge can't cross the other (MIN_OCT
    apart at least), so dragging through it just narrows the band."""
    if which == "lo":
        lo = min(f_new, hi / 2 ** MIN_OCT)
    else:
        hi = max(f_new, lo * 2 ** MIN_OCT)
    return clamp_fq(*centre_q(max(lo, 1e-3), max(hi, 1e-3)))


def apply_fq(reg: Registry, i: int, f: float | None = None, q: float | None = None) -> None:
    """Write a band's centre and/or Q through the registry (base while
    modulated, clamped by the params themselves)."""
    if f is not None:
        reg[f"band.{i}.f"].set_value(f)
    if q is not None:
        reg[f"band.{i}.q"].set_value(q)


def pooled(spec: np.ndarray, k: int = POOL) -> np.ndarray:
    """Max-pool a [T, F] history k × k, and turn it the way the heat map
    reads: rows are frequency, top row highest; columns are time."""
    T, F = spec.shape
    t, f = T // k, F // k
    m = spec[: t * k, : f * k].reshape(t, k, f, k).max(axis=(1, 3))
    return np.ascontiguousarray(m.T[::-1], dtype=np.float32)


def band_under(specs: list[tuple[float, float]], f: float) -> int | None:
    """Index of the narrowest (lo, hi) that contains f, or None."""
    hits = [(math.log2(hi / lo), i) for i, (lo, hi) in enumerate(specs) if lo <= f <= hi]
    return min(hits)[1] if hits else None


# ---------------------------------------------------------- imgui state

def _state(panel) -> dict:
    st = getattr(panel, "_bands_state", None)
    if st is None:
        st = panel._bands_state = {"box": None, "cmap": -1}
    return st


def ensure_context() -> None:
    """implot's context, made on first use — the app never has to know
    the panel plots (and the headless harness gets one the same way)."""
    if implot.get_current_context() is None:
        implot.create_context()


def _colormap(st: dict) -> int:
    if st["cmap"] < 0:
        st["cmap"] = implot.get_colormap_index(CMAP)
        if st["cmap"] < 0:
            st["cmap"] = implot.add_colormap(CMAP, RAMP, False)
    return st["cmap"]


def _base_fq(reg: Registry, i: int) -> tuple[float, float]:
    """A band's setting (the base while modulated) — where its handles sit."""
    return float(reg[f"band.{i}.f"].base), float(reg[f"band.{i}.q"].base)


# ------------------------------------------------------------- drawing

def section(panel, dt: float) -> None:
    """The band section's body under the meters: editor, band row, strip."""
    ensure_context()
    editor(panel)
    band_row(panel)
    imgui.separator()
    strip(panel)


def editor(panel) -> None:
    """The spectrogram with the bands over it and the selected one's handles."""
    st, c = _state(panel), panel.control
    chain = panel.audio.chain
    n, sel = chain.n, c.selb
    spec, freqs = chain.history()
    ly = np.log2(freqs)
    h = float(ly[1] - ly[0])                       # the log bin's height
    ylo, yhi = float(ly[0]) - h / 2, float(ly[-1]) + h / 2
    m = pooled(spec)

    grey = ui.LINE
    implot.push_style_color(implot.Col_.plot_bg, ui.u32(imgui.ImVec4(0, 0, 0, 1)))
    implot.push_style_color(implot.Col_.frame_bg, ui.u32(imgui.ImVec4(0, 0, 0, 0)))
    implot.push_style_color(implot.Col_.plot_border, ui.u32(grey))
    implot.push_style_color(implot.Col_.axis_text, ui.u32(ui.DIM))
    implot.push_style_color(implot.Col_.axis_tick, ui.u32(grey))
    implot.push_style_var(implot.StyleVar_.plot_padding, imgui.ImVec2(0, 0))
    implot.push_style_var(implot.StyleVar_.plot_border_size, 1)
    flags = (implot.Flags_.no_title | implot.Flags_.no_legend | implot.Flags_.no_menus
             | implot.Flags_.no_box_select | implot.Flags_.no_mouse_text)
    axis = (implot.AxisFlags_.lock | implot.AxisFlags_.no_grid_lines
            | implot.AxisFlags_.no_tick_marks | implot.AxisFlags_.no_highlight)
    imgui.push_font(ui._FONTS["micro"], ui.FONT_MICRO)
    opened = implot.begin_plot("##spectrogram", imgui.ImVec2(-1, PLOT_H), flags)
    if opened:
        implot.setup_axes("", "", axis | implot.AxisFlags_.no_tick_labels, axis)
        implot.setup_axes_limits(-HIST_S, 0.0, ylo, yhi, imgui.Cond_.always)
        ticks = [t for t in TICKS if ylo <= math.log2(t) <= yhi]
        implot.setup_axis_ticks(
            implot.ImAxis_.y1, [math.log2(t) for t in ticks],
            [f"{t}" if t < 1000 else f"{t // 1000}k" for t in ticks],
        )
        implot.push_colormap(_colormap(st))
        implot.plot_heatmap("##spec", m, DB_LO, DB_HI, "",
                            implot.Point(-HIST_S, ylo), implot.Point(0.0, yhi))
        implot.pop_colormap()
        _overlays(panel, freqs, ly)
        handle_busy = _handles(panel, sel)
        _box(panel, handle_busy, n, sel)
        implot.end_plot()
    imgui.pop_font()
    implot.pop_style_var(2)
    implot.pop_style_color(5)


def _overlays(panel, freqs: np.ndarray, ly: np.ndarray) -> None:
    """Every band: a translucent horizontal band between its edges and its
    weighting curve profiled along the right edge; the selected one red."""
    reg, c = panel.reg, panel.control
    chain = panel.audio.chain
    dl = implot.get_plot_draw_list()
    pos, size = implot.get_plot_pos(), implot.get_plot_size()
    x0, x1 = pos.x, pos.x + size.x
    pw = size.x * PROFILE_W
    # the y axis is linear in log2 f: one pixel map for everything below,
    # rather than a plot_to_pixels call per point
    yb = implot.plot_to_pixels(implot.Point(0.0, float(ly[0]))).y
    ys = (implot.plot_to_pixels(implot.Point(0.0, float(ly[-1]))).y - yb) / float(ly[-1] - ly[0])
    lb = float(ly[0])
    py = lambda y: yb + (y - lb) * ys                        # log2 f → pixel row
    ypx = yb + (ly - lb) * ys
    implot.push_plot_clip_rect()
    # the affordance, in the top-left corner on a dark backing (the names
    # below keep clear of it)
    tw = imgui.calc_text_size(HINT).x
    dl.add_rect_filled(imgui.ImVec2(x0 + 1, pos.y + 1),
                       imgui.ImVec2(x0 + tw + 7, pos.y + ui.FONT_MICRO + 5),
                       ui.u32(imgui.ImVec4(0, 0, 0, 0.7)))
    dl.add_text(imgui.ImVec2(x0 + 4, pos.y + 2), ui.u32(ui.DIM), HINT)
    order = sorted(range(chain.n), key=lambda i: i == c.selb)   # the selected on top
    for i in order:
        sel = i == c.selb
        f, q = _base_fq(reg, i)
        lo, hi = edges(f, q)
        y_hi, y_lo = py(math.log2(hi)), py(math.log2(lo))
        tone = ui.RED if sel else imgui.ImVec4(1, 1, 1, 1)
        fill = ui.u32(imgui.ImVec4(tone.x, tone.y, tone.z, 0.16 if sel else 0.07))
        line = ui.u32(imgui.ImVec4(tone.x, tone.y, tone.z, 0.9 if sel else 0.3))
        dl.add_rect_filled(imgui.ImVec2(x0, y_hi), imgui.ImVec2(x1, y_lo), fill)
        if not sel:                                # the selected band's edges are its handles
            dl.add_line(imgui.ImVec2(x0, y_hi), imgui.ImVec2(x1, y_hi), line)
            dl.add_line(imgui.ImVec2(x0, y_lo), imgui.ImVec2(x1, y_lo), line)
        # the curve: weight 1 reaches PROFILE_W into the plot from the right
        # (every other bin: 128 points is a pixel apart on this plot)
        w = chain.band_curve(i, freqs, f, q)
        on = np.nonzero(w > 1e-3)[0]
        if len(on):
            a, b = int(on[0]), int(on[-1]) + 1
            ks = list(range(a, b, 2)) + ([b - 1] if (b - 1 - a) % 2 else [])
            xs, yy = x1 - pw * w[ks], ypx[ks]
            pts = [imgui.ImVec2(x1, float(ypx[a]))]
            pts += [imgui.ImVec2(float(x), float(y)) for x, y in zip(xs, yy)]
            pts.append(imgui.ImVec2(x1, float(ypx[b - 1])))
            dl.add_concave_poly_filled(
                pts, ui.u32(imgui.ImVec4(tone.x, tone.y, tone.z, 0.45 if sel else 0.22)))
            dl.add_polyline(pts, line, 1.0, 0)
        # the name at the centre, inside the left edge
        yc = min(max(py(math.log2(f)), pos.y + ui.FONT_MICRO * 1.5 + 6),
                 pos.y + size.y - ui.FONT_MICRO / 2 - 3)
        dl.add_text(imgui.ImVec2(x0 + 4, yc - ui.FONT_MICRO / 2 - 1),
                    ui.u32(ui.RED if sel else ui.DIM), chain.band_names[i].upper())
        # a modulated centre: the effective value as a red hairline ghost
        pf = reg[f"band.{i}.f"]
        if pf.modulated:
            yg = py(math.log2(max(pf.value, 1e-3)))
            dl.add_line(imgui.ImVec2(x0, yg), imgui.ImVec2(x1, yg), ui.u32(ui.RED), 1.0)
            panel.ghosts += 1
    implot.pop_plot_clip_rect()


def _handles(panel, sel: int) -> bool:
    """The selected band's three drag lines; returns True while any of them
    is hovered or held, so the box gesture stays out of their way."""
    reg = panel.reg
    f, q = _base_fq(reg, sel)
    lo, hi = edges(f, q)
    busy = False
    thin = imgui.ImVec4(1.0, 43 / 255, 43 / 255, 0.9)
    changed, y, _, hov, held = implot.drag_line_y(
        0, math.log2(f), ui.RED, 2.0, implot.DragToolFlags_.no_fit, True, True, True)
    busy |= bool(hov or held)
    if changed:
        apply_fq(reg, sel, f=2.0 ** y)
    for k, (which, fe) in enumerate((("lo", lo), ("hi", hi)), start=1):
        changed, y, _, hov, held = implot.drag_line_y(
            k, math.log2(fe), thin, 1.0, implot.DragToolFlags_.no_fit, True, True, True)
        busy |= bool(hov or held)
        if changed:
            apply_fq(reg, sel, *drag_edge(lo, hi, which, 2.0 ** y))
    if busy:
        imgui.set_mouse_cursor(imgui.MouseCursor_.resize_ns)
    return busy


def _box(panel, handle_busy: bool, n: int, sel: int) -> None:
    """Left-drag a rectangle: the selected band's f/q from its height;
    a click (no drag) selects the band under the cursor."""
    st, reg = _state(panel), panel.reg
    io = imgui.get_io()
    lim = implot.get_plot_limits()
    mouse = implot.get_plot_mouse_pos()
    if st["box"] is None:
        if implot.is_plot_hovered() and not handle_busy and imgui.is_mouse_clicked(0):
            st["box"] = (mouse.x, mouse.y, io.mouse_pos.x, io.mouse_pos.y)
        return
    bx, by, px, py = st["box"]
    x = min(max(mouse.x, lim.x.min), lim.x.max)
    y = min(max(mouse.y, lim.y.min), lim.y.max)
    if imgui.is_mouse_down(0):
        dl = implot.get_plot_draw_list()
        p0 = implot.plot_to_pixels(implot.Point(bx, by))
        p1 = implot.plot_to_pixels(implot.Point(x, y))
        implot.push_plot_clip_rect()
        dl.add_rect_filled(p0, p1, ui.u32(imgui.ImVec4(1, 1, 1, 0.08)))
        dl.add_rect(p0, p1, ui.u32(imgui.ImVec4(1.0, 43 / 255, 43 / 255, 0.8)))
        implot.pop_plot_clip_rect()
        return
    st["box"] = None
    moved = math.hypot(io.mouse_pos.x - px, io.mouse_pos.y - py)
    if moved < CLICK_PX or abs(y - by) < MIN_OCT:   # a click, or a drag along time only
        hit = band_under([edges(*_base_fq(reg, i)) for i in range(n)], 2.0 ** by)
        if hit is not None:
            reg["band.select"].set(hit)
    else:                                            # the box's height is the band
        apply_fq(reg, sel, *fit_box(2.0 ** by, 2.0 ** y))


def band_row(panel) -> None:
    """add · remove · ◀ ▶ (strip order) · the band combo · reset."""
    c, chain = panel.control, panel.audio.chain
    panel._button("band.add", "+", small=True)
    imgui.same_line()
    imgui.begin_disabled(chain.n <= 1)
    panel._button("band.remove", "−", small=True)
    imgui.end_disabled()
    imgui.same_line(0, 10)
    imgui.begin_disabled(c.selb == 0)
    if imgui.arrow_button("##movel", imgui.Dir.left):
        c.move_band(c.selb, c.selb - 1)
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        ui.tooltip("Move the band one strip earlier (lanes follow the strip order)")
    imgui.same_line(0, 2)
    imgui.begin_disabled(c.selb >= chain.n - 1)
    if imgui.arrow_button("##mover", imgui.Dir.right):
        c.move_band(c.selb, c.selb + 1)
    imgui.end_disabled()
    if imgui.is_item_hovered(imgui.HoveredFlags_.allow_when_disabled):
        ui.tooltip("Move the band one strip later")
    imgui.same_line(0, 10)
    panel._combo("band.select", 120)
    imgui.same_line(imgui.get_content_region_avail().x - ui.chip_w("Reset"))
    panel._button("band.reset", "Reset", small=True)


def _norm_chip(panel) -> None:
    """AUTO / MANUAL normalisation for the open band (audit A10): lit red on
    MANUAL, where the trim is a plain gain."""
    a = panel.reg["band.sel.norm"]
    p = panel._real(a)
    manual = bool(p.base)
    w = imgui.ImVec2(ui.chip_w("MANUAL"), 0)   # one width: the combos never jump
    if ui.lit_chip(f"{'MANUAL' if manual else 'AUTO'}##norm", manual, size=w):
        p.set(0 if manual else 1)
    panel._tip(a)
    panel._ctx(a)
    panel._learn_frame(a)


def strip(panel) -> None:
    """The selected band's strip — the band.sel.* aliases follow the selection."""
    c, a, r = panel.control, panel.audio, panel.reg
    P = a.chain.params[c.selb]
    lo, hi = edges(*_base_fq(r, c.selb))
    imgui.text_colored(ui.RED, f"{a.chain.band_names[c.selb]} · {SHAPERS[P.fn].tag}")
    imgui.same_line()
    imgui.text_disabled(f"{lo:.0f}–{hi:.0f} Hz")
    sp = imgui.get_style().item_spacing.x
    imgui.same_line(imgui.get_content_region_avail().x - 2 * FN_W - 2 * sp
                    - ui.chip_w("MANUAL"))
    _norm_chip(panel)
    imgui.same_line()
    panel._combo("band.sel.fn", FN_W, SHAPERS[P.fn].name)
    imgui.same_line()
    panel._combo("band.sel.curve", FN_W)
    # the ten faders (f, q, the eight knobs) in two columns so the page fits
    if imgui.begin_table("##bandstrip", 2, imgui.TableFlags_.sizing_stretch_same):
        for p in r.group("band"):
            if p.id.startswith("band.sel.") and p.kind is Kind.CONTINUOUS:
                imgui.table_next_column()
                panel._fader(p.id)
        imgui.end_table()
