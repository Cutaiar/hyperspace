### Spec compliance
✅ compliant. Every item in P4 / Task 4 that T4 owns is built. `wants`, `Want`, `wants_for`, `want_words`, the status-change event, `said`, the chip on the GRAPH head and the PRESET strip, and the SYSTEM lines are all present. `SCHEME_ROLE` moved to `devices.py`, and `graphview` imports it (`graphview.SCHEME_ROLE is devices.SCHEME_ROLE` is asserted). The diff touches only the brief's files. `midi.py`, `apc40.py`, `bindings.default.json`, `ui_desk*`, presets, goldens, fixtures and docs are all untouched. The group-node line (T2) and the spawn notes (T3) are rightly left to those tasks.

How each of the dispatch's doubts settled:
1. **The listeners and the hook fire on changes only.** `poll` calls `_statuses()` once, after the loop, and `_changed()` only `if self._statuses() and not told` (devices.py, the end of `poll`). `said` runs once per changed role. `test_the_hook_fires_once_per_change_with_the_count_and_never_when_steady` holds `told == [1]` and `said == []` over 100 polls, then gets exactly one of each per flip, with the counts. `test_two_devices_changing_in_one_frame_tell_the_listeners_once` covers two devices changing in one frame. I checked the status strings of every adapter (Base, Midi, Pad, Hands, Osc, Off). They come only from `connected` / `lost` / `off` / `error: …`, so nothing can change every frame. An error on an open device is masked (`_word` → None), so a flaky poll does not flap.
2. **The MIDI relight runs as before.** `midi.py` is not in the diff, and the registry only reads `d.status`. The new effect is that `point_at_devices` (app.py) now runs once when an APC40 comes back inside its adapter. I checked `Router.follow_devices`: it is idempotent, and the spec asks for exactly this. The test over the fake bus shows listeners `[1]` and the hook firing once with the real `MidiDevice`.
3. **`wants` is pure but not cheap.** See Important #1. I measured it on the fake bus with an APC40 connected (186 rows): 0.29 ms per call, 0.23 ms of which is `registry.lines()`.
4. **Role order:** `@role`, else the first MIDI role, else `apc40` for cc/note/pitch. For every other scheme the order is `primaries()`, then the first listed publisher (off ones included), then `SCHEME_ROLE`. The two registry lookups go beyond the literal spec, but they match graphview's placeholder rule (`by_scheme` before `SCHEME_ROLE`) and are needed for an off device under another role (the `hands1` test). The placeholder's words are unchanged.
5. **`routing.row_words` needs no new import.** It uses no `apc40` and takes `names` from the caller. `routing` already imported `apc40` on the base. The glyph lookup sits in `devices._desk_glyph` behind a late import.
6. **The `graphview` / `ui_graph` touches stay inside the brief, give or take two comment lines.** `ui_graph` has one call plus `_wants_chip`. `graphview` has the import, the `row_words` import, `cable_words` and two comment/docstring edits, which the report declares (Minor #3).
7. **No built-in scheme is ever named.** `NO_DEVICE_SCHEMES` = lane/lfo/env/seq/mod/key is applied first, and a test covers each.
8. **The tests assert exact words and states throughout.**

⚠️ Cannot verify from the diff: how the chip looks and sits on a narrow PRESET strip (the report flags it; it is for the hand check).

### Strengths
- The once-per-frame logic is right and subtle. A retried open that already told the listeners this frame suppresses the second `_changed()`. `open_all` seeds silently, so the launch says nothing.
- A broken `said` hook is guarded into a note, and the test proves it.
- The test with the real `MidiDevice` over the fake bus is strong end-to-end evidence that nothing fires twice.
- `apply` says an added device, and the test confirms a removed role is forgotten.
- The helper functions are pure and testable on their own. `want_words` has a real (not skipped) doctest example.

### Issues
#### Critical (must fix)
None.

#### Important (should fix)
1. **`wants` pays for `registry.lines()` on every call.** devices.py, `_rig`: `status = {role: st for role, _kind, st, _n, _last in registry.lines()}`.
   - **What is wrong:** `lines()` calls `len(d.sources)` and `d.last` for every device. For a connected `MidiDevice`, `sources` rebuilds the APC40's whole layout as fresh `Port` objects (devices.py, `MidiDevice.sources`), and that happens on every call.
   - **Measured:** 0.23 ms of the 0.29 ms per `wants` call.
   - **Why it matters:**
     - The chip calls `wants` independently on the GRAPH head and the PRESET strip, and the SYSTEM page calls it again. That is up to about 0.6–0.9 ms per control-window frame, about 80% of it Port allocations nobody reads.
     - The brief asked for exactly the opposite ("keep it cheap … no allocation storm").
   - **Fix:** read each device's status directly in `_rig`, behind the same try/except `lines()` uses (`for d in registry: st = d.status`). Optionally compute the wants once per frame and share the result between the head and the strip.

#### Minor
1. **The new role-resolution steps have no register row.** The steps between the MIDI rule and `SCHEME_ROLE` (`primaries()`, then the first listed publisher, off ones included) are a choice the task took itself, but no row in decisions/t4.md (47a–47e) covers them. Add a short row, or fold it into 47b or 47c.
2. **The retry path can still fire the listeners more than once in a frame.** In `poll`, a retry still calls `_changed()` inside the per-device loop. If two devices both reopen through retry in one frame, the listeners fire twice. This behaviour predates T4 (the listeners must re-point before that device polls), and the new end-of-frame call is correctly suppressed. It only falls short of the letter of "once per frame". Either note it in the decisions file or leave it.
3. **graphview.py has two edits beyond the brief's "no other line".** One is the module docstring line, which now reads awkwardly ("nothing of `devices.py` is imported but its `SCHEME_ROLE`"). The other replaces the 3-line comment where the table used to be with a 2-line pointer. Both are declared and far from plan 37's regions, so the merge risk is small. Consider leaving the old comment block's position untouched, so the `main` merge stays mechanical.
4. **`cable_words` now says the row's words when a cable has no owner port.** It used to show the raw address. This is a small change in behaviour on the canvas, declared in the report. With a port, nothing changes.
5. **One test check is weak.** `test_the_chip_draws_on_the_graph_head_the_preset_strip_and_system` ends with `assert callable(ui_graph._wants_chip)`, which asserts nothing useful. The checks before it carry the test.
6. **One test re-derives part of its answer from the code under test.** `test_a_midi_device_coming_back…` computes the expected count from `r.table.desk()`, not from a fixed number. It is acceptable because `wants` uses a different path (`_rows_of`), but a literal count would be firmer.

### Assessment
**Task quality:** Needs fixes. The behaviour, the boundaries and the tests are sound, and every doubt in the dispatch settles in the PR's favour except the per-frame cost: the chip pays about 0.23 ms per call to rebuild device Port layouts through `registry.lines()`, which is a small fix in `_rig`.
