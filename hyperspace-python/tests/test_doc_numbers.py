"""The doc tails merge by union (`.gitattributes`, ENGINEERING §16 "Doc tails"): two
PRs that each add a row merge clean, so two that took one number merge clean too.
These fail on that, since git no longer will."""

import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "hyperspace-python" / "docs"
REGISTER = DOCS / "DECISION-REGISTER.md"
CHECKS = DOCS / "plans" / "11-hand-checks.md"
TAILS = {REGISTER, DOCS / "DECISIONS.md", CHECKS, DOCS / "plans" / "README.md"}

ROW = re.compile(r"\| (\d+) \|")
SECTION = re.compile(r"### (\d+)\.")
GROUP = re.compile(r"## ([A-Z]{1,2})\. ")
CHECK = re.compile(r"\*\*(\d+)\. |(\d+) — covered by")       # steps under a check are plain "1. "


def found(pattern: re.Pattern, text: str) -> list[str]:
    """What `pattern` names at the start of each line."""
    return [next(g for g in m.groups() if g) for line in text.split("\n") if (m := pattern.match(line))]


def twice(names: list[str]) -> list[str]:
    return [name for name, n in Counter(names).items() if n > 1]


@pytest.mark.parametrize(("path", "pattern", "at_least"), [
    (REGISTER, ROW, 600),                   # the answer sheet
    (REGISTER, SECTION, 600),               # its `### <n>.` sections
    (CHECKS, GROUP, 80),                    # group letters
    (CHECKS, CHECK, 500),                   # check numbers
], ids=["row", "section", "group", "check"])
def test_no_number_or_letter_is_taken_twice(path, pattern, at_least):
    names = found(pattern, path.read_text())
    assert len(names) >= at_least, "the pattern has stopped finding them, so this proves nothing"
    assert not twice(names), f"{path.name}: taken twice: {twice(names)}"


@pytest.mark.parametrize(("pattern", "text", "dup"), [
    (ROW, "| 757 | one |\n| 758 | two |\n| 757 | the other PR's |\n", "757"),
    (SECTION, "### 757. One\n\n### 757. The other PR's\n", "757"),
    (GROUP, "## CT. One\n## CT. The other PR's\n", "CT"),
    (CHECK, "**582. One.**\n1. a step\n1. a step\n**582. The other PR's.**\n", "582"),
    (CHECK, "**32. One.**\n32 — covered by check 41.\n", "32"),
], ids=["row", "section", "group", "check", "covered"])
def test_a_clean_union_with_one_number_twice_is_caught(pattern, text, dup):
    assert twice(found(pattern, text)) == [dup]


def test_steps_and_prose_are_not_taken_for_checks():
    assert found(CHECK, "1. a step\n1. a step\n582 words **582. in a sentence**\n") == []


def test_gitattributes_still_names_the_tails():
    """A moved doc would quietly go back to conflicting: the attribute is by path."""
    named = {ROOT / line.split()[0] for line in (ROOT / ".gitattributes").read_text().splitlines()
             if line.endswith(" merge=union")}
    assert named == TAILS
    assert all(path.is_file() for path in named)
