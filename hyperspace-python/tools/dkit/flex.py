"""A measured single-line row (`Flow`) and CSS flexbox on one line (`flex`).

The middle layer of the box model: built on `rect.Rect`, and built on by
`tree.py`. Re-exported by `box.py` - see `HANDOFF.md` item 3a.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rect import Rect


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
