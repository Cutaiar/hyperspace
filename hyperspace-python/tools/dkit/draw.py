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

from imgui_bundle import imgui

from tokens import RADII, rgba


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


def text_cell(dl, cell, faces, col) -> None:
    """One pinned string, vertically centred in its box like CSS line-height.

    ImGui 1.92 renders any face at any size through push_font(face, size), so
    the size comes from the spec rather than from a baked atlas entry.
    """
    face = faces.get(cell["variant"])
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

def push_css_font(faces, variant: str, css_px: float):
    """Push a face at a size that means what CSS means by it.

    See FONT_SPAN_EM: stb_truetype sizes by ascent-descent, CSS by the em.
    """
    imgui.push_font(faces.get(variant), css_px * FONT_SPAN_EM.get(variant, 1.0))


def fit_text(s, faces, variant, size, max_w) -> str:
    """The longest prefix of `s` that fits in max_w, with an ellipsis.

    shadcn leans on `truncate` / `line-clamp-1`; ImGui clips nothing by
    itself. Same binary search ui.py:317-329 uses."""
    if max_w <= 0 or text_w(s, faces, variant, size) <= max_w:
        return s
    lo, hi = 0, len(s)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if text_w(s[:mid] + "\u2026", faces, variant, size) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return s[:lo] + "\u2026"


def label(dl, x, y, s, faces, variant, size, col, *, align="left", box_w=0.0,
          baseline_box=0.0, max_w=0.0):
    """Draw `s` at (x, y). With baseline_box, centre it vertically in that
    height the way a CSS line box would; with align/box_w, align horizontally.
    Returns the advance width."""
    if max_w:
        s = fit_text(s, faces, variant, size, max_w)
    push_css_font(faces, variant, size)
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


def text_w(s, faces, variant, size) -> float:
    push_css_font(faces, variant, size)
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


def trend_arrow(dl, x, y, size, up: bool, col) -> None:
    """A small up/down triangle.

    Geist's latin subset has no arrows, and ImGui draws a missing glyph as a
    box or nothing - so trend marks are drawn, not typed. The panel already
    takes this approach for device glyphs (ui_players.py:421-539).
    """
    h = size * 0.5
    cx, cy = x + size / 2.0, y + size / 2.0
    if up:
        pts = [(cx, cy - h * 0.7), (cx + h * 0.8, cy + h * 0.5),
               (cx - h * 0.8, cy + h * 0.5)]
    else:
        pts = [(cx, cy + h * 0.7), (cx + h * 0.8, cy - h * 0.5),
               (cx - h * 0.8, cy - h * 0.5)]
    dl.add_triangle_filled(imgui.ImVec2(*pts[0]), imgui.ImVec2(*pts[1]),
                           imgui.ImVec2(*pts[2]), _u32(col))
