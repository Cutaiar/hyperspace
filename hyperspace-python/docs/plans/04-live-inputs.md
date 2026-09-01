# Plan 04 — Live inputs (booth hardware)

**Blueprint stage 3, executed fourth.** Renumbered 2026-08-21 — deferred
until deck and IMU hardware access exists. The audio-capture task moved to
plan 03 with the UI; what remains here is Pro DJ Link, the IMU network, and
delay compensation tying metadata to the audio clock.
This plan contains the project's first-ever real audio capture (ENGINEERING
§9: every live path so far is stub-verified only) and its one genuine
unknown (pure-Python DJ Link vs. current Pioneer hardware).

## Prerequisites

Plans 01–03 complete. For task 2: physical access to the decks. For task 3:
a flashed ESP32. Task 1 (audio capture) largely landed with plan 03; what
remains here is verifying the booth interface input on real hardware.

## Deliverables

```
hyperspace/audio.py      # sounddevice capture → analysis.py, device picker
hyperspace/djlink.py     # beat/bar phase source (+ OSC fallback listener)
hyperspace/imu.py        # asyncio UDP ingest + mapping table
hyperspace/clock.py      # Δt delay compensation for metadata
firmware/imu_esp32/      # minimal ESP32 sketch emitting the packet format
docs/plans/assets/03-*   # spike findings, calibration numbers
```

## Tasks

### 1. Audio capture (first real capture — treat everything as unproven)

`sounddevice` input stream at 48 kHz feeding `analysis.py` ring-buffered;
device enumeration with the BlackHole/loopback preselection heuristic ported
from the HTML (`isLoopback`-by-name). `scripts/audio-route on` covers the
system-audio routing; a hardware interface input is just another device.

Verify live, in order: (a) mic — clap test, SUB/BASS respond; (b) BlackHole —
play `gate-prover.wav` through system audio, confirm MIDB/MID/AIR sit at
exactly zero while SUB/BASS/UPR move (the same proof the golden traces
encode); (c) the audio interface on a booth out if hardware is available.
Record which paths were actually exercised — do not report the untested ones
as working.

### 2. Pro DJ Link — spike first, then build

**Spike (timeboxed, ~half a day with the real decks):** can `python-prodj-link`
(or the best current pure-Python client) see the CDJ-3000/XDJ-AZ, identify the
master deck, and stream beat packets with a stable beat grid? Write the
finding — packet types seen, firmware versions, failures — into
`docs/plans/assets/03-djlink-spike.md`.

- **Pass →** build `djlink.py` on it directly.
- **Fail →** fallback per BLUEPRINT §3.3: Beat-Link-Trigger emitting OSC on
  localhost; `djlink.py` becomes an OSC listener with the same interface.

Either way `djlink.py` exposes one contract:
`{bpm, beat_phase, bar_phase, master_deck, on_air[]}` with phases in [0,1)
derived by interpolating beat packets against the monotonic clock,
BPM-corrected between packets. Downstream code never knows which backend ran.

### 3. IMU

- Packet: `struct {uint8 ver; uint8 id; float qw, qx, qy, qz;}` little-endian
  (BLUEPRINT §3.4 — quaternions, versioned). Firmware sketch: ESP32 + BNO055
  fusion output, UDP broadcast at 100 Hz to a configured port.
- `imu.py`: asyncio `DatagramProtocol`; per-sensor last-quat + staleness
  timeout (a prop that stops broadcasting decays to no contribution, it does
  not freeze the shape).
- Mapping: config table `sensor id → planes → gain`; orientation *deltas*
  integrate into angle offsets on the w-planes (XW/YW/ZW). Never map
  orientation to a speed multiplied by absolute time (BLUEPRINT §1,
  correction 3).
- Verify with the real prop: turn the prop, the shape everts; hold it still,
  rotation continues from audio alone; power it off, contribution decays.

### 4. Delay compensation

`clock.py` applies a configurable Δt to the metadata path only:
Δt = stream input latency (reported by sounddevice) + analysis latency
(FFT hop + envelope group delay) − ~1 ms network. Then calibrate per
BLUEPRINT §4.3 / rev-1 §6.4: metronome through the mixer, trim Δt until the
beat-phase flash and the kick transient land on the same frame. Store the
calibrated value in the rig config file and the number in
`docs/plans/assets/03-calibration.md`.

## Exit criteria

- [ ] All three sources drive the shape live, simultaneously, for a full
      track without drift, stall, or unhandled exception.
- [ ] DJ Link spike finding written; primary-vs-fallback decision recorded.
- [ ] Gate-prover live test passes over BlackHole (zero bands stay zero).
- [ ] Δt calibrated on the metronome test; value in config and documented.
- [ ] The honest test matrix (which paths ran against real hardware, which
      didn't) is written into *Results*.

## Risks / notes

- The DJ Link spike is the schedule risk; do it first, everything else here
  is well-trodden.
- Audio callback discipline: the sounddevice callback only copies into the
  ring buffer. FFT + chain run on the frame loop, as in the HTML. No
  allocation, no locks held across the callback.
- Beat-phase continuity through packet jitter matters more than absolute
  accuracy — a visible stutter in a bar-locked effect is worse than 5 ms of
  offset (which Δt absorbs anyway).
