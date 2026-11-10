"""The Combobox's intrinsic size, through the layout tree. Pure, no imgui.

`combobox_size` and `list_content_h` both measure the same `_rows_node`
tree, so the size the popup reserves and the content height its ScrollArea
is told cannot disagree (RETRO row 22). Moved out of `comp_combobox.py` by
`HANDOFF.md` item 3c, which re-exports both.
"""

from __future__ import annotations

from . import box as B
from . import draw as D
from .combobox_items import _is_row, _k
from .combobox_tokens import combobox_table

# --------------------------------------------------------------------------
# intrinsic size, through the layout tree
# --------------------------------------------------------------------------

def _rows_node(items, mw, tbl, *, empty: str = "") -> B.Node:
    """The CommandList's content, as a `box.Node` column.

    Every row carries a `key`, so `box.place_tree` hands its rect straight
    back — which is the whole reason to build a tree instead of adding up
    offsets, the failure `box.py` exists to stop.

    `mw(text, variant, size) -> width` measures text.
    """
    pad = tbl["group_pad"]
    kids: list[B.Node] = []
    group: list[B.Node] | None = None       # the open group's rows

    def open_group() -> list[B.Node]:
        nonlocal group
        group = []
        kids.append(B.Node(dir="column", pad=(pad, pad, pad, pad), kids=group))
        return group

    for i, it in enumerate(items):
        kind = _k(it, "kind", "item")
        if kind == "sep":
            # `-mx-1`: a separator is a child of the LIST and reaches out
            # past a group's padding, so it does not live inside a group.
            group = None
            # `my-1` is 4 above and 4 below, so the block is 9 tall and the
            # 1px rule is centred in it - measured; see `sep_my`.
            kids.append(B.Node(h=tbl["sep_h"] + 2 * tbl["sep_my"],
                               key=("sep", i)))
            continue
        if kind == "label":
            g = open_group()
            tw = mw(_k(it, "label", ""), tbl["head_weight"],
                    tbl["head_font"]) + 2 * tbl["head_pad_x"]
            g.append(B.Node(h=tbl["head_h"], key=("row", i),
                                 measure=lambda w=tw: (w, tbl["head_h"])))
            continue
        g = group if group is not None else open_group()
        lead = ((tbl["field_icon"] + tbl["row_gap"])
                if _k(it, "icon", "") else 0.0)
        tw = (mw(_k(it, "label", ""), "regular", tbl["item_font"]) + lead
              + tbl["row_pad_x"] + tbl["row_pad_r"])
        g.append(B.Node(h=tbl["item_h"], key=("row", i),
                             measure=lambda w=tw: (w, tbl["item_h"])))

    if not any(_is_row(it) for it in items):
        # CommandEmpty is a child of the LIST, not of a group: measured at
        # the list's own width, with no 4px inset.
        tw = mw(empty, "regular", tbl["empty_font"]) if empty else 0.0
        kids.append(B.Node(h=tbl["empty_h"], key=("empty", 0),
                           measure=lambda w=tw: (w, tbl["empty_h"])))
    return B.Node(dir="column", kids=kids, key="list")


def combobox_size(items, faces, *, min_w: float = 0.0, measure=None,
                  theme_name: str = "light", empty: str = "") -> tuple:
    """The panel's intrinsic (w, h), from its contents.

    `box.wants` does the arithmetic; nothing here types a height. The one
    thing that is not a sum is the list's `max-h-72` (288), which is a real
    clamp in the class and is applied as one.

    `measure(text, variant, size) -> width` is injectable, so this is
    testable with no GL and no display the way `box.Node.measure` already
    is; left out, it goes through `draw.text_w` with `faces`.

    The search field contributes no width: it is `w-full`, and measured, the
    220px panel's width came entirely from the recipe's `w-[220px]` with the
    field stretching to fill it.
    """
    tbl = combobox_table(theme_name)
    mw = measure or (lambda s, v, size: D.text_w(s, faces, v, size))
    cw, ch = B.wants(_rows_node(items, mw, tbl, empty=empty))
    pad = tbl["pad"]
    # NO search field. The panel is the list and the list's padding, because
    # the field IS the trigger — that is the whole shape of the real Base UI
    # component. This function went on reserving `field_h + field_pad` after
    # `combobox()` stopped drawing one, so the panel it predicted was 36 px
    # taller than the panel the widget drew. Nothing caught it until a test
    # asked both halves the same question.
    # `data-empty:p-0` on the list: with nothing to show, the panel IS the
    # empty block - 36 tall, no 4px rails. Measured.
    if not any(_is_row(it) for it in items):
        pad = 0.0
    # the clamp is the PANEL's, so the rows get it less the rails - see
    # `list_max_h`
    panel = B.Node(dir="column", pad=(pad, pad, pad, pad), kids=[
        B.Node(w=cw, h=min(ch, tbl["list_max_h"] - 2 * pad)),
    ])
    w, h = B.wants(panel)
    return max(w, min_w), h


def list_content_h(items, tbl) -> float:
    """How tall the list's CONTENT is, which is what a ScrollArea has to be
    told. The same tree, measured with a zero text width — none of the
    heights in it depend on any text."""
    return B.wants(_rows_node(items, lambda *a: 0.0, tbl, empty="x"))[1]
