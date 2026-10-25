# Smoke runs, plans 28 and 30 (integration branch)

The worktree `agent-a0309a769f90bc848` was fast-forwarded to `origin/plan-28-30-integration` at
**327e646** ("Merge plan 28 N5 …"). No source file changed (`git status` is clean). No PR was opened. Machine: this Mac, 2026-10-16.
`uv sync` built the venv (uv's Python 3.14).

## Rules for every run
- **Working directory:** `hyperspace-python/`.
- **Environment:** `VIRTUAL_ENV` unset, `HYPERSPACE_FRAMES=120`.
- **Home:** `HYPERSPACE_HOME` is a scratch home under `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/<stream>/home`.
  - Its `config.toml` has no `[library]` section, so the library is the scratch home.
  - The APC40 is listed with `enabled = false`, and SYSTEM confirms `apc40 · midi · off`.
- **Untouched:** `~/Hyperspace` and `~/My Drive/Hyperspace`. No preset under `hyperspace/library/` was written.
- **Tools:** in `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/tools/`, not committed.
  - `setup.py` builds the homes.
  - `run.sh` runs a command with a 240 s cap. No run came near it.
  - `probe_D.py` and `probe_N.py` are the instrumented runs. They wrap `Renderer._draw_frame`, `Panel.draw`, `ui_graph.page` and `app.GlfwRenderer.render` without changing the source, then call `hyperspace.app.main()`.

Each stream has two runs:
1. **Gate run:** the prompt's exact command, `HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=<scratch> uv run hyperspace -ApplePersistenceIgnoreState YES`.
2. **Probe run:** the same app through the probe, with the same flag. Output 1 is read back with `target.read`. The control window is read back with `glReadPixels` after the imgui render, which is `tools/control_shots.py`'s method.

No run blocked in `glfwInit`. The `-ApplePersistenceIgnoreState YES` flag got past the alert every time.

## Summary

| Stream | Gate run | Probe run | Stall log | Verdict |
|---|---|---|---|---|
| D (plan 30), palette-hands | exit 0 | exit 0 | empty (0 bytes) | **PASS** |
| N (plan 28), party-trip + patching | exit 0 | exit 0 (three probe runs, the last one reported) | empty (0 bytes) after every run | **PASS** |

## Config (the same shape for both streams)

`/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/{D,N}/home/config.toml`:

```toml
# smoke run, stream D (plans 28/30): scratch home, no [library] section
[output]
fullscreen = false

[dream]
enabled = false

[[devices]]
role = "apc40"
kind = "midi"
port = "APC40"
enabled = false

[[devices]]
role = "pad"
kind = "gamepad"
enabled = false

[[devices]]
role = "bridge"
kind = "bridge"
enabled = false

[[devices]]
role = "leap"
kind = "hands"
tape = "synthetic.json"
out = ""
```

- **Hand tape:** `synthetic.json` comes from `uv run python tools/hands_tape.py synth <home>/synthetic.json`. It holds 60 frames over 1.97 s, both hands. `out = ""` means no virtual DAW port is created.
- **Show:** `projects/smoke.hyp.json` has `startup` set to the stream's preset, `bank = [startup]` and `session {"ghost.on": true}`. `last_show` is `smoke`.
- **Output:** one, windowed (1280×820). The control window is 960×900.

## Stream D — plan 30: the palette after the hands

### Setup
- `tests/fixtures/presets/palette-hands.json` is copied byte for byte into `D/home/presets/`.
- The show starts on `palette-hands`.
- The fixture's graph is `{"kind": "effect", "file": "palette", "after": "hands"}`, with `fx.palette.centre` 200 and `fx.palette.width` 60.

### Commands
```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/D/home uv run hyperspace -ApplePersistenceIgnoreState YES
2026-10-16 22:20:20.743 Python[35492:274566808] ApplePersistenceIgnoreState: Existing state will not be touched. New state will be written to …/org.python.python.savedState
exit=0

$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/D/home uv run python /Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/tools/probe_D.py /Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/D -ApplePersistenceIgnoreState YES
exit=0
```
Logs: `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/logs/D-gate.log`, `D-probe.log`.

### What the probe saw (frames 60 and 110 are the same)
- **Wiring:** `Wiring(hands='layer', blend='over', history='scene', draw='solid', extra=(), placed=(EffectAt(file='palette', n=1, after='hands', into=None),), …)`
- **Effects:** `fx chain=['palette']`, `fx_on=False`. The placed effect does not count as an end-of-pipeline effect.
- **Params:** `fx.palette.on=True`, `mix=1.0`, `centre=200.0`, `width=60.0`.
- **SYSTEM gpu lines (frame 118):** `palette` sits directly under `hands`, and the end node's `fx` line reads 0.00:
  ```
  gpu per node, ms (median of the last frames):
    scene       0.46
    cover       0.00
    hands       0.39
    palette     0.02
    history     0.00
    fx          0.00
    capture     0.00
    output.1    0.00
  ```
- **SYSTEM devices:** `apc40 · midi · off · 0 sources`, `pad · gamepad · off`, `bridge · bridge · off`, `leap · hands · connected · 42 sources · tape`.

#### The hands fold and the shape does not
The probe read the hands' own layer (`ghost.tex`, 1280×820, its alpha marking the hand pixels). It compared the hue of the output under the hands with the hue off them.

| Frame 110 | px | saturated share | hue median | saturated hues in 170–230° |
|---|---|---|---|---|
| The hands' layer itself, before the fold | 27 466 | 0.51 | **11°** (pink) | 0.00 |
| Output under the hands, after the fold | 27 466 | 0.39 | **174°** (cyan) | **1.00** |
| Output off the hands (the shape) | 1 022 134 | 0.03 | 0° | 0.00 (the shape's lines are white, with red vertices) |

Frame 60 shows the same: under the hands 0.99 in-band, hue 174; off the hands 0.00.

By eye (`render-110.png`):
- The right hand, pink on the layer, is teal in the output.
- The left hand is pale blue-white on the layer and stays a grey-blue.
- The shape is unchanged: white lines with red vertex dots.

### Frames
- `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/D/render-60.png` (render output)
- `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/D/render-110.png` (render output)
- `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/D/system-118.png` (SYSTEM page, control window 960×900)
- Extra: `ghost-layer-60.png` and `ghost-layer-110.png` in the same folder. These are the hands' layer before the fold, kept for comparison.

### Stall log
`D/home/stall.log` is 0 bytes after both runs.

### Verdict: PASS
- The hands fold into the 170–230° slice, and the shape keeps its colours.
- SYSTEM shows `palette` under `hands`, with `fx 0.00`.
- The stall log is empty, and both runs exit 0.

## Stream N — plan 28: patching on the live app

### Setup
- The show starts on the factory preset `party-trip`. It is not copied; it resolves from the factory library and displays as "TRIP".
- `N/home/presets/` stays empty.

### What the probe did, from the live draw loop
`p` is the `Panel.draw` count. Each frame's `router.modulate` runs before the panel draws.

- **Audio:** every frame, the analyser is fed a synthetic kick, sweep and hats (`control_shots --bands`' signal), with `audio.on = True`, so `lane:0` moves.
- **p5, the LFO route:**
  - `reg["lfo.2.depth"].set(0.5)`: party-trip has LFO 2's depth at 1.0, where any upward push would clip.
  - `router.table.add(Binding("lfo:0", "lfo.2.depth", "push", 1.0))`, through the table's method.
- **p8, the modifiers:**
  - `ui_routing.add_modifier(panel, "smooth")` → `mod.1`, then `ui_routing.set_modifier_input(panel, "mod.1", 0, "hand:right.energy")`.
  - `ui_routing.add_modifier(panel, "combine", how=1.0)` (mul) → `mod.2`, then `set_modifier_input(.., "mod.2", 0, "mod:1")` and `set_modifier_input(.., "mod.2", 1, "lane:0")`.
  - `ui_routing.add_route(panel, "fx.acid.mix", source="mod:2", depth=0.5)`.
  - Result: `[('mod.1','smooth',('hand:right.energy',),…), ('mod.2','combine',('mod:1','lane:0'),{'how':1.0,'balance':0.5})]`.
- **p10:** the GRAPH page opens (`reg["ui.page"]`).
- **p30, the cable:** `ui_graph.connect(panel, "out:mod:1", "mod:view.speed")` (graphview.Edit). It returns `Binding(source='mod:1', target='view.speed', op='position', value=1.0, …)`, and `table.owner("view.speed")` is that row.
- **p95:** shot of the GRAPH page.
- **p100:** the ROUTING page, with its filter field set to "mod". Shot at p106.
- **p108:** the SYSTEM page, with the filter cleared. Shot at p118.

### Commands
```
$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/N/home uv run hyperspace -ApplePersistenceIgnoreState YES
2026-10-16 22:21:37.970 Python[39078:274581555] ApplePersistenceIgnoreState: Existing state will not be touched. …
exit=0

$ HYPERSPACE_FRAMES=120 HYPERSPACE_HOME=/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/N/home uv run python /Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/tools/probe_N.py /Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/N -ApplePersistenceIgnoreState YES
exit=0
```
Logs: `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/logs/N-gate.log`, `N-probe.log`. The per-frame values are in `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/N/rows.json`.

### The LFO-on-LFO lands the same frame
The probe read LFO 1's output, the `lfo.2.depth` param and the depth LFO 2 stepped with, every frame from p4.

| p | LFO 1 out | lfo.2.depth (param) | LFO 2's own depth | LFO 2 out |
|---|---|---|---|---|
| 5 (route added after this frame's pass) | 0.3103 | 0.5000 | 0.5000 | 0.8859 |
| 6 | 0.3183 | **0.3183** = 0.5 + (0.3183 − 0.5) | 0.3183 | 0.6282 |
| 7 | 0.3282 | **0.3282** | 0.3282 | 0.6371 |

- **This frame's input:** on all 115 frames from p6 to p120, the depth equals base + 1.0·(*this frame's* LFO 1 − 0.5).
- **Same step:** LFO 2 stepped with that same depth on every one of those frames.
- **No lag:** the first frame after the row lands already uses it. LFO 2's output drops from 0.886 to 0.628 on p6.
- **Lanes match:** `router.feeds["lfo"]` equals the LFOs' outputs on every frame.
- **Ranges:** LFO 1 ran 0.30–0.70 (its depth is owned by `hand:left.y`). The depth followed it over 0.30–0.70, and LFO 2 ran 0.20–0.80.

### The modifiers' lanes move

| Lane | Range over p9–p120 | Distinct values |
|---|---|---|
| `hand:right.energy` | 0.014 – 0.518 | 115 |
| `mod.1` (smooth) | 0.019 – 0.434 | 112 |
| `lane:0` | 0.326 – 0.455 | 115 |
| `mod.2` (combine, mul) | 0.008 – 0.188 | 112 |

- `mod.1` follows the hand, smoothed.
- `mod.2` stays at or below `mod.1 × lane:0`, as a multiply should.
- `fx.acid.mix` is marked modulated from p9 on.

### The cable shows on ROUTING too
- At p106, `table.routes()` holds `Binding('mod:1' → 'view.speed', op='position')`, along with `mod:2 → fx.acid.mix` and `lfo:0 → lfo.2.depth`.
- `routing-106.png` (filter "mod", "10 of 182 rows") shows both rows:
  - `mod 1 smooth → view.speed`, with the `pos` chip lit and +1.00;
  - `mod 2 comb → fx.acid.mix`, push +0.50.
- The MODIFIERS strip starts below them.
- The count line reads "24 routes" with no filter: party-trip's 21 rows plus 3.

### SYSTEM numbers (frame 118, control window 960×900, CONTROLS panel about 540 px wide)
- **The panel line:** `graph page: 2.78 ms median  (55 nodes, 239 cables)`.
- **The probe's own timing** of `ui_graph.page`, 90 draws: median **2.74 ms**, p90 2.93 ms, max 13.82 ms. The max is the first draw after the page opened.
- **The two earlier probe runs**, same steps: 2.77 ms and 2.90 ms median.
- **GPU lines:** scene 0.68, cover 0.00, hands 0.68, history 0.00, plasma 0.00, kaleido 0.00, zoomblur 0.37, huecycle 0.02, fx 0.00, capture 0.00, output.1 0.04.
- **Devices:** apc40 off, pad off, bridge off, leap connected · 42 sources · tape.

### Frames
- `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/N/graph-95.png` (the GRAPH page: "55 nodes · 239 cables · 50 live", "patched only")
- `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/N/system-118.png` (SYSTEM, with the `graph page:` line)
- Extra: `/Users/dallman/.claude/jobs/7e5d0255/tmp/smoke/N/routing-106.png` (ROUTING, filtered to "mod")

### Stall log
`N/home/stall.log` is 0 bytes after the gate run and after each of the three probe runs.

### Verdict: PASS
- The LFO-on-LFO lands the same frame.
- Both modifiers' lanes move.
- The canvas cable is a ROUTING row.
- The stall log is empty, and every run exits 0.
- The GRAPH page draws in 2.78 ms (median) at 960×900.

## Surprises and notes
1. **`lfo:1` versus `lfo:0`.** The dispatch's route `lfo:1 → lfo.2.depth` would be LFO 2 driving its own depth: lfo lanes are 0-based, and `router.labels["lfo"][1] == "LFO 2"`. I used `lfo:0` (LFO 1) → `lfo.2.depth`, as in `tests/test_lfo.py::test_an_lfo_owning_another_lfos_depth_changes_its_output_the_same_frame`. That is "an LFO owning another LFO's depth".
2. **party-trip's `lfo.2.depth` is 1.0**, so a push from LFO 1 above its 0.5 rest clips. The probe set the base to 0.5 at p5 so the ride shows both ways. This was in memory only; no preset was saved.
3. **`fx.acid.mix` stays at 1.0 although it is modulated.** Its base is already the top of its range, and a push from a lane resting at 0 can only go up, so it clips. Acid is also not in party-trip's chain. The pass criterion here is the modifier lanes, which move. To see the route change the value, the base would need to be below 1.
4. **The canvas cable is a `position` row, not a push.** `out:mod:1 → mod:view.speed` made `op='position', value=1.0`. That follows N3's convention for a `mod` cable (learn's row table), so `view.speed` is now owned outright by `mod.1`.
5. **The left hand barely changes colour (stream D).** The ghost hands' default colours are low-saturation. The left hand is already a pale blue near the band, so it stays a grey-blue; the pink right hand turns teal. This is D1's concern 5 ("grey-teal, not vivid blue") and is for the owner's eye.
6. **The fold lands at the low edge of the slice.** Under the hands the hue median is 174°, inside 170–230° but near its edge. Every saturated hand pixel is in the slice.
7. **The GRAPH screenshot does not single out the new cable.** At this panel width the canvas shows the apc40 column and the LFO nodes, and its 239 cables, so the `mod.1 → view.speed` cable is not distinguishable in the image. Its presence is shown by the table row and the ROUTING shot.
8. **The order of pages differs from the dispatch.** The dispatch says the GRAPH page is drawn "for the rest of the run". Here it was drawn p10–p99, 90 draws, so that the ROUTING (p100–107) and SYSTEM (p108–120) shots fit inside 120 frames. The SYSTEM line keeps the GRAPH page's median after the page closes.
9. **Probe runs only: duplicate-class warnings at startup.** objc printed `Class GLFWHelper is implemented in both …/glfw/libglfw.3.dylib and …/imgui_bundle/libglfw.3.dylib` (5 lines). This comes from the probe importing `glfw` and `OpenGL` before the app. The gate runs printed only the ApplePersistence line. Nothing misbehaved.
10. **What did not appear:** no dialog, no alert banner, no error line, no config note in either run. The hands device read `connected · 42 sources · tape` from frame 1.
