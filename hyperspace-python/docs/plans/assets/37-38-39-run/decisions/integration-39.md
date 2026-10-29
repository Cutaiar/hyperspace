# Integration 39: decisions (plan 39 into plan-37-38-39-integration, head 2b185ea)

## Register-row drafts

**4xx. A held matte, cut or segment keeps its knobs for the projector (HELD_GROUPS)**
- **Answer:** controller — 2026-10-27 (taken at integration; the brief did not name it).
- **Built:** `hold.HELD_GROUPS` gains `matte`, `cut` and `segment`, as `resize` was already held. While held, a key, amount, feather or smooth turned on a node the program shows only changes the preview. The program draws the value as it was at HOLD. The head's red line counts these knobs as "changed".
- **Other options:** leave them one-for-both. A knob turned while held would then move the projector, the thing the hold exists to stop.
- **To reverse:** cheap. Drop the three names from the tuple.
- **Rough edge:** `segment.mode` and `segment.quality` are held too. The program renderer's worker reads the held value during the program draw and the live value outside it. The preview has no worker (ruling 13), so in practice only the program reads it. No one has watched a mode switch while held.
- **Judge it:** AJ.1.

**4xx. `segment` stays cold for hot reload; `masks` is hot**
- **Answer:** controller — 2026-10-27 (39-T2 review 10, 39-T4 notes).
- **Built:** `masks` sits on `hotreload.MODULES` after `glsl` and before `render`. Saving masks.py while the app runs re-executes it and re-binds `render.MaskPasses`. `segment` is left off, like `app`: its worker threads outlive a reload, so a re-executed copy would be a second module next to the live workers. A comment in hotreload.py and in test_hotreload.py's `cold` says so.
- **Other options:** put `segment` on MODULES. The workers would keep their old class while new nodes use the new one.
- **To reverse:** cheap (one line in each of two files).
- **Rough edge:** an edit to segment.py needs a restart.
- **Judge it:** AJ.2.

## Hand-check drafts

**AJ.1 Hold a look with a matte, a cut and a segment, then build something else (projector + control window)**
Headless: `tests/test_hold.py::test_a_landing_while_held_keeps_the_programs_mattes_cuts_and_segments`, `::test_a_knob_turned_on_a_held_matte_cut_or_segment_stays_off_the_projector`, `::test_drop_after_a_blank_landing_brings_the_mattes_cuts_and_segments_back`, `::test_every_kind_a_landing_settles_has_its_program_ids`.
1. Load a preset whose graph has a matte, a cut and a segment (person mode) on the projector.
2. Press HOLD. Press New (a blank graph), then turn nothing.
3. Check the projector: the cut person is still there and still live.
4. Load the matte preset again on GRAPH and turn its key. The projector must not change.
5. Press DROP. Then HOLD, New, TAKE.
6. Save while held, before TAKE, to a scratch name.
*Pass:* the projector never changes until TAKE. DROP brings the three nodes back with their values. The scratch save holds no `matte.*`, `cut.*` or `segment.*` ids when the live graph has none.
*Fail:* the projector goes black or uncut at New, so a declare is in `land`, not `_settle`. A knob moves the projector, so `HELD_GROUPS` is missing the group. The save writes the ids, so a `PROGRAM_IDS` entry is missing.

**AJ.2 Hot reload of masks.py (dev machine, app running)**
Headless: `tests/test_hotreload.py` (MODULES order and the cold set).
1. With a matte on the projector, change a comment in hyperspace/masks.py and save.
*Pass:* no error line, and the matte keeps drawing.
*Fail:* an import-order error, so `masks` is after `render` in MODULES.

## As-built notes
- **Conflict:** one hunk in `hyperspace/preset.py` `GraphSection.land`. Plan 38 replaced the per-kind settling with `self._settle(spec)`. Plan 39 had added three declares to the old inline block. Resolution: `land` calls `_settle(spec)` only. `declare_mattes`, `declare_cuts` and `declare_segments` sit in `_settle` after `declare_resizes`, reading `names["matte"|"cut"|"segment"]` after `hold.keep`. `names()` gains the three kinds in both branches, and so does `_settle`'s no-spec dict. Docstrings cite plan 39. Against each parent, nothing is lost: the diff against 9560027 is additions only, and the diff against plan-39-vision is plan 38's hold changes only.
- **hold.py:** `PROGRAM_IDS` gains `matte`, `cut` and `segment` (`matte_ids`, `cut_ids`, `segment_ids`). `HELD_GROUPS` gains the three groups (row above).
- **hotreload.py:** `masks` follows `glsl` in MODULES. test_hotreload's `cold` loses `masks`.
- **Tests:** four new tests in `tests/test_hold.py`. One existing test was changed on purpose: `test_program_only_knows_every_kind_and_every_file_live` used `matte` as its example of a kind missing from `PROGRAM_IDS`. It now uses a made-up kind, `future`, because `matte` is in the table.
- **Not verified by a person:** everything above. The segment worker's life while held is tested only through its state and params. The headless hold rig has no Renderer, so no worker test runs under a hold. The worker is the program renderer's, kept by node name while the held wiring draws it.

## Not done, and why
- No GL test of a segment worker under a hold. The worker belongs to the renderer. The held wiring keeps its node drawn, so `_tend_segments` keeps the worker; the code was read, not tested.
- `uv run ruff check .` reports 25 errors in files this merge did not touch: docs/plans/assets/39-vision/bench_*.py, hyperspace/media/*, tools/ingest.py and four tests. The touched files are clean.
