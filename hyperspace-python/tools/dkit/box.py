"""A box model: the CSS concepts ImGui has no word for.

Without this the kit degenerates into typing pixel offsets, which is how the
trend badge ended up with `+26`, `+6` and `+19` in it — three constants that
do not agree with each other (6 + a 14px icon is 20, not 19, so the label
overlapped the icon by a pixel, and the icon sat a pixel above centre).
Nobody spots that by reading it. The fix is not better constants, it is not
writing constants.

Two pieces, both pure geometry with no imgui in them, so they are unit-
testable the way `ui_players.lay_out` (`ui_players.py:122-176`) is:

* `Rect` — padding, insets, splits, alignment. CSS shorthand order.
* `Flow` — a measured single-line row. Items are collected, then placed, so
  the row knows its own width before it decides where anything goes. That is
  what lets a row be centred, right-aligned, or sized to fit its contents.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rect:
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0

    # -- derived ----------------------------------------------------------
    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def as_tuple(self) -> tuple:
        return (self.x, self.y, self.w, self.h)

    # -- padding ----------------------------------------------------------
    def pad(self, *v) -> "Rect":
        """Shrink by padding, in CSS shorthand order.

        pad(a)          all sides
        pad(v, h)       vertical, horizontal
        pad(t, h, b)    top, horizontal, bottom
        pad(t, r, b, l)
        """
        if len(v) == 1:
            t = r = b = ll = v[0]
        elif len(v) == 2:
            t = b = v[0]
            r = ll = v[1]
        elif len(v) == 3:
            t, r, b = v
            ll = r
        elif len(v) == 4:
            t, r, b, ll = v
        else:
            raise ValueError("pad takes 1 to 4 values, like CSS")
        return Rect(self.x + ll, self.y + t,
                    max(self.w - ll - r, 0.0), max(self.h - t - b, 0.0))

    def expand(self, n: float) -> "Rect":
        return Rect(self.x - n, self.y - n, self.w + 2 * n, self.h + 2 * n)

    # -- splitting --------------------------------------------------------
    def cut_left(self, w: float) -> tuple["Rect", "Rect"]:
        w = min(w, self.w)
        return (Rect(self.x, self.y, w, self.h),
                Rect(self.x + w, self.y, self.w - w, self.h))

    def cut_right(self, w: float) -> tuple["Rect", "Rect"]:
        w = min(w, self.w)
        return (Rect(self.right - w, self.y, w, self.h),
                Rect(self.x, self.y, self.w - w, self.h))

    def cut_top(self, h: float) -> tuple["Rect", "Rect"]:
        h = min(h, self.h)
        return (Rect(self.x, self.y, self.w, h),
                Rect(self.x, self.y + h, self.w, self.h - h))

    def cut_bottom(self, h: float) -> tuple["Rect", "Rect"]:
        h = min(h, self.h)
        return (Rect(self.x, self.bottom - h, self.w, h),
                Rect(self.x, self.y, self.w, self.h - h))

    # -- placing ----------------------------------------------------------
    def align(self, w: float, h: float, ax: str = "center",
              ay: str = "center") -> "Rect":
        """A w x h box placed inside this one."""
        x = {"start": self.x, "center": self.x + (self.w - w) / 2.0,
             "end": self.right - w}[ax]
        y = {"start": self.y, "center": self.y + (self.h - h) / 2.0,
             "end": self.bottom - h}[ay]
        return Rect(x, y, w, h)

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px < self.right and self.y <= py < self.bottom


# --------------------------------------------------------------------------
# a measured single-line row
# --------------------------------------------------------------------------

@dataclass
class _Cell:
    w: float
    h: float
    kind: str
    payload: tuple = ()


@dataclass
class Flow:
    """Collect items, measure, then place — in that order.

    The two-pass shape is the point: `width()` is answerable before anything
    is drawn, so a row can size a pill to its contents or centre itself in a
    box it did not choose.
    """
    gap: float = 0.0
    items: list = field(default_factory=list)

    def icon(self, name: str, size: float) -> "Flow":
        self.items.append(_Cell(size, size, "icon", (name,)))
        return self

    def text(self, s: str, w: float, h: float, variant: str = "regular",
             size: float = 14.0, tabular: bool = False) -> "Flow":
        self.items.append(_Cell(w, h, "text", (s, variant, size, tabular)))
        return self

    def space(self, w: float) -> "Flow":
        self.items.append(_Cell(w, 0.0, "space"))
        return self

    def width(self) -> float:
        if not self.items:
            return 0.0
        return sum(i.w for i in self.items) + self.gap * (len(self.items) - 1)

    def height(self) -> float:
        return max((i.h for i in self.items), default=0.0)

    def place(self, into: Rect, ax: str = "start",
              ay: str = "center") -> list[tuple[_Cell, Rect]]:
        """Lay the row out inside `into`. Returns (cell, rect) pairs."""
        row = into.align(self.width(), self.height(), ax, ay)
        out, cx = [], row.x
        for it in self.items:
            r = Rect(cx, row.y + (row.h - it.h) / 2.0, it.w, it.h)
            out.append((it, r))
            cx += it.w + self.gap
        return out


# --------------------------------------------------------------------------
# popover placement
# --------------------------------------------------------------------------

def place_popover(anchor: Rect, w: float, h: float, avail: Rect, *,
                  side: str = "bottom", align: str = "end",
                  offset: float = 4.0, pad: float = 8.0) -> tuple:
    """Where a popover goes, anchored to its trigger. Returns (Rect, side).

    This is Radix's model, which shadcn uses: the panel is placed on `side`
    of the ANCHOR — not at the mouse — offset by `sideOffset`, aligned along
    the cross axis, then

      * **flipped** to the opposite side if it would not fit, and
      * **shifted** along the cross axis to stay inside the viewport.

    Mouse-positioned popups are what ImGui does by default and it reads wrong
    for a row action: the panel should hang off the control, so it lands in
    the same place however you arrived at the button.
    """
    def across(sd: str) -> float:
        if sd == "bottom":
            return anchor.bottom + offset
        if sd == "top":
            return anchor.y - offset - h
        return 0.0

    if side in ("bottom", "top"):
        y = across(side)
        flipped = {"bottom": "top", "top": "bottom"}[side]
        if y < avail.y + pad or y + h > avail.bottom - pad:
            alt = across(flipped)
            if avail.y + pad <= alt and alt + h <= avail.bottom - pad:
                side, y = flipped, alt
        x = {"start": anchor.x, "center": anchor.cx - w / 2.0,
             "end": anchor.right - w}[align]
    else:
        x = anchor.right + offset if side == "right" else anchor.x - offset - w
        flipped = "left" if side == "right" else "right"
        if x < avail.x + pad or x + w > avail.right - pad:
            alt = anchor.x - offset - w if side == "right" else anchor.right + offset
            if avail.x + pad <= alt and alt + w <= avail.right - pad:
                side, x = flipped, alt
        y = {"start": anchor.y, "center": anchor.cy - h / 2.0,
             "end": anchor.bottom - h}[align]

    # shift back inside, after flipping; clamping low last means a panel
    # taller than the viewport pins to the top rather than the bottom
    x = min(x, avail.right - pad - w)
    x = max(x, avail.x + pad)
    y = min(y, avail.bottom - pad - h)
    y = max(y, avail.y + pad)
    return Rect(x, y, w, h), side


# --------------------------------------------------------------------------
# flex
# --------------------------------------------------------------------------

@dataclass
class Item:
    """One flex child. `w`/`h` are the content size; None means 'auto',
    which on the cross axis stretches and on the main axis starts at 0."""
    w: float | None = None
    h: float | None = None
    grow: float = 0.0
    shrink: float = 1.0
    align: str | None = None        # align-self
    key: object = None


def _dist(free, items, base, grow: bool):
    """Hand out `free` main-axis space. CSS scales the SHRINK factor by the
    item's base size (so a bigger item gives up more) but does NOT scale
    grow. Getting that backwards is the classic flex bug — the oracle case
    `shrink.weighted` pins it: 120px holding two 80px items at shrink 1 and
    3 resolves to 70 and 50, not 65 and 55."""
    if not items:
        return [0.0] * len(base)
    fac = [(i.grow if grow else i.shrink * b) for i, b in zip(items, base)]
    total = sum(fac)
    if total <= 0:
        return [0.0] * len(base)
    return [free * f / total for f in fac]


def flex(container: Rect, items, *, direction: str = "row", gap: float = 0.0,
         justify: str = "start", align: str = "stretch",
         pad=(0, 0, 0, 0)) -> list[Rect]:
    """CSS flexbox for one line. Returns a Rect per item, in order.

    A pure function of (container, items, options) — so it is cacheable on
    the container's size and never needs to run per frame. That matters:
    Taffy's Python bindings cost 1.4-2.3ms a frame for 180 boxes, which is
    ~10% of a 16.7ms budget. This is arithmetic.

    Conformance is measured, not assumed: `flex_oracle.js` lays the same
    cases out in Chromium and `test_flex.py` asserts agreement.

    Supported: direction, gap, justify (start/center/end/between/around/
    evenly), align (start/center/end/stretch) plus per-item align-self,
    grow, shrink, padding. Not supported: wrap, order, baseline alignment.
    """
    inner = container.pad(*pad) if any(pad) else container
    row = direction == "row"
    main_size = inner.w if row else inner.h
    cross_size = inner.h if row else inner.w
    n = len(items)
    if n == 0:
        return []

    base = [((it.w if row else it.h) or 0.0) for it in items]
    used = sum(base) + gap * (n - 1)
    free = main_size - used
    if free > 0:
        base = [b + d for b, d in zip(base, _dist(free, items, base, True))]
    elif free < 0:
        base = [max(b + d, 0.0)
                for b, d in zip(base, _dist(free, items, base, False))]
    used = sum(base) + gap * (n - 1)
    slack = max(main_size - used, 0.0)

    # justify: where the line starts, and how much goes between items
    lead, between = 0.0, gap
    if justify in ("center",):
        lead = slack / 2.0
    elif justify in ("end", "flex-end"):
        lead = slack
    elif justify == "space-between":
        between = gap + (slack / (n - 1) if n > 1 else 0.0)
    elif justify == "space-around":
        each = slack / n if n else 0.0
        lead, between = each / 2.0, gap + each
    elif justify == "space-evenly":
        each = slack / (n + 1) if n else 0.0
        lead, between = each, gap + each

    out, at = [], lead
    for it, b in zip(items, base):
        a = it.align or align
        other = (it.h if row else it.w)
        if a == "stretch" and other is None:
            c_size, c_at = cross_size, 0.0
        else:
            c_size = other if other is not None else cross_size
            if a in ("center",):
                c_at = (cross_size - c_size) / 2.0
            elif a in ("end", "flex-end"):
                c_at = cross_size - c_size
            else:                                   # start / stretch-with-size
                c_at = 0.0
        if row:
            out.append(Rect(inner.x + at, inner.y + c_at, b, c_size))
        else:
            out.append(Rect(inner.x + c_at, inner.y + at, c_size, b))
        at += b + between
    return out


# --------------------------------------------------------------------------
# component geometry, measured against Radix
# --------------------------------------------------------------------------
#
# Pure width -> rects, no imgui, so these are unit-tested the way
# ui_players.lay_out (ui_players.py:122-176) is. Every law here was read off
# tools/dkit/probe_react.js rather than derived from the Tailwind classes,
# and two of them are not what the classes suggest.

def card_body(card, *, description: bool = True):
    """A Card's content box: inside its padding and below its header.

    Both numbers come from tokens, which measured them off a real shadcn
    Card - 16px of padding, a 22px title, a 4px gap, a 20px description, 16
    to the content. Written out by hand in the demo they came to +14, +34
    and +52, three constants that did not agree with the component.
    """
    from tokens import CARD_PAD, card_body_y
    top = card_body_y(card.y, description=description)
    return Rect(card.x + CARD_PAD, top,
                card.w - 2 * CARD_PAD,
                card.y + card.h - CARD_PAD - top)


def stack(box, n, item_h, *, gap=8.0):
    """`n` rows of `item_h` down `box`, `gap` apart. The vertical Flow.

    A thin wrapper over flex, and it exists because the demo kept writing
    `y + i * pitch` instead - which is how a 24px control ended up on a 27px
    pitch with a 3px gutter, and why the card read cramped.
    """
    # shrink=0: a stack that overflows its box must overflow, not quietly
    # compress every row. Flex's default shrink is 1, which silently turned
    # 24px rows into 16.5px ones the first time this was written.
    return flex(box, [Item(h=item_h, shrink=0.0) for _ in range(n)],
                direction="column", gap=gap)


def slider_geom(x, y, w, h, fracs, *, track_h=4.0, thumb=12.0):
    """(track, range, [thumb, ...]) for a slider, in CSS pixels.

    The measured law, and the surprise in it: the range and the thumb do NOT
    share a mapping.

        range  x = f_lo * W,  width = (f_hi - f_lo) * W      <- edge to edge
        thumb  left = f * (W - thumb)                        <- inset by itself

    So they agree only at f = 0.5. At 25% on a 240px track the range ends at
    60 while the thumb's centre sits at 63; at 100% the range reaches 240 and
    the thumb's centre stops at 234. Radix insets the thumb so it can never
    overhang the track, and does not inset the range to match. Reproducing
    one law for both - which is what reading the classes gets you - puts the
    thumb up to half its own width away from the end of its own fill.

    `fracs` is one fraction for a single thumb, or two for a range. The track
    is centred vertically in (y, h), which is what `items-center` does.
    """
    fs = sorted(fracs if isinstance(fracs, (list, tuple)) else [fracs])
    track = Rect(x, y + (h - track_h) / 2.0, w, track_h)
    lo = fs[0] if len(fs) > 1 else 0.0
    hi = fs[-1]
    rng = Rect(x + lo * w, track.y, (hi - lo) * w, track_h)
    span = max(w - thumb, 0.0)
    thumbs = [Rect(x + f * span, y + (h - thumb) / 2.0, thumb, thumb)
              for f in fs]
    return track, rng, thumbs


def switch_geom(x, y, size=("default",)):
    """(track, thumb_off, thumb_on) for a switch, in CSS pixels.

    The track carries a 1px border, so the thumb lives in the content box:
    inset 1 from the left, centred in the remaining height, and travelling
    (content width - thumb width). For the default size that content box is
    16.390625 tall against a 16px thumb, which is why the thumb sits at
    y + 1.195 rather than at a whole pixel.
    """
    from tokens import SWITCH_SIZES
    name = size[0] if isinstance(size, (list, tuple)) else size
    w, h, th = SWITCH_SIZES[name]
    track = Rect(x, y, w, h)
    cw, ch = w - 2.0, h - 2.0                       # inside the 1px border
    ty = y + 1.0 + (ch - th) / 2.0
    return track, Rect(x + 1.0, ty, th, th), Rect(x + 1.0 + (cw - th), ty, th, th)


# --------------------------------------------------------------------------
# the layout tree: intrinsic sizing, measured then placed
# --------------------------------------------------------------------------
#
# `flex` above is ONE line placed into a box whose size the caller already
# knew. That is half a layout engine, and the missing half is the reason the
# demo kept typing numbers: the bands card is 258 px tall because somebody
# measured a picture and wrote 258, and adding a seventh row to it does not
# make it grow. CSS calls the fix `height: auto`, and it is two passes -
# measure the tree bottom-up to learn what each subtree WANTS, then place it
# top-down to hand out what there actually is.
#
# The ROADMAP rejected Taffy and Yoga for this, and was right to: their
# Python bindings cost 1.4-6.0 ms a frame because every box has to be read
# back across the FFI boundary. But that is an argument against an ENGINE,
# not against intrinsic sizing. Measured here, in pure Python:
#
#     207 nodes  (this dashboard)      0.099 ms      0.6% of a frame
#     487 nodes  (a longer table)      0.229 ms      1.4%
#     955 nodes  (a 600-param panel)   0.381 ms      2.3%
#     200 text measurements            0.029 ms      0.2%
#
# ~15x faster than Taffy at the same node count, because the arithmetic is
# slower per operation and never crosses a boundary. So this can run every
# frame, uncached, and still leave 97% of the budget - which means layout can
# depend on content, which is the thing that makes dynamic UI possible at
# all.
#
# Conformance is measured, not assumed: nest_oracle.js lays the same trees
# out in Chromium and test_nest.py asserts agreement, exactly as flex is.

AUTO = None          # a size that comes from the content


@dataclass
class Node:
    """One box in a layout tree.

    `w` / `h` are content-box sizes; AUTO means "ask the content" - the sum
    of the children along the main axis, the largest of them across it, plus
    padding. A leaf with a `measure` hook reports its own size, which is how
    a Badge comes out as its text plus padding and a Switch as 32 x 18.390625.
    """
    w: float | None = AUTO
    h: float | None = AUTO
    dir: str = "column"
    gap: float = 0.0
    pad: tuple = (0.0, 0.0, 0.0, 0.0)      # CSS shorthand order
    grow: float = 0.0
    shrink: float = 1.0
    # The main-axis starting size. AUTO means "my measured size", which is
    # CSS's `flex-basis: auto`; 0 is its `flex-basis: 0`, i.e. `flex-1`.
    # The difference is not cosmetic: two cards that both grow but carry
    # different content come out DIFFERENT widths on an auto basis, because
    # grow only hands out what is left over. Equal halves need basis 0.
    basis: float | None = AUTO
    justify: str = "start"
    align: str = "stretch"
    align_self: str | None = None
    kids: tuple = ()
    measure: object = None                  # () -> (w, h), for a leaf
    key: object = None                      # what place() keys its rect by
    # filled in by the passes
    mw: float = 0.0
    mh: float = 0.0


def _pad_wh(pad):
    t, r, b, l = pad
    return l + r, t + b


def measure_tree(node: Node) -> tuple:
    """Bottom-up: the size each subtree wants. Returns (w, h).

    Pure arithmetic over the tree, and it writes `mw`/`mh` on every node so
    `place_tree` can read them without a second walk.
    """
    pw, ph = _pad_wh(node.pad)
    if not node.kids:
        if node.measure is not None:
            w, h = node.measure()
        else:
            w, h = 0.0, 0.0
        node.mw = node.w if node.w is not AUTO else w + pw
        node.mh = node.h if node.h is not AUTO else h + ph
        return node.mw, node.mh

    row = node.dir == "row"
    main = cross = 0.0
    for k in node.kids:
        kw, kh = measure_tree(k)
        if row:
            main += kw
            cross = max(cross, kh)
        else:
            main += kh
            cross = max(cross, kw)
    main += node.gap * (len(node.kids) - 1)

    if row:
        iw, ih = main, cross
    else:
        iw, ih = cross, main
    node.mw = node.w if node.w is not AUTO else iw + pw
    node.mh = node.h if node.h is not AUTO else ih + ph
    return node.mw, node.mh


def place_tree(node: Node, rect: Rect, out: dict | None = None) -> dict:
    """Top-down: hand out the space `rect`, recursively. Returns key -> Rect.

    Distribution reuses `flex`, so a nested line resolves exactly the way the
    27 single-line cases already measured against Chromium do - rather than a
    second implementation that agrees with the first until it does not.
    """
    if out is None:
        out = {}
    if node.key is not None:
        out[node.key] = rect
    if not node.kids:
        return out

    # The cross axis goes in as None when the child's own size is AUTO, so
    # `align-items: stretch` fills the line - which is what CSS does with an
    # auto cross size, and what `flex` keys its stretch branch off. Passing
    # the MEASURED cross size instead silently opts every child out of
    # stretch: a column of rows came back 0 px wide.
    row = node.dir == "row"
    items = []
    for k in node.kids:
        auto_cross = (k.h if row else k.w) is AUTO
        main = k.mw if row else k.mh
        if k.basis is not AUTO:
            main = k.basis
        cross = None if auto_cross else (k.mh if row else k.mw)
        items.append(Item(
            w=main if row else cross,
            h=cross if row else main,
            grow=k.grow, shrink=k.shrink, align=k.align_self))
    rects = flex(rect, items, direction=node.dir, gap=node.gap,
                 justify=node.justify, align=node.align, pad=node.pad)
    for k, r in zip(node.kids, rects):
        place_tree(k, r, out)
    return out


def lay(root: Node, rect: Rect) -> dict:
    """Measure then place. The whole engine, as one call."""
    measure_tree(root)
    return place_tree(root, rect)


def lay_auto(root: Node, x: float, y: float, w: float,
             h: float | None = None) -> dict:
    """Measure, then place at the width given and the height the content
    wants. The usual call: a window hands down a width, the content decides
    its own height.

    It exists because `lay(root, Rect(x, y, w, root.mh))` reads `mh` BEFORE
    anything has measured it - it is 0 until the pass runs - so the tree gets
    placed into a zero-height box and every child shrinks to nothing. That is
    a trap worth closing with an API rather than a docstring.
    """
    mw, mh = measure_tree(root)
    return place_tree(root, Rect(x, y, w, mh if h is None else h))


def wants(root: Node) -> tuple:
    """The size a tree wants, without placing it - what a ScrollArea needs
    to know whether its content overflows, and what `height: auto` means."""
    return measure_tree(root)
