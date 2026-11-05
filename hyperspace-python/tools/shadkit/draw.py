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

    Calibrated against tools/shadkit/probe_stroke.py, not against an assumption.
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
