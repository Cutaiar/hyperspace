# Hyperspace (Python)

The active re-platform of Hyperspace: a real-time 4D polytope visualizer with
audio-reactive rotation. Replaces the original single-file
[`hyperspace-web/`](../hyperspace-web/) version, which is preserved for
reference and used as the renderer test oracle.

## Quickstart

Requires macOS with [`uv`](https://docs.astral.sh/uv/) installed
(`brew install uv`). Full prerequisite checklist — including audio routing,
DJ-link, and DAW-bridge tiers — is in [`docs/SETUP.md`](docs/SETUP.md).

```bash
uv sync
uv run pytest          # 208 tests, ~5s
uv run hyperspace      # opens the render window
```

## Layout

- `hyperspace/` — the package: `app`, `render`, `audio`, `geometry`, `bands`,
  `control`, `params` (the parameter registry every input path drives),
  `presets`, `ui`, `midi` + `apc40` (controller adapter and device profile),
  `config`, `hotreload`, `gamepad`, `analysis`, `offline`, and `shaders/`.
- `tests/` — pytest suite plus committed `golden/` traces recorded from
  `hyperspace-web/hyperspace.html` (the oracle for renderer parity).
- `tools/` — `record_golden.py` (re-records goldens via Playwright against the
  HTML oracle), `compare_render.py` (side-by-side diff), `gen_test_audio.py`,
  `midi_probe.py` (echoes what a controller sends; lights an APC40).
- `docs/` — [`BLUEPRINT.md`](docs/BLUEPRINT.md) is the design north star,
  [`ENGINEERING.md`](docs/ENGINEERING.md) is the working reference,
  [`CHECKPOINT.md`](docs/CHECKPOINT.md) is the current pick-up list, and
  [`plans/`](docs/plans/) breaks the re-platform into stages.

## Re-recording golden traces

The `record_golden.py` and `compare_render.py` tools drive
`hyperspace-web/hyperspace.html` in headless Chromium. To run them:

```bash
uv run playwright install chromium   # one-time, ~150 MB
uv run python tools/record_golden.py
```

Consuming committed traces (which `pytest` does) needs neither Playwright nor
Chromium.

## Controls and MIDI

Everything the panel can set is a named parameter in `hyperspace/params.py`
(`view.bright`, `band.2.atk`, `theme.load.0`, …). Keys, the gamepad and MIDI
are all binding tables over that registry — `KEYMAP`/`PADMAP` in `app.py`,
and `midi_map.json` for a controller — so a value moved from any of them
shows on the panel the next frame. Press `?` in the app for the cheat sheet.

Plug in an Akai APC40 and it is picked up on launch (and on reconnect):
the eight device knobs are the open band strip, the track knobs are the
view faders, channel faders are per-band output drive, the clip grid holds
themes, scenes and shapes, and every LED and knob ring tracks the engine.
The full default layout is at the bottom of `hyperspace/apc40.py`.

To rebind anything: right-click the control in the panel → **Learn MIDI**,
then move a knob or press a button. Bindings persist in `midi_map.json`
next to `presets.json` (delete it to get the defaults back). Knobs use soft
pickup — after a band switch or a theme load a knob does nothing until it
sweeps through the current value. An optional `config.toml` names the port,
profile and map file, or disables the adapter (see `hyperspace/config.py`).

## Overlay mode

Press `T` (or the APC40's master-select button) and the window drops its
frame, covers the screen, sits above everything — including another app's
fullscreen video on macOS — and clears to see-through, so only the shape is
drawn over what is behind it. Clicks pass straight through to the window
underneath, so you can run the video behind as normal; that also means the
overlay never takes focus and the keyboard stops reaching it. To get clicks
and keys back, ⌘-Tab to Hyperspace and press `G` (or hit the APC40's pan
button); `G` again hands them back. The crossfader fades the ground from
see-through to black.
The panel's Overlay section holds the same params (`overlay.on`,
`overlay.passthrough`, `overlay.bg`, `overlay.alpha`, `overlay.monitor`),
all learnable. `[overlay] on_start = true` in `config.toml` launches into it.
