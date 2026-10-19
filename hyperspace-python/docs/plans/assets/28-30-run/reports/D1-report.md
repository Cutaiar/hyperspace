# D1 report: placement in the preset

**Status:** DONE_WITH_CONCERNS (the concerns are listed below).

- **Base:** `634f408`, confirmed after the reset.
- **Branch:** `plan-30-d1-placement`.
- **PR:** https://github.com/Cutaiar/hyperspace/pull/213

## Commits
- `debb347` Placing an effect after or into any image edge from the preset's graph
- `ec4b9a4` The three placement fixtures and their goldens (D1 fixture, new)

## What was built
The full list is in `decisions/D1.md` §3.

- **`EffectAt`** gains `after` / `into`, and instance 1 may be named when placed.
- **`read_graph(section, effects=)`**
  - A refused placement is a note in `GraphSpec.notes`, and that effect takes its default placement while the rest of the graph lands.
  - Refusals: both keys at once, a non-string, a name outside the vocabulary, `into` scene/hands (their inputs are geometry), an effect placed on itself, or a loop.
- **`Wiring.placed`**, which is part of the renderer's graph key.
- **`default_graph`**
  - Placed effects are left out of the runs and put on their edges with `Graph.insert`. Each is listed right after its source, so SYSTEM shows it under that source.
  - A placement on a node the graph lacks is dormant: no node, and its words go in `Graph.dormant`.
  - A loop is refused again at build (`Graph.notes`).
- **`Effect`**
  - **Placed after a texture-maker** (the scene or a layer): it folds the texture once, in `run`, into a held pool texture. That makes D0's aliasing safe by construction.
  - **On a layer:** it uses `opaque=0`, the layer's alpha and its depth. The layer's readout is split always.
  - **Into an output:** `Output.folds` folds the settled frame texture, and that pipeline is never painted direct.
  - **Pool:** 2, plus one per held, made or folded effect.
- **Words**
  - `placement_words`, `output_placement_words`, `history_words` and `graph_words(spec, dormant)`.
  - `ui.output_shows(…, n=)`, `ui.dormant_lines`, and the OUTPUT hover and dormant lines.
- **`GraphSection.read`** is now an instance method that passes the effect files on disk, and returns "; the default placement" notes.
- **Fixtures:** 3, force-added. **Goldens:** 24 new; 556 → 580.

## Tests
`tests/test_graph_placement.py` has 11 tests: the nine named in the section, plus `test_after_scene_and_into_the_history_in_the_graph` and `test_the_words_say_the_placements`.

- The `after hands` test checks four things:
  - the scene texture is byte-identical with and without the palette;
  - the layer texture is identical;
  - the output differs only where the layer covers it, and it does differ there;
  - the pass runs once a frame, from `ghost.tex` with `opaque=0`.
- The `after scene` test spies on `lookback.capture`. The capture's source is a pool texture, not `scene.tex`, and the history reads the same effect.

## Gates
```
uv run pytest -q                              -> 2288 passed, 2 skipped in 283.33s
uv run ruff check .                           -> All checks passed!
uv run pytest tests/test_golden_frames.py -q  -> 7 passed in 28.69s
smoke: HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<worktree>/.sdd/home ([midi] enabled=false, no [library];
       projects/party.hyp.json startup = palette-hands) uv run hyperspace -ApplePersistenceIgnoreState YES -> exit 0
git diff --stat origin/plan-28-30-integration -- hyperspace/library/ hyperspace/apc40.py hyperspace/midi.py -> empty
frames.json diff vs base: 0 removed lines (insertions only)
```

## Files changed
- `hyperspace/graph.py`
- `hyperspace/fx.py`: the `run_one` `opaque` keyword. This file is not in D1's list.
- `hyperspace/preset.py`
- `hyperspace/ui.py`
- `tools/golden_frames.py`
- `tests/test_golden_frames.py`: the count only.
- `tests/test_graph_placement.py`: new.
- `tests/fixtures/presets/{palette-hands,palette-glass,acid-scene}.json`
- `tests/golden/frames/frames.json` and 6 PNGs.

## Concerns
1. **`fx.py` was touched.** `run_one` gained the `opaque` keyword so a layer's see-through ground survives the palette. D2 edits the same file, on other lines.
2. (Fixed in round 1: a placed effect no longer counts toward the renderer's `fx_on`.)
3. (Fixed in round 1: presenters get the folded hands and frame.)
4. **The smoke run had no hand tape**, because none exists in the repo and recording one was out of scope. "SYSTEM shows `palette` under `hands`" is proven headless only (graph order plus `timed_in`), not in the window.
5. **The folded ghost hands read grey-teal, not a vivid blue,** because the ghost's colours are low-saturation. That is for the owner's eye (X.4).
6. **The prompt's "note-and-default"** is read as the effect's default placement, with the graph kept, rather than the whole default graph. Its quoted words end "; the default placement".

## Decisions file
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/D1.md` has:
- 7 register-row drafts;
- hand checks X.4–X.9;
- the as-built notes;
- the departures.

## Fix round 1 (commit 6686b5e, pushed to PR #213)

### IMPORTANT 1: presenters
- **`Effect.ghost(frame)`** passes through to the source layer's Ghost. With hands 2 making the layer, the presenter gets ghost 2's opacity again.
- **`Output.run`** hands `_compose` the laid effect's folded texture as `hands_tex`. In `Renderer._compose`, the presenter branch sends `hands=hands_tex or gh.tex`.
- **`into: output.N`** with output N a presenter: `handoff.frame` is the folded texture. This already worked through the folded `frames` dict; it is now tested.
- **`Handoff` docstring:** `frame` / `hands` may be a half-float pool texture. `Presenter._ext` wraps every name as "f1", which only declares the wrapper's dtype; a shader samples by name whatever the real format. This is registered as a rough edge (plan 26's contract, widened).
- **Decisions file and report:** the "no rig output uses a presenter" sentence is gone.
- **Test** `test_a_presenter_lays_the_folded_hands_and_shows_the_folded_frame`:
  - with `after: hands`, `handoff.hands` is a held pool texture, not `ghost.tex`, at alpha 0.7;
  - with `after: hands.2` (hands 1 in the scene, hands 2 the layer), the fold reads `ghost2.tex`, `Effect.ghost` is ghost 2, and `handoff.alpha` is 0.25;
  - with `into: output.2` and output 2 a presenter, `handoff.frame` is a pool texture and output 1 is byte-identical to the frame without the palette.

### MINOR 2: `fx_on`
- **What changed:** `Renderer._draw_frame` builds the graph first and sets `fx_on` to "some name in `chain(FRAME)` is not in `Graph.placed_names`". It also records `stats["fx_on"]`.
- **Base equivalence:** with no placements this is exactly `fx.active()`.
- **`_chain_now`** no longer gates on `fx_on`: `chain()` is already empty when the stack is off, so the base is identical.
- **Clocks:** `Capture` moves them when `fx_on` is on or any effect is on, so a placed effect's clock moves even when its edge had nothing to fold.
- **OUTPUT page:** `_outputs_now` reads `stats["fx_on"]`.
- **Test** `test_a_placed_effect_alone_bends_no_pipeline`: `fx_on` is False, `chain_runs` is 0, a through output routes SCENE with hands over, and there is no SCENE+HANDS pipeline.
- **Goldens:** all 580 hashes still match. The palette-hands through frames were already the same picture.
- **Manifest metadata:** palette-hands was re-recorded with `--only palette-hands`. Only two entries' `route` / `hands_over` changed; no sha256 changed:

  | State | Before | After |
  |---|---|---|
  | scene+hands+through | SCENE+HANDS, no hands over | SCENE, hands over |
  | hands+through | HANDS, no hands over | none, hands over |

  This is noted on the PR as a comment.

### MINOR 3: explicit null
- An explicit `"after": null` / `"into": null` is now a present key, refused as a non-string: `palette after None — a node's name in quotes`, then the default placement.
- Two cases were added to `test_an_unknown_placement_is_a_note_and_the_default`.

### MINOR 4: `opaque`
The decisions file now has a sentence explaining why the node decides `opaque` from its source (`see_through`) rather than the edge carrying it. A layer's picture is premultiplied over a see-through ground wherever it is read, so no edge or wire (D2, N4) needs to carry `opaque`.

### Files
`hyperspace/graph.py`, `hyperspace/render.py`, `hyperspace/outputs.py` (docstring), `hyperspace/ui.py`, `tests/test_graph_placement.py` (13 tests), `tests/golden/frames/frames.json` (2 route fields).

`render.py` and `outputs.py` are new to this PR, as the fix needed.

### Commands
```
uv run pytest tests/test_graph_placement.py tests/test_graph_effects.py tests/test_graph.py tests/test_outputs.py tests/test_render.py tests/test_graph_json.py -q  -> 239 passed in 20.36s
uv run ruff check .                            -> All checks passed!
uv run python tools/golden_frames.py           -> all 580 frames match their goldens (Apple M3 Max)
uv run pytest tests/test_golden_frames.py -q   -> 7 passed in 20.32s (after the metadata re-record)
```
