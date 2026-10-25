# C2 report — the faders freed

**Status:** DONE_WITH_CONCERNS (concerns below)
**PR:** https://github.com/Cutaiar/hyperspace/pull/180 (into `plan-24-26-27-integration`)
**Branch / base:** `plan-24-c2-faders`, cut from `23f2569` (C1, C4, C6 and A0 merged).

## Commits
- `282b9e1` Plan 24 C2: lines and points opacity (view.lines_alpha, view.points_alpha), at 1 = today's picture
- `b163661` Plan 24 C2: S1-S8 are preset-layer targets; band post/dyn/trim on the SHIFT faders
- `a31b91f` Plan 24 C2: tests for the freed faders; invariant-fader examples now use MASTER

## What I built
- `apc40.DEFAULT_MAP`: the eight track-fader rows (`band.{i}.post` on S1–S6, `master.dyn` / `master.trim` on S7–S8) are now on the global (SHIFT) layer. There are no preset-layer fader rows. `TRACK_FADERS` and `SHIFT_FADERS` are new constants. MASTER and the crossfader are still invariant. The docstring says D6 no longer lists the track faders.
- `routing.FADER_SHIFT_ROWS` plus a branch in `remap_factory`: an older `bindings.json` gets its exact invariant fader rows moved to the global layer. Each move is noted, the file is backed up as `bindings.json.bak-v3` and written back once, and the next load says nothing. A fader row the owner changed stays invariant. `APC_REMAP_PLAN` names plan 24 for those rows.
- `midi.MidiIO.redraw(switch=)`, called from `_follow_table`: on a layer switch, every layered fader row starts again from the fader's physical position. It is caught only if its param is already within tolerance of that position, so one fader serving two params never jumps either of them (D7).
- `preset.track_fader`, `_is_track_fader`, and `knob_desk(targets, faders=())`. The docstrings of `fresh_desk` and `file_desk` now say they bind no fader. No factory preset's desk changes.
- `ViewState.lines_alpha` and `points_alpha` (default 1), registered as `view.points_alpha` and `view.lines_alpha` (continuous 0–1, view group, performance, modulatable). Each adds one factor to an existing alpha line in `render.draw_scene`. The VIEW page gets a pair of sliders for them.
- `bindings.default.json` is regenerated.
- New tests: `tests/test_desk_faders.py` (11 tests) and a force-added fixture, `tests/fixtures/desk-faders/faders.json`.
- About 20 existing tests in 11 files used S1 or S3 as "an invariant fader". They now use SM (MASTER) or the crossfader. The schema-1 migration count went from 77 to 85. Each change is listed in the PR body with decision 17.

## Gates (last lines)
```
uv run pytest -q              → 1955 passed, 2 skipped in 127.91s
uv run ruff check .           → All checks passed!
tools/golden_frames.py (diff) → all 427 frames match their goldens (Apple M3 Max, 4.1 Metal - 90.5)
pytest tests/test_golden_frames.py → 6 passed
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/tmp/c2-smoke uv run hyperspace -ApplePersistenceIgnoreState YES → exit 0
git diff --stat -- hyperspace/library/ → empty
```

## Self-review and concerns
1. **Smoke run.** The app cannot take the tests' fake MIDI ports. The windowed run used a scratch home with `[midi] enabled = false` and the fixture in its `presets/` folder. It did not start on FADERS: that would need a project that names FADERS as its startup preset. The required check (the fixture loaded, then SHIFT latched and released, on fake ports) is covered by `tests/test_desk_faders.py`.
2. **A new pickup-on-switch rule (D7).** It is necessary: without it, a fader moved on one layer jumps the other layer's param, and the test fails if the rule is removed. It touches `MidiIO.redraw`, which B2 will carry into the device.
3. **Learn behaviour.** A fader on the preset layer is now a learn candidate, where an invariant fader used to just do its job during a learn. That follows from decision 17. Expect C3 to see S1–S8 as "dark" on every factory preset.
4. **Overlap with A2.** The two `draw_scene` edits add a factor to existing lines (`alpha … * s.lines_alpha`, `pa = … * s.points_alpha`). The factor is applied after the `np.clip` floor so that 0 really is transparent. A2 needs to keep that order.
5. **Stale docs (left for C7).** `DECISIONS.md` D6 and D7, `ENGINEERING.md` §8, and the register row-44 text.

Decisions, hand checks (U.5–U.7, renumber as needed) and as-built notes: `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/C2.md`.

## Fix report: review round 1 (`b96e26e`, pushed; PR body updated)
1. **Stale `last_hw` (midi.py).** In the switch block of `redraw`, `b.last_hw = pos` now runs unconditionally: it is None when no position is known, and then only an on-value catch counts. `_enter` (power-up) now also clears `last_hw` on every cc/pitch row, so invariant faders no longer keep a stale position. The reviewer's probe is now `test_a_power_up_forgets_where_a_fader_was_on_every_layer`. It covers S1 under SHIFT and MASTER. It failed before the fix (band 0.5 → 0.093) and passes after.
2. **`decisions/C2.md` opacity rough edge.** Corrected: a preset that lacks the opacities returns them to 1 on load (the group default).
3. **Learn assertions.** Added `test_a_track_fader_is_learnable_on_the_preset_layer`. It checks that `ui_desk.mappable(S1)` is None on the preset layer, that a desk learn on CC 7 lands `cc:0:7` abs with layer preset, pickup on, and `(feedback, ring) == (None, 0)`, and that S1 is not mappable under SHIFT. To make the learned row match the map's fader row, `apc40.feedback_for` now returns `{"feedback": None, "ring": 0}` for CC 7, MASTER and the crossfader. Before this, a learned fader had feedback None and a meaningless `ring: 2`.
4. **test_ui_routing.** The refusal echo is now "MASTER fader is invariant …". (It was at lines 413/419 on this branch.)
5. **knob_desk.** Kept the filter and added a one-line comment saying it guards a future `file_desk`.

Covering tests:
```
uv run pytest -q tests/test_desk_faders.py tests/test_desk_trust.py tests/test_midi.py tests/test_ui_routing.py tests/test_learn.py
146 passed in 6.94s
uv run pytest -q
1957 passed, 2 skipped in 135.20s (0:02:15)
uv run ruff check .
All checks passed!
git diff --stat -- hyperspace/library/   → empty
```
