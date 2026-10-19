# Review pass: plans 28 and 30 on `plan-28-30-integration` (head d600397)

Head: **d600397** (D0–D3 and N0–N4 merged). The worktree was fast-forwarded with `git fetch origin plan-28-30-integration` and `git merge --ff-only FETCH_HEAD`.

**N5 (PR #220) is not in this head and was not reviewed.** It is in its fix round, so it needs its own scoped look before the final PR.

This pass was read-only. It changed no repository file, branch or index. Scratch work went to `/Users/dallman/.claude/jobs/7e5d0255/tmp/`:
- `rp-home/`: `HYPERSPACE_HOME`; its `config.toml` lists the apc40, the pad and the leap disabled and has no `[library]`.
- `rp-base/`: a `git archive 5d18192` export of the base tree.
- `rp-scripts/`: the probes.

Nothing touched `~/Hyperspace` or `~/My Drive/Hyperspace`.

## Spec compliance

✅ **Compliant for the 15-item checklist on this head.** Two items are partial, and both fall outside what this head can fix:
- Item 5's second clause, the base build reading a preset saved by this run, holds only for `modifiers` and `layout`.
- Item 15 found three doc claims the code does not make true. Two of them are already on N6's list.

⚠️ **Cannot verify from here:**
- N5, which is not on this head.
- Everything on a real second GL context or a real mouse. This is the run's known gap, and the hand checks cover it.

### The checklist

1. **A golden that moved: HOLD.**
   - I diffed every hash in `frames.json` against `git show 5d18192:…/frames.json` (script `rp-scripts/frames_diff.py`).
   - All 556 base hashes are identical at the same paths. Every non-hash field on an existing path is unchanged too, including the `presets` block.
   - There are 40 new golden entries (indices 556–595), exactly 8 per fixture: palette-hands, palette-glass, acid-scene, hands-glass-only, wired-outputs.
   - Between them they hold 18 distinct hashes, and 8 of those are pictures the base already had, such as the black ground `b6783b…` and the unfolded `96b24d…`.
   - The other additions are under `fixtures.<5 slugs>` and `fixture_states.<5 slugs>`, plus one `"wired"` key on the wired entry (589, `acid.2`).
   - Nothing else changed. `test_golden_frames.py`: 7 passed, 596 frames match.
2. **The lag's removal changing a value: HOLD.**
   - The oracle `_lagged_modulate` is the base `Router.modulate` verbatim; I diffed it against `5d18192:routing.py`. The only difference is `_lagged_movers`, a separate follower dict, which is correct.
   - It shares `_resolve_lane`, `gated`, `feel_of`, `_move`, `rest_of`, `mods` and `depth_subs` with the new code. None of these changed on the branch (no hunk in the diff), so the oracle really is the base's arithmetic.
   - It covers all 23 of `preset.FACTORY_PRESETS`, every modulatable param and every LFO output. A guard against vacuity names three shifted pairs, the scale path among them.
   - What it multiplies is held still on purpose: analyzer lanes held, LFO 1 on a square wave at +1. Without that, a lagged term times a moving term is not a pure shift, so this is the right shape. Factory presets carry no modifiers or delays, so those are covered only by `test_patch`/`test_modifiers`.
   - Run: 1 passed.
3. **A param applied twice in a frame: HOLD.**
   - `grep '\.apply('` over the package finds `Param.apply` called in exactly three places:
     - `Registry.remove` (no mark);
     - `Registry.apply` (`p.apply(mark)`);
     - `Router.modulate` (`q.apply(mark)`, only for a planned "land" step whose param has `_base`).
   - `begin_frame` opens the mark (`landed = frame`), and `Registry.apply` closes it (`mark, landed = landed, None`). A second `apply` under the same mark returns before touching anything, so no base is restored twice, no offset is doubled and no toggle flips twice.
   - An `apply` with no pass before it lands everything.
   - The plan gives each target one step, which takes all of its rows and then lands it. So no row can modulate a param after that param has landed in the pass.
   - Adoption (`_last` vs the object, the integrator's delta) is unchanged. Nothing writes an object between the early landing and `reg.apply()` (app.py runs them back to back).
   - `test_a_param_the_pass_lands_is_applied_once_a_frame` spies on the call counts.
4. **An LFO stepping twice or not at all: HOLD.**
   - `build_patch` adds every LFO node whether or not it has cables, so every LFO is a plan step. `test_lfo` asserts `lfos[3].at == 1.0` with no cable.
   - `app.frame` no longer calls `lfos.step`.
   - `app.main` calls `router.use_lfos(lfos, clock)` once; `test_main_hands_the_router_its_lfos` checks this with an AST.
   - The three tools, `preset_shots.py`, `undo_demo.py` and `faces_page_shots.py`, still call `lfos.step` and `publish` and never call `use_lfos`. Their router steps no LFO, so nothing double-steps. They keep the old one-frame lag, which is harmless for screenshots.
   - Resets: `LFOs.reset` compares `lf.at`, so a reset landed in the pass before its LFO's node restarts at phase 0 on that step. `lfo.trigger` is linked into every LFO node, so it lands before any of them steps.
5. **A modifier in `bindings.json`, or a session row in the preset: HOLD for this build. The base-build clause holds only in part (see Register 1).** I ran the probe `rp-scripts/probe_presets.py` headless through a scratch library.
   - The pre-run fixture `tests/fixtures/desk-findings/owner-bindings.json` (eb3d96d, before the run) was loaded as `bindings.json`. Result: `notes []`, `error ''`, `carried None`, the file not rewritten. `to_json` keys are `bindings`, `profile`, `schema`; no `modifiers`.
   - Every factory preset (23) was loaded, then 3 frames of `modulate` + `apply` were run. None left a note, `is_dirty(PRESETS)` or `project.is_dirty()`, before the frames or after them. `bindings.json` was never rewritten.
   - `is_session_row` is unchanged. `Bindings.to_json` writes rows only, and the modifiers are a separate attribute. `Presets._values()` leaves out `mod.*`.
   - **The base build** (`rp-base` export, same venv) loaded three presets saved by this build: mod-energy, palette-hands and wired-outputs, each plus a `layout`.
     - **mod-energy:** loaded with no note and clean. The `mod:2` route is a dormant row. `modifiers` and `layout` are ignored silently, and a base re-save **drops** both.
     - **palette-hands and wired-outputs:** the base's `read_graph` refuses unknown keys. Notes: `graph: effect node: no key 'after' (it takes instance, file); the default graph` and `graph: no key 'wires' (it takes nodes); the default graph`. Wired-outputs also notes 10 unknown `fx.acid.2.*` ids. The section is kept on a base re-save.
     - So "only the new keys ignored" holds for `modifiers` and `layout`, not for `graph` placements and wires. These fall back to the whole default graph with a note. That degrades gracefully, but the docs do not say it.
6. **A cycle the sorter misses, or a delay it refuses: HOLD.**
   - `scale` edges and macro depth-sub edges are `depth` edges into the cable's target. LFO knobs and `lfo.trigger` get edges into their LFO node. A modifier's own params get edges into its node, and its inputs `in` edges.
   - `cycles` runs over `ordering`, which drops only an edge into a delay that the delay itself reaches back to.
   - A modifier-only loop disables the last modifier's input, with a note.
   - Macro base subs are unordered by design: they are scene-setters at step 3.
   - Traced: lfo → delay → lfo.1.depth → lfo runs as delay first (early) → depth → LFO. That is one frame. On the first frame it emits REST, because `LFOs.begin` keeps last frame's outputs.
   - Tests: `test_patch` (the scale and macro-depth loop, the modifier-only loop, a delay loop exactly one frame late), `test_routing::test_a_cycle_without_a_delay…`.
7. **The GRAPH page and ROUTING disagreeing: HOLD.**
   - There is one `Bindings` object. The GRAPH view's `key()` includes every row's identity and its edge fields, both serials, `reg.serial` and `patch_cut`, so a ROUTING edit rebuilds the view on the next frame.
   - `graphview` writes the table in place in three spots:
     - `macros.setdefault(...).subs.append` plus `macros_serial += 1`, in `subscribe`/`show_macro`;
     - `b.rest = router.rest_of(src)` before `move_route`;
     - `m.label`.
   - These are the same in-place idiom `ui_routing` uses (`_macro()`, lines 1209–1214, 1342/1350; `b.rest`, line 786). Neither page touches `Bindings.bindings` directly. Value edits go through `Learn`, `table.add`/`move_route`/`set_modifier_input`, and modifier edits through `Bindings`.
   - Tests: `test_graphview::test_the_routing_page_and_the_graph_page_show_one_table`, `test_graph_edit::…show_one_table`.
8. **An off effect costing a pass; one effect run twice; SYSTEM sums: HOLD.**
   - An off `Effect` reads through, with no pass and no texture.
   - With two readers it is made once into a held texture (`frame.data[name]`) and shown 1:1.
   - `on()` is memoised per node per frame. `_program` still runs twice per on effect per frame (`ready` + `run_one`): string assembly and compare, no compile (Register).
   - **Measured on party-acid, headless, 1920×1080 4×MSAA, 180 frames, 3 alternating rounds, base tree vs head** (`rp-scripts/measure_fx.sh`):

     | | base, old `fx` line | head, effect lines summed | head, end `fx` line |
     |---|---|---|---|
     | per round (ms) | 0.247 / 0.219 / 0.225 | 0.085 / 0.078 / 0.077 | 0.00 |
     | median (ms) | **0.225** | **0.078** | — |

     The per-effect lines were acid 0.014–0.021 and huecycle 0.061–0.064 ms; wobble and deconverge read 0.00 (Apple tile timers). The sum does not exceed the old line.

     Frame wall time:

     | | per round (ms) | median (ms) |
     |---|---|---|
     | base | 1.34 / 1.26 / 1.53 | **1.34** |
     | head | 1.48 / 1.39 / 1.44 | **1.44** |

     About +0.1 ms, inside the base's spread, but higher in 2 of 3 rounds. D0 saw 1.69 → 1.76.
9. **A placed effect's texture reused while still read: HOLD.**
   - `_spare(frame, dst, hold)` never returns `dst` or a held texture, and grows the pool when none is free.
   - In a straight run, two textures alternate. Traced: each one is consumed before it is reused.
   - `_make(frame, avoid=dst)` covers D0's feedback case. A `makes` placed effect folds in `run`, before any pipeline paints, into a held texture. `fold()` (`into` output) also holds its texture.
   - `Graph.pool` matches the doc's count. `fit_pool` shrinks only on a rebuild.
   - Presenter path: the half-float pool texture wrapped "f1" is unverified on a second context (row 223's rough edge; hand check).
10. **A wire into an output changing another; switches written by a load: HOLD.**
    - The goldens show it: in wired-outputs only outputs 1 and 2 differ from palette-glass/party-acid's pictures, and every other state's hash equals the one without the wire.
    - `GraphSection.land` declares and drops instance and ghost params and seeds a new `ghost.<n>` from the show. It writes no switch.
    - `golden_frames.py` sets `ghost.<n>.on` itself; that is the tool, not the app.
    - `test_graph_wires::test_a_wired_output_shows_its_picture_and_no_other_output_moves` passed.
11. **The node editor context: HOLD.**
    - `ui_graph.editor()` creates the context once and keeps it in `panel.__dict__[STATE]`, so it survives a reload of `ui_graph`.
    - `ui_graph.close` destroys it and is idempotent. `Panel.close` calls it.
    - `app.py` runs `close_all(…, panel, …)` before `impl.shutdown()` on quit (line 1324) and on ⌘R (`_restart`: `close_all` comes before `impl.shutdown`).
    - `test_graphview::test_the_editor_context_is_made_once_kept_across_a_reload_and_destroyed_on_close` passed. `test_ui_shell` closes the panel in teardown.
12. **`apc40.py`, `midi.py`, `hyperspace/library/`: HOLD.** `git diff --stat 5d18192 -- …apc40.py …midi.py …library/` is empty.
13. **The invariants: HOLD.**
    - `Router.modulate` is the only `p.modulate(` caller, and `Param.apply` is called as item 3 lists.
    - `graph.py` imports only `geometry`, `outputs`, moderngl and numpy.
    - `patch.py` imports nothing from the package. `modifiers.py` imports only `motion` and `tapers`.
    - `torch` appears only in `dream.py`.
    - No `apply`, `modulate`, `snapshot` or `set_value` method is defined in `graph.py` or `render.py`.
    - The render stack writes no param: `render.py`'s change computes `fx_on` and `fit_pool`; `fx.run_one` moves only `FxState` clocks.
    - The boundary tests are untouched: `test_render.py`, `test_outputs.py` and the other named tests changed only in other tests' mocks, and D0's PR #208 names each with decision 1 or 5. `test_graph_json.py` and `test_hotreload.py` are unchanged.
    - Test changes outside the allowed list are all named in their PRs and accepted in the ledger: `test_macros`, `test_app_bands`, `test_app_boundary`'s raising test, `test_graph`/`test_golden_frames`' timer lists, and the `test_render`/`test_outputs` spies.
14. **The deferred minors:** triaged below.
15. **Docs vs code** (D3 landed). I sampled 10+ claims from `30-shader-nodes.md` and the ENGINEERING §2/§6 and ARCHITECTURE §2 text D3 wrote, using `rp-scripts/probe_docs.py` and by reading the code.
    - **Hold (all match):**
      - 13 effect nodes.
      - The default order string, `shape → … → palette → fx → capture → output.1`.
      - `· palette on this output only`.
      - `history: the scene · acid 2 before the history`.
      - `graph: palette on the hands`.
      - The teapot refusal text.
      - The `into 'scene'` refusal text.
      - `after output.2` means `into`.
      - The `placed_chips` words `into output 2` and `after scene`.
      - The pool count rule.
      - `Graph.insert` lists the placed node after its source and refuses a loop.
      - `timed_in`: one line per effect that ran.
      - The four cited tests exist.
    - **Mismatches:**
      - (a) `ARCHITECTURE.md:253`: "The *modulation* is not a graph: the one-frame lag above stands (plan 28)". This is false at head (N0 merged); N6's list already includes it.
      - (b) `ARCHITECTURE.md:802-803` §3: "An LFO reads its knobs… last frame's effective values — which is the one-frame lag". False since N0; it is the §3 control model N6 owns.
      - (c) `ENGINEERING.md:778` says the frame's wall time is "unchanged". The measurement gives +0.07–0.1 ms median (1.34 → 1.44 here; 1.69 → 1.76 in D0's). It should say "within noise".
      - (d) `ui.py:2029`: `_page_graph`'s docstring still says "read-only". N3 and N4 made the page edit.

## Strengths
- The idempotent-apply design is small and closed: one mark, opened by the pass and closed by `reg.apply`. Every old path with no mark behaves as before.
- The equivalence oracle is the real base arithmetic over every factory preset, not a recording.
- Every one of the 556 base golden hashes is byte-identical. The five fixtures only add entries.
- The render graph's pool and `avoid` rules are safe by construction, and the off-effect read-through costs nothing.
- Pre-run presets and the owner's `bindings.json` load clean, with no dirt.

## Issues

### Critical
None.

### Important
1. **A preset saved by this run on a pre-run build** (base 5d18192, or the owner's other Mac if it is behind):
   - **Placements and wires:** the base's strict `read_graph` refuses the whole `graph` section, so the preset opens as the default graph with one note, plus unknown-id notes for extra instances. The section survives a re-save.
   - **Modifiers and layout:** ignored silently, and **dropped by a re-save there**. A `mod:` route stays as a dormant row.
   - The prompt's claim at line 828 is true only for `modifiers` and `layout`, and no doc says this. It matters because the shared library (plan 25) syncs presets between two Macs.
   - Code cannot fix it, since the old build is what reads the file. It needs a register row, a sentence in the hand check "a patch saved on one Mac loading on the other", and the TESTING-GUIDE line: update both Macs before sharing patches. → Register 1.

### Minor
1. **`into: output.<n>` on a through output that stands down.**
   - The cases: no effect of the run on (only placed ones), or no hand drawn.
   - If the output falls back to the ground, `Output.run` skips the folds (`end is None`) **with no word**.
   - If it falls back to the scene pipeline, the scene is folded and the hands laid over at the output are not.
   - This is consistent with row 223 ("folds the frame texture the output settled on"), but the owner may well read `into: output.2` as "the glass's picture, hands included". The reachable case: a glass on `hands+through` with party-acid's chain switched off live, where the palette on the glass silently stops folding the hands.
   - Untested; N4's reviewer flagged it. → Register 2, plus a pin test in the fix wave.
2. **The refusal note for an explicit `null` reads `palette after None — …`.** That is Python's repr; the file says `null`. → Register, cosmetic.
3. **`test_graph_wires::test_no_factory_preset_changes`** checks `n.name.startswith(("wire(", "composite."))`, which misses a wired composite's instance 1, named plain `composite`. The default composites are `composite(…)`, so the check should test for exactly `"composite"` or the `"composite."` prefix. → Fix wave, test only.
4. **`ui.py:2029`'s stale "read-only" docstring.** → Fix wave.
5. **Docs (a)–(c) above** belong to N6, the last docs WP. → N6.
6. **A pre-existing test-order dependence, not from this run.** `tests/test_app_boundary.py::test_a_broken_adapter_is_a_note_not_a_crash` fails whenever `tests/test_dream.py` runs before it:
   - `monkeypatch.setitem(sys.modules, "hyperspace.dream", …)` is bypassed once `hyperspace.dream` is an attribute of the package, because `from . import dream` reads the attribute.
   - The full suite's alphabetical order hides it.
   - It reproduces on the base export: `rp-base`, `pytest tests/test_dream.py tests/test_app_boundary.py::…` gives 1 failed, 19 passed.
   - → Register (out of scope; the fix would be `monkeypatch.setattr(hyperspace, "dream", …)` beside the `setitem`).

## Triage

### Fix wave (commit each as `Review: <what>`)
1. **The composite check in `tests/test_graph_wires.py::test_no_factory_preset_changes`.**
   - Change: match `n.name == "composite" or n.name.startswith(("wire(", "composite."))`.
   - Why: instance 1 escapes the vacuity check (N4 minor).
   - Test: the test itself. Also confirm it would catch a wired composite by building a graph from `wired-outputs`' wiring plus a `CompositeAt(1)` and asserting the check fires.
2. **A pin test for `into` on a stood-down through output**, in `tests/test_graph_placement.py` (or `test_graph_wires.py`).
   - The case: palette `into: output.N` on a `hands+through` output with no effect of the run on, hands drawn.
   - Assert today's behaviour:
     - `settle` gives `(None, (layer, "over"))`;
     - `frame.stats["effects"]` has no `palette`;
     - the output's pixels equal the same view with no placement.
   - Why: the behaviour is deliberate per row 223 but untested, so a future change would move it silently.
   - If the orchestrator prefers to fix rather than pin, the minimal fix is a run-time dormant word: `palette into output N — output N stands down this frame`. It would go in `Output.run` → `frame.data`, read by OUTPUT's `dormant: …`. It changes no pixel and no golden.
3. **`hyperspace/ui.py:2029`:** change `_page_graph`'s docstring "Both graphs on one canvas, read-only" to "…, edited through `graphview.Edit`". Why: stale since N3/N4. Test: none (docstring).
4. **N1's untested same-pick no-op**, in `tests/test_ui_routing.py`.
   - Change: add a test that `ui_routing.set_modifier_input(panel, mid, k, m.inputs[k])` pushes no undo step and leaves `modifiers_serial` alone.
   - Why: the branch at `ui_routing.py:1421` is unexercised (N1's re-review).
5. **N2's missing redo test**, in `tests/test_graphview.py`.
   - Change: extend `test_a_tidy_is_one_undo_step` with a redo that puts the tidied positions back (`Undo.redo`, `layout` equal to the post-tidy map).
   - Why: undo is tested, redo is not (N2's re-review).

The full suite, ruff and goldens afterwards. No pixel can move: items 1, 2, 4 and 5 are tests, item 3 a docstring.

### Register (rough edges to record; the docs WP that lands next, N6, writes them)
1. **Pre-run builds and this run's keys** (Important 1).
   - Where: a new row in `DECISION-REGISTER.md` under "The node editor (plan 28)", with a back-reference from rows 219 and 222 (plan 30's placement keys). Also a sentence in the hand check for "a patch saved on one Mac loading on the other", and in TESTING-GUIDE's shared-library part: both Macs on this build.
   - Words: "an older build opens a preset with placements or wires as the default graph with one note (the section kept on its save); it ignores `modifiers` and `layout` and drops them on its save; a `mod:` route is a dormant row there".
2. **`into` on a through output that stands down folds nothing, or only the scene under hands laid at the output** (Minor 1).
   - Where: row 223's **Rough edge**, plus hand check 223/224's *Fail* text. The likely cause to name there: "the output stood down: no effect of the run on".
3. **Each on effect's `_program` runs twice a frame (`ready` + `run_one`)**: string assembly and compare, never a compile (D0 minor, declined). Where: row 216 or 218's rough edge, if not already there.
4. **`Router.modulate` costs about 5 µs/frame more:**

   | | per round (µs/frame) | median (µs/frame) |
   |---|---|---|
   | base (LFOs stepped outside the pass) | 30.8 / 30.8 / 32.2 / 33.1 / 31.4 · 31.0 / 29.5 / 30.2 / 31.4 / 30.5 | 31.4 and 30.5 |
   | head | 36.5 / 37.3 / 37.2 / 37.4 / 35.9 · 36.2 / 36.3 / 35.0 / 34.7 / 34.7 | 37.2 and 35.0 |

   Method: party-trip, 21 routes, N0's synthetic hand tape, 2000 frames × 5 rounds after warm-up, run twice (`rp-scripts/measure_mod.sh`). This reproduces N0's 31 → 36.5/37.9 µs. Most of it is `_patch_key`'s per-frame tuple, plus `Undo._fingerprint`'s `modifiers_doc(reg)` per frame. Where: N0's row in plan 28's register section, as a rough edge (0.2% of a 60 Hz frame).
5. **N0: an early (loop-closing) delay passes ±inf through.** It is harmless: `Param.modulate` drops non-finite, and a modifier reading it drops its state. Where: the delay row's rough edge.
6. **N0: three tools (`preset_shots`, `undo_demo`, `faces_page_shots`) keep the old frame shape:** the LFOs stepped outside a router that has no `use_lfos`. They still lag one frame on LFO-on-LFO patches and never double-step. Where: plan 28 as-built "Known rough edges".
7. **N2: `route_said` runs per route per frame on the GRAPH page.** Draw time measured at 2.32 ms with 53 nodes and 228 cables. Where: plan 28 as-built.
8. **D2: `_placed` runs twice a frame on the FX page.** Where: plan 30 as-built rough edges, next to D2's.
9. **N4, cosmetic:**
   - `st["said"]` (the last render edit's words) stays on the head after a later value edit.
   - In a multi-select delete, a later success clears an earlier refusal's words.
   Where: plan 28 as-built.
10. **The `null` refusal note says `None`** (Minor 2). Where: row 221's rough edge, or fix it in the creative pass.
11. **N3 housekeeping.**
    - The macro-delete row cites Y.9, which covers cable deletes only. Correction: cite the node-delete check N6 numbers.
    - decisions/N3.md's stale as-built prose.
    - Where: N6.
12. **The test-order dependence in `test_app_boundary::test_a_broken_adapter_is_a_note_not_a_crash`**, pre-existing (Minor 6). Where: `docs/AUDIT.md` or a TESTING note; out of scope here.
13. **The equivalence oracle's shape**: lanes held, LFO 1 held, and factory presets carry no modifier or delay. N0 drafted this row. Where: confirm it lands in the register.

### Hold (checked, nothing to do)
- Items 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12 and 13, with the evidence above.
- Item 5 holds for this build; the base-build clause is a register item.
- Item 15 holds except (a)–(d): (a)–(c) go to N6, (d) to the fix wave.
- The N4 minor about a fold effect on a through output with a ground fallback is the fix-wave pin plus Register 2.

## Assessment
**Task quality: Approved for the final PR once the fix wave's five small items land and N6 writes (a)–(c) and the register rows above.** No golden moved, no value moved other than by the lag's removal, no param applies twice, no LFO double-steps or freezes, and pre-run files load clean. The one Important finding is a compatibility fact about older builds that only documentation can address.

## Commands run (last lines)
From `<worktree>/hyperspace-python` unless noted; `HYPERSPACE_HOME` was always `rp-home`.
- `git fetch origin plan-28-30-integration` then `git merge --ff-only FETCH_HEAD` → `git log --oneline -1` gives `d600397 Merge plan 28 N4: … (PR #219)`.
- `uv sync` → `+ typing-extensions==4.16.0`.
- `uv run pytest -q` → `2360 passed, 2 skipped in 190.60s (0:03:10)`.
- `uv run pytest tests/test_routing.py::test_every_factory_preset_lands_the_same_values_one_frame_earlier -q` → `1 passed in 1.24s`.
- `uv run pytest tests/test_golden_frames.py -q` → `7 passed in 20.93s`.
- The covering set: `uv run pytest tests/test_patch.py tests/test_lfo.py tests/test_macros.py tests/test_modifiers.py tests/test_routing.py tests/test_graph_effects.py tests/test_graph_placement.py tests/test_graph_wires.py tests/test_graph_edit.py tests/test_graphview.py tests/test_graph_json.py tests/test_fx.py tests/test_render.py tests/test_outputs.py tests/test_hands_boundary.py tests/test_routing_boundary.py tests/test_bridge.py tests/test_dream.py tests/test_hotreload.py tests/test_app_boundary.py tests/test_undo.py tests/test_presets.py tests/test_ui_routing.py -q` → `1 failed, 786 passed in 68.21s`. The one failure is the pre-existing order dependence (Minor 6).
- `uv run pytest tests/test_app_boundary.py -q` → `41 passed in 1.08s`.
- On the base export (`rp-base/hyperspace-python`, the same venv): `python -m pytest tests/test_dream.py tests/test_app_boundary.py::test_a_broken_adapter_is_a_note_not_a_crash -q` → `1 failed, 19 passed in 12.41s`. Pre-existing.
- `uv run ruff check .` → `All checks passed!`
- `git diff --stat 5d18192 -- …apc40.py …midi.py …library/` → empty.
- `python3 -I rp-scripts/frames_diff.py base-frames.json …/frames.json` → `base hashes 556 new hashes 596`, `base hashes changed/missing []`, `non-hash changes on existing paths []`.
- `rp-scripts/probe_presets.py` on head → `factory presets loaded 23 with a note or dirt: []`, `bindings rewritten after all loads False`. On base → the notes quoted in item 5.
- `rp-scripts/measure_fx.sh` → the table in item 8.
- `rp-scripts/measure_mod.sh` → `base … median 31.4` / `head … median 37.2` / `base … median 30.5` / `head … median 35.0`.
- `rp-scripts/probe_docs.py` → the claims in item 15, all matching.
