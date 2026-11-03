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
