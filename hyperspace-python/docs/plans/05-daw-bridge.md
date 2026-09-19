# Plan 05 — DAW bridge (optional I/O)

**Blueprint §3.6.** The pluggable MIDI/OSC edge that keeps FL Studio (and
lighting rigs, other visuals, hardware controllers) connectable. Off by
default; enabling an adapter is config, not code. **Nothing in the core may
import from or depend on this module** — that rule is what keeps the runtime
DAW-free.

## Status (2026-09-08)

Task 3's controller half landed ahead of the rest, driven by an APC40 on
the desk: `params.py` is the parameter registry (every panel widget, hotkey
and gamepad button goes through it), `midi.py` is the inbound MIDI adapter
with soft pickup, LED/ring feedback and right-click Learn, `apc40.py` the
first device profile, `config.py` the `[midi]` gate. The core-independence
rule is tested (`test_core_does_not_import_the_midi_adapter`). OSC, MIDI
clock and the FL script remain as written below.

**Status (2026-09-18, plan 07 WP4c):** task 1's MIDI half and task 3's
external-lane half landed in `bridge.py`: the analyzer's lanes (and any
param's effective norm) go out as per-channel pitch bend or 14-bit CC
pairs, rate-limited and change-gated; the same forms in become the
routing table's `ext:<i>` sources. `[bridge]` in config.py gates it, off
by default; port handling is `midi.Ports`, shared with `MidiIO`. Setup
and the FL link walkthrough: `assets/05-bridge.md`. MIDI clock waits for
a beat source (DJ Link); the loopback round trip is `tests/test_bridge.py`.

## Prerequisites

Plan 04 complete. FL Studio available for the receiving-end tests.

## Deliverables

```
hyperspace/params.py         # parameter registry (done)
hyperspace/midi.py           # inbound MIDI adapter + feedback (done)
hyperspace/apc40.py          # device profile: port, SysEx, LEDs, default map (done)
hyperspace/config.py         # [midi] section; [bridge] to follow (done)
hyperspace/bridge.py         # MIDI lanes out / ext lanes in, config-gated (done)
config: [bridge] section     # ports, channel maps, resolutions, rates
fl/HyperspaceBridge/         # FL MIDI script fusing 14-bit CC pairs
docs/plans/assets/05-bridge.md   # IAC setup + FL link walkthrough (done)
docs/plans/assets/05-fl.md   # FL-side script walkthrough
```

## Tasks

### 1. Outbound MIDI (`mido` / `python-rtmidi`)

To a virtual port — IAC on macOS, loopMIDI on Windows (the port is created
by the OS tooling; the bridge opens it by configured name):

- **CC streams:** per-band `AUDIO.out`, `PLANEDRIVE`, beat/bar phase.
  Default **14-bit MSB/LSB pairs** (CC *n* / *n+32*, 16,384 steps); per-lane
  config can select 7-bit. Rate-limited (default 100 Hz per lane) and
  change-gated so idle lanes go silent.
- **Pitch-bend lanes:** any lane can be mapped to pitch bend on a dedicated
  channel instead — natively 14-bit, and FL links to it with no script.
  Recommended default for the highest-priority lanes.
- **MIDI clock** derived from the DJ Link BPM (24 ppqn), started/stopped
  with beat-grid lock, so FL or fixtures tempo-lock to the decks through
  this system.

### 2. Outbound OSC (`python-osc`)

The same lanes as OSC messages (`/hyperspace/band/{i}/out`, `/planedrive/{p}`,
`/phase/beat`, `/phase/bar`) — for receivers where OSC beats MIDI. Shares the
lane/rate config with MIDI.

### 3. Inbound control

MIDI and OSC listeners feeding the parameter system and the bus:

- Parameter control: scene select, per-band knobs, master gain, brightness —
  addressed by the same parameter registry the UI uses, so anything the
  panel can change, a controller can change. Accepts 7-bit, 14-bit pairs,
  and pitch bend.
- External modulation: an inbound lane may inject per-plane drive, entering
  the bus under the same integration rule as every source
  (velocity/offsets — never `time × rate`; BLUEPRINT §1 correction 3).
- Loop-safety: a parameter change that arrived from the bridge is not echoed
  back out on the bridge.

### 4. FL Studio side

- `fl/HyperspaceBridge/`: an FL MIDI script (FL's built-in Python MIDI
  Scripting API) that fuses incoming MSB/LSB pairs into smooth values, since
  FL's *Link to controller* won't natively (BLUEPRINT §3.6).
- `docs/plans/assets/05-fl.md`: walkthrough — IAC setup, enabling the port,
  installing the script, linking a lane to a plugin parameter, locking FL's
  tempo to the MIDI clock.

## Verification

- Loopback test, no DAW: a second virtual port pair; pytest sends a known
  ramp through outbound → inbound and asserts reconstruction to 14-bit
  precision, rate limiting, and change-gating.
- FL test, by hand: link one band lane via the script and one via pitch
  bend to visible plugin knobs; play `brickwalled.wav`; knobs move smoothly
  (no 128-step zipper); FL tempo follows a deck BPM change within a bar.
- **The no-dependency rule, enforced:** a test imports every core module
  with `bridge` absent/stubbed and asserts clean startup with the bridge
  disabled in config.

## Exit criteria

- [x] Loopback round-trip test green (`tests/test_bridge.py`, fake ports).
- [ ] FL receives smooth 14-bit motion by both mechanisms; walkthrough
      written and followed once from scratch.
- [ ] MIDI clock verified against a deck BPM change.
- [x] Core-independence test green; bridge disabled costs zero at runtime.

## Risks / notes

- 100 Hz × many 14-bit lanes is a lot of MIDI messages; virtual ports handle
  it, but keep change-gating on by default and let config trim rates.
- FL MIDI scripting API has quirks per FL version; pin the tested FL version
  in the walkthrough.
- The user has "a couple different applications" for this bridge — build the
  generic lane/config machinery, not something shaped around one use case.
