# Setup — a new Mac

From nothing to a running Hyperspace, then each optional part with the
one switch that turns it on. Every setting named here goes in
`~/Hyperspace/config.toml` (the home folder; `$HYPERSPACE_HOME` moves it),
which the app does not need to exist — every key has a default. All keys
are listed in [`ENGINEERING.md`](ENGINEERING.md) §5.

## The base

- **macOS on Apple Silicon.** The renderer needs OpenGL 4.1, which every
  Mac has; the dream worker runs on MPS.
- **Xcode Command Line Tools**: `xcode-select --install` (git, clang).
- **uv**: `brew install uv` (or uv's own installer). uv provides Python
  3.12 from `.python-version` and every dependency from `pyproject.toml`
  and the committed `uv.lock`; never pip into a global Python.

```bash
git clone <repo> hyperspace
cd hyperspace/hyperspace-python
uv sync               # everything, including torch for the dream and the dev tools
uv run hyperspace     # opens the render window and the control window
```

`uv sync` also fetches Ultraleap's `leap` wrapper and its `leapc_cffi`
module from GitHub (both pinned to one commit in `pyproject.toml`, and
the cffi module is compiled during the sync); they are only imported
when the hands are switched on.
To check the install: `uv run pytest -q`.

**Microphone permission.** The first time you press M (or *Listen to
mic* on the AUDIO page) macOS asks whether the app that launched the
process — your terminal or editor — may use the microphone. Allow it. If
you denied it, the bands sit at nothing: turn it on in System Settings →
Privacy & Security → Microphone.

## The dream

On by default. torch and torchvision are ordinary dependencies, so plain
`uv sync` installs them. The first time the dream runs it downloads the
pretrained weights (VGG16, or GoogLeNet for some layers) into
`~/Hyperspace/weights` unless they are already there or in torch's hub
cache. If the worker cannot start, the app runs the echoes alone and
says why on the red banner, the SYSTEM page and the LOOKBACK page. To
turn it off:

```toml
[dream]
enabled = false
```

## Capturing the Mac's own sound

To react to music playing on the Mac (not a microphone):

1. `brew install blackhole-2ch`. If macOS blocks the driver, allow it
   under System Settings → Privacy & Security, then restart.
2. In Audio MIDI Setup make a **Multi-Output Device** with BlackHole and
   your speakers, and make it the Mac's output, so you hear the music and
   the app can capture it.
3. In the app, AUDIO page: BlackHole appears as `System · …` and is
   pre-selected. Press M.

An audio interface that is class-compliant needs no driver; pick it in
the same device list (**rescan** if it was plugged in after launch).

## The APC40

Plug it in (USB). Nothing to configure: the MIDI adapter is on by default
and looks for a port whose name contains "APC40". The desk map is
[`ENGINEERING.md`](ENGINEERING.md) §8. To check the device without the
app: `uv run python tools/midi_probe.py`. Another port name or no MIDI at
all:

```toml
[midi]
port = "APC40"      # a substring of the port name
enabled = false     # no MIDI adapter at all
```

## The Ultraleap hands

1. Install **Ultraleap Hand Tracking** for macOS and check its control
   panel sees the camera. The `leap` wrapper loads its library from
   `/Applications/Ultraleap Hand Tracking.app/Contents/LeapSDK`; if it is
   installed elsewhere, set `LEAPSDK_INSTALL_LOCATION` to that `LeapSDK`
   folder in the shell that launches the app. The tracking *service* must
   be the app's; the `leapc_cffi` the app ships is not used — `uv sync`
   builds our own for 3.12, and it is found first on `sys.path`. An
   `ImportError: Cannot import leapc_cffi … Unknown error` means that
   build is missing from the environment (re-run `uv sync`): an older
   Hand Tracking app ships only a Python 3.8 build of it, which this
   project's 3.12 cannot import.
2. Switch the hands on:

   ```toml
   [hands]
   enabled = true
   mode = "screentop"   # only if the camera looks down from above; "desktop" (the default) looks up
   ```

3. Check the axes live: `uv run python tools/hands_probe.py`.
4. Calibrate once in the place you will play: the HANDS page's
   **calibrate 20 s** (or `uv run python tools/hands_probe.py --calibrate
   20`), moving both hands through everything they should reach, with
   nobody else in view. This writes `~/Hyperspace/hands.json`.

Only the desktop mode's axes have been measured; with `screentop` or
`hmd` and the ghost hands on, the HANDS page says so.

## FL Studio (or another DAW) over the IAC bus

1. Audio MIDI Setup → MIDI Studio → **IAC Driver** → tick "Device is
   online". For lanes both out and in, add a second bus: IAC echoes, so
   `in` must never be the bus `out` sends to.
2. Switch the bridge on:

   ```toml
   [bridge]
   enabled = true
   out = "IAC"          # a substring of the bus name the lanes go out on
   in = ""              # a second bus's name to take lanes in as ext:0, ext:1 …
   ```

3. In FL Studio take the IAC bus as a MIDI input. By default lane *i* is
   pitch bend on channel *i* + 1 (`encoding = "cc14"` sends CC pairs
   instead). The SYSTEM page's bridge line shows the port and a rising
   count of messages sent.

The hands send to a DAW on their own port, a virtual one called
"Hyperspace Hands" unless `[hands] out` names another.

## A second screen (or more)

One `[[output.screens]]` table per render output, up to four; the first
is output 1 (it sets the frame's size and paces the loop):

```toml
[[output.screens]]
name = "glass"
monitor = 1          # screen index, the primary is 0; -1 = a window where it was last
fullscreen = true

[[output.screens]]
name = "projector"
monitor = 2
fullscreen = true
```

The screens must be connected **before launch**: a later output whose
screen is missing is not opened, and a screen plugged in afterwards is
not used until a relaunch (Cmd+R). The OUTPUT page lists each output and
what it shows. Details and the per-output switches are
[`ENGINEERING.md`](ENGINEERING.md) §14.

## Share presets with someone

Two people (or two Macs) can have the same presets: whatever either saves
shows up on the other. The presets live in a cloud-synced folder; each
Mac's own settings stay in its home (`~/Hyperspace`).

1. Make a folder in your cloud drive, shared with each other (for
   example `Dropbox/Hyperspace`). On iCloud, mark it "Keep Downloaded";
   on Dropbox, "Available offline". Evicted files are invisible to the
   app.
2. Quit Hyperspace. Run
   `uv run python tools/move_library.py ~/Dropbox/Hyperspace` (whoever
   goes second keeps their own copy of any same-named preset, and the
   tool says which).
3. Add the printed `[library]` lines to `~/Hyperspace/config.toml`, then
   start Hyperspace.
4. If a "conflicted copy" preset shows up, load both, keep one, and
   delete the other.

If the folder is ever missing at launch (the drive not mounted), the app
says so, turns saves off and creates nothing: fix it and restart. Details
are in [`ENGINEERING.md`](ENGINEERING.md) §4, "The shared library".

## Re-recording the golden traces (rare)

Only to re-record the parity traces from the retired HTML app:

```bash
uv run playwright install chromium   # one-time, about 150 MB
uv run python tools/record_golden.py
```

Running the tests on committed traces needs neither.
