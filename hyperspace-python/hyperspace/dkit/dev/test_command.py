"""cmdk's `commandScore`, ported, against the shipped JavaScript.

Moved here with the code it tests. It was in `test_combobox.py` because the
scorer was in `comp_combobox.py`, and the scorer was there because of a
wrong premise — shadcn's Combobox is Base UI, not Popover + Command, and
filters by substring. The port is exact and belongs to the Command palette.

`GOLDEN_SCORE` is `commandScore` out of `cmdk@1.1.1`
(node_modules/cmdk/dist/command-score.js) run under node. 59 pairs were
compared while the port was written and every one agreed to 1e-12; these
are the nine that pin the behaviour worth pinning.
"""

from __future__ import annotations

from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

from hyperspace.dkit import comp_combobox as CB
from hyperspace.dkit import comp_command as C


def items(*labels):
    """The same row model the Combobox uses - a Command palette shows the
    same kind of row, so the type is shared rather than duplicated."""
    return [CB.Item(id=s.lower(), label=s) for s in labels]


SOLIDS = items("Dodecahedron", "Great Dodecahedron", "Dual Dodecahedron",
               "Tesseract", "16-cell")

# --------------------------------------------------------------------------
# command_score — the rule cmdk actually uses
# --------------------------------------------------------------------------
# (string, query, score) straight out of the shipped cmdk under node.
GOLDEN_SCORE = [
    # a prefix runs continuously (1.0 a character), then PENALTY_NOT_COMPLETE
    # 0.99 for leaving the string unconsumed, and 0.9999 for the one case
    # mismatch on the capital D
    ("Dodecahedron", "dod", 0.989901),
    ("Dodecahedron", "DOD", 0.9898020099),   # two more case mismatches
    ("Cube", "cube", 0.9999),                # consumed whole: no 0.99
    ("Dodecahedron", "zz", 0.0),             # no match at all
    ("Tesseract", "", 0.99),                 # an empty query matches anything
    ("", "", 1.0),                           # ...and exactly, when both empty
    ("", "a", 0.0),
    ("Hyper Cube", "hc", 0.8908218089100001),   # a jump to a WORD boundary
    ("snub_cube", "sc", 0.792),              # ..._ is a gap, not a space: 0.8
    ("Dodecahedron", "dh", 0.16744343529970956),   # ...mid-word is 0.17
    ("Dodecahedron", "dcd", 0.02843691861694967),  # three jumps compound
]


@pytest.mark.parametrize("s,q,score", GOLDEN_SCORE)
def test_command_score_matches_cmdk(s, q, score):
    assert C.command_score(s, q) == pytest.approx(score, abs=1e-12)


@pytest.mark.skip(reason="the real Combobox is Base UI and filters by "
                         "CONTAINS - see test_the_match_is_a_substring")
def test_the_match_is_a_subsequence_not_a_substring():
    """The finding worth a test of its own: cmdk's filter is fuzzy.

    "dcd" is not anywhere in "Dodecahedron" as a substring; it is there as a
    subsequence (D-o-**d**-e-**c**-a-h-e-**d**-ron), and cmdk shows the row.
    """
    assert "dcd" not in "Dodecahedron".lower()
    assert C.command_score("Dodecahedron", "dcd") > 0.0
    # and the ranking is the real one, not alphabetical and not source
    # order: 0.028437 > 0.028295 > 0.025593 out of cmdk itself
    assert [i.id for i in CB.filter_items(SOLIDS, "dcd")] == \
        ["dodecahedron", "dual dodecahedron", "great dodecahedron"]


def test_keywords_are_appended_to_the_haystack():
    """cmdk scores `value + " " + keywords.join(" ")`, so a keyword is a
    second spelling — and a row with none is NOT found by it."""
    cube = C.Item(id="cube", label="Cube", keywords=("box", "hexahedron"))
    plain = C.Item(id="other", label="Cube")
    assert C.command_score("Cube", "box", ("box",)) > 0.0
    assert C.command_score("Cube", "box") == 0.0
    assert [i.id for i in CB.filter_items([cube, plain], "box")] == ["cube"]


def test_case_still_costs_score_even_though_it_does_not_filter():
    """PENALTY_CASE_MISMATCH is 0.9999 a character: a mismatch ranks lower
    without ever failing to match."""
    assert C.command_score("Dodecahedron", "dod") > \
        C.command_score("Dodecahedron", "DOD") > 0.0


def test_ties_keep_source_order():
    """Equal scores are left alone: Python's sort is stable and so is V8's,
    which is what cmdk relies on."""
    src = items("Alpha Cell", "Beta Cell", "Gamma Cell")
    out = [i.id for i in CB.filter_items(src, "cell")]
    assert out == ["alpha cell", "beta cell", "gamma cell"]
    scores = [C.command_score(i.label, "cell") for i in src]
    assert len(set(scores)) == 1          # they really are tied


def test_a_query_that_matches_every_item_keeps_them_all():
    """"e" is in all five labels, and — measured out of cmdk — scores
    0.1683 on every one of them, so nothing is dropped AND nothing moves.
    A one-letter query that lands mid-word is 0.17 x 0.99 wherever it
    lands, which is not what "ranked" sounds like it would do."""
    out = CB.filter_items(SOLIDS, "e")
    assert len(out) == len(SOLIDS)
    assert [i.id for i in out] == [i.id for i in SOLIDS]
    scores = [C.command_score(i.label, "e") for i in SOLIDS]
    assert scores == pytest.approx([0.1683] * len(SOLIDS))
