# Plan 51: the Ultraleap orbit camera

O1 and O2 of the post-show plan (`tier-2-3-build-order.md` 3.8, 3.9). Turn
a closed hand and the shape turns with it. O1 gives the palm's orientation
as lanes that mean the same thing whatever the camera does; O2 adds the
clutch and the routes onto the one camera (plan 43 C2).

**Status.** O1 built (wave 3, 2026-11-03; register rows 678–681, hand
checks 514–516, group BU). O2 is the sketch in §6, not built. Nothing here
has run on a real sensor: the proof is tape-driven
(`tests/test_hands_room.py`).

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
`position` row at depth 1 with no feel, on any continuous target (GRAPH's cable
and Route from ▸ both go through it). The default it would otherwise get, a
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
  the box; and a twist made inside the cone shows as a yaw step of up to 90°
  on the way out, softened only by the filter.

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

## 6. O2, the sketch

Not built here; O2's builder may overturn any of it.

- **The clutch.** A `position` row gated by `hand:right.grab` is not an orbit:
  closing the fist slams the camera to the palm's absolute angle, and opening
  returns it to the base. An orbit is **relative and it stays**: while the hand
  is closed, its turn since the last frame is added to the camera's **base**,
  and opening leaves the camera where it is. So O2 needs a row that writes a
  base: a new op (say `turn`) reading a whole-circle lane's shortest change,
  with `Param.nudge`'s wrap, gated by the existing `when`. Being a route it is
  visible and saved like any other, which the WYSIWYG rule asks for. The
  gate is the grab that exists; no new gesture.
- **Which turns go where.** `room.yaw` → `camera.yaw` and `room.pitch` →
  `camera.pitch`, depth 1, sign as §2. Roll has no target on the one camera
  (it has no roll); a 4D plane is a preset's choice.
- **A lost hand mid-clutch.** The lane reads NaN and the grab drops: the row
  moves nothing, and the camera stays at the last turn (on the base, so a
  preset save has it). The first frame back has no previous reading, so no
  jump.
- **Saved and held.** Because it writes the base, `hold.HELD_GROUPS`, the save
  and undo all see an ordinary camera move.
- **Open questions for O2.** Whether the yaw step on leaving the pole cone
  (§4) needs a guard; `Palm.pole` is there to read, and the hysteresis uses it. Whether `ghost.mirror`
  should flip the row's sign. Whether one hand or either hand may clutch.
