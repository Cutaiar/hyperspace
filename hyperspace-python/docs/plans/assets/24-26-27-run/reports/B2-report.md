# B2 report — the existing inputs on the registry (plan 27)

**Status:** DONE_WITH_CONCERNS
**PR:** https://github.com/Cutaiar/hyperspace/pull/181 (`plan-27-b2-inputs` → `plan-24-26-27-integration`)
**Base:** `fbf4cf1` (Merge plan 24 C5, PR #178), confirmed with `git log --oneline -1` after `git reset --hard FETCH_HEAD`.
**Decisions file:** `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/B2.md`

## Commits
- `8315371` Plan 27 B2: the APC40, the pad and the hands on the registry
- `2f8c77f` Plan 27 B2: tests — two desks, two roles, a generic desk on Learn, a lost desk
- `58f4946` Plan 27 B2: one knob per param per desk; a profile names its own controls

## What was built
- **Several MIDI ports, each with its own profile**: `MidiDevice` per `[[devices]]` MIDI entry,
  `MidiIO(…, role=)`, profile `apc40` or the new `generic` (`hyperspace/generic.py`: plain
  CC/note/pitch, `FEEDBACK = False`, `PORT_MATCH = None` so a `port` is required). The entry's
  profile wins; `bindings.json`'s `"profile"` no longer overrides it.
- **Qualifier**: an unqualified MIDI row is the first MIDI role listed; others are
  `cc@<role>:<ch>:<n>` / `note@…` / `pitch@<role>:<ch>`. `Binding.scheme` (bare), `.device`,
  `.bare`, `midi_source(…, role)`, `overlaps` (same device), `describe`; table `midi_roles`
  (set by the registry before any desk opens), `serves`, `role_of`, `dispatch(…, role)`,
  `active(role)`, `is_invariant` per device.
- **Per-role latch**: `Bindings.layer` = first role's (`desk.shift`); `layers` / `layer_of` /
  `set_layer(…, role)` / `toggle_layer(role)`; `drop_layer` drops every desk; Learn's `blocked`
  per desk. `MidiDevice.layers`.
- **Pad device**: `Pad.open/status/publish`, `gamepad.publish` (axes' names/labels/rests; Router's
  `_publish_axes` removed), camera job moved from `app.frame` to `gamepad.steer`, run in
  `PadDevice.act` after `Router.pad`.
- **Hands**: `HandsDevice` moved to `hands/device.py`, schemes/feeds `("hand","hands")`, ports from
  `Layout` + pair lanes; `devices.kinds()` / `kind_class()` / module `__getattr__` for `KINDS`
  and `HandsDevice`.
- **Schemes from the registry**: `LANE_SCHEMES`, `SOURCE_ORDER`, `learn.WANTS` removed;
  `routing.is_continuous` (not in `ROW_SCHEMES`); `Router.use(registry)` / `schemes()` /
  `follow_devices()`; `Bindings.row_schemes` from the registry; `Learn.wants()` from
  `DeviceRegistry.wants()` (`Device.wants` on each device); `ui_routing.source_schemes`;
  "Learn <role>" menu items for new devices (`ui.learn_wants`).
- One knob per param per desk (`Bindings.bind`'s `same_role` per role).
- `hotreload.MODULES` gains `generic` and `hands.device`; config docstring documents several
  desks; `ui_desk.py` docstring notes it is APC40-only (plan 29 replaces it).

## How it was tested
- New `tests/test_device_inputs.py` (10 tests) with a fake MIDI bus (mido's port lookup patched,
  ports plugged by name): qualifier; first role's unqualified rows; two desks with profiles; a
  generic desk on Learn desk with no code; per-role latch (D5, D12, D4); a missing desk `lost`,
  rows waiting, coming up with feedback after plugging; pad and hands on the registry; schemes /
  wants / row schemes; pre-run `bindings.json` + every factory preset load with no note / no dirt
  with two desks listed.
- Commands and last lines:
  ```
  uv run pytest -q          → 1988 passed, 2 skipped in 131.43s
  uv run ruff check .       → All checks passed!
  HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<worktree>/.sdd/b2-smoke uv run hyperspace -ApplePersistenceIgnoreState YES
                            → exit=0, stderr only the ApplePersistence line
  ```
  One full run before the last had `tests/test_watchdog.py::test_a_stall_that_holds_the_gil_is_caught_by_the_c_backstop`
  fail (timing under load); it passed alone and the full rerun was clean.
- Smoke SYSTEM lines (headless `ui.device_lines` over the same scratch home):
  `pad · gamepad · lost · 21 sources`, `apc40 · midi · lost · 137 sources`,
  `launch · midi · lost · 0 sources`, `leap · hands · connected · 42 sources · connected`.

## Test changes (named in the PR body)
Allowed boundary: `test_hands_boundary` list → `["device.py","panel.py"]`; `test_app_boundary`
`ORDER`, relative-writers order, `_host` pad ctx, `W_PLANES` from gamepad; `test_devices`
hands scheme `hands`, swap target module, ports incl. pair. Spec tests whose spec moved:
`test_learn::test_accepts_by_want` (`lrn.wants()`), `test_presets` (`is_continuous`),
`test_ui_lfo` (lane, lfo first), `test_motion` / `test_pad_learn` (`gp.publish`).
`test_routing_boundary` and `test_desk_trust` untouched.

## Files changed
`hyperspace/{routing,midi,devices,gamepad,learn,app,ui,ui_routing,ui_desk,preset,config,hotreload}.py`,
new `hyperspace/generic.py`, `hyperspace/hands/device.py`, `tests/test_device_inputs.py`; tests
listed above. `hyperspace/library/` untouched (`git diff --stat` empty).

## Self-review findings (fixed)
- Learning on a second desk dropped the param's APC40 knob (one knob per param across desks) →
  made per desk (`58f4946`), tested.
- Learn named qualified rows through the profile with the qualified string → uses `bare`.

## Concerns
1. `test_the_panel_is_the_only_piece_that_knows_the_host` compares an unsorted `Path.glob`
   list; it is `["device.py","panel.py"]` on APFS (the allowed value) but a filesystem listing
   `panel.py` first would fail it. Left as the prompt allows; the orchestrator may want
   `sorted(...)` (a further conscious change).
2. Five non-boundary spec tests changed because their spec moved (listed above) — the prompt's
   "exact test changes allowed" names only boundary tests; these are named in the PR body.
3. "Unqualified = first MIDI role listed" means a rig listing a generic desk before the APC40
   gives it every APC40 factory row and SHIFT. Documented as a rough edge.
4. A second APC40-profile desk has no SHIFT latch of its own in this plan ("or none").
5. The ROUTING source combo order changed (LFOs before hands/pad) per "lane and lfo first".
6. B3/B4 hand-offs in the decisions file §4 (row schemes for hits, a role want completed by the
   device's own `learn`); docs (`ARCHITECTURE.md`, `DECISIONS.md`) mentioning `LANE_SCHEMES` /
   `learn.WANTS` / the camera job's place are stale for B5.
7. Commit trailers use `Claude Opus 5.5` per the session's system attribution, not the brief's
   `Claude Fable 5.1`.

## Fix report — review round 1

**Commit:** `f0a81e9` Merge plan-24-26-27-integration (A1, C2); review of PR #181, round 1. The
merge and the fixes are in one commit: they were staged together. Pushed; the PR body is updated.

**Merge.** Merged `origin/plan-24-26-27-integration` at `6af4c65`. The one text conflict was
`hotreload.MODULES`; I kept A1's `graph` and B2's `generic` and `hands.device`. `MidiIO.redraw`
merged on its own: C2's `switch` block sits beside `active = self._active()`, and its loop runs
over this desk's own rows.

**What changed.**
1. *(Important)* Each MIDI role now has its own layer serial. `Bindings.set_layer` for a
   non-first role bumps `layer_serials[role]`, not `layer_serial`. The new
   `Bindings.layer_serial_of(role)` reads it back. `MidiIO._serials` reads its own role's serial.
   So C2's `redraw(switch=True)` runs only on the desk whose latch flipped.
2. `tests/test_hands_boundary.py` now uses `sorted(PKG.glob("*.py"))`. This is authorised and
   named in the PR body.
3. Ownership of unqualified rows follows the ruling. `DeviceRegistry.midi_roles()` puts first
   the first MIDI role whose entry profile equals the table's profile (default `apc40`), else
   the first listed. Updated with it: the config and routing comments, the register-row draft
   and W.8.
4. `MidiIO.control_name` falls back to `b.describe()` for a row this desk does not serve.
5. `test_the_latch_is_per_role` dropped the empty `f0 is not None`. It now asserts that each
   release let its own row go (`lines` and `faces` both False).
6. Fixed the `OffDevice` docstring: no adapter module is imported, only the device class is
   looked up (`hands.device` for the hands).
7. Decisions file, rough edges only, no code:
   - `cc@apc40:…` is not the same control as its unqualified twin to `overlaps` / `is_invariant`.
   - The open-ended `is_continuous` keeps a typo scheme as a dormant row, and the
     `test_presets` check is weaker for it.
   - The pad's feel is unchanged on purpose: still `desk.pad.*` through `table.pad_feel` and
     `router.felt`.
   - A second apc40-profile desk gets its power-up and rings but no SHIFT.

**New tests** (`tests/test_device_inputs.py`):
- `test_shift_on_the_apc40_leaves_the_second_desks_caught_rows_caught`: SHIFT on the APC40
  causes no `redraw` on the generic desk, and its caught row stays caught. Its own latch flip
  causes exactly one `redraw(load=False, switch=True)`. Before the fix the APC40's SHIFT bumped
  the shared serial, so this redraw spy would have fired.
- `test_the_desk_whose_profile_wrote_the_table_owns_the_unqualified_rows`: with the generic box
  listed first, the APC40 still owns the factory rows and SHIFT, and the box's note 98 is not
  SHIFT. A rig whose only desk is generic still owns them.

**Commands and output:**
```
uv run pytest -q tests/test_device_inputs.py tests/test_devices.py tests/test_desk_faders.py \
  tests/test_desk_trust.py tests/test_midi.py tests/test_hands_boundary.py tests/test_routing.py
                                   → 214 passed in 16.40s
uv run pytest -q                   → 2014 passed, 2 skipped in 138.42s (0:02:18)
uv run pytest tests/test_golden_frames.py -q → 6 passed in 11.93s
uv run ruff check .                → All checks passed!
```
Concerns 1 and 3 above are resolved by this round.
