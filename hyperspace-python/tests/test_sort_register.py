"""tools/sort_register.py (row 606): the register's answer sheet and its
numbered sections sorted, no text changed; an unnumbered `### ` and a tail
after the last section do not break it or travel."""

import runpy
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "sort_register.py"

REGISTER = """# Register

| # | Decision |
|---|---|
| 3 | three |
| 1 | one |
| 2 | two |

## Old
### 1. One
one's text

## Plan B
### Background
an unnumbered heading under the plan's
### 3. Three
three's text
### Notes on three
an unnumbered heading in three's section

## Plan A
### 2. Two
two's text

## What no row covers
the tail
"""


def _sort(tmp_path, text, first="1"):
    path = tmp_path / "REGISTER.md"
    path.write_text(text)
    subprocess.run([sys.executable, str(TOOL), first, str(path)], check=True)
    return path.read_text()


def test_unnumbered_headings_stay_with_their_section_and_the_tail_stays_last(tmp_path):
    out = _sort(tmp_path, REGISTER)
    assert sorted(out.split("\n")) == sorted(REGISTER.split("\n"))         # no text changed
    assert out.index("| 1 |") < out.index("| 2 |") < out.index("| 3 |")
    order = [out.index(s) for s in ("### 1.", "## Plan A", "### 2.", "## Plan B",
                                    "### Background", "### 3.", "### Notes on three",
                                    "## What no row covers", "the tail")]
    assert order == sorted(order), out
    assert out.endswith("the tail\n")


def test_importing_it_sorts_nothing(tmp_path, monkeypatch):
    """Importing it once re-sorted the register. Aimed at a scratch file, so if the
    guard ever goes this fails there and not on the real one."""
    path = tmp_path / "REGISTER.md"
    path.write_text(REGISTER)
    monkeypatch.setattr(sys, "argv", ["sort_register.py", "1", str(path)])
    runpy.run_path(str(TOOL), run_name="sort_register")
    assert path.read_text() == REGISTER


def test_a_second_run_changes_nothing_and_first_leaves_older_sections(tmp_path):
    once = _sort(tmp_path, REGISTER)
    assert _sort(tmp_path, once) == once
    older = ("| 1 | one |\n\n### 2. Two\nx\n\n### 1. One\ny\n\n"
             "### 4. Four\nz\n\n### 3. Three\nw\n")
    kept = _sort(tmp_path, older, first="3")
    # the sections before the first numbered 3 or more keep their order
    assert kept.index("### 2.") < kept.index("### 1.") < kept.index("### 3.") < kept.index("### 4.")
