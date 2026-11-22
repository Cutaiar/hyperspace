# The post-install wave: the cloud-agent prompts

One prompt per item in [`66-post-install.md`](66-post-install.md). Paste the block under an item into a new Claude Code cloud session on the `hyperspace` repo. Wave 1 (80–86) can all go at once. Wave 2 (87, 88) waits for decisions D1 and D2 and for 83 to merge; 89 waits for 82.

Every prompt starts the same way, so an agent reads the plan before it builds.

---

## 80. Mandelbrot fixes

```
You are building plan 80 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §6 builder brief. Your row in §1 is 80 (files, rows 1000–1007, checks 800–807, group FA).

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

## 81. An endless, centred fractal dive

```
You are building plan 81 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §6 builder brief. Your row in §1 is 81 (files, rows 1010–1017, checks 810–815, group FB).

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

Branch claude/serene-davinci-cgtewx (unmerged, 2026-11-20) adds a FRACTAL side-pane section (Detail, Reach,
Near, To the top) and moves view.frac_additive there. If it has merged, put the dive-rate control in that
section; if not, read it and don't duplicate it.

Tests: a long dive (hundreds of levels) at a fixed rate stays centred and never jumps; a negative rate
climbs back out to the whole shape; the 3D and 4D fractals both work.
Render a before/after video pair of a Menger sponge dive with drive-the-app and commit it under
docs/plans/assets/81-fractal-dive/.
```

## 82. Control widgets

```
You are building plan 82 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §6 builder brief. Your row in §1 is 82 (files, rows 1020–1029, checks 820–829, group FC).

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
count right. Capture screens with drive-the-app and commit them under docs/plans/assets/82-control-widgets/.
```

## 83. Save and load live

```
You are building plan 83 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §6 builder brief. Your row in §1 is 83 (files, rows 1030–1035, checks 830–835, group FD).

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

## 84. GRAPH: GPU cost at a glance

```
You are building plan 84 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §6 builder brief. Your row in §1 is 84 (files, rows 1040–1045, checks 840–845, group FE).

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

## 85. Hands default: BONES, PLAIN, 50%

```
You are working on plan 85 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §6 builder brief. Your row in §1 is 85 (files, rows 1050–1053, checks 850–852, group FF).

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

## 86. Loader and node-mode fixes

```
You are building plan 86 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §6 builder brief. Your row in §1 is 86 (files, rows 1060–1065, checks 855–858, group FG).

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

## 87. Audio reactivity that survives a load (wave 2: after D1 and after 83 merges)

```
You are building plan 87 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §6 builder brief. Your row in §1 is 87 (files, rows 1070–1077, checks 860–867, group FH).

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

## 88. Install mode (wave 2: after D2 and after 83 merges)

```
You are building plan 88 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §6 builder brief. Your row in §1 is 88 (files, rows 1080–1087, checks 870–877, group FI).

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

## 89. The VIEW page, reviewed and fixed (wave 2: after 82 merges)

```
You are building plan 89 of Hyperspace (Python + moderngl, in hyperspace-python/).
First: git fetch origin plans/66-post-install && git show origin/plans/66-post-install:hyperspace-python/docs/plans/66-post-install.md
Follow its §6 builder brief. Your row in §1 is 89 (files, rows 1090–1099, checks 880–887, group FJ).
§5 of that plan is the review of the VIEW page (2026-11-20): what it holds, how the 158 library patches
use each control, and what to build. Decisions D5–D7 there are yours, built as recommended unless the owner
wrote otherwise below.

Owner's notes on D5–D7: <paste, or "as recommended">

Build §5's list:
1. One page in three sections: Shape, Spin, Copies. In Spin, each plane is one row, its toggle beside its
   rate; this replaces the separate ROTATION strip.
2. A fold in each section, closed by default, for the rarely used controls.
3. Labels and tips where missing.
4. The media path's four controls on MEDIA.
5. No id renamed or re-keyed. Saved patches, routes, learn, desk layers and the APC40's knob 7 alias
   (view.bmp_alpha) must keep working unchanged.

Build it on dkit (ui_view.py, ui_fields) and keep Panel._view_stock in step for the no-kit path.
Plan 82 (control widgets: ticks, bipolar faders, XY pads) has merged before you start; use its widgets.

Branches that touch the same ground, unmerged on 2026-11-22: claude/serene-davinci-cgtewx moves the fractal
controls (and view.frac_additive) out of VIEW into a FRACTAL section; claude/hyperspace-luma-key-transparency-ysmbfq
adds a key to each media channel on MEDIA. Build on whichever has merged.

Before you change anything, re-run the review against the current code: a control added since the review,
or one moved, goes in your plan doc.

Tests with tests/ui_driver.py: every VIEW control is still reachable by its id; a plane's toggle and rate sit
on one row; the folds start closed and remember nothing in a saved patch; the media-path controls set their
params. Capture before/after screens of VIEW and MEDIA with drive-the-app and commit them under
docs/plans/assets/89-view-page/.
```
