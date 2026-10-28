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
uv sync               # everything, including torch for the dream, Apple Vision for the segment, and the dev tools
uv run hyperspace     # opens the render window and the control window
```

`uv sync` also fetches Ultraleap's `leap` wrapper from GitHub (pinned to
one commit in `pyproject.toml`) and compiles its `leapc_cffi` module from
`vendor/leapc-cffi` (upstream's at the same commit, patched to build
against whichever Ultraleap Hand Tracking is installed); they are only
imported when the hands are switched on.
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

## The segment (plan 39)

`uv sync` on macOS also installs `pyobjc-framework-vision` (and
`pyobjc-framework-coreml`), which the `segment` node's person mode uses:
Apple Vision on the Neural Engine. It is imported only when a segment first
needs it, inside the worker's first job. Run `uv sync` on both Macs after
pulling this build. The first time a camera is opened macOS asks whether
the terminal may use the camera: allow it (System Settings → Privacy &
Security → Camera if you denied it); without it the node says `no frame on
channel a`. With `[segment] backend = "torch"` (or on a machine without
Vision) the fallback is torchvision's LR-ASPP: the first time it runs it
downloads its weights (`lraspp_mobilenet_v3_large`, 13 MB) into
`~/Hyperspace/weights` unless they are already there or in torch's hub
cache, as the dream's are. Nothing to set by default:

```toml
[segment]
backend = "auto"     # "auto" (Vision on macOS, else torch), "vision", "torch"
weights_dir = ""     # the torch backend's weights; "" = <library home>/weights
# device = "auto"    # the torch backend's device: "auto" is MPS when there, else CPU
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

Plug it in (USB), before or after launching. Nothing to configure: the
MIDI adapter is on by default and looks for a port whose name contains
"APC40" (the device list below names it `apc40`). The desk map is
[`ENGINEERING.md`](ENGINEERING.md) §8. At the desk:

- **Load a preset**: tap a pad in clip rows 1, 4 or 5 (the bank).
- **Save** (the two-handed save): hold **SAVE** — track 8's clip-stop
  button, the last of the row under the grid — and tap a pad. An empty
  pad gets the live look as a new preset; a filled pad gets a new preset
  too (TRIP → TRIP 2) and its old preset stays in the preset list. The
  pad blinks. Nothing is ever overwritten or trashed from the desk.
  Holding an empty pad alone also saves into it.
- **SHIFT** latches the second layer: the band strip on the device
  knobs, the hand feel and BPM on track knobs 1–5, the band scenes on
  clip rows 2–3, and the sound on the track faders (S1–S6 the bands'
  drive, S7 dynamics, S8 trim). Without SHIFT the knobs and track faders
  are the loaded preset's.
- **Points, lines, faces, rotate** are scene launch 1–4, the same with
  or without SHIFT. The **MASTER** fader is the audio drive and the
  **crossfader** the master dim, on both layers.
- **The track buttons, columns 1–6** (one per band): **select** (G7)
  opens that band's strip — the device knobs follow it under SHIFT;
  **solo** (G9) steps that band's transfer curve to the next one; **rec
  arm** (G10) resets that band. **◀ ▶** step the selected band.
- **QUANT** loads the next filled bank slot (the pad's B walks the preset
  list instead). **STOP ALL** resets every band to the selected scene; a
  second press within 8 s undoes it. **MASTER select** is overlay mode
  and **PAN** its click-through: both do nothing unless `config.toml`'s
  `[output] overlay` allows overlay.
- What each press did: the SYSTEM page's **desk log**. If the desk is
  switched off and on while the app runs it comes back in Akai's
  Generic mode (activator, solo and rec-arm latch on the device, track
  select does nothing); within a press or two the app sees a message only
  Generic mode sends and puts it back, and the desk log says so ("back in
  the app's mode"). The press that told it may be lost: press again.

To check the device without the
app: `uv run python tools/midi_probe.py`. Another port name or no MIDI at
all:

```toml
[midi]
port = "APC40"      # a substring of the port name
enabled = false     # no MIDI adapter at all
```

## The device list

Since plan 27 every device — the desk, the pad, the hands, the bridge,
a phone — is one `[[devices]]` table in `config.toml`, and one line on
the SYSTEM page (`connected`, `lost`, `off` or `error: …`). The old
`[midi]`, `[gamepad]`, `[hands]` and `[bridge]` tables still work: each
becomes its entry at launch, with a note asking for the rename. Today's
rig as a list — paste it in place of those four tables:

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
enabled = false     # true for the hand camera; the [hands] lines below go here

[[devices]]
role = "bridge"
kind = "bridge"
enabled = false     # true for FL Studio; the [bridge] lines below go here
```

The app re-reads the list about half a second after you save the file,
so a device can be added, switched on or off, or removed while it runs;
a mistake is a note and the old list stands. Every kind's keys are
[`ENGINEERING.md`](ENGINEERING.md) §5.

**A second MIDI controller** (any knob box): add an entry after the
APC40's, naming part of its port name. Then right-click a setting →
**Learn desk** and turn one of its knobs. The APC40 keeps SHIFT and
every row it had; the second desk's rows carry its name
(`cc@launch:0:21`) and the app sends it nothing.

```toml
[[devices]]
role = "launch"
kind = "midi"
profile = "generic"
port = "Launch Control"
```

**A phone** (TouchOSC or any OSC app) on the same Wi-Fi: set the app to
send to the Mac's address, port 9000, and list the addresses its faders
and buttons send. Allow Python's incoming connections when macOS asks.
Right-click a setting → **Learn phone**, move a fader.

```toml
[[devices]]
role = "phone"
kind = "osc"
port = 9000
axes = ["/1/fader1", "/1/fader2"]   # → phone:1/fader1, phone:1/fader2
hits = ["/1/push1"]                 # → phone:1/push1, a button
```

## The Ultraleap hands

1. Install **Ultraleap Hand Tracking** for macOS and check its control
   panel sees the camera. The `leap` wrapper loads its library from
   `/Applications/Ultraleap Hand Tracking.app/Contents/LeapSDK`; if it is
   installed elsewhere, set `LEAPSDK_INSTALL_LOCATION` to that `LeapSDK`
   folder in the shell that launches the app. The tracking *service* must
   be the app's; the `leapc_cffi` the app ships is not used — `uv sync`
   builds our own for 3.12, and it is found first on `sys.path`. The
   build finds whichever Gemini version is installed, 5 or 6 (the highest
   `libLeapC.<N>.dylib` in the app's `LeapSDK/lib`, else
   `libLeapC.dylib`), and stages that library inside the built package,
   so no environment variable is needed. If `uv sync` fails with "No
   LeapC library found", Hand Tracking is not installed where the build
   looks: install it, or for an SDK in an unusual place re-run `uv sync`
   with `LEAPSDK_INSTALL_LOCATION` set to its `LeapSDK` folder (or
   `LEAPC_LIB_OVERRIDE` / `LEAPC_HEADER_OVERRIDE` naming the library and
   `LeapC.h` files themselves). An `ImportError: Cannot import leapc_cffi
   … Unknown error` at hands start-up means our build is missing from the
   environment and Python fell back to the app's copy (re-run `uv sync`):
   an older Hand Tracking app ships only a Python 3.8 build of it, which
   this project's 3.12 cannot import. If you upgrade Hand Tracking (say 5
   to 6), re-run `uv sync --reinstall-package leapc-cffi` so the module is
   rebuilt against the new library.
2. Switch the hands on (on a device list, these lines go on the `leap`
   entry instead):

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
2. Switch the bridge on (on a device list, these lines go on the
   `bridge` entry instead):

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

What goes out is rows in `bindings.json` (plan 27): the first launch
with the bridge on writes its `send` list (every lane, by default) there
once, with a note, and from then on the rows say. Send any setting out
too: right-click it → **Learn sink ▸** → a port (`bridge:6 · pitch ch7`);
the ROUTING page's **sinks** section lists, switches and removes them.

The hands send to a DAW on their own port, a virtual one called
"Hyperspace Hands" unless `[hands] out` (or `out` on the hands entry)
names another; on the SYSTEM page it is the `hands-daw` line.

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
hands = true         # the ghost hands on the main projection (the default; say it on the rig)
```

The hands show on every output by default (each entry's `hands`
switch); on the party rig the projector is the main projection, so its
entry says `hands = true` outright and the OUTPUT page's switch turns
them off for a set that wants the shape alone.

The screens must be connected **before launch**: a later output whose
screen is missing is not opened, and a screen plugged in afterwards is
not used until a relaunch (Cmd+R). The OUTPUT page lists each output and
what it shows. Details and the per-output switches are
[`ENGINEERING.md`](ENGINEERING.md) §14.

## Share presets with someone

Two people (or two Macs) can have the same presets: whatever either saves
shows up on the other. A fresh library is empty: the app starts on a blank preset and an unsaved show called `untitled`, and the shared folder holds the owner's own presets. The presets live in a cloud-synced folder; each
Mac's own settings stay in its home (`~/Hyperspace`).

What is shared, in the library folder: `presets/`, `projects/` (shows),
`patches/` (plan 40: groups of GRAPH nodes saved with **save as patch…**,
spawned into any preset), the module preset folders (`band/`, `dream/`,
`view/` …; an old `fx/` is ignored, the fx module presets being retired)
and `trash/`. What stays on each Mac, in its home:
`config.toml`, `bindings.json`, `hands.json`, `windows.json`, `ui.json`
(this Mac's panel settings: the GRAPH side pane's width), `last_show`,
`stall.log`, `weights/`, `media/` (this Mac's own files; shared media go in
the library's `media/`) and `media-cache/`. Both Macs run the
same build: a preset with a GRAPH group is a newer file version (`/8`)
that an older build refuses.

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
