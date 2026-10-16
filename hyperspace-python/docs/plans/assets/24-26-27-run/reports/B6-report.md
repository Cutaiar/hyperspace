# B6 report — several gamepads at once

**Status:** DONE_WITH_CONCERNS · base 9744cac · branch `plan-27-b6-pads` · PR https://github.com/Cutaiar/hyperspace/pull/200

## Commits
- b19cb56 The device qualifier is general: any scheme takes @<role>; Router.pad keeps two pads apart
- 61a5ad1 Several gamepads at once: a joystick per pad device, the registry claims (scheme, role), one USB reader, the camera job the primary's
- 7f4d51c Docs for plan 27 B6: the B6 section, register rows 210-213 (row 141 changed), check 219 (174 changed), ENGINEERING §5/§7, TESTING-GUIDE F6
- 3857cb5 config.py's docstring: a gamepad entry's joystick key and several pads

## What was built
1. **General qualifier** (`routing.py`): `base_scheme` strips `@role` from any scheme; `qualified()`; `Binding.head` (the Router key, `axis@p2`); `Binding.device` for any scheme; `describe` adds "on <role>"; `Bindings.primaries` + `role_of` for non-MIDI rows (MIDI path unchanged); `Router.follow_devices` reads `primaries`; `Router.pad(…, role=)` feeds `axis@<role>`, publishes there, fires only rows whose `device == role`, keeps holds per pad; `source_feel` gives every pad the one feel.
2. **Registry** (`devices.py`): `Base.repeatable` (True on `PadDevice`), `Base.qualifier`, `Base.qualify`; `primaries_of` (first enabled entry of each repeatable kind, else first listed); `make(…, primaries)` qualifies non-primary repeatable entries (incl. off ones), refuses a role listed twice, keeps the scheme refusal for non-repeatable kinds (hands); `DeviceRegistry.primaries`, told to the table in `_tell_table`; `apply` reopens a kept device whose qualifier changed; `Context.pads`.
3. **Pad device**: `joystick` property, `open` attaches the `Pad` to the shared `gamepad.Claims`; qualified `sources`; `last` = `glfw <jid>` / `usb: <name>` / `waiting for joystick n` / the usb note; `learn`/`act` pass the role; camera job primary-only.
4. **gamepad.py**: `Claims` (taken, pinned, usb, release), `JOYSTICKS`, `Pad.attach`, `Pad._find` (keep own → release when gone → next free / pinned), `Pad.close` releases claims; `learn_from(…, role=)`; `publish(router, scheme)`.
5. **learn.py**: `accepts("pad")` on the base scheme; hat step sign and the stick refusal on the bare/base source.
6. **config.py**: `JOYSTICKS = 16`; a gamepad entry's `joystick` checked (int 0–15, else note + dropped); docstring.
7. **ui_routing.py**: `source_schemes` / `_sources` key on `Binding.head`.
8. **Docs** (this WP's own): plan 27 B6 section + two-pad block + key table + not-verified + rough edges; DECISION-REGISTER rows 210–213 + answer sheet + row 141 "Changed in B6" + intro; hand check 219 at the end of group W + 174 changed + order list; plans README (1–219, plan 27 entry); ENGINEERING §5 (keys, two-pads/USB paragraph, SYSTEM row) and §7; DECISIONS (new "Several gamepads" row, row-141 sentence); ARCHITECTURE §3.3 table + module table (HTML has no such sentence: untouched); TESTING-GUIDE F6 + summary + L73.

## Tests (written first)
New: test_routing (3), test_gamepad (5), test_pad_learn (3), test_devices (3 new + 1 rewritten), test_device_inputs (1 new; 1 assertion changed: `hand@x:1`'s scheme is `hand` now).

## Gates
- `uv run pytest -q` → `2211 passed, 2 skipped in 151.08s`
- `uv run ruff check .` → `All checks passed!`
- `uv run pytest tests/test_golden_frames.py -q` → `7 passed in 17.94s`
- `HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/b8e1c57e/tmp/b6/home uv run hyperspace -ApplePersistenceIgnoreState YES` (two gamepad entries at defaults, no MIDI, no hands) → exit 0, `stall.log` 0 bytes. Device lines (`ui.device_lines` over the same config, GLFW initialised, 3 polls):
  ```
  pad  ·  gamepad  ·  lost  ·  22 sources
  p2  ·  gamepad  ·  lost  ·  22 sources  ·  usb: pad has the wired pad
  ```
- `git diff --stat 9744cac -- hyperspace/library/` empty; no goldens moved; no boundary test changed; no MIDI test changed; no fixtures.

## Self-review / concerns
- **Ruling 3 as written has a default-config trap**: with `usb = true` on both entries (the default), the first pad owns the USB reader even while it reads the Bluetooth pad over GLFW, so the wired pad on the second entry is never read. Built as written; documented (row 211, check 219, the block to paste puts `usb = false` on the Bluetooth pad) and the line itself says `usb: pad has the wired pad`. Alternative (USB to the first usb pad without a GLFW joystick) is a few lines if the owner prefers.
- "Learn pad" in the param menu shows only while the *first open* pad is connected (`rig.adapter("gamepad")`); with only the second pad plugged in it is missing (rough edge, no page change made).
- A row qualified with the primary's own role (`pad@pad:A`) is never fired; swapping the pad entries swaps which pad the bare rows mean.
- No real second controller was available: everything is proven with fake GLFW joysticks / scripted pads (check 219 pending).

## Files changed
hyperspace-python/hyperspace/{routing.py,devices.py,gamepad.py,learn.py,config.py,ui_routing.py}; tests/{test_routing.py,test_devices.py,test_gamepad.py,test_pad_learn.py,test_device_inputs.py}; docs/{ARCHITECTURE.md,DECISION-REGISTER.md,DECISIONS.md,ENGINEERING.md,TESTING-GUIDE.md,plans/11-hand-checks.md,plans/27-device-registry.md,plans/README.md}.

Decisions file: /Users/dallman/.claude/jobs/b8e1c57e/tmp/sdd/decisions/B6.md

---

## Fix round 1 (review of head 3857cb5) — head 9c37749

Commits: 8d74d77 (code + tests), 9c37749 (docs).

- **IMPORTANT 1, USB reader lent:** `gamepad.Claims` gains `order`, `reader`, `lend()` (sticky: holder kept while attached, usb on, no GLFW joystick; else the first such pad in order); `Pad.attach` appends to `order` and no longer touches `usb`; `Pad.poll` hands the reader back as soon as the pad has a GLFW joystick; `_usb_state` borrows `claims.reader` (one `UsbPad` ever); `usb_note` is a property (`usb: lent to p2`, "" otherwise); `Pad.close` removes from `order` and closes the shared reader only when no remaining pad has usb on (no-claims path unchanged). Tests: `test_one_usb_reader_across_two_pads` rewritten as specified (glfw 0 + both usb; lent to p2; sticky after joystick 0 drops; one takes the same reader after p2 closes; closed exactly once), plus `test_a_pad_that_finds_a_joystick_hands_the_reader_back`; `test_devices.py::test_two_pads_with_usb_on_the_reader_is_lent_to_the_one_without_a_joystick` (SYSTEM lines `glfw 0  ·  usb: lent to p2` / `usb: Afterglow`). Docs: every `usb = false` / "first usb = true entry owns it" / "has the wired pad" text replaced (ENGINEERING §5 + key table, plan 27 block/key table/At the machine/rough edges, register answer sheet + row 211 with the sticky rule, DECISIONS, check 219 setup/Pass/Fail, TESTING-GUIDE F6, config.py, PadDevice docstring, PR body, decisions file).
- **IMPORTANT 2, Learn p2:** `PadDevice.wants_for(role, qualifier)` / `wants` property → ("pad",) primary, ("pad", role) second; `OffDevice.wants` follows it; `Learn.accepts` for a role want also matches `Binding(source).device == want`. Tests: `reg.wants() == ("pad", "p2")` (and ("pad",) after p2 becomes primary); `test_pad_learn.py::test_learn_p2_completes_only_from_the_second_pad`. Row 212 / plan 27 rough-edge text replaced.
- **MINOR 1:** `test_routing.py::test_each_pad_times_its_own_holds` (MENU hold rows on both pads; staggered presses; only the held-long-enough target fires, the other's timer is not reset).
- **MINOR 2:** `Router.pad` (role "") also fires rows qualified with `table.primaries["pad"]`; `Router._resolve_lane` reads `axis@<primary>` as `axis` (lane cache cleared when primaries change). Test `test_a_row_qualified_with_the_primary_pads_own_role_is_its`. Rough edge dropped from row 210 and plan 27.
- **MINOR 3:** `_find`'s keep-own branch skips a joystick pinned to another pad (`test_keeping_a_joystick_respects_another_pads_pin`); `config._device` drops a second gamepad entry pinned to an already-pinned index (a problem note), tested in `test_the_joystick_key_is_checked`.
- **MINOR 4:** "arm it from ROUTING instead" removed.
- **MINOR 5:** `bright` → `rate` in `test_two_pads_drive_their_own_routes`.

Gates (from hyperspace-python):
- `uv run pytest -q` → `2217 passed, 2 skipped in 150.88s`
- `uv run ruff check .` → `All checks passed!`
- `uv run pytest tests/test_golden_frames.py -q` → `7 passed in 17.28s`
- Smoke `HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=…/tmp/b6/home uv run hyperspace -ApplePersistenceIgnoreState YES` (two gamepad entries, defaults) → exit 0, stall.log 0 bytes; lines:
  ```
  pad  ·  gamepad  ·  lost  ·  22 sources
  p2  ·  gamepad  ·  lost  ·  22 sources  ·  usb: lent to pad
  ```
  (no GLFW joystick on the build Mac, so the reader is lent to `pad`, the first listed.)

Remaining concerns: no real second controller tested (check 219). "Learn p2" is offered only on modulatable params, like every "Learn <role>" item.
