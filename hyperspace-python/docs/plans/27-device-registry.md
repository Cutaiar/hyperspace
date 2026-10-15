# Plan 27 — the device registry

Every input and output the rig has is now a *device* on one registry:
listed in `config.toml` as `[[devices]]`, opened behind its own entry,
polled in list order each frame, shown on the SYSTEM page one line each,
and closed in one list. The APC40, the Xbox pad and the hands run on it
with `bindings.json` and every preset unchanged; several MIDI desks can
be listed, each with its own profile, and a second desk learns onto a
knob with no code; the bridge's out half and the hands' DAW out are
*sinks* fed by rows in the same table; and an OSC device — a phone app
on the Wi-Fi — is added by a `[[devices]]` entry alone, with no edit to
`app.py`. A point-cloud source type and a device that plays a recorded
cloud are the first step to "speaking point clouds" before any sensor is
bought. Built as stream B of the run in
[`24-26-27-orchestrator-prompt.md`](24-26-27-orchestrator-prompt.md)
(F1 in [`24-party-wishlist.md`](24-party-wishlist.md)). No preset was
edited or added (decision 23): every file under `hyperspace/library/` is
byte-identical; the proofs are fixtures under `tests/fixtures/`.

Hand checks: [`11-hand-checks.md`](11-hand-checks.md) group W, checks
168–190. Open decisions: [`DECISION-REGISTER.md`](../DECISION-REGISTER.md)
rows 140–168. The owner's decisions for this plan (10–14 and 16 of the
launch prompt) are in [`DECISIONS.md`](../DECISIONS.md) with Who "owner".

Branch `plan-24-26-27-integration`, in merge order: B1 (PR #177), B2
(#181), B4 (#184), B3 (#185).

## The block to paste

With no `[[devices]]` list the old `[midi]`, `[gamepad]`, `[hands]` and
`[bridge]` tables still work: at load each becomes the equivalent entry,
in this order, with one note per table the file holds ("config: [midi]
is now a [[devices]] entry (role = 'apc40', kind = 'midi') — see
config.py"). Nothing breaks; the notes ask for the rename. **Today's rig
as a list** — the defaults plus the APC40's port; this exact block gives
the same devices as the old tables
(`tests/test_devices.py::test_todays_rig_as_a_devices_list_equals_the_old_tables`):

```toml
[[devices]]
role = "pad"
kind = "gamepad"

[[devices]]
role = "apc40"
kind = "midi"
port = "APC40"

[[devices]]
role = "leap"
kind = "hands"
enabled = false

[[devices]]
role = "bridge"
kind = "bridge"
enabled = false
```

Delete the old tables when you paste it: with a list, the list says, and
each old table left in the file is ignored with a note ("config:
[[devices]] is listed, so [midi] is ignored — its midi entry says").
**The rig with the hands on**: on the `leap` entry write `enabled =
true` and move every key of the old `[hands]` table onto it (`mode`,
`dofs`, `out`, `calibration`, `tape`, …). At load a `hands-daw` entry
(`kind = "midi-out"`, `port = "Hyperspace Hands"`, `carries = "leap"`)
is put right after it for the DAW out, silently for the default port and
with one note when the entry writes `out` itself. With the bridge on, its
old `send` list becomes rows in `bindings.json` once (B3, below).

**A phone app** (TouchOSC, Lemur, GyrOSC, an Open Stage Control page, a
Max/Pd patch — anything that sends OSC over UDP), pointed at the Mac's
LAN address, port 9000:

```toml
[[devices]]
role = "phone"            # the scheme: its sources are phone:x, phone:y, phone:hit
kind = "osc"
port = 9000               # UDP; host = "0.0.0.0" (every interface) is the default
axes = ["/x", "/y"]       # the app's fader / XY addresses → phone:x, phone:y (continuous)
hits = ["/hit"]           # the app's button addresses → phone:hit (a trigger with velocity)
# rest = 0.5              # where the axes idle (default 0), or per address: rest = { "/y" = 0.5 }
# range = [-1.0, 1.0]     # what the app sends (default [0, 1]); mapped onto 0–1 and clamped
# timeout = 5.0           # seconds of silence before the line reads `lost`
# hold = true             # while lost the axes keep their last values; false lets the routes go
```

A deeper address keeps its path: `axes = ["/1/fader1"]` is
`phone:1/fader1`.

**The recorded cloud** (copy `tests/fixtures/clouds/knot.npz` into
`<home>/clouds/`, or any file `devices.write_clouds` wrote):

```toml
[[devices]]
role = "scan"             # published as cloud:scan
kind = "cloud"
file = "clouds/knot.npz"  # relative to the home (the folder config.toml is in)
# rate = 12               # frames per second (default: the file's own)
# loop = true             # false holds the last frame
```

**A second desk** (B2): `[[devices]] role = "launch"  kind = "midi"
profile = "generic"  port = "<part of its port name>"`.

### What was translated from the old tables

| Old table | Entry (`role`, `kind`) | Its keys |
|---|---|---|
| `[gamepad]` | `pad`, `gamepad` | `usb` |
| `[midi]` | the profile's name (`apc40`), `midi` | `port`, `profile`, `map` |
| `[hands]` | `leap`, `hands` | the whole hands table (`hands/core.py` `DEFAULTS`) |
| `[hands] out` (when the hands are on and `out` names a port) | `hands-daw`, `midi-out`, right after the hands entry | `port` = the old `out`, `carries` = the hands' role, `virtual`, `encoding`, `channel`, `cc`, `rate` |
| `[bridge]` | `bridge`, `bridge` | `out`, `in`, `encoding`, `channel`, `cc`, `rate`, `send`, `in_lanes` |
| `[bridge] send` | sink rows in `bindings.json`, once | (B3) |

Each old table's `enabled` becomes the entry's; the defaults are the old
tables' defaults (`config.DEFAULTS`, the hands' own table), so an entry
written with only `role` and `kind` behaves as the old table with
nothing in it. One note per table the file holds, none for a table it
does not; the `hands-daw` entry's note only when the file wrote `out`.
`[dream]` stays a table: the dream worker has no sources and no sinks, so
it is not a device. The first entry of each old kind is folded back into
its old key (`cfg["midi"]`, `cfg["hands"]`, …), so what still reads
those — the binding file's profile, the hands setup — reads what the
entry says. A relative `map`, `calibration` or `tape` resolves against
the config's folder.

## What was built

### B1 — the interface and the registry

- **At the machine.** The SYSTEM page has a **devices** section above
  **midi**: one line per listed device, in list order, `role · kind ·
  status · n sources · last` — `pad · gamepad · connected · 21 sources
  · usb: Afterglow …`, `apc40 · midi · connected · 137 sources · Akai
  APC40 · 160 bindings · cc 0 48 = 64`. Status is `connected`, `lost`
  (the hardware is not there; the device looks for it itself), `off`
  (its entry says `enabled = false`: nothing opened, no adapter imported) or
  `error: …` in the warning colour. The old MIDI and bridge lines are
  gone (their content is in the device lines); the HANDS page keeps its
  own status. An edit to the `[[devices]]` list in `config.toml` lands
  within about half a second with no relaunch ("devices: bridge changed —
  reopened", "… added", "… removed"); an edit that will not parse, or an
  entry that has to be dropped, is one note ("config: [[devices]] not
  applied — … — the old list stands") and nothing changes. A device that
  raises on a frame shows its error on its line and on the hot-reload
  toast and the frame goes on; one whose open raised is retried on the
  MIDI desk's schedule (every 2 s five times, then every 10 s) and comes
  up with no relaunch. ⌘R and quit close every device, last listed
  first — the pad now among them (its USB reader thread is stopped).
- **Code.** `hyperspace/devices.py` (new): `Port` (name, label, kind
  `value` / `trigger` — or `cloud`, B4 — rest, bipolar, velocity, group,
  layer, scheme; `address` = `scheme:name`), the `Device` protocol
  (`role`, `kind`, `schemes`, `feeds`, `layers`, `wants`, `status`,
  `last`, `sources`, `sinks`, `open`, `poll`, `learn`, `act`, `feed`,
  `send`, `close`, `targets`), `Context`, `Base`, `OffDevice`,
  `UnknownDevice`, `RefusedDevice`, `kinds()` / `kind_class()`, `make` /
  `make_all`, `DeviceRegistry` (`open_all`, `poll` → per device `poll`,
  `learn`, `act`; `feed`; `send`; `close`; `watch` / `apply`; `lines`;
  `targets`; `adapter`, `get`, `first`, `schemes`), `retry_after`,
  `RETRY_S` / `RETRY_FAST` / `RETRY_SLOW_S` (held equal to `midi`'s by a
  test), `WATCH_FRAMES = 30`, `BUILTIN_SCHEMES`. `config.py`:
  `DEVICE_TABLES`, `DEVICE_KEYS`, `_kind_defaults`, `_device`,
  `_translate`, `_devices`, `devices`, `read_devices`. `app.py`:
  `_open_devices` (in place of `_open_midi`, `_open_bridge`,
  `_open_hands`, `_open_pad`; `_open_dream` stays), `Host.devices`,
  `Host.adapters == (devices, dream_io)`, `Host.pad`, the frame's three
  device slots, the `point_at_devices` listener that re-points the panel
  and the ghost renderer, `*rig.targets()` in the reloader.
  `ui.device_lines`, `Panel._device_lines`. `gamepad.Pad.close`.
  `hotreload.MODULES` gains `devices`.
- **Roles, not schemes, for today's devices.** An entry's `role` names
  the device; the device class's `schemes` say which Router keys it
  publishes (`axis` / `pad` / `hat` the pad's, `hand` / `hands` the
  hands', `ext` the bridge's, `cc` / `note` / `pitch` MIDI's), so every
  existing row is unchanged whatever the entry is called. A new device
  (B4's OSC) publishes under its role. Two enabled devices may not feed
  one scheme: a second pad or a second hands device is refused with an
  error line naming both ("feeds 'axis', which pad already feeds — not
  opened") and comes up when the first leaves the list.
- **Tests.** `tests/test_devices.py` (new), notably
  `::test_devices_run_in_list_order_poll_learn_act_then_feed_then_send`,
  `::test_one_devices_exception_never_stops_the_frame`,
  `::test_the_registry_retries_a_failed_open_and_a_lost_device_reconnects_itself`,
  `::test_the_close_list_is_every_device_last_listed_first_and_survives_a_broken_one`,
  `::test_the_config_list_is_watched_every_30_frames_and_a_bad_edit_keeps_the_old_list`,
  `::test_a_second_enabled_device_claiming_a_scheme_is_refused_with_a_note`,
  `::test_pad_close_stops_the_usb_reader_and_forgets_the_pad`,
  `::test_todays_rig_as_a_devices_list_equals_the_old_tables`;
  `tests/test_config.py::test_no_devices_list_translates_the_old_tables_with_one_note_each`,
  `::test_a_devices_list_wins_and_is_checked_per_entry`,
  `::test_read_devices_reports_problems_and_prints_nothing`;
  `tests/test_ui_shell.py::test_system_page_shows_one_line_per_device`.
  Boundary tests changed on purpose: `test_app_boundary.py`'s gated list
  gains `hyperspace.osc` and `pythonosc`; `ORDER` is rewritten (devices
  poll in the scene-setter slot, sources feed in the feed slot, sinks
  run after `reg.apply`); the close list is the registry, last listed
  first — `tests/test_app_boundary.py::test_the_host_close_list_is_every_adapter_in_shutdown_order`
  pins `bridge, hands, midi, pad`, then the audio (its stub has no dream
  worker) — where it was `midi, bridge, hands, dream`; with the dream on,
  its worker closes after the devices (`Host.adapters == (devices,
  dream_io)`).

### B2 — the existing inputs on the registry

- **At the machine.** Nothing changes with one desk. **A second MIDI
  controller** is one more `[[devices]]` entry with `profile =
  "generic"` and its `port`: it opens beside the APC40, nothing is ever
  sent to it (no power-up, no ring, no LED), and **Learn desk** on any
  param completes from its knob ("learned view.inst_amp ← MIDI CC 21 ch1
  on launch (into the preset)"). Its rows are written `cc@launch:0:21`,
  so the same CC on the APC40 does not move them, and the APC40's knob on
  the same param stays (one knob per param *per desk*). **SHIFT is the
  APC40's**: latched, the second desk stays on its preset layer, its rows
  act and a learn on it lands; a preset load drops every desk to the
  preset layer. A desk unplugged at launch reads `lost`, its rows wait,
  and plugging it in brings it up with its power-up and every light.
  The pad and the hands work as before. The ROUTING page's source combo
  lists the analyzer's lanes, then LFO 1–4, then each listed device's
  sources in list order (the pad's axes, the hands, `ext`) — the LFOs now
  come before the hands and the pad. A param's right-click menu keeps
  Learn desk, Learn hand ▸ and Learn pad, and offers **Learn <role>**
  for any other listed device that feeds (an OSC phone: "Learn phone").
- **Code.** `midi.MidiIO(…, role=)` with the entry's profile
  (`bindings.json`'s `"profile"` no longer overrides it), `qualifier`,
  per-role `bindings` / `_active` / `_send` (gated by the profile's
  `FEEDBACK`) / `_handle` (D12 per desk); `midi.PROFILES` gains
  `generic`; `hyperspace/generic.py` (new: `PORT_MATCH = None`,
  `FEEDBACK = False`, every CC absolute with soft pickup, no layout, no
  factory rows). `routing.py`: `ROW_SCHEMES`, `QUALIFIER = "@"`,
  `base_scheme`, `is_continuous` (in place of `LANE_SCHEMES`),
  `Binding.device` / `bare`, `midi_source(…, role)`; `Bindings.midi_roles`,
  `row_schemes`, `layers`, `layer_of`, `layer_serial_of`, `set_layer(…,
  role)`, `toggle_layer(role)`, `role_of`, `serves`, `is_primary`,
  `dispatch(…, role)`, `active(role)`, `bind`'s per-desk rule;
  `Router.use(registry)`, `follow_devices`, `schemes` (in place of
  `ui_routing.SOURCE_ORDER`); `Router._publish_axes` is gone.
  `devices.MidiDevice` (profile, qualifier, `layers`: `("preset",
  "global")` for the first role's APC40, `("preset",)` otherwise),
  `PadDevice` (`act` = `Router.pad` then `gamepad.steer`),
  `DeviceRegistry.continuous_schemes` / `row_schemes` / `midi_roles` /
  `wants`. `gamepad.Pad.open` / `status` / `publish`, `gamepad.publish`,
  `gamepad.steer` (the sticks' camera job, moved out of `app.frame`),
  `gamepad.ride_depth`. `hyperspace/hands/device.py` (new):
  `HandsDevice`, the thin wrapper over `HandsIO` (`schemes = feeds =
  ("hand", "hands")`). `learn.py`: `Learn.devices`, `Learn.wants()` (in
  place of `learn.WANTS`), `BARE_WANTS`, `blocked` per desk.
  `ui_routing.source_schemes`, `ui.learn_wants`. `hotreload.MODULES`
  gains `generic` and `hands.device`. `ui_desk.py` stays APC40-only (its
  docstring says plan 29's generic desk replaces it).
- **Which desk owns the unqualified rows.** The first MIDI entry whose
  `profile` is the binding table's (`bindings.json`'s `"profile"`,
  `apc40` by default) — the desk the file's rows were written for — else
  the first MIDI entry listed. So a generic box listed above the APC40
  does not inherit the APC40's rows or SHIFT, and a rig whose only desk
  is generic still maps.
- **Tests.** `tests/test_device_inputs.py` (new; a fake MIDI bus),
  notably `::test_a_qualified_source_is_its_roles_and_adds_no_colon`,
  `::test_two_desks_open_each_with_its_profile_and_its_own_rows`,
  `::test_a_generic_desk_maps_on_the_desks_learn_with_no_code`,
  `::test_the_latch_is_per_role`,
  `::test_shift_on_the_apc40_leaves_the_second_desks_caught_rows_caught`,
  `::test_the_desk_whose_profile_wrote_the_table_owns_the_unqualified_rows`,
  `::test_a_missing_desk_is_lost_its_rows_wait_and_it_comes_up_with_its_feedback`,
  `::test_the_pad_runs_on_the_registry_rows_axes_and_its_camera_job`,
  `::test_the_hands_run_on_the_registry_through_hands_device`,
  `::test_schemes_wants_and_row_schemes_come_from_the_registry`,
  `::test_a_pre_run_bindings_json_and_every_preset_load_quietly_with_two_desks`.
  `tests/test_hands_boundary.py`'s host-reaching list is `["device.py",
  "panel.py"]` (sorted). `tests/test_desk_trust.py` and
  `tests/test_routing_boundary.py` untouched.

### B3 — sinks

- **At the machine.** A param can be sent *out*: right-click it →
  **Learn sink ▸** lists every sink port the rig offers (`bridge:3 ·
  pitch ch4`); a pick lands at once ("sent view.bright → bridge:6 (into
  bindings.json)"), with no question, no undo step and no preset dirt —
  sinks are rig, so the row is the session's. The DAW receives the
  param's **effective** value (base plus whatever performs it), read
  after `reg.apply`, so it is no longer a frame behind. The rows show on
  ROUTING in their own **sinks** section (a checkbox and a ×), and
  Unbind never removes them. The bridge's old `send` list becomes those
  rows once, the first launch the bridge is on with none, with one note
  ("bindings: [bridge] send is now sink rows in bindings.json (lane:* →
  bridge:0, param:view.bright → bridge:6) — the rows say from here on;
  edit them on ROUTING (sinks)"); from then on the rows say, and deleting
  them never brings them back. The hands' DAW messages go out through
  the `hands-daw` sink (`hands-daw · midi-out · connected · 0 sources ·
  0 sinks · Hyperspace Hands · leap's DAW out · cc 102 = 64 ch16`), as
  before; when the port comes back after a gap the DAW is brought up to
  date. ROUTING's source combo offers the bridge's `ext` lanes as the
  bridge publishes them ("ext ext 0" … "ext ext 15").
- **Code.** `routing.py`: `SINK_OP = "send"`, `SINK_SCHEMES`,
  `Binding.is_sink` / `sink`, `sink_target`, `parse_sink`,
  `sink_refusal`, `sink_rows_from_send`, `sink_values`, `Bindings.sinks`,
  `Bindings.sinks_seeded`, `is_session_row`. `bridge.py`: `Sender` (the
  outbound gate: quantise, change-gate, rate-limit, encode), `OutPort`,
  `_open_out` (moved from `hands/core.py`); `Bridge.reconnect`,
  `receive`, `publish` (the `ext` labels and rests), `send_values`.
  `devices.py`: `Device.sinks`, `Context.devices`, `BridgeDevice` as two
  halves (`poll` reconnects, `feed` receives and publishes, `send` sends
  the sink rows), `MidiOutDevice` (`kind = "midi-out"`), `_lane_sinks`,
  `DeviceRegistry.sink_ports`, `_seed_sinks`, the `n sinks` part of a
  sink's line. `hands/core.py` opens no MIDI port: `HandsIO.outbox`,
  `carry`, `resync`. `config.py`: `MIDI_OUT`, `DAW_ROLE`, `_daw`.
  `learn.py`: `Learn.sinks`, `Learn.learn_sink`, `sinks_of`. `ui.py`:
  `sink_items`, the "Learn sink" submenu. `ui_routing.py`: the `sinks`
  section; `N_EXT` is gone.
- **Tests.** `tests/test_sinks.py` (new), notably
  `::test_a_sink_row_is_a_session_row_never_a_performer_and_round_trips`,
  `::test_a_param_routed_to_the_bridge_sends_its_effective_value_after_apply`,
  `::test_the_bridges_send_list_becomes_sink_rows_once_with_one_note`,
  `::test_rows_deleted_on_routing_never_come_back_the_translation_is_marked`,
  `::test_the_bridge_publishes_its_ext_labels_and_rests`,
  `::test_the_system_line_of_a_sink_says_what_it_sends`,
  `::test_hands_out_becomes_the_hands_daw_entry_with_a_note_when_written`,
  `::test_the_hands_daw_sink_on_the_registry_sends_what_handsio_sent`,
  `::test_learn_sink_on_a_param_lands_a_session_row_with_no_question`;
  `tests/test_hands.py::test_the_hands_daw_sink_sends_what_the_instrument_made_and_no_port_is_opened`
  (and the three DAW-port tests, now over `OutPort`);
  `tests/test_ui_routing.py::test_the_routing_page_lists_the_sink_rows_with_the_others`.
  `ORDER`'s sink slot is `table.sinks`, `bridge.send_values`.

### B4 — OSC and point clouds

- **At the machine.** The phone block above, saved while the app runs,
  adds `phone · osc · lost · 3 sources · UDP 0.0.0.0:9000`; the first
  message makes it `connected · … · /x 0.5`, and five seconds of silence
  `lost` again (the faders keep their place unless `hold = false`).
  "Learn phone" on a param's menu takes the next fader moved a quarter of
  its travel as a route, or the next button press as a button row in
  `bindings.json`; a route names `phone:x` like `hand:right.roll`, and
  ROUTING lists the phone's axes. A port another program holds is
  `error: OSError: … Address already in use`, retried until it frees.
  The cloud block adds `scan · cloud · connected · 1 source · knot.npz ·
  frame 7/16 · 144 points · 12 fps`, the frame counting through the
  recording at its own rate, whatever the app's frame rate; nothing on
  screen draws it yet (plan 26's point-cloud node does).
- **Code.** `hyperspace/osc.py` (new; `pythonosc` is imported only when
  a server opens): `Server` (a non-blocking UDP socket read in `poll`,
  at most `MAX_DATAGRAMS` = 512 a frame, no thread), `Layout`,
  `OscDevice`, `fire`, `DEFAULT_HOST`, `DEFAULT_PORT = 9000`,
  `TIMEOUT_S = 5.0`, `LEARN_TRAVEL = 0.25`. `devices.py`: `PointCloud`,
  `CloudFile`, `write_clouds`, `read_clouds`, `CloudDevice`,
  `CLOUD_SCHEME`, `CLOUD_FILE_VERSION`, `DeviceRegistry.clouds`
  (`{"cloud:<role>": PointCloud}`, never through the Router),
  `Base.rows`, `Base.publishes`; the kind table gains `osc` and `cloud`.
  `pyproject.toml`: `python-osc>=1.8`. `tools/cloud_fixture.py` (new)
  writes the fixture `tests/fixtures/clouds/knot.npz` deterministically.
  `hotreload.MODULES` gains `osc`. **`app.py` has no line for either
  kind**: the only code that names the OSC device is `osc.py` and
  `devices.kinds()`.
- **Tests.** `tests/test_osc.py` (new), notably
  `::test_an_osc_entry_alone_adds_the_device_and_a_fader_moves_a_routed_param`
  (a scratch home whose `config.toml` holds only the entry, and the
  fixture preset `tests/fixtures/osc/phone-routes.json`),
  `::test_only_osc_py_and_the_kind_table_name_the_osc_device`,
  `::test_a_hit_with_velocity_fires_its_rows`,
  `::test_lost_after_the_timeout_and_back_on_the_next_message`,
  `::test_hold_false_lets_the_routes_go_in_a_silence`,
  `::test_a_learn_armed_for_the_role_takes_a_hit_as_a_row_and_a_fader_as_a_route`,
  `::test_a_busy_port_is_an_error_line_and_comes_up_when_it_frees`,
  `::test_an_off_osc_entry_imports_no_osc_library`,
  `::test_a_session_hit_row_waits_while_its_device_is_not_listed`;
  `tests/test_clouds.py` (new), notably
  `::test_a_point_cloud_is_a_read_only_gpu_ready_buffer_with_its_bounds`,
  `::test_the_cloud_file_round_trips_ragged_frames_and_refuses_a_bad_one`,
  `::test_the_fixture_is_what_the_committed_generator_writes`,
  `::test_a_cloud_entry_publishes_the_recording_at_its_own_rate`,
  `::test_a_cloud_is_on_the_registry_not_the_router`,
  `::test_a_missing_recording_is_an_error_line_and_comes_up_when_it_appears`.
  All OSC traffic in the tests is `pythonosc`'s client to 127.0.0.1 on a
  port the device bound itself.

`[[devices]]` keys by kind (each kind's own keys have the old table's
defaults; `config.py`'s docstring is the full list):

| Kind | Keys beyond `role`, `kind`, `enabled` |
|---|---|
| `midi` | `port` (a substring of the port name; required for `generic`), `profile` (`apc40`, `generic`), `map` |
| `gamepad` | `usb` |
| `hands` | the `[hands]` table: `mode`, `dofs`, `out`, `channel`, `cc`, `presence`, `note`, `min_confidence`, `calibration`, `tape`, … |
| `bridge` | `out`, `in`, `encoding`, `channel`, `cc`, `rate`, `send` (read once, B3), `in_lanes` |
| `midi-out` | `port` (required), `virtual` (true), `carries` (a hands role), `encoding`, `channel`, `cc`, `rate` |
| `osc` | `host` (`0.0.0.0`), `port` (9000), `axes`, `hits`, `rest`, `range` (`[0, 1]`), `timeout` (5), `hold` (true) |
| `cloud` | `file` (required; relative to the home), `rate` (the file's), `loop` (true) |

`role` is required, unique and has no `:`; `kind` is required; `enabled`
is true unless it says false (a value that is not true or false is true,
with a note). A bad role, a role listed twice or no kind drops the entry
with a note; an unknown kind is kept as an `error: unknown kind` line. An
OSC role that is a row kind or a built-in scheme (`key`, `pad`, `hat`,
`cc`, `note`, `pitch`, `lane`, `lfo`, `cloud`) is an error line on open.

## Not verified by a person

Nothing of this plan has met the hardware through the registry. Every
proof is a headless test with fake ports, a fake MIDI bus, a stub frame
or `pythonosc`'s client on localhost; the smoke runs (120 frames,
windowed, scratch homes) had no APC40, no pad and no DAW plugged in. In
particular:

- **The SYSTEM page's device lines drawn on a screen**, and the config
  watch with a real editor's save (168, 173).
- **The APC40 unplugged at launch and plugged in later** under the
  registry (175): the fake bus proves the path, not the mk1.
- **Two real desks at once** and a generic controller's knob through
  Learn desk (176, 177).
- **The pad's camera job after its move** into the pad device (179):
  the same code in a new place; ⌘R with the USB pad (171).
- **A DAW receiving a sink row's value or the hands through
  `hands-daw`**, and the resync after a reconnect (181–185).
- **A real phone app's messages**, the macOS firewall prompt the first
  time a server binds `0.0.0.0`, and a bundle from a real sender
  (186–189).
- **The "Learn sink ▸" and "Learn <role>" menu items** on a screen.

## Known rough edges

- **"Learn bridge" is offered and never completes.** The bridge feeds
  `ext`, so it inherits the default `wants` (its role) and every
  modulatable param's menu offers **Learn bridge** whenever a bridge is
  listed — on or off, which includes every un-renamed config (the old
  `[bridge]` table is always translated). The bridge has no `learn`, so
  an armed "Learn bridge" waits until cancelled. A fix is one line
  (`wants = ()` on `BridgeDevice`); not made in this docs pass.
- **A missing hand camera reads `error: no camera`, not `lost`.** The
  hands device passes the tracker's own words through
  (`HandsDevice.status`): an unplugged camera is `error: no camera` and a
  stopped service `error: service lost`, in the warning colour, though
  the Leap thread reconnects by itself and the registry never reopens it;
  `lost` is only "connecting" or a tape that has not started.
- An un-renamed rig config prints one note per old table on every launch
  until the file is edited (by design, like `[overlay]`).
- A changed entry is closed and reopened whole: an edit to the `apc40`
  entry re-sends the desk's power-up and redraws it (a blink).
- A device whose `poll` raises every frame stays red on its line and the
  toast; it is never closed and reopened (the retry covers a failed
  `open` only).
- The first MIDI role owns the unqualified rows and SHIFT; a second
  APC40-profile desk gets its power-up and lights but no SHIFT of its
  own. A hand-written `cc@apc40:…` (the owner's role named explicitly)
  acts as that desk's but is a different control from its unqualified
  twin to the referee.
- **List the APC40 first.** The SYSTEM page's desk log and the panel's
  "turn a knob" hints read the first *open* MIDI desk
  (`app.point_at_devices`: `rig.adapter("midi")`).
- A relative encoder on a generic box learns as `abs`; change the row's
  op on ROUTING.
- `is_continuous` is open-ended on purpose (decision 11): a typo'd scheme
  in a preset route (`hnad:right.roll`) is kept as a dormant performer,
  not dropped with a note.
- The ROUTING combo's order changed (the LFOs before the hands and the
  pad); the bridge's lanes read "ext ext 0".
- An entry after `lane:*` in an old `send` list lands at channel 6 (the
  default band count), so on a rig with another band count the DAW's
  channel map may need one move. Editing `[bridge] send` after the first
  launch does nothing (remove the role from `"sinks_seeded"` in
  `bindings.json` to translate again). An `off` sink offers no ports to
  learn onto. `hands-daw` reads `0 sinks` while it carries the hands.
- The DAW messages leave in the sink slot, after `reg.apply`, about a
  millisecond later than before; tools that build a `HandsIO` with no
  `out` no longer make a "Hyperspace Hands" port as a side effect.
- OSC: only a message's first number is read (an XY pad's second value
  is not); `range` maps the axes only; a velocity above 1 clamps; with
  `hold = true` a phone that leaves the network leaves its routes where
  they were; an app that streams continuously is never `lost`. Any op is
  accepted on a `phone:` row when the device has hits. `hyperspace.osc`
  (not `pythonosc`) is imported whenever the registry resolves a kind.
- Clouds: the file is read whole at open, has one rate (no per-frame
  times), and a NaN point gives NaN `bounds`; a recording changed on disk
  is not re-read until its entry changes.
- **What the launch prompt asked for that was built otherwise.** "The
  role is the scheme" holds for a new device only; today's four keep
  their schemes (`Device.schemes`, row 141). The OSC sources are
  `phone:x` (`<role>:<name>`), not `osc:<role>.<name>` (row 161). The
  pad's camera job runs in the pad device's `act`, the registry step that
  is handed the router, not in `poll`; the pad's feel stays the
  `desk.pad.*` session params read through `router.felt`. One `generic`
  profile covers "generic pads" and "generic CC". "desk for every MIDI
  role" is one `desk` want any desk completes. A Learn sink pick lands at
  once rather than arming and waiting. The hands' DAW encoding stays in
  `hands/core.py`; only the port moved out (`bridge.OutPort`). There is
  no OSC output (a sink) — plan 29's.
