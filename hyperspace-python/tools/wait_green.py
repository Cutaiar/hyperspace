#!/usr/bin/env python3
"""Wait for one PR head's CI, and say whether it is green. It merges nothing.

    uv run python tools/wait_green.py <pr> <expected-head>

The port of the wave-4 `wait-green.sh`, with its exit codes:

    0  every run on that head finished, each a success or skipped
    1  the arguments are wrong (no PR, or an empty head)
    2  a run on that head finished any other way; each run is listed
    3  the PR's head is not the expected one (a prefix will do)
    4  no CI run appeared for that head in 10 minutes
    5  CI was still running after 30 minutes

Every doubt lands on a code that is not 0: a `gh` that fails, hangs or
answers nonsense reads as no answer, so a poll goes round again and the
head check fails. `main` has no required checks, so `gh pr merge --auto`
merges at once (plan 58): whoever merges runs this first and merges by
hand after it. Hence nothing here but two reads, and
`tests/test_wait_green.py` holds it to that.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

# `gh` finds the repository from the folder it runs in; this one is the
# worktree the tool sits in, wherever it was called from
REPO = Path(__file__).resolve().parents[2]

APPEAR_TRIES, APPEAR_WAIT_S = 60, 10    # 10 minutes for a run to appear
FINISH_TRIES, FINISH_WAIT_S = 90, 20    # 30 minutes for them to finish
GH_TIMEOUT_S = 60                       # a hung `gh` is one poll with no answer
PASSING = {"success", "skipped"}

GREEN, USAGE, RED, WRONG_HEAD, NO_RUN, STILL_RUNNING = 0, 1, 2, 3, 4, 5


def _gh(*args: str) -> dict | list | None:
    """`gh <args>`'s JSON, or None for no answer of any kind."""
    try:
        done = subprocess.run(("gh", *args), cwd=REPO, capture_output=True,
                              text=True, timeout=GH_TIMEOUT_S, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    try:
        return json.loads(done.stdout)
    except ValueError:
        return None


def pr_head(pr: str) -> str:
    """The PR's head commit, or "" for no answer."""
    doc = _gh("pr", "view", pr, "--json", "headRefOid")
    head = doc.get("headRefOid") if isinstance(doc, dict) else None
    return head if isinstance(head, str) else ""


def runs_on(head: str) -> list[dict] | None:
    """The CI runs on a commit, or None for no answer."""
    doc = _gh("run", "list", "--commit", head, "--json", "name,status,conclusion,url")
    if isinstance(doc, list) and all(isinstance(r, dict) for r in doc):
        return doc
    return None


def wait(pr: str, want: str, sleep: Callable[[float], None] = time.sleep) -> int:
    """Wait, print what happened, and give the exit code."""
    head = pr_head(pr)
    if not head or not head.startswith(want):
        print(f"head {head} is not {want}")
        return WRONG_HEAD
    for _ in range(APPEAR_TRIES):
        if runs_on(head):
            break
        sleep(APPEAR_WAIT_S)
    else:
        print(f"no CI run appeared for {head}")
        return NO_RUN
    for _ in range(FINISH_TRIES):
        # the conclusions come from the read that saw them all finished. An
        # empty list here is not "all finished": runs that vanish are no green
        runs = runs_on(head)
        if runs and all(r.get("status") == "completed" for r in runs):
            break
        sleep(FINISH_WAIT_S)
    else:
        print(f"CI still running after 30 min on {head}")
        return STILL_RUNNING
    if any(r.get("conclusion") not in PASSING for r in runs):
        print(f"CI NOT green on {head}")
        for r in runs:
            print(r.get("name"), r.get("conclusion"), r.get("url"))
        return RED
    print(f"CI green on {head}")
    return GREEN


class _Args(argparse.ArgumentParser):
    def error(self, message: str):
        # argparse's own 2 would read as "CI is red"
        self.exit(USAGE, f"{self.prog}: {message}\n")


def main(argv: list[str] | None = None) -> int:
    ap = _Args(description="Wait for a PR head's CI; exit 0 only if it is green. Merges nothing.")
    ap.add_argument("pr", help="the PR's number")
    ap.add_argument("head", help="the head commit you expect, or a prefix of it")
    args = ap.parse_args(argv)
    if not args.pr or not args.head:
        # "" is a prefix of every commit: it would wave any head through
        ap.error("the PR and the head may not be empty")
    return wait(args.pr, args.head)


if __name__ == "__main__":
    sys.exit(main())
