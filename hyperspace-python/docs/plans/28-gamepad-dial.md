# Plan 28 — the sticks as dials (a prototype spike)

**Status: a prototype.** It is built, tested headless, and nobody has
played it at a pad yet. It is here to be tried and then kept, changed or
taken out.

## The idea

A stick has two things in it: where it points and how far it is pushed.
Read as a clock face, it can do more than orbit the camera. Split the
face into eight equal sectors. **The angle picks a parameter, and the push
is how much of it you get.** At rest every sector reads 0, so the scene
sits on its bases: sane, the shape plainly visible. Push up and one thing
happens. Push up-right and something else does. Sweep round the rim and
you go through eight of them, one after another.

Two sticks give sixteen parameters, each from 0 to 1, and the hand
always knows where it is by feel: centre is home.

## How it is built

- `gamepad.dial(x, y, mode, held)` is the clock: eight lanes from a stick
  position. Sector 0 is straight up and they go clockwise (`COMPASS`:
  N NE E SE S SW W NW). The radius is the stick's distance from centre,
  with the deadzone cut on that distance (not on each axis, which would
  bend the angle). It reaches 1 at the rim and stops there: a pad's square
  gate reads past 1 on the diagonals.
- The 16 lanes are more `axis` lanes after the six raw ones
  (`gamepad.LANES`): `axis:L.N` … `axis:R.NW`, resting at 0. Nothing new
  in the router. A `push` route on one is the whole binding, and the
  pad's feel (`desk.pad.feel`) applies to them as it does to the others.
- A route on any dial lane takes **its whole stick** off the camera job
  (`gamepad.claims`). A stick is either a dial or a camera, never both.
- **Learn pad** on a stick that already has a dial route lands the sector
  it points into (`gamepad.learn_from`'s `dials`). A stick with no dial
  route learns `LX` / `LY` as before. So the first dial route comes from
  a preset or the ROUTING page, and Learn fills in the rest.
- SYSTEM → gamepad draws both faces: each sector filled out to how far
  it reads, named by the param its route drives, the stick as a white
  dot. Under them are the two readings and **Swap dials**.

## The two readings

The question the spike is meant to answer is which one feels right.
There is one reading per stick, switched live:

| Reading | What a sector reads | Feels like |
|---|---|---|
| **petal** | the whole radius in the sector the stick points into, 0 in every other; a border is sticky (`DIAL_STICKY`, 15 % of a sector) so a stick held on one does not flicker | eight separate buttons with depth: crossing a border is a cut from one parameter to the next |
| **blend** | a triangle about each sector's own direction: on a sector's centre it has the whole radius, halfway to the next the two share it | a crossfade: a sweep round the rim morphs one parameter into the next, and the lanes always add up to the radius |

They start as the gamepad entry's `dial_left = "petal"` and `dial_right = "blend"`
(a `[[devices]]` entry, or the old `[gamepad]` table).
**Swap dials** (`desk.pad.dial.swap`) trades them, so the same routes can
be felt both ways. Learn pad can put it on BACK (`pad:VIEW`), which is
free.

## The DIAL preset

A quiet tesseract with every effect below switched on at a base where it
does nothing (or next to nothing, for the wobble).

| | Left (petal) | Right (blend) |
|---|---|---|
| N ↑ | wobble speed | 4D depth |
| NE | wobble amount | speed |
| E → | deconverge (the light coming apart into its colours) | glimmer |
| SE | double vision | hue cycle |
| S ↓ | trip warp | zoom burst |
| SW | trip colour | plasma |
| W ← | kaleidoscope | pattern mix |
| NW | fractals | acid |

The depths in the file are first guesses.

## Recorded (headless, a scripted pad)

`tools/dial_demo.py` runs the whole app under Xvfb with DIAL loaded and a
pad whose sticks follow a script, on a simulated 30 fps clock. The script
is: a push up and let go, a slow lap of the rim on each stick, a stick
shaking ±4° on the N | NE border, then the readings swapped and the left
stick's lap again. Its output is in
[`assets/28-gamepad-dial/`](assets/28-gamepad-dial/): `dial.mp4` (scene
beside the faces), `dial-sheet.png`, `dial-traces.png` (each lane and the
param it pushes), `dial-borders.png`, `dial-trace.csv` and
`dial-timing.txt`.

What it showed (2026-10-17):

- **Every sector reaches its param, and nothing else moves.** Each lane
  peaks at 0.94 on its lap (the script's rim is 0.95 of the throw) and
  only its own param leaves its base. Let go, and every param is back on
  its base the same frame.
- **The camera job is released.** With both sticks dials, the camera's
  yaw, pitch and zoom and the W planes' rates did not move at all
  (`dial-timing.txt`).
- **Petal's sticky border works.** Shaking ±4° on a border, petal stayed
  on one sector (0 changes in 2 s); blend crossfaded N ↔ NE at 3 Hz, the
  two lanes each about 0.45 (`dial-borders.png`).
- **Cost:** the dial adds about 6 µs a frame (0.04 % of a 60 Hz frame).
  The recording's own frame times (about 300 ms) are the software
  rasterizer's, not the Mac's.
- **Depths to retune** (from the frames): wobble amount at full push
  melts the tesseract out of recognition; plasma at full push covers the
  whole frame; kaleidoscope at full mix replaces the scene. Deconverge,
  double vision, trip colour, fractals, hue cycle and acid read well.
- **Fixed on the way:** the first recording showed the rim labels of the
  two faces colliding and both wobble sectors cut to "Wobbl…". The faces
  now stack, each with a legend.

It cannot show how a stick feels in the hand. That is the list below.

## To try at the pad

1. Load DIAL. Let go of both sticks: is the scene sane? Is anything
   still moving that should not be?
2. Push each direction slowly to the rim. Does each sector's parameter
   arrive smoothly and show plainly at full push? Note any depth that is
   too much or too little.
3. Sweep each stick round the rim, slowly and then fast. Which reading
   is better for which stick? Is petal's sticky border too sticky or not
   sticky enough? Does blend's in-between (two at half) look muddy?
4. Swap the readings and do 3 again on the same routes.
5. With `desk.pad.feel` on follow, does letting go glide home well, or
   should a dial have a feel of its own?

## Open questions

- **8 sectors or 12.** The first sketch put the sectors 30° apart (12 of
  them). This build uses 8 at 45°: the compass names and the panel assume
  8, and wider sectors are easier to hit blind. `DIAL` is one constant;
  12 would need names (clock hours, say: `L.12`, `L.1` …).
- **A centre ring.** Should the inner part of the throw be a dead ring,
  so only a real push picks a sector?
- **Latch.** A third reading where a sector keeps the value you left it
  at (push to set, click to clear) would let more than one parameter be
  up at once. It gives up "let go and it's home".
- **Triggers as a master.** LT / RT could scale the whole dial (one
  `scale` param on every dial route), so one finger sets how hard the
  dial hits.
- **Learn's first route.** Learn pad only lands sectors on a stick that
  is already a dial. A "Learn dial" item in the menu would let you start
  a dial from scratch.
- **Feedback.** Rumble at a sector border (petal) would make it playable
  without looking. GLFW cannot drive rumble, but the 360 pad's USB path
  can.
