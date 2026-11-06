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
