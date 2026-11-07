"""The layout tree: intrinsic sizing, measured bottom-up then placed top-down.

The top layer of the box model: built on `rect.Rect` and `flex.flex`.
Re-exported by `box.py` - see `HANDOFF.md` item 3a.
"""

from __future__ import annotations

from dataclasses import dataclass

from flex import Item, flex
from rect import Rect


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
