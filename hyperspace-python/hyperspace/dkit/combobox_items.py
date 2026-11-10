"""The Combobox's items, and the filter over them. Pure, no imgui.

`Item`, `heading` and `sep` are the row model; `filter_items` is Base UI's
plain case-insensitive substring match. Moved out of `comp_combobox.py` by
`HANDOFF.md` item 3c. `comp_command.py` imports from HERE - including the
two private helpers `_k` and `_is_row`, which `test_module_surface.py`
keeps on its ledger of names crossing a module boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------
# items
# --------------------------------------------------------------------------

@dataclass
class Item:
    """One row. `kind` is item | label | sep, as `menu.Item`'s is.

    A `menu.Item` is accepted anywhere this is: every field below is read
    through `getattr` with a default, so the two are interchangeable and a
    caller already holding menu rows does not have to convert them.
    """
    id: str = ""
    label: str = ""
    icon: str = ""
    kind: str = "item"
    # cmdk scores `value + " " + keywords.join(" ")`, so a keyword is a
    # second spelling a row can be found by.
    keywords: tuple = ()
    enabled: bool = True
    # None means "work it out from the trigger's current label", which is
    # what the recipe does with `value === item.value`.
    checked: bool | None = None


def heading(text: str) -> Item:
    """A CommandGroup heading. It also OPENS a group: the rows after it are
    ranked among themselves and the group travels as a block, which is what
    cmdk does — it sorts groups by their best row's score."""
    return Item(kind="label", label=text)


def sep() -> Item:
    """A CommandSeparator. cmdk renders one only while the search box is
    EMPTY (`alwaysRender` aside) — read out of cmdk 1.1.1's own source — so
    `filter_items` drops separators as soon as there is a query."""
    return Item(kind="sep")


def _k(it, name, default):
    return getattr(it, name, default)


def _is_row(it) -> bool:
    return _k(it, "kind", "item") == "item"


# --------------------------------------------------------------------------
# the filter — pure, no imgui
# --------------------------------------------------------------------------
#
# A plain case-insensitive SUBSTRING match, which is what Base UI's Combobox
# uses. The kit once shipped cmdk's `commandScore` here, because the premise
# was that a Combobox is Popover + Command; it is not. That port was exact -
# verified against the shipped JavaScript over 382 pairs - and it was the
# wrong rule, which is RETRO row 3. It now lives in `comp_command.py`, where
# it is the right one.


_SPACE = frozenset(" \t\n\r-")


def _fold(t: str) -> str:
    """Lowercase, with whitespace and hyphens folded to a space.

    The Combobox's own, deliberately not shared with `comp_command`'s
    identical-looking one. They answer to different components: this folds
    for Base UI's `contains`, that one is a line of cmdk's `formatInput`.
    If cmdk ever changes its folding, this must not follow it.
    """
    return "".join(" " if c in _SPACE else c for c in t.lower())


def filter_items(items, query: str) -> list:
    """Base UI's filter: SUBSTRING, case-insensitive, author's order kept.

    This is what the real `combobox.tsx` does, and it is not what the kit
    first shipped. Measured by typing into the component and reading its
    rows back:

        "dodec" -> Dodecahedron, Great Dodecahedron
        "DODEC" -> the same two               (case-insensitive)
        "ant"   -> Grand antiprism            (not anchored)
        "dcd"   -> nothing
        "grt"   -> nothing
        "tsrct" -> nothing

    The last three are the decisive ones: every one of them MATCHES under
    cmdk's subsequence scoring. They return nothing, so the rule is
    `contains`, and there is no ranking - rows keep the order they were
    given.

    cmdk's subsequence scoring is the other rule, and it lives in
    `comp_command.py` now, where the component that wants it is.
    """
    items = list(items)
    if not query or not query.strip():
        return items
    q = _fold(query).strip()
    out = []
    for it in items:
        kind = _k(it, "kind", "item")
        if kind == "sep":
            continue            # a separator means nothing in a filtered list
        if kind == "label":
            out.append(it)      # headings are resolved below
            continue
        hay = _fold(_k(it, "label", "") or str(_k(it, "id", "")))
        for kw in _k(it, "keywords", ()) or ():
            hay += " " + _fold(str(kw))
        if q in hay:
            out.append(it)
    # drop a heading whose rows all went
    keep, i = [], 0
    while i < len(out):
        it = out[i]
        if _k(it, "kind", "item") == "label":
            if i + 1 < len(out) and _k(out[i + 1], "kind", "item") != "label":
                keep.append(it)
        else:
            keep.append(it)
        i += 1
    return keep
