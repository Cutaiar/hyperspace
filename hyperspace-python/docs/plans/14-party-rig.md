# Plan 14 — The party rig: an opaque window, one show, a readable desk

**From the owner's first session at the machine after plan 13 (2026-09-29).**
Plan 13 made the preset one file and the desk two layers; running it for
real showed a rig that is still built for a developer, not a party. This
plan fixes what blocks the show (a see-through window, an unexplained
freeze), makes the party show the thing the rig opens on, and makes the
desk readable at a glance. Investigated first, without code changes, on
main 69ae578 (scripts and screenshots in the job's `tmp/inv/`); every
finding below cites what was measured.

The owner's to-do list at the machine is §6. The owner's decisions are §4
(`docs/DECISION-REGISTER.md` rows 21–25), **all answered on 2026-09-29**.

## 1. What the owner hit, and what it is

| # | The owner saw | What it is | Evidence |
|---|---|---|---|
| 1 | The desktop shows through the shape. The render is for a **Pepper's Ghost** illusion: it must be opaque black. | The render window is created with a transparent framebuffer in every mode (`app._windows`, since the overlay commit 4317cc6), and `view.cut_through` (default on, PR #26) blends alpha down wherever faces or faint lines draw — even in plain window mode on an opaque ground. The APC40's MASTER select and the `T` key float the window into overlay (see-through, click-through) with one press. | Offscreen, window mode: TUMBLE 23 % of pixels below alpha 255 (lowest 93), FACES 70 %, TRIP 65 %. `tests/test_lookback.py::test_cut_through_toggle_on_an_opaque_ground` pins the bug. |
| 2 | Loading a party preset freezes — the owner, 2026-09-29: **the render stopped drawing while the panel kept working**. | **Not reproduced** in ~20 runs of the real app: the owner's home copied (and a pre-migration copy), the real APC40 and Leap connected, fake moving hands, the live mic, `[dream] enabled` without torch; loads by bank click, F-key, APC40 clip row 1, strip, and project load ▾ cold. Every load 7–9 ms, worst frame ~90 ms; GPU cost at 4K with MSAA and every heavy preset 1–4 ms. Not yet tried: the Leap service stopped with `[hands] enabled`, real hands entering and leaving, a real fullscreen / projector switch. | `run_*.txt`; faulthandler dumps showed the main thread in normal code |
| 3 | The PRESETS page is confusing: "Default", "Startup", Party hidden in the project list. "I don't care about the default project — this is a party device." | The project name is covered by an unlabelled startup combo (a layout bug: only "de" shows); the bank chips show 1–8 with names only in a tooltip; "startup" takes effect only on save; the rig always opens the project named `default` and forgets `party`; your migrated `default` starts on `MIGRATED` with the house moods behind it. | `panel_presets_*.png` |
| 4 | Are the FX tab's effects in the presets? | Mostly no. Of 12 effects only 4 (plasma, kaleido, zoomblur, huecycle) are in a party preset (TRIP); acid is in `hands-fx`, which is in no bank; warp, wobble, doublevision, deconverge, fractals, glimmer, tripcolour are in no preset. `hands-pinch`, `lfo-breathe` and your `MIGRATED` route into `fx.mix` / acid / kaleido with the effects off (dead rows). The `library/fx` module presets (acid, mandala, noita-*) are referenced by nothing. A preset load resets every effect not in the preset (D2), so FX-page experiments vanish on an F-key. | `fx_cov.py` |
| 5 | The dream says "no worker"; it should be on by default. | The dream worker needs **torch**, an optional extra (`uv sync --extra dream`), which is not installed; plain `uv sync` removes it. The failure goes only to stderr; README and SETUP never mention the extra. With no worker, the look-back shows raw echoes only, and WAKE's two dream rows do nothing. | `app._open_dream`, `ui_lookback._worker_status`, `pyproject.toml` |
| 6 | The echoes are hard to read. | Echo decay and cadence are **per frame**: at WAKE's settings the oldest echo weighs 0.3·0.93³² ≈ 0.03, and at 120 Hz the trail lasts about 0.1 s; faces with `occlude 1` hide the wake. A tuned set (24 echoes every 4, decay 0.985, mix 0.7, darken 0, occlude 0.3, faces off, points on) reads clearly. | `echo_wake_301.png` vs `echo_legible_601.png` |
| 7 | The APC40 is hard to follow; Akai's names ("track", "device", "clip") mean nothing here. Wanted: a diagram of the desk on screen, and on the ROUTING page a glyph per row to find on it. | There is no layout data; names come from `apc40.control_name`. A glyph scheme was checked against all 137 controls and all 920 MIDI rows shipped (unique, ≤ 5 characters). | `apc_glyphs.py` |

Also found in the first five minutes: dirty dots lit on VIEW / CAMERA /
LOOKBACK / FX / LFO right after a factory preset loads (they compare
against fresh defaults); the factory project shows "unsaved" the moment it
opens; the ROUTING head says "LAYER PRESET" beside save; FIELD's left hand
can pan the shape off screen at the extremes (a number for the eye check).

## 2. Work packages

Order is the order of what blocks the show.

| WP | What | Size | Needs |
|---|---|---|---|
| 1 | **Opaque window** (cut-through only in overlay; every factory preset renders at alpha 255 in window mode, pinned by a GL test); **the render watchdog** — a `renderer.draw` error (which the frame loop swallows, so the render keeps its last image while the panel lives: the owner's freeze exactly) or a render window that stops presenting is logged with its traceback to `<home>/stall.log` and shown as a banner; plus a whole-loop stall dump and `kill -USR1`; **the dream in the app** (decision 23 (a): torch an ordinary dependency, the worker on by default). | S | — (in progress, PR to come) |
| 2 | **Overlay behind config** (decision 21): the transparent framebuffer only when `[output] overlay = true`; MASTER select and `T` do nothing otherwise. | S | decision 21 |
| 3 | **Party is the show** (decision 22): the rig opens on the party project; the house moods become a project named `house`; the last project opened is remembered; your `MIGRATED` stays a preset in the list. | S | decision 22 |
| 4 | **The PRESETS page for a party**: the show's name visible; eight named buttons, the live one lit; "starts on" labelled and saved when set; save / save as; modules and projects folded under "more"; one word per thing (§3); the dirty dots compare against the loaded preset, not fresh defaults; the ROUTING head's words. | M | WP3 |
| 5 | **The effects in the show** (decision 24): three new party presets on F6–F8, each an effect family with hand routes and a device-knob desk like TRIP; the dead `fx.mix` / acid rows fixed or removed; a test that every effect is on in at least one factory preset (or on an allow-list) and no factory route drives an effect that is off; a note on the FX page that a preset load resets the stack. | S | decision 24 |
| 6 | **Dream and echoes** (decision 23): the dream on by default as decided; a TRACER preset with the legible echo set; WAKE re-tuned; echo decay and cadence per second, not per frame, so a 120 Hz screen looks like a 60 Hz one. | S + M | decision 23 |
| 7 | **The desk, drawn** (decision 25): `apc40.LAYOUT` (every control's position, kind and glyph), the glyph on every ROUTING desk and session row and in every Learn message, and an APC40 diagram above the cheat sheet — the up layer's mapped controls lit, the rest dark, ⇧ lit on the global layer, a hover naming the param. | S + M | decision 25 |
| 8 | **The freeze, found**: a fuzz of every value the party presets reach, through `renderer.draw`, looking for the exception the frame loop hides (in progress); fix it with a test on that road; else the render watchdog's log from the machine. | S–M | the fuzz or a stall.log |
| 9 | **Docs and hand checks**: every hand check this plan changes (§6's list), the plan's "As built". | S | last |

## 3. One word per thing

The page and the docs use these and nothing else:

- **show** — what the panel today calls a project: a bank of eight presets
  and what it starts on. (The file stays `*.hyp.json`; the word "project"
  and "session" stay in the code.)
- **preset** — one performance moment (plan 13's preset). F1–F8 load one.
- **starts on** — the preset the show opens with (today "startup").
- **module preset** — one group's values (a strip on the PRESETS page, under "more").
- **factory** — shipped with the app; saving one makes your copy.

## 4. Decisions for the owner (register rows 21–25)

| # | Decision | Recommendation |
|---|---|---|
| 21 | Does overlay mode (the render floating see-through over the desktop) survive? | **answered as recommended**: (a) keep it behind a config key, off by default; the rig can never show through unless asked |
| 22 | How does the rig become "the party device"? | **answered as recommended**: the party show is the factory default and what the rig opens on; the house moods become a `house` show; the last show opened is remembered |
| 23 | "Dream on by default": install torch always, or keep it optional and on? | **answered (a)**: torch is part of the app — ordinary dependencies, `uv sync` installs them, the worker on by default |
| 24 | Which effects go in the party show's F6–F8? | **answered as recommended**: ACID, MANDALA and NOITA (the three module presets already tuned), each with hands and eight device knobs |
| 25 | The desk's glyphs and diagram | **answered as recommended**: K1–K8 track knobs, D1–D8 device knobs, S1–S8 faders, SM master, X crossfader, C cue, G row·column for the button field, B1–B22 other buttons, ⇧ SHIFT; the diagram shows the layer that is up, above the cheat sheet |

## 5. What this plan does not change

Plan 13's model stands: a preset load replaces every performance value and
route (D2); the desk's two layers (D4–D8); the session / performance split
(D9). Nothing here makes a module preset chain-load (D3).

## 6. The owner's to-do list at the machine

Every item is a check in `docs/plans/11-hand-checks.md` (commands, pass,
fail, where a fail points). Ordered so each device is plugged in once. The
numbers marked † change with this plan and are re-checked after the WP
named; run the rest now. Log a fail as a dated row in
`docs/AUDIT-2026-09.md` with the check number.

**Before anything:** `cp -R ~/Hyperspace ~/Hyperspace-before-13` (already
migrated: keep the copy anyway). If the app freezes at any point, note
what you did, run `kill -USR1 $(pgrep -f "bin/hyperspace")` from another
terminal (after WP1), and keep `~/Hyperspace/stall.log`.

**1. Laptop alone — about 45 minutes**
- [ ] 1 — the windowed smoke (the check that would have caught the first-frame crash, fixed in PR #71).
- [ ] 3 — first real audio capture from the mic or the interface.
- [ ] 2, 4, 5, 7, 8 — config notes, pages fit (†WP4, WP7), effects by eye (†WP5), the LFO page and B / ⇧B, hot reload.
- [ ] 6 † — cut-through, rewritten by WP1: window and fullscreen opaque whatever the toggle.
- [ ] 9 † — the dream by eye: needs `uv sync --extra dream` first (WP1's setup note) and WP6's echoes.
- [ ] 33 — the migration: `MIGRATED` holds your routes and learned knob; the backups exist.
- [ ] 38, 40 † — a load replaces everything (a tapped BPM survives); the show opens on its "starts on" preset (†WP3, WP4).
- [ ] 44 † — the stall log: `kill -USR1` writes a dump (WP1).

**2. APC40 plugged in — about 35 minutes**
- [ ] 31 **first** — the knobs take the host's value. If it fails, stop: the desk needs pickup on the knobs too.
- [ ] 10–12 — mode, rings, pickup, TAP / NUDGE / METRONOME / QUANT.
- [ ] 34 — SHIFT latches and lights; a button held across SHIFT fires once.
- [ ] 35 — knobs jump on a layer switch, faders pick up.
- [ ] 36 — unmapped controls dark and dead.
- [ ] 37 — Learn refuses faders and the global layer; a learn marks the preset unsaved, writes no file.
- [ ] 39 — `lfo-breathe`, device knob 1: brighter and slower together.
- [ ] 45 † — the on-screen desk diagram matches the device, control by control; a ROUTING row's glyph is where the diagram says (WP7).

**3. Camera and box — about 50 minutes, APC40 still in**
- [ ] 13–18 — the probe, the angle signs, calibration, the default feel, independence, the pinch threshold.
- [ ] 19–25 — Learn prompts, pinch-gated rows, a knob on a hand-owned param, a hand leaving the box, latency.
- [ ] 42 — reorder `[hands] dofs`: the presets still drive the same axes.
- [ ] Freeze hunt (WP8): hands in and out of the box while pressing F1–F5; the Leap service stopped with `[hands] enabled`.

**4. Projector — about 25 minutes**
- [ ] 43 † — **Pepper's Ghost: an opaque black window**, fullscreen on the projector, faces on, a bright desktop behind: nothing shows through (WP1, WP2).
- [ ] 26 † — output monitor, fullscreen, follow window (overlay behind config after WP2).
- [ ] 41 (and 32) † — the party show on F1–F8 by eye: the five, the three effect presets (WP5), WAKE's and TRIP's device knobs, FIELD's pan at the extremes.

**5. IAC + FL Studio — about 15 minutes**
- [ ] 27–29 — the bridge, `ext:` lanes, the hands' DAW port.

**6. Back on the laptop — 3 minutes**
- [ ] 30 — backups before every rewrite, never over yours.

**Not covered yet:** the Xbox gamepad (no check; it drives keys and camera
rows through the same table) — WP9 adds one.

## 7. As built

Filled as the work packages land.
