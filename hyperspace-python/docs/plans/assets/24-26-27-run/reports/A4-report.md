# A4 report — the graph in the preset as JSON; node instances and the naming rule; the OUTPUT and LOOKBACK pages in words

**Status:** DONE_WITH_CONCERNS
**Branch:** `plan-26-a4-graph-json` · **Base:** `plan-24-26-27-integration` at `3fa2f88` ("Merge plan 26 A3: the hands as a geometry node … (PR #187)") — confirmed with `git log --oneline -3` right after the reset.
**PR:** https://github.com/Cutaiar/hyperspace/pull/191
**Decisions file:** `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/A4.md`

## What I built

1. **The `graph` section** (`preset.py` `GraphSection`, `load_doc` / `document` / `signature` / `dumps`; `graph.py` `GraphSpec`, `read_graph`, `NODE_KINDS`, `HandsAt`, `EffectAt`, `HistoryAt`). Plain JSON, `{"nodes": [...]}`, one object per node that differs from the default graph (kind, instance, wiring), one per line in the file. Absent → default graph, `signature`'s new fifth element `None`, no dirt. Unreadable (unknown kind, bad value, stray key, two layers…) → a note and the default graph, kept verbatim for a save. Lands after the load's undo push (so no spurious undo step), declares instances before the file's values for them are read; a refused load puts the old graph back; `library.Marks` carries the graph so undo / redo of a load put it back first. `NODE_KINDS` is the one place a later node kind is named in the JSON (A4b's clouds do not use it: they follow the device list; a `cloud` kind is unknown until plan 28).
2. **Node instances, the naming rule.** Effects: `FxState.set_instances` → effect `acid.2` (the acid file's spec, "Acid 2"), `fx.acid.2.*` performance params, own clock and order, one compiled program per file; `fx.declare` never drops an instance's ids when re-declaring its file; `fx.parse` refuses a purely decimal `@param` key (A0's ask). Hands: `ghost.register(reg, state, n)` → `ghost.2.*` (session); `Renderer.ghost_of(name)` / `ghost_states` / `drop_ghosts` — each hands node its own `Ghost`; the layer node `hands.2`, readout `readout.2`; `HandsLayer` / `Readout` / `Output` per node (`frame.data`), `_compose(ghost=, readout_ghost=)`.
3. **`Hands.TIMED` fixed:** `Hands.TIMED = False`; `Graph.timed` lists solid geometries a scene draws (`Graph.in_scene`) — the consumer edge decides; the Scene no longer mutates its geometries.
4. **Hands as lines:** `HandsAt.draw` / graph JSON `draw: "lines"` → `Ghost.draw_solid(lines=)`, `Ghost.layer(lines=)`, `Geometry.draw(lines=)` (`ctx.wireframe`, reset in `finally`); guide stays solid.
5. **Words:** `graph.hands_words` / `layer_words` / `history_words` / `graph_words`; OUTPUT's "shows:" line under a preset graph (`ui.output_shows(…, wiring)`, `Panel.graph_now`, hover); LOOKBACK's `history: …` line (`ui_lookback.history_line`). Default-graph words unchanged.
6. **The proof fixture** `tests/fixtures/presets/hands-lines.json` (force-added), loaded through a scratch library by `tools/golden_frames.py` (`FIXTURE_PRESETS`), 8 new goldens; manifest `fixture_states` / `fixtures`; completeness test covers it.

## How I tested it

```
$ uv run pytest -q                       # from hyperspace-python
2171 passed, 2 skipped in 153.17s (0:02:33)      # base: 2133 passed, 2 skipped (+38 test_graph_json)
$ uv run ruff check .
All checks passed!
$ uv run python tools/golden_frames.py
all 552 frames match their goldens (Apple M3 Max, 4.1 Metal - 90.5)   # base 544 + 8 hands-lines
$ HYPERSPACE_FRAMES=240 HYPERSPACE_HOME=/tmp/a4/smoke-home uv run hyperspace -ApplePersistenceIgnoreState YES
exit 0, stall.log empty
```

- New `tests/test_graph_json.py` (38 tests): JSON round trip and every unreadable form; kind table; wiring; two-hands default graph and its SYSTEM lines; one hands node in a scene and a layer timed by its scene; words; decimal-key guard; second acid's params / clock / order / hot re-declare / reload / removal; over a scratch library (test_presets' `boot`): no factory preset carries a graph and each loads clean, the fixture lands its graph, unknown kind is a note kept for a save, two acids in data, a second hands node's session params and kept state, refused load and undone load (test_undo's `boot`) put the graph back; GL: two acids on one program, the second hands node's Ghost on the glass byte-equal to a lone ghost at its opacity (and `hands.2` in `gpu_ms`), hands as lines with the wireframe off after.
- Smoke run (windowed, scratch home `/tmp/a4/smoke-home`, config with no `[library]`, MIDI / pad / dream off, `[hands] enabled = true`, `tape = "synthetic.json"` from `tools/hands_tape.py synth`; the show `smoke` starts on `hands-lines` with `ghost.on` true; `-ApplePersistenceIgnoreState YES`): `HYPERSPACE_FRAMES=240 … uv run hyperspace` exited 0 with an empty stall log. `screencapture` is not permitted here, so a second identical run went through a throwaway probe (`/tmp/a4/smoke_probe.py`, wraps `Renderer._draw_frame`, not committed) that read output 1 back at frames 100 and 200: wiring `Wiring(hands='scene', blend='over', history='scene+hands', draw='lines', extra=())`, SYSTEM lines `ghost scene cover readout history fx capture output.1` (ghost ≈ 0.40 ms, scene ≈ 0.39 ms, history ≈ 0.18–0.46 ms), `in_scene` true, `layer` false, the chain `['acid']`, no ghost error. **What I saw** (frame 200, `/tmp/a4/smoke-frame-200.png`): both hands drawn as wire hands (a dense lattice of edges) inside the shape — the left pale blue, the right pink — the acid heaving the shape's edges and the hands together, and the tracers trailing behind both: soft smeared copies of the hands and the edges.

## Files changed

- `hyperspace-python/hyperspace/graph.py`, `render.py`, `ghost.py`, `fx.py`, `preset.py`, `library.py`, `params.py`, `app.py`, `ui.py`, `ui_fx.py`, `ui_lookback.py`
- `hyperspace-python/tools/golden_frames.py`
- `hyperspace-python/tests/test_graph_json.py` (new), `tests/test_graph.py`, `tests/test_golden_frames.py`
- `hyperspace-python/tests/fixtures/presets/hands-lines.json` (new, force-added)
- `hyperspace-python/tests/golden/frames/frames.json`, `tests/golden/frames/png/` (3 new PNGs)
- Nothing under `hyperspace/library/` (byte-identical); no doc in the do-not-edit list touched.

## Self-review findings (fixed before the PR)

- A line per output for the hands words overflowed the OUTPUT page with four outputs and the LOOKBACK page by 3 px (the page-fit tests): moved the words onto the existing "shows:" line (+ hover) and the LOOKBACK line into the spacing under the switch.
- `fx.declare(names={"acid"})` used `remove_prefix("fx.acid.")`, which would have dropped `fx.acid.2.*` on every hot edit of acid.glsl: now drops only `fx.<name>.<key>` ids.
- `FxState._adopt` keyed values by `spec.name` (the file): an instance would have overwritten the first's values; now by the effect's name.
- A load refused for a bad value after the graph landed: the old graph and its instances' values are put back (snapshot taken before the graph lands).
- The graph section's lander was first placed inside the desk-template comment block; moved to its own block.

## Concerns

- "Hands as lines" is the wireframe of the style's meshes (one pixel wide, a dense hatching of the capsules), not a skeleton of bone lines — registered with its rough edge and hand check V.21; the owner may want bone lines (plan 28 / H3).
- `ghost.2.*` are session params (the naming rule keeps the group): a show saved while a second hands node exists reports them as unknown ids if opened before a preset with the node lands; `ghost.2.on` starts off (decision 24), so a preset that adds the node shows nothing on the glass until switched on; there is no HANDS-page block for `ghost.2.*` (ROUTING / Learn reach them).
- The section is wiring choices for `default_graph`, not a node-and-wire graph: outputs stay the session's switches; at most one hands layer. Plan 28 must change this (decisions file §4).
- A4b (point cloud, PR #190) touches `default_graph` beside this; at the merge the scene line becomes `[*points, *(geo[h.n] for h in inside), shape]` (the orchestrator's). No cloud kind in `NODE_KINDS` (ruling, review round 1).

## Note on the first full run

The first full run (while I moved the `GraphSection` block in preset.py mid-run) failed `test_presets.py::test_active_follows_the_loaded_preset_from_one_place` on `inspect.getsource` reading the file as it changed; it passes alone and the clean re-run is the 2171 passed above.

## Review fix round 1 (base `8cee346`, commit `66e05ad`)

What changed, item by item:
- **IMPORTANT 1 (a load can drop the graph and refuse itself):** `preset.load_doc` now looks at every node-instance id (`params.is_instance_id`: `fx.<file>.<n>.*`, `ghost.<n>.*`) only after the file's graph has landed, against what that graph holds. So `Twice` (acid 2) → `Plain` (no section, values `fx.acid.2.twist`) loads with the id unknown and a note, and the same holds for a section that fell back (`"kind": "cloud"`). Everything from `GraphSection.land` to the values landing sits in one `try`: any raise puts the held graph back with its instances' values. Test: `test_an_instance_id_is_sorted_against_the_graph_the_load_lands` (the reviewer's scenario, plus a forced `KeyError` after the landing).
- **IMPORTANT 2 (ghost.2 settings lost on a show reopen):**
  - `library.Project` holds back `ghost.<n>.*` ids it cannot place. `_apply` does not report them, `is_dirty` and `save` carry them (`_held_back`), and `_take` counts the shows opened (`opened`).
  - `preset.GraphSection` seeds a newly declared hands node from the open show's session once per show opened. An id the show lacks takes the state the landing left.
  - Test: `test_a_second_hands_nodes_settings_survive_reopening_the_show` (open the show → the startup preset with ghost.2 → values restored, no unknown id, clean; a preset without the node → still clean, and a save keeps them; a live change survives a drop and bring-back; reopening the show brings its own values back).
  - The register draft is rewritten.
- **MINOR 1:** `graph.hands_words` / `ui.output_shows`: an output whose scene holds the hands says so whatever its hands switch (tested).
- **MINOR 2:** the GL test now renders twice with only `acid.2`'s twist changed (acid's values equal) and asserts the frames differ.
- **MINOR 3:** `FxState.load` refuses a stem with a dot or of digits alone (`acid.2.glsl`, `2.glsl`) before parsing, never kept as last good. Test: `test_an_effect_file_whose_name_would_read_as_an_instance_is_refused`.
- **MINOR 4:** `tools/golden_frames.py` records the fixture's landed graph section (`said["graph"]`), not `repr(Wiring)`. In `frames.json` only that text changed (`git diff` shows no `sha256` line). The completeness test compares it to the fixture's section. Nothing re-recorded.
- **MINOR 5 / 6:** in the decisions file only. Corrected per the ruling: clouds follow the device list, a `cloud` kind is unknown until plan 28, and nothing was added to `NODE_KINDS`. Also added the hot-reload class-identity rough edge.

Tests:
```
$ uv run pytest -q tests/test_graph_json.py tests/test_presets.py tests/test_fx.py tests/test_graph.py tests/test_undo.py tests/test_library.py tests/test_ui_shell.py tests/test_golden_frames.py -k "not byte_for_byte"
371 passed, 1 deselected in 31.30s          (before the last test edit; test_graph_json alone after: 41 passed)
$ uv run pytest -q
2174 passed, 2 skipped in 153.09s (0:02:33)   # includes test_golden_frames' byte-for-byte test: 552 frames, no hash moved
$ uv run ruff check .
All checks passed!
```
