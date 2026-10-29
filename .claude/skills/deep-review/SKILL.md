---
name: deep-review
description: An independent deep review of the current branch against the project's own rules (REVIEW.md, ARCHITECTURE.md, DECISIONS.md, CHECKPOINT.md) before it merges. Use when asked for an architectural review, a final pass, or a deep review of a branch or PR in this repo.
---

# Deep review

Review the current branch before it merges, the way PR #289 was reviewed:

- an independent reviewer, given the code and the project's rules but not
  the author's conclusions;
- then each finding reproduced before it is fixed.

The checklist is [`REVIEW.md`](../../../REVIEW.md) at the repo root. Read
it first.

It runs when asked, in a session on the branch. Running it on every PR,
unattended, is an idea in `hyperspace-python/docs/CHECKPOINT.md` under
"Ideas for later": the ways to trigger it, and the PR mode it would need
(post the findings as one comment, no pushes).

## 1. Fix the scope

- Run `git fetch origin main`. The base is `git merge-base HEAD
  origin/main`, and the diff is `git diff <base>..HEAD`.
- Read the commit list. If the branch went through several designs, the
  reviewer should look for leftovers from the ones it dropped.
- Don't merge `main` into the branch until the review is back. That keeps
  the reviewer's diff the branch's own. Commits of your own during the
  review should only be docs.

## 2. Brief one reviewer and let it work

Spawn one general-purpose agent, read-only (no edits, commits or pushes),
in the background. Its brief:

- the branch and the diff command;
- one plain line per changed file saying what it does: facts, not your
  assessment and not what you're worried about;
- the rules to read:
  - `REVIEW.md`;
  - `hyperspace-python/docs/ARCHITECTURE.md`, `DECISIONS.md` and
    `CHECKPOINT.md`;
  - the contract at the top of `hyperspace-python/hyperspace/hotreload.py`;
  - for any file the branch writes, how its loader handles schemas,
    migrations and backups;
- how to run the tests (below), and the base branch's own failures, so it
  ignores them;
- the report's shape:
  - a ranked list of findings, each with file:line, a concrete failure
    scenario or the rule it breaks, and a fix;
  - "should fix before merge" kept separate from "follow-up", plus
    "checked and fine";
  - under about 800 words.

While it runs, don't review the same ground yourself. Useful meanwhile:

- dry-run the merge with `git merge-tree --write-tree HEAD origin/main`;
- write the owner's new decisions into DECISIONS.md.

## 3. Act on the report

- **Reproduce first.** Reproduce every "should fix" finding, with a script
  or a test that fails, before fixing it. A finding you can't reproduce
  goes back to the owner with what you tried.
- **Fix with a test.** Each fix comes with the test that fails without it.
- **Follow-ups:** fix the cheap ones in the same pass, and list the rest
  for the owner in one line each, with why they can wait.
- **Merge and recheck.** Merge `origin/main`, re-run the changed packages'
  tests and `ruff`, compare the failures with the base branch's, then
  push.
- **Write up compatibility in the PR:** what changes on disk, what an
  older build makes of the new files, and whether to restart rather than
  hot reload.

## Running the tests in a Linux cloud container

The app targets macOS, so `uv sync` fails on Linux: the Ultraleap SDK
(`leapc-cffi`) won't build. Make a small venv in the scratchpad instead:

```bash
uv venv -p 3.12 "$SP/venv"
apt-get install -y libportaudio2 libsndfile1        # sounddevice, soundfile
v=$(grep -A1 'name = "imgui-bundle"' hyperspace-python/uv.lock | grep -oP 'version = "\K[^"]+')
VIRTUAL_ENV="$SP/venv" uv pip install "imgui-bundle==$v" numpy pytest pytest-xdist glfw \
    moderngl pyopengl pillow mido cffi python-osc sounddevice soundfile ruff
cd hyperspace-python && VIRTUAL_ENV="$SP/venv" uv pip install --no-deps -e .
"$SP/venv/bin/python" -m pytest -q -p no:cacheprovider tests/test_motion.py   # for example
```

- `$SP` is the session's scratchpad directory.
- Pin `imgui-bundle` to the version in `uv.lock`, because a newer one
  renames API the panel uses.
- A test that imports a module the venv lacks (`torch`, `leap`) can't run
  here. Say which ones you skipped.
- Some UI tests fail on Linux before any change: the macOS fonts are
  missing and labels get truncated. Run the same files on the base branch
  (`git stash` or a worktree) and compare the lists of failures.
