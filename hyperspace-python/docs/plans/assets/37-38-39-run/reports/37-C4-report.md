# 37-C4 report: the faces' sheets and the migration map (dry run)

**Status:** DONE_WITH_CONCERNS. The P2 planning concerns are listed at the end.
**PR:** https://github.com/Cutaiar/hyperspace/pull/250 (into `plan-37-pictures`)
**Branch:** `plan-37-c4-faces-sheets`. Base: `cb78963`, confirmed by `git log --oneline -1`.
- `git reset --hard` was refused by the auto-mode classifier.
- Because the tree was clean, I reached the same state with `git merge --ff-only FETCH_HEAD`.

## Commits
- `2ad9a01` Plan 37 C4 (dry run): the face patterns' migration map, generated and checked
- `103a592` Plan 37 C4 (dry run): the 17 face patterns on sheets for the owner's D1

## Built
- **`hyperspace-python/tools/faces_sheets.py`**
  - **Sheets:** each of the 17 modes is drawn on a preset's shape through the golden rig. That covers the real `Presets`, a scratch HYPERSPACE_HOME and library, the shipped wiring and `draw_outputs`.
    - The hands are absent and `view.pattern` is set to the mode.
    - Mix is 1.0, and the inputs sit at the factory depth on plan 22's MEDIUM passage. The bands are set to match.
    - Each frame is read 3 frames in. The tile is the middle 480×300 of the frame at full resolution.
  - **Map:** `usage()` loads all 25 factory presets and all 24 fixtures through the real loader.
    - It reads the landed `view.pattern` and `view.faces`.
    - It walks the drawn wires back from `shape.faces` to find the pattern's run.
    - It also records any other port the pattern feeds and the rows that set `view.pattern`.
  - **Map data:** `render_map` writes the map from `DRAWS` (one line per mode) and `NEAREST` (three ranked neighbours, each with a reason). `nearest_kept(mode, kept)` gives the answer for any subset kept.
  - **Check:** `--check` regenerates the map and validates the data.
- **`hyperspace-python/docs/plans/assets/37-faces/`** (1.5 MB in all):
  - `sheet.png`: `party-faces`' tesseract, 506 KB
  - `heart-sheet.png`: `plasma-heart`'s Heart, lit at `view.bright` 2.5, 215 KB
  - one `<NAME>.png` per mode
  - `migration-map.md`
- **`hyperspace-python/tests/test_faces_map.py`**
  - fast: the map is current (`check() == []`, about 1.5 s); data shape; `nearest_kept` over subsets
  - slow: spot checks of the usage reading
- Nothing in `hyperspace/` changed, and no preset or fixture was edited.

## Key findings (from the generated map)
- **On screen in factory presets:**

  | mode | factory presets |
  |---|---|
  | RINGS | dial, inverse-halo, party-acid |
  | MOIRE | strobe-cage |
  | CAUSTIC | big-blue-wave |
  | HEX | hex-engine, party-faces |
  | SPIRAL | spiral-silk |
  | CELLS | party-tumble |
  | PLASMA | party-mandala, party-trip, party-wake, plasma-heart |
  | EMBER | ember-orbit, party-field, party-noita |

- **Faces off:** FLAT in 7 presets, PLASMA in party-tracer, WEAVE in woven-lattice.
- **Unused:** no factory preset or fixture shows PLAID, BLOOM, METER, PULSE, MARBLE, TRUCHET or KALEIDO, so dropping them moves no golden.
- **Fixtures:** 8 carry HEX while their faces read something else (unwired).
- **Desk knob:** 17 of the 25 factory presets put `view.pattern` on a desk knob (`abs`), so after P2 the knob's throw is the kept list.

## Tests (from `hyperspace-python/`)
- **`uv run pytest -q`:** `1 failed, 3960 passed, 2 skipped in 204.76s`
  - That is the base's 3958 plus my 3 fast tests, less the 1 failure.
  - The failure is `test_media_render.py::test_render_thread_never_waits`, a load flake. It passes serially: `1 passed in 5.70s`.
- **`uv run ruff check .`:** my two files are clean.
  - The tree reports `Found 25 errors`, all in files I did not touch (media/*, the 39-vision benches, `tools/ingest.py`, four tests).
  - This is ruff 0.16.4 in the fresh worktree venv and is not mine.
- **`uv run pytest -q --all tests/test_golden_frames.py`:** `128 passed in 31.77s`. No golden moved, 757 unchanged.
- **`uv run pytest -q --all`:** `4 failed, 4170 passed, 2 skipped in 223.74s`
  - The four are load-flaky media and migrate-library tests, among them `test_media_channels…slow_closes…`, `test_media_core::test_bad_file_is_an_error` and `test_migrate_library::test_the_real_picture_check_passes_an_old_preset`.
  - `uv run pytest -q --all --lf -n0` gives `4 passed in 43.85s`.
  - Total: 4174, which is the base's 4172 plus my 4 tests.

## Self-review
- **Eyeballed:** both sheets.
  - The first render had an unrenderable em dash in the title, small shapes and a very dim heart.
  - Fixed: a colon instead of the dash, a full-resolution centre crop, and the Heart at bright 2.5 (documented).
- **"On screen" check:** it does not confirm that the shape itself reaches an output. Every factory preset does, so this is noted rather than coded.
- **Stills can't show motion** (METER, PULSE, SPEED). Judge those on the FACES page with music.

## Concerns for P2 (details and exact steps in decisions/37-C4.md §4)
1. **Presets store `view.pattern` as an index.** Removing modes shifts the indices.
   - Option (a): renumber and remap the values. This needs an owner or schema call: an older build would read the wrong patterns.
   - Option (b): keep the indices and mark retired modes as tombstones, mapped at load.
   - The plan doesn't address this. It needs a decision before the build.
2. **`preset.py` needs an edit plan 37 isn't given.** It writes `view_pattern=` for four presets (lines about 1609, 1703, 1735 and 1767), and the factory sources under `tests/fixtures/factory-sources/presets/` need the same change. Plan 37's ownership table gives `preset.py` "nothing", so the controller must allow the edit.
3. **`NEAREST` and `DRAWS` reflect only my judgement.** No person has checked them yet.

Decisions file: /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/37-C4.md (rows 4xx-a/b/c, hand check AH.6, as-built notes, P2 steps).
