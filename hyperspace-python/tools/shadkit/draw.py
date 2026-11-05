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
