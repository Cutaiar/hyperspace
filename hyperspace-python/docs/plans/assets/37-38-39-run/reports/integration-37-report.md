# integration-37 report

**Status: DONE.** Branch `integ-37` at **96773ca**, pushed to origin with no PR. It was cut from `origin/plan-37-38-39-integration` @ 2b185ea.

## Commits
- `1feddab` Merge plan-39-vision into plan-37-38-39-integration: plan 39 T5–T6 (PRs #267, #268). Parents: 2b185ea and 2a57af6.
- `96773ca` Merge plan-37-pictures into plan-37-38-39-integration: plan 37 C1–C5 (PRs #250, #253, #255, #258, #261). Parents: 1feddab and d2ffa7c.

## What was done
1. **Plan 39 merge.** The code merged clean (`graphview.py` included). Docs conflicts with plan 38's B4 docs kept both sides, and ARCHITECTURE's Host row was joined. Fast tier: 4141 passed, 2 skipped.
2. **Plan 37 merge.**
   - `ui_graph.py`: the head reads hold chips, then plan 36's chips, then `_tint_chip` last. The HELD line, the forced backdrop and the PROJECTOR inset are plan 38's. C1's `_canvas` wants the thumbnails and `_node` draws them. Nothing of either side was lost: the only lines dropped are plan 37's superseded backdrop guard and the reads plan 38 had already routed.
   - `graphview.returns`: plan 39's MASK type plus plan 37's `kept()`.
   - `render.py`: imports from both sides.
3. **Thumbnails during a hold.**
   - The new `ui_graph.picture_sources(panel)` reads through `hold.canvas_renderer`. It supplies `st["thumbs"]`, `st["preview"]` and `st["gpu_ms"]`, and `thumbnail_line` uses it too.
   - The preview renderer has its own `PreviewTextures`, made in `Renderer.__init__`. `MIRRORED` carries no `thumbs`, and a test asserts it. The hue reads follow `st["thumbs"]`.
   - Output 1's node shows `panel.monitor`, the program's picture, while held. A comment and row 499 say so.
   - Tests, in the new `tests/test_hold_thumbnails.py` (5 tests):
     - The headless sources follow the canvas renderer.
     - `mirror` never shares `thumbs`.
     - A headless page draw while held puts the wishes on the preview's `PreviewTextures`, and none on the main one's.
     - On GL, held with the page drawn, the preview copies and the main renderer copies 0. After Take and after Drop, the main renderer copies again.
     - On GL, a hold with the page closed makes no thumbnail and no preview renderer.
   - Mutation check: with `picture_sources` reading `panel.renderer`, 3 of the 5 fail.
4. **Seams fixed.** Rows 498–500 are in the register; decisions are in `decisions/integration-37.md`.
   - `graphview.THUMBS["cut"]` was added. The table test now skips the segment's pins and asserts that matte and segment are text.
   - The faces migration map was regenerated for plan 39's four fixtures (`tools/faces_sheets.py --map`, scratch home).
5. **Docs.**
   - Register rows 417–500 are in numeric order: one header sentence, the answer sheet sorted, and one body section with each plan's note.
   - The hedge was dropped from rows 459, 495 and 496. Row 466's edge is updated.
   - Hand checks run AH, AI, AJ with one header line. Check 378 gets step 5.
   - TESTING-GUIDE: plan 38's entries are now L179–L181, and the order items are 21, 22 (new), 23.
   - README: three plan lines.
   - CHECKPOINT: one "Where the code stands" paragraph for the three plans and one "What is left".
   - DECISIONS: three tables in order 37, 38, 39, plus a row.
   - ARCHITECTURE: the hold paragraph, a "while held" bullet under Nodes as pictures, and the `render.py` row merged. One clause was added to the `.html`.

## Gates (from `hyperspace-python/`)
- `uv sync`: ok (torchvision etc. installed in the worktree venv).
- `uv run pytest -q` → `4227 passed, 2 skipped in 28.75s`.
- `uv run pytest -q --all` → `1 failed, 4449 passed, 2 skipped in 58.74s`. The failure is the known load-flaky `tests/test_media_core.py::test_bad_file_is_an_error` (status still "fetching" under load). Serially, `--all -n0 tests/test_media_core.py` → `17 passed`.
- `uv run pytest -q --all -n0 tests/test_golden_frames.py` → `136 passed in 30.18s`. `frames.json` lists 789 goldens. `git diff 2b185ea -- tests/golden` is empty, so no golden moved in this integration.
- `git diff cb78963 -- tests/fixtures/frame-signatures.json`: empty.
- `uv run ruff check` on the touched files: all checks passed. The whole tree has 25 errors, all in untouched files and all present at the base (`hyperspace/media/*`, `tools/ingest.py`, plan 39's bench scripts, four tests).

## Files changed by the integrator (beyond the merges)
- `hyperspace/ui_graph.py`: `picture_sources`; `_canvas` and `thumbnail_line` read through it.
- `hyperspace/graphview.py`: `THUMBS["cut"]`; the `returns` resolution.
- `hyperspace/render.py`: imports.
- `tests/test_hold_thumbnails.py`: new.
- `tests/test_thumbnails.py`: the table test.
- `docs/plans/assets/37-faces/migration-map.md`: regenerated.
- Docs: `DECISION-REGISTER.md`, `DECISIONS.md`, `ARCHITECTURE.md/.html`, `CHECKPOINT.md`, `TESTING-GUIDE.md`, `plans/11-hand-checks.md`, `plans/README.md`.

## Concerns
- Only output 1 has a program picture on the page. While held, outputs 2–4's nodes show the preview's handoff frames (row 499's rough edge).
- The first frame after HOLD still reads the main renderer, until the preview has been drawn once (row 466's edge, carried into row 498).
- The segment node shows no thumbnail (row 500). The owner may want it to show its foreground.
- Nothing on screen has been seen by a person.
