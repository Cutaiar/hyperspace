# Plan 47 — the Joy-Con as a 4D totem (an experiment)

**Status: an experiment on `experiment/joycon-totem` (2026-11-02), a draft
PR, not a plan item.** No decision rows, no register rows, no preset or
schema change. It is here so the owner can feel it at the machine and
say whether it is worth a real plan.

## The ask (the owner, 2026-11-02)

> Make the position and rotation of the Joy-Con control the position and
> rotation of the shapes. I want to control the entire DCM matrix with
> just the Joy-Con's IMU, the six axes. […] the gamepad buttons X, Y and
> B toggle whether a given rotation plane is the normal 3-space plane or
> the fourth-dimensional W plane. You can only have three planes of
> rotation selected at once, and those get mapped onto the gyro. The A
> button, or D-pad down, is a reset: given the current position of the
> Joy-Con, reset the shape's position and rotation to world zero.

## What it does

`hyperspace/totem.py`, run by the pad device (`PadDevice._totem`) once a
frame while `totem.on` is set, on the first pad with motion sensors.

**Turn.** The pad's calibrated gyro (deg/s, in the pad's axes after the
Joy-Con's axis map: x right, y up out of the face, z toward the player)
goes through a soft dead band (`DEADBAND_DPS` = 3, a still Joy-Con reads
up to ~2 deg/s on the real tape) and a one-pole smoothing (`SMOOTH_S` =
20 ms), and is integrated, dt-correct, into three plane angles — one per
axis:

| Turn about the pad's | 3-space plane | W plane (latched by) |
|---|---|---|
| x (the far end up / down) | YZ | XW (**X**) |
| y (turning left / right) | XZ | YW (**Y**) |
| z (rolling) | XY | ZW (**B**) |

Held face up and pointing at the screen, the pad's axes are the world's
(x right, y up, z toward the eye), so the shape turns the way the pad
does. Each of X / Y / B is a latch on the press. A plane an axis leaves
keeps its angle; the plane it takes continues from its own. Three planes
of six are live at all times.

**Position.** Tilt from gravity (the pad's roll and pitch, as the
`motion:` lanes read them) against the pose at the last reset, onto
`camera.pan`: 1.5 world units a radian, at most 3, smoothed over 80 ms.
Right side down moves the shape right, the far end up moves it up, and
levelling the pad brings it back.

**Reset — A (or the D-pad's down).** Every `rot.phase.*` to 0, the pan to
0, the camera's orbit (yaw, pitch) to 0, the 3D switch's held pose
dropped: the shape square to the world's axes. The pad's pose right now
becomes the reference for the tilt. (On a Joy-Con (L) held sideways, A
*is* the down arrow; on a Pro Controller the D-pad's down does it too.)

**Its buttons.** While the totem reads a pad, that pad's rows on A, B, X,
Y and the D-pad's down do not fire (`totem.SKIP` → `Router.pad(skip=)`),
or the factory rows would toggle the faces, points and lines with every
plane switch. Every other button keeps its row.

## How to switch it on

Either:

- the pad window: SYSTEM → *Pad diagram* on; its header reads **totem
  off** after the view's word — **click it**. On, it reads **totem YZ · XZ
  · XY** (the three live planes) and changes as X / Y / B are pressed; the
  hover has the button map and the last change. The GRAPH page's pad node
  shows the same header in its side pane. Or
- `config.toml`:

  ```toml
  [totem]
  on = true
  ```

Each change is also written to the terminal (`totem: x → XW  (XW · XZ · XY)`).

The params are `totem.on`, `totem.w.x` / `.y` / `.z`, `totem.pan` (the
tilt-pan, on by default) and the trigger `totem.reset` — rig switches,
never saved (`persist` off) and never a performer's (`modulatable` off).
A key or desk row could fire `totem.reset` or flip a `totem.w.*` like any
toggle.

The Joy-Con itself is plan 46's entry:

```toml
[[devices]]
role = "joy"
kind = "gamepad"
controller = "joycon-l"
```

## How it is built, and why not routes

A module, not routes. Routes and a new source would have been the
graph-visible way, but a route lives in the loaded preset (an experiment
must not touch one), a `position` row's clamp to [0, 1] would whip the
angle at ±π, and the feel's spring would lag it. The module instead
writes through the registry like any scene-setter: `Param.set` on the six
`rot.phase.*` (the integrated angles, `persist=False`, already a
modulation target), `Param.nudge` on `camera.pan.*` (as the sticks' orbit
does). No new writer path, no new performer: a hand route on a phase
still adds its offset on top under the one-performer rule, and the totem
moves the base under it. Its state is visible: the angles are the
`rot.phase.*` values, the latches are params.

**While it is on the totem owns the turn.** It adopts the six phases when
it takes over (nothing jumps), then writes all six every frame from its
own angles — so the planes' own spin (`view.plane.*`, which the host's
integrator adds after the devices run) is held where the totem has it. A
spinning plane is drawn one frame's spin ahead of the totem's angle, a
fraction of a degree. Switched off, the integrator carries on from where
the totem left it.

## Caveats

- **Composition order.** The six angles are composed the way the app
  always has (`geometry.rotate4`: XY, XZ, YZ, XW, YW, ZW, each about the
  world's axes, in that order). Three integrated angles composed in a
  fixed order are Euler angles, not a general path through SO(4): a big
  turn about one axis followed by one about another lands where Euler
  angles say, not where the pad is, and near some poses one axis seems to
  turn another's plane. It is fine for small turns and for one axis at a
  time; a true attitude (a quaternion pair integrated, then decomposed)
  would be the real plan.
- **Position is a stand-in.** The sensor cannot give one: the
  accelerometer integrated twice drifts away in seconds. Tilt-pan is what
  there is, and it couples: tipping the pad to turn the shape about x or
  z also tilts it, so the shape slides as it turns. `totem.pan` off gives
  the turn alone.
- **The turn drifts a little.** Nothing holds an integrated angle (no
  gravity reference for it, no magnetometer). The dead band stops a still
  pad creeping, but while the pad moves its bias rides along; over
  minutes the shape's pose and the pad's part a few degrees. A press of A
  puts them together again.
- **The pan is a scene-setter's write**, so it lands in undo and lights
  the preset's dirty dot as an orbit with the stick does. The phases do
  not (`persist=False`).
- **The 3D switch and 3D shapes.** A 3D shape ignores the W planes
  (`geometry.view_angles`), so with X / Y / B latched its axes do nothing;
  with the 3D switch on, likewise.

## What to feel for at the machine

1. Switch it on, hold the Joy-Con face up pointing at the screen, press
   A: the shape square on. Turn it slowly about each axis: does the shape
   turn the same way (right is right, the far end up tips the shape's top
   toward you)? The (L)'s signs are from its checked axis map; an (R) or a Pro is
   unverified (plan 46).
2. Press B, roll the pad: the shape turns through W (ZW). Press B again:
   rolling is XY again, and the ZW angle stayed where it was.
3. All three in W (X, Y, B): the pad steers a pure 4D tumble.
4. Tilt and hold: the shape stays off centre; level: it comes back. Is the
   coupling with the turn tolerable, or should tilt-pan go?
5. Fast turns: is the dead band (3 deg/s) eating slow motion, or is the
   still pad still creeping? (`DEADBAND_DPS`, `SMOOTH_S`, `PAN_PER_RAD` in
   `totem.py` — a save lands live.)

## Tests

`tests/test_totem.py`: the tables against the app's (`geometry.PLANES`,
the rotation sense against `rot_matrix`), the six-choose-three invariant,
the latches, a constant turn integrated and a flip mid-stream carrying on
in W, a still pad not drifting under the host's spin, take-over without a
jump, the tilt-pan and its return, the reset (A and the D-pad's down), the
pad device stepping it only while on and holding its buttons off the rows,
the router's skip — and the plan 46 tape driven through it: the still
window holds, the turn-right window turns XZ positive, the right-down and
far-up windows pan right and up.

## The poi (2026-11-03, the same terms)

**An experiment beside the totem, on the same pad.** No decision rows, no
register rows, no preset or schema change.

### The ask (the owner, 2026-11-03)

> I want the Joy-Con to be the handle of a poi. I want to be able to adjust
> the weight of the object that's attached to it, the length of the
> string, and the springiness of the string. […] use the Joy-Con like it's
> the handle of a poi, in order to have the geometry fly around the space
> like it is attached via a string to the Joy-Con.

### What it does

`hyperspace/poi.py`, run by the pad device (`PadDevice._totem`, before the
totem) once a frame while `poi.on` is set, on the first pad with motion
sensors. **The shape is the weight**; the scene shows it where the weight
is.

**The handle.** A pad cannot say where it is, only how it turns and what
it feels, so the handle is modelled as:

- **a wrist** at the world's origin (the screen's centre), moved by the
  hand's push: the accelerometer, turned into the world with its 1 g of
  gravity taken out (a dead band of 0.04 g off the top), drives a point
  held home by a critically damped spring at `HAND_HZ` = 0.7 Hz. A quick
  push or a hand circling registers; a slow drift, and the gravity the
  attitude's error leaks, do not. `poi.hand` scales it; 0 is the wrist
  alone.
- **the tip**, `HANDLE` = 0.3 world units out of the wrist along the pad's
  far end (−z in its axes: toward the screen, held face up), turned by the
  pad's **attitude**. The attitude is the gyro integrated in full (a
  rotation matrix, not three angles), with its tilt pulled toward gravity
  while the pad reads within 0.15 g of 1 g, that is, while it is not being
  flung (a complementary filter, 2 rad/s per radian). The start, and each
  reset, takes the tilt from gravity with the heading straight ahead. The
  string hangs from the tip, so **a turn of the wrist swings the weight**,
  as on a real poi, where small circles of the hand drive the weight
  round.

**The string** has a rest length (`poi.length`, world units: the shape's
own radius is 1) and pulls only when stretched. It never pushes, so a slack
string lets the weight fly. Its stiffness is `poi.spring`, from 0 (3000, a
cord that barely stretches) to 1 (6, a bungee), geometric between. Its
pull is damped along its line at a quarter of critical. It never stretches
past 4× its length (`MAX_STRETCH`), a stop that keeps a soft string on a
heavy weight in the picture.

**The weight** (`poi.weight`) is the inertia. A heavy one stretches the
string further, keeps its swing longer against the air (`poi.drag`, a
linear drag) and answers the hand later. Gravity is `poi.gravity` × the
world's. The world's is 9.81 m/s² at 2.5 world units a metre (`UNITS_PER_M`),
so a 1-unit string swings at a real 40 cm poi's period, about 1.3 s. At 0
the poi is in orbit.

The physics runs at a fixed 960 Hz (`STEP_S`, semi-implicit Euler) whatever
the frame rate, at most 96 steps a frame, so the stiffest string on the
lightest weight stays stable. It costs about 0.1 ms a frame.

**What it moves.** The weight's x and y set where the shape sits
(`camera.pan`, y down). Its depth toward the eye, measured from the tip at
rest, scales it (`camera.zoom`, half an octave a unit; `poi.depth` turns
this off). The poi keeps the base it found (`pan_home`, `zoom_home`) and
writes home + its offset each frame through `Param.set`. Anyone else's
write on an axis (a knob, `camera.reset`, the totem's reset, a load)
becomes that axis's new home. Switched off, each base goes back to home.
A still pad hangs the shape `poi.length` below where it was.

### With the totem

Each has its own switch, and both can run from the same pad. While the poi
is on it owns the pan, so the totem's tilt-pan steps aside (`poi.owns_pan`).
The totem's turn still turns the shape as it flies. Both reset on A (or the
D-pad's down). The poi steps first, so it has let go of the pan before the
totem's reset zeroes it. The rows held off the pad are the union of both
modules' (`poi.SKIP` is A and the D-pad's down, a subset of `totem.SKIP`).

### How to switch it on

- The pad window (SYSTEM → *Pad diagram*): its header reads **poi off**
  after the totem's word. **Click it.** On, it reads **poi 1.00 · 0.30 ·
  0.20** (length · weight · springiness), and the six dials (length,
  weight, spring, gravity, drag, hand) and *depth zooms* are drawn under the
  header. The GRAPH page's pad node shows the same. Or:
- `config.toml`, which is also the only way the dials outlast a launch:

  ```toml
  [poi]
  on = true
  length = 1.0     # world units (the shape's radius is 1), 0.2–4
  weight = 0.3     # 0.05–2
  spring = 0.2     # 0 a cord, 1 a bungee
  gravity = 1.0    # × the world's, 0–2
  drag = 0.15      # 0–1
  hand = 1.0       # the hand's push, 0–2
  depth = true     # depth toward the eye zooms
  ```

The params are `poi.on`, `poi.weight`, `.length`, `.spring`, `.gravity`,
`.drag`, `.hand`, `.depth` and the trigger `poi.reset`. Like the totem's,
they are rig switches: never saved (`persist` off) and never a performer's
(`modulatable` off). A key or desk row can still set any of them, since a
desk row is a scene-setter. Each change is written to the terminal
(`poi: on — 1.00 · 0.30 · 0.20`).

### Caveats

- **The writes are a scene-setter's.** The pan and the zoom move every
  frame while the weight swings, so they land in undo (one long step that
  closes when the weight settles) and light the preset's dirty dot, as an
  orbit with the stick does. A save while the weight is out saves it out.
  The clean form is a source: `poi:` lanes a route performs onto the pan
  (an offset, no undo, no save). That is the next step if this feels
  right, but it puts routes in the preset.
- **No real hand position.** The wrist's spring home means a hand held
  off to one side drifts back to centre in a second or two. Only motion
  registers.
- **The heading drifts** a little, as the totem's turn does (no
  magnetometer). The swing does not care, because the weight follows the
  tip whatever way is "ahead". A reset puts it straight again.
- **The shape hangs off centre at rest**, `poi.length` below home, since
  the hand is at the centre. With `poi.gravity` at 0 it floats where it
  was left.
- **A heavy weight on a soft string can stretch to the stop**, 4× the
  length, where the stop holds it.

### What to feel for at the machine

1. Switch it on and hold the Joy-Con still, face up, pointing at the screen.
   The shape should hang below centre and keep still. Press A: it should
   still hang there.
2. Circle the wrist slowly, the far end tracing a cone. Does the shape wind
   up into a circle round the centre? Does it lag the hand the way a poi
   does?
3. Length: a longer string should give a wider, slower circle.
   Springiness: with spring at 0.8 and a heavy weight, does the shape
   bounce on the string? Weight: does a heavy one keep its swing longer
   when you stop?
4. A quick push of the hand, with no turn: does the shape get thrown? With
   `hand` at 0, does only the wrist's turn move it?
5. With the totem on as well, does the shape tumble with the pad's turn
   while it flies?

### Tests

`tests/test_poi.py`:
- off by default and never saved; the config's start, clamped
- a still pad hangs the shape at length plus sag, with no creep over ten
  seconds
- a longer string hangs lower, and a softer or heavier one stretches
  further
- circling the wrist swings the weight round, held by the stop
- a slack string never pushes, and with no gravity the weight floats
- the air takes the swing out, slower on a heavier weight
- the hand's push moves the handle, does nothing with `hand` at 0, and the
  wrist comes home afterwards
- the stiffest string on the lightest weight stays finite under a violent
  pad
- the swing is the same at 30 and 120 frames a second
- the tilt settles on gravity
- home is kept per axis, and off puts it back
- depth zooms, and its switch turns that off
- the reset, on A and on the D-pad's down
- the pad device steps it only while on, holding the union of skips
- with the totem: its tilt-pan steps aside while its turn still turns, and
  a reset that fires both leaves the poi hanging from zero
- the plan 46 tape: a still Joy-Con hangs the shape still

`tests/test_ui_pad.py`: the header's word and the dials.
