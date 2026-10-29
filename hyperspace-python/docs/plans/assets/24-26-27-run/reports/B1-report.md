# B1 report — Plan 27 B1: the Device interface and the registry, `[[devices]]` in config.toml

**Status:** DONE_WITH_CONCERNS (the concerns are environmental and scoping notes, below).
**Branch / base:** `plan-27-b1-registry` cut from `plan-24-26-27-integration` at `cd9106d` (Base: silence ruff S110 …).
**PR:** https://github.com/Cutaiar/hyperspace/pull/177 (into `plan-24-26-27-integration`).
**Commits:**
- `1b28f42` config: [[devices]] list, the old tables translated at load, fold-back (plan 27 B1)
- `073e893` devices.py: the Device protocol, four shims, the DeviceRegistry; a real Pad.close() (plan 27 B1)
- `49254e7` app, ui: Host.devices, the frame's three device slots, one SYSTEM line per device (plan 27 B1)

**Decisions file:** `/Users/dallman/.claude/jobs/91c58534/tmp/sdd/decisions/B1.md` (six register-row drafts, hand checks W.1–W.6, as-built notes, deliberate deviations, and the exact `[[devices]]` block for today's rig).

## What was built

- `hyperspace/devices.py` (new): `Port`, the `Device` protocol, `Context`, `Base`, `OffDevice`, `UnknownDevice`, the four shims `MidiDevice` / `PadDevice` / `HandsDevice` / `BridgeDevice` over today's `MidiIO` / `Pad` / `HandsIO` / `Bridge` (each adapter imported lazily inside `open()`), `KINDS`, `make`, `DeviceRegistry` (open behind the entry; `poll` → `learn` → `act` per device in the scene-setter slot; `feed` in the feed slot; `send` after apply; one device's exception recorded, never the frame's; a failed `open` retried on the Ports schedule; config.toml's mtime watched every 30 frames and only the device list re-read; close last-listed-first; listeners; hot-reload targets; SYSTEM lines).
- `hyperspace/config.py`: the `[[devices]]` list checked per entry; the old `[midi]` / `[gamepad]` / `[hands]` / `[bridge]` tables translated to equivalent entries when there is no list (one note per table in the file); the old tables ignored with a note when there is a list; fold-back of the first entry of each kind into its table; `config.devices(cfg)`, `config.read_devices(path)`. `[dream]` is not a device (a worker; stays `app._open_dream`).
- `hyperspace/app.py`: `_open_midi` / `_open_bridge` / `_open_hands` / `_open_pad` → `_open_devices`; `Host.devices`, `Host.adapters == (devices, dream_io)`, `Host.pad` property; `frame` polls the registry in the scene-setter slot, feeds it in the feed slot, sends after `reg.apply`; the reloader's targets include `rig.targets()`; the panel and the ghost renderer are re-pointed by a registry listener; `panel.config_notes` is `cfg["notes"]` itself (the registry appends there).
- `hyperspace/ui.py`: a `devices` section on SYSTEM with one line per device (`Panel._device_lines`, its own helper; `ui.device_lines()` the pure text); `_midi_status` / `_bridge_status` removed; `Panel.devices`.
- `hyperspace/gamepad.py`: a real `Pad.close()` (stops and joins the USB reader, forgets the pad). `hyperspace/hotreload.py`: `devices` in `MODULES` (after `hands`, before the `ui_*` modules).
- Not touched: `midi.py`, `apc40.py`, `bridge.py`, `hands/*`, `routing.py`, `learn.py`, `ui_routing.py`, every preset (`git diff --stat -- hyperspace/library/` empty), no docs.

## How it was tested

- `tests/test_devices.py` (new, 17 tests): schedule equal to `midi`'s; kinds and `make`; the three slots in list order; one device's exception; retry of a failed open on the schedule; the close list; the config watch (added / changed / removed, a bad entry, a parse error, the old-table form); lines and page text; swap targets watched and defined; the four shims over fakes and a real `HandsIO` layout; `Pad.close`; today's rig as a list equals the old tables.
- `tests/test_config.py` +3 (translation with one note per table; a list wins and is checked per entry; `read_devices`).
- Boundary tests rewritten as the PR body lists (gated list +`hyperspace.osc`, `pythonosc`; the gate tests, `ORDER`, the close list, the raising adapter, the relative writers; `test_ui_shell`'s bridge line → device lines; `test_undo`'s Host; `test_hands_tape`'s bad-tape note through the registry). Untouched: `test_routing_boundary.py`, `test_hands_boundary.py`, `test_bridge.py::test_core_does_not_import_the_bridge`, both hotreload watch-list tests, goldens / core / shapes4d.

```
$ uv run pytest -q
1905 passed, 2 skipped in 113.37s (0:01:53)        # base: 1885 passed, 2 skipped

$ uv run ruff check .
All checks passed!

$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/tmp/b1-smoke/old uv run hyperspace -ApplePersistenceIgnoreState YES
config: [gamepad] is now a [[devices]] entry (role = 'pad', kind = 'gamepad') — see config.py
config: [midi] is now a [[devices]] entry (role = 'apc40', kind = 'midi') — see config.py
config: [hands] is now a [[devices]] entry (role = 'leap', kind = 'hands') — see config.py
config: [bridge] is now a [[devices]] entry (role = 'bridge', kind = 'bridge') — see config.py
dream: mps · alias copy path · fp32 · weights /tmp/b1-smoke/old/weights
exit=0

$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/tmp/b1-smoke/new uv run hyperspace -ApplePersistenceIgnoreState YES
dream: mps · alias copy path · fp32 · weights /tmp/b1-smoke/new/weights
exit=0
```

`/tmp/b1-smoke/old/config.toml` holds today's old tables (`[midi]`, `[gamepad]` on; `[hands]`, `[bridge]` off; no `[library]`); `/tmp/b1-smoke/new/config.toml` holds the equivalent `[[devices]]` block (pad, apc40 with `port = "APC40"`, leap off, bridge off). Both `stall.log`s are empty. The device lines both runs show, printed headless through the same `ui.device_lines` over the same homes (a script at `/tmp/b1-patches/headless_lines.py`):

```
pad  ·  gamepad  ·  lost  ·  21 sources
apc40  ·  midi  ·  lost  ·  137 sources
leap  ·  hands  ·  off  ·  0 sources
bridge  ·  bridge  ·  off  ·  0 sources
```

## Files changed

`hyperspace-python/hyperspace/devices.py` (new), `config.py`, `app.py`, `ui.py`, `gamepad.py`, `hotreload.py`; `tests/test_devices.py` (new), `test_config.py`, `test_app_boundary.py`, `test_ui_shell.py`, `test_undo.py`, `test_hands_tape.py`. No fixtures added.

## Self-review findings

- The hands' hardware read moved from before `output.apply` / `mouse.poll` / `audio.step` to after `audio.publish` (the feed slot, where `HandsIO.poll` is made from `HandsDevice.feed`). Nothing in between reads the `hand` feed; the HANDS page and the ghost read `HandsIO` state after the frame either way. Named in the PR body.
- The sticks' camera job now runs after every device polled (pad rows, MIDI rows, then the sticks) rather than between the pad and MIDI; independent base writers. Named in the PR body.
- A device whose `poll` raises every frame is red on its line and the toast but never closed/reopened (the Ports schedule covers a failed `open` only) — the same as the per-adapter guards did.
- A changed `[[devices]]` entry is reopened wholesale (the APC40 re-sends `enter` and redraws once).
- `Host.devices`'s annotation reads `devices.DeviceRegistry` while the field is itself named `devices`; with `from __future__ import annotations` it is a string and never evaluated. Tests construct `Host(devices=…)` fine.

## Concerns

1. **The windowed smoke run on this machine blocks inside `glfwInit`** on macOS's "reopen windows?" alert (`NSPersistentUIRestorer promptToIgnorePersistentStateWithCrashHistory`: a Python.app crash left saved state behind; another agent's `uv run hyperspace` was sitting on the same alert). I passed `-ApplePersistenceIgnoreState YES` on the command line, which sets that default for the one process only (NSArgumentDomain; nothing written to the owner's defaults; the app ignores argv), and both runs went through with exit 0. Someone at the machine clicking the alert once clears it for every later run; I did not touch the machine's defaults.
2. The SYSTEM page's new section, the config watch with a real editor, ⌘R with the USB pad, and a tracker coming up through the retry have not been seen by a person (hand checks W.1–W.6 in the decisions file).
3. For B2: the protocol has `act(router)` beside `poll` so the pad can learn before its rows; B2 may fold it into the real pad device's `poll`. `HandsDevice` lives in `devices.py` (not `hands/device.py`) on purpose, so `tests/test_hands_boundary.py` is untouched; B2 moves it. `DeviceRegistry.schemes()` is ready for B2's Router hand-over; routing never imports `devices`.
4. The translation notes print on every launch of an un-renamed rig config (four lines for the owner's `config.toml.rig`) — as the prompt asks, like `[overlay]`.

## Fix round 1 (review of PR #177) — commit `37a08da`

**What changed**
- Important 1 — role ≠ scheme: a register-row draft added to the decisions file ("Role ≠ scheme for today's devices; `Device.schemes` maps them; one scheme, one enabled device" — other options, cost to reverse, rough edge, check W.7). The hazard is closed in `devices.make(entry, ctx, claimed)` / `make_all`: a second enabled entry whose class claims a scheme an earlier enabled entry already publishes becomes a `RefusedDevice` (`error: claims 'axis', which pad already publishes — not opened`), never opened, one note naming both roles, in effect `enabled = false`; `DeviceRegistry.apply` re-makes the list so it comes up when the first leaves. `off` entries claim nothing.
- Minor 2 — `config._kind_defaults(kind)` takes the kind's defaults from `DEFAULTS[section]` / the hands' own table, never the merged `cfg[section]`; an ignored `[midi] port` no longer leaks into a list entry without one.
- Minor 3 — `config.read_devices` parses the file with `tomllib` first (a parse error is the one blocking problem) and otherwise reports only `[[devices]]` problems; a stray top-level scalar elsewhere no longer blocks a live edit.
- Minor 4 — reconnect ownership stated in the module docstring, the `Device` docstring, the protocol's register row and the test's name: the registry retries only an `open` that raised (Ports schedule); a device that reports `lost` after a successful open reconnects itself (today's adapters do; B2/B4 devices must). The registry never closes or reopens a `lost` device.
- Minor 5 — `Port.scheme` and `Port.address` (`scheme:name`); the four shims set the scheme (`axis:LX`, `pad:A`, `hat:UP`, `hand:right.roll`, `ext:0`, `cc:0:48` with `name = "0:48"`). `Device.feeds` (the schemes a device feeds: `axis`, `hand`, `ext`; MIDI none), `devices.BUILTIN_SCHEMES = ("lane", "lfo")`, `DeviceRegistry.continuous_schemes()` (built-ins first, then each listed device's feeds in list order; an `OffDevice` carries its kind's schemes/feeds so a row naming it stays dormant).
- Minor 6 — the MIDI line keeps the port name and the binding count: `MidiDevice.last` is `"<port>  ·  N bindings"` then `"  ·  <last message>"` once one has come (`apc40 · midi · connected · 137 sources · Akai APC40 · 160 bindings · cc 0 48 = 64`).
- Minor 7 — hand check W.5 rewritten around a missing `[hands] tape` file that is then created (and the unplugged Leap as the `lost`, self-reconnecting contrast); W.7 added for the refusal.
- Minor 8 — the PR body names the close-order change (`midi, bridge, hands, dream` → `bridge, hands, midi, pad, dream`: last-listed-first, every close independent) and the two frame-order moves (the hands' read in the feed slot because the shim makes the instrument's one call from `feed`; the camera job after every device polled because the registry polls the list in one pass), each with its reason.

**Covering tests** (new or changed): `tests/test_devices.py::test_a_second_enabled_device_claiming_a_scheme_is_refused_with_a_note`, `::test_the_registry_retries_a_failed_open_and_a_lost_device_reconnects_itself` (renamed; a `lost` device is never reopened and is polled every frame), `::test_continuous_schemes_are_the_builtins_then_each_devices_feeds_in_list_order`, `::test_the_kinds_table_lists_todays_four_and_make_sorts_an_entry` (`Port.address`, an off device's schemes), the pad / hands / bridge / MIDI shim tests (addresses, the MIDI line); `tests/test_config.py::test_a_devices_list_wins_and_is_checked_per_entry` (an entry without `port` beside `[midi] port = "ignored"` gets the default), `::test_read_devices_reports_problems_and_prints_nothing` (a stray `midi = true` does not block the list); `tests/test_ui_shell.py::test_system_page_shows_one_line_per_device` (the MIDI line); `tests/test_app_boundary.py` (the stub gains `bindings`).

**Commands and output**
```
$ uv run pytest -q --no-header -p no:cacheprovider tests/test_devices.py tests/test_config.py tests/test_app_boundary.py tests/test_ui_shell.py
133 passed in 4.52s

$ uv run pytest -q
1907 passed, 2 skipped in 119.30s (0:01:59)

$ uv run ruff check .
All checks passed!
```

## Fix round 2 (re-review) — commit `baff390`

**What changed:** the scheme-claim guard in `devices.make` checks `cls.feeds` (the continuous schemes a device publishes into the Router), not `cls.schemes`. A second gamepad (`axis`) or hands device (`hand`) is still a `RefusedDevice` with the note (`error: feeds 'axis', which pad already feeds — not opened`); a second MIDI entry of a different role is accepted, since MIDI feeds nothing (its messages are rows) — `launchpad` beside `apc40` opens (`lost` at this machine) and is listed on the SYSTEM page, the configuration B2 builds. A duplicate role is already dropped by `config._device` (at load and on a re-read); `make_all`'s docstring says so. `RefusedDevice`'s text and the module / `make` docstrings reworded (feeds, not claims). The register-row draft reworded: the refusal is per fed scheme and per role; its rough edge now carries the open question whether the pad's row schemes (`pad`, `hat`) should block a second pad — B2's call — and the two-desks-unqualified-rows note until B2. PR body updated (decision 1b, a "Fix round 2" section).

**Covering tests:** `tests/test_devices.py::test_a_second_enabled_device_claiming_a_scheme_is_refused_with_a_note` (the `launchpad` entry is a `MidiDevice`, `lost`, no note, both desks in `lines()`; `pad2` still refused with the new text); `tests/test_config.py`, `tests/test_app_boundary.py` unchanged and green.

**Commands and output**
```
$ uv run pytest -q --no-header -p no:cacheprovider tests/test_devices.py tests/test_config.py tests/test_app_boundary.py
79 passed in 1.34s

$ uv run pytest -q
1907 passed, 2 skipped in 117.00s (0:01:56)

$ uv run ruff check .
All checks passed!
```
