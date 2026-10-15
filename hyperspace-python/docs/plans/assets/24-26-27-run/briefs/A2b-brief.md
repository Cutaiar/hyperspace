# A2b — the stroke-space toggle (plan 26, an owner decision taken after A2)

Branch `plan-26-a2b-strokes`. PR title:
`Plan 26 A2b: strokes in world space or screen space — the owner's toggle, world space by default`.

## Where this fits
Plan 26 A2 (PR #183, merged on the integration branch) made `camera.zoom` the
shape's world scale and stopped the line width and the point radius scaling
with the zoom ("a stroke keeps its weight"). A2's own register draft records
the rough edge: at the zoomed-out factory looks (ember-orbit 0.5, hex-engine
0.4, party-field 0.42) the dots are 2–2.5× bigger and the edges heavier than
before. The owner looked at it on 2026-10-14 and decided:

> The owner does **not** necessarily want lines and points to be
> zoom-invariant. The owner likes the old effect — strokes that render at
> different sizes as you are close to or far from them — and wants **a
> toggle: strokes drawn in screen space (A2's, zoom-invariant) or in world
> space (scaling with zoom, the pre-A2 feel)**. Build it as a `view.*`
> toggle (performance part, modulatable or not — decide, register it) with a
> hand check, and re-record only the frames it moves with that one reason.

This WP is that toggle. It is small: it touches `draw_scene`'s stroke width
and point radius (`hyperspace/render.py`, see the "Plan 26 A2: no longer ×
the zoom" comments near the line width and the point radius), possibly the
line/point vertex shaders if your design needs them, `view.py` / `params.py`
for the param, the UI page the `view.*` toggles live on, the preset
document only if the param needs anything beyond being a `view` param, and
the goldens that move.

## The orchestrator's rulings (build these as written)
1. **Default: world space** (the pre-A2 feel). Reason: decision 24 says
   every new param defaults to today's picture, and the owner's "today" is
   `main`, where strokes scaled with the zoom; the owner said outright that
   they like that effect and the heavy zoomed-out looks were the rough edge.
   Cost: the goldens A2 recorded for strokes at zoom ≠ 1 move again, each
   with this one reason. (Screen space as the default would have kept
   A2's goldens; register it as the other option.)
2. **"World space" means the pre-A2 formula**: the stroke width and the
   point radius are multiplied by `camera.zoom` again, nothing else — no
   per-depth (perspective) thinning. So **at `camera.zoom = 1` every frame
   stays byte-identical to A2's goldens in both modes**, and only frames at
   zoom ≠ 1 with lines or points showing move. Register "true perspective
   width (a stroke a world size, projected)" as the other option, not built.
3. **Screen space is exactly A2's current behaviour** (byte-identical to
   today's integration frames when the toggle is flipped to screen space).
4. The param is yours to shape within these bounds: a `view.*` switch (two
   states; name it so the OUTPUT/VIEW pages read well — e.g.
   `view.stroke_space` with `world` / `screen`, or a boolean — your call,
   registered), in the preset (it is part of the look), following the
   nearest existing `view.*` switch for whether it is routable/modulatable
   (say what you followed and why). Default per ruling 1.
5. Only frames that move are re-recorded. Diff every golden before and
   after; list each moved frame in the PR body with the one reason
   ("strokes back in world space by default (owner, 2026-10-14)"). A frame
   at zoom 1 that moves means the build is wrong.
6. Points: keep A2's whole-pixel rounding of the point diameter (its
   register row "Point quads are a whole number of pixels across") — apply
   the zoom before the rounding, as the pre-A2 code did (check A2's PR
   #183 diff or the A2 decisions file if unsure what the pre-A2 code was:
   `git show 14834c2:hyperspace-python/hyperspace/render.py` is the
   render.py from just before A2).

## Read, in this order (paths relative to `hyperspace-python/`)
1. `docs/plans/assets/24-26-27-run/briefs/common.md` — the rules every WP
   works under (worktree setup, hard rules, the PR, the report). Where it
   names the orchestrator's workspace, use the paths at the end of this
   brief. Its commit-trailer block is from the previous session: use the
   attribution your own session reminder gives you.
2. `docs/plans/24-26-27-orchestrator-prompt.md` lines 81–255 (stream A,
   where the frame was) and 256–312 (A2's section) — for the A2 contract
   this toggle sits beside; then the shared sections 929–1115, 1116–1176,
   1177–1245.
3. `docs/plans/assets/24-26-27-run/decisions/A2.md` — A2's register-row
   drafts, in particular "camera.zoom is the shape's world scale; strokes
   and dots keep their pixel weight" and "Point quads are a whole number of
   pixels across". Your new row supersedes the first's "strokes and dots
   keep their pixel weight" sentence: say so in your draft.
4. `docs/ENGINEERING.md` §2 Rendering (the naming rule, the goldens and how
   to re-record them: `tools/golden_frames.py`), `docs/ARCHITECTURE.md` §2.
5. `hyperspace/render.py` (`draw_scene`, the line and point VAOs and
   vertex shaders), `hyperspace/view.py`, `hyperspace/params.py` (the
   `view.*` group), the UI page for `view.*`, `tests/test_render.py`,
   `tests/test_golden_frames.py`, `tools/golden_frames.py`.

## Tests
- A test that at zoom 1 the scene is byte-identical in both modes.
- A test that at zoom 0.5 with lines and points on, world space draws them
  thinner/smaller and screen space does not (pin the width/radius
  arithmetic, not only "something changed").
- The param's default, group and presence in a preset document.
- The goldens: `uv run pytest tests/test_golden_frames.py -q` must pass
  after you re-record only the moved frames (`tools/golden_frames.py
  --record --only …`); the contact sheet of the differences goes under
  `docs/plans/assets/26-render-graph/`.

## Decisions file (write it; A5 lifts it into the docs)
At the path below, in common.md's shape:
1. Register-row drafts: (a) the default (world space) with screen space as
   the other option, the cost to reverse, the rough edge (A2's goldens for
   strokes at zoom ≠ 1 moved again), and the hand check; (b) the param's
   form (id, routable or not) if you count it a separate decision.
2. A `DECISIONS.md` row draft for the **toggle itself** with **Who =
   `owner`** (the owner asked for the toggle on 2026-10-14); the default's
   row is yours (`row N`).
3. One hand-check draft numbered `V.A2b.1`: at the machine, a zoomed-out
   factory look (party-field, hex-engine) at the default: the dots and
   edges have the pre-A2 weight; zoom in and out with the pad/mouse: strokes
   grow and shrink with the shape; flip the toggle: they stay put. *Pass:* /
   *Fail:* with the likely cause.
4. As-built notes (At the machine / Code / Tests / what no person has
   verified / rough edges).
5. Anything a document says that the code now does not do (A2's register
   text in `docs/DECISION-REGISTER.md` is not yet written — A5 writes it —
   but A2's decisions file and ENGINEERING §2 may say "strokes keep their
   pixel weight": list each place).

## Paths
- Workspace: `/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/`
- Decisions file: `/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/decisions/A2b.md`
- Report file: `/Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/reports/A2b-report.md`
- If a write there is refused: `<your worktree>/.sdd/A2b-decisions.md` and
  `<your worktree>/.sdd/A2b-report.md` (do not commit them; give the paths).

## Gates before the PR (from `hyperspace-python/`)
```
uv run pytest -q                         # integration today: 2133 passed, 2 skipped
uv run ruff check .
uv run pytest tests/test_golden_frames.py -q   # 544 frames on "Apple M3 Max"
```
No smoke run is asked of this WP. Never touch `~/Hyperspace` or
`~/My Drive/Hyperspace`; `hyperspace/library/` stays byte-identical.
