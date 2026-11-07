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
GROUP = re.compile(r"## ([A-Z]{1,2})\. ")
# Steps under a check are plain "1. ", so a plain check needs its three digits and its bold.
CHECK = re.compile(r"\*\*(\d+)\. |(\d+) — covered by|(\d{3})\. \*\*")
SPAN = re.compile(r"### (\d+)(?:[–-](\d+))?\.")   # `### 544–553.` is one section for ten rows


def found(pattern: re.Pattern, text: str) -> list[str]:
    """What `pattern` names at the start of each line."""
    return [next(g for g in m.groups() if g) for line in text.split("\n") if (m := pattern.match(line))]


def twice(names: list[str]) -> list[str]:
    return [name for name, n in Counter(names).items() if n > 1]


def heading_numbers(line: str) -> list[int]:
    """Every row a `### ` heading covers."""
    return list(range(int(m[1]), int(m[2] or m[1]) + 1)) if (m := SPAN.match(line)) else []


def section_numbers(text: str) -> list[str]:
    return [str(n) for line in text.split("\n") for n in heading_numbers(line)]


def row_numbers(text: str) -> list[str]:
    return found(ROW, text)


def group_letters(text: str) -> list[str]:
    return found(GROUP, text)


def check_numbers(text: str) -> list[str]:
    return found(CHECK, text)


@pytest.mark.parametrize(("path", "names_in", "at_least"), [
    (REGISTER, row_numbers, 600),           # the answer sheet
    (REGISTER, section_numbers, 600),       # its `### <n>.` sections, a range's every row
    (CHECKS, group_letters, 80),
    (CHECKS, check_numbers, 500),
], ids=["row", "section", "group", "check"])
def test_no_number_or_letter_is_taken_twice(path, names_in, at_least):
    names = names_in(path.read_text())
    assert len(names) >= at_least, "the pattern has stopped finding them, so this proves nothing"
    assert not twice(names), f"{path.name}: taken twice: {twice(names)}"


@pytest.mark.parametrize(("names_in", "text", "dup"), [
    (row_numbers, "| 757 | one |\n| 758 | two |\n| 757 | the other PR's |\n", "757"),
    (section_numbers, "### 757. One\n\n### 757. The other PR's\n", "757"),
    (section_numbers, "### 756–758. Three\n\n### 757. The other PR's\n", "757"),
    (group_letters, "## CT. One\n## CT. The other PR's\n", "CT"),
    (check_numbers, "**582. One.**\n1. a step\n1. a step\n**582. The other PR's.**\n", "582"),
    (check_numbers, "**318. One.**\n318. **The other's, plain.**\n", "318"),
    (check_numbers, "**32. One.**\n32 — covered by check 41.\n", "32"),
], ids=["row", "section", "range", "group", "check", "plain", "covered"])
def test_a_clean_union_with_one_number_twice_is_caught(names_in, text, dup):
    assert twice(names_in(text)) == [dup]


def test_steps_and_prose_are_not_taken_for_checks():
    assert found(CHECK, "1. a step\n1. **a bold step**\n582 words **582. in a sentence**\n") == []


# A merge can leave every number unique and still lose a section or move one's text under
# another heading: #411's review commit deleted 770's, 771's and 772's text, and the next
# union left 787's text under 770 and 789. These hold what can be read without a person.
HEADING = re.compile(r"#{1,6} ")
NO_SECTION = {560, 563, 564}                    # wave 0's rows, which never had one
HEADERS = {"| Decision", "| Not built"}
JUDGE = re.compile(r"(?:- )?\*\*Judge it\.\*\*(.*)")
CHECK_FLOOR = 673                               # older rows use the Check cell looser: 44 disagree
CHECK_CELL = re.compile(r"(—|\d[\d, ]*)(?:; rows? [\d, ]+)?|rows? [\d, ]+")


def cells(line: str) -> int:
    """A row's cells: GitHub splits on a pipe even in a code span, so only an escaped one is text."""
    return line.replace("\\|", "").count("|") - 1


def sections(text: str) -> dict[int, list[str]]:
    """Each row a `### <n>.` heading covers, to the lines under it, up to the next heading."""
    lines, held, under = text.split("\n"), {}, None
    for line in lines:
        if HEADING.match(line):
            under = None
            if numbers := heading_numbers(line):
                under = []
                for n in numbers:
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
    return sorted(n for n, under in sections(text).items() if sum(bool(JUDGE.match(x)) for x in under) > 1)


def check_cell_wrong(text: str) -> dict[int, str]:
    """From the floor on: a Check cell holds checks, then any rows, and every check its section's "Judge it" names."""
    held, bad = sections(text), {}
    for n, line in rows(text).items():
        cell = re.split(r"(?<!\\)\|", line)[3].strip()
        checks = set(re.findall(r"\d+", cell.split(";")[0]))
        judged = {c for x in held.get(n, []) if (m := JUDGE.match(x)) for c in re.findall(r"\b\d{3}\b", m[1])}
        if n >= CHECK_FLOOR and (judged - checks or not CHECK_CELL.fullmatch(cell)):
            bad[n] = cell
    return bad


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


def test_a_rows_check_cell_agrees_with_its_section():
    wrong = check_cell_wrong(REGISTER.read_text())
    assert not wrong, f"a Check cell without its section's Judge it numbers: {wrong}"


def decision_names(text: str) -> list[str]:
    """Each `DECISIONS.md` row's first cell, tables' headers and rules left out."""
    return [c for line in text.split("\n") if line.startswith("| ") and (c := line.split(" | ")[0]) not in HEADERS]


def test_no_decision_is_there_twice():
    doubled = twice(decision_names((DOCS / "DECISIONS.md").read_text()))
    assert not doubled, f"a row kept twice by a union: {doubled}"


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
    (two_verdicts, "### 710. Node\n\n**Judge it.** 541.\n- **Judge it.** 542.\n", [710]),
    (lost_text, "### 787. GRAPH\n### 785. Proof\n\n- text\n", [787]),                       # what #411's merge left
    (lost_text, "### 787. GRAPH\n\n\n## A part\n", [787]),
    (two_verdicts, "### 789. Audit\n\n- **Judge it.** None.\n- **Judge it.** 612.\n", [789]),
    (outside_groups, "## What no test covers\n**582. One.**\n", ["582"]),
    (outside_groups, "## DL. Moves\n\n623. In a sentence, no bold.\n", ["DL. Moves"]),      # how 623 sat
], ids=["plain-verdict", "heading-on-heading", "heading-on-part", "two-verdicts", "no-group", "empty-group"])
def test_what_a_scrambled_merge_leaves_is_caught(find, text, named):
    assert find(text) == named


def test_a_range_heading_covers_its_rows_and_a_code_pipe_is_no_cell():
    assert sorted(sections("### 544–546. Plan 42\n\n- text\n")) == [544, 545, 546]
    assert cells(r"| 1 | a\|b | — | owner |") == 4
    assert cells("| 1 | `a|b` | — | owner |") == 5       # GitHub draws this with a column too many


@pytest.mark.parametrize(("line", "wrong"), [
    ("| 700 | x | 532 | y |\n\n### 700. X\n\n- **Judge it.** 532, 578.\n", True),
    ("| 700 | x | — | y |\n\n### 700. X\n\n- **Judge it.** 532.\n", True),
    ("| 781 | x | Keep the old way | y |\n\n### 781. X\n\n- text\n", True),
    ("| 700 | x | 532, 578; rows 656, 684 | y |\n\n### 700. X\n\n- **Judge it.** 532, 578.\n", False),
    ("| 700 | x | — | y |\n\n### 700. X\n\n- **Judge it.** No hand check.\n", False),
], ids=["short", "dash", "prose", "agrees", "none"])
def test_a_check_cell_that_disagrees_is_caught(line, wrong):
    assert bool(check_cell_wrong(line)) is wrong


def test_a_doubled_decision_is_caught_and_a_header_is_not():
    text = "| Decision | Where | Who |\n|---|---|---|\n| **A** | x | y |\n\n| Decision | Who |\n|---|---|\n| **A** | z |\n"
    assert twice(decision_names(text)) == ["| **A**"]


def test_gitattributes_still_names_the_tails():
    """A moved doc would quietly go back to conflicting: the attribute is by path."""
    named = {ROOT / line.split()[0] for line in (ROOT / ".gitattributes").read_text().splitlines()
             if line.endswith(" merge=union")}
    assert named == TAILS
    assert all(path.is_file() for path in named)
