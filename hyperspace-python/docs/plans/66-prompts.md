# Plan 66: the cloud-agent prompts

One prompt per item in [`66-post-install.md`](66-post-install.md). Paste the block under an item into a new Claude Code cloud session on the `hyperspace` repo. Wave 1 (67–73) can all go at once. Wave 2 (74, 75) waits for decisions D1 and D2 and for 70 to merge.

Every prompt starts the same way, so an agent reads the plan before it builds.

---

## 67. Mandelbrot fixes

```
You are building plan 67 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §4 builder brief. Your row in §1 is 67 (files, rows 902–909, checks 699–706, group EB).

Plan 63 (PR #462) built the Mandelbrot node: mandel.glsl plus its Python half mandel.py, through @hook.
Read docs/plans/63-mandelbrot.md first. Making patches with it on the rig (an M3 Max) turned up four problems.
Fix them in this order:

1. Black unless a picture is wired in. With nothing wired into mandel.image the frame is black, with no note,
   though the node paints the whole frame and ignores its input. Make it render with no input. Add a test.
2. "Inside coloured" is wrong under perturbation. At the seahorse point, zoom 9e6 and Steps 6000, the inside
   is flat grey with rectangular blocks; at 1e6 it shows odd flat bands and discs. In the direct tier it is
   clean. Find the cause: likely the periodicity time, or the tile fill, mixed with rebasing. Fix it in the
   shader and its numpy twin, with a test against the float64 oracle.
3. The c and z0 drives are far too sensitive on slices where their term isn't the screen's axis. On a Julia
   slice, one view height is about 1.8 units of c at zoom 1.7, and a 0.03 change in c tears the set apart, so
   routes needed depths around 0.01. Make an off-screen term's drive rate scale with something that matches
   how the picture responds (for example the view width times a per-term factor, or a measured sensitivity).
   Record the choice as a register row. Keep pan and dive as they are.
4. Perturbation cost. Rig numbers, Size 810, Steps 2000:
   - direct at 1.5e4: 4 ms;
   - perturbation at 1.5e4: 19 ms;
   - at 4e5: 38 ms;
   - at 1e7: 80 ms;
   - skip black at 3e6: 72 ms on, 59 ms off. It makes perturbation slower.
   Find why. Candidates: reference-orbit texture fetches per iteration, the Horner binomial at p=2 (use the
   closed form there), rebasing frequency, and the tile pre-passes' overhead under perturbation. Reduce what
   you can. Make skip black turn itself off where it costs more. Extend tools/mandel_bench.py so the owner
   can confirm on the rig. Series approximation (skipping the first iterations for the whole screen) is in
   scope if you have time; mark it a stretch.

Not in scope: the deep tier (mpmath), floatexp, the Misiurewicz loop, fractional p.
The library's three Mandelbrot patches are in 5-zooms-nov/mandelbrot/ in the owner's Drive library.
You can't reach them. Their behaviour is described above.
```

## 68. An endless, centred fractal dive

```
You are building plan 68 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §4 builder brief. Your row in §1 is 68 (files, rows 910–917, checks 707–712, group EC).

Plan 64 (PR #460) built recursive geometry. Read docs/plans/64-recursive-geometry.md and
64-depth-dependent-grab.md, and fractal.py (Dive, step, frame). Making loadable patches turned up two problems:

1. A plain zoom dive drifts toward an edge. Over a few levels, part of the screen goes empty: the re-root
   picks a child and the view zooms about the rooted cell's centre, not about the middle of the screen.
   Decision D4 (recommended, build it): zoom about the screen centre, so the point under the centre stays
   put through every re-root and the screen stays full. A grabbed or panned view must still re-root
   correctly, and no re-root may jump (keep the 0.000 px tests).
2. There is no endless dive. A saw LFO on camera.zoom jumps at each wrap, so patches dive in and back out
   on a triangle. Add a dive-rate control: a velocity on the zoom in levels per second, signed, integrated
   in float64 like the Mandelbrot's drives. Route an LFO, a hand or a knob to it for a dive that never ends.
   Decide where it lives (a camera param, or a fractal-only one) and record it as a register row. It must
   save in a loadable patch like any param.

Tests: a long dive (hundreds of levels) at a fixed rate stays centred and never jumps; a negative rate
climbs back out to the whole shape; the 3D and 4D fractals both work.
Render a before/after video pair of a Menger sponge dive with drive-the-app and commit it under
docs/plans/assets/68-fractal-dive/.
```

## 69. Control widgets

```
You are building plan 69 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §4 builder brief. Your row in §1 is 69 (files, rows 918–927, checks 713–722, group ED).

Three control improvements from the install, for the panel's sliders (ui_fields.py and the fader drawing
in ui.py):

1. Tick marks on stepped controls. Integer params already snap (slider_int, ui.py around line 1894) but show
   no steps. Draw one tick per position when it fits, for example Zoom burst's Taps and Kaleidoscope's
   Segments. Thin them when there are too many.
2. Two classes of continuous param, drawn differently:
   - unipolar: 0..1-like, rests at 0 or the top, filled from the left;
   - bipolar: symmetric, neutral at 0, filled from the centre with a centre detent.
   Infer the class (lo < 0 < hi with a 0 default means bipolar). Allow an explicit marker on an effect's
   @param line (`bipolar` or `unipolar`; extend fx.py's parse). Also give neutral-at-1 multipliers a detent
   at 1 (Kaleidoscope zoom, Blocks aspect, Hue cycle saturation). One abstraction draws all of these.
3. XY pads and an XYZ volume, modelled on the X/Y pads in Image-Line's Harmor and FL Studio.
   - A compound control replaces a pair of sliders: a square you click or drag on to set X and Y, plus a
     small knob per axis.
   - Declared in an effect file with a new directive: `// @pair u_cx u_cy "Centre"`, and
     `// @volume u_cx u_cy u_amount "Burst"` for three. No param is renamed or re-keyed, so saved patches,
     routes and learn are untouched.
   - Decision D3 (recommended, build it): add @pair to Prism, Wave and Zoom burst (cx/cy) and to Wave Table
     (offset_x/offset_y), and @volume to Zoom burst (cx, cy, amount).
   - Routes and learn still address each param on its own. The pad shows modulation as it moves.
   - It must work on a trackpad on stage: big, with a clear dot.

Tests with tests/ui_driver.py: a drag on a pad sets both params; a bipolar fader rests centred; ticks
count right. Capture screens with drive-the-app and commit them under docs/plans/assets/69-control-widgets/.
```

## 70. Save and load live

```
You are building plan 70 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §4 builder brief. Your row in §1 is 70 (files, rows 928–933, checks 723–728, group EE).

Two pains from the install, on a trackpad during a live set:

1. Saving takes 3–4 clicks, and the meta controller can load a patch but not save one. Put a Save as button
   right next to the meta controller's Load button. One press saves the current state as a new loadable
   patch with a fresh name (follow how START-hold on the pad does preset.save_new), in the folder of the
   patch that was loaded (the library has era folders now, e.g. 4-install-nov/distort/). Show the new name
   for a moment. Never overwrite. Also expose it as a param or action a desk pad or pad button can be
   learned to.
2. The playlist UI doesn't scroll: add too many entries and they run off the edge of the screen. Make it
   scroll, keep the playing entry in view, and keep the rows big enough for a trackpad.

Find the meta controller's Load button and the playlist page first (deck.py, ui_loadable.py,
ui_playlist.py, playlist.py). Tests with tests/ui_driver.py: one click saves a new file that loads back
equal; a 40-entry playlist scrolls and its playing row stays in view.
```

## 71. GRAPH: GPU cost at a glance

```
You are building plan 71 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §4 builder brief. Your row in §1 is 71 (files, rows 934–939, checks 729–734, group EF).

Hovering a node on GRAPH already shows its GPU time per frame (plan 37; render.py's per-node pass timer,
around line 903). That readout is how we caught a preset (Rugged Doctor) sitting at the 60 FPS floor with
only a couple of effects. Make the bottleneck visible at a glance:

- A head chip on GRAPH, off by default, that marks every node with its GPU cost: a black-to-white (or hot)
  tint or badge, ranked within the frame and smoothed over about a second so it doesn't flicker.
- The frame's total and the top three nodes in a small line.
- It must cost nothing when off.
- Show nodes that made nothing this frame as such, not as zero-cost.

Stretch: thumbnails for unwired picture nodes other than effects (#461 did effects, through
render.unwired_through), under the same per-frame budget. Read plan 65's doc for why unreached nodes aren't
built, and keep them unbuilt.

Tests: the ranking and smoothing are pure and unit-tested; the chip off draws nothing extra. Capture GRAPH
with the chip on using drive-the-app.
```

## 72. Hands default: BONES, PLAIN, 50%

```
You are working on plan 72 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §4 builder brief. Your row in §1 is 72 (files, rows 940–943, checks 735–737, group EG).

The owner changed the ghost hands' show look on 2026-11-18: on, BONES style, PLAIN material, opacity 0.5.
PR #459 (branch worktree-ghost-bones-default) set it as GLASS at 0.35 and isn't merged.

1. Update that PR, or replace it with a new one from origin/main if it has drifted too far, so the code
   default is on, BONES, PLAIN, 0.5 (ghost.SHOW_LOOK, applied in app.py and to extra hands nodes;
   GhostState stays neutral, as #459 explains, so render goldens don't move).
2. Write tools/set_hands_look.py for the owner to run on the library:
   - it backs up first;
   - it sets every loadable patch's hands to the show look and wires an unwired hands layer to
     output.all.hands and output.all.guide, as #459's description of the 2026-11-15 run says;
   - it has a dry run by default and --apply to write;
   - it walks folders, because the library is in era folders now.
   Test it on tmp copies of tests/corpus patches. Put the command in the PR body; don't run it on any
   real library.
```

## 73. Loader and node-mode fixes

```
You are building plan 73 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §4 builder brief. Your row in §1 is 73 (files, rows 944–949, checks 738–741, group EH).

1. A loadable patch file with no "units" marker is read as an older file, and the loader silently rescales
   route depths on effect amount params (0.12 became 0.28; 0.25 became 0.8) with no note. Two agents writing
   patches by hand hit this on 2026-11-19. Make the loader add a note when it rescales for a missing marker,
   naming the routes and the old and new depths. Don't change the rescale itself: old files depend on it.
   Add a test.
2. Node mode doesn't map dropdowns (enum params). Find out why, in nodemode.py and what it maps. If enum
   params can be mapped cleanly (stepping through choices, or a choice per node position), build it.
   If they can't, or it touches the graph's model, write it up as a register row with options and stop.
   The owner suspects some of the program's ideas don't line up underneath here, so explain what you find.
```

## 74. Audio reactivity that survives a load (wave 2: after D1 and after 70 merges)

```
You are building plan 74 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §4 builder brief. Your row in §1 is 74 (files, rows 950–957, checks 742–749, group EI).

Every time a patch loads, the owner opens the faces UI and uses the shortcut that routes an analyzer band's
lane to the face fader (ui_routing.py, "route the selected band's lane to this param"). Doing that on every
load is the pain. Audio reactivity must not be forced onto every patch.

Decision D1: <paste the owner's answer; the recommendation is A>.
A = band-to-fader routes on the meta controller (the rig layer), laid over whatever patch loads:
- one toggle and one depth knob on the meta controller panel, learnable;
- a patch can opt out with a saved flag;
- a patch's own routes on the same param win over the meta controller's.

Read GLOSSARY "meta controller" and the plan 43 preset contract first. A bends "a preset is a complete look",
so write the reasoning into DECISIONS. Which faders and bands: the face fader(s) the shortcut targets today,
with the band choice editable. Tests: load three patches in a row and the routes are live on each, with no
click; an opted-out patch has none; nothing of the meta controller's routes is saved into a patch.
```

## 75. Install mode (wave 2: after D2 and after 70 merges)

```
You are building plan 75 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §4 builder brief. Your row in §1 is 75 (files, rows 958–965, checks 750–757, group EJ).

At a multi-day install the rig ran for hours with nobody at it. It should do something good on its own and
hand back the moment someone touches a controller.

Decision D2: <paste the owner's answer; the recommendation is below>.
- [install] in config.toml: on, idle_after = 300 s, playlist = "<name>".
- After idle_after with no desk, pad, Joy-Con or hand input, play that playlist from the top, with its
  dwell times, crossfading as the playlist already does.
- Any touch returns to the loadable patch that was up when it went idle, restored as it was left.
- A small "install" indicator on the panel. Never on the output.

Use one idleness signal for the whole app: idle_lights.py (#464) already detects an untouched desk
(IdleLights.touched). Share or extend that signal rather than building a second one, and coordinate with
PR #465 (open) by reading, not editing, idle_lights.py where you can. Hands count as touch only when a hand
is actually tracked. Tests with a fake clock: idle triggers at the threshold, a touch returns to the exact
patch and values, and a playlist end loops.
```
