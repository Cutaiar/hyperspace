# Setup — priors for any Mac

Everything that must be true on a machine before the plans in
[`docs/plans/`](plans/README.md) can be implemented and run there. Tiered:
tier A unblocks development (plans 00–02); later tiers unblock the plans
that touch hardware. Nothing outside this list may be assumed — if an
implementation step needs something not listed here, the fix is to add it
here, not to install it silently.

## A. Base toolchain — required for all plans

- [ ] **macOS 13+**, Apple Silicon or Intel. The GL ceiling everywhere is
      OpenGL 4.1 core (deprecated-but-working; BLUEPRINT §6) — nothing to
      install, but nothing newer to rely on either.
- [ ] **Xcode Command Line Tools** — `xcode-select --install`. Provides git
      and clang (source-builds of any wheel-less dep).
- [ ] **Homebrew** — installer of record for everything below that isn't
      Python.
- [ ] **uv** — `brew install uv`. Owns the Python toolchain: the interpreter
      version comes from the repo's `.python-version` (≥3.12), dependencies
      from `pyproject.toml` + the **committed `uv.lock`**. Setup on a fresh
      clone is `uv sync` — never global pip, never a hand-built venv.
- [ ] **Python dependencies** — arrive via `uv sync`, listed here so the
      full surface is visible. All ship macOS wheels (universal2), so no
      compiler is exercised in the normal case:
      - runtime: `numpy`; `moderngl` + `glfw` (02); `sounddevice` —
        PortAudio is bundled in the wheel (03); `imgui-bundle` (04);
        `mido`, `python-rtmidi`, `python-osc` (05)
      - dev-only: `pytest`, `ruff`, `playwright`
- [ ] **Playwright's Chromium** — `uv run playwright install chromium`
      (~150 MB download; the only network fetch at setup beyond brew/uv).
      Needed only where plan-00 traces are (re)recorded; a machine that
      just consumes committed traces can skip it.
- [ ] **Repo hygiene that makes the rest portable** (enforced from plan 00):
      - `uv.lock` and `.python-version` committed; `tests/golden/`
        committed (minus the real track, which is sha256-referenced — all
        tests except its trace run without it).
      - Zero rig-specific values in code. Device names, Δt, IMU port, MIDI
        port names, bridge lanes live in a git-ignored `config.toml`. Once
        rig-facing plans land, a `config.example.toml` will be committed for
        new machines to copy and edit.
      - No absolute paths anywhere; nothing may reference this machine's
        checkout location.

**Verify tier A:** fresh clone → `uv sync` → `uv run pytest` passes;
`uv run hyperspace` opens the render window (post-plan-02).

## B. Live & system audio — plan 03 task 1 (and the current HTML features)

- [ ] **Microphone permission** for the terminal app (or IDE) that launches
      the process — System Settings → Privacy & Security → Microphone.
      CoreAudio input prompts once per hosting app; a denied prompt is a
      silent zero-signal, so check here first when bands sit at nothing.
- [ ] **BlackHole 2ch** — `brew install blackhole-2ch`. If macOS blocks the
      driver, allow "Existential Audio" under Privacy & Security, then
      restart (README has the walkthrough).
- [ ] **Multi-Output Device** in Audio MIDI Setup containing BlackHole +
      the speakers, so audio is heard *and* captured. Manual, per-machine,
      one-time. AirPlay outputs can't join one (README).
- [ ] **Audio routing helper (optional)** — the CoreAudio switcher previously
      shipped as `scripts/audio-route` has been extracted to the standalone
      [`loopback`](https://github.com/Cutaiar/loopback) repo. Clone it if you
      want a CLI to snapshot and swap default in/out devices.
- [ ] **Audio interface** (booth-out capture): any class-compliant
      interface needs no driver; if the rig's interface isn't
      class-compliant, its vendor driver goes on the rig's own checklist.

## C. DJ booth & sensors — plan 03 tasks 2–4

- [ ] **Wired Ethernet** to the Pro DJ Link switch — on a modern MacBook
      that means a USB-C/Thunderbolt Ethernet adapter. Wi-Fi to the booth
      switch is not a substitute for the spike.
- [ ] **Local Network permission** (macOS 15+ prompts per app) granted to
      the launching terminal, and — if the macOS firewall is on — incoming
      UDP allowed for the Python binary. Both failure modes look like "no
      packets", so check them before debugging code.
- [ ] **UDP ports free**: Pro DJ Link owns 50000–50002 (exactly one client
      may bind them — the Python client and Beat-Link-Trigger cannot run
      simultaneously); the IMU port (default 8888) is configurable in
      `config.toml`.
- [ ] **Fallback JVM** — only if the DJ Link spike fails and the
      Beat-Link-Trigger route is taken: `brew install --cask temurin`
      (Java 17+) plus the BLT app itself.
- [ ] **ESP32 toolchain** (firmware flashing only, not the visualizer
      machine per se): `arduino-cli` or PlatformIO via brew; USB-serial
      driver if the board uses CH340 (CP210x/native-USB boards need none);
      a **2.4 GHz** Wi-Fi AP on the same subnet as the visualizer — ESP32
      has no 5 GHz, and UDP broadcast doesn't cross subnets.

## D. DAW bridge — plan 05, optional

- [ ] **IAC Driver enabled** in Audio MIDI Setup → MIDI Studio (built into
      macOS, off by default) with a bus named to match `config.toml`.
- [ ] **FL Studio** (macOS build) installed; the tested FL version pinned
      in `docs/plans/assets/05-fl.md`; the `fl/HyperspaceBridge` MIDI
      script copied into FL's user data folder per that walkthrough.

## E. Ultraleap hands — plan 08, optional

- [ ] **Ultraleap Hand Tracking** (Gemini ≥ 5.17, macOS) installed and the
      camera seen by its control panel.
- [ ] **`leap` bindings** built for Python 3.12 from
      `ultraleap/leapc-python-bindings` (precompiled only for 3.8), with the
      steps in [`plans/08-hands.md`](plans/08-hands.md#install-the-sdk-is-not-on-this-machine-yet).
- [ ] `[hands] enabled = true` in config.toml; `tools/hands_probe.py
      --calibrate 20` (or the HANDS page's calibrate) run once in the box.

## Quickstart transcript for a fresh Mac (tiers A+B)

```bash
xcode-select --install
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install uv blackhole-2ch
git clone <repo> hyperspace && cd hyperspace/hyperspace-python
uv sync
uv run playwright install chromium   # only if re-recording golden traces
uv run pytest                        # tier-A verification
# manual, one-time: Multi-Output Device in Audio MIDI Setup;
# grant mic + local-network permission on first launch
uv run hyperspace
```
