"""A box model: the CSS concepts ImGui has no word for.

Typing pixel offsets by hand produces constants that disagree with each other
(6 + a 14px icon is 20, not 19) and nobody spots that by reading them. The
remedy is to write no constants: measure, then place.

Two pieces, both pure geometry with no imgui in them, so they are unit-
testable the way `ui_players.lay_out` (`ui_players.py:122-176`) is:

* `Rect` — padding, insets, splits, alignment. CSS shorthand order.
* `Flow` — a measured single-line row. Items are collected, then placed, so
  the row knows its own width before it decides where anything goes. That is
  what lets a row be centred, right-aligned, or sized to fit its contents.

This module is a facade. The code lives in three layers that depend strictly
one way, and nothing here is defined, only re-exported, so every `B.x` and
`from box import x` in the kit resolves (`test_module_surface.py` checks each
one):

* `rect.py` - `Rect`, popover placement, and the component geometry that is
  nothing but rectangles (`card_body`, `slider_geom`, `switch_geom`,
  `scroll_thumb`, `stretched_hit`).
* `flex.py` - `Flow`, `Item`, `flex`, `stack`. Needs `Rect`.
* `tree.py` - `Node`, `AUTO`, `measure_tree`, `place_tree`, `lay`,
  `lay_auto`, `wants`. Needs `Rect`, `Item` and `flex`.

The layers' private helpers (`_Cell`, `_dist`, `_pad_wh`) are NOT
re-exported: nothing outside the box model uses them.

Code may import from a layer directly or through this facade.
"""

from __future__ import annotations

from .flex import Flow, Item, flex, stack
from .rect import (
                  Rect,
                  card_body,
                  place_popover,
                  scroll_thumb,
                  slider_geom,
                  stretched_hit,
                  switch_geom,
)
from .tree import AUTO, Node, lay, lay_auto, measure_tree, place_tree, wants

__all__ = [
                  # tree
                  "AUTO",
                  # flex
                  "Flow",
                  "Item",
                  "Node",
                  # rect
                  "Rect",
                  "card_body",
                  "flex",
                  "lay",
                  "lay_auto",
                  "measure_tree",
                  "place_popover",
                  "place_tree",
                  "scroll_thumb",
                  "slider_geom",
                  "stack",
                  "stretched_hit",
                  "switch_geom",
                  "wants",
]
