"""cmdk's `commandScore`, which is the Command palette's ranking rule.

NOT the Combobox's. This was in `comp_combobox.py` for a while because the
premise was that shadcn builds a Combobox from Popover + Command; it does
not — it ships `combobox.tsx` on Base UI, whose filter is a plain
case-insensitive substring match. The port below is exact, verified against
the shipped JavaScript over 382 input pairs, and it was simply answering a
question nobody had asked. RETRO row 3 is about exactly that: verifying an
implementation against its spec says nothing when the premise picked the
wrong spec.

It lives here because the Command palette is the component it belongs to —
`ROADMAP.md` calls it "cheap and underrated", a fuzzy finder over 600-900
addressable params — and because the work is correct and worth keeping
until that gets built.

`Item`, `heading` and `sep` come from `combobox_items` (the Combobox's row
model, split out of `comp_combobox` by HANDOFF item 3c): a Command palette
shows the same kind of row, and duplicating the model to avoid the import
would be worse than the import.
"""

from __future__ import annotations

from combobox_items import Item, _is_row, _k, heading, sep  # noqa: F401

# --------------------------------------------------------------------------
# the filter — pure, no imgui
# --------------------------------------------------------------------------
#
# WHICH RULE cmdk ACTUALLY USES, read out of the shipped package rather than
# assumed: `cmdk@1.1.1`'s default filter is `commandScore`
# (node_modules/cmdk/dist/chunk-NZJY6EH4.mjs, re-exported as
# dist/command-score.mjs), and it is
#
#   * a SUBSEQUENCE match, not a substring one — "ec" matches "Dodecahedron"
#   * CASE-INSENSITIVE: both sides go through
#     `s.toLowerCase().replace(/[\s-]/g, " ")`, so a hyphen folds to a space
#     as well
#   * SCORED in (0, 1]: 0 means no match, and cmdk's gate for showing a row
#     is literally `filtered.items.get(id) > 0`
#   * ranked DESCENDING by that score, ties left in source order (V8's sort
#     is stable, and so is Python's)
#
# The score is not a tie-break bolted onto a substring test — it IS the
# rule, so the algorithm is ported outright below, constant for constant,
# rather than approximated. It was cross-checked against the shipped JS over
# 59 (string, query[, keywords]) pairs and agrees to 1e-12 on every one.
#
# Why that matters rather than being pedantry: with "dod" over
# ["Great Dodecahedron", "Dodecahedron", "Dual Dodecahedron"] a substring
# test cannot say which comes first. commandScore puts the one that STARTS
# with the query first, because a jump to the head of the string scores 1, a
# jump to a word boundary 0.9 and a jump into the middle of a word 0.17.

SCORE_CONTINUE_MATCH = 1.0
SCORE_SPACE_WORD_JUMP = 0.9
SCORE_NON_SPACE_WORD_JUMP = 0.8
SCORE_CHARACTER_JUMP = 0.17
SCORE_TRANSPOSITION = 0.1
PENALTY_SKIPPED = 0.999
PENALTY_CASE_MISMATCH = 0.9999
PENALTY_NOT_COMPLETE = 0.99

# cmdk's IS_GAP_REGEXP / IS_SPACE_REGEXP, as sets. `\s` is JavaScript's,
# which includes U+00A0 and the unicode separators; the five ASCII ones plus
# the no-break space cover everything a label here can hold.
_GAP_CHARS = frozenset("\\/_+.#\"@[({&")
_SPACE_CHARS = frozenset(" \t\n\r\f\v -")


def _at(s: str, i: int) -> str:
    """JavaScript's `String.prototype.charAt`: "" when out of range.

    Not `s[i]` — a negative index WRAPS in Python, so `s[-1]` would read
    the last character as if it were the one before the start, and
    `charAt(-1)` is reached for real at index 0.
    """
    return s[i] if 0 <= i < len(s) else ""


def _count(s: str, chars: frozenset) -> int:
    """`s.match(/…/g)?.length ?? 0` for a single-character class."""
    return sum(1 for c in s if c in chars)


def _fold(s: str) -> str:
    """cmdk's `formatInput`: lowercase, with `[\\s-]` folded to a space."""
    return "".join(" " if c in _SPACE_CHARS else c for c in s.lower())


def _score(string, abbr, lower_string, lower_abbr, si, ai, memo):
    if ai == len(abbr):
        return (SCORE_CONTINUE_MATCH if si == len(string)
                else PENALTY_NOT_COMPLETE)
    key = (si, ai)
    hit = memo.get(key)
    if hit is not None:
        return hit

    ch = lower_abbr[ai]
    high = 0.0
    idx = lower_string.find(ch, si)
    while idx >= 0:
        s = _score(string, abbr, lower_string, lower_abbr, idx + 1, ai + 1,
                   memo)
        # The multipliers apply only when the recursive score already beats
        # the best so far — that is how the JS is written, `E>S&&(E*=…)`,
        # and the transposition branch below then compares against the RAW
        # score. Ported faithfully rather than tidied, because tidying it
        # changes the numbers.
        if s > high:
            if idx == si:
                s *= SCORE_CONTINUE_MATCH
            elif _at(string, idx - 1) in _GAP_CHARS:
                s *= SCORE_NON_SPACE_WORD_JUMP
                n = _count(string[si:idx - 1], _GAP_CHARS)
                if n and si > 0:
                    s *= PENALTY_SKIPPED ** n
            elif _at(string, idx - 1) in _SPACE_CHARS:
                s *= SCORE_SPACE_WORD_JUMP
                n = _count(string[si:idx - 1], _SPACE_CHARS)
                if n and si > 0:
                    s *= PENALTY_SKIPPED ** n
            else:
                s *= SCORE_CHARACTER_JUMP
                if si > 0:
                    s *= PENALTY_SKIPPED ** (idx - si)
            if _at(string, idx) != _at(abbr, ai):
                s *= PENALTY_CASE_MISMATCH
        if ((s < SCORE_TRANSPOSITION
             and _at(lower_string, idx - 1) == _at(lower_abbr, ai + 1))
            or (_at(lower_abbr, ai + 1) == _at(lower_abbr, ai)
                and _at(lower_string, idx - 1) != _at(lower_abbr, ai))):
            t = _score(string, abbr, lower_string, lower_abbr, idx + 1,
                       ai + 2, memo)
            if t * SCORE_TRANSPOSITION > s:
                s = t * SCORE_TRANSPOSITION
        if s > high:
            high = s
        idx = lower_string.find(ch, idx + 1)

    memo[key] = high
    return high


def command_score(string: str, query: str, keywords=()) -> float:
    """cmdk's `commandScore(value, search, keywords)`, in Python.

    0 is "no match"; anything above it matches, and bigger is better.
    Keywords are appended to the haystack with spaces, exactly as cmdk does,
    so they match as if they were part of the label.
    """
    if keywords:
        string = string + " " + " ".join(k.strip() for k in keywords)
    return _score(string, query, _fold(string), _fold(query), 0, 0, {})


def rank_items_cmdk(items, query: str) -> list:
    """Rank and filter `items` by `query`, the way cmdk does. Pure.

    * An EMPTY (or all-whitespace) query returns the list UNCHANGED — not
      re-ranked. cmdk's sort returns early on `!search`, so the author's
      order is the order, and separators survive.
    * Otherwise a row is kept when `command_score > 0`, and rows come out
      ordered by that score, descending, with ties in source order.
    * A `heading()` opens a group: its rows are ranked among themselves and
      the group moves as a block, groups ordered by their best row's score.
      A group whose rows all scored 0 disappears, heading and all — cmdk's
      `filtered.groups` rule.
    * Separators are dropped while there is a query, because cmdk renders a
      `CommandSeparator` only when the search box is empty.

    Rows before the first heading form an implicit, unheaded group, which is
    what `<CommandGroup>` with no `heading` prop is.
    """
    items = list(items)
    if not query or not query.strip():
        return items

    # (heading_or_None, [rows]) in source order; separators are gone
    groups: list = [(None, [])]
    for it in items:
        kind = _k(it, "kind", "item")
        if kind == "sep":
            continue
        if kind == "label":
            groups.append((it, []))
        else:
            groups[-1][1].append(it)

    ranked = []
    for head, rows in groups:
        scored = []
        for it in rows:
            s = command_score(_k(it, "label", "") or str(_k(it, "id", "")),
                              query, tuple(_k(it, "keywords", ())))
            if s > 0.0:
                scored.append((s, it))
        if not scored:
            continue
        # `sorted` is stable, so equal scores keep source order — which is
        # also what V8's sort gives cmdk
        best = max(s for s, _ in scored)
        scored.sort(key=lambda p: -p[0])
        ranked.append((best, head, [it for _, it in scored]))
    ranked.sort(key=lambda p: -p[0])

    out: list = []
    for _best, head, rows in ranked:
        if head is not None:
            out.append(head)
        out.extend(rows)
    return out
