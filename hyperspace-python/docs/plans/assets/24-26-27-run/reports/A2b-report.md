# A2b report — the stroke-space toggle

**Status:** DONE. **Base:** `a9386f1` (plan-24-26-27-integration). **Branch:** `plan-26-a2b-strokes`. **PR:** https://github.com/Cutaiar/hyperspace/pull/192 (into plan-24-26-27-integration, not merged).

Commits:
- `094cc46` Plan 26 A2b: view.screen_strokes — strokes in world space by default, screen space on the switch
- `eb0e255` Plan 26 A2b: re-record the 212 frames with strokes at zoom != 1 (world space by default)

## What was built
- `view.screen_strokes` (toggle, group `view`, performance, modulatable/routable like `view.lines` / `view.cut_through`), default off = world space.
- `render.draw_scene`: `sz = 1.0 if screen_strokes else zoom` (the clamped zoom the model matrix uses); `width … * sz` before the 1 px floor and the alpha fold; `r … * dpr * sz` before the whole-pixel rounding — the pre-A2 formula exactly (checked against `git show 14834c2:…/render.py`: `width … * wscale * zoom`, `r … * dpr * zoom`). Module docstring updated.
- `view.py` field; `ui.py` checkbox under the points/lines opacity sliders on the view page.

## Files changed
- hyperspace/view.py, hyperspace/params.py, hyperspace/render.py, hyperspace/ui.py
- tests/test_stroke_space.py (new, 7 tests), tests/test_camera.py (one test now draws with `screen_strokes=True`)
- tests/golden/frames/frames.json + 79 PNGs removed / 80 added
- docs/plans/assets/26-render-graph/a2b-moved.png (compact contact sheet, 0.7 MB; the tool's full sheet was 14 MB and is not committed)

## Testing
```
uv run pytest -q                              → 2140 passed, 2 skipped in 169.36s (base 2133 + 7)
uv run ruff check .                           → All checks passed!
uv run pytest tests/test_golden_frames.py -q  → 7 passed in 18.18s
git diff --stat -- hyperspace/library/        → empty
```
Goldens: `tools/golden_frames.py` (diff) reported "212 of 544 frames moved"; re-recorded with `--record --only` the 16 presets that moved; a manifest diff old vs new shows exactly 212 changed hashes, same 544 keys, header unchanged. Every moved preset has `camera.zoom ≠ 1` with lines or points (hands-orbit only with the hands present, its zoom route); every zoom-1 preset (legacy6, lfo-breathe, hands-fx/pinch/play, party-noita) and plasma-heart (no strokes) stayed byte-identical. The contact sheet was inspected: zoomed-out fields (ember-orbit, hex-engine, party-field) have smaller dots / finer edges, zoomed-in (party-tumble) slightly heavier — the pre-A2 look.

## Self-review
- The zoom factor in world space is the same clamped `zoom` the pre-A2 code used (`max(s.zoom, 1e-3)`).
- The new param needs no preset migration: a file without the key loads the group default (off), tested.
- No render-stack param write; no banned method names; no library file touched; no fixture added.

## Concerns
- The A2 docs (A2.md row "strokes and dots keep their pixel weight", hand check V.7) now describe the switch-on behaviour only; listed in the decisions file §5 for A5.
- Nothing visible was verified by a person (no smoke run asked).

Decisions file: /Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/decisions/A2b.md

## Fix report — review round 1 (FIX BASE eb0e255 → 7395bca)

**A (the hands).** One sentence added to the register-row draft (§1 row 1, Built), the as-built notes ("At the machine") and the hand check (Pass), plus the code comment at the `sz` site in `draw_scene`. It says the switch moves the shape's strokes only. A3's tubes are world-sized (`ghost.py` `WIRE_R`, `BONE_R`) and by design never follow `camera.zoom`. A4's hand lines are 1 px edges drawn by `ghost.Geometry.draw(lines=True)`, not through `draw_scene`'s width. So the hands look the same in both modes.

**B (learn).** `learn.cannot_show("view.screen_strokes")` now returns "points and lines off" when both `view.points` and `view.lines` are off. `_switched_on` puts the switch in click-to-map's "on" tier while either one is on. The coverage table comment is updated. Tests: three asserts added to `tests/test_desk_coverage.py::test_cannot_show_is_the_rule_by_group`. The zoom-1 case is written as a rough edge in register row 1, not as a rule, because a routed zoom makes the switch live. Register row 2's wrong sentence ("no cannot-show rule") is replaced.

**C.** The PR body now says "15 presets … plus hands-orbit with the hands present". The hand check says that Screen strokes rests unticked.

**D** waits for round 2, after A4 is merged.

Tests:
```
uv run pytest tests/test_stroke_space.py tests/test_desk_coverage.py tests/test_learn.py -q  → 46 passed in 3.52s
uv run ruff check .                                                                      → All checks passed!
uv run pytest -q                                                                          → 2140 passed, 2 skipped in 150.12s
```
No golden moved in this round. The fix touches only learn.py, a comment in render.py, and a test. Commit `7395bca`, pushed. The PR body is updated.

## Fix report — review round 2, item D (FIX BASE 7395bca → 51f4953 merge, 0fafe23 re-record)

**Merge.** I merged `origin/plan-24-26-27-integration` (f497059: A4 #191, A4b #190) into `plan-26-a2b-strokes` as merge commit `51f4953`. The only conflicted file was `tests/golden/frames/frames.json`. I resolved it with a script: the integration side's 556 entries, with this branch's hash taken for every entry this branch changed from the merge base (212). No entry had been changed on both sides. Every referenced PNG exists and there are no orphan PNGs. `render.py`, `ui.py` and `view.py` merged automatically. Both `sz` lines in `draw_scene` are kept, and so are A4's and A4b's changes.

**Diff over all 556 frames** (`HYPERSPACE_HOME=<scratch> uv run python tools/golden_frames.py`): "6 of 556 frames moved".
- `hands-lines|present|`: `scene+hands`, `scene+hands+through`, `scene`, `scene+through`. These are the 4 the coordinator expected (zoom 0.9, lines and points on).
- `party-faces|present|`: `cloud/scene`, `cloud/scene+hands`. These are 2 of A4b's 4 cloud frames, at zoom 1.1 with lines on. legacy6's 2 cloud frames are at zoom 1 and did not move.

**Why the cloud frames moved: the shape's strokes, not the cloud's points.**
1. With the default temporarily flipped to screen space, every one of these 6 frames matched its integration golden. So the switch is the only cause. The flip was reverted, and `git checkout` confirmed the file is back.
2. Full-resolution experiment (`.sdd/cloudexp.py`, which patches `Rig.frame` to set view values). It rendered party-faces' cloud/scene with the switch both ways:
   - with lines on: 2837 px moved, and every one is a pixel the shape's strokes touch (0 px outside them);
   - with lines off: 0 px moved.
3. The cloud draws through `_CloudGL` at `cloud.size` and never reads the zoom or the switch.

**Re-record.** `tools/golden_frames.py --record --only party-faces,hands-lines`. The manifest diff against the merge commit shows exactly those 6 hashes changed: 3 PNGs replaced, the header unchanged, 556 keys. The contact sheet `a2b-moved.png` is regenerated against the integration branch's goldens: 18 rows, now with the party-faces cloud/scene and hands-lines scene rows. The PR body lists the 6 new frames with the same reason, plus the cloud explanation. The decisions file counts are now 218 of 556.

**Gates** (from hyperspace-python):
```
uv run pytest -q                              → 2190 passed, 2 skipped in 154.12s
uv run ruff check .                           → All checks passed!
uv run pytest tests/test_golden_frames.py -q  → 7 passed in 17.38s (556 frames)
git diff --stat -- hyperspace/library/        → empty
```
Pushed (0fafe23).
