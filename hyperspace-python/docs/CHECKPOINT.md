# Checkpoint

Hyperspace is a live-visuals app: a 4D polytope driven by music, hands
(an Ultraleap camera), an APC40 and LFOs, shown on a Pepper's Ghost glass
and a projector. It is one Python process in `hyperspace-python/`.

## Where things are

- **The app:** `hyperspace-python/` (package `hyperspace/`, tests in
  `tests/`, tools in `tools/`). Presets are shared through a cloud-synced
  folder named by `[library] path` (plan 25; [`SETUP.md`](SETUP.md)).
- **Run it:** `uv sync`, then `uv run hyperspace`; machine setup is in
  [`SETUP.md`](SETUP.md).
- **The docs:**
  - [`ARCHITECTURE.md`](ARCHITECTURE.md): the parts, the frame, who may
    write a parameter.
  - [`ARCHITECTURE.html`](ARCHITECTURE.html): the same map as a diagrammed
    page, for reading in a browser. Maintained with the Markdown.
  - [`ENGINEERING.md`](ENGINEERING.md): how each part behaves.
  - [`DECISIONS.md`](DECISIONS.md): the decisions in force, and what was
    decided not to build.
  - [`DECISION-REGISTER.md`](DECISION-REGISTER.md): rows 34–541 (bar
    109), built on a recommendation and waiting for the owner's keep or
    overturn; row 109 records the owner's plan 25 answers, and some later
    rows are the owner's own answers before a build (plan 40's 501–510
    among them).
  - [`AUDIT-2026-09.md`](AUDIT-2026-09.md): the open defects.
  - [`TESTING-GUIDE.md`](TESTING-GUIDE.md): everything a person still has
    to test, in plain words, by hardware.
  - [`plans/11-hand-checks.md`](plans/11-hand-checks.md): the same checks,
    numbered 1–403, with the automated test behind each.
  - [`plans/`](plans/README.md) `15-…` to `30-…`: what each plan built
    (plan 23 in part); plan 22 also has a ranked shortlist of new
    4-polytopes and macro candidates to audition; `24-party-wishlist.md`
    is the owner's wishlist the last run came from.
  - [`plans/assets/12-presets/`](plans/assets/12-presets/): the performer
    cards, one per party preset.

## Where the code stands

`main` holds everything through plan 25 (the shared library folder),
plan 22's shapes and face patterns among it, and the fixes merged since
(the pad's share button #197, the hands' own `leapc_cffi` #201, uv's
own Python 3.14 #206, among others). Plans 24, 26 and 27 were run
together on 2026-10-14 and are built on `plan-24-26-27-integration`,
waiting for the owner's merge into `main` (PR #195): the party fixes
([`plans/24-party-fixes.md`](plans/24-party-fixes.md)), the render graph
([`plans/26-render-graph.md`](plans/26-render-graph.md)) and the device
registry ([`plans/27-device-registry.md`](plans/27-device-registry.md)).
No preset was edited or added. Check `git log` and the PRs for the
current state.

**Plans 28 and 30 are built** on `plan-28-30-integration` (cut from the
plan 24–26–27 branch with `main` merged in), waiting for the run's final
PR into `plan-24-26-27-integration` and then the owner's merge. Plan 30, shader nodes
([`plans/30-shader-nodes.md`](plans/30-shader-nodes.md)): every effect an
image node, placeable by a preset on any image edge. Plan 28, the node
editor ([`plans/28-node-editor.md`](plans/28-node-editor.md)): the
modulation evaluated in dependency order (no one-frame lag), modifiers
in the preset, the GRAPH page drawing and editing both graphs, a wire
list with the outputs as nodes, the APC40 as two nodes — and, after the
owner's first look (N7, 2026-10-20), a legible GRAPH: every node
collapsed by default, one wire a node pair, the routes and the modifiers
edited on GRAPH (ROUTING points there; its desk, macros, session and
sinks stay); then the palette as a colour compression (N8, 2026-10-20).
About 2410 tests pass (2411, 2 skipped, with N8), ruff is
clean, and 596 golden frames match on the gate Mac, every one recorded
before unchanged. No preset was edited or added; `apc40.py` and
`midi.py` (Dylan's desk work) untouched.

**Plans 37, 38 and 39 are built** and integrated on
`plan-37-38-39-integration` (2026-10-27: plan 38 first, then plan 39,
then plan 37), which goes to `main` in one final PR the owner merges.
They ran in parallel, one branch each.

- **Plan 38, hold the projector** ([`plans/38-hold.md`](plans/38-hold.md)).
  **hold** keeps every output on the wiring, the rig's bus cables and the
  look as they were at the press, still live under the bands and LFOs,
  while every edit (a GRAPH change, **new**, a load) lands as the preview
  behind GRAPH's nodes, drawn by a second renderer only while the page
  shows it, with a PROJECTOR inset of what the room sees. **take** cuts
  to the preview; **drop** goes back to the hold point as one undo step
  (the preset's part, not the rig). A landing during a hold keeps the
  projector's effects, switches, resizes, mattes, cuts and segments; a
  load's delay reset goes to the preview.
- **Plan 39, vision** ([`plans/39-vision.md`](plans/39-vision.md), every
  decision the owner's). `segment` takes any picture and puts out its
  foreground, its background and its mask (Apple Vision on the Neural
  Engine on a worker thread, torchvision behind it, a motion mode with no
  model); `matte` (picture → mask) and `cut` (picture + mask → picture);
  the mask its own purple wire that never rides in alpha, readable as a
  white-on-black picture wherever a picture is taken; `edges` an effect
  file; the cut-through blend made honest (eight backdrop fixture goldens
  re-recorded for it); on GRAPH a media ▸ and a masks ▸ group and a
  cut-out starter. The hold's preview runs no segment worker.
- **Plan 37, nodes as pictures and the faces**
  ([`plans/37-pictures-and-faces.md`](plans/37-pictures-and-faces.md)).
  Every node that makes a picture is drawn as it on GRAPH, a thumbnail
  made at the frame's end only for nodes on screen, moving no output
  pixel; hovering it gives the node's lines, the size and the GPU time.
  While the projector is held the thumbnails are the preview's, and
  output 1's node shows the program's picture. A head chip, `pictures ·
  tint cables`, is off by default and leans each picture cable's red by
  what flows. An effect is laid in the area of its consumers, so
  `acid-scene` draws forward. The faces are a dry run: sheets of all 17
  modes and a generated migration map are in
  [`plans/assets/37-faces/`](plans/assets/37-faces/); nothing is dropped
  until the owner names the list.

At the integration head the fast tier is 4227 passed, 2 skipped, the full suite 4450 passed,
2 skipped (one load-flaky media test passes serially),
and the goldens 136 passed over 789 pictures, none moved beyond the eight
backdrop frames plan 39 re-recorded. `uv sync` on both Macs
(`pyobjc-framework-vision`), and **both Macs on this build before a
preset with `segment`, `matte` or `cut` is shared**: an older build reads
such a section as black. No preset was edited or added.

**Plan 40, patches, is built** on `plan-40-build`
([`plans/40-patches.md`](plans/40-patches.md), every decision D1–D10 the
owner's, 2026-10-27), cut from the plans 37–39 integration branch with
`main` (PRs #270, #275) merged in; it goes to `main` in one final PR the
owner merges. A **patch** is a group of GRAPH nodes saved with its
boundary — the cables that cross its edge, a knob or a hand axis kept as
the address it is, the scene in and the outputs out kept as typed ports
with the name they were on — as `<library>/patches/<slug>.json`
(`hyperspace.patch/1`, `patches.py`). **Group** folds selected nodes into
one node on GRAPH (`+` opens it in place, a tinted region), saved in the
preset's `groups` (`/8`): a fold of the canvas the renderer never sees,
and the one sanctioned exception to "no hidden edges". **save as patch…**
writes the file; the **patches** chip and **spawn ▸** land one in any
preset under fresh ids as one undo step through the existing doors, its
host ports open pins, or spliced in when dropped on a picture cable; a
knob or hand that collides is asked in one sheet, every row starting on
the patch. The devices the loaded preset wants and the rig lacks are said
on the group, as **N devices missing** on GRAPH's head and the PRESET
strip, and on SYSTEM; a device coming back is said in the footer. The fx
module presets are retired outright (the FX page stays, less its module
strip); `patch.py` is `modgraph.py`. Plan 38's PROJECTOR inset, which
never drew on `main` (an `add_rect` TypeError), is fixed on the same
branch. At e0675a6 the fast tier is 4320 passed, 2 skipped, the full suite
4551 passed, 2 skipped, and the goldens 144 passed (8 new grouped-twin
proofs), none moved. No preset was edited or added; Dylan's files are
untouched.

**Plan 41, the PRESETS page and one tier, is built** (2026-10-28,
[`plans/41-presets-one-tier.md`](plans/41-presets-one-tier.md), every
decision the owner's, from his ask of that day). The library has **one
tier**: nothing ships with the app, nothing is "factory", nothing is
hidden, every preset is listed, loaded, renamed and trashed alike, and a
fresh library opens an unsaved `untitled` show on a blank preset. The
twenty-five presets the build shipped, their generator and the `party` /
`house` shows left the app; the files are the golden frames' corpus now
(`tests/corpus/`, `tools/golden_frames.py` `CORPUS_PRESETS`, the test
harness's `seed`), and the goldens' subjects and hashes are unchanged.
The band scenes are code data (`hyperspace/scenes/band/`). The PRESETS
page is the preset strip over a flat list of every preset (click loads;
rename, ×), the trash at its foot, the patches fold and one line for the
show (what it is, its name ●, open ▾, save, as…, new) — no pills, no
"starts on", no drop-down, no module-preset fold. The pads are the desk's
to set; `startup` stays in the show file for Home. The Drive library's
`hidden.json` was deleted and the four unhidden shipped presets adopted
as the owner's own, lower-cased (`dial`, `trip`, `plasma heart`,
`seq-demo`). Dylan's files are untouched. **Both Macs on this build.**

## What is left

- **Plan 37: the owner's list of face patterns** (register row 417, D1).
  The sheets are in `plans/assets/37-faces/`. With the list, the owner
  also says whether to renumber `view.pattern` or keep tombstones, and the
  controller allows the `preset.py` edit. Then P2 runs: shaders and modes
  dropped, presets migrated to their nearest kept mode with a note, and
  only those presets' goldens re-recorded. Only the second half of check
  375 waits for P2.
- **The hand checks.** None has been run by a person. Start from
  [`TESTING-GUIDE.md`](TESTING-GUIDE.md), on a copy of `~/Hyperspace`;
  plans 24, 26 and 27 add checks 144–218, plans 30 and 28 checks
  220–276 (N8's palette as compression 267–271, N9's graph by concern
  272–276). Above all: a cable dragged on the GRAPH page (247), which no
  test can do. Plans 37, 38 and 39 add groups AH (370–376: the pictures
  on GRAPH, their cost, the hover, the faces sheets, `acid-scene`), AI
  (377–383: the hold on the rig with the projector up, take, drop, the
  desk buttons, the preview's cost) and AJ (384–393: the camera, a
  dancer, the party light, two cameras, an unplugged camera, and the
  honest cut-through by eye). Plan 40 adds group AK (394–401: group and
  ungroup, save and spawn, splice, the conflict sheet with the APC40, the
  desk unplugged and plugged back, a rig without a Leap, the fx module
  presets gone, a patch twice).
- **The owner's keep or overturn** on register rows 34–310 (the answer
  sheet at the top of [`DECISION-REGISTER.md`](DECISION-REGISTER.md)),
  plans 30 and 28's being rows 214–310 (N7's 278–290, N8's 291–298, N9's
  299–310); and on rows 417–500, plans 37, 38 and 39's: plan 37's
  417–429 and 460 (D1, 417, still open), plan 38's 430–439 (its D1–D5
  are 430–434, taken as recommended) and 461–470, plan 39's 440–459 and
  471–497 (440–447 the owner's own), and the integrator's 498–500; and
  plan 40's 501–536 (501–510 its D1–D10, the owner's own; **521 and 524
  pending the owner**: whether a preset with no group also saves as `/8`,
  per row 394, and whether **wire as saved** gets a take-over chip).
- **Both Macs on this build before sharing presets**: an older build
  drops a preset's modifiers and positions when it saves (row 277), and
  refuses a preset with a GRAPH group outright (plan 40's `groups` key,
  `hyperspace.preset/8`).
- **The owner's creative pass** on the new mechanisms, which few of his
  presets use yet: fader sets for S1–S8, hand mappings (the dance sources,
  the grab), dance presets, palettes and where they sit, modifier
  patches, desk templates, and the presets' graph wiring (hands in the
  scene, as lines, in the history, on one output); touch shows.
- **Plan 29**, the devices: wands, drums, a Kinect or other depth sensor
  (the point-cloud node is ready for it), DMX / sACN lights, bulbs, a
  generic on-screen desk.
- **Known faults**: the open audit findings R14, R15, U9, U10, P6, V8.
- **Things nobody has observed:** frame pacing with two screens; a screen
  unplugged mid-run; anything on the APC40, the hand camera, the
  projector or the glass — the registry's devices, the hands through the
  shared camera and the golden presets by eye among them; any mouse drag
  on the GRAPH page; a placed or wired picture on a real second window. No real hand
  has been tracked: every hands picture comes from a synthetic pose or
  tape. No person has watched the lifted shapes or the Klein bottle
  turn, or seen the FACES page or the seventeen patterns on the Mac: its
  fit and Apple's shader compiler are unverified (hand checks 120, 121).
- **Plan 22's choices for the owner:** which new 4-polytopes to build
  ([`plans/22-polytope-shortlist.md`](plans/22-polytope-shortlist.md)) and
  the macro candidates' listening session
  ([`plans/22-macro-candidates.md`](plans/22-macro-candidates.md)).
- **Deliberately not built:** see "Decided not to build" in
  [`DECISIONS.md`](DECISIONS.md).

## Standing rules

- Tests and agents never read or write the owner's real `~/Hyperspace`.
  Tests run against a temp home (`HYPERSPACE_HOME`, set by
  `tests/conftest.py`).
- Never push to `main`. The owner merges.
- A change to a file format backs the old file up before the first
  rewrite.

## Ideas for later (not started)

- An IMU prop feeding rotation phase offsets over UDP: packet
  `struct {uint8 ver; uint8 id; float qw, qx, qy, qz}`, little-endian,
  100 Hz; orientation deltas go to the XW / YW / ZW phase offsets, never
  to a speed; a silent prop decays to no contribution.
- DJ Link tempo: `{bpm, beat_phase, bar_phase, master_deck, on_air[]}`;
  a pure-Python source first, Beat-Link-Trigger over OSC as the fallback.
  MIDI clock in is the other tempo source. (DECISIONS currently says
  neither is built: tempo is tap-only.)
- Audio delay compensation: stream latency + analysis latency − about
  1 ms, calibrated with a metronome.
- FL Studio does not fuse 14-bit MSB/LSB pairs in "Link to controller":
  the bridge needs a small FL MIDI script, or per-channel pitch bend.
- An instanced GPU field (per-instance rotation phases, true instancing).
