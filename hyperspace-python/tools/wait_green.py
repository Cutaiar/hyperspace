#!/usr/bin/env python3
"""Wait for one PR head's CI, and say whether it is green. It merges nothing.

    python3 tools/wait_green.py <pr> <expected-head>

Standard library only, so plain `python3`: `uv run` would sync a project first,
and uv's own failure codes would read as the codes below.

    0  the newest run of the `tests` workflow on that head finished with success
    1  the arguments are wrong (no PR, or a head under 7 characters); also `--help`
    2  that run finished any other way, skipped and cancelled included
    3  the PR's head is not the expected one, or moved during the wait
    4  no `tests` run appeared for that head in 10 minutes
    5  that run was still going 30 minutes after it appeared
    6  `gh` gave no answer: at the first read, or for 5 minutes in a row. Its
       own stderr comes through, so a login or a rate limit says so

The head is read again after every read of the runs, so no verdict outlives a
push: `tests.yml` has `cancel-in-progress`, and a push cancels the run on the
old head, which is a moved head (3), not a red one (2). The waits are a monotonic
clock's, so a slow `gh` can't stretch them, and they can run over by one poll.

`main` has no required checks, so `gh pr merge --auto` merges at once (plan 58):
whoever merges runs this first and merges by hand after it. Hence nothing here
but two reads, and `tests/test_wait_green.py` holds it to that. The only exit 0 is
a green head, so there is no `--help` exit 0: it prints the help and exits 1.
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

WORKFLOW = "tests"      # `name:` in .github/workflows/tests.yml; a test holds the two together
# Polls of 5 s (row 870): a merge waits up to one poll past green, and with CI
# near two minutes 20 s was a sixth of it. Two `gh` reads a poll, far inside the API's limit.
APPEAR_S, APPEAR_POLL_S = 10 * 60, 5    # for a run to appear
FINISH_S, FINISH_POLL_S = 30 * 60, 5    # for it to finish, from when it appeared
SILENT_S = 5 * 60                       # no answer from `gh` for this long is the end of the wait
GH_TIMEOUT_S = 60                       # a hung `gh` is one read with no answer
MIN_HEAD = 7                            # a shorter prefix checks next to nothing

GREEN, USAGE, RED, WRONG_HEAD, NO_RUN, STILL_RUNNING, NO_ANSWER = 0, 1, 2, 3, 4, 5, 6


def _gh(*args: str) -> dict | list | None:
    """`gh <args>`'s JSON, or None for no answer of any kind. Its stderr stays on ours."""
    try:
        done = subprocess.run(("gh", *args), cwd=REPO, stdout=subprocess.PIPE,
                              text=True, timeout=GH_TIMEOUT_S, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"gh: {e}", file=sys.stderr)
        return None
    if done.returncode != 0:
        return None
    try:
        return json.loads(done.stdout)
    except ValueError:
        return None


def pr_head(pr: str) -> str | None:
    """The PR's head commit, or None for no answer."""
    doc = _gh("pr", "view", pr, "--json", "headRefOid")
    head = doc.get("headRefOid") if isinstance(doc, dict) else None
    return head if head and isinstance(head, str) else None


def runs_on(head: str) -> list[dict] | None:
    """Every workflow's runs on a commit, or None for no answer."""
    doc = _gh("run", "list", "--commit", head, "--json",
              "workflowName,databaseId,attempt,status,conclusion,url")
    if isinstance(doc, list) and all(isinstance(r, dict) for r in doc):
        return doc
    return None


def newest(runs: list[dict]) -> dict | None:
    """The run that speaks for this head: `tests`, newest attempt. An older one was superseded."""
    ours = [r for r in runs if r.get("workflowName") == WORKFLOW]
    return max(ours, key=lambda r: (r.get("databaseId") or 0, r.get("attempt") or 0), default=None)


def wait(pr: str, want: str, sleep: Callable[[float], None] = time.sleep,
         clock: Callable[[], float] = time.monotonic) -> int:
    """Wait, print what happened, and give the exit code."""
    head = pr_head(pr)
    if head is None:
        print(f"gh did not answer about PR {pr}")
        return NO_ANSWER
    if not head.startswith(want):
        print(f"head {head} is not {want}")
        return WRONG_HEAD
    appear_by = clock() + APPEAR_S
    finish_by = None
    answered = clock()
    while True:
        runs = runs_on(head)
        now_head = pr_head(pr)      # after the runs, so a verdict is never older than its head
        if now_head is not None and now_head != head:
            print(f"head moved from {head} to {now_head}")
            return WRONG_HEAD
        if runs is None or now_head is None:
            if clock() - answered >= SILENT_S:
                print(f"gh stopped answering about {head}")
                return NO_ANSWER
        else:
            answered = clock()
            run = newest(runs)
            if run is not None:
                if finish_by is None:
                    finish_by = clock() + FINISH_S
                if run.get("status") == "completed":
                    if run.get("conclusion") == "success":
                        print(f"CI green on {head}")
                        return GREEN
                    print(f"CI NOT green on {head}")
                    print(run.get("workflowName"), run.get("conclusion"), run.get("url"))
                    return RED
        left = (appear_by if finish_by is None else finish_by) - clock()
        if left <= 0:
            if finish_by is None:
                print(f"no CI run appeared for {head}")
                return NO_RUN
            print(f"CI still running after 30 min on {head}")
            return STILL_RUNNING
        sleep(min(APPEAR_POLL_S if finish_by is None else FINISH_POLL_S, left))


class _Args(argparse.ArgumentParser):
    def error(self, message: str):
        # argparse's own 2 would read as "CI is red"
        self.exit(USAGE, f"{self.format_help()}\n{self.prog}: {message}\n")


def main(argv: list[str] | None = None) -> int:
    # no add_help: `--help` falls to `error`, which prints it, and the code stays off 0
    ap = _Args(add_help=False, description="Wait for a PR head's CI; exit 0 only if it is green. "
                                           "Merges nothing. Codes: see the tool's docstring.")
    ap.add_argument("pr", help="the PR's number")
    ap.add_argument("head", help=f"the head commit you expect, or {MIN_HEAD}+ characters of it")
    args = ap.parse_args(argv)
    if not args.pr or len(args.head) < MIN_HEAD:
        # "" is a prefix of every commit, and "a" of a sixteenth of them
        ap.error(f"give a PR, and at least {MIN_HEAD} characters of the head")
    return wait(args.pr, args.head)


if __name__ == "__main__":
    sys.exit(main())
