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
uv run hyperspace      # opens the render window and the control window
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
(`view.bright`, `band.2.atk`, `theme.load.0`, …). Keys, the gamepad, MIDI
and the analyzer's lanes are one binding table over that registry
(`hyperspace/routing.py`, persisted as `bindings.json`; factory default in
`hyperspace/library/bindings/`) — so a value moved from any of them shows
on the panel the next frame, and any audio band can modulate any param.
Press `?` in the app for the cheat sheet.

Plug in an Akai APC40 and it is picked up on launch (and on reconnect):
the eight device knobs are the open band strip, the track knobs are the
view faders, channel faders are per-band output drive, the clip grid holds
themes, scenes and shapes, and every LED and knob ring tracks the engine.
The full default layout is at the bottom of `hyperspace/apc40.py`.

To rebind anything: right-click the control in the panel → **Learn MIDI**,
then move a knob or press a button. Bindings persist in `bindings.json`
in the library home (delete it to get the defaults back; an older
`midi_map.json` there is migrated into it on first run). Knobs use soft
pickup — after a band switch or a theme load a knob does nothing until it
sweeps through the current value. An optional `config.toml` names the port
and profile, or disables the adapter (see `hyperspace/config.py`); MIDI
and the gamepad are the two adapters on by default (`[gamepad] enabled =
false` stops polling for a pad), the bridge, dream and hands are off.

## Presets, projects and the library

Every registry group (view, camera, band…) has a preset library, and a
*project* (`*.hyp.json`) saves everything at once, including the F1–F8
theme bank. Factory presets live in `hyperspace/library/`; yours go in
`$HYPERSPACE_HOME` (default `~/Hyperspace`) in the same tree, with
`projects/`, `config.toml` and `midi_map.json` next to them — a user file
shadows a factory file of the same name. The files are plain JSON: edit one
in a text editor while the app runs and the loaded preset updates in place.
See `hyperspace/library.py` for the formats and the API the panel uses.

The panel is a rail of pages — Output · View · Faces · Bitmap · Camera ·
Audio · Analyzer · Presets · System — and every section that is a
registry group carries its preset strip: `◀ name ▶`, save, save-as,
reset, and a red dot once the group has moved off its preset. The
Presets page holds the project row (save / save-as / load / new) and the
F1–F8 theme bank. A param a lane is driving shows its *setting* as the
handle and the *effective* value as a red hairline.

## Two windows: output and controls

The *render* window is pure output — what goes on the projector or TV —
and the *control* window holds the panel, the cheat sheet and the
hot-reload notices. Keys work from either; the mouse orbits, pans and zooms
in the render window. The panel's Output section (`output.monitor`,
`output.fullscreen`, `output.overlay`, `output.passthrough`, `output.bg`,
`output.alpha`, all learnable) says where the render window goes:
fullscreen on a chosen screen, or overlay mode.

**Overlay mode.** Press `T` (or the APC40's master-select button) and the
render window drops its frame, covers the screen, sits above everything —
including another app's fullscreen video on macOS — and clears to
see-through, so only the shape is drawn over what is behind it. Clicks pass
straight through to the window underneath, so you can run the video behind
as normal; that also means the render window never takes focus — keys keep
working from the control window, and `G` (or the APC40's pan button) takes
clicks back for orbiting. The crossfader fades the ground from see-through
to black. The pre-split `overlay.*` ids remain as aliases, so old MIDI maps
keep working. `[output] fullscreen = true` or `on_start = true` (overlay) in
`config.toml` launches straight into a mode; `monitor = 1` picks the screen
(`-1`, the default, follows the window — the SYSTEM page says "follow window").
An older `[overlay]` section is read as the same thing (with a note asking
for the rename); the keys are documented in `hyperspace/config.py`.
