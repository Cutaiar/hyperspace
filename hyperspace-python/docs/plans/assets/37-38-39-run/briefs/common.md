# Common brief — plans 37, 38 and 39 (every task reads this first)

You are one sub-agent of the orchestrator running plans 37 (nodes as
pictures, and the faces), 38 (hold the projector) and 39 (vision) in
`Cutaiar/hyperspace` (the Python app under `hyperspace-python/`), in
parallel, one branch per plan. You own exactly one task. Everything you
need is in your worktree.

## Where you work
- The harness gave you your own git worktree: it is your working directory
  (under `.claude/worktrees/`), on an auto-named branch. **Your first
  commands**, from that worktree root (one plain git command per shell
  call — compound commands may be refused):
  ```
  git fetch origin <plan branch from your dispatch>
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
- Base: the **plan branch** named in your dispatch (`plan-37-pictures`,
  `plan-38-hold` or `plan-39-vision`). The PR goes into that plan branch,
  not `main` and not the integration branch. Never push to `main`; never
  merge; never rebase a branch another task is on.
- Your decisions file and report file live in the orchestrator's workspace
  (paths in your dispatch, under `/Users/dallman/.claude/jobs/9679624d/tmp/run/`).
  If a write there is refused, write them to `<your worktree>/.run/<task>-…md`
  instead (do not commit them) and give that path in your reply.
- `uv run …` inside your worktree builds its own `.venv` the first time
  (uv's own Python 3.14, torch included, ~1.2 GB); that is expected. Ignore
  the `VIRTUAL_ENV … does not match` warning.

## What to read, in this order (paths relative to `hyperspace-python/`)
1. This file, then your dispatch.
2. `docs/plans/37-38-39-orchestrator-prompt.md` in full (it is short): the
   rules every stream keeps, the file-ownership table (**binding**: the
   files your stream owns, what it may touch in another's, and nothing
   else), the numbers, the merge order.
3. Your plan's spec and build plan (your dispatch names them and the
   sections that are yours), and the spike where the dispatch says so.
4. `docs/ARCHITECTURE.md` §2 (the frame; "Drawing: the render graph") and
   the §1 table rows for the modules you touch, `docs/DECISIONS.md` for the
   rules in force ("The WYSIWYG graph (plan 36)" above all), and
   `docs/plans/36-wysiwyg-graph.md` ("What changed in the build" and
   "Known follow-ups").
5. The code and tests you touch. Tests are the spec of today's behaviour.

## Hard rules (the owner's; do not relitigate)
- **The graph on GRAPH is the whole truth.** No default graph, no hidden
  edge, no auto layout, nothing filled in at load. Every input of every
  node is a drawn wire. A hold never fills in a wire. A thumbnail or a
  worker's shortcut changes where something is read, never what is wired.
- **Alpha is not a mask.** A mask is a pattern — a pixel passes or it does
  not — on its own `mask` wire; it never rides in a picture's alpha.
- **Pictures don't move.** No golden under `tests/golden/` changes except
  where a plan says so with the reason in the commit (only plan 37's P2
  re-records the presets whose pattern is dropped, and that waits for the
  owner). New fixtures add goldens; `tests/fixtures/frame-signatures.json`
  gains cases, loses none.
- **Never touch the owner's real `~/Hyperspace`, nor the Drive library**
  (`[library] path`, a cloud folder synced to another Mac). Never run the
  app or a tool against the real home. Tests already point
  `HYPERSPACE_HOME` at a tmp folder (`tests/conftest.py`); any script or
  smoke run you launch sets `HYPERSPACE_HOME` to a scratch folder whose
  `config.toml` has no `[library]` section and lists no devices (the
  owner's collaborator may be at the desk).
- **No preset is edited or added** under `hyperspace/library/` unless your
  dispatch says so (plan 37 C4 only, and only when the owner's list has
  arrived). Proofs are fixtures under `tests/fixtures/` loaded through a
  scratch library. If `git status` does not show your new fixture, it is
  ignored: `git add -f` it and say so in the PR body.
- **Both Macs on this build** before any preset saved with the new kinds
  is shared: nothing you build saves a new kind into the owner's library.
- The render stack reads params and never writes one; `graph.py` imports
  only the render stack (`tests/test_graph.py::test_graph_imports_only_the_render_stack_and_names_no_write`);
  `import hyperspace.app` imports no gated adapter, no `torch`, no
  `Vision`/`objc` (`tests/test_app_boundary.py`); every new param defaults
  to today's picture (a new switch off, a new mix at what the frame does now).
- **Do not edit** `docs/DECISIONS.md`, `docs/DECISION-REGISTER.md`,
  `docs/plans/11-hand-checks.md`, `docs/TESTING-GUIDE.md`,
  `docs/ARCHITECTURE.md/.html`, `docs/CHECKPOINT.md`, `docs/plans/README.md`
  or any `docs/plans/3*.md` unless your dispatch is a docs task: the docs
  tasks write those from your notes. Docstrings and code comments are
  yours to write freely (cite the plan: `# plan 39 T3: …`).
- You do not dispatch sub-agents (no helpers, no reviewers). Review comes
  from the orchestrator after your report.
- If you are blocked, or the plan text contradicts the code in a way you
  cannot settle, stop and report BLOCKED / NEEDS_CONTEXT with the
  specifics. Bad work is worse than no work.

## How to work
- TDD where it fits: the failing test, then the code. Focused tests while
  iterating; the gates once before the PR.
- Keep your diff to your task and to the files the ownership table gives
  your stream. If you must touch another stream's file, do it in the
  smallest way the table allows and say so in your report.
- Commit in small, well-named commits. **Every commit message ends with:**
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_012HeFJ3coaFYJ9durdEgBjC
  ```

## Gates — all green before the PR (from `hyperspace-python/`)
```
uv run pytest -q                                   # the fast tier; base count in your dispatch
uv run ruff check .
uv run pytest -q tests/test_golden_frames.py       # every golden matches on this Mac; new ones listed
uv run pytest -q --all                             # the full suite, once, before DONE
```
Paste the last lines of each into your report. The goldens compare only
on the gate Mac ("Apple M3 Max" — this machine).

## Decisions you made: write them down
Create `<workspace>/decisions/<task>.md` (path in your dispatch) with:
1. **Register-row drafts**, one per decision you took yourself, in
   `docs/DECISION-REGISTER.md`'s row format (see rows 396–416): title;
   **Answer** (`controller — 2026-10-27`); **Built** (what the owner will
   see or feel); **Other options**; **To reverse** (cost); **Rough edge**;
   **Judge it** (which hand check). Number them `4xx`; the docs task
   numbers them inside your plan's range.
2. **Hand-check drafts** in `docs/plans/11-hand-checks.md`'s format (bold
   number and title with where it runs; `Headless:` the tests behind it;
   the steps; *Pass:* / *Fail:* with the likely cause). Number them
   `AH.n` (plan 37) / `AI.n` (plan 38) / `AJ.n` (plan 39).
3. **As-built notes** for your task in the shape of
   `docs/plans/36-wysiwyg-graph.md`'s "What changed in the build": what
   was built, what differs from the spec and why, what no person has
   verified, known rough edges.
4. Anything a document says that your code does not do, or anything in
   your dispatch you deliberately did not do, and why.

## The PR
- Push your branch; open a PR **into your plan branch** with
  `gh pr create --base <plan branch>`, titled as your dispatch says
  (`Plan 39 T0: …`). Body: what was built; the goldens recorded (new only)
  or the boundary assertions consciously changed, each with its one
  reason; the decisions you took (a short list; the drafts live in the
  decisions file); fixtures force-added; the gate outputs. End the body
  with:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_012HeFJ3coaFYJ9durdEgBjC
  ```
- Do not merge. The orchestrator reviews and merges.

## Report
Write your full report to `<workspace>/reports/<task>-report.md` (path in
your dispatch): what you built, how you tested it (commands + last lines),
files changed, self-review findings, concerns, the PR URL. Then reply with
ONLY (under 15 lines): **Status** (DONE | DONE_WITH_CONCERNS | BLOCKED |
NEEDS_CONTEXT), the commits (short SHA + subject), the PR URL, a one-line
test summary, your concerns, the report path.

After review you may be resumed with findings: fix them, re-run the
covering tests, append a fix report to the same report file, push, and
reply with the same short contract.
