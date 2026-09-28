# Hyperspace — System Blueprint, rev. 2 (Python target)

> **Reading note (plan 10, 2026-09-27).** The `ENGINEERING §N` references
> below predate plan 10's rewrite of `ENGINEERING.md`, which removed the
> HTML-era sections and renumbered the rest. Read them by topic against the
> current section titles, and treat this document as the design of record
> for the port, not as a description of the system as built — that is
> [`ARCHITECTURE.md`](ARCHITECTURE.md).

This supersedes `System Architecture Blueprint.md` (the Gemini spitball, kept for
reference). That draft sketched the right *inputs* — Pro DJ Link metadata, IMU
steering, a real audio feed, delay compensation — but proposed building them on
FL Studio + ZGameEditor Visualizer, discarding everything this repo already
does. This revision keeps the draft's good ideas, corrects its errors, and
retargets the system as a **Python application** whose renderer and audio chain
are ports of the proven implementation in `hyperspace.html`.

Ground truth for all ported behaviour is [`ENGINEERING.md`](ENGINEERING.md).
Where this document and that one disagree about how the existing chain works,
`ENGINEERING.md` wins.

---

## 1. Rectification — what changed from rev. 1 and why

**Dropped entirely:**

| Rev. 1 component | Why it's gone |
|---|---|
| FL Studio + ZGameEditor Visualizer | Replaced by a native Python renderer. No DAW in the runtime loop — but FL Studio remains connectable through the optional bridge in §3.6. |
| loopMIDI / IAC as *internal* plumbing | With everything in one process, values flow as floats internally. MIDI survives only at the edges, as an optional adapter (§3.6). |
| 14-bit MIDI CC (MSB/LSB) as *internal* transport | The stepping problem it solved only exists because of 7-bit MIDI; native floats make it disappear internally. The MSB/LSB technique returns only inside the bridge (§3.6) when emitting high-resolution CC to a DAW. |
| Python UDP→MIDI bridge daemon | IMU packets are read directly by the application. The bridge was only needed to reach FL Studio. |
| Fruity Parametric EQ 2 + Fruity Peak Controller | The repo's six-band chain is a superset of a Peak Controller — built deliberately as one (ENGINEERING §1, item 6) — and its dynamics-recovery stage exists precisely for brickwalled DJ masters, rev. 1's exact input. One sub-bass band would be a downgrade. |
| The raymarched tesseract shader | It renders one shape; the repo has 18 exact polytopes. Kept only as a possible future "solid" render mode. |

**Kept from rev. 1:**

- Pro DJ Link ingestion — master deck BPM, beat/bar phase, on-air status.
- ESP32 + IMU sensors over UDP for live plane steering.
- Booth/Master out into a proper audio interface (the transport options —
  passive snake over CAT6, or RF — stand as written).
- Delay compensation at the metadata ingress point, and the metronome
  calibration procedure from rev. 1 §6.4.

**Corrected errors in rev. 1:**

1. **Slicing vs. projection.** Rev. 1 §2.1 specifies perspective 4D→3D
   projection but its shader does hyperplane *slicing* (`vec4(p3D, w)`). These
   produce fundamentally different pictures. This system projects:
   `k = D4 / (D4 − w)`, as `hyperspace.html` does.
2. **Missing rotation planes.** Rev. 1's shader declares six speed uniforms but
   defines only four rotation matrices (`rotateXZ`, `rotateYW` absent, their
   uniforms unused). All six planes are first-class here, as in the repo.
3. **The `angle = time × speed` bug.** Rev. 1 multiplies absolute time by a
   live-modulated speed, so any speed change at time *t* jumps the angle by
   `Δspeed × t` — minutes into a set, a small IMU nudge whips the shape through
   many revolutions. Rotation state must be *integrated*:
   `ang[p] += dt · drive[p]` (`hyperspace.html:1218`). All modulation targets
   angular velocity or angle offsets, never `time × rate`.
4. **Fader positions.** Rev. 1 §2.2 promises per-channel fader positions from
   Pro DJ Link. The broadcast carries on-air flags, not continuous fader
   values. Dropped from the extracted-attributes list; verify against the
   actual mixer before ever re-promising it.

---

## 2. System overview

```
┌──────────────────────────── DJ BOOTH ────────────────────────────┐
│  [ CDJ-3000s / XDJ-AZ + DJM ]                                    │
│    ├─ Pro DJ Link (Ethernet UDP) ─────────────┐                  │
│    └─ Booth / Master 2 out (analog) ──────────┼────────┐         │
│  [ ESP32 + IMU props ]                        │        │         │
│    └─ Orientation packets (Wi-Fi UDP) ─────┐  │        │         │
└────────────────────────────────────────────┼──┼────────┼─────────┘
                                             │  │        │
┌──────────────────── VISUALIZER MACHINE ────┼──┼────────┼─────────┐
│                                            ▼  ▼        ▼         │
│  ┌───────────── one Python process ─────────────┐  [ Audio      │
│  │  imu.py        djlink.py                     │    interface ] │
│  │  (UDP listen)  (Pro DJ Link client)          │        │       │
│  │      │             │ ◄─ delay Δt ─┐          │        │       │
│  │      ▼             ▼              │          │        ▼       │
│  │  ┌────────── modulation bus ──────┴──┐   audio.py (capture)   │
│  │  │  per-plane angular velocity +     │◄──── bands.py          │
│  │  │  angle offsets + beat phase       │      (ported chain)    │
│  │  └───────────────┬───────────────────┘                        │
│  │                  ▼                                            │
│  │  render.py (moderngl: 4D rotate → project → draw edges)       │
│  │  ui.py     (band strips, meters, scenes, transport)           │
│  └───────────────────────────────────────────────────────────────│
└──────────────────────────────────────────────────────────────────┘
```

One process, one language. The only external moving parts are the audio
interface driver and (optionally) Beat-Link-Trigger if the pure-Python DJ Link
route falls short — see §3.3.

---

## 3. Subsystems

### 3.1 Renderer — port, not rewrite

The wireframe engine is the product's identity and it ports directly:

- **Geometry:** `geometry.py` is a transliteration of the 18 shape
  constructions (`expand`, `cyc3`, `prism`, `duoprism`, `edgesByMinDist`) into
  numpy. The vertex/edge/cell counts table in ENGINEERING §2 becomes the unit
  test — every shape must match exactly.
- **Pipeline (unchanged):** rotate in 4D across six planes → perspective
  project 4D→3D (`D4 / (D4 − w)`) → view orientation (yaw/pitch) → project
  3D→2D. The six-plane rotation composes into one 4×4 matrix per frame on the
  CPU (numpy, trivial at these sizes) and uploads as a uniform; the vertex
  shader applies rotation and both projections.
- **Backend:** moderngl + a GLFW window. Edges as a line list; vertices as
  points. Works on macOS (GL 4.1 core) and Windows alike.
- **Depth cueing:** the Canvas version painter-sorts edges and fades alpha on
  w-depth. In GL, prefer additive blending (order-independent, and the
  glow-vs-recede look survives); keep the density-compensation term
  (`dens = clamp(340/edges, .42, 1)`) — without it the 120-cell blows out
  exactly as documented in ENGINEERING §3.
- **Aesthetic:** black ground, white edges, red `#ff2b2b` vertices, monospace
  instrument-panel UI. This is a considered look (ENGINEERING §7); the port
  keeps it.

### 3.2 Audio engine — port the chain, prove parity

- **Capture:** `sounddevice` (PortAudio). Any interface input, including
  BlackHole loopback — the same routing `scripts/audio-route` already
  automates. 48 kHz; blocksize small enough that capture latency is dominated
  by the interface (sounddevice reports actual stream latency; that number
  feeds Δt in §4.3).
- **Analysis:** replicate Web Audio semantics so the ported constants stay
  valid — fftSize 4096, Blackman window, per-frame magnitude smoothing
  `s = 0.15·prev + 0.85·cur` (the deliberately low `smoothingTimeConstant`;
  the band envelopes do the real smoothing).
- **The chain (ENGINEERING §4, ported verbatim):** six bands → power-sum RMS →
  dB → `u`; LEVEL path (asymmetric one-pole, valley tracker, confidence gate,
  upward expansion) and TRANSIENT path (fast − slow envelope) → per-band blend
  → harmonic coupling → pre-drive → transfer function (all 13 `SHAPERS`, with
  per-band scratch state) → post-drive → `PLANEDRIVE[plane] = dir · out · 3.2
  · masterGain`. `softCeil` with NOM 1.0 / KNEE 1.25 / CEIL 2.6, warm-up fade,
  no hard clamps anywhere. The 11 scenes and per-band knob set carry over,
  including the fader taper objects (`map`/`unmap` exact inverses).
- **Parity is the acceptance test, not code review.** The repo already has a
  headless-Chromium harness (ENGINEERING §6). Use it to capture golden traces:
  feed known WAVs (the 50 Hz + 3 kHz gate-prover, the synthetic brickwalled
  file, one real commercial track) through `hyperspace.html`, log
  `AUDIO.inp/out` and `PLANEDRIVE` per frame, and require the Python chain to
  match within tolerance on the same input. Port bugs faithfully first —
  including the known trim non-monotonicity (ENGINEERING §4 warning) — then
  fix them in Python where regressions are testable. Fixing during the port
  makes parity failures undiagnosable.

### 3.3 Pro DJ Link ingestion

- **Primary:** a pure-Python client (`python-prodj-link` or equivalent) inside
  the process, extracting master-deck BPM, beat number within bar, and beat
  timestamps; derive continuous 0–1 beat and bar phase by interpolating
  between beat packets against the local clock.
- **Fallback (de-risk):** Beat-Link-Trigger (mature JVM implementation,
  first-class CDJ-3000 support) emitting **OSC over localhost** — not MIDI —
  into an OSC listener in the process. Same data, one extra box.
- **Risk to burn down first:** pure-Python library support for current
  hardware (CDJ-3000 / XDJ-AZ) is unproven. This is a day-one spike with the
  real decks: if it can't lock to the beat grid, take the BLT fallback and
  move on.
- Extracted: BPM, beat/bar phase, master deck identity, on-air flags. Not
  extracted: fader positions (see §1, correction 4).

### 3.4 IMU sensors

- **Hardware as rev. 1:** ESP32 + BNO055 (preferred — onboard fusion) or
  MPU6050, broadcasting UDP.
- **Packet:** keep it dumb and versioned: `struct {uint8 ver; uint8 id; float
  qw, qx, qy, qz;}`. Quaternions over Euler — the props this is for
  (ENGINEERING §10: flow props) spin through gimbal lock constantly; yaw
  range conventions (rev. 1 assumed ±180°, BNO055 reports 0–360°) stop
  mattering too.
- **Ingest:** asyncio `DatagramProtocol` in-process. Values arrive as floats
  and stay floats.
- **Mapping:** IMU orientation contributes *angle offsets and steering*, never
  raw speeds (see §1, correction 3). v1 mapping: prop orientation → the three
  w-plane angle offsets (XW/YW/ZW), so physically turning the prop turns the
  shape through the fourth dimension; a config table maps sensor id → target
  planes → gain, so multiple props can steer different planes.

### 3.5 Control UI

The band strips, meters, scenes, transport and tooltips in `hyperspace.html`
are a large share of its value. Two options:

1. **In-process immediate-mode UI** (imgui via `pyimgui`/`imgui-bundle`) drawn
   in the same GL window — recommended for v1. Meters and knobs are natural
   there, and the instrument-panel look is reproducible.
2. **Serve the existing HTML panel** from the Python app over a WebSocket,
   keeping the browser as a detached control surface. More reuse, but keeps a
   protocol boundary alive forever.

Start with (1); revisit (2) only if a remote/tablet control surface becomes a
real requirement.

### 3.6 External I/O bridge — keeping FL Studio (and friends) connectable

The runtime is DAW-free, but the modulation bus gets a pluggable adapter layer
so a DAW can sit on either side of it later. Off by default; enabling one is
config, not code.

**Outbound** (`mido` / `python-rtmidi` to a virtual port — IAC on macOS,
loopMIDI on Windows — plus an OSC emitter):

- Band outputs (`AUDIO.out`), `PLANEDRIVE`, and beat/bar phase as CC streams —
  14-bit MSB/LSB pairs (CC *n* / CC *n+32*, 16,384 steps) where the receiver
  benefits, since 7-bit stepping is a real problem again at this boundary.
  Caveat: FL Studio's *Link to controller* does not natively fuse MSB/LSB
  pairs — plan on either a small FL MIDI script (its built-in Python MIDI
  Scripting API) to combine them, or per-channel **pitch bend**, which is
  natively 14-bit and links directly with no script (16 channels = 16
  high-res lanes per virtual port).
- MIDI clock derived from the DJ Link BPM, so FL Studio (or lighting rigs,
  or anything else) can tempo-lock to the decks through this system.

This makes the visualizer usable as an analysis front end: FL Studio patches,
other visuals, or fixtures consume the same six-band chain the renderer does.

**Inbound** (MIDI or OSC listener feeding the bus and the parameter system):

- External control of scenes, per-band knobs, master gain — so FL automation
  or a hardware controller can drive the visualizer.
- An external modulation source can inject plane-drive the same way a band
  does, subject to the same integration rule (§1, correction 3).

The bridge is deliberately not in the v1 migration stages — it lands after
Stage 4, and nothing in the core may depend on it.

---

## 4. Modulation bus & synchronization

### 4.1 The bus

Every frame, per plane `p`:

```
ang[p] += dt · speed · RATE[p] · PLANEDRIVE[p]      # audio (as today)
ang[p] += imu_offset_delta[p]                        # IMU steering (§3.4)
```

Beat phase does not add a third rotation term by default — it drives the
**time base of the tempo-syncable shapers**: CHOP and TREM (and future LFOs)
lock to bar phase instead of free-running Hz, which is the tempo-sync open
thread from ENGINEERING §9 resolved properly. An optional per-plane "bar spin"
(one full turn per bar, phase-locked) is cheap to add and visually legible;
make it a scene parameter, off by default.

### 4.2 Beat phase

`beat_phase`, `bar_phase` ∈ [0,1), derived by interpolating between DJ Link
beat packets against the monotonic clock, BPM-corrected between packets so
phase stays continuous through packet jitter.

### 4.3 Delay compensation (rev. 1's best idea, kept)

Metadata outruns audio: a beat packet arrives ~1 ms after the CDJ emits it,
while the same beat's audio passes through the interface buffer and the
analysis chain. Apply a configurable delay **Δt to the metadata path only**:

```
Δt = (interface input latency, reported by the stream)
   + (analysis latency: FFT hop + envelope group delay)
   − (network latency ≈ 1 ms)
```

Computed as a starting point, then trimmed by ear/eye with rev. 1 §6.4's
calibration: metronome through the mixer, adjust Δt until the beat-phase flash
and the kick transient land on the same frame. Store per-rig in config.

Note the audio *band* path needs no compensation against itself — it is
self-timed, as today. Δt only aligns the metadata clock to the audio clock.

---

## 5. Migration plan

Each stage has an exit criterion; nothing advances on vibes.

To be unambiguous about the HTML file's role: **nothing in `hyperspace.html`
executes at runtime, ever.** It is a test oracle used once, during the port, to
record the golden traces that prove the Python code reproduces its behaviour —
after Stage 2 it is never run again except to re-record a trace. The final
system is Python end to end, renderer included.

- **Stage 0 — golden traces.** Use the headless-Chromium harness to record
  per-frame `AUDIO.inp/out`, `PLANEDRIVE`, and projected vertex positions from
  `hyperspace.html` for the test WAVs and a fixed rotation script. *Exit:
  traces committed under `tests/golden/`.*
- **Stage 1 — geometry + audio parity, headless.** `geometry.py` matches the
  V/E table exactly; `bands.py` matches golden traces within tolerance on the
  same audio. No window yet. *Exit: parity tests green in CI.*
- **Stage 2 — renderer.** moderngl window, all 18 shapes, drag orbit,
  brightness/density behaviour verified against screenshots of the HTML at
  matched angles. *Exit: side-by-side is visually indistinguishable on the
  5-cell, tesseract, 120-cell, and Clifford torus.*
- **Stage 3 — live inputs.** Audio capture path (first real capture ever —
  ENGINEERING §9 notes no session has done one); IMU ingest with a real ESP32;
  DJ Link spike against real decks, fallback decision made. *Exit: all three
  sources drive the shape live; Δt calibrated on the metronome test.*
- **Stage 4 — UI + scenes.** Band strips, meters with NOM/KNEE landmarks and
  the over-drive annunciator, scenes, transport for file playback. *Exit:
  everything reachable in the HTML panel is reachable natively.*
- **Stage 5 — divergence.** Fix the trim non-monotonicity (the three candidate
  fixes are listed in ENGINEERING §9 — decide there), add tempo-locked
  shapers, per-band LFO knobs, saveable scenes (trivially unblocked: it's a
  JSON file now). The HTML artifact is frozen at the parity point; whether it
  stays deployed as a zero-install demo is cosmetic — it has no role in the
  running system, and new work lands only in Python.

---

## 6. Risks & carried-over open issues

- **Pure-Python DJ Link support for current hardware** — the one genuine
  unknown; spiked first in Stage 3, with BLT+OSC as the standing fallback.
- **Web Audio analyser replication** — smoothing/window semantics must match
  or every ported constant drifts; that's what Stage 1 parity exists to catch.
- **Trim non-monotonicity** is ported as-is and fixed in Stage 5, not during
  the port (ENGINEERING §4 warning, §9 decision).
- **No live capture has ever run** (ENGINEERING §9) — Stage 3 is the first;
  treat mic/loopback/interface paths as unproven until then.
- **macOS OpenGL is deprecated-but-working** (4.1 core). Fine for line
  rendering for years; if it ever bites, `wgpu-py` is the escape hatch and the
  pipeline (§3.1) is simple enough to carry across.

## 7. Target repo layout

```
hyperspace/            # python package
  app.py               # entry point, main loop, config
  geometry.py          # 18 shapes + edge recovery (ports ENGINEERING §2)
  bands.py             # six-band chain, shapers, scenes (ports §4)
  audio.py             # sounddevice capture + FFT front end
  djlink.py            # Pro DJ Link client (or OSC listener fallback)
  imu.py               # UDP ingest + mapping table
  render.py            # moderngl pipeline (ports §3)
  ui.py                # imgui panel (ports the drawer)
  bridge.py            # optional MIDI/OSC in+out adapters (§3.6)
tests/
  golden/              # traces recorded from hyperspace.html (Stage 0)
  test_geometry.py     # V/E/cell parity
  test_bands.py        # chain parity vs golden traces
hyperspace.html        # reference only — never executed at runtime (§5)
docs/ENGINEERING.md    # living reference for the ported behaviour
docs/BLUEPRINT.md      # this file
docs/plans/            # staged implementation plans
docs/SETUP.md          # machine prerequisites
```
