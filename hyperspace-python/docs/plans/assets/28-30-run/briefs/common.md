# Common brief — plans 28 and 30 (every WP reads this first)

You are one sub-agent of the orchestrator running plans 28 (the node editor)
and 30 (shader nodes) in `Cutaiar/hyperspace` (the Python app under
`hyperspace-python/`). You own exactly one work package (WP). Everything you
need is in your worktree.

## Where you work
- The harness gave you your own git worktree: it is your working directory
  (under `.claude/worktrees/`), on an auto-named branch cut from
  `origin/main`. **Your first three commands**, from that worktree root
  (one plain git command per shell call — compound commands are refused):
  ```
  git fetch origin plan-28-30-integration
  git reset --hard FETCH_HEAD          # HEAD must now be the base SHA in your dispatch, or later
  git branch -m <your branch name from the dispatch>
  ```
  Then `git log --oneline -1` and confirm the base in your report. If the
  rename is refused, keep the auto name and push with
  `git push origin HEAD:refs/heads/<branch name>`, then
  `gh pr create --head <branch name> …`.
- **Run every command from `<your worktree>/hyperspace-python`.** Never
  `cd` to the main checkout `/Users/dallman/antigrav_repos/hyperspace` and
  never touch another worktree. Never check out another branch.
- Base: branch `plan-28-30-integration`. The PR goes into that branch,
  not `main`. Never push to `main`.
- Your decisions file and report file live in the orchestrator's workspace
  (paths in your dispatch). If a write there is refused, write them to
  `<your worktree>/.sdd/<WP>-decisions.md` / `<WP>-report.md` instead (do
  not commit them) and give that path in your reply.
- `uv run …` inside your worktree builds its own `.venv` the first time
  (uv's own Python 3.14, torch included); that is expected. Ignore the
  `VIRTUAL_ENV … does not match` warning.

## What to read, in this order (paths relative to `hyperspace-python/`)
1. This file.
2. `docs/plans/28-30-orchestrator-prompt.md` — ONLY the line ranges your
   dispatch names (your stream's "where it is today", your WP's section,
   and the shared sections 673–763 "Decisions already made / you may make /
   Out of scope", 764–839 "How to orchestrate" (the expected overlaps),
   840–900 "Gates"). Do not read the other stream's WP sections except
   where your dispatch says. Code sites in it are `file:line` as of an
   older commit: re-find them by symbol.
3. The design file for your stream: `docs/plans/30-shader-nodes.md`
   (stream D) or `docs/plans/28-node-editor.md` (stream N). Where the
   prompt and the design differ, the design's *intent* wins; say so in
   your report.
4. `docs/ARCHITECTURE.md` §2 (the frame; the one-frame-lag rule stream N
   is changing) and §3, and the parts of `docs/ENGINEERING.md` that cover
   the modules you touch. `docs/DECISIONS.md` for the rules in force
   (D1–D12 are its "Presets and the desk" rows). `docs/plans/26-render-graph.md`
   for the render graph as built, `27-device-registry.md` for the registry.
5. The code and tests you touch. Tests are the spec of today's behaviour.

## Hard rules (the owner's; do not relitigate)
- **Never touch the owner's real `~/Hyperspace`, nor `~/My Drive/Hyperspace`
  (a Google Drive folder that syncs to another Mac).** Never run the app or
  a tool against the real home. Tests already point `HYPERSPACE_HOME` at a
  tmp folder (`tests/conftest.py`); any script or smoke run you launch
  must set `HYPERSPACE_HOME` to a scratch folder whose `config.toml` has no
  `[library]` section **and lists the APC40 disabled** (the owner's
  collaborator is at the desk: a process that opens it and exits leaves it
  in Generic mode).
- **No preset is edited or added.** Every file under `hyperspace/library/`
  stays byte-identical (`git diff --stat origin/plan-28-30-integration -- hyperspace/library/`
  empty). Every proof uses a fixture under `tests/fixtures/` loaded through
  a scratch library. `tests/fixtures/` is gitignored at the repo root:
  **force-add your fixture files (`git add -f`)** and say so in the PR body.
- **`hyperspace/apc40.py` and `hyperspace/midi.py` are not yours**: the
  desk (the faders, the APC40 map and feel, the desk templates' content,
  the coverage report) is Dylan's work in flight on the same integration
  branch. Never edit those two files. If the integration branch moves
  under you in `routing.py` or `ui_routing.py`, merge
  `origin/plan-28-30-integration` into your branch before the PR and never
  revert a line you did not write.
- **Every new param defaults to today's picture** (a new mix/opacity at
  what the frame does now, a new switch off, a new source at its rest).
- The render stack reads params and never writes one; adapters only
  `feed`; `Router.modulate` is the only caller of `Param.modulate`;
  `Param.apply` is called by `Registry.apply` and (from N0) by
  `Router.modulate` under the frame mark, nowhere else; the hands package
  stays liftable; the core never imports `midi`, `bridge`, `dream`, `osc`,
  `torch`, `leap`. No node/graph method named `apply`, `modulate`,
  `snapshot` or `set_value` in `render.py` / `graph.py` (a test bans the
  names); `graph.py` imports no `params`, `routing`, `library`, `preset`,
  `undo`, `control`, `devices`. New leaf modules (`patch.py`,
  `modifiers.py`) import nothing from the package but `motion` and
  `tapers`.
- The boundary tests listed under "Gates" (prompt lines 840–900) keep
  passing untouched, except the exact changes the prompt allows for your
  WP; name each changed assertion in your PR body with its reason and
  decision number.
- **Every golden frame in `tests/golden/frames/` matches as recorded.**
  No WP re-records a hash. A moved frame is a bug. Only D1 and N4 add
  frames (their fixtures'), recorded once with the one reason the prompt
  gives. The goldens compare only on the gate Mac ("Apple M3 Max" — this
  machine); run `uv run pytest tests/test_golden_frames.py -q` before the PR.
- The sixteen decisions at prompt lines 673–723 are the owner's: build
  them as written. Anything they leave open is yours to decide: decide
  it, build it, and write it down (below). Do not stop to ask about those.
- **Do not edit** `docs/DECISIONS.md`, `docs/DECISION-REGISTER.md`,
  `docs/plans/11-hand-checks.md`, `docs/TESTING-GUIDE.md`,
  `docs/ARCHITECTURE.md/.html`, `docs/CHECKPOINT.md`, `docs/plans/README.md`
  or any `docs/plans/2*.md` / `3*.md`: the docs WPs write those from your
  notes. (Exception: N0 drafts `docs/ARCHITECTURE.md` §2's lag rule, as
  its section says.) You may add docstrings and code comments freely.

## How to work
- TDD where it fits: write the failing test, then the code. Run focused
  tests while iterating; the full gates once before opening the PR.
- Keep your diff to your WP. The prompt lists the overlaps the orchestrator
  expects at integration (lines 764–839); never "fix" a sibling WP's area.
  If something outside your scope blocks you, note it in your report and
  work around it minimally.
- Commit in small, well-named commits. Every commit message ends with:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01A6XK1P4mW5qTKkf6cDGxC6
  ```
- You do not dispatch sub-agents (no helpers, no reviewers). Review comes
  from the orchestrator after your report.
- If you are blocked, or the plan text is contradictory in a way you cannot
  settle from the code, stop and report BLOCKED / NEEDS_CONTEXT with the
  specifics. Bad work is worse than no work.

## Gates — all green before the PR
```
uv run pytest -q                                  # from hyperspace-python; the base count is in your dispatch
uv run ruff check .
uv run pytest tests/test_golden_frames.py -q      # every frame matches on this Mac
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<scratch> uv run hyperspace -ApplePersistenceIgnoreState YES   # windowed smoke run, when your dispatch asks for it
```
Paste the last lines of each into your report.

## Decisions you made: write them down
Create `<workspace>/decisions/<WP>.md` (path in your dispatch) with:
1. **Register-row drafts**, one per decision you took yourself, in
   `docs/DECISION-REGISTER.md`'s row format (see its rows 196–209): title;
   **Built** (what the owner will see or feel); **Other options**;
   **To reverse** (cost); **Rough edge**; **Judge it** (which hand check).
   Leave the row number as `2xx` — the docs WP numbers them from 214.
2. **Hand-check drafts** in `docs/plans/11-hand-checks.md`'s format (bold
   number and title; `Headless:` the tests behind it; the setup; *Pass:* /
   *Fail:* with the likely cause). Number them `X.n` (plan 30) / `Y.n`
   (plan 28); the docs WP numbers them from 220.
3. **As-built notes** in the shape of `docs/plans/26-render-graph.md`
   ("What was built" by WP, "What no person has verified", "Known rough
   edges") for your WP — the docs WP lifts them into the plan file.
4. Anything a document says that your code does not do, or anything in the
   prompt you deliberately did not do, and why.

## The PR
- Push your branch; open a PR **into `plan-28-30-integration`** with
  `gh pr create --base plan-28-30-integration`, titled as your dispatch
  says (`Plan 30 D0: …`). Body: what was built; the goldens recorded (new
  only) or the boundary assertions consciously changed, each with its one
  reason and decision number; the decisions you took (a short list; the
  drafts live in the decisions file); fixtures force-added; the gate
  outputs; for N5 the diff-stat of `apc40.py` / `midi.py` against the base
  (empty). End the body with:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_01A6XK1P4mW5qTKkf6cDGxC6
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
