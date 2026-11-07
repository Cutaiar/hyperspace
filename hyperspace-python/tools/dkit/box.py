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

Since `HANDOFF.md` item 3a this module is a FACADE. The code lives in three
layers that depend strictly one way, and nothing here is defined, only
re-exported, so every `B.x` and `from box import x` in the kit still
resolves (`test_module_surface.py` checks each one):

* `rect.py` - `Rect`, popover placement, and the component geometry that is
  nothing but rectangles (`card_body`, `slider_geom`, `switch_geom`,
  `scroll_thumb`).
* `flex.py` - `Flow`, `Item`, `flex`, `stack`. Needs `Rect`.
* `tree.py` - `Node`, `AUTO`, `measure_tree`, `place_tree`, `lay`,
  `lay_auto`, `wants`. Needs `Rect`, `Item` and `flex`.

The layers' private helpers (`_Cell`, `_dist`, `_pad_wh`) are NOT
re-exported: nothing outside the box model used them, so they moved freely.

New code may import from the layer directly; there is no need to rewrite the
existing call sites, and doing so is churn rather than a fix.
"""

from __future__ import annotations

from rect import (Rect, card_body, place_popover, scroll_thumb, slider_geom,
                  switch_geom)
from flex import Flow, Item, flex, stack
from tree import (AUTO, Node, lay, lay_auto, measure_tree, place_tree,
                  wants)

__all__ = [
    # rect
    "Rect", "place_popover", "card_body", "slider_geom", "switch_geom",
    "scroll_thumb",
    # flex
    "Flow", "Item", "flex", "stack",
    # tree
    "AUTO", "Node", "measure_tree", "place_tree", "lay", "lay_auto", "wants",
]
