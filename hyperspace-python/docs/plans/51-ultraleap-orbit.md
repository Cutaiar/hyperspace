# Plan 51: the Ultraleap orbit camera

O1 and O2 of the post-show plan (`tier-2-3-build-order.md` 3.8, 3.9). Turn
a closed hand and the shape turns with it. O1 gives the palm's orientation
as lanes that mean the same thing whatever the camera does; O2 adds the
clutch and the routes onto the one camera (plan 43 C2).

**Status.** O1 built (wave 3, 2026-11-03; register rows 678–681, hand
checks 514–516, group BU). O2 built (§6; rows 682–685, hand checks 517–519,
group BV). Nothing here has run on a real sensor: the proof is tape-driven
(`tests/test_hands_room.py`, `tests/test_hands_orbit.py`).

## 1. Why new lanes

`hand:<side>.roll / pitch / yaw` stay as they are. They are the wrong
reading for a camera, in three ways:

- **They are the sensor's.** Each is one `atan2` of a raw Leap vector, so
  a Leap hung in screentop mode or mounted at an angle reads differently.
- **They are anatomical.** Mirrored per hand: the same turn in the room
  reads opposite signs on the two hands.
- **They are clamped ranges.** ±45° to ±90° onto 0–1, shaped; past the end
  the lane sticks, and each angle blows up on its own near a vertical hand.

## 2. The frame

The room is **x to the performer's right, y up, z toward the performer**:
the stage of `ghost.MODES`, which is the tracking mode's basis
(`room.MODES`, a copy, because the instrument imports nothing from the
host; a test pins the two tables together; screentop and HMD are as
unmeasured there as here).

It is not the camera's. The lanes are computed from the tracker alone,
and the camera's params are not an input, so an orbit cannot move them.
It leaves out two things the drawing uses:

- `Units.tilt`, the 32° that turns the ghost hands toward the eye. That
  is how the hands are drawn, not where the room's up is.
- `ghost.mirror`. A mirror flips the picture, not the hand. With a mirror
  in the room the turn reads opposite to what the performer sees; a
  route's sign answers that (O2, §6).

A level palm with fingers pointing away from the performer reads
(0°, 0°, 0°). The palm's axes are the same on both hands (up = −`normal`,
back = −`direction`, right = up × back), so the two hands read alike, not
mirrored. The angles are `Ry(yaw) · Rx(pitch) · Rz(roll)`, each
right-handed about the room's axes:

| Lane | Turn | Positive |
| --- | --- | --- |
| `hand:<side>.room.yaw` | about the room's up | fingers swing left |
| `hand:<side>.room.pitch` | about the palm's sideways axis | fingers rise |
| `hand:<side>.room.roll` | about the fingers | the palm's right side rises |

`geometry._camera` turns the same way (its yaw is `Ry`, its pitch `Rx`), so
a route onto `camera.yaw` or `camera.pitch` needs no minus sign to make the
shape follow the palm. The camera yaws first and pitches second and the
palm the other way round, so the match is exact per axis and approximate
when both are far from zero. A clutch of small turns does not show this.

## 3. Calibration

Two layers, both the rig's, neither a preset's:

1. **The tracking mode** (`[hands] mode`), always. A tape plays in its own.
2. **Level room**, optional, a button on the HANDS page: hold one hand flat
   with the fingers pointing where "forward" is, press, keep still for a
   second. The mean palm over at least `CAL_MIN_SAMPLES` frames becomes
   the room's axes. It answers a Leap mounted at an angle and a performer
   facing somewhere other than the sensor's −z, in one gesture.

The window runs at least `LEVEL_S` and on until enough frames have arrived,
up to `LEVEL_WAIT_S` more, so a slow frame rate can still pass. The room is
left as it was, in words, when too few frames arrive, a second hand comes into
view at any point, the palm strays more than `LEVEL_STILL_DEG` from its mean,
or its up is more than `LEVEL_TILT_DEG` from the stage's. The button is hidden
and `start_level` refuses during a calibration sweep, whose palms are moving,
and a sweep started during a levelling ends it.

The result is saved in `hands.json` as `"room": {"mode", "level"}`, the
tracking mode it was made in and the stage → room rotation. The key is written
only when the room was levelled and read as no levelling when absent, so **no
schema move**: an unlevelled file is written as before, and a build from before
ignores the key (and drops it at its next save, costing one more press). A bad
entry is ignored and said once on stderr, as `units` does. **clear** on the
same line goes back to the tracking mode's frame. `reset ranges` does not touch
it: it answers where the sensor is, not how far a hand goes.

A levelling applies only in the mode it was made in, because it is relative to
that mode's stage. In another mode it is ignored and said once, and stays in the
file. **A tape never uses one and cannot make or clear one**: it has its own
mode and no rig, so the rig's `hands.json` is not its to rewrite.

## 4. The lane scale and wrap at ±180°

**A lane is the whole circle:** `0.5 + degrees / 360`, in `[0, 1)`, resting
at 0.5. Depth 1 onto a wrapping param with a full-circle range (`camera.yaw`,
`camera.pitch`: ±π) is one-to-one, a 90° turn of the palm being a 90° turn
of the shape, and the seam at 0 / 1 lands on the same orientation in both.

**A dropped wire lands that row.** `learn.row_for` makes a room lane a
`position` row at depth 1 with no feel, on a continuous target that does not
wrap, and since O2 a clutched `turn` on one that does (§6). GRAPH's cable and
Route from ▸ both go through it. The default it would otherwise get, a
push at the hands' Learn depth on the `smooth` spring, is not one-to-one, and
the spring glides across the seam through the whole range. This is the one line
of knowledge outside `hands/`: `learn.whole_circle` reads the address, because
`row_for` has only the address, and `learn` may not import the hands.

- **Filtered unwrapped.** Each fresh tracking frame adds its shortest step
  to a running angle, and the One Euro filter (the HANDS page's `smooth` and
  `response`, in half turns, the units of the default roll axis) runs on
  that. Only then does it wrap. A hand crossing ±180° steps the lane from
  about 1 to about 0 in one frame, and never sweeps through the middle. This
  is the case that matters for roll: a palm turned up is at the seam.
- **A consumer reads the seam as a turn.** On a wrapping target a `position`
  row needs nothing; a consumer taking differences (O2) takes the shortest
  difference. Anything linear over the seam (a row onto a clamped param, a
  row with a feel) sees a jump, which is what a whole-circle lane is. For a
  clamped range the anatomical axes are still there.
- **Over the top.** At fingers-vertical yaw and roll become one turn. Two
  rules keep the lanes from flipping. Inside `POLE_DEG` (8°) of vertical yaw
  holds and roll carries the twist, until the fingers are `POLE_EXIT_DEG` (11°)
  off vertical, so noise on the edge does not let it go. Past it, of the two
  solutions (yaw, or
  yaw + 180° with pitch and roll going the long way) a hand takes the one
  nearest its last yaw. So pitch runs on past ±90° ("tumbling over the top is
  just more turn", as `camera.pitch` does), with no 180° flip in any lane. The
  costs: a hand back at level after going over the top may read pitch 180°
  rather than yaw 180° and roll 180°, the same orientation, until it leaves
  the box. A twist made inside the cone would show as a yaw step of up to 90°
  on the way out, so past `POLE_STEP_DEG` (5°) the hand reads NaN that frame
  and restarts, as a returning hand does (O2; §6). A smaller step goes through.

## 5. What a lost hand does

The same as every other reading of that hand. When the tracker loses it, the
box keeps it out or the confidence floor drops it, all three lanes read NaN
that frame, so a row lets go and its base returns. The running angle and the
filter forget. A returning hand starts at its new reading with no glide,
because a glide across a circle has no right direction. A hand first seen
within the pole's margin has no yaw to read, so all three lanes stay NaN until
it leaves the margin, rather than latching a guess. A source with no
skeleton (a palm-only fake) reads NaN, as the curls do; the lanes read the
skeleton's palm vectors because the features hold only the anatomical angles.

They carry no setup params, no DAW output and no Learn (`_learn` looks at the
axes only): pick them under **Route from**. `[hands] dofs`, the twelve axes
and every older lane index stay as they are; these lanes come after the grabs
(`Layout.room`), per side, in the order roll, pitch, yaw.

## 6. O2: the clutch and the `turn` row

Built (wave 3, 2026-11-03). **Close a fist and the shape turns with the hand;
open it and the hand moves freely while the shape stays; close it again and
the turn goes on from where the shape sits, like lifting a mouse.** To set it
up, wire `room.yaw` → Yaw and `room.pitch` → Pitch on GRAPH: each cable lands
the row below, and a save keeps it.

### The row

```json
{"source": "hand:right.room.yaw", "target": "camera.yaw", "op": "turn", "when": "hand:right.grab"}
```

A `position` row gated by the grab is not an orbit: closing slams the camera to
the palm's absolute angle, and opening returns it to the base. So **`turn` is a
new performer op that writes the base** (`routing.TURN_OP`, `Router._turn`, one
branch in `Router.modulate`). While the row acts, `depth · scale ·` the reading's
shortest change since the last frame is added to the target's base, wrapped on a
wrapping param and clamped on any other continuous one. It never calls
`Param.modulate`, so nothing rides on the base and nothing is left to let go.

- **No jump, one rule.** The frame a row starts acting it only reads. A frame it
  does not act (`when` shut, the source NaN, the row disabled) it forgets
  (`Router._end_turns`, once a pass). A closing clutch and a returning hand are
  the same case.
- **The seam.** The difference is read as a circle, so ±180° is one-to-one at any
  depth, with no sweep.
- **No feel.** A row's `motion` is not read: a follower would glide across the
  seam. The palm's own filter (`smooth`, `response`) is the row's only smoothing.
- **It is a performer.** In `MOD_OPS`, so it owns its target under the referee,
  is saved with the preset's routes, is drawn on GRAPH and is listed on ROUTING,
  where the op chip goes `position` ↔ `turn` from a room lane. A scene-setter
  (a knob, the pad's stick) still writes the same base.
- **A target that cannot turn** (not continuous, integer, not modulatable) is
  dormant, as a row to an unknown param is.

### What closes the clutch

**The same hand's grab**, `hand:<side>.grab`: `learn.clutch_of` names it when a
wire lands. It is the existing Schmitt-and-debounce switch, and "turn a closed
hand" is the owner's own picture. The row's `when` is an ordinary gate, so a preset
can pick otherwise:

| Alternative | For | Against |
| --- | --- | --- |
| A pinch (`hand:right.pinch.index`) | The hand stays open, which may suit the tracker better | Presets already use pinches as gates; easier to hold by accident |
| The other hand's grab | The turning hand keeps a relaxed pose | Two hands busy; the ghost hands show both |
| No gate | Nothing to learn | The camera follows whenever a hand is in view, so a hand cannot get to where it starts a turn |
| A button lane (`axis:RT`, any fed lane) | No gesture at all | A hand on a controller |

Which reads best on the sensor is hand check 518. Whether closing a fist itself
tips the palm's reading is untested: the proof's fist has the same palm vectors
as its open hand, and the clutch closes only after `GRAB_HOLD_S`, so a real
fist's closing motion mostly falls before it, and an opening's falls inside it.

**One hand per target.** The referee holds a target to one performer, so "either
hand may clutch" is not offered: a second hand's row asks Replace / Keep. Yaw from
one hand and pitch from the other is allowed.

### A lost hand

The lanes read NaN and the grab drops at once (§5), so the row does not act and
forgets. The camera stays where it was, on its base: **a lost hand is an opened
clutch.** It does not fall back to anything. A hand coming back reads afresh and
the clutch has to close again, debounce included, so it returns with no jump
however it is turned.

### The cone (the open question from O1, answered)

A twist made inside the pole's cone would come out as a yaw step of up to 90°, and
on a `turn` row that is a camera jump. So `Palm.step` treats a yaw step above
`POLE_STEP_DEG` (5°) on leaving the cone as no turn of the hand: all three lanes
read NaN for that one frame and the filter restarts. A `turn` row forgets and goes
on with no jump. The cost falls on `position` rows on room lanes: one frame at the
base, where they would have had the step anyway. A `turn` row's undo step also
ends there (below).

### Undo: one step per closure

The first row acting opens a step named "orbit" and no quiet closes it, so a fist
held still past `SETTLE_S` is still one step; when no row acts, it closes at once.
Two rows on one gate are one step. A closure that moved nothing leaves none.

- **The mechanism is the base chase's** (plan 52): `Undo.keep_open` / `let_close`,
  and their module-level forms. B1 is not this branch's base, so those lines are
  **copied from #356 unchanged**, without its `trims`, and either PR landing second
  merges them as identical changes. `Param._commit` / `_trim` are not shared: a chase
  commits what an offset landed and must count it, and a turn has no offset, so it
  needs no ledger and touches nothing in `params.py`.
- **Exceptions, stated.** A lost hand or a cone restart mid-orbit ends the step, so
  it is two steps. An edit made during a closure (a knob) is in the orbit's step, as
  with the chase.
- **Anything else that closes the step cuts the turn** (an undo, a load, the hold's
  engage): the row keeps reading and writes nothing until every row has let go. A
  fist still closed does not run on from what was just put back. The step is kept
  only on an `Undo` watching this registry; on another deck the edits settle by the
  quiet, as a knob's do, until D4 gives each deck its own `Undo` in the call.

### Saved, held, and two decks

- **Saved.** The row is the preset's (plan 43 C2) and the camera's new base is in
  `values`; the dirty dot lights by the ordinary compare, as for the pad's stick.
- **The hold.** It writes the base, so under the hold it moves the preview and the
  projector keeps the held camera, as a knob does, not as a performer riding on both
  does. Row 684.
- **Two decks.** Each router keeps its own readings and writes its own deck's camera.
  D4's dormant rule on a session param comes first, because the turn branch sits
  after that check.

### Format

**No schema move** (row 683, accepted as a recommendation by the wave's orchestrator,
pending the owner). A new op changes what an older build reads: `preset.py` drops the
row with the note "(turn): not a performer row", the rest of the file lands, and a
save from that build loses the row. The alternatives are worse: a `position` row with
a flag slams the camera on an older build, which ignores the flag, and a schema move
refuses the whole file for one camera row. Nothing in the library holds a turn row
until someone wires one, and both Macs update together.

### Known limits

- **It is not a trackball.** The one camera is yaw then pitch, so with the camera
  pitched far over a palm's yaw turns the shape about its own axis, not the screen's.
  Matching the palm exactly would take a rotation for a base, which the camera lacks.
- **Roll has no target** on the one camera. A wire from `room.roll` onto a 4D plane
  (`rot.phase.*`, which wraps) lands a turn.
- **`ghost.mirror` does not flip it.** The mirror is the room's and the row the
  preset's; a mirror in the room is answered by the row's depth, −1. Row 685.
- **After going over the top** a hand may read pitch 180° (§4). A `turn` row takes
  differences, so it does not jump, but a pitch made from there reads reversed until
  the hand leaves the box.
- **No real sensor has run any of this.** Hand checks 517–519.
