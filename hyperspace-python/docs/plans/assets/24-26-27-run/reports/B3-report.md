# B3 report — plan 27, sinks

**Status:** DONE_WITH_CONCERNS (concerns at the end)
**Base:** `plan-24-26-27-integration` at `c831770` (B2's merge, PR #181), verified with `git log --oneline -3`.
**Branch:** `plan-27-b3-sinks`. **PR:** https://github.com/Cutaiar/hyperspace/pull/185 (into `plan-24-26-27-integration`, not merged).
**Commits:**
- `768f437` Plan 27 B3: the sink row — a param or a lane to <role>:<channel>, the session's; Learn sink; ROUTING's sinks
- `1ab41f9` Plan 27 B3: the bridge and the hands' DAW out as sinks; [bridge] send and [hands] out translated

**Decisions file:** `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/B3.md` (6 register-row drafts, hand checks W.13–W.17, as-built notes, deviations).

## What was built
- **Sink row** (`routing.py`): `{"source": "param:<id>" | "lane:<i>" | "lane:*", "target": "<role>:<channel>", "op": "send"}` (`SINK_OP`). It's a session row in `bindings.json` and never a performer, so the referee is unchanged and it never prompts. It never goes into a preset. Pieces: `Binding.is_sink` / `.sink`, `sink_refusal`, `sink_values` (effective values, read after apply), `sink_rows_from_send`, `Bindings.sinks(role)`, and a sink branch in `_check`.
- **devices.py**:
  - `Device.sinks` / `Base.sinks` and `Context.devices` (the registry sets it to itself).
  - `BridgeDevice` now has two halves: `poll` reconnects, `feed` does receive + publish ext labels and rests, `send` sends the sink rows.
  - A separate "sinks" block holds `MidiOutDevice` (`kind = "midi-out"`). It owns an `OutPort`, carries the `HandsIO` named by `carries` (resync in `poll`, `carry` in `send`) and also sends its own sink rows.
  - `kinds()` gains `"midi-out"`.
  - `DeviceRegistry` gains `sink_ports`, `_seed_sinks` (run in the constructor and in `apply`), and an `n sinks` prefix on the line of any device that has sinks.
- **bridge.py**: `Sender` (the outbound gate, shared by the bridge and midi-out), plus `_open_out`, `_close_port` and `OutPort`, all moved here from hands/core.py. `Bridge` gains `reconnect`, `publish`, `send_values` and `labels`; `step` / `transmit` are kept for a standalone `Bridge`.
- **hands/core.py**: opens no port any more. `outbox`, `carry(send, name, error)`, `resync()`, `daw` / `daw_error`; `out_name` falls back to the carrier's port name. An injected `out=` still works as before. The `RECONNECT_*` constants and the reconnect fields are removed. It still imports nothing from the host.
- **config.py**: `MIDI_OUT` defaults, `DAW_ROLE = "hands-daw"`, and `_daw`, which turns `[hands] out` into the midi-out entry in both the old-table form and the list form. One note when the file wrote `out`.
- **learn.py**: `Learn.sinks`, `Learn.learn_sink` (lands immediately, writes bindings.json, no undo step, no question), `sinks_of`.
- **ui.py**: "Learn sink ▸" submenu (`sink_items`); the param's sink rows appear in the menu's bound lines.
- **ui_routing.py**: `N_EXT` removed; a "sinks" section; `found` counts sink rows.
- **Other files**: `app.py` sends a sink error to the toast; `hands/panel.py` shows `daw_error`; `tools/hands_probe.py` carries its own DAW out through an `OutPort`.

## Tests
- New: `tests/test_sinks.py` (14 tests) and `tests/test_ui_routing.py::test_the_routing_page_lists_the_sink_rows_with_the_others`.
- Rewritten with the same meaning: three DAW-port tests in `test_hands.py` (plus one added), three in `test_hands_leap.py`.
- Assertions consciously changed (also listed in the PR body):
  - `test_app_boundary.py`: `ORDER` and the `bridge.step` → `bridge.receive` line.
  - `test_devices.py`: the kinds table and the bridge shim test.
  - `test_config.py`: two tests now expect the derived `hands-daw` entry.
  - `test_ui_lfo.py`: the ext count, now that `N_EXT` is gone.
- Untouched: `test_bridge.py` (including `test_core_does_not_import_the_bridge`), `test_routing_boundary.py`, `test_hands_boundary.py`, `test_hotreload.py`. `hyperspace/library/` is untouched.

```
uv run pytest -q tests/     2030 passed, 2 skipped in 134.02s
uv run ruff check .         All checks passed!
HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<worktree>/.sdd/b3-smoke uv run hyperspace -ApplePersistenceIgnoreState YES   exit 0 (two runs)
```
In the smoke runs, the first run printed one note, "bindings: [bridge] send is now sink rows in bindings.json (lane:* → bridge:0, param:view.bright → bridge:6) …", and wrote the two rows. The second run printed no note. The device lines, printed headless over the same home:
```
pad  ·  gamepad  ·  lost  ·  21 sources
apc40  ·  midi  ·  lost  ·  137 sources
leap  ·  hands  ·  lost  ·  42 sources  ·  connecting
hands-daw  ·  midi-out  ·  lost  ·  0 sources  ·  0 sinks  ·  out 'B3-absent-daw': no such port  ·  leap's DAW out
bridge  ·  bridge  ·  lost  ·  16 sources  ·  2 sinks
```

## Concerns
1. **Merge overlap with B4.** `kinds()`, `Context` and `test_the_kinds_table_…` are the same lines B4 edits. Expect a small conflict.
2. **Seeding writes bindings.json once.** The first launch with an enabled bridge (or any entry with a `send` list) that has no sink rows writes `bindings.json`. If the owner deletes every row for a role, the default `lane:* → bridge:0` comes back at the next launch; disabling a row instead prevents that.
3. **Learn sink lands at once.** It does not arm and wait. That's a deliberate reading of "Learn arms a sink port", recorded in the decisions file.
4. **Commit trailer.** The commits carry the session's attribution trailer (`Claude Opus 5.5`), not the `Claude Fable 5.1` line the common brief quotes: the session's attribution reminder replaced it.
5. **Not verified on hardware.** No real DAW or MIDI monitor was used, and the menu and ROUTING section have not been seen drawn on a screen.

## Fix round 1 (review of PR #185) — commit `81fbced`

**What changed**
1. (Important) `devices.DeviceRegistry._seed_sinks` now marks the translation done in `bindings.json`, never by consuming the config key. It writes a top-level `"sinks_seeded": [<role>]` (`routing.Bindings.sinks_seeded`), read by `from_json` and written by `to_json` / `dumps_doc` only when non-empty, so files without it are unchanged. A role in the list is never seeded again. A file that already holds sink rows on a role counts as seeded: the mark is added and the file written. This also removes the mid-session reseed on a config re-read. The register-row draft's rough edge is updated.
2. `tests/test_app_boundary.py`: the stub bridge has a table with `sinks`, so `ORDER`'s sink slot is now `table.sinks`, `bridge.send_values` (the live path). The absent-device test filters `table.sinks`.
3. `test_a_raising_adapter_is_a_note_that_survives_the_frame` adds a raising sink (`send_values` → boom). The toast reads `bridge: RuntimeError: boom`, the bridge's line shows the error, and the frame still integrates and draws.
4. `Binding.describe` for a lane sink row: `lane 3 HIGH → bridge:3` (asserted in `test_sinks.py`).
5. Renamed `test_the_kinds_table_lists_todays_four_…` to `test_the_kinds_table_maps_each_kind_and_make_sorts_an_entry`.
6. `hands/core.py::_close_port`: comment on why it duplicates bridge.py's.
7. Hand check W.14 names the channel rule: an entry after `lane:*` lands at `len(BANDS)` = 6, so check the DAW's channel map once. It also adds the delete-and-relaunch check.
- Also: `routing.sink_values` returns early with no rows, and the sink devices read `analyzer.n` through `getattr`. The stub host's chain is a bare object.

**New test:** `tests/test_sinks.py::test_rows_deleted_on_routing_never_come_back_the_translation_is_marked`. It seeds, removes every row (writing the file each time), re-applies the list (a config save), reloads the table, re-runs the registry, and checks that no row comes back and no note is made. It also covers the pre-mark file with rows.

**Commands and output**
```
uv run pytest -q tests/test_sinks.py tests/test_devices.py tests/test_routing.py tests/test_app_boundary.py tests/test_bridge.py tests/test_hands.py tests/test_ui_routing.py
321 passed in 11.91s
uv run pytest -q tests/        2031 passed, 2 skipped in 157.57s
uv run ruff check .            All checks passed!
```
Pushed; the PR body has a "Review round 1" section. The integration branch is not merged in (B4 goes first, per the orchestrator).

## Fix round 2 — the merge of `plan-24-26-27-integration` (8e0a9fb: B4, A2, C3) — commit `cf30ee2`

Three files had textual conflicts:
- `devices.py`:
  - The module docstring merged cleanly: my device list and "Sinks" paragraph sit beside B4's text. I added a sink sentence to `Port`'s docstring, after B4's `kind = "cloud"` sentence.
  - The block after `BridgeDevice` conflicted. I kept both, in this order: my sinks block (`_lane_sinks`, `MidiOutDevice`, `_said`), then B4's point-cloud block (`PointCloud`, file format, `CloudDevice`).
  - `kinds()` conflicted. I kept all of `"midi-out"`, `"osc"` and `"cloud"`, in that order.
  - These merged cleanly and I kept B4's form unchanged: `Context` (only my `devices` field was added), `Base` / `OffDevice` (B4's `rows` / `publishes`), and `make` (B4's `publishes(role, entry)` loop).
  - Interplay checked:
    - `MidiOutDevice` publishes no schemes, feeds or rows, so it never collides with another device in `make`.
    - An `OffDevice` inherits `Base.sinks` = `()`. That is deliberate: an off sink offers no ports.
    - `lines()` adds the `n sinks` prefix; `clouds()` is unchanged.
- `learn.py`: the imports are the union — B4's `PERFORMANCE_GROUPS` and my `SINK_OP` / `parse_sink`.
- `tests/test_devices.py`: the `KINDS` set is the union, `{midi, gamepad, hands, bridge, midi-out, osc, cloud}`.
- `config.py` merged cleanly. I reworded the `kind =` docstring line to list all seven kinds. `_kind_defaults` keeps the `midi-out` branch; B4 had not touched it.

Gates on the merged tree:
```
uv run pytest -q tests/                      2114 passed, 2 skipped in 177.65s
uv run ruff check .                          All checks passed!
uv run pytest tests/test_golden_frames.py -q 6 passed in 12.80s
```
Pushed to `plan-27-b3-sinks` (PR #185).
