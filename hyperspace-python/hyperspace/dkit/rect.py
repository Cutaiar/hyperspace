"""Rectangles, and the component geometry that is nothing but rectangles.

The bottom layer of the box model: nothing here depends on anything else in
the kit's layout code. `flex.py` builds on `Rect`, and `tree.py` builds on
both. `box.py` re-exports all three, so `B.Rect` and `from box import Rect`
keep working - see `HANDOFF.md` item 3a.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    def pad(self, *v) -> Rect:
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

    def expand(self, n: float) -> Rect:
        return Rect(self.x - n, self.y - n, self.w + 2 * n, self.h + 2 * n)

    # -- splitting --------------------------------------------------------
    def cut_left(self, w: float) -> tuple[Rect, Rect]:
        w = min(w, self.w)
        return (Rect(self.x, self.y, w, self.h),
                Rect(self.x + w, self.y, self.w - w, self.h))

    def cut_right(self, w: float) -> tuple[Rect, Rect]:
        w = min(w, self.w)
        return (Rect(self.right - w, self.y, w, self.h),
                Rect(self.x, self.y, self.w - w, self.h))

    def cut_top(self, h: float) -> tuple[Rect, Rect]:
        h = min(h, self.h)
        return (Rect(self.x, self.y, self.w, h),
                Rect(self.x, self.y + h, self.w, self.h - h))

    def cut_bottom(self, h: float) -> tuple[Rect, Rect]:
        h = min(h, self.h)
        return (Rect(self.x, self.bottom - h, self.w, h),
                Rect(self.x, self.y, self.w, self.h - h))

    # -- placing ----------------------------------------------------------
    def align(self, w: float, h: float, ax: str = "center",
              ay: str = "center") -> Rect:
        """A w x h box placed inside this one."""
        x = {"start": self.x, "center": self.x + (self.w - w) / 2.0,
             "end": self.right - w}[ax]
        y = {"start": self.y, "center": self.y + (self.h - h) / 2.0,
             "end": self.bottom - h}[ay]
        return Rect(x, y, w, h)

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px < self.right and self.y <= py < self.bottom


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
    from .tokens import CARD_PAD, card_body_y
    top = card_body_y(card.y, description=description)
    return Rect(card.x + CARD_PAD, top,
                card.w - 2 * CARD_PAD,
                card.y + card.h - CARD_PAD - top)


def slider_geom(x, y, w, h, fracs, *, track_h=4.0, thumb=12.0, origin=0.0):
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

    `origin` is where a SINGLE thumb's range starts, as a fraction: 0, the
    left end, is shadcn's and the default. Hyperspace fills a bipolar param
    (yaw, pan: `lo < 0 < hi`) from its zero (`ui.Panel._origin`), so a port
    passes that; the range then runs from whichever of the two is lower.
    Ignored for a range slider, whose two thumbs ARE the ends.
    """
    fs = sorted(fracs if isinstance(fracs, (list, tuple)) else [fracs])
    track = Rect(x, y + (h - track_h) / 2.0, w, track_h)
    if len(fs) > 1:
        lo, hi = fs[0], fs[-1]
    else:
        lo, hi = min(origin, fs[0]), max(origin, fs[0])
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
    from .tokens import SWITCH_SIZES
    name = size[0] if isinstance(size, (list, tuple)) else size
    w, h, th = SWITCH_SIZES[name]
    track = Rect(x, y, w, h)
    cw, ch = w - 2.0, h - 2.0                       # inside the 1px border
    ty = y + 1.0 + (ch - th) / 2.0
    return track, Rect(x + 1.0, ty, th, th), Rect(x + 1.0 + (cw - th), ty, th, th)


def scroll_thumb(bar_x, bar_y, bar_w, bar_h, viewport_h, content_h, scroll_y,
                 *, inset=1.0, thumb_w=7.0, thumb_inset=2.0, thumb_min=18.0):
    """Where a Radix scrollbar's thumb goes. Pure geometry, no imgui.

    Measured on ?probe rather than reasoned about:

        track       = the scrollbar less `inset` at each end
        thumb h     = max(thumb_min, viewport / content * track)
        thumb y     = track_y + frac * (track - thumb)

    `thumb_min` is a real floor, not rounding: at a 198px viewport the ideal
    thumb goes 97.0, 32.3, 12.9, 4.9, 1.3 as the content grows and the
    rendered one stops at 18.

    Returns None when there is nothing to scroll, which is what the browser
    does too - a scrollbar with no overflow is not drawn at all.
    """
    if content_h <= viewport_h + 0.5 or viewport_h <= 0:
        return None
    track_y = bar_y + inset
    track_h = bar_h - 2 * inset
    if track_h <= 0:
        return None
    th = max(thumb_min, viewport_h / content_h * track_h)
    th = min(th, track_h)
    span = max(content_h - viewport_h, 1e-6)
    frac = min(max(scroll_y / span, 0.0), 1.0)
    return Rect(bar_x + thumb_inset, track_y + frac * (track_h - th),
                thumb_w, th)


def stretched_hit(x, y, w, h, *, stretch=(12.0, 8.0), border=1.0) -> Rect:
    """The pointer target of a control carrying `after:-inset-x-N -inset-y-M`.

    Pure geometry. An absolutely positioned `::after` is laid out against
    its containing block's PADDING box, one `border` inside the border box,
    so `-inset-x-3` (12px) reaches 11px past a 1px-bordered control's edge,
    not 12. Measured on ?probe both ways - real clicks, and the pseudo
    element's computed size (38 x 30 around a 16px Checkbox, 54 x 32.39
    around a 32 x 18.39 Switch).

    `stretch` is the CSS insets, `tokens.HIT_STRETCH`.
    """
    sx, sy = stretch[0] - border, stretch[1] - border
    return Rect(x - sx, y - sy, w + 2.0 * sx, h + 2.0 * sy)
