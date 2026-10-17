# Common brief — plans 24, 26 and 27 (every WP reads this first)

You are one sub-agent of the orchestrator running plans 24, 26 and 27 in
`Cutaiar/hyperspace` (the Python app under `hyperspace-python/`). You own
exactly one work package (WP). Everything you need is in your worktree.

## Where you work
- The harness gave you your own git worktree: it is your working directory
  (under `.claude/worktrees/`), on an auto-named branch cut from
  `origin/main`. **Your first three commands**, from that worktree root:
  ```
  git fetch origin plan-24-26-27-integration
  git reset --hard FETCH_HEAD          # HEAD must now be cd9106d or later
  git branch -m <your branch name from the dispatch>
  ```
  Then `git log --oneline -1` and confirm the base in your report. If the
  rename is refused, keep the auto name and push with
  `git push origin HEAD:refs/heads/<branch name>`, then
  `gh pr create --head <branch name> …`.
- **Run every command from `<your worktree>/hyperspace-python`.** Never
  `cd` to the main checkout `/Users/dallman/antigrav_repos/hyperspace` and
  never touch another worktree. Never check out another branch.
- Base: branch `plan-24-26-27-integration`. The PR goes into that branch,
  not `main`. Never push to `main`.
- Your decisions file and report file live in the orchestrator's workspace
  (paths in your dispatch). If a write there is refused, write them to
  `<your worktree>/.sdd/<WP>-decisions.md` / `<WP>-report.md` instead (do
  not commit them) and give that path in your reply.
- `uv run …` inside your worktree builds its own `.venv` the first time
  (torch included); that is expected. Ignore the `VIRTUAL_ENV … does not
  match` warning.

## What to read, in this order (paths relative to `hyperspace-python/`)
1. This file.
2. `docs/plans/24-26-27-orchestrator-prompt.md` — ONLY the line ranges your
   dispatch names (your stream's "where it is today", your WP's section,
   and the shared sections 929–1115 "What landed / Decisions / Out of
   scope", 1116–1176 "How to orchestrate", 1177–1245 "Gates"). Do not
   read the other streams' sections. Code sites in it are `file:line`
   as of an older commit: re-find them by symbol.
3. `docs/ARCHITECTURE.md` §1–§3 and the parts of `docs/ENGINEERING.md`
   that cover the modules you touch. `docs/DECISIONS.md` for the rules in
   force (D1–D12 are its "Presets and the desk" rows).
4. The code and tests you touch. Tests are the spec of today's behaviour.

## Hard rules (the owner's; do not relitigate)
- **Never touch the owner's real `~/Hyperspace`, nor `~/My Drive/Hyperspace`
  (a Google Drive folder that syncs to another Mac).** Never run the app or
  a tool against the real home. Tests already point `HYPERSPACE_HOME` at a
  tmp folder (`tests/conftest.py`); any script or smoke run you launch
  must set `HYPERSPACE_HOME` to a scratch folder whose `config.toml` has no
  `[library]` section.
- **No preset is edited or added.** Every file under `hyperspace/library/`
  stays byte-identical (`git diff --stat -- hyperspace/library/` empty).
  Every proof uses a fixture under `tests/fixtures/` loaded through a
  scratch library. `tests/fixtures/` is gitignored at the repo root:
  **force-add your fixture files (`git add -f`)** and say so in the PR body.
- **Every new param defaults to today's picture** (a new mix/opacity at
  what the frame does now, a new switch off, a new source at its rest).
- The render stack reads params and never writes one; adapters only
  `feed`; `Router.modulate` is the only caller of `Param.modulate`; the
  hands package (`hands/core.py`, `signal.py`, `tape.py`) stays liftable;
  the core never imports `midi`, `bridge`, `dream`, `osc`, `torch`, `leap`.
  No node/graph method named `apply`, `modulate`, `snapshot` or `set_value`
  in `render.py` (a test bans the names). Use `run` / `evaluate`.
- The boundary tests listed under "Gates" (prompt lines 1177–1245) keep
  passing untouched, except the exact changes the prompt allows for your
  WP; name each changed assertion in your PR body with its reason.
- The 24 decisions at prompt lines 975–1072 are the owner's: build them as
  written. Anything they leave open is yours to decide: decide it, build
  it, and write it down (below). Do not stop to ask about those.
- **Do not edit** `docs/DECISIONS.md`, `docs/DECISION-REGISTER.md`,
  `docs/plans/11-hand-checks.md`, `docs/TESTING-GUIDE.md`,
  `docs/ARCHITECTURE.md/.html`, `docs/CHECKPOINT.md`, `docs/plans/README.md`
  or any `docs/plans/2*.md`: the docs WPs write those from your notes.
  (Exceptions only where your WP section says so, e.g. A0's naming rule in
  ENGINEERING.md.) You may add docstrings and code comments freely.

## How to work
- TDD where it fits: write the failing test, then the code. Run focused
  tests while iterating; the full gates once before opening the PR.
- Keep your diff to your WP. The prompt lists the overlaps the orchestrator
  expects at integration (lines 1116–1176); never "fix" a sibling WP's area.
  If something outside your scope blocks you, note it in your report and
  work around it minimally.
- Commit in small, well-named commits. Every commit message ends with:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01B185QGNNV4gpnBQEBD6k3z
  ```
- You do not dispatch sub-agents (no helpers, no reviewers). Review comes
  from the orchestrator after your report.
- If you are blocked, or the plan text is contradictory in a way you cannot
  settle from the code, stop and report BLOCKED / NEEDS_CONTEXT with the
  specifics. Bad work is worse than no work.

## Gates — all green before the PR
```
uv run pytest -q            # from hyperspace-python; today 1885 passed, 2 skipped
uv run ruff check .
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<scratch> uv run hyperspace   # windowed smoke run, when your dispatch asks for it
```
Paste the last lines of each into your report.

## Decisions you made: write them down
Create `<workspace>/decisions/<WP>.md` (path in your dispatch) with:
1. **Register-row drafts**, one per decision you took yourself, in
   `docs/DECISION-REGISTER.md`'s row format (see its rows 87–109): title;
   **Built** (what the owner will see or feel); **Other options**;
   **To reverse** (cost); **Rough edge**; **Judge it** (which hand check).
   Leave the row number as `1xx` — the docs WP numbers them.
2. **Hand-check drafts** in `docs/plans/11-hand-checks.md`'s format (bold
   number and title; `Headless:` the tests behind it; the setup; *Pass:* /
   *Fail:* with the likely cause). Number them `U.n` / `V.n` / `W.n`.
3. **As-built notes** in the shape of `docs/plans/21-outputs-and-the-hands.md`
   ("At the machine", "Code", "Tests", what no person has verified, rough
   edges) for your WP — the docs WP lifts them into the plan file.
4. Anything a document says that your code does not do, or anything in the
   prompt you deliberately did not do, and why.

## The PR
- Push your branch; open a PR **into `plan-24-26-27-integration`** with
  `gh pr create --base plan-24-26-27-integration`, titled as your dispatch
  says (`Plan 26 A0: …`). Body: what was built; the goldens re-recorded or
  the boundary assertions consciously changed, each with its one reason;
  the decisions you took (a short list; the drafts live in the decisions
  file); fixtures force-added; the gate outputs. End the body with:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_01B185QGNNV4gpnBQEBD6k3z
  ```
- Do not merge. The orchestrator reviews and merges.

## Report
Write your full report to `<workspace>/reports/<WP>-report.md` (path in
your dispatch): what you built, how you tested it (commands + last lines),
files changed, self-review findings, concerns, the PR URL. Then reply with
ONLY (under 15 lines): **Status** (DONE | DONE_WITH_CONCERNS | BLOCKED |
NEEDS_CONTEXT), the commits (short SHA + subject), the PR URL, a one-line
test summary, your concerns, the report path.

After review you may be resumed with findings: fix them, re-run the
covering tests, append a fix report to the same report file (what changed,
the tests, the command, the output), push, and reply with the same short
contract.
