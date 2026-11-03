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
is integrated into three plane angles — one per axis — **per report, on
the hid reader's thread**. As each report arrives, the reader (`hid.Turn`)
pulls its gyro samples out without decoding the rest (`gyro_of`: a
Joy-Con's three, 5 ms apart; a DualSense's one), puts each through the
calibration and a soft dead band per report (`gesture.TURN_DEADBAND_DPS`
= 3: a still Joy-Con reads up to ~2 deg/s on the real tape, and a rate
under the band turns nothing for that report), and multiplies it by the
time since the report before, by the reports' own clock (`report_clock`:
a DualSense's sensor timestamp, 0.33 µs a count; a Joy-Con's timer byte, 5
ms a tick) so a Bluetooth burst that arrives all at once after a pause
still covers the time it was sent over, at most 50 ms a report
(`gesture.REPORT_DT_MAX`, so a real gap is no turn); arrival time stands
in where a codec has no clock or a tape loops round. Each frame the pad takes the sum
(`HidPad.take_turn`), puts it through its axis map, and adds it to the
angle the totem takes (`Motion.take_turn`). A report that stalls adds
nothing. Two reports between frames both count. A 1000 Hz DualSense
loses no report to a slow frame. The frame still decodes only the newest
report (`latest`). A frame with no report lets the motion lanes leak home
(`Motion.decay`), with no turn. A recorded tape sums the reports it
passed the same way, across its loop's seam. (The first cut multiplied
the last report's rate by the frame's dt and smoothed it; the code
reviews' fixes dropped both.)

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

**Reset — A (or the D-pad's down).** The registry's own `camera.reset`
("Reset view": every `rot.phase.*`, the orbit, the zoom and the pan to
their rests, the 3D switch's held pose dropped — the shape square to the
world's axes), one reset rather than a copy of its list; a phase a route
modulates goes to 0 through its param as well, so the route's base does
not bring the old angle back. The pad's pose
right now becomes the reference for the tilt. (On a Joy-Con (L) held sideways, A
*is* the down arrow; on a Pro Controller the D-pad's down does it too.)

**Its buttons.** While the totem reads a pad, that pad's rows on A, B, X,
Y and the D-pad's down do not fire (`totem.SKIP` → `Router.pad(skip=)`),
or the factory rows would toggle the faces, points and lines with every
plane switch. Every other button keeps its row. Learn ignores those
buttons on that pad too, from the very frame the totem takes it, and a `hold` row whose press began before the
totem took the pad forgets it, so it does not fire when the totem lets go
mid-press.

**Letting go.** Switched off, the totem takes back the pan its tilt
added. A pad it reads that stops stepping it for half a second
(`LOST_S` — its device gone) lets it go and gives the pan back: the
header reads **(no pad)** and the next pad with sensors takes over. A pad is named by its device
role (`[[devices]]`' `role`, "joy" above), never the router's qualifier
(which is "" for the first pad): the terminal says `reading joy`.

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
A `[totem]` that is not a table (`totem = true`) is config.load's error
on the SYSTEM page ("must be a table"), and the totem stays off.

The state survives a hot reload of `totem.py`: the pad device checks it by
duck type, not `isinstance`, and the deck lists it among the objects a
reload re-classes (`Deck.targets`).

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
- **The reset is the view's reset**, so it puts the zoom back to 1× as
  well (the first cut left the zoom alone).
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
   still pad still creeping? (`TURN_DEADBAND_DPS` in `pads/gesture.py`,
   `PAN_PER_RAD` in `totem.py` — a save lands live.)

## Tests

`tests/test_totem.py`: the tables against the app's (`geometry.PLANES`,
the rotation sense against `rot_matrix`), the six-choose-three invariant,
the latches, a constant turn integrated and a flip mid-stream carrying on
in W, a still pad not drifting under the host's spin, take-over without a
jump, the tilt-pan and its return, the reset (A and the D-pad's down), the
pad device stepping it only while on and holding its buttons off the rows,
the router's skip — and the plan 46 tape driven through it: the still
window holds, the turn-right window turns XZ positive, the right-down and
far-up windows pan right and up. The review's fixes each have a test:
a hot reload's new class still drives (and the deck lists the state for
re-classing); a stalled report adds no turn and two reports in a frame
both count (through the real Joy-Con reader and `Pad` as well); a pad gone
quiet lets the totem go and the header says "(no pad)"; on / off / on
while tilted leaves the pan at 0; the totem's reset equals the camera
reset plus a re-reference; Learn ignores the totem's buttons; a hold
begun before the skip does not fire after it; a scalar `[totem]` (through
config.load) leaves it off; the pad is named by its device role. The
second review's: a 0x21 reply as the newest report adds no second turn;
a 1000 Hz burst through a 120 ms frame loses no turn and decodes once; a
tape's turn across the loop's seam and a one-report tape's; the dead band
per report and a capped gap; a stall eases the energy and yaw home; a pad
gone quiet gives the pan back with no pad taking over; Learn on the frame
the totem takes the pad. The third's: the same pad back after
`LOST_S` takes over afresh; the pan given back is what was applied at the
range's edge; a Joy-Con burst after a pause turns the whole time it spans;
a reset zeroes a modulated phase's base; `will_drive` and `step` agree on
a pad that lost its sensors; one rule finds the state; an unarmed Learn
never asks the totem.

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
  0.20** (length · weight · springiness), followed by the word **dials**.
  The dials have their own small window, **Poi**, which opens when the poi
  comes on: the six dials (length, weight, spring, gravity, drag, hand),
  *depth zooms*, *show string* and a **reset** button. It is movable and
  starts at the top centre of the control window. Clicking **dials** (or
  the window's close box) hides it, and clicking **dials** again brings it
  back. The pad window keeps all its room for the pad: the dials used to
  sit under its header and shrank the map, Faithful and Cockpit until they
  could not be read (2026-11-03). The GRAPH page's pad node has the same
  header and opens the same window. Or:
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

### The guide: the string, the handle and the weight (2026-11-03)

The owner, after a first go at the machine: the string cannot be seen,
and the handle must be seen where it is in space. Asked where it should
draw, they chose an operator's guide (not the audience's picture), with a
marker for the weight.

`hyperspace/poi_guide.py` draws, in the world the shape is drawn in and
through the shape's eye:
- the **handle**: a grey tube from the wrist to the tip, a grey ball at the
  wrist and a blue one at the tip;
- the **string**: from the tip to the weight, white while taut and grey
  while slack;
- the **weight**: a red marker on the shape's centre as drawn (the live
  pan), so it never parts from the shape, scaled by the depth zoom as the
  shape is.

The poi's space sits on the pan's home. The guide is drawn once a frame
into its own multisampled layer with depth, before the graph runs, and is
laid over each output after the hands and their readout
(`Renderer._poi_layer`, `_compose`). It never goes through the effects or
into the look-back, so it is not in the history. An output's hands switch
(`output.N.hands`) mutes it with the hands. `poi.guide` (*show string* in
the pad window, `guide` in `[poi]`) turns it off. It is on by default
while the poi is on, and draws nothing until the poi has written the pan.
With no poi handed to the renderer (`Renderer.poi_source` None), nothing
changes: no golden moved.

Held face up and pointing at the screen, the handle points into the
screen, so the guide shows it end-on, the wrist ball covering the tip.
Tipping the pad shows its length.

Tests are in `tests/test_poi_guide.py`:
- nothing draws while the poi is off, its guide is off, or it has no home
- the weight marker sits on the shape, and the string runs from tip to
  weight
- the handle follows the home, and the marker grows with depth
- the string is bright while taut and dim while slack
- the renderer lays the guide where the weight and the tip project, and
  leaves the rest of the picture alone
- an output's hands switch mutes the guide

### The hand, second cut: a frame that does not centre itself (2026-11-03)

The owner, at the machine: the Joy-Con carried a full metre to one side
moved the shape a little, then it came back to the centre; fast moves
drifted a lot; and the tip was drawn toward them. Their intent is a Wii
remote's: the object held in the hand, in a reference frame that does not
re-centre itself. Above, "No real hand position" and the wrist's spring
home are replaced by the following:

- **The hand stays where it is carried** (`poi._hand`). Its push (the
  accel through the attitude, with gravity taken out) is integrated into
  a velocity and that into a place, with no spring home. A metre carried
  is 2.5 world units at `poi.hand` 1, and the place stays there. A puts
  the hand home. It is held within `HAND_LIMIT` (8 units), and a pad
  whose readings stop (`STALL_S`) pushes nothing.
- **Still means still** (`_stillness`): turning slower than 15 deg/s, with
  a push under 0.06 g left after taking out gravity, for 80 ms. While
  still, the velocity is zeroed, so the drift a double integral gathers
  cannot run on between moves. The tilt is pulled to gravity only while
  still: the old test, |accel| near 1 g, took a gentle sideways push for
  gravity, tilted the attitude into it and swallowed the move. As a
  fallback, a pad that turns slowly and reads 1 g for 1.5 s while the
  attitude still sees a push counts as still, because the attitude is
  wrong, and no hand pushes one way that long.
- **Every report's turn**, through the poi's own tap
  (`Motion.take_turn("poi")`), so the totem and the poi each get every
  degree.
- **The dead band passes a real turn exact** (`gesture._banded`): zero
  under 3 deg/s, a ramp to 6, exact above. It used to subtract 3 deg/s from
  every rate, which on a hard swing lost about ten degrees of attitude in
  seconds, and that error leaked gravity into the push. The totem gains
  the same accuracy.
- **A hard spin bleeds the velocity**: faster than 120 deg/s, at up to 2/s.
  A spin gives no still moment to zero what the attitude's errors leak.
  A carry turns little, so it is untouched, and the place is never pulled
  home.
- **The handle points along the pad's +z**, away from the player as the
  owner holds it.

**What it cannot do.** An IMU alone gives no absolute position. A move's
travel is a double integral, so a metre lands about a metre away, with
an error that stays put rather than being pulled back. The Wii's sensor
bar is what gave its remote an absolute point; nothing here does.

The tests now drive a physically consistent pad (`Truth` in
`tests/test_poi.py`: its accel turns with its gyro), and cover:
- a metre carried that stays, and A bringing the hand home
- a still pad with a 3° tilt error that does not drift
- the limit, and a stalled pad
- both consumers getting every degree
- fast swings with no travel that leave the hand where it was
