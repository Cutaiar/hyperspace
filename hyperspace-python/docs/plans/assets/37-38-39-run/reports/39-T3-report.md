# 39-T3 report: `cut`, a picture cut by a mask

**Status:** DONE_WITH_CONCERNS (minor; see Concerns)
**PR:** https://github.com/Cutaiar/hyperspace/pull/260 (`plan-39-t3-cut` → `plan-39-vision`)
**Base:** 06db42b, confirmed. The harness refused the compound `git reset --hard`, so I used `git merge --ff-only FETCH_HEAD` from a clean tree.
**Decisions file:** /Users/dallman/.claude/jobs/9679624d/tmp/run/decisions/39-T3.md

## Commits
- def80c1 Plan 39 T3: cut — a picture cut by a mask (CutNode, the flip flag, declare_cuts)
- 5fd0ff1 Plan 39 T3: the cut tests and the cut-out fixture with its goldens

## What I built
- **`graph.py`**
  - `CutAt` and its reader, plus every table line T2 added for `matte`: `NODE_KINDS`, `RESERVED`, `DECLARED`, `_CUT`/`_wired_kind`, `WIRED_MAKES` (IMAGE), `WIRED_TAKES` (`image` IMAGE, `mask` MASK), the from/to words, `_WireCtx.cuts`, `GraphSpec.cuts`, `read_graph`'s context, `Frame.cuts`, and the `_Build._make` branch. A cut fed nothing on `image` is dormant.
  - `CutNode`:
    - Its own size is its picture's; an own-sized picture is cut at that size and refitted by cover.
    - When no mask is wired, or the mask makes nothing, the picture passes through untouched.
    - Otherwise it makes the cut once per frame into its own target `<name>#cut`.
    - It reports its state in `said`.
  - `mask_of(node, frame) -> (tex, flipped)`: the flip flag's reader. A mask maker may define `rows_top_first(frame)`.
- **`masks.py`.** `CUT_FS` gains `u_flip`, and `MaskPasses.cut` gains `flip=`.
- **`view.py`.** `CutState` (`invert` False, `amount` 1) and `ViewState.cuts`.
- **`params.py`.** `CUT_GROUP`, `cut_ids`, `is_cut_id` and `declare_cuts`. `cut` is added to `PERFORMANCE_GROUPS` after `matte`, and `build_registry` binds `ViewState.cuts`.
- **`preset.py`.** Declares the cuts on land, defers `cut.*` values until the graph lands, leaves them out of a new preset's values, and adds the group to `NO_MODULE`.
- **`graphview.py`.** Table entries only.
- **`ui_presets.py`.** `"cut"` is excluded from `OVERVIEW_GROUPS`. This is one word in a file outside the ownership table, the same edit T2 made for `matte`.
- **Fixture.** `tests/fixtures/presets/cut-out.json` (`/7`, wired): a still → `matte` → `cut.mask`; the scene through `kaleido` (zoom 0.5) → `cut.image`; the cut over the scene into All outputs. It has 8 goldens with one new PNG.
- `tools/golden_frames.py` lists it in `MEDIA_FIXTURES` and `WIRED_FIXTURES`. `test_golden_frames.py` raises the count by 8, adds it to `GOLDENS_SINCE` and adds it to `no_hands`.

## How I tested it
`tests/test_graph_cut.py`, 23 tests, all passing. They cover:
- Tables and identity.
- The entry's round trip, and that a cut must be declared.
- The type rule: a picture into `cut.mask` gets the matte words; a cut works as a picture everywhere a picture is taken.
- The build: the mask port gets the mask itself; dormant without a picture; mask None when unwired.
- `mask_of`'s flag.
- The canvas tables, `declare_cuts`, and registry → `ViewState`.
- The fixture's `/7` round trip through two rigs, and that a new preset holds no `cut.*`.
- In GL:
  - the hole is transparent in the cut's own target;
  - the under shows through on a composite;
  - amount 0.5 halves colour and alpha;
  - invert works;
  - amount 0 leaves the picture whole;
  - no mask is byte-identical to the picture;
  - a matte reading nothing is byte-identical too;
  - orientation, with an asymmetric still;
  - the flip, with a rows-top-first CPU mask;
  - an own-sized cut is made at 64×36 and laid in by cover.

Gate outputs:
- `uv run pytest -q` → `4044 passed, 2 skipped in 55.09s`
- `uv run ruff check .` → `Found 25 errors.` These are all the base's own. On the touched files, `All checks passed!`
- `uv run pytest -q --all -n0 tests/test_golden_frames.py` → `134 passed in 46.30s`. The manifest now holds 781 goldens (773 + 8); none moved, and the 741 digest is unchanged.
- `uv run pytest -q --all` → `1 failed, 4261 passed, 2 skipped in 90.89s`. The failure is `test_media_publish::test_ndi_out_loopback`, which is load-flaky and untouched by this task. Run alone, `uv run pytest -q --all -n0 tests/test_media_publish.py` gives `11 passed`.

## Goldens
New: `cut-out` × 8 (`png/ec720a1619ff1aa3.png` for the four scene states; the four none/hands states reuse the existing black `b6783b14bd504ef1.png`). I checked the picture by eye: the kaleidoscope sits inside the still's disc, right of centre, and the scene is everywhere else. The fixture is not ignored, so it was added normally with no `-f`. I recorded with `HYPERSPACE_HOME` set to a scratch folder with an empty `config.toml`.

## Files changed
- `hyperspace/graph.py`
- `hyperspace/masks.py`
- `hyperspace/view.py`
- `hyperspace/params.py`
- `hyperspace/preset.py`
- `hyperspace/graphview.py`
- `hyperspace/ui_presets.py`
- `tests/test_graph_cut.py` (new)
- `tests/fixtures/presets/cut-out.json` (new)
- `tests/golden/frames/frames.json`
- `tests/golden/frames/png/ec720a1619ff1aa3.png` (new)
- `tests/test_golden_frames.py`
- `tools/golden_frames.py`

## Self-review
- `graph.py` still imports neither `masks` nor anything outside the render stack; it reaches the cut pass through `frame.r.mask_passes()`.
- No node method is named `apply`, `modulate`, `snapshot` or `set_value`.
- The cut is the only node that writes a mask into a picture's alpha, which is its job.
- No plan-36 node changed:
  - `_taken` still promotes only into IMAGE ports, so `cut.mask` gets the raw mask.
  - `laid_over` is untouched (row 4xo).
  - Every factory `graph.signature` test is green.
- The pass is timed under the cut's name alone. The picture and the mask are made before the timer.
- The cut's pass writes only into its own target. It never cuts into the consumer's framebuffer (row 4xm).

## Concerns
1. **The flip flag is honoured by `CUT_FS` only.** `PROMOTE_FS` and `MaskPasses.fit` (a mask read as a picture, and a mask port's refit) do not read `mask_of` yet. Before a rows-top-first `segment.mask` is wired into an output or into `lookback.cover`, T4 must add `u_flip` there and have `MaskPicture` and the fit read `mask_of`. Row 4xl explains.
2. **No frame-signature case for `cut-out`.** Wired fixtures are excluded by the tool's rule, as with T2 (row 4xq).
3. **A cut does not pass "laid over" up to the scene.** In `cut-out`, the kaleidoscope's black covers the scene inside the disc. This is a deliberate choice to change no plan-36 rule (row 4xo).
4. **Out-of-table edits.** `ui_presets.py` (one word) and `view.py` (`CutState`, beside T2's `MatteState`).
5. **Commit attribution.** Commits use the session's `Claude Opus 5.5` lines rather than common.md's `Fable 5.1`. The session's attribution reminder names this model, and T2 did the same.
6. **Expected merge conflicts.** Other fixture-adding tasks will conflict with these lines in `test_golden_frames.py` (the count, `GOLDENS_SINCE`, `no_hands`) and in `tools/golden_frames.py`'s tuples. Both sides only add, so the merge is mechanical.

---

## Fix report (review round 1)

**Commit:** 302b5cd Plan 39 T3 review: a cut is transparent to laid-over-ness, as an effect is (pushed to `plan-39-t3-cut`, PR #260)

**Important (laid-over-ness).** This supersedes concern 3, the self-review line "`laid_over` is untouched", and the golden named in the "Goldens" section above.
- `_Build.laid_over` now recurses through `kind in ("effect", "cut") and w.port == "image"`. The `mask` port is not a picture path, and the docstring says "through effects or cuts". `CutNode` itself is unchanged.
- New tests in `tests/test_graph_cut.py`:
  - `test_a_cut_is_transparent_to_laid_over_ness`: for `scene → kaleido → cut.image, cut → composite.over`, `scene.ground == 0.0` and `kaleido.laid_over`; for `scene → cut → output.all.image`, `ground is None`.
  - `test_the_under_shows_where_a_laid_over_scene_draws_nothing` (GL): the scene cut and laid over channel c shows the under inside the passing area, and in the hole.
- I re-recorded `cut-out` with `--only cut-out`. It is a fixture recorded in this same task, and the commit gives the reason.
  - The four scene states moved from `png/ec720a1619ff1aa3.png` to `png/a0abb485a6c1ca6a.png`. By eye, inside the disc the cube's edge now shows through the kaleidoscope's empty space.
  - `git diff --stat tests/golden`: `frames.json | 16 ++++++++--------` (only cut-out's 4 sha/png pairs), plus the old PNG deleted. The other 773 are byte-identical.

**Decisions file.**
- Row 4xo is rewritten to the new answer.
- AJ.5's Pass line now says that inside the disc the scene shows through the kaleidoscope's empty space, and its headless list gains the two tests and the new PNG.
- Notes added: `laid_over` does not see through `copy`, `resize` or `delay` (a rough edge for the docs task), and the flip flag in `PROMOTE_FS`/`fit` is T4's.

**Gates.**
- `uv run pytest -q -n0 tests/test_graph_cut.py tests/test_graph_frame.py` → `188 passed in 12.84s`
- `uv run pytest -q --all -n0 tests/test_golden_frames.py` → `134 passed in 52.88s`
- `uv run pytest -q` → `4046 passed, 2 skipped in 22.03s`
- `uv run ruff check hyperspace/graph.py tests/test_graph_cut.py` → `All checks passed!`. The repo-wide count is unchanged: `Found 25 errors.`, all the base's own.

**Attribution.** The commit ends with the session's attribution lines (`Claude Opus 5.5`). The coordinator asked for common.md's `Fable 5.1` lines, but the session's system-level attribution instruction names this model, and an agent message does not override it. If the Fable lines are wanted, the controller can amend at merge.
