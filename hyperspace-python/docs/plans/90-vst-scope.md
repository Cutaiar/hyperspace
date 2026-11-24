# Plan 90 — Hyperspace as a VST3 / AU / CLAP plugin (scope, not a build)

**Draft, scoping only**, 2026-11-24. Nothing here is built, and no application
code changed. Rows and hand checks are unassigned.

Evidence tags on every claim: **[R]** read in this repo · **[I]** inferred
from what was read · **[W]** from a web page, linked in "Sources" · **[M]**
from memory, **needs verification**.

## 1. The answer in six lines

1. **Thin native plugin + the existing Hyperspace app as a separate process.**
   The Python/GL/torch app cannot live in a DAW's process [I].
2. The plugin sends **four things** to the engine: transport/tempo, the track's
   audio, N generic knob values, and a saved state blob. It renders nothing.
3. **v1 needs no headless engine and no packaging.** The engine is today's app,
   launched from the repo by the plugin or by hand. Owner is the only user.
4. **First spike needs zero engine changes**: the existing OSC device
   (`osc.py`) already takes UDP and feeds source lanes [R].
5. **Real engine work**: a `host` ingest device, a host-slaved clock (reverses a
   recorded owner decision), a `host` audio mode, load-patch-from-blob. All
   sit behind the control-surface layer being designed in parallel.
6. **Long pole** is only real if this ships to others: a signed, notarized
   engine bundle. Defer it.

## 2. What exists today (facts the plan rests on)

| Fact | Tag |
|---|---|
| One Python process: GLFW + moderngl, imgui panel, one frame loop in `app.frame`; `app.main` opens a visible control window, a hidden root GL window and ≥1 output window | R (`app.py` 615–640, 2160–2200) |
| 862 registered params (525 continuous, 156 enum, 128 toggle, 51 trigger, 2 text) | R (counted via `headless.make_app`) |
| `headless.py` = registry + library + router with **no GL, no audio, no window**; a test/migration harness. **No production windowless engine exists.** | R (`headless.py` docstring) |
| The only DAW link is `bridge.py`: virtual MIDI, 14-bit pitch-bend or CC pairs, 16 lanes out and 16 in; in = `ext` source vector, `Router.feed("ext", …)` | R |
| `osc.py`: UDP, non-blocking read in the frame (≤512 datagrams/frame), axes = first number of a message mapped to 0–1, hits = triggers; role = scheme (`host:x` if role `host`). Added by a `[[devices]]` entry alone | R |
| Devices poll at step 2, feed at step 8, send at step 12 of the frame; registry written only at those slots | R (ARCH §2) |
| Tempo is **tap-only**: `beat(t) = (t − t0)·bpm/60 + nudge`, 4/4 assumed. "No DJ Link, no MIDI clock" is a recorded owner decision | R (`tempo.py`, `DECISIONS.md` 162, 743) |
| Audio: capture or file → `_Ring` → analyzer on the frame loop. A `mix` mode already lets **another producer push mono 48 kHz into the ring** with no stream opened, and falls silent after 6 idle frames | R (`audio.py`) |
| Syphon (GPU, ~0.3 ms at 1080p) and NDI publishers exist per output | R (`media/publish.py`) |
| Patches load **by name from the library folder** (`LoadedPatch.load(name)`); `loadable.dumps(doc)` exists. No load-from-blob door seen | R (`loadable.py` 694, 959) — verify |
| No bundling tool (py2app, PyInstaller, Briefcase) in the repo; install is `uv sync` | R (grep; only `.venv` hits) |
| Heavy/optional pieces are gated and lazily imported: torch (`[dream] enabled`), Ultraleap (`hands` group, built from `vendor/`), segment/Vision | R (`pyproject.toml`, ARCH §1) |
| Mac-only deps: pyobjc, mlx, Vision, Syphon. Linux works for tests only | R (`pyproject.toml`) |
| Plan 58 §6 declined the UI-decoupling phases (for other reasons: test monkeypatching, owner says orthogonal). The control surface does **not** need them: it reads the registry, not the panel | R (58 §6) · I (the last part) |

## 3. Architecture

```
 DAW (FL Studio, macOS)                         Hyperspace engine (today's app)
┌───────────────────────────┐   loopback       ┌─────────────────────────────┐
│ plugin (effect, audio in) │ ── UDP: time+lanes ─▶ host device  → Router.feed │
│  audio thread: lock-free  │ ── UDP: audio ──────▶ AudioEngine "host" ring    │
│  ring → sender thread     │ ◀─ control surface ─▶ state / commands (HTTP+WS) │
│  params, state blob, UI   │    (parallel design)  applied at scene-setter slot│
└───────────────────────────┘                    └─────────────────────────────┘
```

### 3.1 Plugin ⇄ engine: decision and alternatives

| Option | Verdict | Why |
|---|---|---|
| **A. Thin plugin + separate engine, two channels: fast UDP feed + control surface** | **Recommended** | Only shape that works [I]. Fast data (≥60 Hz transport, audio) stays off HTTP/WS; slow data (state, commands, patch) rides the control surface |
| B. Everything through the control surface (WS) | Reject for audio/time | Head-of-line blocking and TCP jitter on the time-critical path [I]. Fine for state |
| C. Embed Python in the plugin | Reject | GL, torch, GLFW main-thread rules, DAW crash = process crash [I] |
| D. Port the renderer to native | Reject | Whole-product rewrite; 862 params, graph, shaders [R] |
| E. Plugin sends MIDI via `bridge.py` only | Keep as the **no-plugin fallback**, not the plan | No transport, 14-bit lanes max 16 [R] |
| F. Reuse `osc.py` as the wire | **Spike only** | Zero engine change, but one number per axis, values clamped 0–1, no timestamps [R] |

### 3.2 Audio path

| Option | Verdict | Notes |
|---|---|---|
| **Raw mono audio from the plugin → engine ring** (mode `host`, same pattern as `mix`) | **Recommended** | One analyzer, one set of lanes/bands, no C++ port of `analysis.py`/`bands.py` [R/I]. Header carries sample rate; `_attach(mode,label,rate)` already takes a rate [R] |
| Transport for it: **UDP datagrams** (e.g. 1024-sample chunks) first; **shared-memory SPSC ring** only if profiling demands | UDP first | ~192 kB/s mono 48 kHz [I]. A lost chunk is a glitch in a FFT window, harmless to visuals [I]. The audio thread must never call `send()`; it writes a lock-free ring and a plugin worker thread sends [M — standard audio-thread practice] |
| Analysis lanes only (plugin computes RMS + a few bands) | Spike only | Two analyzers that drift; the lane set is fixed by what C++ computes [I] |
| Loopback capture (today) | Keep as fallback | Works with no plugin; needs BlackHole-style driver and per-track routing is awkward [R/I] |
| Which audio: put the plugin **as an insert effect** on the mixer track → it gets that track's audio with no routing. Sidechain only to tap *another* track | Recommended | FL sidechaining needs a mixer route plus a plugin setting [W]. Insert-effect behaviour in FL [I] — verify |

### 3.3 Transport and tempo

- Plugin sends **host-clock-stamped** records: `{host_mono_time, ppq, bpm, playing, bar_start, time_sig}`, ~60–120 Hz and on every change [I].
- Same machine, so both ends can use the same monotonic clock; engine extrapolates `beat(now)` from the last record [I].
- **Needs a host-slaved mode in `tempo.Clock`** (set bpm and a beat anchor from outside). This **reverses recorded owner decisions** (no MIDI clock / DJ Link). Tap stays the default; host-slave is opt-in per patch or toggle [R/I]. Owner must confirm.
- Latency: DAW audio plays ~one device buffer after `process()`; the visual has render + display latency. Ship a **manual offset (ms)** in the plugin, reusing the idea of `nudge` [R/I]. Do not try to auto-compensate.
- What a DAW actually reports about transport (and what FL Studio does when stopped, looping, time-sig changes) is **[M] — spike item S2**.

### 3.4 Parameters

| Option | Verdict | Why |
|---|---|---|
| **Fixed N generic params** (suggest 32 floats "Hyperspace 1…32", plus one patch-index stepped param, one master intensity) | **Recommended** | Arrive as a `host` lane vector; the **existing routing table** maps lane → any of 862 params, per patch [R/I]. DAW automation lists stay usable, ids never change |
| Dynamic: expose registry params | Reject | 862 params, ids/labels change with patches; hosts handle runtime param lists unevenly [I/M] |
| 14-bit MIDI lanes (today) | Superseded | 7–14 bit, 16 lanes, no names [R] |

- Lane **names**: engine publishes labels (as `bridge` does for `ext`) [R]. Whether FL shows renamed params live is **[M]**, so the plugin GUI shows names regardless.
- Pitfall: do **not** feed back. The plugin's knob → engine lane → param; the engine must not write the DAW param (two-way would loop) [I].

### 3.5 State and recall

| Option | Verdict |
|---|---|
| **Embed** the loadable patch JSON (`hyperspace.loadable/12`) + 32 knob values + schema/engine version in the plugin state blob | **Recommended** — the project is self-contained [I] |
| Store the patch **name + content hash** only | Fallback if size or merge pain: needs the library on the same machine [I] |
| Store nothing; engine keeps its own "last show" | Reject: visual does not follow the song [I] |

- **Missing assets**: embedded patch references media files/the library by path; report a warning, do not fail [I].
- Engine needs **load-from-blob** and **get-current-blob** (patch JSON) doors. Today's load is by name through the library [R] — control-surface requirement R6 below.
- Host `getState` is synchronous on the DAW's main thread [M], so the plugin keeps a **cached last-known blob** updated by an engine event, never blocks on the network.

### 3.6 GUI

| Option | Verdict |
|---|---|
| **v1: no embedded view.** Plugin panel = status, 32 knobs (generic), offset, "open Hyperspace" | **Recommended** — engine's own windows show the visual and the panel |
| v2: preview in the plugin via **Syphon client** of a dedicated output (`publish.py` already makes the server) | Later; macOS only, ObjC++ client, GPU shared surface [R for server; M for client details] |
| v2 alt: small JPEG/WebP preview over the control surface WS | Later; simplest cross-platform, low fps [I] |
| GL inside the plugin GUI | Reject: macOS GL is deprecated and the host owns the view; several instances would fight for the context [M] |

### 3.7 The cross-cutting cases

| Case | Decision |
|---|---|
| Several instances, one engine | Engine is a **singleton** (lock file + known loopback port in a per-user dir). Each instance gets an id. **v1: one active instance drives**, others show "idle (another instance is driving)". v2: namespaced lanes `host.<n>` [I] |
| Engine absent / crashed | Plugin never blocks or glitches audio. Shows status, backs off and retries (like `midi.RECONNECT_S`), keeps all state locally, **re-sends full state on reconnect**. Auto-launch only on explicit click, never in a loop [R pattern / I] |
| Offline bounce / export | **Unsupported v1.** Plugin reports "realtime only"; engine ignores the feed. A frame-exact export is a separate product feature [I] |
| Host sample-rate / buffer changes | Header carries sample rate every chunk [I] |
| Windows | Out of scope: Syphon, pyobjc, mlx, Vision are Mac-only [R] |

### 3.8 Framework

| Option | For | Against |
|---|---|---|
| **JUCE** | VST3 + AU + standalone from one codebase; AudioPluginHost for testing [M] | AGPLv3 or a paid licence if distributed [W]; check current tiers on juce.com |
| CLAP SDK direct + clap-wrapper (to VST3/AU) | Tiny plugin (no GUI v1); FL lists CLAP on macOS [W] | Wrapper licences/maturity **[M]**; FL's CLAP behaviour with audio effects **[M]** |
| nih-plug (Rust) | Safe, small | VST3 bindings licence **[M]**; AU not supported **[M]** |

**Recommendation:** spike in **JUCE → VST3** (FL's most-used path [M]); revisit CLAP and licensing before any distribution. Personal, undistributed use makes AGPL a non-issue [I — not legal advice].

**Target DAWs:** FL Studio on macOS lists CLAP, VST3, AU and VST2 [W]. A third-party table says FL has no CLAP [W]; it looks stale next to Image-Line's own docs, but **owner should confirm in their FL version**. Other DAWs: untested.

## 4. What the plugin needs from the control surface

This is a requirements list, not a design. Items marked ⚠ would change the design.

| # | Need | Data / rate | Latency / ordering | Flag |
|---|---|---|---|---|
| R1 | **Snapshot subscription**: patch name, dirty flag, lane labels (names for the 32 knobs), engine version, engine status | events on change, < 1 Hz | none | |
| R2 | **Commands** from the plugin: `load_patch(blob)`, `set_host_clock_mode`, `set_lane_labels` ask, `get_patch_blob` | rare | applied at the **scene-setter slot** (step 2), as in the parallel design | ⚠ **load-from-blob** is not in today's library API (R6) |
| R3 | **Fast ingest channel** `host`: time record (60–120 Hz) and 32 knob values (change-driven + ≤60 Hz) | small UDP datagrams | **Fed at step 8 (feed slot)** like `ext`; latest-wins, drop-old; **must not go through HTTP** | ⚠ If the surface is HTTP/WS-only, add a UDP/datagram ingest or a WS binary fast path. The engine should read it **without a thread**, as `osc.py` does [R] |
| R4 | **Audio ingest** `host` mode: framed PCM + sample rate + sequence number | ~190 kB/s mono | none ordered; sequence for gap detect | Different from R3: not part of "state/commands" |
| R5 | **Timestamps**: records carry the plugin's monotonic host time; engine reads the same clock | ns | must be same-machine monotonic clock | ⚠ If the surface stamps on arrival, phase jitters by the transport jitter |
| R6 | **Patch blob out/in**: `get_patch_blob()` returns loadable JSON for the live state; `load_patch(blob)` loads it | ~10s–100s kB | one undo step; reject on schema mismatch | ⚠ today `load(name)` goes through the library folder [R] |
| R7 | **Auth**: loopback only, per-user token in a file the plugin can read | — | — | ⚠ any local process could drive the engine otherwise |
| R8 | **Event when the user edits the patch** in the engine, so the plugin's cached blob is fresh | on change | debounced | |

## 5. What must exist in the engine first

| # | Piece | Today | Work | Size |
|---|---|---|---|---|
| E0 | **Control surface** (R1–R8) | Being designed elsewhere | Not scoped here | (parallel) |
| E1 | **`host` device kind**: UDP non-blocking poll → `Router.feed("host", vec)` + labels/rests | `osc.py` is the pattern; registered in `devices.kinds()` [R] | New adapter module + kind-table line; tests like `tests/test_osc.py` | S–M |
| E2 | **Host-slaved clock** | `tempo.Clock` tap-only [R] | `Clock.slave(bpm, beat, t)` mode; owner decision change; LFO sync tests | M |
| E3 | **`host` audio mode** | `mix` mode does the push-into-ring pattern [R] | `AudioEngine.start_host(...)`, rate-aware ring, idle→silence | S–M |
| E4 | **Patch load/save by blob** | `Library.load(group, name)` [R] | Blob in/out beside the file path; one undo step | M |
| E5 | **Launchable by the plugin** | `uv run` from the repo [R/I] | A documented launch command + singleton lock | S |
| E6 | **No-window engine mode** | `app.main` needs windows and a GL context; `headless.py` has no GL [R] | **Not needed for v1.** Needed only for a server-style install or the embedded preview | L, deferred |
| E7 | **Packaging** (.app, signing, notarization) | Nothing in repo [R] | py2app/PyInstaller/Briefcase **[M]**; exclude torch (gated, lazy) [R]; Ultraleap needs the SDK on the machine [R]; signing certs are the owner's | L–XL, deferred |

## 6. Phased breakdown

Agent = can be done in a cloud session (Linux builds/tests; no macOS). Owner = needs a Mac, a DAW, certs or hardware.

| Phase | Work | Size | Depends | Agent / owner |
|---|---|---|---|---|
| **P0 Spike** (§8) | Trivial plugin → OSC; verify FL transport/audio facts | S | none | Agent: plugin code + a Linux test host. Owner: build on Mac, load in FL, report |
| **P1 Engine ingest** | E1 + E3 against a local fake plugin (Python script) | M | E0 for transport choices | Agent, fully |
| **P2 Host clock** | E2, decision change, tests | M | P1, owner's go-ahead | Agent; owner decides |
| **P3 Plugin v1** | Real plugin: 32 params, time + audio sender, status, reconnect, state blob (name only) | M–L | P0, P1 | Agent writes; owner builds and tests in FL |
| **P4 Recall** | E4 + embed patch in state, missing-asset warning | M | E0 (R6), P3 | Agent; owner round-trip test (save project, reopen) |
| **P5 Multi-instance + crash** | Singleton, one-active rule, reconnect-resend | M | P3 | Agent; owner tests |
| **P6 Preview GUI** | Syphon client or WS preview | M–L | P3, E6 maybe | Owner-heavy (macOS GUI) |
| **P7 Packaging** | E7 | L–XL | all | Owner (certs, notarization, clean-Mac test) |

## 7. Risks and open questions for the owner

**Risks**

| Risk | Note |
|---|---|
| FL Studio's plugin host quirks (transport when stopped, effect vs generator, sidechain) | All **[M]**; spike S1–S4 settles them |
| Audio↔visual sync feels off | Offset knob is the answer; no auto-compensation promised |
| Engine on the frame loop at 60–120 fps vs feed rates | Latest-wins; fine [I] |
| Distribution (JUCE licence, notarized engine) | Only matters if you ship to others |
| Control-surface design may not allow a non-HTTP fast path | Flagged in R3/R5 |
| Agent cannot test in a DAW | Every plugin phase ends in an owner test |

**Questions for the owner**

1. Personal tool or product to ship? (Decides packaging, licensing, E7.)
2. OK to reverse "no MIDI clock / no DJ Link" for an **opt-in host-slaved clock**? (E2)
3. Which FL Studio version, and does it load CLAP and VST3 for you? Is the plugin an insert on a track?
4. Is the plugin allowed to **launch** the engine, or do you start it yourself?
5. Embed the patch in the project (self-contained, bigger) or reference by name?
6. Is one active instance enough for v1?
7. Do you want any visual inside the plugin window, or is the engine's own window fine?

## 8. Recommended first spike (≈ a day of owner time)

**Goal:** prove the loop end to end with no engine code change.

1. A minimal **JUCE VST3** effect (audio pass-through) that sends, over UDP to `127.0.0.1:9000` as OSC: `/level` (RMS 0–1), `/phase` (beat phase 0–1 of the bar), `/playing` (0/1), `/bpm` (scaled), `/k1` (one automatable param). Audio thread writes a lock-free value, a timer thread sends at 60 Hz.
2. Engine side: a `[[devices]]` entry `role = "host"`, `kind = "osc"`, `port = 9000`, `axes = [...]` [R: `osc.py` header]. Route `host:level` to a visible param (e.g. brightness) in the existing routing page.
3. Add a Python script that replays the same messages with no plugin, to separate engine problems from plugin ones.

**Answers it gives** (each one a currently-unverified claim):

| # | Question |
|---|---|
| S1 | Does FL load the plugin as an insert effect and give it the track's audio? |
| S2 | What does FL report for tempo and ppq: stopped, playing, looping, tempo automation? |
| S3 | Is the audio-to-visual offset acceptable, and is a single static offset enough? |
| S4 | Do FL's automation clips drive the generic param, and does it survive project save/reopen? |
| S5 | What does a second instance do to the first? |
| S6 | OSC rate/precision: are the 0–1 axes and one-number-per-message enough, or is a real `host` device needed now? |

**Not in the spike:** audio streaming, state blob, GUI, packaging.

## Sources

- [FL Studio manual — plugin standards](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/plugins_supported.htm): macOS lists CLAP, VST3, AU, VST2 [W].
- [FL Studio 2024 release notes](https://forum.image-line.com/viewtopic.php?p=1953419): CLAP added in 2024 [W].
- [Antares formats blog](https://www.antarestech.com/blog/vst3-au-aax-clap-plugin-formats-2026): says FL has no CLAP; likely stale [W].
- [Nuro Audio — sidechain in FL](https://help.nuroaudio.com/article/47-how-to-sidechain-in-fl-studio): mixer route plus plugin setting [W].
- [JUCE forum — licences](https://forum.juce.com/t/help-understanding-licenses/69205): AGPLv3 or commercial; check juce.com for current tiers [W].
- Not found by search, so [M]: VST3 host transport details in FL, clap-juce-extensions / nih-plug / clap-wrapper licences.
