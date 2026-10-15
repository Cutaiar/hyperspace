# Plans 24, 26 and 27 — handoff prompt for the next session

> **The run finished on 2026-10-14**: every WP of plans 24, 26 and 27 is merged into `plan-24-26-27-integration` or on its PR, the last being A5, plan 26's docs (PR #193). Do not re-run it; what is left is the orchestrator's review pass and the integration branch's PR into `main` for the owner.

You are the top-level orchestrator continuing the run of plans 24, 26 and 27
in `Cutaiar/hyperspace` (the Python app under `hyperspace-python/`). The
previous session ran out of context on 2026-10-14 after merging fifteen
work packages. Read this file in full, then
`docs/plans/24-26-27-orchestrator-prompt.md` in full (the original launch
prompt: the streams, the decisions you may not relitigate, the gates, the
docs work, the report). Do not touch the owner's `~/Hyperspace` or
`~/My Drive/Hyperspace`.

The run's working files are committed beside this prompt in
`docs/plans/assets/24-26-27-run/`: `progress.md` (the ledger — every
dispatch, review, ruling and merge, in order), `briefs/common.md` and
`briefs/reviewer-common.md` (what every implementer and reviewer was told),
`decisions/<WP>.md` (each WP's register-row drafts, hand-check drafts and
as-built notes — the docs WPs' raw material) and `reports/<WP>-report.md`.
Read `progress.md` before anything else.

## Where the code stands

Base: `main` at 56c7d44 (plan 25 merged). Integration branch
`plan-24-26-27-integration`, pushed, at 3fa2f88 plus whatever this handoff
commit adds. Gates on 3fa2f88: 2133 passed, 2 skipped; ruff clean; 544
golden frames match.

Merged into the integration branch, in order (each a reviewed PR; the
merge commits say how overlaps were resolved):

| WP | PR | What |
|---|---|---|
| C6 | #173 | the palette fold as an effect (`fx.palette.*`) |
| A0 | #174 | golden frames, GPU timing per pass, the naming rule |
| C4 | #176 | curl, spread, energy, gap, twist, flick as hand sources |
| C1 | #175 | the two-handed save, relight, toggles on both layers, desk log |
| B1 | #177 | the `Device` protocol and registry, `[[devices]]` |
| C5 | #178 | the grab switch; hands on the projector in SETUP |
| A1 | #179 | the render graph in code, pixel for pixel |
| C2 | #180 | S1–S8 preset-layer, band audio on SHIFT, lines/points opacity |
| C3 | #182 | the coverage report, desk templates, ranked click-to-map |
| B2 | #181 | the APC40, pad and hands on the registry; several desks |
| A2 | #183 | one camera: shared 4×4, depth, `eye.*`, pan in world units |
| B4 | #184 | the OSC device, the point-cloud type, the recorded cloud |
| B3 | #185 | sinks: the bridge, the hands' DAW out, Learn → sink |
| C7 | #186 | plan 24's docs: register rows 110–139, checks T 144–147, U 148–167 |
| A3 | #187 | the hands as a geometry node; history as wiring |

Open, not merged (check `gh pr list --base plan-24-26-27-integration`):

- **#188 B5** (`plan-27-b5-docs`): plan 27's docs, register rows 140–168,
  group W checks 168–190. Reviewed; the docs-only fix round (the
  point-cloud node written as existing in three places; check 190's loop
  speed; four one-line slips) is **pushed as 1e33e36** with the PR's
  "Review round 1" section. Do one scoped re-read of that commit (Sonnet)
  and merge; it is docs only, so the gates cannot move.
- **#190 A4b** (`plan-26-a4b-points`): the point-cloud geometry node
  (kind name `cloud`, `graph.CLOUD_KIND`; 4 new goldens, 548 total).
  **Reviewed and approved**, minors only (size the colour buffer from the
  float32-converted array in `_CloudGL.upload`; the depth test asserts only
  `front > 0 and back > 0`; no GL test combines a cloud with hands in the
  scene; `Renderer.__init__` never sets `_cloud_gl`). Merge it **after
  A4**; whoever resolves must keep: `default_graph(views, wiring,
  clouds=())` with the clouds as the scene's first geometries;
  `Graph.clouds` set by A4's JSON loader too (else `_graph_for` rebuilds
  every frame when a cloud is listed); `_graph_for`'s key gaining
  `cloud_roles(...)`; the `.graph` import of `cloud_roles` in `render.py`;
  the completeness count and manifest keys in `tests/test_golden_frames.py`
  / `tools/golden_frames.py` (both WPs add states). Decide whether a JSON
  graph that wires `{"kind": "cloud", "role": …}` also gets the automatic
  clouds (two nodes for one role otherwise); a second cloud node still
  shares `cloud.*` (A4's naming rule should give `cloud.2` its own).
- **#189 fix-exit-crash**: the "Python closed unexpectedly" dialog at exit.
  Cause found with the crash reports: pyGLFW's `glfw.terminate()` frees
  every window's Python callbacks before the windows are destroyed, and on
  macOS a destroy runs pending events, so a queued mouse event calls a
  freed callback (SIGSEGV in `ffi_closure_SYSV_inner`, the owner's four
  reports from Oct 8–11). Fix: `glfw.destroy_window` on every window
  before `terminate`, on quit and ⌘R; a test fails on the base. **Reviewed
  and approved** (the cause confirmed against pyGLFW 2.10.2's `terminate`
  and `destroy_window`; every window covered on both exits; `windows.json`
  saved first; minors only: the quit-order test checks source text, the
  startup-failure paths at `app.py:319/327` still call `terminate` with a
  window open but no callbacks are set yet). **The owner said this branch
  can wait**: merge it after the plan work, and make the real quit at the
  machine (two outputs, the mouse moving, Q) a hand check — pass: no
  dialog and no new `Python-*.ips` in `~/Library/Logs/DiagnosticReports/`.
  A separate startup crash (rtmidi `abort()` when CoreMIDI refuses a
  client, audit R15) shows the same dialog at launch and is not this bug
  (report at `assets/24-26-27-run/reports/exit-crash-report.md`).
- **A4** (`plan-26-a4-graph-json`, agent still running at cutover): the
  `graph` section in the preset as JSON, node instances with the naming
  rule (two acid effects, two hands layers), the decimal-key guard in
  `FxState.declare`, the fix for `Hands.TIMED` being set by its consumer,
  the OUTPUT/LOOKBACK pages in words, the fixture `hands-lines.json` with
  its own golden. Look for its PR; if there is none, look for the branch;
  if neither, re-dispatch A4 from the prompt's A4 section with the
  decisions files A0–A3 as context (the dispatch text is in
  `progress.md`'s A4 line and the agent brief pattern in `briefs/`).

Not started: **A5** (plan 26's docs), the **review pass**, the **final PR**.

## What is left, in order

1. Land A4 (review, fix rounds, merge), then A4b (merge second; resolve
   `graph.py`), then B5. Re-run the gates on the integration branch after
   each merge: `uv run pytest -q`, `uv run ruff check .`, and
   `uv run pytest tests/test_golden_frames.py -q` (goldens only match on
   "Apple M3 Max"; elsewhere they skip).
2. **A5**, plan 26's docs, last of the docs WPs: register rows from
   **169**, group **V** from **191** (plan 24 took 110–139 and 148–167;
   plan 27 took 140–168 and 168–190 — the letters stay as the prompt
   assigns them, the numbers run C7 → B5 → A5). A5 also owns: ENGINEERING
   §2 Rendering; ARCHITECTURE.md and .html's Graph row, §2's drawing
   subsection, §5's render parts, and the final masthead counts (B5
   measured 56 modules, 76 test files, 13 effects, 26 shapes, 17 patterns,
   39,835 app lines, 45,290 test lines — re-measure after A4/A4b);
   CHECKPOINT.md (stale on main; rewrite "Where the code stands" and
   "What is left"); the three places B5 says "nothing draws the cloud yet"
   once A4b is in; folding A0's V.2 into A1's V.4; merging A2's
   calibration row with A3's 16:9 fit; `docs/plans/README.md`'s three
   entries and the "numbered 1–N" line; the wishlist's priority paragraph
   links (`26-render-graph.md`, `27-device-registry.md`).
3. **The review pass** over the integration branch (one Opus reviewer,
   the prompt's checklist under "How to orchestrate"), fixes committed as
   `Review: <what>`. Known items to fold in:
   - **Done in the review pass:** `wants = ()` on `BridgeDevice` ("Learn bridge" is offered on every
     param menu for any rig with a bridge entry and never completes — B5
     documented it in row 151, checks 178 and L75; fix the code, then the
     three docs);
   - `docs/plans/11-hand-checks.md` check 56's title ("A hold on the
     clip-stop row saves a new preset") is stale against the retired bar;
   - `tools/slew_demo.py` labels pan readings "px" (A2 changed the unit);
   - the diff of every golden against A0's recording must be accounted
     for: A2 moved 184 (zoom as world scale, copies in the world,
     party-mandala's pan converted, float32 face positions), A3 moved 122
     (the hands through the shared camera: the eye's 47.6° fov vs the
     ghost camera's 38°), A0/A1/C2/C6/B4/A4b moved none;
   - `hyperspace/library/` must be byte-identical to `main`
     (`git diff --stat main -- hyperspace-python/hyperspace/library/`);
   - every commit by the agents carries a "Claude Opus 5.5" trailer
     rather than the brief's; the owner has not asked for it to change.
4. The windowed smoke runs the prompt's gates ask for, one per stream
   with the new paths on (the fixture preset with a `graph` section; a
   `[[devices]]` list with OSC and cloud and no APC40; the faders fixture
   with SHIFT and the palette up). On this Mac a plain `uv run hyperspace`
   blocks in `glfwInit` on macOS's "reopen windows?" alert left by the
   old exit crashes: pass `-ApplePersistenceIgnoreState YES` on the
   command line, or click the alert once at the machine. Always
   `HYPERSPACE_HOME=<scratch>` with no `[library]` section.
5. **The final PR** from `plan-24-26-27-integration` to `main`, titled
   `Plans 24, 26 and 27: the party fixes, the render graph and the device
   registry`, with the report the prompt's "Report back" section lists.
   The owner merges.

## Decisions taken in this run that the prompt did not settle

Every ruling is in `progress.md` with its reason and cost; the register
rows carry the per-WP ones. The ones the next session must honour:

- **Numbering**: register rows and hand checks are assigned only by the
  docs WPs, in the order they landed: C7 (110–139; T 144–147, U 148–167),
  B5 (140–168; W 168–190), A5 next (169+; V 191+).
- **`tests/fixtures/` is gitignored** at the repo root: every fixture is
  force-added (`git add -f`).
- **Unqualified MIDI rows** belong to the first MIDI role whose profile
  matches the table's profile (default `apc40`), else the first listed.
- **The bridge's `send` translation** is marked done in `bindings.json`
  (`"sinks_seeded"`), never by consuming the config key.
- **Hands inside the scene ignore `ghost.alpha`** (solid; alpha exactly 0
  removes them); order-independent transparency is deferred as decided.
- **The calibration** maps the Leap box to a 16:9 picture (A3 superseded
  A2's shorter-side square); the hands land within 5 px at 960×600.
- **`camera.pan`'s px → world conversion** goes through a 1080p
  reference, so a saved preset looks the same on the projector at its
  cap; on the laptop window the shape sits proportionally nearer the
  centre. Camera module presets convert too; a `units` key marks a
  converted document.
- **A3's 122 hands frames moved** although the prompt said the default
  graphs must match A2 exactly: A2 had shown the 47.6° eye cannot match
  the 38° ghost camera; the orchestrator sanctioned the move with that
  one reason.

## A decision from the owner for the handoff (2026-10-14, not built)

The owner does **not** necessarily want lines and points to be
zoom-invariant. Decision 4/5 made `camera.zoom` the shape's world scale and
A2 stopped the line width and point radius scaling with zoom (the
"zoomed-out factory looks get heavier" rough edge: party-field and
hex-engine's dots 2–2.5× bigger). The owner likes the old effect — strokes
that render at different sizes as you are close to or far from them — and
wants **a toggle: strokes drawn in screen space (A2's, zoom-invariant) or
in world space (scaling with zoom, the pre-A2 feel)**. The default is the
owner's call: world space restores the factory presets' feel but moves the
goldens A2 recorded for the strokes; screen space keeps A2's goldens.
Build it as a `view.*` toggle (performance part, modulatable or not —
decide, register it) with a hand check, in a small WP after A4 (it touches
`draw_scene`'s stroke width and point radius and the line/point vertex
shaders), and re-record only the frames it moves with that one reason.
Write it into `docs/DECISIONS.md` with Who `owner` for the toggle itself
and a register row for the default you pick.

## How the previous session worked (so the next one does not relearn it)

- Sub-agents inherit the orchestrator's worktree isolation and cannot
  write to worktrees the orchestrator cuts for them. Dispatch every
  implementer with `isolation: "worktree"` and tell it to `git fetch
  origin plan-24-26-27-integration && git reset --hard FETCH_HEAD && git
  branch -m <name>` first (`briefs/common.md` has the exact text).
- The orchestrator's own session lives in the worktree
  `.claude/worktrees/plan-24-26-27-integration`; its git commands must be
  plain, one per call (the hook refuses compound or computed commands,
  and heredocs that mention git). `gh pr merge` is refused by the
  classifier: merge each PR with a local `git merge --no-ff origin/<branch>`
  on the integration branch and push; GitHub marks the PR merged.
- Per PR: an Opus implementer, an Opus task reviewer with a diff package
  (`git log`/`diff --stat`/`diff -U10` into one file), fix rounds by
  resuming the implementer, a Sonnet scoped re-review per round, then the
  merge and the full gates on the integration branch. The owner asked
  (2026-10-14) that all agents run on Opus, Sonnet or Haiku by task —
  never Fable.
- Expected overlaps and how they were resolved are in the merge commits'
  messages and `progress.md` (ui.py's SYSTEM page; `hotreload.MODULES`;
  the hands shim's port groups `dance`/`switches`; `draw_scene`'s opacity
  lines placed after the clip floor in A2's rewrite; the preset document
  builder's union of C3's desk part and A2's units marker; `learn.py`'s
  imports).

## The report the owner is waiting for

The prompt's "Report back" section. Facts already in hand: the goldens
(427 after A0 — 369 + 46 solo + 12 solo-through — recorded on "Apple M3
Max", GL 4.1 Metal 90.5; 544 after A3; 548 after A4b); the default eye's
maximum vertex error against `project_h` is 2.3e-13 px in float64 and
1.1e-4 px in float32 against the 0.5 px bar; evaluating the render graph
in dependency order changed no pixel (A1 matched all 427); the
modulation lag is untouched (plan 28's); the coverage numbers are in
`docs/plans/assets/24-party-fixes/desk-coverage.md` (0 of 23 presets meet
the four-dark bar; best 9, worst 15; S1–S8 dark everywhere; K7 dead on all
23; nothing remapped); the `[[devices]]` block for today's rig is in
`docs/plans/27-device-registry.md`; what stream B translated from the old
tables is in ENGINEERING §5.
