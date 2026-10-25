# N8 report — the palette as a colour compression; its strip's controls

Status: DONE_WITH_CONCERNS (minor; see Concerns). Final register row N = **298**, hand check M = **271**.
Base: `origin/plan-28-30-integration` at 980bdd9. Fast-forward was refused because the branches had diverged, so I used `git reset --hard origin/plan-28-30-integration`, then renamed the branch to `plan-30-n8-palette-compression`.
PR: https://github.com/Cutaiar/hyperspace/pull/226 (into plan-28-30-integration)
Commits: f92d99c (code, tests, fixtures), 0ae8de6 (docs).

## What I found before changing anything
- `palette.glsl`: the header is `@order 95`, `@mix 0`, `@blend mix`. `mode` was an int `@param 0 1 0` drawn as a slider. The fold was `hue = (centre + (tri − 0.5)·width)/360` with `tri = 1 − |2·fract(h) − 1|`: a seamless triangle map, red to centre − w/2 and cyan to centre + w/2. Sat and val were already a linear MAP (`mix(lo, hi, x)`), not a clamp. The gradient mode maps luma through 2–4 anchors. With the defaults (centre 0, width 360) the fold is **not** the identity: it maps the wheel onto itself twice. That's why row 135 said "no identity exists".
- `fx.parse`: only float/int ranges with `log`/`wrap` flags, and no discrete kind. `target` and `face_map` are enums declared by hand in `declare` (`r.enum`). Reserved names: on, mix, speed, blend, order, target. A param that disappears from a file is dropped from `values` on reload. A saved preset value for an id that no longer exists becomes "N unknown id(s)" in the load notes (`preset.load_doc`), and a route to it stays dormant.
- `params.Kind.ENUM` exists and is drawn by `Panel._combo` (blend uses it).
- `ui_fx.strip_rows` packs `_lo/_hi` and `_hue/_sat/_val`; `HIDDEN_BY_MODE` hides one mode's rows. `strip` drew every param with `_row`/`_slider`.
- Users of `fx.palette.*`: palette-hands, palette-glass **and wired-outputs** (N4's, centre 200 width 60); `tests/fixtures/palettes/fx/sunset.json` (mode 1 only); tests in test_fx_palette, test_fx (strip fit and each-effect), test_graph_placement (`_palette`), test_graph_effects (mix only). Nothing under `hyperspace/library/` names `fx.palette` (I grepped, and there's now a test for it).
- Plan 26's camera.pan conversion: `params.pan_world(doc)` is called on read from `Presets.load_doc` step 0 and `library._module_values` (camera group), with a `units` marker written on save. The old palette ids are unambiguous, so no marker is needed. I used the same two call sites.
- Design intent (24 C6, 30-shader-nodes.md): the fold is a final colour pass, off and at mix 0 by default, and a saved palette is an `fx` module preset. Nothing there conflicts with the owner's new direction.

## What I built
- `palette.glsl`: compress mode with `hue_from/hue_to` (0–360, no wrap), `sat_from/sat_to`, `val_from/val_to`. The arc runs from `from` up to `to`, through 360 when to < from. Hue: the old fold expression (centre = from + arc/2, width = arc) for arc ≤ 180, bit for bit. Above 180, `tri` is replaced by an asymmetric climb whose peak `p = 0.5 + 0.5·smoothstep(180, 360, arc)`, which is the identity at 360. `mode` is `@param choice [compress|gradient] 0`.
- `fx.py`: the `_CHOICE` form plus `ParamSpec.choices` (it's in the signature); `_check_key` factored out; `declare` emits `r.enum` for a choice; `palette_slice(doc)` with `PALETTE_RENAMED` and `FOLD_EXACT`.
- `preset.py`: `load_doc` step 0 calls `palette_slice` (notes appended). `library.py`: `_module_values` handles the fx group.
- `ui_fx.py`: the choice drawn with `_combo`; the `compress_line` text under mode; `_from/_to` pairs drawn with `→`; `_hue_bar` under the hue row; `ROW_SUFFIXES` gains `_from/_to`; `HIDDEN_BY_MODE` updated; `slice_arc`.
- Fixtures: palette-hands, palette-glass and wired-outputs now carry hue 170 → 230 (notes reworded for the two D1 fixtures). Force-added.
- `graph.py`: the VALUE docstring wording only.

## Goldens
None re-recorded; all 596 match. My first rewrite (`from + arc·0.5 + (tri−0.5)·arc`, then `from + tri·arc`) moved 1 px by 1 level in `palette-glass|present|scene+hands+through` and `wired-outputs|present|scene+hands`; that's fast-math reassociation. Computing `centre`/`width` as locals and keeping the old expression moves nothing. I checked this with a side-by-side render of the base shader and fixtures (24 frames, 0 differ), then with test_golden_frames.

## Changed assertions (reason: the N8 ids and defaults, rows 291–297)
- tests/test_fx_palette.py: key set, defaults tuple, `hue_from/hue_to` instead of centre/width (narrow = 200 → 200 with `sat_from=1`), hot-reload edit on "Hue to", route target `hue_from`, `val_from` in the alpha test.
- tests/test_fx.py::test_the_palette_strip_fits_in_both_modes: `val_to`; `mode` now drawn by `_combo` and not `_slider`.
- tests/test_fx.py::test_each_effect_changes_the_frame (palette case), tests/test_graph_placement.py::_palette, tests/test_graph_effects.py (two lines): set a slice, because the defaults are now the identity.

## Tests
tests/test_palette.py (18 new): identity at defaults; red (350 → 10, sat .6–1, val .3–1), yellow (45 → 75), wrapping (300 → 60), one hue and wide (0 → 270) slices on a synthetic rainbow through the real shader via `FxChain.run_one`; inverted val; gradient still works; choice parsing and refusals; registry enum; strip rows and the compress line; `palette_slice` (values, instances, routes, width-360 note, new form wins, identity on a new doc); an old preset through `Library.load` (no note, routes moved, save writes the new keys); an old fx module preset; fixtures need no conversion; no factory file names the palette.

## Gates
```
uv run pytest -q                              -> 2405 passed, 2 skipped in 187.65s (base 2387 + 18)
uv run ruff check .                           -> All checks passed!
uv run pytest tests/test_golden_frames.py -q  -> 7 passed in 20.08s
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<worktree>/.sdd/home ([midi]/[gamepad]/[hands] enabled=false, no [library]) uv run hyperspace -ApplePersistenceIgnoreState YES -> exit 0
git diff --stat origin/plan-28-30-integration -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py -> empty
```
(The graph.py docstring edit came after the full run; ruff was run again and is clean.)

## Docs (in the PR)
DECISIONS (palette row rewritten, owner 2026-10-20; decision-2 row amended; the ids row and strip row updated); DECISION-REGISTER (intro, answer sheet 291–298, section with rows 291–298, rows 135/136/138/139 marked superseded in part); 11-hand-checks (header range 1–271, the before-you-start list, 267–271 at the end of group X, 166/167/223/231 and the two-palettes variant rewritten, the "what no test covers" bullet); TESTING-GUIDE (C9–C11, L129, L130, tables, branch line, L69/L70/D23 rewritten, a judge item); 30-shader-nodes.md (intro ranges, N8 section, centre/width mentions, decision 2); ENGINEERING §2 palette paragraph and VALUE port; README and CHECKPOINT ranges (rows 214–298, checks 220–271).

## Concerns
- The hue params don't wrap, so a route that turns the slice stops at 0/360 (row 291).
- Slices wider than 180° are a choice nobody has looked at (row 292).
- Old centre/width presets wider than 180° convert to a different look; they get a note.
- Macro subscribers and position routes on the old centre/width are not converted.
- The `.sdd/` scratch folder in the worktree (scripts, scratch home) is untracked and not committed.
- If N9 lands first, renumber rows 291–298 and checks 267–271.

## Fix round 1 (commit 183485c, pushed to PR #226)

**IMPORTANT 1, the stray wide-fold note.** The note now appears only when the palette would show the change: the instance is on with mix > 0, or a route or desk row names one of its ids, and it is in compress mode with a fold wider than 180°. At w ≥ 360 the note reads "the old fold doubled the whole wheel; its slice 0 → 360 now leaves the colours as they are". Values are written only for an instance whose centre/width were present, or set outright. New test `test_a_full_snapshot_from_before_loads_with_no_note_and_no_dot`: a full performance snapshot with the old palette ids at their defaults, palette off, loads with no note and `is_dirty(PRESETS)` False. New test `test_a_wide_fold_is_said_only_when_it_shows` covers off, mix 0, gradient, 360, 270, 180, and a route on mix.

**IMPORTANT 2, macros.** `palette_slice` now converts `doc["macros"]`:
- Base and depth subscribers on `_lo`/`_hi` are renamed.
- A depth subscriber on a centre route moves to `hue_turn`.
- A depth subscriber on a width push is split into one each for `hue_from` and `hue_to`. Its from/to stay the same, since `Router` multiplies the route's depth by `s.at(m)`, and the halving/negation already sits in the split route values.
- A base subscriber on the width is converted about the document's centre when both ends stay inside 0–360 over its travel. Otherwise it is dropped with a note.
- A base subscriber on the centre: see "set outright" below.
Test: `test_the_macros_follow_their_params_and_routes`. The load test also checks a depth subscriber through the real `Library.load`.

**IMPORTANT 3, the slice collapsing or ballooning.** I added `uniform float u_hue_turn; // @param 0 360 0 wrap "Hue turn"`, and the shader adds it to the centre (`centre = from + arc/2 + turn`). The goldens are unmoved, since the turn defaults to 0. Every row on the old centre now goes to `hue_turn` and wraps exactly as the centre did.

When something sets the centre outright (a `position` route, or a base subscriber), the arc is laid about 0 and `hue_turn` holds the centre. Example: centre 200, width 60 becomes 330 → 30, turned 200. Those rows then move to `hue_turn` unchanged.

Tests:
- `test_the_turn_moves_the_whole_slice_and_keeps_its_width`: the shader at turns 0, 90, 200 and 330.
- `test_a_converted_centre_push_turns_the_slice_through_a_full_turn`: through the real `Router`; the arc stays 170 → 230 while the turn goes round.
- `test_a_centre_set_outright_becomes_the_turn`.

Row 291 is corrected.

**Minors:**
1. The identity claim is now limited to an opaque ground, in ENGINEERING §2, DECISIONS, row 291, 30-shader-nodes, the shader comment and the test comment.
2. Row 138 now reads "Superseded in part" in both the answer sheet and the section.
3. Rows 225, 231 and 269 now carry the N8 pointer.
4. CHECKPOINT now says 2411.
5. `palette_slice` moved to the new leaf `hyperspace/palettecompat.py`, which imports only copy and re. It is in `hotreload.MODULES` before `undo`. `fx.py` drops `copy`, and `library.py`/`preset.py` import from the leaf.
6. The mode label now calls `_ctx_label`.
7. The PR body now lists `library.py`, `graph.py`, `hotreload.py` and `palettecompat.py`.

**Strip.** `ROW_SUFFIXES` gains `("_from", "_to", "_turn")`, so the hue row draws from → to plus a 64 px turn slider. The compress line adds "turned N°" when the turn is non-zero, and the hue bar is drawn as turned. Hand checks 270, 271 and 231 (Palette 2's hue turn), and TESTING-GUIDE L129, L130 and D23, are updated to match.

**Bug I found in round 0.** My `graph.py` docstring edit came after round 0's full run, and it split "plan 29" across two lines. That broke `test_graph_effects.py::test_the_value_port_type_exists_and_no_node_uses_it` on the round-0 head. It is fixed here.

**Gates:**
```
uv run pytest tests/test_palette.py tests/test_fx.py tests/test_fx_palette.py tests/test_presets.py tests/test_library.py tests/test_macros.py tests/test_graph_placement.py -q -> 277 passed (before the last two test additions' ruff fix; content unchanged)
uv run pytest -q                              -> 2411 passed, 2 skipped in 166.57s
uv run ruff check .                           -> All checks passed!
uv run pytest tests/test_golden_frames.py -q  -> 7 passed in 19.56s (596 match, none re-recorded)
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<scratch, devices disabled> uv run hyperspace -ApplePersistenceIgnoreState YES -> exit 0
git diff --stat origin/plan-28-30-integration -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py -> empty
```
The final N is still 298 and M is still 271.
