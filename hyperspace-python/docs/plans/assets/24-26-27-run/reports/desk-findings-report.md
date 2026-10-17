# Desk findings — report (branch `fix-desk-findings`, base 0892fc8)

## The one root cause behind most of it

**On the owner's desk the APC40 was in Akai's Generic mode (0x40), not in the Alternate Ableton mode (0x42) the app sets.** Akai's protocol (rev 1, the inbound table's "Mode 0 Button Type" column, pp. 6–7 and 16–17) says that in Mode 0:
- ACTIVATOR, SOLO and RECORD ARM, and also CLIP/TRACK, DEVICE ON/OFF, ◀ ▶, PAN and SEND A–C, are **toggles kept inside the device**. Each press sends one message: a note-on when the button turns on, a note-off when it turns off.
- TRACK SELECTION and MASTER are **N/A**: they send no MIDI. Track selection banks the device knobs locally and lights its own LEDs.
- The device knobs and the eight device buttons (CLIP/TRACK … METRONOME) send **on the channel of the track the device selected**.
- The unit starts in Mode 0 whenever it powers up. In Mode 2 every button is momentary.

The app sends the 0x42 intro only when the port opens (`MidiIO._enter`). After that the device can fall back to Mode 0 without the app noticing:
- a power cycle, if the port survives it;
- **any other process that opens the APC40 and exits.** `MidiIO.close` sends `apc40.leave()`, which ends with the Generic intro. This includes a smoke run of the app or `tools/midi_probe.py`. My own smoke run here found the real "Akai APC40" and opened it, so an agent's smoke run during the owner's session is a concrete candidate. Which of these hit the owner's desk is not known.

I measured the host side with the fake port. `tests/test_desk_findings.py::Apc40` plays the device in either mode, from the protocol table. In Mode 0 a toggle flips its own state on a press, and a light the host sends sets that state. That is the only reading that gives the owner's asymmetry. With the owner's session file and a factory preset, before the fix:
- G8 (activator 4 → XY), starting on, over seven presses: `T, F, T, T, F, T, T`. One press goes off, two presses come back on, so from on: "doesn't toggle off; again: off; again: on". This is exactly the owner's description.
- G9: the LED stays at 1 for good, and the transfer steps only every other press.
- G10: the LED goes 1, 0, 1, 0, one change per press, which is "responds to toggle and untoggle". The reset fires every other press.

The same file in Mode 2 (momentary) is a clean one press per flip. `test_in_alternate_mode_the_activator_is_one_press_a_flip` passed before the fix and still passes.

The lead "switch pickup on a latch flip" is refuted. `redraw(switch=True)` only re-arms `cc`/`pitch` abs rows, never a note row.

## Per item

| Item | Factory map | Owner's file | What the code does | Why the owner saw it | Verdict |
|---|---|---|---|---|---|
| G8 two presses to off | `view.plane.*` toggle, preset layer (in every preset's desk) | no row (preset layer) | toggles on note-on, ignores note-off | Mode 0: one message per press, alternately on/off, resynced by the host's light → on,on,off | **FIXED** (re-entry) |
| G7 not on the diagram | `band.select` set i, invariant | same | the diagram lit the selected band and labelled the pads "SUB", "LOW"… | Mode 0: track select sends nothing and banks the device knobs locally, so the app never saw the presses. The pads were also labelled with bare band names | **FIXED** (re-entry); label now "band SUB" |
| G9 can't be untoggled | `band.{i}.fn` (enum, Transfer) on op toggle = next transfer | same | `b.lit` set on press, cleared on release only for triggers | a real host bug: an enum cycle row's echo never went out (Mode 2 too) | **FIXED** (echo clears at release); label "SUB Transfer: next (SQ)" |
| G10 responds | `band.{i}.reset` trigger | same (op "toggle" = the factory `_note` default, not stale) | press echo | Mode 0 latch → LED on/off per press | **BY DESIGN** (register "the rec-arm row (a band's reset)"); Mode 0 fixed |
| B10 Next Preset dead | `preset.next` on QUANT note:0:63, bank cycle | same | needs channel 0 | Mode 0: QUANT comes on the locally selected track's channel; there is no row for ch≠0 | **FIXED** (device buttons read on ch 0 + re-entry); label "Next bank preset". There is no APC row for `preset.list.next` by design (tip: "The desk's QUANT walks the bank instead") |
| G7·9 Overlay | `overlay.on` on MASTER select | same | `Output._set_overlay`: shut unless `[output] overlay` allows | MASTER sends nothing in Mode 0. Even in Mode 2, overlay is off unless config allows it | **BY DESIGN**, labelled "Overlay (if config allows)" |
| G6·9 Reset All | `scene.reset_all` | same | resets every band to the selected scene; a second press within 8 s undoes it | no visible change when the bands already match the scene; a double press undoes | **BY DESIGN**, labelled "Reset all bands (again: undo)" |
| B1 Click Through | `overlay.passthrough` on PAN (not `view.cut_through`) | same | mouse passthrough in overlay mode only | does nothing outside overlay; PAN is also a Mode-0 toggle | **BY DESIGN**, labelled "Click-through (overlay)" |

The owner's suspicion of "conflicting ideas" is not borne out by the file. `test_the_owners_file_holds_the_factory_session_rows_and_nothing_else`: every MIDI row in the owner's file is a factory row, and the only factory rows missing from it are preset-layer rows. No migration fix was needed.

## Fixes (commits eb3d96d, d9b34b0)
- `apc40.fell_back(kind, ch, n, on, held)` returns True for a message only Mode 0 sends:
  - a device knob or device button on channel ≠ 0;
  - on a Mode-0 toggle, a note-off with no press held;
  - on a Mode-0 toggle, a note-on while the last press is still held.

  `MidiIO._handle` then calls `_reenter`. That sends the intro and every light (`_enter`), at most every `REENTER_S` = 2 s, and says so on stderr and in the desk log.
- `apc40.in_channel`: a device button is read on channel 0.
- A desk-learn press records its release as held, so the release is never taken as a Mode-0 sign.
- `midi._apply`: an enum stepped by a toggle row clears its echo at the release.
- `ui_desk.text`:
  - `SET_WORDS` gives "band SUB";
  - an enum on a toggle row reads "<label>: next (<value>)";
  - `DESK_WORDS` covers MASTER, PAN, STOP ALL and QUANT.
- `ui.CHEATSHEET`: four `APC40 …` rows. In `tests/test_ui_shell.py::_sheet_keys` one line changed: columns starting "APC40 " are desk rows, not keys.
- `docs/SETUP.md`: the track buttons, QUANT, STOP ALL, MASTER/PAN, and the Mode-0 fall-back. ENGINEERING §8 already described them correctly and is unchanged.
- Fixture `tests/fixtures/desk-findings/owner-bindings.json` (a copy of the owner's session file) is force-added.

PR: https://github.com/Cutaiar/hyperspace/pull/202

## Gates
- `uv run pytest -q` → `2227 passed, 2 skipped in 176.51s` (2217 + 10 new)
- `uv run ruff check .` → `All checks passed!`
- `uv run pytest tests/test_golden_frames.py -q` → `7 passed` (`test_every_golden_frame_is_drawn_byte_for_byte`; no golden moved)
- `git diff --stat -- hyperspace/library/ tests/golden/` → empty
- Smoke run: `HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=…/desk/smoke-home uv run hyperspace -ApplePersistenceIgnoreState YES` (home = the owner's bindings copy plus an empty config.toml; the factory presets come from the package) → exit 0. Stderr shows `midi: Akai APC40 (apc40, 99 bindings)`; there were no migration notes, the bindings.json is unchanged (13793 B), and stall.log is empty.

## Concerns
1. **The smoke run opened the owner's real APC40**, which was plugged in, and at exit put it in Generic mode (`leave()`). No hyperspace app was running at the time (`pgrep`). The next launch puts it back. This is the same mechanism that probably caused the finding: any second process's exit drops a shared desk to Mode 0. A smoke or probe run under a live show should not open the desk. Not fixed here: out of scope, and an owner's call.
2. The press that reveals the fall-back is lost on a toggle row; from the next press on, everything is momentary again. With the LED in sync, an activator that starts off can take up to three presses before the signature shows. On a device-button channel the first press already counts.
3. Hand check: power-cycle the APC40 under the running app, then press an activator twice. The desk log should say "back in the app's mode" and G8 should then flip once per press. Track select should light on the diagram.
4. Latent bug, not fixed: `Project.cycle` sticks on a bank slot whose preset file is missing (`load_slot` leaves `active` unchanged). It is not what the owner hit.

## Fix round 1 (FIX BASE d9b34b0 → 17f5a10)
1. **Stale `_held` after a reveal.** `_handle` now keeps `fell`. After the rows of a press on a Mode-0 toggle that revealed the fall-back have been applied, it handles a synthetic note_off on the same channel and number. That pops `_held` and clears a trigger's echo. The synthetic release is no sign itself (held, off). Test first: `test_a_revealing_press_is_finished_so_the_next_press_is_no_second_sign` (with `r.t[0] += 3` between presses, intros stay at 2 and G10's echo is dark). It failed before the fix.
2. **The lost press is not replayed** (orchestrator's ruling). SETUP.md and the PR body say the first press after a power cycle may be lost.
3. **Label.** The enum-on-toggle text is now `f"{label}: {p.text()} · next"`, and the test is updated.
4. **SETUP.md wording.** It now says the app notices "within a press or two". The hand check in the PR body adds: in 0x42, select track 2 and turn a device knob; the desk log must show no "back in the app's mode" line.

Gates (round 1):
- `uv run pytest -q tests/test_desk_findings.py tests/test_midi.py tests/test_desk.py tests/test_ui_shell.py` → `142 passed`
- `uv run ruff check .` → `All checks passed!`
- `uv run pytest -q` → `2228 passed, 2 skipped in 156.56s`

No smoke run this round, as instructed. Pushed 17f5a10, and the PR body is updated.
