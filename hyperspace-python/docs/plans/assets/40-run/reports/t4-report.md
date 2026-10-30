# T4 report: what the preset wants and the rig lacks, and the arrival

**Status:** DONE_WITH_CONCERNS (minor: the PRESET strip on a narrow panel and the always-lit chip on the laptop have not been checked by a person).
**PR:** https://github.com/Cutaiar/hyperspace/pull/272 (plan-40-t4 into plan-40-build).
**Base:** 51106e1, confirmed with `git log --oneline -1` after the reset.
**Commits:**
- 20aec1a Plan 40 T4: devices.wants, routing.row_words, the registry's status-change event and the arrival line
- 6aea053 Plan 40 T4: the N devices missing chip on GRAPH and the PRESET strip, the SYSTEM lines, tests

## What I built

- **`devices.wants(table, registry, only=None)`** returns `[Want(role, state, scheme, rows)]`.
  - **Rows counted:** enabled performer routes, enabled preset-layer desk rows and modifier inputs.
  - **Role:** the row's `@role`, else the first MIDI role, else the scheme's primary, else the first listed publisher (off ones count), else `SCHEME_ROLE`.
  - **State:** connected / lost / off / missing.
  - **Rows:** in words, each once (APC40 glyphs where the profile is the APC40's). Built-in schemes are never named.
  - **Helpers:** `wants_for(table, registry, ids)` and `want_words(ws)` (for T2, with docstring examples and tests), `want_lines`, `missing_chip`, `wanted_lines`, `said_words`, `arrival`.
  - `SCHEME_ROLE` and `NO_DEVICE_SCHEMES` live in devices now.
- **`routing.row_words(row, names=None)`** is pure. `graphview.cable_words` delegates to it, with the port's name first.
- **The status-change event:**
  - In `DeviceRegistry.poll`, after every device has polled, the statuses are compared (`_statuses`, `_word`).
  - On a change, `_changed()` runs once per frame, and not again when a retried open already told the listeners that frame. `said(role, before, after)` runs once per change, guarded.
  - `apply` says an added device. `open_all` seeds the statuses silently.
  - `said` is a class-level no-op; app.py sets `rig.said = lambda …: library.say(devices.arrival(router.table, rig, …) or None)`.
- **Where it shows:**
  - GRAPH head: `ui_graph._wants_chip(panel)`, called in one line after the head's chips.
  - PRESET strip: the same function, after the ▶ arrow.
  - SYSTEM page: `ui.wanted_lines` in the warning colour under the device lines.

## Where the build differs from the spec, and why

- The footer words are composed in `devices.arrival` and called from app.py's hook, so the registry stays table-free in its hook signature (role, before, after), as dispatched.
- "controls" versus "rows" is decided by the want's scheme (cc/note/pitch), so a desk the rig lacks still says "controls".
- Errors (ruling 47a): an open device's error is ignored by the comparison (no flapping), and a failed-open device counts as `lost`. So the open that succeeds is said as a connection, and `wants` maps error to `lost`.

## Tests

- **New file:** `tests/test_device_wants.py`, 15 tests. It covers:
  - the words, and the moved table being identical;
  - hand rows on a rig without hands giving `Want("leap","missing","hand",(3 rows))`;
  - off / lost / connected states, and a role named by the registry;
  - `cc@launch` → `missing` for launch, not for the primary;
  - only the preset's rows counting, never built-in schemes;
  - `wants_for` / `want_words`;
  - the chip text and the SYSTEM lines (pure, plus headless frames of GRAPH, PRESETS and SYSTEM in `build_rig`);
  - the hook firing once per change with counts, and nothing over 100 steady frames;
  - two devices changing in one frame telling the listeners once;
  - errors not flapping, and a failed open that succeeds being said;
  - a broken hook becoming a note;
  - a real `MidiDevice` over the fake bus going lost → connected, firing the listeners once and the hook once ("apc40 connected — N controls live");
  - `apply` saying an added device and forgetting a removed one.
- **Gates:**
  ```
  uv run pytest -q                     4137 passed, 2 skipped in 33.70s   (base 4122 + 15)
  uv run ruff check <touched files>    All checks passed!
  uv run pytest -q --all -m golden     136 passed in 11.14s               (nothing moved or re-recorded)
  uv run pytest -q --all               1 failed, 4358 passed, 2 skipped in 56.37s
     failure: tests/test_media_publish.py::test_ndi_out_never_blocks (assert 0.146 < 0.05, timing under -n auto)
     serially (-n0): 1 passed in 6.08s
  ```
  The full-suite failure is a load-flaky timing test that is not one of the two named in common.md. It passes serially and has nothing to do with this change.

## Files changed (`git diff --stat 51106e1 HEAD`)

- app.py +3
- devices.py +352
- graphview.py 14 (the `SCHEME_ROLE` import, the moved table now a comment, `cable_words`, one docstring line)
- routing.py +67 (`row_words` only)
- ui.py +13
- ui_graph.py +22 (`_wants_chip` + one call)
- ui_presets.py +3
- tests/test_device_wants.py +392 (new)

No `midi.py`, `apc40.py`, `bindings.default.json` or `ui_desk*` changes. No preset, golden, schema or fixture changes.

## Self-review findings

- **graphview:** besides the dispatched lines, I changed one docstring line, because "nothing of devices.py is imported" would be false. I also replaced the table's 3-line comment with a 2-line pointer. Both are well away from plan 37's regions.
- **app.py** was touched (2 lines + a comment), because the registry's listeners are set there, as the dispatch allowed.
- **Behaviour change:** `cable_words` with no owner port now says the row's words instead of the raw address. With a port it is unchanged, and the existing test passes.
- **Factory desk rows:** with the APC40 unplugged, every preset with preset-layer desk rows shows "1 device missing" (apc40 lost, about 26 controls). That is correct, but it will be on the laptop constantly. The owner may want it; flag it at the hand check.
- **Cost:** `wants` runs every frame where the chip or the SYSTEM lines are drawn: one pass over the bindings plus `registry.lines()`, no allocation storm, and the glyphs are `lru_cache`d. There is no cache on (table, registry) serials, because the table has no serial covering route edits.

## Concerns

- The PRESET strip's chip sits before the flush-right chips; on a very narrow panel they may overlap. Not checked by a person.
- The `said` hook names the role, not the kind, in the footer ("apc40 connected …"), as the spec's words do.

## Rulings

47a–47e in `/Users/dallman/.claude/jobs/45478892/tmp/run/decisions/t4.md`, with hand-check drafts AK.n1 and AK.n2.

---

# Fix report (review of PR #272), commit 5189232

**Important #1, fixed:**
- `devices._rig` now reads each device's `status` directly, behind the same try/except `lines()` uses, instead of calling `registry.lines()`. That call rebuilt every connected desk's Port layout through `MidiDevice.sources`.
- `ui_graph.panel_wants(panel)` computes `devices.wants` once per frame. It is cached on the panel, keyed by (imgui frame count, registry id, table id). The GRAPH head chip, the PRESET strip chip and the SYSTEM lines all use it.
- **Timing:** on the fake bus with an APC40 connected (factory table, 26 counted rows), `wants` takes 0.060 ms per call, against 0.29 ms in the review. `registry.lines()` alone is 0.225 ms. The shared cache cuts it to one call per frame.
- **New tests:**
  - `test_wants_builds_no_ports`: `MidiDevice.sources` and `DeviceRegistry.lines` are patched to raise, and `wants` still answers `connected`.
  - `test_the_wants_are_asked_once_a_frame_for_every_place_that_shows_them`: one call per drawn frame, and a second ask in the same frame is the same object with no call.

**Minors:**
- (a) Register-row draft 47f added (the role-resolution steps).
- (b) The note on the retry path's per-device `_changed()` added to the decisions file.
- (c) graphview: the old 3-line comment block is back in place, with one pointer line appended; the docstring now reads "so of `devices.py` only its `SCHEME_ROLE` table is imported".
- (d) The empty `assert callable(...)` is dropped.
- (e) The APC40 coming-back test now expects the literal "apc40 connected — 26 controls live".

**Gates:**
```
uv run pytest -q                   4139 passed, 2 skipped in 37.67s
uv run ruff check <touched files>  All checks passed!
uv run pytest -q --all -m golden   136 passed in 10.83s
```
Pushed to plan-40-t4 (PR #272).
