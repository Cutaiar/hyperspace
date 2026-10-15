# The review pass — plans 24, 26 and 27 on `plan-24-26-27-integration`

You are the whole-branch reviewer for the run of plans 24, 26 and 27 in
Cutaiar/hyperspace (the Python app under `hyperspace-python/`), before the
final PR to `main`. Every WP had its own task review and fix rounds; this is
the pass the launch prompt asks for over the merged branch. Read-only:
change no file, branch or index; no sub-agents; a focused test for a
specific doubt is allowed (say what you ran). The fixes are dispatched by
the orchestrator from your findings, as commits `Review: <what>`.

## Inputs
- The branch: the integration worktree at
  `/Users/dallman/antigrav_repos/hyperspace/.claude/worktrees/plan-24-26-27-integration`
  (HEAD = `73e2bb6`; base `main` at 56c7d44). Read code there.
- The diff package (merge-base..HEAD: commit list, stat, full diff
  -U10 — large; read the stat first, then the diff by file as you need it):
  `/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/reviews/review-pass-diff.md`
- The launch prompt: `hyperspace-python/docs/plans/24-26-27-orchestrator-prompt.md`
  (in the worktree). Lines 1116–1176 "How to orchestrate" hold the
  checklist this pass exists for; 1177–1245 the gates and the tests that
  may change only as stated; 975–1072 the owner's decisions.
- The run's ledger `hyperspace-python/docs/plans/assets/24-26-27-run/progress.md`
  (every ruling, every deferred minor), the decisions files under
  `.../decisions/` and the reports under `.../reports/`.
- The as-built docs the three docs WPs wrote: `docs/plans/24-party-fixes.md`,
  `26-render-graph.md`, `27-device-registry.md`; `docs/DECISION-REGISTER.md`
  rows 110–N; `docs/plans/11-hand-checks.md` T 144–147, U, W, V.

## The checklist (the prompt's, verbatim in substance) — answer every item
1. **A golden that moved without a reason.** Diff every frame in
   `tests/golden/frames/` against A0's recording (A0's manifest is
   `git show bf41438:hyperspace-python/tests/golden/frames/frames.json`
   in the worktree — A0 merged at bf41438; A2's re-recording is at the
   merge of PR #183; A3's at 3fa2f88; A2b's and A4's/A4b's after). The
   accounting the ledger holds: A2 moved 184 (zoom as world scale, copies
   in the world, party-mandala's pan converted, float32 face positions);
   A3 moved 122 (the hands through the shared camera: the eye's 47.6°
   fov vs the ghost camera's 38°, sanctioned by the orchestrator); A2b
   moved 212 + A4's 4 hands-lines scene frames (strokes back in world
   space by default, the owner's 2026-10-14 decision); A0/A1/C2/C6/B4/A4b
   moved none, A4 added 8, A4b added 4. Confirm the counts from the
   manifests and name any frame whose move no WP accounts for.
2. **The hands flipped, mirrored or scaled twice**: `ghost.mirror`, the
   output flips (`Switches.flip_x/y`), the shared camera and the Leap
   calibration all touch the same pixels. Trace one hand point through
   `ghost.calibration` → the eye → `Output`'s flip and say where each
   flip/mirror/scale happens exactly once.
3. **A second output in another context** (`Presenter`): after A3/A4 the
   hand-off must still carry hands-over, readout and dim; and now a
   second hands node (`ghost.2`) on the glass.
4. **A device that raises on `open` or `poll`**: the frame goes on, the
   SYSTEM line says `error`, the retry schedule runs, nothing else changes.
5. **A preset or `bindings.json` from before this run** loads with no note
   and no dirt (`camera.pan` in px converted silently; no `graph` section;
   no `units` key; no `view.screen_strokes`; a `bindings.json` without
   `sinks_seeded`).
6. **A missing device at launch** (`lost`): its rows wait, the desk shows
   dark, plugging it in later brings it up with its feedback.
7. **The two-handed save on a filled slot**: the old preset's file is
   untouched and still in the list, the slot holds the new preset, the new
   one is loaded, the pad blinks, the trash is unchanged, a SAVE press
   with no pad does nothing. Under SHIFT the same.
8. **The toggles under SHIFT**: points, lines, faces, rotate from both
   layers, their LEDs right after a load on either layer.
9. **The coverage report** regenerates byte-identical on a second run
   (`tools/desk_coverage.py` or whatever C3 named it; run it twice into a
   scratch folder and diff; never against `~/Hyperspace`).
10. `hyperspace/library/` byte-identical to `main`:
    `git diff --stat main -- hyperspace-python/hyperspace/library/` empty.
11. The invariants: the render stack reads params and never writes one
    (grep `render.py`, `graph.py`, `ghost.py`, `lookback.py`, `fx.py` for
    `.set_value(`, `.modulate(`, `.apply(`); `Router.modulate` the only
    caller of `Param.modulate`; no new module imports `torch` outside
    `dream.py`; the core never imports `midi`, `bridge`, `dream`, `osc`,
    `torch`, `leap`; `graph.py` imports only the render stack.

## Known items to confirm fixed or to fix (the orchestrator's list)
- `wants = ()` on `BridgeDevice` ("Learn bridge" offered on every param
  menu for any rig with a bridge entry and never completes; B5 documented
  it in register row 151, checks 178 and L75): the code fix and then those
  three docs' "Known: … cancel it" text.
- `docs/plans/11-hand-checks.md` check 56's title ("A hold on the clip-stop
  row saves a new preset") is stale against the retired bar.
- `tools/slew_demo.py` labels pan readings "px" (A2 changed the unit).
- A4b's approved minors: size the colour buffer from the float32-converted
  array in `_CloudGL.upload`; the depth test asserts only `front > 0 and
  back > 0`; no GL test combines a cloud with hands in the scene;
  `Renderer.__init__` never sets `_cloud_gl`.
- A4's rough edge: after a `graph.py` hot reload the held `Wiring` is an
  old-class instance (`ui.output_shows`'s `wiring != Wiring()` always
  True).
- Every deferred minor in the ledger (grep `deferred` and `Minor` in
  `progress.md`): C6 (a route on a palette row hidden by the inactive mode
  is invisible on the strip), C4 (`ghost.routed_rows` gives dance rows no
  tether), C5 (a closed grab holds if the skeleton drops; SETUP wording;
  fist level only in a tooltip), C3 (`compact_desk` loses a hand-edited
  twin row; plan-13 `same()` on templated presets; the "on" tier plumbing
  keys; PICK_S timeout with the popup open), B1 (`Host.devices` shadows
  the module name), B4 (`kinds()` imports `hyperspace.osc` on lookup),
  B2's registered rough edges. Triage each: must fix before merge, or
  leave registered (say which and why).
- The smoke runs (reports/smoke-report.md): stream B's first cold run logged
  one 2.2 s first-frame stall on a lazy `numpy.random` import at
  `geometry.py:808` (absent on re-run) — the gate wants an empty stall log:
  fix by importing at module load (or say why not). Stream A: the stroke
  switch's weight change at zoom 0.9 is ~11% and mostly sub-pixel; the hand
  check must use party-field (0.42) or hex-engine (0.4) — confirm A5 wrote
  it that way.
- Every agent commit carries a "Claude Opus 5.5" trailer; the owner has
  not asked for it to change — note only.
- Anything a document says that the code does not do: the docs WPs each
  listed theirs in their reports; spot-check ten claims across the three
  as-built files against the code.

## Output
The reviewer-common format
(`hyperspace-python/docs/plans/assets/24-26-27-run/briefs/reviewer-common.md`):
Spec compliance over the checklist (one line per item, ✅/❌/⚠️ with
what you checked), Strengths, Issues by Critical / Important / Minor with
file:line, a triage table for the known items (fix now / leave
registered), and the Assessment. Concrete and verifiable only.
