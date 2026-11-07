"""The owner, 2026-11-06: "Session and rig need to go away." (register rows 778-780.)

Neither word may return in a string a person reads. Every string literal in `hyperspace/`
is scanned, docstrings excluded: an f-string's pieces are read one by one, and comments
are not read at all. `LEFT` is what stays and why: each is a saved key or a word the code
compares against itself, so no person ever sees it. Add to it only for a string no person
reads; say a new panel string as what it means, in `docs/GLOSSARY.md`'s words.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import hyperspace

ROOT = Path(hyperspace.__file__).parent
WORDS = re.compile(r"\b(sessions?|rigs?)\b", re.IGNORECASE)

# (file, the whole string): why it stays. No line numbers: others move lines.
SAVED_SHOW_KEY = "a key of a saved show file; goes with the one migration"
LEFT: dict[tuple[str, str], str] = {
    ("graphview.py", "session"): "`META_SECTION`, which side a node's position sits on, compared in code",
    ("graphview.py", "rig:"): "a prefix hashed into a cloud cable's id, never drawn",
    ("headless.py", "session"): SAVED_SHOW_KEY,
    ("library.py", "session"): SAVED_SHOW_KEY,
    ("library.py", "rig"): SAVED_SHOW_KEY,
    ("loadable.py", "session"): "`getattr` on the show object: an attribute's name",
    ("patches.py", "rig"): "`CONTROL`, a cable's class against a region, compared in code",
    ("ui_routing.py", "session"): "the mark's section key in ROUTING, compared in code",
}


def said_by(source: str) -> list[str]:
    """Every string in `source` a person could read: all but the docstrings."""
    tree = ast.parse(source)
    docs = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs
    ]


def _found() -> set[tuple[str, str]]:
    return {
        (path.relative_to(ROOT).as_posix(), text)
        for path in sorted(ROOT.rglob("*.py"))
        for text in said_by(path.read_text(encoding="utf-8"))
        if WORDS.search(text)
    }


def test_session_and_rig_leave_every_string_a_person_reads():
    back = sorted(_found() - set(LEFT))
    assert not back, (
        "say these as what they mean (docs/GLOSSARY.md: the meta controller's, the bus "
        f"cable, not on this Mac), or add to LEFT with why no person reads them: {back}"
    )


def test_what_is_left_is_still_there():
    """So the list shrinks as the migration and the cleanup take these keys away."""
    gone = sorted(set(LEFT) - _found())
    assert not gone, f"no longer in the code, so take them off LEFT: {gone}"


def test_the_scan_finds_the_word_in_every_shape_it_could_come_back_in():
    source = '''
"""A session's docstring is not read."""
# a rig's comment is not read
TIP = "the rig's cable"
LABEL = "Session"
MICRO = "session"
SPLIT = ("not in this "
         "rig")
def f(x):
    """A rig's docstring is not read."""
    return f"{x} is the session's"
'''
    said = [text for text in said_by(source) if WORDS.search(text)]
    assert sorted(said) == sorted(
        ["the rig's cable", "Session", "session", "not in this rig", " is the session's"]
    )


def test_right_rigid_and_origin_are_no_rig():
    assert not WORDS.search("the right rigid origin, a trigger's rigging")
