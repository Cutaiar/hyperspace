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

import functools
import itertools
import json
import math
from math import floor
from pathlib import Path

from imgui_bundle import imgui

from .tokens import RADII, RING_W, SCROLL, SELECT_SIZES, rgba


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

    Calibrated against hyperspace/dkit/dev/probe_stroke.py, not against an assumption.
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


def px(v: float) -> int:
    """Round a COORDINATE to a whole pixel, monotonically.

    Not `round()`. Python's built-in rounds half to EVEN, and this kit puts
    things on half pixels constantly - anything centred in a box of odd
    height lands on one. Step such a value down by 1 and banker's rounding
    gives 126, 124, 124, 122, 122: a two-pixel lurch, then nothing, then a
    two-pixel lurch. While the page scrolls, every line doing that at its
    own phase is the wobble.

    `floor(v + 0.5)` steps by exactly 1 every time, which is what makes a
    scrolled page move as one piece. It is also what the browser does: ties
    go up, not to even.
    """
    return floor(v + 0.5)


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
    x0, y0 = px(x), px(y)
    return float(x0), float(y0), float(px(x + w) - x0), float(px(y + h) - y0)


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
def _blur_layers(sigma: float, reach: int | None = None):
    """Integer-expansion layers approximating a Gaussian falloff.

    `reach` is how far out the stack goes, and it MUST scale with sigma. It
    was fixed at 3, which is ample for the 2px shadows the kit was first
    calibrated on (sigma 1, so 3 sigma) but truncates anything softer:
    shadow-md's blur 6 is sigma 3 and reaches ~9px, so two thirds of its
    falloff was simply not drawn. Measured on a menu panel, that was 5
    levels down the sides and under the bottom edge - the whole of the only
    cell in the gallery that was failing.
    """
    from math import ceil, erf, sqrt
    if reach is None:
        reach = max(3, ceil(3.0 * sigma))
    # Integer steps. Half-steps were tried on the soft end and came out a
    # level WORSE for twice the draw calls, which says the residual is not
    # quantisation: Chromium blurs with three box passes (Skia), not a true
    # Gaussian, and the two shapes diverge most against the box's own edge.
    # Modelling the triple box is the way to close it, and is not done.
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
    off headless with no fallback, so it cannot back the diff harness.

    Measured accuracy, rather than asserted:

        shadow-xs   blur 2 (sigma 1)   within 1 level everywhere (the cards)
        shadow-md   blur 6 (sigma 3)   within 1 level from 2px out, and up
                                       to 7 levels on the TWO rows against
                                       the box's own edge

    Chromium blurs with three box passes, not a true Gaussian, and the two
    shapes diverge most where the gradient is steepest. Half-step layers
    make it a level worse, so the fix is to model the triple box; until
    then the limit is this, and `diff.py` reports it rather than hiding it.
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


# --------------------------------------------------------------------------
# faces and metrics
# --------------------------------------------------------------------------
#
# What the kit's text is measured against: Chromium laying out the same
# variable font the faces are cut from (Inter; `FAMILY`). Three things about ImGui's own text path each disagreed with it,
# measured (RETRO row 61), and each is handled here rather than per
# component:
#
# * ImGui ROUNDS every font size to a whole pixel, and its FreeType loader
#   sizes a face by ascender - descender (REAL_DIM). Geist's span was 1.30
#   em, so 12px CSS had to be asked for as 15.6 - which became 16, text 2.6%
#   large. build_fonts.py now writes a one-em line box into the TTFs, so the
#   size pushed IS the CSS px and is already whole.
# * FreeType HINTS by default, and a hinted advance is a whole pixel. So
#   every face loads with hinting off, and the advances are the font's own.
# * ImGui applies no OpenType positioning or substitution; Chromium applies
#   `kern` and the default substitutions (`calt`, `liga`, ...). They are
#   exported at build time into fonts/metrics.json and replayed by `shape`.

_METRICS = json.loads(
    (Path(__file__).resolve().parent / "fonts" / "metrics.json").read_text())

# The font's REAL vertical metrics - the TTFs no longer carry them (above).
UPEM = float(_METRICS["upem"])
ASCENT_EM = _METRICS["ascender"] / UPEM            # Inter: 1984/2048
DESCENT_EM = -_METRICS["descender"] / UPEM         # Inter: 494/2048

# (ascender - descender) / upem, per face: the height of the font's glyph box
# in em. No longer a size multiplier - the faces are loaded so that a push
# of N px is N px of em - but still the glyph box the underline and the
# Blink baseline are worked out from.
FONT_SPAN_EM = {v: ASCENT_EM + DESCENT_EM
                for v in ("regular", "medium", "semibold")}


class Faces(dict):
    """A variant → ImFont map (`load_faces`, `host_faces`) that carries its
    own `span_em`: the ratio above is the kit's font's, and a host handing the kit
    its own faces needs its own, or its text renders at the wrong size.

    `measured` says whether these are the kit's own faces, built with a
    one-em line box and measured into fonts/metrics.json (RETRO 77, 90). A
    host's faces are neither: they keep ImGui's own metrics and the span
    multiplier, the path the kit had before."""
    span_em: dict = FONT_SPAN_EM
    measured: bool = True


def is_measured(faces) -> bool:
    """Are `faces` the kit's own (`load_faces`), not a host's."""
    return getattr(faces, "measured", True)


def span_em(faces, variant: str) -> float:
    """`variant`'s ascent-to-descent span in ems, from `faces` if it says
    (a `Faces`), else the kit's font's (`FONT_SPAN_EM`)."""
    return getattr(faces, "span_em", FONT_SPAN_EM).get(variant, 1.0)


def span_em_of(path) -> float:
    """A TrueType face's ascent-to-descent span in ems, as stb_truetype
    sizes it (hhea ascender - descender, over unitsPerEm): what `span_em`
    needs for a host's face. Read off the file's own tables."""
    import struct
    data = Path(path).read_bytes()
    n = struct.unpack(">H", data[4:6])[0]
    tables = {data[12 + 16 * i:16 + 16 * i]: struct.unpack(">II", data[20 + 16 * i:28 + 16 * i])
              for i in range(n)}
    head, hhea = tables[b"head"][0], tables[b"hhea"][0]
    upem = struct.unpack(">H", data[head + 18:head + 20])[0]
    asc, desc = struct.unpack(">hh", data[hhea + 4:hhea + 8])
    return (asc - desc) / upem


def host_faces(io, files: dict, density: float = 1.0, fallback=None) -> Faces:
    """The kit's faces from a HOST's files — {variant: path} — each with
    `fallback` merged in behind it and its own `span_em`, so the kit's
    Button, Select, Kbd and label draw in the host's type at the size CSS
    would give it."""
    out = Faces()
    out.span_em = {}
    out.measured = False
    for variant, path in files.items():
        cfg = imgui.ImFontConfig()
        cfg.rasterizer_density = density
        f = io.fonts.add_font_from_file_ttf(str(path), 16.0, cfg)
        if fallback is not None and Path(fallback).exists():
            m = imgui.ImFontConfig()
            m.merge_mode = True
            m.rasterizer_density = density
            io.fonts.add_font_from_file_ttf(str(fallback), 16.0, m)
        span = span_em_of(path)
        for key in (variant, f"{variant}-tnum"):
            out[key] = f
            out.span_em[key.removesuffix("-tnum")] = span
    return out


# The six faces build_fonts.py produces: three weights, each with and
# without its tabular figures (see build_fonts.py).
FAMILY = _METRICS["family"]   # dev/build_fonts.py's FAMILY
FACE_FILES = [(f"{v}{t}", f"{FAMILY}-{w}{t}.ttf")
              for v, w in (("regular", "Regular"), ("medium", "Medium"),
                           ("semibold", "SemiBold"))
              for t in ("", "-tnum")]


# The panel merges DejaVu behind every face for the symbols its own faces do
# not carry (ui.py:152-153). The kit needs the same: the latin subset has
# no arrows and no command key, and a missing glyph draws as a box.
FONTS = Path(__file__).resolve().parent / "fonts"         # the kit's faces
FALLBACK = FONTS.parent.parent / "fonts" / "DejaVuSans.ttf"  # the panel's (hyperspace/fonts)
# DejaVu Sans is (1901 + 483) / 2048 em from ascender to descender, and it
# is NOT rebuilt with a one-em line box, so its loader is asked for that
# much more to set it at the same em as the face it falls back from - as a
# browser sets a fallback font at the element's font-size.
FALLBACK_SPAN_EM = (1901 + 483) / 2048

# ImGuiFreeTypeLoaderFlags_NoHinting (imgui_freetype.h). imgui_bundle does
# not bind the enum. Hinting snaps advances to whole pixels; Chromium's
# Linux text is laid out on fractional advances (and subpixel-positioned).
FT_NO_HINTING = 1 << 0


def load_faces(io, here=None, density: float = 1.0) -> dict:
    """Every face, each with the symbol fallback merged in behind it. The
    faces are the package's own (`FONTS`); `here` is accepted and unused,
    for the callers from when the kit was a folder of scripts."""
    out = Faces()
    fb = FALLBACK
    for key, fn in FACE_FILES:
        cfg = imgui.ImFontConfig()
        cfg.rasterizer_density = density
        cfg.font_loader_flags = FT_NO_HINTING
        out[key] = io.fonts.add_font_from_file_ttf(str(FONTS / fn), 16.0, cfg)
        if fb.exists():
            m = imgui.ImFontConfig()
            m.merge_mode = True
            m.rasterizer_density = density
            m.font_loader_flags = FT_NO_HINTING
            m.extra_size_scale = FALLBACK_SPAN_EM
            io.fonts.add_font_from_file_ttf(str(fb), 16.0, m)
    return out


class _Shaper:
    """One face's substitutions and `kern`, from fonts/metrics.json.

    `subst` replays the font's default GSUB lookups (dev/build_fonts.py
    `export_gsub`) the way HarfBuzz applies them: each top-level lookup in
    turn over the whole string, left to right; at each position the first
    rule that matches wins, and a matched chain rule skips past its input -
    including a rule with nothing to do, which is how a font writes an
    exception. Checked against HarfBuzz itself, glyph for glyph, in
    dev/test_text.py."""

    def __init__(self, d: dict):
        lookups, order, sets = d["gsub"]
        sets = [frozenset(x) for x in sets]
        self.lookups = {int(k): v for k, v in lookups.items()}
        for kind, data in self.lookups.values():
            if kind == "chain":       # set indices -> the sets themselves
                for rule in data:
                    for part in range(3):
                        rule[part] = [sets[x] for x in rule[part]]
        self.order = order
        # every character any top-level lookup can start on: a string with
        # none of them is returned as it came, which is most UI text
        first = set()
        for li in order:
            kind, data = self.lookups[li]
            if kind == "chain":
                for rule in data:
                    first |= rule[1][0]
            else:
                first |= set(data)
        self.first = frozenset(first)
        self.left = {c: i for i, cls in enumerate(d["left"]) for c in cls}
        self.right = {c: i for i, cls in enumerate(d["right"]) for c in cls}
        self.m = [dict(zip(row[::2], row[1::2])) for row in d["kern"]]
        self.adv = {c: v / UPEM for c, v in d["adv"].items()}

    def _at(self, buf: list, i: int, li: int) -> int:
        """Apply lookup `li` at position i if it matches there. Returns the
        position to continue from, or -1 if nothing matched."""
        kind, data = self.lookups[li]
        c = buf[i]
        if kind == "single":
            out = data.get(c)
            if out is None:
                return -1
            buf[i] = out
            return i + 1
        if kind == "liga":
            for rest, out in data.get(c, ()):
                n = len(rest)
                if "".join(buf[i + 1:i + 1 + n]) == rest:
                    buf[i:i + 1 + n] = [out]
                    return i + 1
            return -1
        for back, inp, ahead, do in data:
            n = len(inp)
            if i + n + len(ahead) > len(buf) or i < len(back):
                continue
            if not all(buf[i + k] in inp[k] for k in range(n)):
                continue
            if not all(buf[i - 1 - k] in back[k] for k in range(len(back))):
                continue
            if not all(buf[i + n + k] in ahead[k] for k in range(len(ahead))):
                continue
            end = i + n
            for seq, sub in do:
                before = len(buf)
                self._at(buf, i + seq, sub)
                end -= before - len(buf)      # a ligature shortens the input
            return end
        return -1

    def subst(self, s: str) -> str:
        if not self.first.intersection(s):
            return s
        buf = list(s)
        for li in self.order:
            i = 0
            while i < len(buf):
                j = self._at(buf, i, li)
                i = j if j > i else i + 1
        return "".join(buf)

    def kern(self, a: str, b: str) -> float:
        li = self.left.get(a)
        if li is None:
            return 0.0
        rj = self.right.get(b)
        return 0.0 if rj is None else self.m[li].get(rj, 0) / UPEM


_SHAPERS = {key: _Shaper(_METRICS["faces"][fn]) for key, fn in FACE_FILES}


@functools.lru_cache(maxsize=4096)
def shape(s: str, variant: str, tabular: bool = False):
    """(glyphs, pen) for `s`: the string after the font's substitutions, and the
    pen's advance after each glyph in em - its `hmtx` advance plus the
    kerning to the next - as HarfBuzz gives Chromium. None for a glyph the
    font does not carry (it comes from the fallback face, whose advance the
    loaded font supplies).

    Pure: no ImGui, so it is cached - an immediate-mode UI shapes the same
    strings every frame. Ligatures first, then kerning between what they
    leave, as GSUB precedes GPOS."""
    sh = _SHAPERS.get(face_key(variant, tabular)) or _SHAPERS[variant]
    g = sh.subst(s)
    pen = []
    for i, c in enumerate(g):
        a = sh.adv.get(c)
        pen.append(None if a is None else
                   a + (sh.kern(c, g[i + 1]) if i + 1 < len(g) else 0.0))
    return g, tuple(pen)


def face_key(variant: str, tabular: bool) -> str:
    """The face to use. `-tnum` carries the font's tabular figures - replayed by
    `shape`, and frozen into its cmap for stock widgets (build_fonts.py).
    Numbers that change in place — a readout, a table column — want it; words
    do not, exactly as shadcn turns `tabular-nums` on selectively."""
    return f"{variant}-tnum" if tabular else variant


def text_cell(dl, cell, faces, col) -> None:
    """One pinned string, vertically centred in its box like CSS line-height.

    The oracle sets font-variant-numeric: tabular-nums on every text cell,
    so the kit uses the frozen faces to compare like with like - and sets
    `line-height` to the cell's height, which is what places its baseline."""
    if not is_measured(faces):
        _text_cell_host(dl, cell, faces, col)
        return
    label(dl, cell["x"], cell["y"], cell["text"], faces, cell["variant"],
          float(cell["size"]), col, baseline_box=cell["h"], tabular=True,
          line_h=float(cell["h"]))


def _text_cell_host(dl, cell, faces, col) -> None:
    """`text_cell` for a host's faces (`host_faces`): ImGui's own metrics,
    which is what those faces were measured with - the tables in
    fonts/metrics.json are the kit's font's and say nothing about another."""
    # the oracle sets font-variant-numeric: tabular-nums on every text cell,
    # so the kit must use the frozen faces to compare like with like
    face = faces.get(face_key(cell["variant"], True)) or faces.get(cell["variant"])
    # ImGui's font size is NOT a CSS px. stb_truetype scales so that
    # ascent - descent equals the requested size; CSS maps the em square to
    # font-size. Geist was upem 1000 with ascent 1005 / descent -295, so its
    # span was 1.30 em and ImGui renders 14px CSS text at 77% unless asked for
    # 14 * 1.30. Per-face, because the ratio is a property of the font.
    size = float(cell["size"]) * span_em(faces, cell["variant"])
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

    The faces are built and loaded so that ImGui's size is the em (see
    "faces and metrics"), so this is the CSS px itself - no multiplier, and
    so nothing for ImGui's whole-pixel rounding of sizes to change."""
    key = face_key(variant, tabular)
    face = faces.get(key) or faces.get(variant)
    imgui.push_font(face, css_px if is_measured(faces) else css_px * span_em(faces, variant))


@functools.lru_cache(maxsize=64)
def ascent_descent(css_px: float) -> tuple:
    """Blink's ascent and descent for the kit's font at `css_px`: each ROUNDED to a
    whole pixel on its own (SkScalarRoundToScalar, Linux and Windows)."""
    return float(px(ASCENT_EM * css_px)), float(px(DESCENT_EM * css_px))


# Tailwind's `text-*` scale sets a line-height with every size (`text-xs` is
# 12px on a 16px line, `text-sm` 14px on 20), and every shadcn component
# sizes its text with one. So a label's line box is that height, not
# `line-height: normal`, unless a caller says otherwise. In Geist this never
# showed: its 12px glyph box (A + D) was 16 anyway. Inter's is 15, and
# centring 15 in a 20px Kbd put the glyph a pixel below Chromium's.
TEXT_LEADING = {12.0: 16.0, 14.0: 20.0, 16.0: 24.0, 18.0: 28.0, 20.0: 28.0,
                24.0: 32.0, 30.0: 36.0, 36.0: 40.0}


def baseline_y(y: float, css_px: float, box_h: float = 0.0,
               line_h: float = 0.0) -> float:
    """Where Chromium puts the alphabetic baseline of one line of the kit's font.

    The line box is `line_h` tall (0: `line-height: normal`, which for the
    font is A + D, `ascent_descent`), centred in a box `box_h` tall at y as
    `items-center` does - or, with no box, its top is y. Two roundings,
    measured on 252 cells (11-20px, boxes 15-33, line-height normal, 16px
    and 20px) in Geist and again in Inter, all of which this reproduces:

    * the line box's offset in the box rounds half UP;
    * inside the line box, the half-leading above the glyphs is FLOORED -
      so an odd leading puts the extra pixel below.

    Reading Blink's source had suggested flooring both; the measurement
    refuted the first. The gallery's text cells (`line-height` = the cell)
    are where the second shows: 16px in 36 and 30px in 36 each sat 1px low
    with the leading rounded."""
    a, d = ascent_descent(css_px)
    lh = line_h or (a + d)
    top = px(y + (box_h - lh) / 2.0 if box_h else y)
    return float(top + floor((lh - (a + d)) / 2.0)) + a


def stock_text_y(y: float, css_px: float, box_h: float, faces=None) -> float:
    """The line top to hand a STOCK ImGui text widget (InputText) so that
    its glyphs sit on `baseline_y` - the line `draw.label` draws on.

    ImGui puts a line's baseline its face's baked ascent below the line's
    top, truncating the top to a whole pixel; that ascent comes from the
    one-em line box build_fonts.py writes, not from the font's real metrics,
    so it is read rather than assumed. Call with the face pushed.

    With a host's `faces` it is ImGui's own centring, as before."""
    if faces is not None and not is_measured(faces):
        return y + (box_h - imgui.get_font_size()) / 2.0
    asc = imgui.get_font().get_font_baked(imgui.get_font_size()).ascent
    return baseline_y(y, css_px, box_h, TEXT_LEADING.get(float(css_px), 0.0)) - asc


def _glyph_run(dl, x: float, base: float, glyphs: str, pen, css_px: float,
               col: int) -> None:
    """Draw a shaped run one quad per glyph, its left edge at x and its
    baseline at base. Exact, and ~10x the cost of `add_text`, so `label`
    uses it only for a single glyph; longer strings go through `_runs`.

    Not `add_text`. ImGui truncates a text origin to a whole pixel and has
    no kerning, so a kerned run - which has to restart after every pair -
    would land on whole pixels, where Chromium positions each glyph at its
    fractional pen position (measured: the ink follows a quarter-pixel
    shift of the element). So each glyph is its own quad, at the pen, and
    the backend's LINEAR sampling of the atlas carries the fraction.

    Each quad is exactly its bitmap. A first version widened every quad by
    the atlas padding, reasoning that ink sliding past a quad's edge would
    otherwise be lost; measured, it was worse on both counts - a "W"
    centred in a Kbd moved 0.18px off Chromium's rather than 0.08, and in a
    full atlas the widened edge sampled a neighbour's texels, a 13-level
    speck beside the gallery's `text.mixed`. Vertically the baseline is
    whole, and glyph tops are whole device pixels from it."""
    if (col >> 24) & 0xFF == 0:
        return
    font = imgui.get_font()
    baked = font.get_font_baked(css_px)
    top = base - baked.ascent
    for c, p in zip(glyphs, pen):
        g = baked.find_glyph(ord(c))
        if g.is_visible():
            dl.prim_reserve(6, 4)
            dl.prim_rect_uv(imgui.ImVec2(x + g.x0, top + g.y0),
                            imgui.ImVec2(x + g.x1, top + g.y1),
                            imgui.ImVec2(g.u0, g.v0),
                            imgui.ImVec2(g.u1, g.v1), col)
        x += g.advance_x if p is None else p * css_px


@functools.lru_cache(maxsize=4096)
def _width_em(s: str, variant: str, tabular: bool = False):
    """`s`'s advance in em, or None if a glyph needs the fallback face."""
    pen = shape(s, variant, tabular)[1]
    return None if None in pen else sum(pen)


def _run_w(glyphs: str, pen, css_px: float) -> float:
    """A shaped run's advance, with the face pushed. Not `calc_text_size`,
    which rounds its width UP to a whole pixel."""
    w = sum(p for p in pen if p is not None) * css_px
    if None in pen:
        baked = imgui.get_font().get_font_baked(css_px)
        w += sum(baked.get_char_advance(ord(c))
                 for c, p in zip(glyphs, pen) if p is None)
    return w


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


# How far ImGui's own pen may drift from the kerned one before `label`
# starts a new `add_text` run. Measured on the dashboard's strings: at 0.25
# a 24-character string is 5-8 runs and no glyph lands more than ~0.7px
# from Chromium's position (half of that is the run's start rounding to a
# whole pixel, which `add_text` does). One quad per glyph is exact, and was
# ~10x the cost - 3ms of a dashboard frame. See RETRO row 83.
DRIFT_PX = 0.25

_RUNS: dict = {}


def _runs(glyphs: str, pen, key: str, css_px: float, baked) -> tuple:
    """`glyphs` cut into ((offset, text), ...) for `add_text`, with the face
    pushed. Inside a run ImGui places glyphs on its own advances - unhinted,
    so fractional, but unkerned; a run ends where that pen has drifted more
    than DRIFT_PX from the kerned one, and the next starts at the kerned
    offset. Cached: the cut depends only on the string, face and size (and
    the density the face was baked at)."""
    ck = (glyphs, key, css_px, baked.rasterizer_density)
    hit = _RUNS.get(ck)
    if hit is not None:
        return hit
    out, start, rs, ipos, exact = [], 0, 0.0, 0.0, 0.0
    for i, c in enumerate(glyphs):
        if i > start and abs(rs + ipos - exact) > DRIFT_PX:
            out.append((rs, glyphs[start:i]))
            start, rs, ipos = i, exact, 0.0
        adv = baked.get_char_advance(ord(c))
        ipos += adv
        exact += adv if pen[i] is None else pen[i] * css_px
    out.append((rs, glyphs[start:]))
    if len(_RUNS) > 8192:
        _RUNS.clear()
    _RUNS[ck] = hit = tuple(out)
    return hit


def label(dl, x, y, s, faces, variant, size, col, *, align="left", box_w=0.0,
          baseline_box=0.0, max_w=0.0, tabular=False, line_h=None):
    """Draw `s` at (x, y). With baseline_box, centre it vertically in that
    height the way a CSS line box would (`baseline_y`, `line_h` its
    line-height: by default Tailwind's for the size, `TEXT_LEADING`, and 0
    for `normal`); with align/box_w, align horizontally.
    Returns the advance width - Chromium's, exactly (`text_w`).

    The LAYOUT is exact: width, alignment and baseline. The glyphs inside
    the string are drawn by `add_text` in runs (`_runs`), each within
    DRIFT_PX of the kerned pen plus its start's rounding - so a glyph can
    sit up to ~0.7px from where Chromium puts it, for a tenth of the cost of
    placing each one. A single glyph - a Kbd key - is one quad at its exact
    fractional x, which costs no more than a run and is what keeps a
    centred "K" or "W" on Chromium's centre (RETRO row 77)."""
    if not is_measured(faces):
        return _label_host(dl, x, y, s, faces, variant, size, col, align=align,
                           box_w=box_w, baseline_box=baseline_box, max_w=max_w,
                           tabular=tabular)
    if line_h is None:
        line_h = TEXT_LEADING.get(float(size), 0.0)
    if max_w:
        s = fit_text(s, faces, variant, size, max_w, tabular)
    glyphs, pen = shape(s, variant, tabular)
    em = _width_em(s, variant, tabular)
    push_css_font(faces, variant, size, tabular)
    try:
        w = em * size if em is not None else _run_w(glyphs, pen, size)
        tx = x
        if align == "right":
            tx = x + box_w - w
        elif align == "center":
            tx = x + (box_w - w) / 2.0
        base = baseline_y(y, size, baseline_box, line_h)
        c = _u32(col)
        if len(glyphs) == 1:
            _glyph_run(dl, tx, base, glyphs, pen, size, c)
        elif glyphs:
            baked = imgui.get_font().get_font_baked(size)
            top = base - baked.ascent
            for off, sub in _runs(glyphs, pen, face_key(variant, tabular), size,
                                  baked):
                # add_text TRUNCATES its origin; rounding first makes it round
                dl.add_text(imgui.ImVec2(px(tx + off), top), c, sub)
        return float(w)
    finally:
        imgui.pop_font()


def text_w(s, faces, variant, size, tabular=False) -> float:
    """The advance of `s` as Chromium lays it out: fractional, kerned, with
    the font's substitutions. Checked against canvas measureText in test_text.py.

    Pure arithmetic on the frozen metrics unless `s` holds a glyph the font
    does not carry, which only the loaded fallback face can measure."""
    if not is_measured(faces):
        push_css_font(faces, variant, size, tabular)
        try:
            return float(imgui.calc_text_size(s).x)
        finally:
            imgui.pop_font()
    em = _width_em(s, variant, tabular)
    if em is not None:
        return float(em * size)
    glyphs, pen = shape(s, variant, tabular)
    push_css_font(faces, variant, size, tabular)
    try:
        return float(_run_w(glyphs, pen, size))
    finally:
        imgui.pop_font()


def _label_host(dl, x, y, s, faces, variant, size, col, *, align="left",
                box_w=0.0, baseline_box=0.0, max_w=0.0, tabular=False):
    """`label` for a host's faces (`host_faces`): ImGui's own metrics and
    centring, as the kit drew all text before RETRO 77 - the tables and
    baseline rule were measured for the kit's font and say nothing about
    another."""
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
        dl.add_text(imgui.ImVec2(px(tx), px(ty)), _u32(col), s)
        return float(ext.x)
    finally:
        imgui.pop_font()


# `kbd_size` and `kbd_group_size` take a `text_w` OVERRIDE, as
# comp_button.button_size does, which shadows this function inside them;
# this alias is how they reach it.
text_w_ = text_w


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
        for a, b in itertools.pairwise(pts):
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
    from .icons import BOX as ICON_BOX
    from .icons import ICONS
    from .icons import STROKE as ICON_STROKE
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


def corner_notches(x, y, w, h, r, *, seg: int = 0):
    """The four corner notches of a rounded rect, as point lists.

    Pure geometry, no imgui - so it is unit-tested the way box.py is, and
    `cover_corners` is left with nothing but the draw call. One notch is a
    square of side r with a quarter disc taken out of it, so the region is
    CONCAVE: the arc bulges into it.
    """
    n = seg or max(6, int(r * 2))
    # (outer corner, arc centre, the angle the arc starts at) per corner
    corners = (
        ((x, y), (x + r, y + r), 180.0),                  # top-left
        ((x + w, y), (x + w - r, y + r), 270.0),          # top-right
        ((x + w, y + h), (x + w - r, y + h - r), 0.0),    # bottom-right
        ((x, y + h), (x + r, y + h - r), 90.0),           # bottom-left
    )
    out = []
    for (ox, oy), (cx, cy), a0 in corners:
        pts = [(ox, oy)]
        for i in range(n + 1):
            a = math.radians(a0 + 90.0 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        out.append(pts)
    return out


def cover_corners(dl, x, y, w, h, radius, backdrop, *, seg: int = 0) -> None:
    """Paint back the four corner notches of a rounded box.

    The companion to push_clip_rect for content that is NOT a rect - text,
    icons, a whole scrolling subtree. Draw the content clipped to the box,
    then call this: it fills, in the colour BEHIND the box, the area inside
    the bounding rect but outside the rounded rect. Exact whenever that
    backdrop is a known flat colour, which inside a panel it is.

    The shape is `corner_notches`; this is only the draw. Each notch goes up
    as an explicit polygon through add_concave_poly_filled (the call
    ui_bands.py:261 already uses for the spectrogram) rather than through the
    path API's convex fill, which would bridge the arc and cover the box's
    own corner.
    """
    r = css_radius(radius, w, h)
    if r <= 0.0 or backdrop[3] <= 0.0:
        return
    c = _u32(backdrop)
    for poly in corner_notches(x, y, w, h, r, seg=seg):
        dl.add_concave_poly_filled([imgui.ImVec2(px, py) for px, py in poly], c)


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
           track_h=None, thumb=None, origin=0.0):
    """shadcn Slider.

    `ring_f` is 0..1 for the thumb's band, so a caller can ease it rather
    than snap it. THREE states turn it on, which is why it is `ring_f` and
    not `focus_f`: the thumb carries `hover:ring-3 focus-visible:ring-3
    active:ring-3`, so it is the only control in the kit a bare HOVER rings.
    `interact.slider` folds the three into one value.

    `fracs` is one fraction or two. The range is clipped by the track exactly
    the way `overflow-hidden rounded-full` clips it - see fill_clipped.
    """
    from . import box as B
    th = tbl["track_h"] if track_h is None else track_h
    tz = tbl["thumb"] if thumb is None else thumb
    a = tbl["disabled_opacity"] if disabled else 1.0

    def c(key, mul=1.0, themed=True):
        tok, al = tbl[key]
        return rgba(tok, al * mul * a, theme=theme if themed else None)

    track, rng, thumbs = B.slider_geom(x, y, w, h, fracs, track_h=th, thumb=tz,
                                       origin=origin)
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


def slider_box(dl, x, y, w, h, frac, theme, tbl, *, origin=0.0, ring_f=0.0,
               disabled=False) -> None:
    """A Slider too short for its track to read, drawn as a value box: the
    track's colour as a field (`radius md`), and a 2 px bar along its foot
    in the range's colour from `origin` to `frac` — where the value sits.
    The value's words are the caller's, centred over it. A keyboard focus
    rings it as the thumb would be (`ring_f`)."""
    a = tbl["disabled_opacity"] if disabled else 1.0

    def c(k, mul=1.0):
        tok, al = tbl[k]
        return rgba(tok, al * mul * a, theme=theme)

    bx, by, bw, bh = snap(x, y, w, h)
    r = RADII["md"]
    if ring_f > 0.01:
        ring(dl, bx, by, bw, bh, c("ring", ring_f), r)
    fill(dl, bx, by, bw, bh, c("track", 0.6), r)
    lo, hi = sorted((min(max(origin, 0.0), 1.0), min(max(frac, 0.0), 1.0)))
    inset = r / 2
    x0, x1 = bx + inset + (bw - 2 * inset) * lo, bx + inset + (bw - 2 * inset) * hi
    if x1 - x0 >= 1.0:
        fill(dl, x0, by + bh - 3, x1 - x0, 2, c("range"), 1.0)


def switch(dl, x, y, on_f, theme, tbl, *, size="default", focus_f=0.0,
           disabled=False):
    """shadcn Switch. `on_f` is 0..1, so the thumb slides and the track
    cross-fades on the same eased value rather than snapping.

    `focus_f` is `:focus-visible`, eased, and it draws BOTH halves of the
    answer shadcn gives: the 3px `ring/50` band outside the track, and the
    track's own 1px border swapping from `transparent` to `ring`. Measured,
    the band and the border arrive together; drawing only the band leaves the
    control a shade short of the real one at the edge the eye lands on.

    Keyboard only - a switch pressed with the pointer matches `:focus` and
    not `:focus-visible` - which is `interact.switch`'s business, not this
    function's. Both colours come out of `tbl`, never off a token spelled
    here: tokens.SWITCH carries `ring` and `focus_border`.
    """
    from . import box as B
    from .ease import mix
    track, off, onr = B.switch_geom(x, y, size)
    a = 0.5 if disabled else 1.0
    # The default size is 18.390625 px tall, and the browser paints that box
    # snapped to whole pixels while still laying the thumb out off the
    # fraction - so the TRACK snaps and the thumb does not. See draw.snap.
    px, py, pw, ph = snap(track.x, track.y, track.w, track.h)
    if focus_f > 0.01 and not disabled:
        ring(dl, px, py, pw, ph,
             rgba(tbl["ring"][0], tbl["ring"][1] * focus_f, theme=theme),
             ph / 2.0)
    bg = mix(rgba(tbl["off"][0], tbl["off"][1] * a, theme=theme),
             rgba(tbl["on"][0], tbl["on"][1] * a, theme=theme), on_f)
    bcol = mix(rgba(*tbl["border"], theme=theme),
               rgba(*tbl.get("focus_border", tbl["border"]), theme=theme),
               0.0 if disabled else focus_f)
    box(dl, px, py, pw, ph, fill_col=bg, border_col=bcol,
        radius=ph / 2.0, border_w=1.0)
    tx = off.x + (onr.x - off.x) * on_f
    # the thumb's own colour is themed AND state-dependent: in dark it
    # inverts between `foreground` and `primary-foreground`
    tc = mix(rgba(tbl["thumb_off"][0], tbl["thumb_off"][1] * a, theme=theme),
             rgba(tbl["thumb_on"][0], tbl["thumb_on"][1] * a, theme=theme), on_f)
    qx, qy, qw, qh = snap(tx, off.y, off.w, off.h)
    fill(dl, qx, qy, qw, qh, tc, qw / 2.0)
    return track


def kbd_size(s: str, faces, tbl, *, text_w: float | None = None) -> tuple:
    """(w, h) of one shadcn Kbd: `max(min-w-5, text + px-1 twice)` by 20.

    `text_w` overrides the measurement so the law is testable with no font
    atlas, as `comp_button.button_size`'s is. ?probe: "K" and "W" are both
    20 (min-w wins), "Ctrl" 29.203, and the fallback-font "⌘" 20.016 -
    its glyph is 12.016 wide, so min-w loses by a sixty-fourth.
    """
    tw = text_w if text_w is not None else text_w_(s, faces, "medium",
                                                     tbl["font"])
    return max(tbl["min_w"], tw + 2.0 * tbl["pad_x"]), tbl["h"]


def kbd(dl, x, y, s, faces, theme, tbl, *, in_tooltip=False,
        text_w: float | None = None, glyphs: bool = True,
        w: float | None = None) -> float:
    """shadcn Kbd at (x, y). Returns its width.

    The glyphs are centred in the box (`justify-center items-center`);
    measured, a cap glyph's ink sits at y 5..14 of the 20, centroid ~9.6.
    `in_tooltip` is the recipe's `in-data-[slot=tooltip-content]` restyle.
    `glyphs=False` is the gallery's chrome pass: the box with the text not
    drawn, at its intrinsic width, which is the kit's text measure through
    the width law. `w` pins a width instead.
    """
    kw, h = kbd_size(s, faces, tbl, text_w=text_w)
    w = kw if w is None else w
    bg = tbl["tip_bg"] if in_tooltip else tbl["bg"]
    ink = tbl["tip_ink"] if in_tooltip else tbl["ink"]
    # "Ctrl" is 29.203 wide, and the browser paints that box snapped to
    # whole pixels while laying out on the fraction - the README's finding,
    # and draw.switch's. Unsnapped, the right edge is a partial column: 6
    # levels over 4px in dark, the first time this cell was diffed.
    bx, by, bw, bh = snap(x, y, w, h)
    fill(dl, bx, by, bw, bh, rgba(*bg, theme=theme), RADII[tbl["radius"]])
    if glyphs:
        label(dl, x, y, s, faces, "medium", tbl["font"],
              rgba(*ink, theme=theme), align="center", box_w=w,
              baseline_box=h)
    return w


def kbd_sep_w(sep: str, tbl, sep_font: float) -> float:
    """A KbdGroup separator's advance: UA monospace, 0.6em a character -
    see tokens.KBD["group_sep_em"] for why it is monospace at all."""
    return len(sep) * tbl["group_sep_em"] * sep_font


def kbd_group_size(keys, faces, tbl, *, sep: str | None = None,
                   sep_font: float = 14.0, text_w=None) -> tuple:
    """(w, h) of a KbdGroup: the keys `gap-1` apart, with `sep` - plain
    text at the parent's size `sep_font` - between each pair. `text_w` is a
    `(s, variant, size) -> width` measure, for tests."""
    mw = text_w or (lambda t, v, size: text_w_(t, faces, v, size))
    g = tbl["group_gap"]
    ws = [kbd_size(k, faces, tbl, text_w=mw(k, "medium", tbl["font"]))[0]
          for k in keys]
    w = sum(ws) + g * (len(ws) - 1)
    if sep and len(ws) > 1:
        w += (kbd_sep_w(sep, tbl, sep_font) + g) * (len(ws) - 1)
    return w, tbl["h"]


def kbd_group(dl, x, y, keys, faces, theme, tbl, *, sep: str | None = None,
              sep_font: float = 14.0, sep_ink=("foreground", 1.0),
              in_tooltip=False) -> float:
    """shadcn KbdGroup at (x, y): `inline-flex items-center gap-1`.

    ?probe's `Ctrl + B`: the second key at 46.813 = 29.203 + 4 + the "+"
    (9.609, monospace 0.6em at the parent's 16px) + 4. Returns the width.
    """
    g = tbl["group_gap"]
    cx = x
    for i, k in enumerate(keys):
        if i and sep:
            sw = kbd_sep_w(sep, tbl, sep_font)
            label(dl, cx, y, sep, faces, "regular", sep_font,
                  rgba(*sep_ink, theme=theme), align="center", box_w=sw,
                  baseline_box=tbl["h"])
            cx += sw + g
        cx += kbd(dl, cx, y, k, faces, theme, tbl, in_tooltip=in_tooltip) + g
    return cx - g - x


def checkbox(dl, x, y, on_f, tick, theme, tbl, *, focus_f=0.0,
             disabled=False, backdrop=None):
    """shadcn Checkbox's box: fill, border, tick, and the focus ring.

    `on_f` is 0..1 and eases the FILL and BORDER (`transition-colors`, the
    same 150ms curve as everything else). `tick` is a bool and does NOT ease:
    the indicator is `transition-none` and Radix unmounts it when unchecked,
    so measured on ?probe the tick is fully there on the first frame of a
    check, over a fill still at 0-8%, and gone on the first frame of an
    uncheck while the fill fades out. Passing the eased value for both would
    fade a tick the browser snaps.

    `focus_f` is `:focus-visible`, eased, and draws both halves of the
    answer: the 3px `ring/50` band outside the box, and the border swapping
    to `ring` - on a CHECKED box too, where it replaces `primary`.

    `disabled` is `opacity: 0.5` on the whole control, which is a GROUP
    opacity: the tick and the border are composited over the fill FIRST and
    the result is then faded. Halving each colour's alpha instead puts a
    quarter of the fill under the tick - about 58 levels too dark on a light
    page. Doing it exactly needs the colour underneath, so `backdrop` is that
    (opaque) colour; without one they fall back to `draw.field`'s rule. The
    fill is exact either way: a single layer needs no backdrop.
    """
    from .ease import mix, over
    size = tbl["size"]
    bx, by, bw, bh = snap(x, y, size, size)
    r = tbl["radius"]
    if focus_f > 0.01 and not disabled:
        ring(dl, bx, by, bw, bh,
             rgba(tbl["ring"][0], tbl["ring"][1] * focus_f, theme=theme), r)
    fill_c = mix(rgba(*tbl["off_bg"], theme=theme),
                 rgba(*tbl["on_bg"], theme=theme), on_f)
    bord_c = mix(mix(rgba(*tbl["off_border"], theme=theme),
                     rgba(*tbl["on_border"], theme=theme), on_f),
                 rgba(*tbl["focus_border"], theme=theme),
                 0.0 if disabled else focus_f)
    tick_c = rgba(*tbl["tick"], theme=theme)
    a = tbl["disabled_opacity"] if disabled else 1.0

    def faded(top):
        """`top` painted over the fill, then the group faded to `a`."""
        if a >= 1.0:
            return top
        if backdrop is None:
            # draw.field's rule: stack over the fill, then dim. Exact while
            # the fill is transparent; short by a quarter of the fill under
            # an opaque one, which is the case `backdrop` exists for.
            c = over(top, fill_c)
            return (c[0], c[1], c[2], c[3] * a)
        bd = (backdrop[0], backdrop[1], backdrop[2], 1.0)
        return mix(bd, over(top, over(fill_c, bd)), a)

    box(dl, bx, by, bw, bh,
        fill_col=(fill_c[0], fill_c[1], fill_c[2], fill_c[3] * a),
        border_col=faded(bord_c), radius=r, border_w=tbl["border_w"])
    if tick:
        bw_ = tbl["border_w"]
        icon(dl, "check", bx + bw_, by + bw_, tbl["icon"], faded(tick_c))
    return bx, by, bw, bh


def field(dl, x, y, w, h, theme, tbl, *, focus_f=0.0, invalid=False,
          disabled=False, radius=None):
    """The chrome an Input and a Select trigger share: a 1px bordered box
    with a 3px focus ring outside it.

    One function because the two are measured identical apart from height,
    radius and padding - and keeping them one place is what stops the two
    drifting a pixel apart the way the trend badge's three constants did.
    """
    from .ease import mix
    r = RADII[tbl.get("radius", "lg")] if radius is None else radius
    # `disabled:opacity-50` is an opacity on the ELEMENT, so it multiplies the
    # border and the fill alike - on top of a fill that is already themed
    # (input/50 in light, input/80 in dark). Missing this left the whole
    # 200x32 box wrong by 12 levels: the fill was right and the border was
    # twice as dark as it should be.
    from .ease import over
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




def scroll_bar(dl, x, y, w, h, viewport_h, content_h, scroll_y, theme, *,
               alpha=1.0, border=None):
    """Radix's overlay scrollbar: the track is transparent, so this is the
    thumb and nothing else. Returns its Rect, or None with no overflow.

    Shared by `interact.scroll_area` and the gallery, so the thing the diff
    measures is the thing the demo draws.
    """
    from . import box as B
    s = SCROLL
    # `border` is the region's own 1px frame, which the scrollbar sits
    # INSIDE: measured, the viewport is (1,1) 318x198 in a 320x200 root and
    # the bar hangs off the viewport's right edge, not the root's. Pass 0
    # for a region with no border, which is what the dashboard's page is.
    b = s["border"] if border is None else border
    t = B.scroll_thumb(x + w - b - s["bar_w"], y + b, s["bar_w"], h - 2 * b,
                       viewport_h, content_h, scroll_y,
                       inset=s["track_inset"], thumb_w=s["thumb_w"],
                       thumb_inset=s["thumb_inset"], thumb_min=s["thumb_min"])
    if t is None or alpha <= 0.001:
        return t
    fill(dl, *snap(t.x, t.y, t.w, t.h),
         rgba(s["thumb"][0], s["thumb"][1] * alpha, theme=theme),
         s["thumb_w"] / 2.0)
    return t


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
    from .ease import mix
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
