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


# A merge can leave every number unique and still lose a section or move one's text under
# another heading: #411's review commit deleted 770's, 771's and 772's text, and the next
# union left 787's text under 770 and 789. These hold what can be read without a person.
HEADING = re.compile(r"#{1,6} ")
SPAN = re.compile(r"(\d+)(?:[–-](\d+))?\.")     # `### 544–553.` is one section for ten rows
NO_SECTION = {560, 563, 564}                    # wave 0's rows, which never had one


def cells(line: str) -> int:
    """A row's cells: a pipe in a code span or escaped is text."""
    return re.sub(r"`[^`]*`|\\\|", "", line).count("|") - 1


def sections(text: str) -> dict[int, list[str]]:
    """Each row a `### <n>.` heading covers, to the lines under it, up to the next heading."""
    lines, held, under = text.split("\n"), {}, None
    for line in lines:
        if HEADING.match(line):
            under = None
            if line.startswith("### ") and (m := SPAN.match(line, 4)):
                under = []
                for n in range(int(m[1]), int(m[2] or m[1]) + 1):
                    held[n] = under
        elif under is not None:
            under.append(line)
    return held


def rows(text: str) -> dict[int, str]:
    return {int(m[1]): line for line in text.split("\n") if (m := ROW.match(line))}


def lost_text(text: str) -> list[int]:
    return sorted(n for n, under in sections(text).items() if not any(line.strip() for line in under))


def two_verdicts(text: str) -> list[int]:
    """A second "Judge it." is another section's text, come in by a merge."""
    return sorted(n for n, under in sections(text).items() if sum(x.startswith("- **Judge it.**") for x in under) > 1)


def outside_groups(text: str) -> list[str]:
    """Checks not under a lettered `## ` group, or a group with no check in it."""
    group, bad, held = None, [], {}
    for line in text.split("\n"):
        if line.startswith("## "):
            group = line[3:] if GROUP.match(line) else None
            if group:
                held[group] = 0
        elif m := CHECK.match(line):
            name = next(g for g in m.groups() if g)
            if group is None:
                bad.append(name)
            else:
                held[group] += 1
    return bad + [g for g, n in held.items() if not n]


def test_every_section_keeps_its_text():
    text = REGISTER.read_text()
    assert len(sections(text)) >= 600, "the pattern has stopped finding them, so this proves nothing"
    assert not lost_text(text), f"a heading with nothing under it: {lost_text(text)}"
    assert not two_verdicts(text), f"two sections' text under one heading: {two_verdicts(text)}"


def test_every_row_has_a_section_and_every_section_a_row():
    text = REGISTER.read_text()
    held, table = sections(text), rows(text)
    assert not sorted(set(table) - set(held) - NO_SECTION), "rows with no `### <n>.` section"
    assert not sorted(set(held) - set(table)), "sections with no row"


def test_a_row_has_the_tables_cells():
    table = rows(REGISTER.read_text())
    short = {n: cells(line) for n, line in table.items() if cells(line) != 4}
    assert not short, f"# | Decision | Check | Keep / overturn: {short}"


def test_every_decisions_row_has_its_tables_cells():
    wide, bad = 0, []
    for line in (DOCS / "DECISIONS.md").read_text().split("\n"):
        if not line.startswith("|"):
            wide = 0
        elif not wide:
            wide = cells(line)
        elif cells(line) != wide:
            bad.append(line[:60])
    assert not bad, f"a row's cells aren't its table's: {bad}"


def test_every_check_sits_in_a_group():
    bad = outside_groups(CHECKS.read_text())
    assert not bad, f"a check outside a lettered group, or a group with no check: {bad}"


@pytest.mark.parametrize(("find", "text", "named"), [
    (lost_text, "### 787. GRAPH\n### 785. Proof\n\n- text\n", [787]),                       # what #411's merge left
    (lost_text, "### 787. GRAPH\n\n\n## A part\n", [787]),
    (two_verdicts, "### 789. Audit\n\n- **Judge it.** None.\n- **Judge it.** 612.\n", [789]),
    (outside_groups, "## What no test covers\n**582. One.**\n", ["582"]),
    (outside_groups, "## DL. Moves\n\n623. In a sentence, no bold.\n", ["DL. Moves"]),      # how 623 sat
], ids=["heading-on-heading", "heading-on-part", "two-verdicts", "no-group", "empty-group"])
def test_what_a_scrambled_merge_leaves_is_caught(find, text, named):
    assert find(text) == named


def test_a_range_heading_covers_its_rows_and_a_code_pipe_is_no_cell():
    assert sorted(sections("### 544–546. Plan 42\n\n- text\n")) == [544, 545, 546]
    assert cells(r"| 1 | `a|b` c\|d | — | owner |") == 4


def test_gitattributes_still_names_the_tails():
    """A moved doc would quietly go back to conflicting: the attribute is by path."""
    named = {ROOT / line.split()[0] for line in (ROOT / ".gitattributes").read_text().splitlines()
             if line.endswith(" merge=union")}
    assert named == TAILS
    assert all(path.is_file() for path in named)
