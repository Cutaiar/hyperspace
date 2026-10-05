# Plan 18 — Hand and knob feel: the box, a learn's default, knob smoothing, two hands on the camera

**From the Oct 3–4 session at the machine** (Dan and Dillon;
[`15-21-roadmap.md`](15-21-roadmap.md) §2 row 6 and §4 "Plan 18"). The
session asked to "lower hand sensitivity" and "tame rotation", and found
the desk's knobs stepping on wide params. There is no sensitivity
setting to lower. What was felt is what a hand Learn lands with, that a
hand is "in" wherever the tracker can see it, and that a knob moves a
param in the param's detents. This plan changes those three defaults and
adds one camera preset.

Written 2026-10-04 against `plan-15-integration` at 2c3b282 (`finish-line`
plus all of plan 15), by reading the code; no code was changed. Every row
of §1 cites the function as it stands on that commit. Three things were
measured headless on a temp home (the scripts are not kept): what a
learned row does to `rot.rate.XY`, `view.speed` and the camera params
across a hand's travel; what "present" means at the edge of tracking; and
the size of one knob step on the base of each wide param, with the
proposed glide worked as arithmetic beside it. Nobody was available to
answer questions, so every fork met is in §6 with the option taken.

Plan 16 (paper cuts) lands before this plan is built and touches nothing
in `hands/` or `midi.py`. Plan 17 (Learn, Unbind, the desk) runs beside
it; its document did not exist when this was written, so the seam with it
(§2, "Shared with plan 17") is drawn from the roadmap's §5.

## 1. What the owner hit, and what it is

| # | The session said, or the roadmap says | What the code does today | So |
|---|---|---|---|
| 1 | "Lower hand sensitivity" | No such setting exists. A hand Learn ends in `Learn.learn_source` (`learn.py`), which builds `Binding(source, p.id, "position", 1.0, when=when)`: a `position` row at depth 1 on whatever param was armed. `Router.modulate` (`routing.py`) lands it as `clamp(depth · u) − p.norm`: the hand's reading *is* the param's fader, end to end, and the param's own base is ignored while the hand is in. | WP3: a learn lands as a `push` about the base wherever that is the gentler reading, at one depth the session sets. |
| 2 | "Tame rotation" | `rot.rate.*` spans ±`ROT_RATE_MAX` = ±66.56× (`params.py`: `CEIL · DRIVE · 8`, as wide as the reference's largest plane drive), untapered. Measured, a learned roll on `rot.rate.XY` with the default 0.04 dead zone: a level hand reads **0×** (the preset's 1× is gone: the plane stops), 9° of roll is 4.16×, 18° is 11.09×, the ends ±66.56×. A learned height (rest at the bottom) reads **−66.56×** at the bottom and −53× a tenth of the way up. On `view.speed` (`tapers.T_SPEED`, stop then 0.016–4 rad/s) a level centred hand reads 0.25 rad/s whatever the preset set, and the ends are stop and 4 rad/s. | The same package. As a `push` at depth 0.25 a level hand leaves the base alone; on `view.speed` from 0.35 the whole tilt is 0.175–0.70 (an octave each way, 0.31–0.39 inside ±18°); on `rot.rate.XY` from 1× it is −15.6×…+17.6× (−1.8×…+3.8× inside ±18°). The rate range is still wide: see fork 8. |
| 3 | The roadmap: plan 18 owns "`_place`'s op and depth" | `Learn._place` sets neither. It removes the axis's other `position` rows and calls `Bindings.replace_owner`. The op and the depth are the literals in `Learn.learn_source`, which also holds the "same axis again" test (`cur.op == "position"`). | WP3 edits **two** functions in `learn.py`: `learn_source` and `_place`. |
| 4 | "Centred axes" | `hands/core.py`: `BIPOLAR = {"x", "z", "roll", "pitch", "yaw"}`. `AxisSettings.__post_init__` gives those `bipolar=True`, `deadzone=0.04`, `rest_value=0.5`; every other feature (height `y`, `grab`, `pinch`, `grab_angle`, `pinch_mm`, the four `pinch_*` ratios) gets `bipolar=False`, dead zone 0, rest 0. On the default rig (`DEFAULT_DOFS`) five of each hand's six axes are centred and height is the one-sided one. `bipolar` is also a per-axis setup param (`hands.<axis>.bipolar`, labelled "Centred"), and `HandsIO.rests` publishes each axis's `rest_value` for `Router.rest_of`. | "Centred" is read from the axis's setup at the moment of the learn, not from the feature table. A learned push carries no `rest` of its own, so it follows the axis's (DECISIONS: "Push is centred where the source rests"). |
| 5 | "Today 'in the box' is only the tracker's confidence" | `HandsIO.poll`: `here = h is not None and h[1] >= self.min_conf` (`[hands] min_confidence`, 0.1), and `LeapSource.latest` drops a frame older than `STALE_S` (0.25 s). The ranges in `hands.json` only *normalise* (`AxisState.norm`, clamped to 0–1 in `poll`). Measured: a palm at (600, 900, 500) mm, far outside every range, is present and reads 1.0 on x, y and z. A hand at confidence 0.05 is absent. A confidence alternating 0.09 / 0.11 flips presence 59 times in 60 frames and the lane is `NaN` on 30 of them: the floor has no hysteresis. | WP1: explicit bounds, with a Schmitt edge. A hand working the APC40, or a passer-by's, is tracked today and performs. |
| 6 | "Explicit bounds in `hands.json`" | The file is `{"schema": "hyperspace.hands/1", "axes": {"left.x": {"lo": …, "hi": …}, …}}` (`save_calibration`). `load_calibration` reads `axes` and never looks at `schema`. `HandsIO.save_ranges` overwrites the file with no backup, from the sweep's end (`_finish_calibration`) and from "reset ranges". Nothing rewrites it at load. | WP1 adds one optional key, `box`. A file without it reads exactly as today. |
| 7 | "Set by the existing calibration sweep" | The sweep samples only the axes the rig has: `self._cal[a.name].append(st.raw)` inside the axis loop of `poll`. A rig whose `dofs` leave out x, y or z records nothing about where the palm was. Each range is the 2nd–98th percentile of at least `CAL_MIN_SAMPLES` (30) readings. | WP1 samples the palm's x, y, z during a sweep whatever the `dofs`. |
| 8 | "Drawn on the HANDS page's box" | `hands/panel.py::_box` draws a 190 × 92 px frame (`BOX_W`, `BOX_H`) from above at a fixed scale (x over ±260 mm, z over ±160 mm), a dot per hand from `io.frame[side]`, its size the height. `io.frame[side]` is `None` for an absent hand, so nothing is drawn for one. The pinch switches sit beside the box (`page`: "the page has to fit the control window"). | The bounds are drawn inside the same 190 × 92; a hand tracked but outside is drawn hollow. No new height on the page. |
| 9 | The ghost hands' camera "fits the calibrated box" | `ghost.box_of` takes the union over both hands of each hand's x, y, z *axis range* (`HandsIO.axes` / `.state`), the defaults where the rig lacks an axis. `HandsIO._skeletons` keeps a skeleton only for a hand that is present. | With bounds set, `box_of` returns them; a hand outside them is absent, so its ghost fades out at the edge (`ghost.FADE_OUT`), which is the boundary made visible. |
| 10 | Knobs "need smoothing" | `MidiIO._apply` (`midi.py`), `abs` branch: `p.set_norm(u)` with `u = value / 127`. `Param.set_norm` is `set_position(round(u · steps))`: the value lands on a **detent**, and an untapered param has 100 (`RAW_STEPS`). Measured over all 128 CC values: 101 distinct values on every untapered param. One step on the base: `rot.rate.*` 1.33×; `camera.pan.*` 80 px; `camera.yaw` and `dream.hue` 3.6°; `camera.pitch` 1.8°; `camera.zoom` ×1.069 (6.9 %); `view.speed` (160 taper steps, 128 reachable) up to 0.26 rad/s at the top; `master.gain` up to 0.52×. A slow turn, one CC step every 50 ms for two seconds, moves the base on 31 frames out of 120, a whole detent each time. | WP2. The staircase is the detent grid more than the 7 bits. |
| 11 | "A short slew on values arriving … written through `Param.set_norm`" | A slew that writes each frame through `set_norm` lands on the same 101 values, so a slow turn is exactly as stepped as today. Writing the base between detents already has two callers: `Router.follow_macros` (`q.set(q._value_of_norm(…))`, "without snapping to a detent") and `Param.nudge` (the mouse and the sticks). | WP2's glide writes `Param.set(p._value_of_norm(y))` on the way and ends with the very `set_norm(u)` today's code makes, so the value *rests* where it rests today. Still a scene-setter writing the base; never an offset. Fork 10. |
| 12 | What `poll` knows of time | `MidiIO.poll()` takes no `dt`. The adapter has kept `self.clock` since plan 15 WP4 (`_now`, the hold and the blink). | The glide is timed on that clock; tests inject it. |
| 13 | Ring feedback and a value still moving | `MidiIO.feedback` sends `round(p.norm · 127)` on the knob's own CC whenever it changes, and `_rebase` then treats the endless encoder as sitting there (`apc40.RING_REBASES_KNOB`, hand check 31, still not seen at the machine). A ring that followed a base lagging behind the knob would re-base the encoder *backwards* on every frame of a turn. | During a glide the ring shows where the base is going (the value the knob sent, as landed), which is the same message today's code sends. |
| 14 | "The undo's settle time must outlast it" | `undo.SETTLE_S = 0.4` ("Plan 18's knob slew must stay under it"). `Undo._observe` stamps `_changed_at` on every frame the bases differ; `tick` closes the open step after `SETTLE_S` of quiet. | WP2 bounds the glide at 0.25 s and a test holds the two constants together. What it does to "one knob turn is one step" is in WP2. |
| 15 | "One session param" for each of the two numbers | Session is by group (`params.SESSION_GROUPS`). `hands.*` is a session group and `hands.core.register` declares its global feel there. `desk.shift` (`routing.register_desk`) is in a group, `desk`, that is in neither list; it is `persist=False`, so `test_params.py`'s "every persisted param is in exactly one" never sees it. | The learn depth is `hands.learn_depth`. The knob smoothing is `desk.slew`, and `desk` joins `SESSION_GROUPS` (fork 13). |
| 16 | "A new session feel setting might belong on a free global knob" | `apc40.DEFAULT_MAP`, global layer: K1–K5 are `hands.smooth`, `hands.response`, `hands.catch`, `hands.sel.return`, `tempo.bpm`; K6–K8 have no row ("6–8 are free, so dark and dead under SHIFT"). A new factory row also has to reach every existing `bindings.json` through `routing.remap_factory`, with one more backup and rewrite. | Not taken (fork 15). |
| 17 | "Two-hand orbit camera … only if it needs no new axis" | The camera params are `camera.yaw` (±π, wraps), `camera.pitch` (±1.55), `camera.zoom` (0.05–40, log), `camera.pan.x` / `.y` (±4000 px). A hand lane is one hand's own reading (`hands.core.Layout`); a target takes one performer (`Bindings.owner`); `Router.modulate` adds one row's offset. An orbit steered by the hands *relative to each other* (their separation, the angle of the line between them) needs the difference of two lanes, which is a new lane. | Buildable as each hand owning some of the camera params, with no new axis (WP4). The steering-wheel form is not built (fork 17). |
| 18 | The roadmap: plan 18 "runs beside 17 because its code is `hands/` and `midi.py`, not `learn.py` and the UI" | The four items need `hands/core.py`, `hands/panel.py`, `midi.py`, and also `learn.py` (two functions), `routing.py` (`register_desk`, `Bindings`), `params.py` (one tuple), `ui.py` (one row on SYSTEM), `ghost.py` (`box_of`) and `preset.py`. | §2's shared-files table says who edits which lines. |
| 19 | "Learning it onto another param moves it" | True of `position` rows only: `_place` removes rows with `x.op == "position"`, and `test_learn.py::test_a_learned_axis_drives_one_param` pins "its push rows stay". Until now every learned row was a `position` and every `push` was written by hand. | Once learns land as pushes the rule has to be restated (fork 7). |
| 20 | "Rate-type params under a hand are allowed … `party-noita` keeps its two" | Nothing in the code classes a param as rate-type, and nothing warns. `party_noita_routes` (`preset.py`) has `fx.warp.drift` and `fx.tripcolour.pulse` under a hand. | Nothing here flags, warns about or refuses a target. The learn rule reads the axis's `bipolar` flag and the target's declared range, never a list of ids. |

## 2. Work packages

| WP | What | Size | Needs |
|---|---|---|---|
| 1 | **The interaction box** | M | — |
| 2 | **Knob smoothing** | S–M | — |
| 3 | **A learn's default** | S | WP1 merged; plan 17's Learn package on `plan-17-integration` |
| 4 | **Two hands on the camera** (`hands-orbit`) | S | — |
| 5 | **Docs and hand checks** | S | last |

**Waves.** Wave 1: WP1, WP2 and WP4 are built at once; they share no
file. Wave 2: WP3. It starts only when (a) WP1 is merged into
`plan-18-integration`, because both edit `hands/core.py` and
`hands/panel.py`, and (b) plan 17's Learn package (the one that makes
"Learn desk" and "Learn hand ▸ left / right") is on
`plan-17-integration`. `plan-18-integration` then merges
`plan-17-integration` (or `finish-line`, if plan 17 has reached it) and
WP3 branches from the result. If plan 17 slips, WP1, WP2, WP4 and WP5's
share of them can go to `finish-line` without WP3. Wave 3: WP5.

Merge order onto `plan-18-integration`: **WP2, WP1, WP4, (plan 17's
branch), WP3, WP5**. One PR and one merge commit each (decision 30), each
with a demo in its body: WP1 a screenshot of the HANDS page with a box
set and a hand outside it; WP2 a headless script that prints a turn's
bases frame by frame at 0 and at 100 ms; WP3 the ROUTING rows three
learns land with; WP4 the sweep of each axis against its camera param.

**Shared files, and who edits what.** A package may edit only its lines.

| File | WP1 | WP2 | WP3 | WP4 |
|---|---|---|---|---|
| `hands/core.py` | the box: constants, `load_box`, `inside`, `save_calibration(box=)`, `_keep`, `HandsIO.box` / `.outside`, the presence line in `poll`, the palm samples, `_finish_calibration`, `reset_ranges`, `save_ranges`; the module docstring's file paragraph | — | `HandSettings.learn_depth`, one `cont(...)` in `register`, the `learn_source` call in `HandsIO._learn` | — |
| `hands/panel.py` | `_box`, `_status`, `_calibrate`, the module docstring | — | one id in `page`'s feel list | — |
| `hands/__init__.py` | — | — | the docstring's `learn_source(src, when=)` line | — |
| `ghost.py` | `box_of` and its docstring | — | — | — |
| `midi.py` | — | `_apply`'s `abs` tail, `poll`, the ring's value in `feedback`, one rule in `redraw(load=True)`, the new `Slew`, `_aim`, `_glide`, `_land_all`, `_ring_norm`; the module docstring | — | — |
| `routing.py` | — | `SLEW_PARAM`, `SLEW_MAX_S`, `Bindings.slew`, `register_desk` | — | — |
| `params.py` | — | `"desk"` in `SESSION_GROUPS` and its comment | — | — |
| `ui.py` | — | one row in `_page_system`, under "midi" | — | — |
| `learn.py` | — | — | `Learn.learn_source`, `Learn._place`, `PUSH_DEPTH`, `centred_target`, two sentences of the module docstring | — |
| `preset.py` | — | — | — | `hands_orbit_routes`, one `FACTORY_PRESETS` entry |
| `library/presets/hands-orbit.json` | — | — | — | generated (`python -m hyperspace.preset`) |
| `tests/test_routing.py` | — | — | — | the pinned set of factory presets |

Not edited by any package: `hands/signal.py`, `hands/tape.py`,
`apc40.py`, `bindings.default.json`, `undo.py`, `app.py`, `Param` and
`Registry` in `params.py`, and `Router.modulate`.

**Shared with plan 17.** Plan 17 owns `learn.py`'s arming and listening
(`Learn.__init__`, `arm`, `take`, `same_source`, `target_for`,
`resolve_pending`, `said`, `refuse`, and anything it adds to say which
source a learn listens to) and the right-click menu (`ui.Panel._ctx`,
`_learn_hint`, `hands.panel.ctx_rows`, `MidiIO.unbind` / `_learned`).
Plan 18 owns what a learned hand row looks like. Where the two meet:

| File | Plan 17's lines | Plan 18's lines |
|---|---|---|
| `learn.py` | everything but → | in `learn_source`: the keyword arguments, the line that builds the row, and the "same axis again" test; in `_place`: the filter that picks which rows go, and the status text. No other line. |
| `hands/core.py` | in `HandsIO._learn`: which hand's axes count (if it filters there) | in `HandsIO._learn`: the arguments of the `learn_source` call. Everything else in the file. |
| `hands/panel.py` | `ctx_rows`, `_gate_menu` | `_box`, `_status`, `_calibrate`, `page`'s feel list |
| `midi.py` | `unbind`, `_learned`, the learning branch of `_handle` | `_apply`'s `abs` tail, `poll`, `feedback`'s ring value, `redraw`'s load rule, the glide's own methods |
| `ui.py` | `_ctx`, `_learn_hint` | one row in `_page_system` |

Plan 17 merges first wherever they meet. If its Learn package changed
`learn_source`'s positional arguments, WP3 keeps that signature and adds
its two keywords after them.

No code package edits `ARCHITECTURE.md`, `DECISIONS.md`, `ENGINEERING.md`,
`DECISION-REGISTER.md`, `plans/README.md`, `CHECKPOINT.md`,
`11-hand-checks.md` or this file. Each PR body carries its "as built"
paragraph; WP5 folds them in.

### WP1 — The interaction box

**What.** A box in the Leap's own millimetres, kept in `hands.json`. A
hand whose palm is outside it reads absent: its axes read `NaN`, so every
row on them lets go and the base returns that frame (B1), its pinch
switches drop, its presence lane and note go off, and its ghost fades.
The calibration sweep sets the box; "reset ranges" opens it. No new
control.

**Owns.** `hands/core.py`, `hands/panel.py`, `ghost.py::box_of`,
`tests/test_hands.py`, `tests/test_ghost.py`. **Must not touch.**
`hands/signal.py` (`Follower` is unchanged: the catch that already glides
a returning hand is the edge's second half), `hands/tape.py`, `learn.py`,
`routing.py`, `midi.py`, `ghost.py` beyond `box_of`, `config.py` (no
`[hands]` key), and `HandsIO._learn` (WP3's).

**The box.** One box for both hands (fork 2), axis-aligned, on the
palm's position as `features()` reports it: `x`, `y`, `z` in mm, origin
at the camera. Any of the three may be open (no bound). No box at all is
the default, and is today's behaviour exactly.

```python
# hands/core.py
CAL_SCHEMA = "hyperspace.hands/2"
BOX_AXES = ("x", "y", "z")
BOX_MARGIN = 40.0     # mm: the sweep's box stands this far outside what the palms covered
BOX_EDGE = 15.0       # mm: a hand that is in stays in until it is this far past a face
BOX_MIN_SPAN = 120.0  # mm: a coordinate swept over less than this is left open

# "x" / "y" / "z" → (lo, hi) in mm, or None for an open coordinate
Box = dict[str, tuple[float, float] | None]

def load_box(path: Path | None) -> Box | None: ...
def inside(box: Box | None, feats: dict, grow: float = 0.0) -> bool: ...
def save_calibration(path: Path, ranges: dict[str, tuple[float, float]],
                     box: Box | None = None) -> None: ...

class HandsIO:
    box: Box | None                    # None: no bounds, as before this plan
    outside: dict[str, dict | None]    # side → the features of a hand tracked but outside
```

**The file.**

```json
{"schema": "hyperspace.hands/2",
 "axes": {"left.x": {"lo": -214.2, "hi": 18.5}, "…": {}},
 "box": {"x": [-262.0, 262.0], "y": [71.5, 402.0], "z": [-148.0, 131.0]}}
```

- `box` is absent or `null` (no bounds), or an object whose `x`, `y`, `z`
  are each `[lo, hi]` or `null` (that coordinate open).
- **An old file** (`hyperspace.hands/1`, no `box`) loads its `axes` as
  today and has no bounds. Nothing rewrites it at load, so a launch of
  this build leaves the owner's calibration byte for byte.
- `load_calibration(path)` keeps its signature and its return (the
  `axes`). `load_box` reads the same file. Both go on ignoring the
  `schema` string, as `load_calibration` does today. A pair that is not
  two finite numbers with `lo < hi` makes that coordinate open and is
  said once on stderr (`hands: hands.json: box.x: …`): a bad box must
  open, never hide the hands.
- `save_calibration` writes schema 2 and always writes the `box` key.
  Numbers rounded to 3 places like the ranges.
- **Backup.** The first time this build is about to overwrite a file
  that is not schema 2 (a sweep ending, or "reset ranges"), `save_ranges`
  first copies it beside itself as `hands.json.bak-v1`, by an exclusive
  create, or `hands.json.bak-v1-<YYYYmmdd-HHMMSS>` when that name is
  taken: `routing.backup`'s naming and its rule that nothing already
  there is overwritten. It is a small function of `core.py`'s own
  (`_keep(path)`), because this module imports nothing from the package.
  A copy that cannot be made is said in `cal_note` and never stops the
  save. Later overwrites of a schema-2 file are as today, no copy.

**In or out, each frame.** In `HandsIO.poll`, the line that decides
`here` becomes:

```python
tracked = h is not None and h[1] >= self.min_conf
grow = BOX_EDGE if self.present[side] else 0.0
here = tracked and (self.box is None or self._cal is not None
                    or inside(self.box, h[0], grow))
self.outside[side] = h[0] if tracked and not here else None
```

- `inside(box, feats, grow)` is true when, for each coordinate with a
  bound, `lo − grow <= feats[c] <= hi + grow`. `None` box: true.
- **Hysteresis.** A hand that is out comes in only inside the faces; a
  hand that is in leaves only `BOX_EDGE` past one. A hand hovering on a
  face therefore does not flicker (the confidence floor's flicker, §1
  row 5, is the tracker's and is left alone). When it does come back,
  `Follower.step` catches it over `hands.catch` exactly as it catches a
  hand the tracker lost: the lane is live through the catch, so there is
  no jump and no hole.
- **During a sweep** (`self._cal is not None`) the box is not applied,
  or a box could never be swept wider.
- Nothing else in `poll` changes. Presence, the pinch switches
  (`_pinches`), the skeleton (`_skeletons`), the axes and the lanes all
  already key on `here` / `self.present`, so "outside reads absent"
  holds for the routing table, the DAW port and the ghost hands alike.
- A `HandsIO` from before a hot reload has no `box`: read it with
  `getattr(self, "box", None)`, and `outside` the same way.

**The sweep sets it.** While a sweep runs, every fresh frame of a hand
that is `tracked` adds its palm `(x, y, z)` to one list, whatever the
`dofs` (both hands into the same list). `_finish_calibration`, after the
ranges:

- Fewer than `CAL_MIN_SAMPLES` palm samples: the box is left as it was.
- Otherwise, per coordinate: `lo`, `hi` = the 2nd and 98th percentile
  (the ranges' own rule). If `hi − lo < BOX_MIN_SPAN` the coordinate is
  **open** (a sweep that never moved sideways must not make a slot 80 mm
  wide). Else the bound is `(lo − BOX_MARGIN, hi + BOX_MARGIN)`.
- `x` is made symmetric about the camera: `half = max(|lo|, |hi|) +
  BOX_MARGIN`, bound `(−half, half)`. A sweep of one hand must not shut
  the other out.
- All three open: `box = None`.
- `cal_note` gains the result: `calibrated 12 axes · box 524 × 330 ×
  279 mm`, or `… · box: x open (not swept)`.
- The margin is what lets a hand hold an axis at its end stop: the range
  ends at the 98th percentile and the box 40 mm beyond it.

`reset_ranges` also sets `box = None` ("ranges back to the defaults, box
open"). That is the one-click way out of a box that came out too tight;
the proper fix is another sweep. The file can also be edited by hand.

`tools/hands_probe.py --calibrate` ends in the same
`_finish_calibration`, so the probe sets the box too; it is not edited.

**The HANDS page.** The 190 × 92 frame keeps its size and place (the
switches still sit beside it). Inside it, the view from above takes the
left 174 px and a height gauge the right 10 px, 6 px apart:

```
   the box from above (x across, z down)            height
 ┌──────────────────────────────────────────────┐   ┌──┐
 │                                              │   │  │
 │      ┌──────────────────────────────┐        │   │┬ │  y hi
 │      │                              │        │   ││ │
 │      │     ●            ●           │    ○   │   │● │  right hand
 │      │   left    ·    right         │        │   │● │  left hand
 │      │        (camera)              │        │   ││ │
 │      └──────────────────────────────┘        │   │┴ │  y lo
 │                  performer                   │   │  │
 └──────────────────────────────────────────────┘   └──┘
        inner rectangle: the box's x and z            bracket: the box's y
        ● in the box      ○ tracked, outside it (hollow, dim)
```

- The view from above keeps today's fixed scale (x over ±260 mm, z over
  ±160 mm) and clamps to the frame as it does now. The box's x and z
  draw as an inner rectangle in `ui.DIM`; an open coordinate draws no
  line on its sides. No box: no rectangle, and the view is today's.
- A hand in the box: its filled dot, as today (left white, right red,
  size by height). A hand in `io.outside`: a hollow circle in its colour
  at 40 % alpha, at its clamped position.
- The gauge maps 80–400 mm bottom to top (the range the dot's size
  already uses), a tick per hand in its colour, and a bracket from the
  box's `y` lo to hi when it has one.
- The tooltip gains one line: `box x −262…262 · y 72…402 · z −148…131 mm
  — a hand outside it reads absent`, or `no box — calibrate to set one`.
- `_status`: each hand's glyph is `●` in, `◌` tracked but outside the
  box, `○` not seen.
- `_calibrate`: the sweep's tooltip ends "…and the box becomes what your
  palms covered plus 40 mm; a hand outside it reads absent". Under the
  selected axis's range, one disabled line with the box's three ranges,
  or "box open". "reset ranges" keeps its label; its tooltip says it
  opens the box.
- Nothing is dragged and nothing is typed (fork 1).

**The ghost hands.** `ghost.box_of(source)`: for each of x, y, z, when
`getattr(source, "box", None)` has a bound for it, that bound; otherwise
today's union of the axis ranges and defaults. `ghost.camera` then frames
the interaction box padded by `PAD`, and a hand's ghost is drawn exactly
while the hand is inside what the frame shows. With no box the result is
today's to the float.

### WP2 — Knob smoothing

**What.** One session param, `desk.slew`, 0 to 250 ms, **0 by default**.
Above 0, an absolute knob or fader no longer jumps the base from detent
to detent: each value it sends arrives over that long, in a straight
line, and comes to rest on the same value it rests on today. At 0 no
line of today's path is skipped and nothing new runs.

**Owns.** `midi.py`, its lines in the shared table, `tests/test_midi.py`,
`tests/test_desk.py`, `tests/test_undo.py`, `tests/test_params.py`.
**Must not touch.** `Param` and `Registry` (`set_norm`, `set` and
`_value_of_norm` are used as they are), `Router.modulate`, `undo.py`,
`apc40.py`, `MidiIO._learned`, `unbind`, `_fire_holds` and the learning
branch of `_handle`.

**Contracts.**

```python
# routing.py
SLEW_PARAM = "desk.slew"
SLEW_MAX_S = 0.25          # under undo.SETTLE_S (0.4) by more than a slow frame

class Bindings:
    slew: float = 0.0      # seconds; the session's, never written to bindings.json

def register_desk(reg, table):   # beside desk.shift, each guarded by its own `in reg`
    reg.continuous(SLEW_PARAM, "Knob smoothing",
                   lambda: getattr(table, "slew", 0.0),
                   lambda v: setattr(table, "slew", min(max(float(v), 0.0), SLEW_MAX_S)),
                   lo=0.0, hi=SLEW_MAX_S, group="desk", modulatable=False,
                   fmt=lambda v: "off" if v <= 0 else f"{v * 1000:.0f} ms",
                   tip="How long a value from a desk knob or fader takes to arrive. "
                       "Off: it jumps a detent at a time, as before. One setting for "
                       "every knob and fader; buttons and the cue knob are not smoothed.")

# params.py
SESSION_GROUPS = (..., "ui", "desk")

# midi.py
SLEW_TOL = 1e-6            # norm: further than this from our last write, someone else set it

@dataclass
class Slew:
    y: float               # where the base is now, norm, between detents
    target: float          # where it will rest: round(u · steps) / steps
    t: float               # the clock at the last step
    t_end: float           # the clock when it lands: the last message + desk.slew
    wrote: float           # p.norm as read back after our last write

class MidiIO:
    _slews: dict[str, Slew]            # by param id; made on first use (hot reload)
    def _aim(self, p: Param, u: float, seconds: float) -> None: ...
    def _glide(self, now: float) -> None: ...
    def _land_all(self) -> None: ...
    def _ring_norm(self, p: Param) -> float: ...
```

`desk.slew` is persisted (a show keeps it), so it is a session param by
`desk` joining `SESSION_GROUPS`; `desk.shift` stays `persist=False`. A
preset can never name it (D9). It is watched by the undo like any
session param.

**Behaviour.**

- **Where it sits.** In `_apply`'s `abs` branch, after the trigger case
  and after the pickup test have run exactly as today, the last write
  `p.set_norm(u)` becomes:

  ```python
  seconds = getattr(self.table, "slew", 0.0)
  if seconds > 0.0 and p.kind is Kind.CONTINUOUS and not p.integer:
      self._aim(p, u, seconds)
  else:
      self._slews.pop(p.id, None)
      p.set_norm(u)
  ```

  followed by `_note_written(p)` as now. So: `cc` and `pitch` rows with
  op `abs` on a continuous, non-integer param glide. Everything else is
  untouched: `rel` and `rel64` (the cue knob steps detents on purpose),
  `step`, `toggle`, every note op, `hold`, an `abs` row on an enum, a
  toggle, a trigger or an integer param (`view.instances`: its steps are
  the integers).
- **`_aim(p, u, seconds)`.** Take the param's glide, or start one at
  `y = wrote = p.norm` when there is none or when
  `abs(p.norm − s.wrote) > SLEW_TOL`. A new glide's `t` is the time of
  the previous `poll` (kept as `self._polled`, and no further back than
  50 ms), so its first step lands on the frame the message arrives: the
  glide adds no dead frame. Then `s.target = round(u · p.steps) /
  p.steps` (what `set_norm(u)` would land, as a norm) and `s.t_end = now
  + seconds`. One glide per param: a second control on the same param
  re-aims it.
- **`_glide(now)`**, called once per `poll`, after `_fire_holds` and
  before the second `_follow_table`:

  ```python
  seconds = getattr(self.table, "slew", 0.0)
  for pid, s in list(self._slews.items()):
      p = self.reg.get(pid)
      if p is None or abs(p.norm - s.wrote) > SLEW_TOL:
          del self._slews[pid]                  # someone else set it: theirs stands
          continue
      if seconds <= 0.0 or now >= s.t_end:
          p.set_norm(s.target)                  # the write today's code makes
          del self._slews[pid]
      else:
          s.y += (s.target - s.y) * (now - s.t) / (s.t_end - s.t)
          p.set(p._value_of_norm(s.y))          # the base, between detents
          s.t = now
          s.wrote = p.norm
      self._note_written(p)
  self._polled = now
  ```

  A straight line that arrives exactly `desk.slew` after the last
  message: no tail and no snap at the end, because the line's end *is*
  the detent. Worked for a slow turn (one CC step every 50 ms, a
  `camera.pan` knob): today the base moves on 31 of 120 frames, 80 px
  each; at 100 ms it moves on every frame, about 25 px at most. A flick
  of 50 steps in 5 frames: today's largest frame-to-frame move is 11 %
  of the throw, at 100 ms 4.5 %, and the last write is on the first
  frame at or after 100 ms from the last message.
- **Who writes.** `Param.set` and `Param.set_norm`: the base, by a
  scene-setter, in the adapter (ARCHITECTURE §3.2). On a param a
  performer owns, both write `_base`, so the glide moves the return
  value under the hand like any knob. `Param.modulate` is not called.
- **Someone else writes the param mid-glide** (the panel, a key, a
  macro's subscriber, an undo): the next `_glide` sees the base is not
  where it left it and drops the glide. Theirs stands.
- **A preset load mid-glide.** `redraw(load=True)` drops every glide
  whose param is not a session param (`not routing.is_session_id(pid)`)
  before anything else: the load's value stands even when it happens to
  equal the glide's last write. A glide on a session param (the
  crossfader's dim, a band's drive) goes on arriving; a preset never
  moves those (D9).
- **A layer switch mid-glide.** Nothing: the glide belongs to the param,
  not to the control, and finishes arriving. The redraw draws the new
  layer's rings as below.
- **Ring feedback.** `feedback` computes a ring's value from
  `self._ring_norm(p)`: the glide's `target` while the param has one,
  else `p.norm`. So during a turn the ring carries what the knob itself
  just sent, as landed, which is the message today's code sends, and
  `_rebase` re-bases the encoder where the hand has it, never behind it.
  `_rebase` itself is unchanged. DECISIONS' "rings show the base" stands:
  the ring shows the base the knob is setting, a quarter second early at
  most, and still never a performer's offset.
- **Soft pickup.** Unchanged. The pickup test still compares the fader
  with `p.norm`. `_glide` calls `_note_written`, so `_uncatch_moved`
  does not read the adapter's own glide as "moved without us", and a
  caught fader stays caught through it. A fader that is not caught
  writes nothing, as today.
- **The port goes away mid-glide.** `poll`, before it returns for "not
  on", calls `_land_all()`: every glide lands on its target at once.
- **`desk.slew` turned to 0 mid-glide**: the next `_glide` lands
  everything (`seconds <= 0`).
- **Undo.** A glide keeps writing the base for up to `desk.slew` after
  the knob stops, and that changes three things, all bounded:
  1. *One turn is still one step.* The step opens on the first write.
     Every later write, the landing included, comes no more than
     `desk.slew` ≤ 0.25 s after the one before, which is under
     `SETTLE_S`, so nothing closes the step inside a turn even on frames
     where an in-between write happens not to move the fingerprint. It
     closes `SETTLE_S` after the landing, and its label reads the landed
     value.
  2. *Two turns merge when they are closer than `SETTLE_S + desk.slew`*
     (0.4 s today; 0.5 s at 100 ms; 0.65 s at the maximum).
  3. *⌘Z during a glide.* `Undo._swap` closes the step as it stands and
     puts the earlier value back; the glide sees a write that is not its
     own and stops, so the undo holds. A redo then returns to where the
     glide had got to, not to where the knob was heading.
  `SLEW_MAX_S` is 0.25 so that (1) survives a 100 ms frame. A test
  asserts `routing.SLEW_MAX_S <= undo.SETTLE_S − 0.1`.
- **At 0** `_aim` is never called, `_slews` stays empty, `_glide` loops
  over nothing and `_ring_norm` returns `p.norm`: every base and every
  message sent is today's. Every existing test in `test_midi.py`,
  `test_desk.py` and `test_undo.py` passes unedited; that is the proof.
- **The page.** `self._row("desk.slew")` on SYSTEM, first under the
  "midi" section header. No other widget; no per-control setting; no
  row on the desk (fork 15).

### WP3 — A learn's default

**What.** A hand Learn lands as a `push` about the param's base wherever
either end is centred, at one depth the session sets
(`hands.learn_depth`, 0.25). Only a one-sided axis on a one-sided param
(height on brightness) still lands as the fader. Rows that already exist
are never rewritten: this is what a *new* learn lands with.

**Starts** after WP1 is merged and plan 17's Learn package is on its
integration branch (see "Waves"). **Owns.** In `learn.py`:
`Learn.learn_source` and `Learn._place`, the two module-level additions
below, and the two docstring sentences that say what a hand learn writes.
In `hands/core.py`: `HandSettings.learn_depth`, its `cont(...)` in
`register`, and the `learn_source` call at the end of `HandsIO._learn`.
One id in `hands/panel.py::page`'s feel list; one line of
`hands/__init__.py`'s docstring. `tests/test_learn.py`,
`tests/test_hands.py`, `tests/test_hand_names.py`. **Must not touch.**
Every other function in `learn.py`; how `_learn` chooses the axis or the
hand; `routing.py` (`Binding`, `Router.modulate`, `rest_of` are used as
they are); any file under `library/presets/`.

**Contracts.**

```python
# learn.py
PUSH_DEPTH = 0.25          # a push learn's depth when the adapter names none

def centred_target(p: Param) -> bool:
    """A continuous range centred on zero, by declaration: no taper, not
    log, lo == -hi (rot.rate.*, rot.phase.*, camera.yaw / pitch / pan.*,
    dream.hue, any effect uniform declared that way)."""

class Learn:
    def learn_source(self, source: str, when: str | None = None, *,
                     centred: bool = False, depth: float | None = None) -> None: ...

# hands/core.py
@dataclass
class HandSettings:
    learn_depth: float = 0.25

# in register(), with the global feel:
cont(f"{GROUP}.learn_depth", "Learn depth", g, "learn_depth", 0.05, 1.0,
     fmt=lambda v: f"{v:.2f}",
     tip="The depth a hand Learn lands with when it lands as a push — the number "
         "the ROUTING row shows. 0.25: the whole tilt moves the param a quarter of "
         "its throw, half each way from where you set it. Rows you already have "
         "keep theirs.")

# the end of HandsIO._learn
a = self.axes[best]
learn.learn_source(self.address(best), when=gate, centred=bool(a.bipolar),
                   depth=float(self.settings.learn_depth))
```

`hands.learn_depth` is a `hands.*` param like `hands.smooth`: session by
group, not modulatable, saved by a hands setup and by the show, learnable
onto a knob by right-click like every param. `PUSH_DEPTH` and the
dataclass default say 0.25 twice because `hands/core.py` imports nothing
from the package; a test pins them equal.

**The rule**, in `learn_source` where the row is built today (the
resolved target `p` is in hand):

| The target | A centred axis (`centred=True`) | A one-sided axis |
|---|---|---|
| continuous, range centred on zero (`centred_target(p)`) | `push`, depth D | `push`, depth D |
| any other continuous param | `push`, depth D | `position`, depth 1 — today's row |
| an enum, a toggle, a trigger | `position`, depth 1 — today's row | `position`, depth 1 — today's row |

- D is `depth`, or `PUSH_DEPTH` when the caller passed none. A push row
  is `Binding(source, p.id, "push", D, when=when)` with `rest` left
  `None`, so it is centred on the axis's own rest, resolved every frame
  (`Router.rest_of`): 0.5 on a centred axis, 0 on a one-sided one, and
  whatever the setup later makes them.
- What that gives: a level centred hand, or a height at the bottom, adds
  nothing, so the preset's value shows until the hand moves. A centred
  axis moves the param ±D/2 of its throw. A one-sided axis on a centred
  range (height on `rot.rate.XY`) adds 0 to D upward from the base
  instead of starting at full reverse.
- A discrete target keeps the position row because a push of 0.25 about
  a toggle's base never crosses `MOD_ON` (`params.py`): the learn would
  land and do nothing.
- Called with neither keyword (a test, another adapter) on a target that
  is not centred on zero, the row is today's, field for field.
- Nothing reads the target's id or group, and nothing is refused,
  flagged or warned about: a rate-type param under a hand lands by the
  same table as any other (roadmap §7).

**The same axis again.** Today: when the target's performer is this same
source *and a `position` row*, only its gate is refreshed. That test
drops the op: when the target's performer is this same source, whatever
its op, the learn refreshes `when` and changes nothing else. The row's op
and depth (a preset's, or one the owner tuned on ROUTING) stay.

**One axis, one param** (`_place`; fork 7). Today the axis's other
`position` rows go before the new row lands, and its push rows stay.
With learns landing as pushes, the filter becomes "the axis's other
performer rows" (`x.is_performer`, the same source by `same_source`,
another target), whatever their op, and the status line says what moved:
`learned view.speed ← hand right.roll pushes +0.25 (into the preset;
moved from rot.phase.XW)`. It is one undo step as before (`undo.push` is
already the first line of `_place`), so one ⌘Z brings the rows back.

**The page.** `"learn_depth"` joins the list of ids under HANDS' "feel &
calibration" header, after `catch`. No other widget. ROUTING's depth
field on each row is where one row is tuned, as today.

### WP4 — Two hands on the camera

**What.** One factory preset, `hands-orbit`: the right hand orbits the
camera, the left hand pans and zooms it. Routes onto the camera params
that exist, from axes that exist. Not a mode, no new source.

**Owns.** `preset.py` (`hands_orbit_routes` and one `FACTORY_PRESETS`
entry), the generated `library/presets/hands-orbit.json`,
`tests/test_presets.py`, and the pinned set in `tests/test_routing.py`. **Must not touch.** `hands/`, `routing.py`,
`params.py`, every other preset and every show's bank (it is in the list,
on no F-key).

**Behaviour.**

```python
def hands_orbit_routes() -> list[Binding]:
    return [_push("R", "x", "camera.yaw", 0.5),       # sideways: orbit, ±90°
            _push("R", "pitch", "camera.pitch", 0.5),  # fingers up: look down, ±44° (as FACES)
            _push("L", "x", "camera.pan.x", 0.1),      # as FIELD: fly sideways
            _push("L", "z", "camera.pan.y", 0.1),      # as FIELD: reach in
            _push("L", "y", "camera.zoom", 0.3)]       # raise: zoom in

"hands-orbit": Factory(hands_orbit_routes, dict, "hands-orbit",
                       "Two hands on the camera: the right hand orbits (sideways turns, "
                       "fingers up tips), the left pans (sideways, reaching in) and "
                       "zooms (height).", desk=None),
```

Every row is a push from its axis's own rest, so a level, low or absent
hand adds nothing and the camera the mouse set stays (plan 12's rule for
a hand row). `values` is `dict` and `desk` is `None`, as `hands-play`:
the look is the app's defaults and the desk the factory preset layer.
The depths are a first cut, to be judged at the machine (check N9).

### WP5 — Docs and hand checks

**Owns.** `ARCHITECTURE.md` (§2: a hand outside the box is absent before
any lane is fed; §3.2: the glide among the scene-setters, the ring
showing a glide's target; §3.4: a learned row's op by the table above;
§3.7: the knob row, the Learn row; §4: `hands/core.py`'s box),
`DECISIONS.md` (rows for the box, the learn default, the smoothing;
the "Learn on a hand writes a `position` route" history; the three-places
row gains "the box is `hands.json`'s"; the plan 12 preset row is left
alone), `ENGINEERING.md`, `DECISION-REGISTER.md` (rows for forks 1, 3, 6,
7, 8, 12 and 17, each "built on the recommendation; confirm or overturn"
with its cost to reverse), `plans/README.md` (a row for this plan),
`CHECKPOINT.md`, `11-hand-checks.md` (§8 below as group N; check 15's
pass text gains the box; checks 19 and 22 say "pushes" where a learn now
does), and this file's "As built".

## 3. Parameter budget

Everything the plan adds, and what each replaces.

| Added | Kind | Replaces, or why nothing |
|---|---|---|
| `hands.learn_depth` | 1 session param, 1 row under HANDS' collapsed "feel & calibration" | Replaces the literal `1.0` in `learn_source`, and opening ROUTING after every learn to turn that row's depth down. It is the route's own depth, the number the ROUTING row already shows; no new concept. |
| a learn's op by axis and target | a default | Replaces `position` on everything. No setting: the table in WP3 is the rule. |
| `desk.slew` | 1 session param, 1 row on SYSTEM | Nothing: the desk had no smoothing. One number for every knob and fader. Off by default (fork 12). |
| `desk` in `SESSION_GROUPS` | a group name in a tuple | Nothing; `desk.shift` already lived in that group, unsaved. |
| `hands.json`: `box`; schema 2 | 1 optional file key | Nothing: "in the box" had no bounds. Written by the sweep, cleared by "reset ranges"; no widget edits it. |
| `hands.json.bak-v1` | a file, written once | Nothing; the owner's calibration before this build first rewrites it. |
| the box's rectangle, the height gauge, the hollow dot | a drawing in the existing 190 × 92 frame | Nothing; no control, no new height on the page. |
| `◌` in the HANDS status line | a glyph | Nothing; without it "tracked but outside" and "not seen" look alike. |
| `hands-orbit` | 1 factory preset | Nothing. The session asked for it; it is a file in the list, on no F-key, and plan 19's "hide" removes it in one click if it is not wanted. |
| `learn_source(centred=, depth=)` | 2 keyword arguments | Nothing; internal. |

Rejected because a default or an existing concept does the job:

- A "sensitivity" param per hand or per axis (the route's depth is the
  sensitivity, and the curve and dead zone already shape an axis).
- A per-route "learned at" extra, or an op picker in the Learn menu (the
  ROUTING row's op and depth fields exist).
- A warning or a refusal on rate-type targets (the owner, 2026-10-04).
- Six sliders for the box's faces, drag handles on the drawing, a margin
  setting, a hysteresis setting, a box per hand, an on/off switch for
  the box (forks 1–3).
- A `[hands] box` key in `config.toml` (the box is the room's, and
  `hands.json` is where the room's numbers live).
- Smoothing per control, per layer or per param; a curve for the glide;
  a second number for faders.
- A row for either new number on the global layer's free knobs K6–K8
  (fork 15).
- A camera "orbit mode", and derived two-hand axes (fork 17).

## 4. What this plan does not change

- **The control model** (ARCHITECTURE §3). Scene-setters write the base:
  the glide is the MIDI adapter writing `Param.set` / `set_norm`.
  Exactly one performer per param writes an offset through
  `Router.modulate`, which is not edited. `Registry.apply()` lands both.
  The render stack only reads.
- **The hands boundary.** `hands/core.py` and `hands/signal.py` import
  nothing from the package; `panel.py` is the one adapter
  (`tests/test_hands_boundary.py`). The box, its file and its backup are
  `core.py`'s own code; the learn's shape reaches `learn.py` as two
  duck-typed keywords.
- **B1**: "A hand out of the box reads NaN on its axes, so every row on
  them lets go and the base returns that frame … the return catch stays
  live." The box only changes which hands count as out. `Follower` is
  untouched.
- **"Hands grab; they never yield. No pickup on a performer row."** A
  hand entering the box takes its rows at once, through the catch.
- **"Two ops. push … position …"** and **"Push is centred where the
  source rests."** A learn picks between the two ops that exist and
  leaves `rest` to the source.
- **"Twelve axes … No gesture vocabularies, no more DOFs."** No lane is
  added. `hands-orbit` is five rows; the steering-wheel orbit is not
  built because it would need one.
- **"Rig settings (`[hands]`), box ranges (`hands.json`) and performance
  settings (a `hands` preset) live in three places."** The box is with
  the ranges; the learn depth is with the feel; no `[hands]` key is
  added.
- **"Rings show the base"**; **D7**: "the faders soft-pick-up", "knobs
  jump … the encoder re-based by the ring message". `_rebase` and the
  pickup test are unchanged; a ring never shows a performer.
- **Decision 9**: the global layer's track knobs are the four hand-feel
  settings and BPM, three free. Unchanged.
- **D5 / D6 / D8**: nothing is learned into the global layer, no
  invariant control changes, an unmapped control is dark.
- **D9**: a preset never moves a session param. `desk.slew` and
  `hands.learn_depth` are session.
- **The ghost hands are display-only** and read the skeleton raw. They
  show a hand exactly while it is present, which now means "in the box".
- **Rate-type params under a hand are fine** (the owner, 2026-10-04).
  `rot.rate.*` keeps its ±66.56× range and its linear map: the `legacy6`
  routes' depth (`routing.ROT_DEPTH`) is derived from it, and that is
  the parity anchor.
- **Existing rows.** No preset file is rewritten and no row in a loaded
  table is converted: the party presets' pushes, the `hands-*` presets'
  positions and the owner's own learned rows play as they did.
- **`undo.SETTLE_S`** stays 0.4 and `undo.py` is not edited.
- `[hands] min_confidence` and its lack of hysteresis (§1 row 5): the
  tracker's edge, not the box's. Left as found.

## 5. Exit criteria

### Headless: named tests

**WP1** (`tests/test_hands.py` unless a file is named)

| Test | Proves |
|---|---|
| `test_no_box_is_todays_presence` | with no `box`, a palm far outside every range is present and its lanes read as before |
| `test_a_hand_outside_the_box_reads_absent_everywhere` | lanes `NaN`, presence lane 0, presence note off, pinch switches dropped, `skeleton` without that side, `outside[side]` holding its features |
| `test_a_hand_outside_the_box_releases_its_rows_and_the_base_returns` | through the table (`make_app`): a `position` row and a `push` row both let go the frame the palm leaves (B1's own assertions, with the box as the cause) |
| `test_the_boxs_edge_has_hysteresis` | a palm alternating ±5 mm about a face never flips; it leaves only `BOX_EDGE` past the face and re-enters only inside it |
| `test_a_hand_re_entering_the_box_is_caught_not_jumped` | `Follower` goes through `CATCH`; the lane is live on the first frame back |
| `test_an_open_coordinate_bounds_nothing` | `"y": null`: any height is in |
| `test_the_sweep_sets_the_box_with_its_margin_and_a_symmetric_x` | one hand swept: x symmetric about 0, each face `BOX_MARGIN` outside the percentiles; the other hand is inside |
| `test_a_coordinate_not_swept_is_left_open` | a sweep that never moves sideways: `x` is `None`; nothing swept wide enough: `box is None` (`test_calibration_sweep_sets_and_saves_ranges` passes unchanged) |
| `test_the_box_is_not_applied_during_a_sweep` | with a tight box set, a sweep sees the hand everywhere and ends with a wider box |
| `test_the_palm_is_sampled_whatever_the_dofs` | `dofs = ["roll", "pitch"]`: a sweep still makes a box |
| `test_reset_ranges_opens_the_box` | `box is None` in memory and `null` in the file |
| `test_an_old_hands_json_reads_as_before_and_is_not_rewritten_at_load` | a schema-1 file: same ranges, no box, the file's bytes and mtime unchanged after construction and 60 polls |
| `test_the_first_rewrite_of_an_old_file_keeps_a_backup` | `hands.json.bak-v1` holds the old bytes; a second sweep makes no second copy; an existing `.bak-v1` is never overwritten |
| `test_a_malformed_box_opens_and_says_so` | `[5, 1]`, a string, a missing pair: that coordinate open, one stderr line, the hands still present |
| `test_the_box_round_trips_through_the_file` | save, a new `HandsIO`, the same box |
| `test_hands_page_draws_the_box_and_a_hand_outside_it` | the page draws with a box, with an open coordinate, with a hand in `outside`, and with no tracker (`test_hands_page_draws_live_and_offline` passes unchanged) |
| `test_ghost.py::test_the_camera_frames_the_interaction_box_when_one_is_set` | `box_of` returns the box's bounds, and the axis ranges for an open coordinate; `::test_the_box_is_the_calibrated_ranges_else_the_defaults` passes unchanged |
| `test_ghost.py::test_a_hand_outside_the_box_fades_out` | absent to the ghost, by the existing fade |
| `test_hands_boundary.py` (all three) | unchanged and green: `core.py` gained no host import |
| `test_ui_shell.py::test_every_page_fits_the_control_window` | HANDS, measured full, still does not scroll |

**WP2** (`tests/test_midi.py` unless a file is named)

| Test | Proves |
|---|---|
| `test_smoothing_is_off_by_default_and_every_write_is_immediate` | `desk.slew` is 0 on a fresh table; a CC lands that poll; `_slews` stays empty |
| `test_a_smoothed_knob_arrives_in_a_straight_line_and_rests_on_the_detent` | fake clock, 100 ms: the base moves on every poll, between detents, and at 100 ms equals exactly what `set_norm(u)` gives |
| `test_a_glide_starts_on_the_frame_of_the_message` | the first poll after a message already moved the base |
| `test_a_new_message_re_aims_the_glide_from_where_it_is` | no jump back to the old target; one glide per param |
| `test_the_ring_shows_where_the_knob_is_going` | during a glide the ring CC sent is `round(target · 127)`, never a lagging value; `b.last_hw` after `_rebase` is the knob's own position |
| `test_a_fader_keeps_its_catch_through_a_glide_and_an_uncaught_one_writes_nothing` | `_uncatch_moved` does not fire on the adapter's own glide; pickup as before |
| `test_someone_elses_write_stops_a_glide` | a `Param.set` from outside mid-glide stands; the glide is gone |
| `test_buttons_relative_knobs_and_discrete_targets_are_not_smoothed` | `rel`, `rel64`, a note `set`, an `abs` row on an enum, on a toggle and on `view.instances`: immediate, with smoothing on |
| `test_turning_smoothing_off_or_losing_the_port_lands_every_glide` | both roads to `_land_all` / the `seconds <= 0` branch |
| `test_a_glide_on_a_hand_owned_param_moves_the_return_value` | the base glides under a live `position` row; the effective value is the hand's; no `modulate` call from `midi.py` (`test_routing_boundary.py` green) |
| `test_desk.py::test_a_layer_switch_leaves_a_glide_to_finish` | SHIFT mid-glide: the param still arrives; the new layer's rings are drawn |
| `test_desk.py::test_a_preset_load_stops_a_glide_on_a_performance_param_and_not_on_the_dim` | the load's value stands; the crossfader's `output.dim` goes on arriving |
| `test_undo.py::test_a_smoothed_knob_turn_is_one_step` | CCs through `MidiIO` at 250 ms with the tick running: one step, labelled with the landed value; undo puts back the value before the turn |
| `test_undo.py::test_undo_during_a_glide_holds` | ⌘Z mid-glide: the earlier value stays through the next polls |
| `test_undo.py::test_the_slew_can_never_outlast_the_settle_time` | `routing.SLEW_MAX_S <= undo.SETTLE_S − 0.1`, and the param's `hi` is `SLEW_MAX_S` |
| `test_params.py::test_every_persisted_group_is_performance_or_session` | green with `desk.slew` persisted and `desk` a session group |
| `test_presets.py::test_a_preset_load_never_touches_a_session_param` (extended) | a load and a show load leave `desk.slew`; a show save and load round-trips it |
| `test_ui_shell.py::test_every_page_fits_the_control_window` | SYSTEM with its new row |
| every existing test in `test_midi.py`, `test_desk.py`, `test_undo.py` | unedited and green: at 0 the adapter is today's |

**WP3** (`tests/test_learn.py` unless a file is named)

| Test | Proves |
|---|---|
| `test_a_centred_axis_learns_as_a_push_about_the_base_at_the_learn_depth` | `learn_source(…, centred=True, depth=0.25)` on `view.speed`: `("push", 0.25, rest None)`; through the router a mid reading leaves the base, the ends move it ±0.125 norm |
| `test_a_one_sided_axis_on_a_one_sided_param_is_still_the_fader` | `centred=False` on `view.bright`: `("position", 1.0)`, equal to today's row field for field |
| `test_a_one_sided_axis_on_a_zero_centred_range_pushes_up_from_the_base` | `rot.rate.XY`, `camera.yaw`, `camera.pan.x`: `push`; a reading of 0 adds nothing |
| `test_a_discrete_target_keeps_the_position_row` | a toggle, an enum and a trigger, from a centred axis |
| `test_centred_target_reads_the_declared_range` | true for `rot.rate.*`, `camera.yaw`, `camera.pitch`, `camera.pan.*`, `dream.hue`; false for `view.speed`, `view.bright`, `camera.zoom`, `fx.mix` |
| `test_no_target_is_refused_or_flagged` | every modulatable continuous param in the registry takes a learn from each kind of axis with `refused` false and no `pending` |
| `test_the_same_axis_again_only_refreshes_the_gate_whatever_the_op` | a push row with a tuned depth keeps its op and depth |
| `test_a_learned_axis_drives_one_param` (rewritten) | the axis's other performer rows go, push or position; the status names what moved; other axes' rows stay |
| `test_a_learn_is_one_undo_step` (extended) | one ⌘Z brings back the rows a learn moved |
| `test_the_two_default_depths_agree` | `learn.PUSH_DEPTH == HandSettings().learn_depth` |
| `test_hands.py::test_learn_passes_the_axiss_centredness_and_the_sessions_depth` | roll: `centred=True`; height: `False`; an axis whose "Centred" was switched off: `False`; `hands.learn_depth` at 0.5 lands 0.5 |
| `test_hands.py::test_learn_depth_changes_only_the_next_learn` | a row learned at 0.25 stays 0.25 after the param moves |
| `test_hands.py::test_learn_takes_the_axis_that_moved_as_a_position_route` (renamed, updated) | the moved pitch on `view.inst_amp` is now `("push", 0.25)`; the rest of its assertions follow the push |
| `test_hands.py::test_setup_is_registry_params_that_round_trip` | `hands.learn_depth` saves and loads with a setup |
| `test_plan12_presets.py`, `test_presets.py::test_the_party_presets_routes_are_the_codes`, `::test_write_factory_regenerates_every_factory_file` | unchanged and green: no factory row moved |
| `test_hands_boundary.py`, `test_ui_shell.py::test_every_page_fits_the_control_window` | green |

**WP4**

| Test | Proves |
|---|---|
| `test_presets.py::test_hands_orbit_is_five_pushes_onto_the_camera` | the rows; every target a real `camera.*` id; every source one of `preset.HAND_AXES` |
| `test_presets.py::test_an_absent_or_level_hand_leaves_the_orbit_camera_alone` | through a `HandsIO` on fake hands: no hand, and both hands at rest, move no camera param off its base |
| `test_presets.py::test_each_orbit_axis_moves_its_camera_param_as_its_row_says` | a sweep of each axis: the sign and the size at the ends |
| `test_routing.py`'s pinned set of `FACTORY_PRESETS` (in the test that walks every factory route), `test_presets.py::test_write_factory_regenerates_every_factory_file`, `::test_every_factory_presets_hand_rows_are_named`, `::test_the_routing_presets_are_full_factory_presets` | the new key, its generated file, its named rows |

**Every package**: `uv run pytest -q` and `uv run ruff check` green on
the integration branch after its merge, run with `HYPERSPACE_HOME` on a
temp folder. No agent reads, lists or writes `~/Hyperspace`.

### At the machine

Group N, §8: checks N1–N9, calibration first.

## 6. Forks

Each was settled without the owner. The cost to reverse is what it takes
to switch to another option after the build.

**1. How the box is set.**

| Option | Trade-off |
|---|---|
| **(a) The calibration sweep sets it: what the palms covered, plus 40 mm** | No new control. The box is where the performer actually played. A careless sweep makes a careless box; another sweep or "reset ranges" fixes it. |
| (b) Drag the faces on the HANDS drawing | Direct. The view is from above, so height needs a second drawing and handles; hit-testing in a 190 px frame at arm's length. |
| (c) Six sliders | Exact. Six controls for a thing set once per venue. |

**Recommended: (a).** The file is plain JSON for the rare hand edit.
Reverse: (b) or (c) add widgets over the same `HandsIO.box`.

**2. One box or one per hand.**

| Option | Trade-off |
|---|---|
| **(a) One box, x symmetric about the camera** | Three ranges. Hands may cross. A one-hand sweep cannot shut the other hand out. |
| (b) A box per hand | Each hand kept to its side. Six ranges, two rectangles, and a hand crossing the middle drops out. |

**Recommended: (a).** Each hand's own side is already its x *range*.
Reverse: the file's `box` becomes two objects; `inside` takes the side.

**3. A switch for the box.**

| Option | Trade-off |
|---|---|
| **(a) None: the box exists when the file has one; "reset ranges" opens it** | Nothing to learn. Opening the box also drops the calibrated ranges. |
| (b) A "use box" checkbox on HANDS | Keeps the ranges while the box is off. One more control, for something a sweep fixes in 20 s. |

**Recommended: (a).** Reverse: one checkbox and an `on` key in `box`.

**4. The ghost hands' camera.** (a) frames the axis ranges as today:
with a box 40 mm wider, a hand in the margin can sit at the frame's
edge. **(b) frames the box when there is one**: the frame is exactly
where a hand counts. **Recommended: (b).** Reverse: one branch in
`box_of`.

**5. Is a hand outside the box still drawn as a ghost?** (a) yes, dim:
shows people where the edge is, but a hand that performs nothing is on
the glass. **(b) no: absent everywhere**; the fade at the edge is the
cue, and the HANDS page shows it hollow. **Recommended: (b)**: one
meaning of "in". Reverse: `_skeletons` reads `tracked` instead of
`present`.

**6. What a one-sided axis (height) learns as.**

| Option | Trade-off |
|---|---|
| (a) `position`, depth 1, on everything (today) | "The hand is the fader" everywhere. Height on `rot.rate.XY` still starts at −66.56×: rotation is not tamed for one axis in six. |
| (b) `push` at the learn depth on everything | One rule for every axis. Height can only add to the base: on a param the preset left near its top, a learn appears to do nothing, and the `hands-*` presets' own idiom (height *is* brightness) stops being what a learn makes. |
| **(c) `push` on a range centred on zero, `position` elsewhere** | Height on brightness, mix or speed is still the fader; height on a rate, an angle or a pan adds from the base. Two sentences instead of one. |

**Recommended: (c).** It reads only the target's declared range.
Reverse: one condition in `learn_source`.

**7. What a learn does to the axis's other rows.** Today a learn moves
the axis (its other `position` rows go) and leaves its hand-written
pushes.

| Option | Trade-off |
|---|---|
| (a) Leave `_place` alone: only `position` rows move | No change to a pinned test. Five axes in six now learn as pushes, so for them "learn it again somewhere else" silently stops moving and starts adding: roll ends up on three params. |
| **(b) The axis's other performer rows go, whatever their op** | "A learned axis drives one param" stays true and matches a knob learn (`Bindings.bind` moves the control). On a factory preset it takes out the preset's own rows on that axis; the status line names them and one ⌘Z brings them back. |
| (c) Only rows of the new row's op go | Today's position learn is unchanged to the letter. Height learned onto brightness and then onto a rate keeps both. |

**Recommended: (b).** It rewrites `test_a_learned_axis_drives_one_param`'s
"its push rows stay". Reverse: one condition and that test.

**8. The default learn depth.**

| Option | Trade-off |
|---|---|
| 0.5 | A full tilt is ±25 % of a throw: speed ×¼…×4, zoom 0.19×…5.3×, yaw ±90°, `rot.rate` ±33×. Lively; close to the complaint. |
| **0.25** | ±12.5 %: speed ×½…×2, zoom 0.43×…2.3×, yaw ±45°, brightness 1.3×…3.1× from 2×, `rot.rate` ±16.6×. The party presets' own turn depth (`preset.TURN`). |
| 0.1 | ±5 %: `rot.rate` ±6.7×, but mix ±0.05 and speed ×0.76…×1.32 read as "the learn did nothing". |

**Recommended: 0.25.** No single depth is gentle on `rot.rate.*` and
audible on everything else, because that range is 133× wide for the
reference's sake; narrowing or tapering it would move the `legacy6`
anchor and is not done. The owner turns the one number down for a rate
session, or the one row on ROUTING. Reverse: two constants.

**9. Where the learn depth lives.** **(a) `hands.learn_depth`**, with
the hands' feel: session, saved by a hands setup, no new group. (b) a
`[hands]` config key: not changeable at the machine without a restart.
(c) a `learn.*` group: a new group and page home for one number.
**Recommended: (a).** Reverse: rename one id.

**10. How the glide writes.**

| Option | Trade-off |
|---|---|
| (a) Every frame through `Param.set_norm` | The one setter a knob uses today. It rounds to the detent, so a slow turn is as stepped as now; only a fast flick is spread out. Does not fix what was seen. |
| **(b) Between detents through `Param.set`, landing with `set_norm`** | Smooth at any speed, and the value rests exactly where today's does. Uses `Param._value_of_norm` from the adapter, as `Router.follow_macros` already does. |
| (c) Rest between detents too (no landing) | Smoothest in principle. Every knob-set value would differ from today's in a saved preset, and rings and pickup compare against other numbers. |

**Recommended: (b).** Reverse to (a): one line.

**11. The glide's shape.** (a) a one-pole follow: familiar, but it never
quite arrives, so the end needs a snap and the time has no plain
meaning (worked: at a 25 ms time constant a slow turn still moves 0.56 %
of the throw in a frame). **(b) a straight line that arrives `desk.slew`
after the last message**: the number means what it says, the end is
exact, and the undo bound is exact (0.33 % a frame on the same turn).
**Recommended: (b).** Reverse: the body of `_glide`.

**12. Smoothing's default.**

| Option | Trade-off |
|---|---|
| **(a) 0: off until the owner turns it up** | Today's desk to the bit; every existing test stands unedited. The complaint stays until someone finds SYSTEM → Knob smoothing (check N7 says to). The show then keeps the number. |
| (b) 80–100 ms out of the box | Fixed without anyone looking. But it rests on the ring re-basing the encoder cleanly while a value is in flight, and hand check 31 (the re-base itself) has not been seen yet; a wrong guess makes every knob feel bad at the party. |

**Recommended: (a)**, and N7 picks the number at the machine. Reverse:
the default of `Bindings.slew`, plus the test fixtures that assume an
immediate write.

**Settled by the orchestrator, 2026-10-04: (b), 80 ms in the running
app.** During a glide the ring carries the knob's own target (fork 14),
the very message today's code sends, so the glide adds no new assumption
about the encoder beyond the one hand check 31 already covers; and a fix
that ships switched off is a new knob where a default would do (roadmap
§1). How it is built so that (a)'s proof survives: a bare `Bindings`
still has `slew = 0.0` (every existing test passes unedited and 0 is
bit-identical to today); `routing.SLEW_DEFAULT_S = 0.08` is what the
**app** sets on its table before the show's session values land
(`app.main`, one line; a show that saved `desk.slew` keeps its number, 0
included), without marking a factory show unsaved at launch. Wherever
this document says "0 by default" or "off by default", read "0 on a bare
table, 80 ms in the app". Check N7 becomes "judge 80 ms; turn it down or
off if a knob feels late". Cost to reverse: one constant.

**13. Where `desk.slew` lives.** **(a) `desk.slew`, with `desk` made a
session group**: named for what it is, beside `desk.shift`; one tuple
edit. (b) in an existing group (`ui.`, `master.`, `output.`): no tuple
edit, a misleading name. (c) `midi.slew` registered by the adapter: the
param would not exist with `[midi] enabled = false`, and a show's saved
value would be reported as an unknown id. **Recommended: (a).** Reverse:
rename one id (a show file's one value is dropped with a note).

**14. The ring during a glide.** (a) the lagging base: literally "the
ring shows the base", and it re-bases the encoder backwards mid-turn.
(b) hold the ring's last value until the glide lands: the ring freezes
under the fingers. **(c) the glide's target**: the same message as
today. **Recommended: (c).** Reverse: one line in `feedback`.

**15. A free global-layer knob (K6–K8) for the learn depth or the
smoothing.**

| Option | Trade-off |
|---|---|
| **(a) Neither** | Both are set once per room or per performer, not ridden. No factory row, no `bindings.json` rewrite. K6–K8 stay the owner's to give away (decision 9: "a first cut"). |
| (b) `hands.learn_depth` on K6 | Beside the other hand feel. A knob for a number that only matters at the next Learn. |
| (c) `desk.slew` on K6 | A knob that sets how knobs feel; hard to judge while turning it. |

**Recommended: (a).** Either can be learned by right-click today, and
adding a factory row later is one `DEFAULT_MAP` line and one
`APC_NEW_ROWS` entry.

**16. `hands.json`'s schema.** (a) leave it `/1` and add the key: no
number to explain, but a file that changed shape under one name. **(b)
`/2`, written on the next save; a `/1` file read as it is and never
rewritten at load; one backup before the first rewrite.** An older build
reading a `/2` file reads its ranges and drops the box on its next save.
**Recommended: (b).** Reverse: one constant.

**17. The two-hand orbit.**

| Option | Trade-off |
|---|---|
| **(a) A preset where each hand owns some camera params** (`hands-orbit`) | Five rows on axes that exist. It is two hands *on* the camera, not the hands turning the scene between them. |
| (b) Nothing | One fewer preset in a list the owner wants shorter. The session's ask goes unanswered. |
| (c) Derived lanes (`hand:both.spread`, `hand:both.turn`) | The steering wheel. Two new axes: DECISIONS, "no gesture vocabularies, no more DOFs". Not built. |

**Recommended: (a)**, last in the queue and droppable. Reverse: delete
one entry and one file.

## 7. As built

Filled as the work packages land.

## 8. Appendix — group N for `11-hand-checks.md`

WP5 pastes this in after group M (its heading at the level of the other
groups'), and adds "then plan 18's group N" to the file's opening
paragraph. The check numbers are placeholders (N1…N9) until the file's
running numbers are known. The text is final except for PR numbers.

### N. Plan 18 — the box, a learn's default, knob smoothing — added 2026-10-04

Run on `finish-line` once plan 18 is merged into it. All of it needs the
camera and the box; N3, N7 and N8 also need the APC40. About 40 minutes.
Whether the rig was calibrated on Oct 3 is not known, so **N1 comes
first** and everything after it assumes its box. Before the first launch:
`cp -R ~/Hyperspace ~/Hyperspace-2026-10-04` if that copy does not exist
yet. The headless tests named are the ones each package adds; run them
first.

**N1. Calibrate, and the box it draws (plan 18 WP1; replaces the pass
text of check 15).**
Headless: `uv run pytest -q tests/test_hands.py::test_the_sweep_sets_the_box_with_its_margin_and_a_symmetric_x tests/test_hands.py::test_an_old_hands_json_reads_as_before_and_is_not_rewritten_at_load tests/test_hands.py::test_the_first_rewrite_of_an_old_file_keeps_a_backup`.
Launch, HANDS page. Before touching anything: if `~/Hyperspace/hands.json`
existed, the page's ranges are the ones it held and the box view shows
**no inner rectangle** (an old file has no box). Open "feel &
calibration", press **calibrate 20 s**, and move both hands through
everything they should reach: side to side, low to high, near to far,
and each tilt end to end. *Pass:* the note reads "calibrated 12 axes ·
box W × H × D mm"; the box view now has an inner rectangle and the
height gauge a bracket; both hands' dots are inside it wherever you
played; `hands.json` holds `"schema": "hyperspace.hands/2"` and a `box`;
if the file existed before, `hands.json.bak-v1` beside it is the old
one. Every axis still reaches both ends of its row. *Fail:* "x open (not
swept)" → sweep wider than 12 cm on that direction and run it again; no
rectangle → `_finish_calibration`'s palm samples (`hands/core.py`); no
`.bak-v1` → `HandsIO.save_ranges`.

**N2. A hand outside the box reads absent, and the edge does not flicker
(plan 18 WP1).**
Headless: `uv run pytest -q tests/test_hands.py::test_a_hand_outside_the_box_reads_absent_everywhere tests/test_hands.py::test_the_boxs_edge_has_hysteresis tests/test_hands.py::test_a_hand_re_entering_the_box_is_caught_not_jumped`.
PRESETS: `hands-play` (R height positions brightness). Right hand in the
box, mid height. Move it slowly out through the right face. *Pass:* a
few centimetres past the rectangle its dot turns hollow, the status
shows `R◌`, its axis rows dim, and brightness is back at its base that
frame. Hold the hand right at the edge and wobble it a centimetre:
brightness does not flicker between the two. Bring it back in: the row
glides onto the hand (the catch), no jump. Repeat upward past the
gauge's bracket and toward yourself past the near face. *Fail:* still
performing far outside → `HandsIO.box` is `None` (N1) or the presence
line in `poll`; flicker at the edge → `BOX_EDGE`; a jump on re-entry →
`hands.catch` is 0, or the lane read `NaN` during the catch
(`Follower.live`).

**N3. A hand on the desk does not perform (plan 18 WP1).**
With `hands-play` still loaded and the APC40 where it will stand for the
show, reach for it and turn a knob with the right hand, the left hand
out of the way. *Pass:* brightness moves only by the knob; the right
hand's dot is hollow (or gone) the whole time. If the dot is filled
while your hand is on the desk, the desk stands inside the swept box:
move it, or run N1 again keeping the sweep clear of it. With ghost hands
on (HANDS page), a hand leaving the box fades out at the frame's edge
and the frame shows the whole box. *Fail:* the ghost still drawn outside
→ `HandsIO._skeletons`; the frame not matching the box → `ghost.box_of`.
Last: press **reset ranges**. *Pass:* the rectangle and the bracket go,
"box open", and a hand is present wherever the tracker sees it, as
before this plan. Then run N1 again to put the box back.

**N4. A tilt learned onto rotation and speed is gentle (plan 18 WP3).**
Headless: `uv run pytest -q tests/test_learn.py::test_a_centred_axis_learns_as_a_push_about_the_base_at_the_learn_depth tests/test_hands.py::test_learn_passes_the_axiss_centredness_and_the_sessions_depth`.
PRESETS: `hands-play` (it has no band rows on the rotation rates). VIEW
page: right-click Speed → Learn hand ▸ right (plan 17's menu), and roll
the right hand. Speed is already performed by L height, so the prompt
asks: **Replace**. *Pass:* the ROUTING row reads "R roll pushes +0.25";
with the hand level the speed is the preset's; a full roll either way
takes it to about half and about double, not to stop and flat out. Now
the same onto a rotation rate (VIEW page, "rotation", the XY rate) with
the right hand's yaw: level leaves the plane turning as the preset set
it; a small turn nudges it. If rotation is still more than you want, lower
**Learn depth** under "feel & calibration" (0.10 is ±6.7× on a rate) and
learn the right hand's pitch onto another rate (XZ): that row carries
the new number and the two earlier rows kept their 0.25 (learning the
same axis onto the same param again changes only its gate). *Fail:* "positions" on a tilt → `HandsIO._learn` is not
passing `centred` (`hands/core.py`) or `learn_source`'s table; the
param jumps when the hand enters → the row has a `rest` of its own.

**N5. Height is still the fader where that makes sense (plan 18 WP3).**
Headless: `uv run pytest -q tests/test_learn.py::test_a_one_sided_axis_on_a_one_sided_param_is_still_the_fader tests/test_learn.py::test_a_one_sided_axis_on_a_zero_centred_range_pushes_up_from_the_base tests/test_learn.py::test_a_discrete_target_keeps_the_position_row`.
Still on `hands-play`. Learn the left hand's **height** onto a fader
nothing performs yet (Pattern mix, say). *Pass:* "L height positions":
low is none, high is full, the hand is the fader as before. Learn the
left hand's height onto a rotation rate nothing performs (YZ): "L height
pushes" at the learn depth, and the Pattern mix row is gone (N6); with the hand low the
plane turns as the preset set it, and raising it speeds it up; it never
runs backwards at the bottom. Learn any tilt onto a toggle (Faces):
"positions", and tilting past the middle flips it. Load `hands-play`,
`hands-pinch` and F1–F8 in turn and open ROUTING on each: every factory
row reads as it did before this plan. *Fail:* a factory row changed → a
preset file was regenerated or a load converted rows (neither may
happen).

**N6. A learn moves the axis (plan 18 WP3, fork 7).**
Headless: `uv run pytest -q tests/test_learn.py::test_a_learned_axis_drives_one_param tests/test_learn.py::test_a_learn_is_one_undo_step`.
F1 (TUMBLE): right roll turns the XW plane. Learn right roll onto
Brightness. *Pass:* the learn line says "learned view.bright ← … (into
the preset; moved from rot.phase.XW)", ROUTING no longer has the XW row,
and roll moves brightness only. ⌘Z once: the XW row is back and the
brightness row is gone. Say here whether you would rather a learn
*added* (the old row staying): that is fork 7 (a), one condition in
`Learn._place`.

**N7. Knob smoothing: pick the number (plan 18 WP2).**
Headless: `uv run pytest -q tests/test_midi.py::test_smoothing_is_off_by_default_and_every_write_is_immediate tests/test_midi.py::test_a_smoothed_knob_arrives_in_a_straight_line_and_rests_on_the_detent tests/test_midi.py::test_the_ring_shows_where_the_knob_is_going`.
APC40 in, F3 (FIELD) so a pan or zoom step is easy to see. SYSTEM page:
**Knob smoothing** reads "off". Turn K8 (zoom) slowly: the picture moves
in steps, as it always has. Set Knob smoothing to 100 ms and turn K8
slowly again. *Pass:* the zoom glides; when you stop it settles within
a blink and the ring sits where your fingers left it; a fast spin
neither lags behind noticeably nor overshoots; the ring never crawls
backwards under your fingers and the next turn carries on from it.
Try 50 and 200 ms and leave it where it feels right; that number is
saved with the show. Move a fader (S1) and the crossfader: they glide
too, and a fader that had not been picked up still does nothing until
it reaches its value. Turn the cue knob (shapes) and press a clip
button: unchanged, one step a click. *Fail:* the knob fights you or the
ring runs behind → `MidiIO._ring_norm` / `_rebase` (and check 31 if the
ring misbehaves with smoothing off too); a value that never settles →
`_glide`'s landing; set it back to "off" and the desk is as it was.

**N8. A smoothed knob with everything else (plan 18 WP2).**
Headless: `uv run pytest -q tests/test_desk.py::test_a_layer_switch_leaves_a_glide_to_finish tests/test_desk.py::test_a_preset_load_stops_a_glide_on_a_performance_param_and_not_on_the_dim tests/test_undo.py::test_a_smoothed_knob_turn_is_one_step tests/test_undo.py::test_undo_during_a_glide_holds`.
Knob smoothing at 250 ms (the maximum, to see it). Spin K1 (brightness)
and press F5 at once. *Pass:* the look is TRIP's, with TRIP's
brightness, not the knob's. Spin K1 and latch SHIFT at once: brightness
still arrives; K1's ring now shows the global layer's value. Sweep K1
once, wait a second, ⌘Z: brightness is back where it was before the
sweep in **one** press, and the footer names the value the sweep landed
on. Sweep K1 and press ⌘Z while it is still moving: it goes back and
stays back. With a hand owning brightness (`hands-play`, hand in the
box), turn K1: the picture does not move; take the hand out and
brightness is where the knob put it. Slide the crossfader to dim and
press F2 mid-slide: the dim finishes arriving. *Fail:* the knob's value
winning over a load → `redraw(load=True)`'s rule; two presses to undo
one sweep → `SLEW_MAX_S` against `undo.SETTLE_S`.

**N9. Two hands on the camera (plan 18 WP4).**
Headless: `uv run pytest -q tests/test_presets.py::test_hands_orbit_is_five_pushes_onto_the_camera`.
PRESETS: `hands-orbit`. Right hand in, level, mid box: nothing moves.
Slide it left and right: the camera orbits, about a quarter turn each
way. Tip the fingers up: it looks down onto the shape. Left hand: side
to side and reaching in pan; raising it zooms in. Take both hands out:
the camera is back where the mouse left it. *Pass:* each move does the
one thing, a still hand is calm, and it can be taught in a sentence.
Note any depth that wants changing (the five numbers in
`preset.hands_orbit_routes`), and whether this is the "orbit" you meant:
the version where the two hands turn the scene between them needs a new
axis and was not built (fork 17). If it is not wanted, hide it (plan
19).
