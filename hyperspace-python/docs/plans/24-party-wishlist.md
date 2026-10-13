# Party wishlist — the owner's intent, 2026-10-12

**Not built.** The working plan lives in a shared Claude Doc so Dylan can
comment and add his own items without committing:
<https://claude.ai/code/artifact/ac6ea6d8-c18d-40ae-9dab-828618791dc3>.
This file keeps what the doc does not: what the owner meant by each
wishlist item, from the Q&A that produced the doc. When a stream below
becomes a plan, it gets its own file in the usual format and this file
points to it.

## Priority (owner, 2026-10-12)

- **The node-based render pipeline is high priority.** F2, the render graph,
  starts now (plan 25), and the node editor follows it directly (plan 27).
- **The device registry is a high-leverage idea.** F1 runs in parallel
  (plan 26), then the devices on it (plan 28).
- The party fixes (plan 24) run alongside as a small plan.

## Render graph design decisions (owner, 2026-10-12)

**Hands, and any geometry, are drawn either inside the scene or as a
separate buffer composited anywhere in the pipeline**, and the same hands
can do both at once (in the scene on the projector, a clean layer on the
glass).

- **Geometry nodes** (shape, hands, point cloud) produce draw calls in one
  shared camera and have no framebuffer of their own.
- **A scene node** draws several geometries into one colour + depth target:
  solid geometry first, then the sorted see-through shape.
- **A layer node** draws one geometry into its own colour + depth target. It
  can go before the FX (today's "through"), after them, into history, or to
  a single output.
- **A composite node** merges layers with over, add, or depth-aware
  blending, so a separate hands layer can still be hidden by the shape.

Why depth is the hard part, from the code (see the shared doc's F2 section):

- **2D pixels only.** The shape reaches the GPU only as 2D pixels
  (`project_h`, `geometry.py:1009`; buffers are `"2f 1f"`,
  `render.py:609`), through a hand-written camera.
  - The hands use their own matrix in Leap mm (`ghost.camera`).
  - Fix: 4D→3D as now, then 3D→screen in the vertex shader with one shared
    4×4 matrix. Point clouds need this anyway.
- **Camera controls.** `camera.yaw/pitch/zoom` become the shape's rotation
  and scale, and the shared camera stays framed on the Leap box, so hands
  stay where the performer's hands are. A calibration maps Leap mm into
  shape units.
- **See-through looks.**
  - The shape is see-through, alpha-over in painter order
    (`render.py:11`). Solid geometry is drawn first, then the sorted
    see-through shape.
  - Order-independent transparency is deferred. Until then, hands inside
    the scene have `ghost.alpha` at 1 or are sorted as one object.
- **Lines and points** are screen-space and become vertex-expanded quads
  with a real depth.
- **History becomes wiring.** Look-back and the dream capture from a chosen
  node, with or without hands.
- **Today's three pipelines** (`outputs.py:34`) become default graphs that
  F2 step 1 must reproduce pixel for pixel.

**Step 0, before F2 step 1:**

- golden-frame fixtures for every factory and party preset
- GPU timing for each pass
- the param-naming rule: the first instance of a node keeps today's ids
  (`fx.acid.mix`), and only extra instances get a prefix, so no preset or
  binding needs migrating

## The wishlist as the owner meant it

- **Fix the APC40.** Keep the map's shape but make it better:
  - Hold-to-save on a bank pad was unreliable, and save/load felt
    inconsistent.
  - The points/lines/faces/rotate toggles acted inconsistently. They sit on
    the preset layer only (`apc40.py:469`), so they go dark under SHIFT.
  - About a quarter of the controls did something interesting on a given
    preset. The aim is that every preset's controls do something.
  - The owner wants git-diffable tooling to map controls more easily.
- **Faders need to be useful.**
  - The master fader stays audio drive.
  - Every other fader becomes a free target that the preset's desk binds.
  - No auto-suggested fill.
  - No global behaviours inherited by every preset; the SHIFT latch is
    where globals live.
  - Per-layer or per-effect mix is interesting, but which layers get the
    faders is the preset author's choice.
- **Hands: geometry, graphics and intuition.**
  - Guests assumed the hands were in the same scene as the shape and tried
    to touch it.
  - Many danced with their hands close together, gloving and tutting,
    rather than using the 12 axes. The 12 axes stay.
  - Add on top of them: hands as part of the art, meaning FX on the hand
    mesh, textures, tracers, and the hands' look modulated by other
    controls.
  - The hands must stop being their own subsystem and plug into the render
    pipeline as modular geometry (F2).
- **Node based editor.** For both modulation and the visual pipeline.
- **Colour palette sync / transforms.** Other installs at the event used
  restricted palettes. The owner wants a latent transform that maps the HSV
  cylinder onto a subspace that can be defined and moved live, so the
  rainbows land in a chosen slice. The doc calls it the palette fold.
- **DMX.** Both directions: the visuals drive the lights, and the lights are
  a controllable layer. The main reason is to interface with other people's
  lighting rigs. We own no gear yet, so we need a buy list.
- **Smart bulbs.**
  - Our own portable ambient lighting, separate from DMX.
  - We own GE Cync and Feit bulbs, plus two-prong-to-E26 socket adapters;
    Govee was mentioned.
  - The owner will do whatever it takes for low latency, Wi-Fi or Bluetooth.
- **Kinect.**
  - We own two Xbox 360 Kinects.
  - The stretch goal is crowd surface reconstruction: GPU space carving and
    marching cubes across several cheap sensors. It is deferred for cost.
  - Short term, the app should "speak point clouds" and 3D displacements
    before any hardware is bought.
  - Pilot: one 360 Kinect for body pose, or two for basic space fill.
- **Wiimotes.**
  - Concrete and wanted almost immediately: hand-held remotes that guests
    hold, over Bluetooth, for low-latency gesture control.
  - The owner is open to alternatives.
  - The owner asked for the Bluetooth caveats.
- **Drum pads.**
  - Guests drumming physically; the more modes of interaction the better
    (hands, APC, Kinect, wands, drums).
  - Prove the concept with the Bluetooth Rock Band kit we have access to
    (an older Wii/PS3/360 kit; the exact model is not yet known).
  - Then build our own piezo or contact triggers into a high-Z interface.
- **Dante.** The event's sound rig spoke Dante, and a long XLR run to front
  of house was not possible. Next time, take the DJ/FOH feed over the
  venue's network. The owner half-remembered an open "64-channel" festival
  protocol; the research suggests MADI, or AES67 for a network.
- **Touchscreen.** An operator panel wired to the MacBook. The laptop was
  hidden in the cart, so operating it meant crouching, and a MacBook can't be
  left out in the open.
- **Pocket projector.** Hardware, to make the rig portable.
- **Mic mount.** Hardware: a mount for the mic on the cart. The owner is
  sourcing it.
