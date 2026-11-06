"""Draw helpers that put CSS box semantics onto an ImDrawList.

The one that matters is `border`. CSS paints a border *inside* the box
(border-box): a 1px border on a box at x covers exactly pixel column x.
ImGui's add_rect strokes *centred on the path*, so the same call straddles the
edge and antialiases into two half-covered columns. Every helper here works in
CSS box coordinates (x, y, w, h) and does the half-pixel inset itself.

Pure functions of (draw list, rect, tokens) — no widget state, so they can be
reasoned about and diffed one at a time.
"""

from __future__ import annotations

import math

from imgui_bundle import imgui

from tokens import RADII, RING_W, SELECT_SIZES, rgba


def _u32(col) -> int:
    return imgui.get_color_u32(imgui.ImVec4(*col))


def css_radius(r: float, w: float, h: float) -> float:
    """CSS clamps a corner radius when adjacent radii exceed the side.

    For a uniform radius that reduces to min(r, min(w, h) / 2) — which is also
    what ImGui clamps to internally, so the two agree. Kept explicit because
    the kit needs the clamped value to inset strokes correctly.
    """
    return min(r, min(w, h) / 2.0)


def fill(dl, x, y, w, h, col, radius=0.0) -> None:
    """A filled rounded rect covering exactly [x, x+w) x [y, y+h)."""
    if col[3] <= 0.0:
        return
    dl.add_rect_filled(
        imgui.ImVec2(x, y), imgui.ImVec2(x + w, y + h), _u32(col),
        css_radius(radius, w, h),
    )


def border(dl, x, y, w, h, col, radius=0.0, width=1.0) -> None:
    """A CSS border: `width` px drawn INSIDE the box edge.

    Calibrated against tools/dkit/probe_stroke.py, not against an assumption.
    An add_rect stroke of thickness 1 is NOT centred on the path: the top/left
    edges cover [p_min, p_min + 1] and the bottom/right cover [p_max - 1, p_max].
    So the stroke already falls wholly INSIDE the rect bounds, which is exactly
    CSS border-box — and the right inset is none at all.
    """
    if col[3] <= 0.0 or width <= 0.0:
        return
    # imgui_bundle orders this (rounding, thickness, flags) — not the C++
    # (rounding, flags, thickness). Keyword args so it cannot silently swap.
    dl.add_rect(
        imgui.ImVec2(x, y), imgui.ImVec2(x + w, y + h), _u32(col),
        rounding=css_radius(radius, w, h), thickness=width,
    )


def snap(x, y, w, h):
    """Round a rect's edges to whole pixels, the way Chromium paints one.

    Chromium lays out on a 1/64 px grid but PIXEL-SNAPS a box decoration's
    painted edges to whole device pixels. ImGui antialiases them instead -
    which is the more faithful rendering of the stated geometry, and the
    wrong answer if the bar is "match the browser".

    Measured twice, on the two shapes that have fractional edges:

    * the Switch is `h-[18.4px]`, so its box runs y 790 .. 808.390625. The
      background is painted into rows 790..807 and row 808 is left
      completely empty. Unsnapped that was 91 levels on a dark switch - the
      largest single disagreement the diff has ever reported.
    * a Slider thumb at 33.3% lands at x 102.604 .. 114.604. The browser
      paints it at 103 .. 115 - snapped at both edges, width preserved at
      12 - and puts no ink at all in column 102, where ImGui put 133.

    This matters well beyond the gallery: 292 of the registry's 427 params
    are continuous, so a thumb sits on a fraction almost always. Layout keeps
    the fraction (box.slider_geom and box.switch_geom are exact, and the
    thumb's placement depends on it); only paint snaps.

    Round, not floor: 808.390625 -> 808 and 102.604 -> 103, which is what
    matching edge positions rather than extents requires.

    Round, not floor: 808.390625 -> 808 and 807.6 -> 808, which is what
    matching edge positions rather than extents requires.
    """
    x0, y0 = round(x), round(y)
    return float(x0), float(y0), float(round(x + w) - x0), float(round(y + h) - y0)


def box(dl, x, y, w, h, *, fill_col=None, border_col=None, radius=0.0,
        border_w=1.0) -> None:
    """Fill then border, the order a browser paints them."""
    if fill_col is not None:
        fill(dl, x, y, w, h, fill_col, radius)
    if border_col is not None:
        border(dl, x, y, w, h, border_col, radius, border_w)


# A CSS blur radius is 2 sigma. Stacking rounded rects at integer expansions
# with these weights reproduces 1 - Phi(d / sigma), the coverage of a blurred
# straight edge, to within a level at the alphas shadcn uses.
def _blur_layers(sigma: float, reach: int = 3):
    from math import erf, sqrt
    phi = lambda z: 0.5 * (1.0 + erf(z / sqrt(2.0)))
    cum = {e: 1.0 - phi((e + 0.5) / sigma) for e in range(-1, reach + 1)}
    out = []
    for e in range(reach, -2, -1):
        inner = cum.get(e - 1, 1.0)
        out.append((float(e), inner - cum[e]))
    return [(e, w) for e, w in out if w > 0.001]


def shadow(dl, x, y, w, h, col, radius, dx=0.0, dy=0.0, blur=0.0, spread=0.0) -> None:
    """A CSS box-shadow, as stacked rounded rects.

    ImGui has no shadow primitive and NanoVG (which does, via box_gradient) is
    off headless with no fallback, so it cannot back the diff harness. For the
    shadows shadcn actually uses - 2px blur at 5% - stacking is within a level.
    """
    if col[3] <= 0.0:
        return
    sigma = max(blur, 0.01) / 2.0
    for e, wgt in _blur_layers(sigma):
        a = col[3] * wgt
        if a < 0.002:
            continue
        ex = e + spread
        fill(dl, x + dx - ex, y + dy - ex, w + 2 * ex, h + 2 * ex,
             (col[0], col[1], col[2], a), radius + ex)


def card(dl, cell, theme, grad_tex: int | None) -> None:
    """One shadcn Card: shadow, background, gradient, then the ring.

    The ring (`ring-1 ring-foreground/10`) is a box-shadow, so it sits wholly
    OUTSIDE the border box - measured at rows y-1 and y+h in the oracle.
    """
    x, y, w, h = cell["x"], cell["y"], cell["w"], cell["h"]
    r = RADII["xl"]                                   # rounded-xl = 14
    grad = cell["variant"] == "gradient"

    if grad:                                          # shadow-xs: 0 1px 2px #0000000d
        shadow(dl, x, y, w, h, (0.0, 0.0, 0.0, 0.05), r, dy=1.0, blur=2.0)

    fill(dl, x, y, w, h, rgba("card", theme=theme), r)

    if grad and grad_tex is not None:
        dl.add_image_rounded(
            imgui.ImTextureRef(grad_tex),
            imgui.ImVec2(x, y), imgui.ImVec2(x + w, y + h),
            imgui.ImVec2(0, 0), imgui.ImVec2(1, 1),
            imgui.get_color_u32(imgui.ImVec4(1, 1, 1, 1)),
            css_radius(r, w, h),
        )

    border(dl, x - 1, y - 1, w + 2, h + 2,
           rgba("foreground", 0.10, theme=theme), r + 1, 1.0)


# (hhea.ascender - hhea.descender) / unitsPerEm, per face. Geist: 1300/1000.
FONT_SPAN_EM = {"regular": 1.30, "medium": 1.30, "semibold": 1.30}


# The six faces build_fonts.py produces: three weights, each with and
# without Geist's tabular figures frozen into the cmap.
FACE_FILES = [(f"{v}{t}", f"Geist-{w}{t}.ttf")
              for v, w in (("regular", "Regular"), ("medium", "Medium"),
                           ("semibold", "SemiBold"))
              for t in ("", "-tnum")]


# The panel merges DejaVu behind every face for the symbols its own faces do
# not carry (ui.py:152-153). The kit needs the same: Geist's latin subset has
# no arrows and no command key, and a missing glyph draws as a box.
FALLBACK = "../../hyperspace/fonts/DejaVuSans.ttf"


def load_faces(io, here, density: float = 1.0) -> dict:
    """Every face, each with the symbol fallback merged in behind it."""
    out = {}
    fb = (here / FALLBACK).resolve()
    for key, fn in FACE_FILES:
        cfg = imgui.ImFontConfig()
        cfg.rasterizer_density = density
        out[key] = io.fonts.add_font_from_file_ttf(str(here / "fonts" / fn),
                                                   16.0, cfg)
        if fb.exists():
            m = imgui.ImFontConfig()
            m.merge_mode = True
            m.rasterizer_density = density
            io.fonts.add_font_from_file_ttf(str(fb), 16.0, m)
    return out


def face_key(variant: str, tabular: bool) -> str:
    """The face to use. `-tnum` carries Geist's tabular figures, frozen into
    the cmap at build time because stb_truetype applies no OpenType feature.
    Numbers that change in place — a readout, a table column — want it; words
    do not, exactly as shadcn turns `tabular-nums` on selectively."""
    return f"{variant}-tnum" if tabular else variant


def text_cell(dl, cell, faces, col) -> None:
    """One pinned string, vertically centred in its box like CSS line-height.

    ImGui 1.92 renders any face at any size through push_font(face, size), so
    the size comes from the spec rather than from a baked atlas entry.
    """
    # the oracle sets font-variant-numeric: tabular-nums on every text cell,
    # so the kit must use the frozen faces to compare like with like
    face = faces.get(face_key(cell["variant"], True)) or faces.get(cell["variant"])
    # ImGui's font size is NOT a CSS px. stb_truetype scales so that
    # ascent - descent equals the requested size; CSS maps the em square to
    # font-size. Geist is upem 1000 with ascent 1005 / descent -295, so its
    # span is 1.30 em and ImGui renders 14px CSS text at 77% unless asked for
    # 14 * 1.30. Per-face, because the ratio is a property of the font.
    size = float(cell["size"]) * FONT_SPAN_EM.get(cell["variant"], 1.0)
    imgui.push_font(face, size)
    try:
        ext = imgui.calc_text_size(cell["text"])
        # CSS centres the line box, so the glyph box sits at (h - lineheight)/2;
        # ImGui's text origin is the top of its own line, which is `size`-based.
        ty = cell["y"] + (cell["h"] - ext.y) / 2.0
        dl.add_text(imgui.ImVec2(cell["x"], ty), _u32(col), cell["text"])
    finally:
        imgui.pop_font()


def badge(dl, cell, theme, variant_table) -> None:
    """One shadcn Badge, pinned to the spec rect."""
    v = variant_table[cell["variant"]]
    box(
        dl, cell["x"], cell["y"], cell["w"], cell["h"],
        fill_col=rgba(*v["fill"], theme=theme),
        border_col=rgba(*v["border"], theme=theme),
        radius=RADII["4xl"],
        border_w=1.0,
    )


# --------------------------------------------------------------------------
# text
# --------------------------------------------------------------------------

def push_css_font(faces, variant: str, css_px: float, tabular: bool = False):
    """Push a face at a size that means what CSS means by it.

    See FONT_SPAN_EM: stb_truetype sizes by ascent-descent, CSS by the em.
    """
    key = face_key(variant, tabular)
    face = faces.get(key) or faces.get(variant)
    imgui.push_font(face, css_px * FONT_SPAN_EM.get(variant, 1.0))


def fit_text(s, faces, variant, size, max_w, tabular=False) -> str:
    """The longest prefix of `s` that fits in max_w, with an ellipsis.

    shadcn leans on `truncate` / `line-clamp-1`; ImGui clips nothing by
    itself. Same binary search ui.py:317-329 uses."""
    if max_w <= 0 or text_w(s, faces, variant, size, tabular) <= max_w:
        return s
    lo, hi = 0, len(s)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if text_w(s[:mid] + "\u2026", faces, variant, size, tabular) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return s[:lo] + "\u2026"


def label(dl, x, y, s, faces, variant, size, col, *, align="left", box_w=0.0,
          baseline_box=0.0, max_w=0.0, tabular=False):
    """Draw `s` at (x, y). With baseline_box, centre it vertically in that
    height the way a CSS line box would; with align/box_w, align horizontally.
    Returns the advance width."""
    if max_w:
        s = fit_text(s, faces, variant, size, max_w, tabular)
    push_css_font(faces, variant, size, tabular)
    try:
        ext = imgui.calc_text_size(s)
        tx = x
        if align == "right":
            tx = x + box_w - ext.x
        elif align == "center":
            tx = x + (box_w - ext.x) / 2.0
        ty = y + (baseline_box - ext.y) / 2.0 if baseline_box else y
        dl.add_text(imgui.ImVec2(round(tx), round(ty)), _u32(col), s)
        return float(ext.x)
    finally:
        imgui.pop_font()


def text_w(s, faces, variant, size, tabular=False) -> float:
    push_css_font(faces, variant, size, tabular)
    try:
        return float(imgui.calc_text_size(s).x)
    finally:
        imgui.pop_font()


# --------------------------------------------------------------------------
# widgets
# --------------------------------------------------------------------------

def button(dl, x, y, w, h, s, faces, theme, *, variant="outline", state="rest"):
    """shadcn Button. `state` is rest | hover | active, which in an immediate
    mode UI is read back off the stock widget - see FINDINGS on the sandwich."""
    r = RADII["md"]                                   # rounded-md = 8
    if variant == "default":
        base, ink = "primary", "primary-foreground"
        bg = rgba(base, 0.90 if state != "rest" else 1.0, theme=theme)
        box(dl, x, y, w, h, fill_col=bg, radius=r)
    elif variant == "outline":
        bg = rgba("accent", 1.0, theme=theme) if state != "rest" else rgba("transparent", theme=theme)
        box(dl, x, y, w, h, fill_col=bg,
            border_col=rgba("border", theme=theme), radius=r)
        ink = "foreground"
    else:                                             # ghost
        bg = rgba("accent", 1.0, theme=theme) if state != "rest" else rgba("transparent", theme=theme)
        box(dl, x, y, w, h, fill_col=bg, radius=r)
        ink = "foreground"
    label(dl, x, y, s, faces, "medium", 14, rgba(ink, theme=theme),
          align="center", box_w=w, baseline_box=h)


def tabs(dl, x, y, h, items, active, faces, theme, *, pad=3.0, gap=0.0):
    """shadcn Tabs: a muted track, the active trigger raised on a card fill.
    Returns the list of per-item rects so a caller can hit-test them."""
    ih = h - 2 * pad
    widths = [text_w(s, faces, "medium", 14) + 20 for s in items]
    total = sum(widths) + gap * (len(items) - 1) + 2 * pad
    fill(dl, x, y, total, h, rgba("muted", theme=theme), RADII["lg"])
    rects, cx = [], x + pad
    for i, (s, w) in enumerate(zip(items, widths)):
        if i == active:
            # the raised trigger carries shadow-sm in shadcn
            shadow(dl, cx, y + pad, w, ih, (0, 0, 0, 0.10), RADII["md"],
                   dy=1.0, blur=3.0)
            fill(dl, cx, y + pad, w, ih, rgba("card", theme=theme), RADII["md"])
        ink = "foreground" if i == active else "muted-foreground"
        label(dl, cx, y + pad, s, faces, "medium", 14, rgba(ink, theme=theme),
              align="center", box_w=w, baseline_box=ih)
        rects.append((cx, y + pad, w, ih))
        cx += w + gap
    return rects, total


def sidebar_item(dl, x, y, w, h, s, faces, theme, *, active=False, icon=None):
    """A sidebar menu button: rounded-md, accent fill when active."""
    if active:
        fill(dl, x, y, w, h, rgba("accent", theme=theme), RADII["md"])
    ink = rgba("foreground" if active else "muted-foreground", theme=theme)
    tx = x + 10
    if icon is not None:
        icon(dl, x + 10, y + h / 2.0, ink)
        tx = x + 32
    label(dl, tx, y, s, faces, "medium", 14, ink, baseline_box=h)


def meter(dl, x, y, w, h, frac, theme, *, track="muted", bar="primary"):
    """The plane-routing bar: a full-round track with a filled lead."""
    r = h / 2.0
    fill(dl, x, y, w, h, rgba(track, theme=theme), r)
    fw = max(0.0, min(1.0, frac)) * w
    if fw > 1.0:
        fill(dl, x, y, fw, h, rgba(bar, theme=theme), r)


def sparkline(dl, x, y, w, h, values, col, *, lo=0.0, hi=1.0, fill_a=0.18):
    """A filled area chart. Two polylines rather than a tessellated mesh: the
    fill is a concave polygon, so it goes through add_concave_poly_filled -
    the same call ui_bands.py:261 already uses for the spectrogram."""
    if len(values) < 2:
        return
    span = max(hi - lo, 1e-6)
    pts = []
    for i, v in enumerate(values):
        px = x + w * i / (len(values) - 1)
        py = y + h * (1.0 - (min(max(v, lo), hi) - lo) / span)
        pts.append(imgui.ImVec2(px, py))
    if fill_a > 0:
        # One convex trapezoid per segment rather than one concave polygon:
        # add_concave_poly_filled triangulates the whole outline and leaves
        # visible streaks across an area chart's interior.
        c = _u32((col[0], col[1], col[2], fill_a))
        base = y + h
        for a, b in zip(pts, pts[1:]):
            dl.add_quad_filled(imgui.ImVec2(a.x, a.y), imgui.ImVec2(b.x, b.y),
                               imgui.ImVec2(b.x, base), imgui.ImVec2(a.x, base), c)
    # imgui_bundle orders this (col, thickness, flags), as with add_rect
    dl.add_polyline(pts, _u32(col), thickness=1.5, flags=0)


def hrule(dl, x, y, w, theme, col="border"):
    fill(dl, x, y, w, 1, rgba(col, theme=theme))



# --------------------------------------------------------------------------
# icons
# --------------------------------------------------------------------------

try:
    from icons import BOX as ICON_BOX, ICONS, STROKE as ICON_STROKE
except ImportError:                       # not built yet
    ICONS, ICON_BOX, ICON_STROKE = {}, 24.0, 2.0


def icon(dl, name, x, y, size, col, *, width=None) -> bool:
    """Stroke a Lucide icon into `size` x `size` at (x, y).

    Vector, so it stays crisp at any size and takes its colour from a token:
    no atlas, no texture, no runtime dependency. Lucide's geometry is stroked
    paths on a 24x24 box with round caps and joins, which is what ImGui's
    path API draws natively.

    Returns False for an unknown name rather than raising, so a missing icon
    degrades to a gap instead of taking the frame down (the panel's draws are
    individually guarded — ARCHITECTURE.md:168 — and a kit should not fight
    that).
    """
    subs = ICONS.get(name.replace("-", "_"))
    if not subs or col[3] <= 0.0:
        return False
    s = size / ICON_BOX
    w = (width if width is not None else ICON_STROKE) * s
    c = _u32(col)
    for ops in subs:
        dl.path_clear()
        closed = False
        first = last = None
        for op in ops:
            k = op[0]
            if k in ("M", "L"):
                dl.path_line_to(imgui.ImVec2(x + op[1] * s, y + op[2] * s))
                last = (op[1], op[2])
            elif k == "C":
                dl.path_bezier_cubic_curve_to(
                    imgui.ImVec2(x + op[1] * s, y + op[2] * s),
                    imgui.ImVec2(x + op[3] * s, y + op[4] * s),
                    imgui.ImVec2(x + op[5] * s, y + op[6] * s))
                last = (op[5], op[6])
            elif k == "Z":
                closed = True
            if first is None and last is not None:
                first = last
        # A path whose last point IS its first point is already closed.
        # Asking ImGui to close it too adds a zero-length segment, which under
        # round joins draws a visible tick - it showed up on every circle.
        if closed and first and last and \
                abs(first[0] - last[0]) < 1e-6 and abs(first[1] - last[1]) < 1e-6:
            closed = False
        # imgui_bundle orders this (col, thickness, flags) - the third time
        # this binding reverses the C++ order; always pass these by keyword
        dl.path_stroke(c, thickness=w,
                       flags=imgui.ImDrawFlags_.closed if closed else 0)
    return True


def icon_centred(dl, name, cx, cy, size, col, **kw) -> bool:
    return icon(dl, name, cx - size / 2.0, cy - size / 2.0, size, col, **kw)


def flow_text(f, s, faces, variant="regular", size=14.0, tabular=False):
    """Add a measured text cell to a box.Flow."""
    return f.text(s, text_w(s, faces, variant, size, tabular), size,
                  variant, size, tabular)


def draw_flow(dl, placed, faces, col):
    """Render the (cell, rect) pairs a box.Flow.place() returned."""
    for cell, r in placed:
        if cell.kind == "icon":
            icon(dl, cell.payload[0], r.x, r.y, r.w, col)
        elif cell.kind == "text":
            s, variant, size, tabular = cell.payload
            label(dl, r.x, r.y, s, faces, variant, size, col,
                  baseline_box=r.h, tabular=tabular)


# --------------------------------------------------------------------------
# rounded clipping  (CSS `overflow: hidden` on a rounded box)
# --------------------------------------------------------------------------
#
# ImGui clips to rectangles only - push_clip_rect takes an AABB and nothing
# else - so a rounded container cannot clip its children the way a browser
# does. This bites immediately: shadcn's slider track is
# `overflow-hidden rounded-full` and its range is a plain rect, so the
# range's ends are shaped entirely by the track's corners. A ScrollArea is
# the same problem one size up.
#
# There is no stencil in a draw list, and nothing can erase what is already
# drawn, so there are exactly two honest techniques:
#
#   1. For an axis-aligned RECT child - which is what `overflow-hidden`
#      actually meets most of the time (a slider range, a progress fill, a
#      selected row inside a rounded card) - round the child's own corners by
#      the container's radius, but only the corners it actually reaches.
#      That is not an approximation of the clip: it IS the clip, exactly,
#      because the intersection of a rect with a rounded rect is a rect whose
#      touched corners carry the container's arc.
#
#   2. For arbitrary content - text, icons, a whole scrolling subtree - clip
#      to the rect with push_clip_rect and then paint the four corner
#      notches back in the colour behind the container. Exact whenever that
#      backdrop is a known flat colour, which inside a panel it is.
#
# `corner_flags` is (1) and `cover_corners` is (2). Both are measured against
# the browser in the gallery rather than taken on trust.

_CF = None


def _corner_flag_table():
    """ImDrawFlags for each corner, resolved once.

    Built lazily: the enum lives on the imgui module, and naming it at import
    time would make this module depend on a context existing.
    """
    global _CF
    if _CF is None:
        f = imgui.ImDrawFlags_
        _CF = {
            "tl": f.round_corners_top_left, "tr": f.round_corners_top_right,
            "bl": f.round_corners_bottom_left, "br": f.round_corners_bottom_right,
            "none": f.round_corners_none,
        }
    return _CF


def corner_flags(cx, cy, cw, ch, bx, by, bw, bh, *, eps: float = 0.5) -> int:
    """Which of a rounded container's corners an axis-aligned child reaches.

    (cx, cy, cw, ch) is the child, (bx, by, bw, bh) the container. A child
    reaches a corner when it touches BOTH of that corner's sides, within
    `eps`. Returns ImDrawFlags to pass as `flags` to a rounded fill, so the
    child is rounded exactly where the container would have clipped it and
    square everywhere else.

    `eps` is half a pixel rather than zero because these rects are computed
    in float CSS space and a range at 100% lands on 239.99999 as readily as
    on 240.
    """
    cf = _corner_flag_table()
    left = cx <= bx + eps
    right = cx + cw >= bx + bw - eps
    top = cy <= by + eps
    bottom = cy + ch >= by + bh - eps
    out = 0
    if left and top:
        out |= cf["tl"]
    if right and top:
        out |= cf["tr"]
    if left and bottom:
        out |= cf["bl"]
    if right and bottom:
        out |= cf["br"]
    return out or cf["none"]


def fill_clipped(dl, x, y, w, h, col, box, radius) -> None:
    """Fill a rect child as a rounded container would have clipped it.

    `box` is (bx, by, bw, bh). The child is rounded by the container's radius
    on the corners it reaches and left square elsewhere - see the note above
    on why that is the clip rather than a stand-in for it.
    """
    if col[3] <= 0.0 or w <= 0 or h <= 0:
        return
    bx, by, bw, bh = box
    r = css_radius(radius, bw, bh)
    flags = corner_flags(x, y, w, h, bx, by, bw, bh)
    # ImGui clamps rounding to min(w, h) / 2 of the rect it is drawing, not of
    # the container, so a child narrower than the container's diameter would
    # otherwise lose the arc it is supposed to inherit. Nothing can be done
    # about that through add_rect_filled, and at the sizes that matter (a
    # slider range a pixel or two wide) the difference is sub-pixel - but say
    # so rather than pretend the clamp is not there.
    dl.add_rect_filled(imgui.ImVec2(x, y), imgui.ImVec2(x + w, y + h),
                       _u32(col), r, flags)


def cover_corners(dl, x, y, w, h, radius, backdrop, *, seg: int = 0) -> None:
    """Paint back the four corner notches of a rounded box.

    The companion to push_clip_rect for content that is NOT a rect - text,
    icons, a whole scrolling subtree. Draw the content clipped to the box,
    then call this: it fills, in the colour BEHIND the box, the area inside
    the bounding rect but outside the rounded rect. Exact whenever that
    backdrop is a known flat colour, which inside a panel it is.

    One notch is a square of side r with a quarter disc taken out of it, so
    the region is CONCAVE - the arc bulges into it. It goes up as an explicit
    polygon through add_concave_poly_filled (the call ui_bands.py:261 already
    uses for the spectrogram) rather than through the path API's convex fill,
    which would bridge the arc and cover the box's own corner.
    """
    r = css_radius(radius, w, h)
    if r <= 0.0 or backdrop[3] <= 0.0:
        return
    c = _u32(backdrop)
    n = seg or max(6, int(r * 2))
    # (outer corner, arc centre) per corner, and the angle the arc starts at
    corners = (
        ((x, y), (x + r, y + r), 180.0),              # top-left
        ((x + w, y), (x + w - r, y + r), 270.0),      # top-right
        ((x + w, y + h), (x + w - r, y + h - r), 0.0),   # bottom-right
        ((x, y + h), (x + r, y + h - r), 90.0),       # bottom-left
    )
    for (ox, oy), (cx, cy), a0 in corners:
        pts = [imgui.ImVec2(ox, oy)]
        for i in range(n + 1):
            a = math.radians(a0 + 90.0 * i / n)
            pts.append(imgui.ImVec2(cx + r * math.cos(a), cy + r * math.sin(a)))
        dl.add_concave_poly_filled(pts, c)


# --------------------------------------------------------------------------
# rings  (shadcn's `ring-N`, which is a box-shadow and not an outline)
# --------------------------------------------------------------------------

def ring(dl, x, y, w, h, col, radius, width=None) -> None:
    """A CSS `box-shadow: 0 0 0 Npx col` - an N px band OUTSIDE the box.

    Not a filled expanded rect: CSS clips an outer box-shadow so it is never
    painted under the element, and the kit has elements with transparent
    backgrounds (the Input in light) where a filled ring would show through
    the middle. So it is a true annulus, which means a stroke - and that
    needs to know where ImGui actually puts one.

    Calibrated, because the obvious guesses are all wrong. An add_rect stroke
    of thickness t is centred on `p + 0.5`, not on `p`:

        t = 1   covers [p, p + 1)          <- wholly inside, the README's finding
        t = 3   covers [p - 1, p + 2)      <- measured here

    So to land a band of `width` px wholly outside the box, the path must be
    expanded by `0.5 + width / 2` - 2.0 for the 3px ring shadcn uses, which
    is neither 3 nor 1.5. Verified on all four sides against the exact rows
    and columns CSS paints. At width 1 the formula gives 1.0, which is the
    expansion `card` was already measured to need for its 1px ring.
    """
    s = RING_W if width is None else width
    if col[3] <= 0.0 or s <= 0.0:
        return
    e = 0.5 + s / 2.0
    dl.add_rect(
        imgui.ImVec2(x - e, y - e), imgui.ImVec2(x + w + e, y + h + e),
        _u32(col),
        # concentric with the box's own corner, so the band's outer edge
        # lands at radius + s and its inner edge at radius
        rounding=css_radius(radius, w, h) + e, thickness=s,
    )


def shadow_stack(dl, x, y, w, h, radius, layers) -> None:
    """Several CSS box-shadows at once, painted back to front.

    `layers` is (dx, dy, blur, spread, alpha) per shadow - the shape
    tokens.SHADOW_MD holds. CSS lists shadows front to back, so they go up in
    reverse.
    """
    for dx, dy, blur, spread, a in reversed(layers):
        shadow(dl, x, y, w, h, (0.0, 0.0, 0.0, a), radius,
               dx=dx, dy=dy, blur=blur, spread=spread)


# --------------------------------------------------------------------------
# Tier 1 components - chrome only, state passed in
# --------------------------------------------------------------------------
#
# Pure functions of (rect, state, tokens), the way `badge` and `card` are, so
# the gallery can pin them to spec rects and the diff can measure them one at
# a time. The interactive versions in interact.py call straight into these.

def slider(dl, x, y, w, h, fracs, theme, tbl, *, ring_f=0.0, disabled=False,
           track_h=None, thumb=None):
    """shadcn Slider.

    `ring_f` is 0..1 for the thumb's hover/active ring, so a caller can ease
    it rather than snap it; `fracs` is one fraction or two. The range is
    clipped by the track exactly the way `overflow-hidden rounded-full`
    clips it - see fill_clipped.
    """
    import box as B
    th = tbl["track_h"] if track_h is None else track_h
    tz = tbl["thumb"] if thumb is None else thumb
    a = tbl["disabled_opacity"] if disabled else 1.0

    def c(key, mul=1.0, themed=True):
        tok, al = tbl[key]
        return rgba(tok, al * mul * a, theme=theme if themed else None)

    track, rng, thumbs = B.slider_geom(x, y, w, h, fracs, track_h=th, thumb=tz)
    # Exact geometry above, snapped paint below - the browser does the same.
    ptrack = snap(track.x, track.y, track.w, track.h)
    fill(dl, *ptrack[:4], c("track"), ptrack[3] / 2.0)
    if rng.w > 0.0:
        px, py, pw, ph = snap(rng.x, rng.y, rng.w, rng.h)
        if pw > 0.0:
            fill_clipped(dl, px, py, pw, ph, c("range"), ptrack, ptrack[3] / 2.0)
    for t in thumbs:
        tx, ty, tw, tht = snap(t.x, t.y, t.w, t.h)
        if ring_f > 0.01:
            ring(dl, tx, ty, tw, tht, c("ring", ring_f), tw / 2.0)
        box(dl, tx, ty, tw, tht,
            # a literal white, NOT a token - see the note in tokens.SLIDER
            fill_col=c("thumb_fill", themed=False),
            border_col=c("thumb_border"),
            radius=tw / 2.0, border_w=1.0)
    return track, rng, thumbs


def switch(dl, x, y, on_f, theme, tbl, *, size="default", ring_f=0.0,
           disabled=False):
    """shadcn Switch. `on_f` is 0..1, so the thumb slides and the track
    cross-fades on the same eased value rather than snapping."""
    import box as B
    from ease import mix
    track, off, onr = B.switch_geom(x, y, size)
    a = 0.5 if disabled else 1.0
    # The default size is 18.390625 px tall, and the browser paints that box
    # snapped to whole pixels while still laying the thumb out off the
    # fraction - so the TRACK snaps and the thumb does not. See draw.snap.
    px, py, pw, ph = snap(track.x, track.y, track.w, track.h)
    if ring_f > 0.01:
        ring(dl, px, py, pw, ph, rgba("ring", 0.5 * ring_f, theme=theme),
             ph / 2.0)
    bg = mix(rgba(tbl["off"][0], tbl["off"][1] * a, theme=theme),
             rgba(tbl["on"][0], tbl["on"][1] * a, theme=theme), on_f)
    box(dl, px, py, pw, ph, fill_col=bg,
        border_col=rgba(*tbl["border"], theme=theme),
        radius=ph / 2.0, border_w=1.0)
    tx = off.x + (onr.x - off.x) * on_f
    # the thumb's own colour is themed AND state-dependent: in dark it
    # inverts between `foreground` and `primary-foreground`
    tc = mix(rgba(tbl["thumb_off"][0], tbl["thumb_off"][1] * a, theme=theme),
             rgba(tbl["thumb_on"][0], tbl["thumb_on"][1] * a, theme=theme), on_f)
    qx, qy, qw, qh = snap(tx, off.y, off.w, off.h)
    fill(dl, qx, qy, qw, qh, tc, qw / 2.0)
    return track


def field(dl, x, y, w, h, theme, tbl, *, focus_f=0.0, invalid=False,
          disabled=False, radius=None):
    """The chrome an Input and a Select trigger share: a 1px bordered box
    with a 3px focus ring outside it.

    One function because the two are measured identical apart from height,
    radius and padding - and keeping them one place is what stops the two
    drifting a pixel apart the way the trend badge's three constants did.
    """
    from ease import mix
    r = RADII[tbl.get("radius", "lg")] if radius is None else radius
    # `disabled:opacity-50` is an opacity on the ELEMENT, so it multiplies the
    # border and the fill alike - on top of a fill that is already themed
    # (input/50 in light, input/80 in dark). Missing this left the whole
    # 200x32 box wrong by 12 levels: the fill was right and the border was
    # twice as dark as it should be.
    from ease import over
    dim = tbl.get("disabled_opacity", 0.5) if disabled else 1.0

    def c(spec, mul=1.0):
        tok, al = spec
        return rgba(tok, al * mul, theme=theme)

    if invalid:
        ring(dl, x, y, w, h, c(tbl["invalid_ring"]), r)
        bcol = c(tbl["invalid_border"])
    else:
        if focus_f > 0.01:
            ring(dl, x, y, w, h, c(tbl["ring"], focus_f), r)
        bcol = mix(c(tbl["border"]), c(tbl.get("focus_border", tbl["border"])),
                   focus_f)
    bg = c(tbl["disabled_bg"] if (disabled and "disabled_bg" in tbl)
           else tbl["bg"])

    if dim < 1.0:
        # `disabled:opacity-50` is an opacity on the ELEMENT: CSS composites
        # the fill and the border first and dims the RESULT. So the border's
        # colour here is the border already stacked over the fill, and the
        # fill is drawn inset by the border width so it is not counted twice.
        # Scaling each layer's alpha instead leaves the fill showing through
        # a border that should have covered it.
        bcol = _dim(over(bcol, bg), dim)
        bg = _dim(bg, dim)
        fill(dl, x + 1.0, y + 1.0, w - 2.0, h - 2.0, bg, max(r - 1.0, 0.0))
        border(dl, x, y, w, h, bcol, r, 1.0)
        return r

    box(dl, x, y, w, h, fill_col=bg, border_col=bcol, radius=r, border_w=1.0)
    return r


def _dim(col, f: float):
    return (col[0], col[1], col[2], col[3] * f)




def select_trigger(dl, x, y, w, h, theme, tbl, *, size="default", hot=0.0,
                   focus_f=0.0, disabled=False, open_=False):
    """shadcn SelectTrigger: the Input's box, plus a chevron.

    The chevron is `size-4 text-muted-foreground`, right-aligned inside the
    padding and vertically centred - measured at x = w - 1 - 8 - 16 and
    y = (h - 16) / 2 for both sizes.

    The radius is NOT constant across sizes: default is rounded-lg (10) and
    sm is rounded-md (8), which is the sort of thing that only shows up in a
    dump.
    """
    from ease import mix
    _h, rkey = SELECT_SIZES[size]
    r = RADII[rkey]
    # light has no hover tint at all and dark goes input/30 -> input/50, so
    # this interpolates between two table entries rather than guessing one
    # The hover tint is themed in an asymmetric way: light stays transparent
    # at both ends and dark runs input/30 -> input/50. Interpolating between
    # the two table entries covers both without a special case.
    t2 = dict(tbl)
    t2["bg"] = ("#00000000", 1.0)          # painted below, after the ring
    field(dl, x, y, w, h, theme, t2, focus_f=focus_f, disabled=disabled,
          radius=r)
    bg = mix(rgba(*tbl["bg"], theme=theme),
             rgba(*tbl["hover_bg"], theme=theme), hot)
    fill(dl, x, y, w, h, bg, r)
    cs = tbl["chevron"]
    icon(dl, "chevron-down", x + w - 1.0 - tbl["pad_r"] - cs,
         y + (h - cs) / 2.0, cs, rgba("muted-foreground", theme=theme))
    return r


def tooltip_panel(dl, x, y, w, h, theme, tbl, *, arrow_at=None, side="top"):
    """shadcn TooltipContent: a rounded fill, plus a rotated-square arrow.

    The arrow is `size-2.5 rotate-45 rounded-[2px]` with
    `translate-y-[calc(-50%_-_2px)]`, which measures as: a 10px square turned
    45 degrees (so a 14.142 px bounding box) whose CENTRE sits 2 px inside
    the panel's edge. Half of it is therefore hidden behind the panel and
    what shows is a triangle 5.071 px tall with a 10.142 px base - the
    diamond's exposed tip, with one rounded corner on it.

    It is centred on the TRIGGER rather than on the panel, which is what
    `arrow_at` is for: pass the trigger's centre x. Radix shifts a panel to
    stay on screen without moving the arrow, so the two genuinely come apart.
    """
    r = RADII[tbl["radius"]]
    col = rgba(*tbl["bg"], theme=theme)
    fill(dl, x, y, w, h, col, r)
    if arrow_at is None:
        return r
    half = tbl["arrow"] * math.sqrt(2.0) / 2.0        # 7.071
    inset = tbl["arrow_dy"]                            # 2
    vis = half - inset                                 # 5.071, the exposed tip
    cx = min(max(arrow_at, x + r + vis), x + w - r - vis)
    cy = (y + h - inset) if side == "top" else (y + inset)
    _diamond(dl, cx, cy, tbl["arrow"], tbl["arrow_radius"], col)
    return r


def _diamond(dl, cx, cy, side, radius, col) -> None:
    """A square of `side` px turned 45 degrees, with `radius` corners.

    The tooltip's arrow, and NOT a triangle: the square's `rounded-[2px]`
    leaves a visibly blunt tip. Drawn as a sharp triangle the tip pixel came
    out at 55% coverage against the browser's 23% - the single largest
    remaining disagreement on the panel.

    Only the half below the panel's edge is ever seen, but the whole shape
    goes down: it is the same colour as the panel it overlaps, so there is
    nothing to clip and nothing to see.

    Built from the four corner arcs, which ImGui joins with the straight
    edges by itself. A rotated rounded square is convex, so it fills convex.
    """
    a = side / 2.0
    d = (a - radius) * math.sqrt(2.0)      # arc centres, along the 4 axes
    c = _u32(col)
    dl.path_clear()
    # clockwise from the top corner; each corner's arc spans the 90 degrees
    # between the outward normals of its two edges
    for (ox, oy), a0 in (((0.0, -d), 225.0), ((d, 0.0), 315.0),
                         ((0.0, d), 45.0), ((-d, 0.0), 135.0)):
        dl.path_arc_to(imgui.ImVec2(cx + ox, cy + oy), radius,
                       math.radians(a0), math.radians(a0 + 90.0))
    dl.path_fill_convex(c)
