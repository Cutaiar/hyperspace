# 39-T2 report — the mask wire and `matte`

**Status:** DONE_WITH_CONCERNS
**PR:** https://github.com/Cutaiar/hyperspace/pull/256 (`plan-39-t2-matte` → `plan-39-vision`)
**Base:** cb78963. Confirmed after fetch and fast-forward; the harness refused `git reset --hard`, so I used `git merge --ff-only FETCH_HEAD` from a clean tree.
**Decisions file:** /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/39-T2.md

## Commits
- dc6b2f1 Plan 39 T2: masks.py — the matte, blur, promote and cut passes
- 092bb60 Plan 39 T2: the mask wire and matte — promotion, MatteNode, declare_mattes
- 6574f16 Plan 39 T2: the mask-as-picture fixture and its goldens
- cb2d68b Plan 39 T2: a matte has no own_size — its mask size is size_for's

## What I built
- **The promotion (W1).** `_wired_error` now accepts MASK → IMAGE. Picture → mask is refused with `PICTURE_INTO_MASK`, whose words name the matte. `_Build._taken` wraps a mask that a picture port reads in one `graph.MaskPicture` per mask node. That node paints `masks.PROMOTE_FS` by cover at the consumer's size: white where the mask passes, opaque black elsewhere. It has no GRAPH node and is untimed. The scene-cover pin is unchanged.
- **`matte[.n]` (W2).** `MatteAt` and its reader, `NODE_KINDS`, `DECLARED`, `RESERVED`, `_MATTE` and `_wired_kind`, `WIRED_MAKES` and `WIRED_TAKES`, `_WireCtx.mattes`, `GraphSpec.mattes` and the `_Build._make` branch. `MatteNode` makes an R8 mask at its input's size, keyed `(<name>#mask, size)`; when the feather is above 0 it runs two separable blur passes through `(<name>#mask/blur, size)`. It has no `own_size` override, because no consumer fits a mask by `OWN_FIT`.
- **`hyperspace/masks.py`.** A new leaf module. It holds `MATTE_FS`, `BLUR_FS`, `PROMOTE_FS` and `CUT_FS`. `CUT_FS` and `MaskPasses.cut` are written and tested for T3. `MaskPasses` compiles the programs once, gets its targets from the renderer's `_frame_target`, and samples inside edge texels so nothing wraps.
- **`render.py`.** Only `Renderer.mask_passes()`, plus `_frame_target(..., components=4)`.
- **`view.py`.** `MATTE_FROM`, `MATTE_FEATHER`, `MatteState`, and `ViewState.mattes`.
- **`params.py`.** `MATTE_GROUP`, `matte_ids`, `is_matte_id` and `declare_mattes`. `matte` is added to `PERFORMANCE_GROUPS` after `resize`, and `build_registry` binds `view.mattes`.
- **`preset.py`.** It declares the mattes on land, sends `matte.*` values to `later`, leaves them out of a new preset's values, and adds `MATTE_GROUP` to `NO_MODULE`.
- **`graphview.py`.** Table entries only: `OWNERS`, `LABELS`, `HOVERS`, `FRAME_CLASS`, `PICKER_GROUP` (`masks`), and `matte` in `_node_name`'s declared kinds.
- **`ui_presets.py`.** `matte` is excluded from `OVERVIEW_GROUPS`. This file is outside the ownership table; the change is one word.
- **Fixture.** `tests/fixtures/presets/mask-as-picture.json` (`/7`) has 8 new goldens with one PNG. `tools/golden_frames.py` lists it in `MEDIA_FIXTURES` and `WIRED_FIXTURES`.

## Tests
`tests/test_graph_masks.py` has 36 tests. They cover:
- that `masks.py` is a leaf, and that the cover scale equals the media fit;
- the node's identity;
- the entry's round trip, and that a matte must be declared;
- the type rules: ten picture ports accept a mask; picture → `lookback.cover` gets the matte words; a mask is still neither geometry nor depth; the scene cover is as it was;
- that a matte is built only when it is reached and fed;
- one `MaskPicture` per mask, and that a mask port takes the raw mask;
- the canvas tables, `declare_mattes`, and the registry → `ViewState`;
- the `/7` save and load of the fixture through two rigs;
- in GL: luma, alpha and chroma; that the key moves the mask; soft and invert; that the feather widens the edge in one channel; the promotion at the consumer's size; the promote pass by cover; orientation (an asymmetric still lands top-left); a matte reading nothing makes nothing; a matte into `lookback.cover` draws; and the cut pass.

Gate outputs:
- `uv run pytest -q` → `3996 passed, 2 skipped in 23.12s` (base 3958 + 38)
- `uv run ruff check .` → `Found 25 errors.`. These were all there at base; none is in a file I touched, and touched files are clean.
- `uv run pytest -q --all tests/test_golden_frames.py` → `130 passed in 14.22s`. There are 765 goldens: 757 + 8, and none moved.
- `uv run pytest -q --all` → `1 failed, 4209 passed, 2 skipped in 75.86s`. The failure is `test_media_channels::test_rapid_switching_with_slow_closes_stays_fast_and_balances`, the known load-flaky test; `uv run pytest -q -n0 --all tests/test_media_channels.py` gives `19 passed`.

## Tests changed, one reason each
- `test_plan36_edges.py`: the refusal words gain "— put a matte between".
- `test_hotreload.py`: `masks` is added to `cold`, because `hotreload.py` is plan 38's.
- `test_golden_frames.py`: the count goes up by 8, `GOLDENS_SINCE` gains `mask-as-picture`, and `mask-as-picture` joins the no-hands fixtures.
- `test_graph_free.py`: the source schema ladder now includes `/7`.

## Concerns, for the orchestrator
1. **Hot reload.** `masks` must go onto `hotreload.MODULES` (before `render`) and come off `test_hotreload`'s `cold` set at integration. That is plan 38's file, and the brief forbade me to touch it.
2. **No frame-signature case.** The brief asked for a case for `mask-as-picture`. The tool leaves out every wired fixture by design (as `channel-out-only` and `resize-crop`), so `frame-signatures.json` is unchanged. Instead, `test_graph_masks` pins the shape of the built graph.
3. **Cable colour.** A promoted mask cable is drawn red: `graphview` colours a cable by the destination port's type. W6 wants "purple into a red port". Changing that is a `graphview` code change outside the table entries, so it falls to T5.
4. **No way to add a matte from GRAPH yet.** There is no picker item or `render_add` branch for `matte`, so until T5 a matte comes only from a preset file. `test_the_picker_groups_by_primitive` pins the current list.
5. **Out-of-table edit.** `ui_presets.py` got a one-word change outside the ownership table (row 4xj).
6. **Expected conflict with T0.** T0, which also adds a fixture, will conflict with these lines in `test_golden_frames.py` (the count, `GOLDENS_SINCE`) and in `tools/golden_frames.py`'s fixture tuples. Both sides add, so the merge is mechanical.
7. **Commit attribution.** Commit and PR attribution use the session's lines (Claude Opus 5.5). common.md said Fable 5.1.

## Self-review
- The promotion sits only at the build sites where a picture port reads a node: `_from`, `_aux` and the window ports. Geometry is untouched (`scene.geometry` reads `self.node` directly), and a mask is refused there anyway.
- `_taken` checks the destination port's type in `WIRED_TAKES`, so `lookback.cover` (MASK) gets the raw mask.
- `MaskPicture.image` uses an RGBA8 frame target under `frame.key`, and `_prune_sized` frees it like any other.
- No node method is named `apply`, `modulate`, `snapshot` or `set_value`. `graph.py` does not import `masks` (a test checks this).
- The full suite and every golden pass. `graph.signature` is unchanged for every recorded case.

---

## Fix report (review round 1)

**Commits**
- `52121a0` Plan 39 T2 review: a mask port gets the mask at the frame's size; cut fits by cover; reload drops the passes
- `19bf4d4` Merge plan-39-vision (T0 edges-scene, T1 blend) into plan-39-t2-matte

Both commits carry common.md's attribution lines.

**Important 1 (a mask's size).**
- `MatteNode.image` is what a mask port binds. When the mask's size differs from `frame.size`, it now returns the mask refitted by cover to `frame.size` via `MaskPasses.fit`: `PROMOTE_FS` into an R8 frame target `<name>#fit`, once a frame.
- `MatteNode.native` returns the mask at its own size. `MaskPicture` promotes from `native`, so the mask is fitted once and never refitted twice.
- `CUT_FS` gains `u_scale = cover_scale(mask.size, picture size)`, and `MaskPasses.cut` passes it in. T3's cut therefore agrees with the promoted picture.

New tests:
- `test_an_own_sized_mask_lands_on_the_cover_where_its_picture_shows_it`: resize (64×36) → matte → `lookback.cover` in a 160×90 frame. The cover the look-back binds is 160×90 and one channel, it equals output 1's promoted picture to within 1/255, and the native mask is still 64×36.
- `test_the_cut_pass_fits_its_mask_by_cover`.

No plan-36 node was changed.

**Important 2 (hot reload).** `Renderer.on_reload` now pops and releases `_mask_passes`. New test: `test_a_reload_drops_the_mask_passes`. The decisions file (row 4xg) records the integration steps: insert `"masks"` before `"render"` in `hotreload.py:59`, and drop it from `cold` in `test_hotreload.py:239`.

**Minor.**
- `MatteNode.own_size` now passes its input's own size through. `test_nothing_of_plan_33_has_an_own_size` stays green (`--all -n0` on `test_graph_delay` + `test_render`: 196 passed).
- AJ.6 now says that a promoted mask wired into `lookback.occluder` or `composite.over` is opaque everywhere, so it is not a cut.

**Merge of `plan-39-vision`.** There were conflicts in three files, all bookkeeping:
- `tests/test_golden_frames.py`: the count is now +8 (T0) +8 (T2), and `GOLDENS_SINCE` lists both `edges-scene` and `mask-as-picture`.
- `tools/golden_frames.py`: `WIRED_FIXTURES` lists both fixtures.
- `tests/test_graph_free.py`: the schema ladder is `/2`–`/7`.

Nothing was re-recorded.

**Gates**
- `uv run pytest -q tests/test_golden_frames.py --all -n0` → `132 passed in 25.13s`; manifest holds 773 goldens.
- `uv run pytest -q` → `4019 passed, 2 skipped in 31.33s`
- `uv run ruff check .` → `Found 25 errors.` These are the base's own, in untouched files; every touched file is clean.
- `tests/test_graph_masks.py` → 40 passed.
