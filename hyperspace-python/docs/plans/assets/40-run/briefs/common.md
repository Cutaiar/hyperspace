# Common brief — plan 40, patches (every task reads this first)

You are one sub-agent of the controller running plan 40 (**patches**: a
group of nodes and its boundary, saved once, spawned anywhere) in
`Cutaiar/hyperspace`, the Python app under `hyperspace-python/`. You own
exactly one task. Everything you need is in your worktree.

## Where you work
- The harness gave you your own git worktree: it is your working directory
  (under `.claude/worktrees/`), on an auto-named branch. **Your first
  commands**, from that worktree root (one plain git command per shell
  call — compound commands may be refused):
  ```
  git fetch origin plan-40-build
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
- Base: **`plan-40-build`** at the SHA in your dispatch. The PR goes into
  `plan-40-build`, not `main`. Never push to `main`; never merge; never
  rebase a branch another task is on.
- Your decisions file and report file live in the controller's workspace
  (paths in your dispatch, under `/Users/dallman/.claude/jobs/45478892/tmp/run/`).
  If a write there is refused, write them to `<your worktree>/.run/<task>-…md`
  instead (do not commit them) and give that path in your reply.
- `uv run …` inside your worktree builds its own `.venv` the first time
  (uv's own Python 3.14, torch included, ~1.2 GB); that is expected. Ignore
  the `VIRTUAL_ENV … does not match` warning.

## What to read, in this order (paths relative to `hyperspace-python/`)
1. This file, then your dispatch.
2. `docs/plans/40-patches.md` — the spec. **Every decision D1–D10 is the
   owner's**: build the "the owner" column, not the recommendation where
   they differ (D3 the conflict sheet, D4 the folded group, D6 no
   conversion, D10 the FX page stays). Read "What is there today (the
   map)" before touching anything; its file:line references are to
   `main` @ f2351a0 and have drifted — the names hold.
3. `docs/plans/40-patches-build.md` — "Global constraints", "Numbers",
   your task's section (your dispatch repeats it verbatim), "Order".
4. `docs/ARCHITECTURE.md` §2 ("Drawing: the render graph", "The WYSIWYG
   graph") and §3 (the control model, 3.3–3.8 above all: the rows, the
   one path, one performer per param, chaining, the binding file);
   `docs/DECISIONS.md` ("The WYSIWYG graph (plan 36)", "Presets and the
   desk", "Undo", "Process"); `docs/plans/36-wysiwyg-graph.md` (the rule);
   `docs/plans/28-node-editor.md` N2, N5, N7 (the canvas, the template
   node — the one subgraph drawn as a node today — collapsed by default).
5. The code and tests you touch. Tests are the spec of today's behaviour.

## Hard rules (the owner's; do not relitigate)
- **The graph on GRAPH is the whole truth** (plan 36): no default graph,
  no hidden edge, no auto layout, nothing filled in at load. A spawn
  attaches nothing by itself (D2); a patch's layout is its own, placed
  where the user clicked. **The one exception is the owner's (D4)**: a
  collapsed group folds its internal cables until `+`. Nothing else may
  hide a cable.
- **The renderer learns nothing.** `graph.build_graph`, `graph.signature`,
  `render.py` and the goldens see the flat graph. **No golden PNG under
  `tests/golden/` changes**; `tests/fixtures/frame-signatures.json` is not
  re-recorded. A group is a fold on the canvas and a list in the file.
- **Through the doors.** Every change to the table, the banks, the graph
  section and the values goes through the calls that exist (`gs.land`,
  `Bindings.add` / `bind` / `replace_owner` / `add_modifier` /
  `set_macros`, `bank.add`, `lib.restore`). No new write path onto a
  `Param`, no new path onto the table. A spawn, a group, an ungroup, a
  "wire as saved" are each **one undo step** (`undo.push(label,
  load=True)` before the first write).
- **No file is written by a spawn.** The preset's dirty dot lights; a save
  writes it. Saving a patch writes `<library>/patches/<slug>.json` and
  nothing else. `bindings.json` is never touched by this plan.
- **Dylan's files are untouched**: `apc40.py`, `midi.py`,
  `bindings.default.json`, the desk diagram and `ui_desk*.py` (D8: the
  browser and spawn are the control window's only).
- **Never touch the owner's real `~/Hyperspace`, nor the Drive library**
  (`[library] path`, a cloud folder synced to another Mac). Never run the
  app or a tool against the real home. Tests already point
  `HYPERSPACE_HOME` at a tmp folder (`tests/conftest.py`); any script or
  smoke run you launch sets `HYPERSPACE_HOME` to a scratch folder whose
  `config.toml` has no `[library]` section and lists no devices (the
  owner's collaborator may be at the desk).
- **No preset is edited or added** under `hyperspace/library/` (T5 removes
  the six fx module files and nothing else). Proofs are fixtures under
  `tests/fixtures/` loaded through a scratch library. **`tests/fixtures/`
  is gitignored**: `git add -f` any new fixture and say so in the PR body.
- **Both Macs on this build** before a preset with `groups` is shared: an
  older build drops the key on its save. Nothing you build saves a new key
  into the owner's library.
- `graph.py` imports only the render stack
  (`tests/test_graph.py::test_graph_imports_only_the_render_stack_and_names_no_write`);
  `import hyperspace.app` imports no gated adapter, no `torch`
  (`tests/test_app_boundary.py`); new modules are leaves like
  `graphmigrate.py` (pure data in, pure data out, nothing imported from the
  app); every new param defaults to today's picture.
- **Style.** Match the surrounding code: docstrings in the repo's voice,
  comments that cite the plan (`# plan 40 T<n>: …`), no new dependencies.
- **Do not edit** `docs/DECISIONS.md`, `docs/DECISION-REGISTER.md`,
  `docs/plans/11-hand-checks.md`, `docs/TESTING-GUIDE.md`,
  `docs/ARCHITECTURE.md/.html`, `docs/ENGINEERING.md`, `docs/SETUP.md`,
  `docs/CHECKPOINT.md`, `docs/plans/README.md` or any `docs/plans/40-*.md`
  unless your dispatch says so (T0's symbol-only sed; T6 the docs task):
  the docs task writes those from your notes. Docstrings and code comments
  are yours to write freely.
- You do not dispatch sub-agents (no helpers, no reviewers). Review comes
  from the controller after your report.
- If you are blocked, or the plan text contradicts the code in a way you
  cannot settle, stop and report BLOCKED / NEEDS_CONTEXT with the
  specifics. Bad work is worse than no work.

## How to work
- TDD where it fits: the failing test, then the code. Focused tests while
  iterating; the gates once before the PR.
- Keep your diff to your task and to the files your dispatch gives you. If
  you must touch a file it does not list, do it in the smallest way and
  say so in your report.
- Commit in small, well-named commits. **Every commit message ends with:**
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_012HeFHywoiCGN2SbvC1U35W
  ```

## Gates — all green before the PR (from `hyperspace-python/`)
```
uv run pytest -q                                   # the fast tier; base count in your dispatch
uv run ruff check <the files you touched>     # the base has 25 pre-existing errors in media/, tools/ingest.py, the plan 39 bench scripts and four tests — not yours; your files are clean
uv run pytest -q --all -m golden                   # every golden matches on this Mac; nothing re-recorded (goldens are behind --all)
uv run pytest -q --all                             # the full suite, once, before DONE
```
Paste the last lines of each into your report. The goldens compare only
on the gate Mac ("Apple M3 Max" — this machine). Two media tests
(`test_media_channels.py::test_rapid_switching_with_slow_closes_stays_fast_and_balances`,
`test_media_core.py::test_bad_file_is_an_error`) are load-flaky under
`-n auto` and pass serially; if your `--all` shows only those two, re-run
them serially and report that.

## Decisions you made: write them down
Create `<workspace>/decisions/<task>.md` (path in your dispatch) with:
1. **Register-row drafts**, one per decision you took yourself where the
   spec was silent, in `docs/DECISION-REGISTER.md`'s row format (see rows
   461–470): title; **Answer** (`controller — 2026-10-27`); **Built**
   (what the owner will see or feel); **Other options**; **To reverse**
   (cost); **Rough edge**; **Judge it** (which hand check). Number them
   `50x`; the docs task numbers them inside 501–525 (the prompt's 471–495 were taken by plans 37–39's later rows; the controller's ruling 12).
2. **Hand-check drafts** in `docs/plans/11-hand-checks.md`'s format (bold
   number and title with where it runs; `Headless:` the tests behind it;
   the steps; *Pass:* / *Fail:* with the likely cause) only where your
   task adds something the spec's eight checks (394–401, group AK) do not
   cover. Number them `AK.n`.
3. **As-built notes** for your task in the shape of
   `docs/plans/36-wysiwyg-graph.md`'s "What changed in the build": what
   was built, what differs from the spec and why, what no person has
   verified, known rough edges.
4. Anything a document says that your code does not do, or anything in
   your dispatch you deliberately did not do, and why.

## The PR
- Push your branch; open a PR **into `plan-40-build`** with
  `gh pr create --base plan-40-build`, titled as your dispatch says
  (`Plan 40 T0: …`). Body: what was built; the boundary assertions
  consciously changed, each with its one reason; the decisions you took
  (a short list; the drafts live in the decisions file); fixtures
  force-added; the gate outputs. End the body with:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  https://claude.ai/code/session_012HeFHywoiCGN2SbvC1U35W
  ```
- Do not merge. The controller reviews and merges.

## Report
Write your full report to `<workspace>/reports/<task>-report.md` (path in
your dispatch): what you built, where the spec and the build differ and
why, how you tested it (commands + last lines: fast tier, goldens, full
suite), files changed, self-review findings, concerns, the rulings you
made, the PR URL. Then reply with ONLY (under 15 lines): **Status** (DONE
| DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT), the commits (short SHA +
subject), the PR URL, a one-line test summary, your concerns, the report
path.

After review you may be resumed with findings: fix them, re-run the
covering tests, append a fix report to the same report file, push, and
reply with the same short contract.
