# Decision register — the open decisions

Rows 34–88 were each decided during an unattended build on 2026-10-04:
the build took its own recommendation and built it. Every one is in the
app now and waits for the owner to say **keep** or **overturn**. Each row
says what was built (what you will see or feel), the other option(s), what
it costs to reverse, the known rough edge, and the hand check that lets you
judge it. The checks are numbered in
[`plans/11-hand-checks.md`](plans/11-hand-checks.md); the same checks in
plain words, by hardware, are in [`TESTING-GUIDE.md`](TESTING-GUIDE.md)
(each entry ends with its check numbers). None has been run by a person.

Decisions already settled, and these rows once kept, are in
[`DECISIONS.md`](DECISIONS.md); a row there marked "row N" points here.
When you answer a row: keep → mark it "owner" in DECISIONS and delete it
here; overturn → the change, then the same.

## Answer sheet

| # | Decision | Check | Keep / overturn |
|---|---|---|---|
| 34 | Undo on ⌘Z and Ctrl+Z; exact chords | 48 | |
| 35 | Band add / remove / move not undoable | — | |
| 36 | Taps and BPM are not undo steps | — | |
| 37 | Trash only when the file changes | 53, 88 | |
| 38 | Home is the Home key only | 54 | |
| 39 | Camera moves are undo steps | — | |
| 40 | Home may be fired by a performer; dim may not | 54, 55 | |
| 41 | The dim in overlay fades alpha too | — | |
| 42 | Save-as hold: how it fires and lights | 56 | |
| 43 | A paused drag is two undo steps | 48 | |
| 44 | A load releases only faders it moved | 55 | |
| 45 | FX chip: dot switches, name opens; three a row | 59 | |
| 46 | An idle effect's faders dimmed but live | 60 | |
| 47 | Instances reach zero from slider and K3 | 62 | |
| 48 | Where the windows open | 61 | |
| 49 | The dream's layer cannot be performed | 63 | |
| 50 | The interaction box: set by the sweep | 72–74 | |
| 51 | A hand outside the box is absent everywhere | 73, 74 | |
| 52 | A hand Learn lands as a gentle push | 75, 76 | |
| 53 | A hand Learn moves the axis's other rows | 77 | |
| 54 | Knob smoothing on at 80 ms | 78, 79 | |
| 55 | Where knob smoothing and Learn depth live | 75, 78 | |
| 56 | `hands-orbit`: two hands on the camera | 80 | |
| 57 | The big on-screen desk and its names | 69 | |
| 58 | Click a desk control, then a param | 70 | |
| 59 | One Unbind removes desk rows and routes | 64 | |
| 60 | "Learn desk" and "Learn hand ▸ left / right" | 66–68 | |
| 61 | Session controls work through a desk learn | 65 | |
| 62 | One road onto the desk, no APC40 needed | 70 | |
| 63 | The ROUTING filter: only you clear it | 71 | |
| 64 | Two hand-Learn details left alone | 66 | |
| 65 | The faces' effect picture: what, size, fit | 91–93, 98 | |
| 66 | Performers on effect target and face mapping | 91 | |
| 67 | The chip grid is the chain; drag to reorder | 94 | |
| 68 | Re-aim an effect by the strip's combo | 91, 94 | |
| 69 | LOOKBACK as ECHOES / DREAM / BOTH; every layer in one menu | 95 | |
| 70 | Dream "speed" is `dream.k`, in frames | 96 | |
| 71 | Instance layouts: grid, honeycomb, ring | 97 | |
| 72 | The bank of twenty-four | 81, 83 | |
| 73 | Clip rows 4–5 are the bank; their lights | 82–84 | |
| 74 | No backup, no rewrite of `bindings.json` | 84, 57 | |
| 75 | Device knobs only where they do something | 85 | |
| 76 | Hide, rename and the trash | 86–88 | |
| 77 | The red dot and "save copy" | 89 | |
| 78 | The home in git | 90 | |
| 79 | Where "hands through effects" puts the hands | 102, 103 | |
| 80 | The guide and labels are never bent | 103 | |
| 81 | Output switches are rig settings | 101, 104 | |
| 82 | Another shape is letterboxed | 106 | |
| 83 | One window renders, others copy | 107 | |
| 84 | Ghost hands and each output's hands tick | 102, 105 | |
| 85 | The OUTPUT page says it in words | 102, 105 | |
| 86 | A screen not connected at launch | 101, 111, 112 | |
| 87 | `ghost.style`: five drawn objects | 109 | |
| 88 | Ghost mirror / guide / tethers not performable | 110 | |

"—": no hand check shows it; tests only.

---

## Undo, home, the dim, save-as

### 34. Undo on ⌘Z and Ctrl+Z; a key fires only its exact chord

- **Built.** ⌘Z and Ctrl+Z undo; adding ⇧ redoes. A key press fires only
  the row whose modifiers are exactly the ones held, so ⌘⇧Z redoes and
  does not also undo.
- **Other options.** ⌘Z only (Ctrl+Z does nothing); Ctrl+Z only (wrong for
  Mac hands).
- **To reverse.** Delete two rows in `routing.LOOP_KEY_ROWS`: minutes. The
  exact-chord rule is needed by redo under any option.
- **Rough edge.** A row you made by hand on a bare key (`key:Z`) no longer
  fires while ⇧, ⌘ or Ctrl is held. No factory row is affected.
- **Judge it.** Check 48.

### 35. Adding, removing or moving a band is not an undo step

- **Built.** ⌘Z after adding a band does not remove it. Each undo step
  remembers the band layout it was made on; strip values go back only onto
  that same layout. When a step's strip values are skipped, the footer
  says "the bands have changed: their strips were left". A band preset
  load, a show load and a scene pick undo whole. The 8-second "Reset all"
  undo is unchanged.
- **Other options.** Make add / remove / move undo steps (about a day,
  builds on this); clear the whole history on a layout change.
- **To reverse.** About a day for full undo of layout changes.
- **Judge it.** No check; tests only.

### 36. A tap, a nudge or a typed BPM is not an undo step

- **Built.** The tempo group is not watched by undo, so tapping never fills
  the history, and undoing a show load leaves the tempo where it is.
- **Other option.** Watch the BPM: each tap of a burst becomes a step.
- **To reverse.** One line (`undo.EXCLUDED_GROUPS`).
- **Judge it.** No check; tests only.

### 37. A preset goes to the trash only when the file would change

- **Built.** Saving or deleting a preset first copies the old file to
  `~/Hyperspace/trash/presets/<name>.<date>-<time>.json` (a module preset
  to its own folder there), but only when the text would actually change.
  If the copy fails (a full disk), a save warns and goes on; a delete is
  refused.
- **Other options.** Trash on every save (identical copies pile up); a
  failed copy also refuses the save.
- **To reverse.** One condition in `library.to_trash`'s callers.
- **Judge it.** Checks 53 and 88.

### 38. Home is the Home key only (fn ← on a MacBook)

- **Built.** `key:HOME` fires home; the desk's OVERDUB is the other road.
  The row is in `bindings.json` and can be moved to another key there.
- **Other option.** A second key as well (say ⇧H).
- **To reverse.** One row.
- **Rough edge.** Whether fn+← reaches the app as Home has not been tried.
- **Judge it.** Check 54.

### 39. Camera moves are undo steps

- **Built.** R (reset view), a mouse orbit, the sticks, the wheel and ↑ / ↓
  each undo like any setting; one continuous orbit is one step. The
  history holds 100 steps.
- **Other option.** Leave the camera out, so ⌘Z always reaches a "real"
  edit.
- **To reverse.** Add `"camera"` to `undo.EXCLUDED_GROUPS`.
- **Judge it.** No check of its own; any undo check after an orbit.

### 40. A performer may fire home; nothing may drive the master dim

- **Built.** A pinch, band or LFO routed onto `preset.home` fires it, like
  "next preset". The master dim (`output.dim`) cannot be a route's target,
  is never saved and is never moved by a preset or a show. No factory
  preset routes onto home.
- **Other options.** Home not performable; the dim performable (a band
  could strobe the room, a hand leaving the box could black it out).
- **To reverse.** One flag each.
- **Judge it.** Checks 54 and 55.

### 41. In overlay mode the dim fades colour and transparency together

- **Built.** On the normal opaque window the dim scales the colour toward
  black. In overlay mode (only when `config.toml` sets `[output] overlay =
  true`) it also fades the alpha, so the render fades away over the
  desktop.
- **Other option.** Colour only: a dark veil stays over the desktop.
- **To reverse.** One line in `Renderer.dim_pass`.
- **Judge it.** No check: the rig runs with overlay off.

### 42. The save-as hold on the clip-stop row

- **Built.** Holding any of the eight clip-stop buttons for 0.6 s saves the
  live look as a new preset ("TRIP" → "TRIP 2") into the next empty bank
  slot, while you are still holding. The eight act as one bar: two fingers
  save once. The bar is dark at rest, lit while held, and blinks for
  1.5 s with the new slot's pad when it saves. A new name never matches a
  file, a listed name or a bank entry. The new preset becomes the loaded
  one, so panel Save then writes it. With the bank full the preset still
  saves, to the list, and the footer says so. A save that fails blinks
  nothing.
- **Other options.** Fire on release; the bar lit at rest; stay on the old
  preset after saving; a per-row hold time.
- **To reverse.** Each is a line or a constant (`midi.HOLD_S`, the rows'
  "off" velocity).
- **Rough edge.** The on-screen desk lights the bar while held but does not
  blink. The hold, lights and blink have never been on the APC40.
- **Judge it.** Check 56.

```
 clip row 1     [ 1 ][ 2 ][ 3 ][ 4 ][ 5 ][ 6 ][ 7 ][ 8 ]   bank slots 1–8
 clip rows 4–5  slots 9–16 and 17–24 (row 73)
 clip stop      [========== SAVE AS: hold 0.6 s ==========]  [STOP ALL: reset all]
                a NEW preset → the next empty slot, whose pad blinks; a tap: nothing
```

### 43. A slider drag that pauses is two undo steps

- **Built.** An undo step ends after 0.4 s in which nothing you set has
  changed. A drag held still longer than that, then moved again, is two
  steps. One rule for the panel, the desk, keys and typed values.
- **Other option.** Hold the step open while a panel widget is dragged
  (the desk's knobs gain nothing).
- **To reverse.** One flag the panel sets; the quiet time is one constant
  (`undo.SETTLE_S`; knob smoothing must stay under it).
- **Judge it.** Check 48 (does 0.4 s feel right).

### 44. A preset load releases only the faders whose parameter it moved

- **Built.** A fader "has" its parameter once moved onto its value (soft
  pickup). A preset load makes a fader let go only if the load moved its
  parameter, the parameter is gone, the fader has never been moved, or
  another control moved the parameter since. So the crossfader's dim, the
  band faders and the master fader carry straight on through a load. A
  fader moved while its row is switched off, or while a Learn took its
  message, picks up again from where it is.
- **Other options.** Every fader lets go on every load (the crossfader
  sometimes dead after a load); the crossfader with no pickup (one parked
  at the left blacks the rig out).
- **To reverse.** One condition in `MidiIO.redraw`.
- **Judge it.** Check 55 (e).

## Effects, windows, instances

### 45. An effect chip: the dot switches, the name opens; three chips a row

- **Built.** On the FX page each chip has a dot at its left end that
  switches the effect on or off (● on, ○ off; a diamond when the effect is
  aimed at the faces), and a name that opens its faders without switching
  it. The open chip has a white outline. Chips sit three to a row so every
  name fits. The open effect is remembered by name, so a reorder or a load
  never opens a different one.
- **Other options.** No switch on the chip, only the strip's "on" box;
  click opens and ⇧click switches.
- **To reverse.** Remove the dot (about a dozen lines in `ui_fx._chip`);
  four a row is one constant (`ui_fx.CHIPS_PER_ROW`).
- **Rough edge.** The dot is small; nobody has tried it with a trackpad.
- **Judge it.** Check 59.

### 46. An effect that is not running: its faders dimmed but live

- **Built.** The open effect says why it is idle ("off" with a **turn on**
  button, the stack bypassed with **effects on**, FX mix at 0, its own mix
  at 0). Its faders sit under a veil but still move and still offer
  right-click → Learn. The "on" box, and the mix fader when the mix is the
  reason, are not dimmed.
- **Other option.** Disabled: greyed and dead, no Learn on an off effect.
- **To reverse.** A few lines in `ui_fx.page`; the strength is
  `ui_fx.IDLE_ALPHA`.
- **Judge it.** Check 60.

### 47. The instance count reaches zero from the slider and K3

- **Built.** `view.instances` runs 0–100. At 0 the readout says "0 ·
  nothing drawn"; the ground, the echoes, the effects, the ghost hands and
  the dim carry on. The slider's left end and the bottom of track knob K3
  are zero. ⌘Z brings the count back. No factory preset, desk value or
  hand route lands on zero.
- **Other options.** Stop the slider and knob at 1 (zero only by preset or
  typing); a separate "blank" switch.
- **To reverse.** Two lines (the range's floor and the renderer's clamp);
  a preset saved at 0 would then load as 1.
- **Rough edge.** A route of yours that pushes both ways on the count (an
  LFO) can now blank the scene for half its cycle.
- **Judge it.** Check 62.

### 48. Where the windows open

- **Built.** The app remembers both windows' places in
  `~/Hyperspace/windows.json`, written on quit and on ⌘R only. A screen
  number in `config.toml` (`[output] monitor`, `control_monitor`) wins over
  the file. Fullscreen is never remembered (`[output] fullscreen` says).
  A first launch opens at full size: render top-left, controls flush
  right. A remembered spot that is not on a connected screen falls back to
  the default spot with a note. Delete `windows.json` to forget.
- **Other options.** The file beats the config; write the file while
  running (survives a crash); remember fullscreen; fit a first launch to a
  small screen.
- **To reverse.** Each is a branch or a line in `placement.place`,
  `placement.default_rect` or the frame loop.
- **Rough edge.** A configured screen number with no screen at launch is
  ignored for the whole run (audit P6). Never run with a second screen.
- **Judge it.** Check 61.

### 49. The dream's layer cannot be performed

- **Built.** `dream.layer` (which net layer the dream works on) is not a
  route target, like "Echo time apart" and "Look-back detail": changing it
  reloads part of the net. A preset, a key, the page's menu and a learned
  knob or button still set it. A saved preset's route onto it is dropped
  at load with a note.
- **Other option.** Leave it performable: a band on it reloads the net on
  every swing.
- **To reverse.** One flag in `params.py`.
- **Judge it.** Check 63.

## The hands and the knobs

### 50. The interaction box, set by the calibration sweep

- **Built.** A hand counts only while its palm is inside one box, the same
  for both hands, symmetric left and right of the camera. The 20-second
  calibration sweep on the HANDS page sets it: where the palms went plus
  40 mm all round (`BOX_MARGIN`). A direction gets a bound only if one hand
  travelled over 12 cm along it. At the edge a hand that is in stays in
  until it is 15 mm past a face (`BOX_EDGE`). There is no on/off switch:
  "reset ranges" opens the box (and resets the ranges). The box is saved in
  `hands.json` (format 2); an older file is read unchanged and backed up
  as `hands.json.bak-v1` the first time it is rewritten.
- **Other options.** Drag the box on the drawing, or six sliders; a box
  per hand; a "use box" checkbox.
- **To reverse.** Widgets over the same ranges (`HandsIO.box`); the three
  sizes are constants in `hands/core.py`.
- **Rough edge.** The box is off during the sweep, so anyone the camera
  sees is counted into it: calibrate with nobody else in view. No camera
  has seen any of this.
- **Judge it.** Checks 72–74 (72 first).

### 51. A hand outside the box is absent everywhere, its ghost included

- **Built.** Outside the box a hand's rows let go and their params return
  to their base that frame, its pinches drop, its "present" light goes
  off, and its ghost fades out. The ghost hands' frame is the box. Only
  the HANDS page still shows it, hollow and as `◌`. A hand coming back is
  caught and glided onto, no jump.
- **Other options.** Still draw it as a dimmed ghost; frame the ghost by
  the axis ranges.
- **To reverse.** One line in `HandsIO._skeletons`; one branch in
  `ghost.box_of`.
- **Judge it.** Checks 73 and 74.

### 52. A hand Learn lands as a gentle push

- **Built.** A new hand Learn now adds to where you set the control,
  instead of the hand becoming the fader:

  | Learned onto | A tilt, sideways or reach (rests in the middle) | Height (rests at the bottom) |
  |---|---|---|
  | a range centred on zero (a rotation rate, an angle, a pan, the hue) | push at the Learn depth | push at the Learn depth |
  | any other fader (speed, brightness, a mix) | push at the Learn depth | the fader, as before |
  | a switch, a list, a button or a whole-number count | the fader | the fader |

  The Learn depth is 0.25 (a quarter of the travel over the hand's whole
  range), on the HANDS page as "Learn depth". A level or low hand leaves
  the preset's value showing. Existing rows and factory presets are not
  changed.
- **Other options.** Height a push everywhere, or the fader everywhere;
  depth 0.5 or 0.1; the depth in `config.toml`.
- **To reverse.** One condition each in `Learn._row`; the depth is
  `learn.PUSH_DEPTH` and `HandSettings.learn_depth`.
- **Rough edge.** Learning the same axis onto the same control again does
  not tame an old row: it only refreshes the pinch gate. No real hand has
  felt 0.25.
- **Judge it.** Checks 75 and 76.

### 53. A hand Learn takes the axis's other rows with it

- **Built.** Learning a hand axis onto a control removes that axis's other
  push and position rows in the loaded preset, switched off or on: a
  learned axis drives one control. The footer names what moved
  ("…; moved from rot.phase.XW"); one ⌘Z brings it back. The file is not
  touched until you save.
- **Other options.** Only position rows move (an axis can end up on three
  controls); only rows of the new row's kind move.
- **To reverse.** One condition in `Learn._place`.
- **Rough edge.** On a factory preset this removes the preset's own row on
  that axis.
- **Judge it.** Check 77 (would you rather a Learn added?).

### 54. Knob smoothing, on at 80 ms

- **Built — against the plan's recommendation.** A value from a desk knob
  or fader now arrives in a straight line over 80 ms and rests exactly on
  the step it always did; the ring shows where the knob is sending it.
  "Knob smoothing" on the SYSTEM page sets it, off to 250 ms; it is saved
  with the show, and a show that saved a number (off included) keeps it.
  Not smoothed: buttons, the cue knob, and a knob on a list, switch or
  whole-number count. One knob turn is still one undo step.
- **Other option.** The plan's recommendation: off until you turn it up.
  Its worry: smoothing leans on the APC40 accepting a ring message
  mid-turn (check 31, never seen on the device).
- **To reverse.** One constant (`routing.SLEW_DEFAULT_S` to 0).
- **Rough edge.** Never on an APC40. If knobs feel late or fight you, turn
  it off on SYSTEM.
- **Judge it.** Checks 78 and 79.

### 55. Where knob smoothing and Learn depth live

- **Built.** Knob smoothing (`desk.slew`) is on SYSTEM; Learn depth
  (`hands.learn_depth`) is on HANDS with the hand feel. Both are saved with
  the show, never by a preset. Neither is on a global-layer knob (K6–K8
  stay free); either can be put on a control by Learn.
- **Other options.** Learn depth or smoothing on K6.
- **To reverse.** One factory row each (and a `bindings.json` rewrite,
  with its backup).
- **Rough edge.** "Knob smoothing" also shows in the ROUTING page's list
  of things a route's depth can be scaled by; scaling by it is not useful.
- **Judge it.** Checks 75 and 78.

### 56. Two hands on the camera: the `hands-orbit` preset

- **Built.** A factory preset in the list, on no F-key. Right hand:
  sideways orbits up to a quarter turn each way; fingers up tip the camera
  to look down (±44°). Left hand: sideways and reaching in pan; raising it
  zooms in, to 2.2× at the top (depth 0.12). A level, low or absent hand
  adds nothing. The two-hand "steering wheel" (the hands measured against
  each other) is not built.
- **Other options.** No preset; the steering wheel (two new axes, against
  the rule of twelve).
- **To reverse.** Hide it from the list, or delete its entry; the depths
  are the five numbers in `preset.hands_orbit_routes`.
- **Rough edge.** Nobody has played it; directions and depths are a first
  cut.
- **Judge it.** Check 80.

## Learn, Unbind and the on-screen desk

### 57. The big on-screen desk, and what a control says

- **Built.** The APC40 drawing takes the room it has. With the panel hidden
  (H, DEVICE ON/OFF, or the desk's `big` chip) it fills the control window
  and every lit control carries a name once a layout unit is at least
  44 × 32 px. A control says the panel's name for what it does (a bank pad
  its preset's name, ▲ "Brightness +3"). White names are the loaded
  preset's (or the global layer's under SHIFT); grey names are the
  session's. A dark control shows only its glyph. There is no DESK page.
- **Other options.** A DESK page (no room for names); a page that widens
  the panel; a separate "big desk" switch.
- **To reverse.** A page is one function calling `ui_desk._body`; ids
  instead of names is `ui_desk.text`; the sizes are `ui_desk.LABEL_UNIT`,
  `LABEL_UNIT_H`, `LABEL_PX`.
- **Rough edge.** Names that do not fit drop to 11 px on two lines, and a
  few are still cut with "…". Nobody has looked at it on the control
  window.
- **Judge it.** Check 69 (readable from two paces?).

### 58. Click a desk control, then click the param it should drive

- **Built.** A click on the on-screen desk picks a control (framed red;
  ROUTING scrolls to its line). The next click on a param's control maps
  it. While a control is picked every page but ROUTING is dimmed and takes
  no other input. A pick lets go after 20 s with no click, when its footer
  line is clicked, or when the control is clicked again. No click maps
  until the mouse has moved 12 px from the picking click. If the param
  already had a knob, that knob lets go; one ⌘Z undoes both. The session's
  controls cannot be picked to map.
- **Other options.** A click opens ROUTING at the control's line; map via
  a "put D3 here" menu item instead of the dimmed page.
- **To reverse.** One line in `ui_desk.click`; the 20 s and 12 px are
  `ui_desk.PICK_S`, `PICK_MOVE`.
- **Rough edge.** A stray click on the dimmed page maps (one ⌘Z). No real
  mouse has clicked any of it.
- **Judge it.** Check 70.

### 59. One Unbind removes the preset's desk rows and every route

- **Built.** The param's menu lists everything bound to it (a knob, a hand,
  an LFO, a band). **Unbind** removes the loaded preset's desk rows on the
  param and every route on it, whatever drives it; with both kinds bound
  it becomes **Unbind ▸ desk / route / both**. It is offered only when it
  would remove something, never touches a session control, works with no
  APC40 or MIDI off, and is one ⌘Z.
- **Other option.** Desk rows and hand rows only (an LFO or band route
  could not be unbound from its control).
- **To reverse.** A filter on the source's kind in `Learn.unbind`.
- **Judge it.** Check 64.

### 60. "Learn desk" and "Learn hand ▸ left / right"

- **Built.** A Learn says what it waits for. **Learn desk** completes only
  from a knob, button or a click on the on-screen desk; **Learn hand ▸
  left** only from the left hand. Anything else does its own job meanwhile.
  The footer shows what is armed on every page; click it to cancel. An
  armed learn never times out. The menu also opens from a row's label and
  from every meter.
- **Other options.** Three flat items (desk, left hand, right hand); one
  `Learn ▸` submenu.
- **To reverse.** The item list in `Panel._ctx_learn`.
- **Rough edge.** Within the chosen hand the axis that travelled furthest
  still wins (row 64). No real hand has completed one.
- **Judge it.** Checks 66–68.

### 61. The session's controls work through an armed desk learn

- **Built.** With "Learn desk" armed, a session control (below) is not a
  candidate: it does its own job and the learn stays armed. A refusal
  also leaves the learn armed.
- **Other options.** As before (the first touch of anything ends the
  learn); refuse and swallow the touch but stay armed.
- **To reverse.** One branch in `MidiIO._handle`, one line in
  `Learn.learn_control`.
- **Rough edge.** A bank pad pressed mid-learn loads its preset, and the
  learn then lands in that preset. With SHIFT latched every non-session
  control is refused until SHIFT is off. Never on an APC40.
- **Judge it.** Check 65.

```
 the session's controls: the same on both layers; never learned, mapped by a click, or unbound

   S1–S8, SM     the faders                    G1·1–G1·8      bank slots 1–8 (clip row 1)
   X             the crossfader (master dim)   G4·1–G5·8      bank slots 9–24 (clip rows 4–5)
   ⇧             SHIFT                         G6·1–G6·8      the clip-stop row (hold: save as)
   B20           TAP TEMPO                     G6·9           STOP ALL CLIPS (reset all)
   B21, B22      NUDGE − / +                   G7·1–G7·6      track select (pick a band)
   B19, B18      ◀ ▶ (band −1 / +1)            G7·9           MASTER select (overlay)
   B10           QUANT (next preset)           G9·1–G9·6      the solo row (a band's transfer)
   B11           OVERDUB (home)                G10·1–G10·6    the rec-arm row (a band's reset)
   B12           METRONOME (LFO trigger)       B13–B15        PLAY, STOP, REC (the mic)
   B5, B6, B9    CLIP/TRACK, DEVICE ON/OFF,    B1             PAN (click-through)
                 DETAIL (cheat sheet)

 the preset's to map: the 16 knobs, the cue knob, clip rows 2–3, the scene-launch
 column, the activator row (G8), ▲ ▼, and the dark buttons
```

### 62. One road onto the desk, with or without the APC40

- **Built.** Putting a param on a desk control lives in the Learn object,
  not the MIDI adapter. A knob bump, a click on the on-screen desk with
  Learn desk armed, and pick-then-click all make the same row, refuse in
  the same words and cost one ⌘Z. With no APC40 plugged in you can still
  lay out a preset's desk by clicking.
- **Other option.** Keep it in the MIDI adapter (no adapter, no mapping).
- **To reverse.** Move the body back.
- **Rough edge.** The device's ring lighting for a row made by a click is
  unseen.
- **Judge it.** Check 70.

### 63. The ROUTING filter: only you clear it

- **Built.** One text field on ROUTING keeps only the lines that contain
  every word typed (a glyph `d3`, a param, a source `r roll`). Only you
  clear it (empty it or its ×), or a click on a desk control; it holds
  across preset loads. The count turns red ("4 of 176 rows") while
  something is hidden. It is never saved and is empty at every launch.
- **Other option.** Also clear it on a preset load.
- **To reverse.** One line where a load is called.
- **Rough edge.** A route, Learn or undo added while it is set can be
  hidden by it (the red count is the only sign). "lfo 1" also matches
  LFO 2, whose address is `lfo:1`. Nobody has typed in it.
- **Judge it.** Check 71.

### 64. Two hand-Learn details left as they were

- **Built (nothing changed).** If a finger is pinched when a hand learn
  lands, that pinch becomes the row's gate: the learning hand's thumb
  first, then the other hand's. Within the wanted hand, the axis that
  travelled furthest wins; there is no "click an axis, then a param".
- **Other options.** Only the learning hand's pinch may gate; build the
  axis-first learn (about twenty lines on the desk pick).
- **To reverse.** One line in `HandsIO.held_gate`; a click handler on the
  HANDS page's axis rows.
- **Judge it.** Check 66: if the wrong axis keeps winning, the axis-first
  learn is the fix.

## Effects on the faces, the look-back, layouts

### 65. The faces' effect picture: what it holds, its size, its fit

- **Built.** An effect aimed at the faces runs over one square picture of
  the whole face as face 0 shows it (the pattern with the bitmap over it),
  1024 × 1024 (`render.FACE_PIC`, not a setting). The faces show it per
  face or in screen space; in screen space it is cover-fit (scaled to the
  longer side, about a fifth cropped top and bottom at 16:9). It is made
  before the scene pass, so the echoes and the dream carry it. With
  nothing aimed at the faces nothing runs and the frame is unchanged.
- **Other options.** The bitmap only (keeps the per-face pattern phase);
  one picture per face; 512 or 2048; stretch or contain.
- **To reverse.** About thirty lines (bitmap only); one number (size); one
  line of GLSL (fit).
- **Rough edge.** While any effect is on the faces, every face shows face
  0's pattern phase. Per face, a subtle effect can read faint. Never seen
  on a projector or the glass.
- **Judge it.** Checks 91–93 and 98.

### 66. Performers on an effect's target and on the face mapping

- **Built.** An effect's target (`fx.<name>.target`, frame or faces)
  cannot be driven by a hand, band or LFO, like its order; a knob, key,
  the page or a preset sets it. The face mapping (`fx.face_map`, per face
  or screen) can be driven by any performer.
- **Other options.** The target performable (an effect flickering between
  chains); the mapping not performable.
- **To reverse.** One flag each (`fx.declare`).
- **Judge it.** Check 91.

### 67. The chip grid is the chain view; drag a chip to reorder

- **Built.** The FX page's chips are in stack order. Dragging a chip by
  its name onto another puts it before that one (the right half of the
  last chip's name is "to the end"). A drop opens the dragged effect and
  is one undo step. Two status lines read what runs on the frame and on
  the faces, in order. The order slider stays.
- **Other options.** Two lists of rows, one per target (the chip grid
  would have to go); the grid split into frame and faces groups.
- **To reverse.** The grouping is one loop in `ui_fx.page`; the drag is
  two blocks in `ui_fx._chip`.
- **Rough edge.** No real mouse or trackpad has dragged a chip.
- **Judge it.** Check 94.

### 68. An effect is re-aimed by the open strip's ONTO chips

- **Built.** The open strip's title line ends in **ONTO** and two chips,
  frame and faces, the lit one where it runs. A drag only reorders; it
  never changes a target or a switch. A target change is one undo step.
- **Other option.** Drop a chip on a status line to re-aim it.
- **To reverse.** A dozen lines in `ui_fx._faces_row` and the frame line.
- **Judge it.** Checks 91 and 94.

### 69. The LOOKBACK page as ECHOES, DREAM and BOTH, and every dream layer in one menu

- **Built.** The page has three sections named for what a knob acts on.
  The dream's layer is one menu offering every layer of both nets — the
  13 conv layers of VGG16 and GoogLeNet's conv1–conv3 and nine inception
  blocks, 25 in all — under a heading per net, shallow to deep, each
  with its own name and a few words on what it draws; a hover says more.
  The deepest six say "slower" (over 25 ms a frame at 256 px). The new
  labels are used everywhere: ROUTING, a Learn's line and the desk say
  "Echo time apart" (was Spacing), "Shape hides wake" (was Occlude),
  "Look-back detail" (was Resolution), "Dream speed", and so on. A saved
  look keeps its layer: the stored index of the six older layers is
  unchanged.
- **Other option.** Offer only a few hand-picked layers, under nicknames.
- **To reverse.** The words are one table, `lookback.LAYER_INFO`; a layer
  left out is a line there and in `dream.TRUNKS` (append-only `LAYERS`
  keeps saved indices).
- **Rough edge.** The descriptions come from one to two seconds of
  dreaming a still 24-cell and a colour field at the defaults
  (`assets/20-fx-dream-looks/dream-layers*.jpg`), and from depth; nobody
  has watched the new layers on the rig. A key or desk row that *steps*
  the layer walks the stored order (the six older layers first), not the
  menu's.
- **Judge it.** Check 95: are the words right, and are 25 too many?

### 70. The dream's "speed" is `dream.k`, read in frames

- **Built.** `dream.k` (the share of each frame blended into the dream) is
  labelled "speed" and reads as the dream frames it takes a frame's share
  to halve: "≈23 frames" slow, "≈14 frames" at the default, one decimal
  under ten ("1.9 frames" fastest).
- **Other options.** A new `dream.speed` that also scales the strength;
  make `k` per second (a migration).
- **To reverse.** Three strings and `params.dream_speed_text`.
- **Rough edge.** Faster is also shallower. It counts the worker's frames,
  so a slower worker is a slower dream. Nobody has judged the dream at any
  speed.
- **Judge it.** Check 96.

### 71. Instance layouts: grid, honeycomb, ring

- **Built.** `view.inst_layout` (VIEW page, under the count) is GRID (the
  old layout, bit for bit), HEX (a honeycomb spiral from the centre, whole
  hexagons at 7, 19, 37, 61, 91; a copy never moves as the count grows) or
  RING (one circle, copy 0 at the top). The three motions are unchanged.
- **Other options.** HEX as offset rows; RING as concentric rings.
- **To reverse.** One branch of `render.inst_positions`.
- **Rough edge.** HEX with ORBIT at amp 0.35 overlaps neighbours visibly.
- **Judge it.** Check 97.

## Presets and the desk

### 72. The bank of twenty-four

- **Built.** A show's bank is 24 slots: 1–8 are F1–F8 and clip row 1;
  9–24 are clip rows 4–5 and the PRESETS page's sixteen smaller buttons
  (four a row). Slots 9–24 have no triggers of their own; they are
  reached through `preset.select`. The show file stays
  `hyperspace.project/2`, is never rewritten by a load, and holds the bank
  only up to its last filled slot; the first write past slot 8 keeps the
  old file as `<show>.hyp.json.bak-v2-bank8`. A fresh home's factory party
  show has TRACER on slot 9.
- **Other options.** Load/save triggers for every slot (32 more params);
  a new `project/3` format (older builds refuse your show); far slots
  eight a row.
- **To reverse.** One line each (`params.build_registry`,
  `library/projects/party.hyp.json`, `ui_presets.FAR_COLS`); a new format
  needs a migration.
- **Rough edge.** An absolute knob learned onto `preset.select` spreads
  over all 24 and can rest on an empty slot (audit R14). With "more" open,
  a warning line scrolls the PRESETS page a little.
- **Judge it.** Checks 81 and 83.

### 73. Clip rows 4–5 are the bank, and how the bank lights

- **Built.** Rows 4–5 load slots 9–24 on both layers (invariant). A bank
  pad is green when its preset is loaded, amber (Akai velocity 5) when its
  slot is filled, dark when empty. The sixteen shape pads older presets
  carry on those rows are dropped quietly at load; any other row of yours
  on them is dropped with a note. Shapes are on the cue knob (all 25).
- **Other options.** Only the loaded pad lit; a note per dropped row.
- **To reverse.** `apc40.filled_of` returns None (lights); empty
  `routing.RETIRED_DESK_ROWS` (quiet drop); rows 4–5 back to shapes needs
  the map and a remap with a backup.
- **Rough edge.** No pad shows which shape is up. Amber beside green is
  unseen on the mk1.
- **Judge it.** Checks 82–84.

```
 the desk's clip grid      preset layer                             under SHIFT (global layer)
        1     2     3     4     5     6     7     8      9         1 … 8                  9
 G1   [ 1]  [ 2]  [ 3]  [ 4]  [ 5]  [ 6]  [ 7]  [ 8]   Points      [ 1] … [ 8]            ·
 G2     ·     ·     ·     ·     ·     ·     ·     ·    Lines       scene 1 … scene 8      ·
 G3     ·     ·     ·     ·   STILL ORBIT WAVE RIPPLE  Faces       scene 9, 10, 11        ·
 G4   [ 9]  [10]  [11]  [12]  [13]  [14]  [15]  [16]   Rotate      [ 9] … [16]            ·
 G5   [17]  [18]  [19]  [20]  [21]  [22]  [23]  [24]   Reset view  [17] … [24]            ·
 G6   [============ SAVE AS (hold) ============]      [Reset all]  [==== SAVE AS ====]   [Reset all]
 C    cue knob: Shape (all 25)                                     ·

 [ ] invariant (the same on both layers)   · dark   [n] bank slot n
 a bank pad: green = loaded · amber = a preset is here · dark = empty
```

### 74. No backup, no rewrite of `bindings.json`

- **Built.** When a launch brings `bindings.json` up to date it backs the
  file up first; if the copy fails, the file is not rewritten for the rest
  of the session (the table in memory is updated; the next launch tries
  again). One line on the SYSTEM page says what the launch did, e.g.
  "bindings.json updated (16 rows changed), the old file kept as
  bindings.json.bak-v3"; each change is also on stderr.
- **Other option.** Rewrite anyway, with nothing to go back to.
- **To reverse.** The three `backup(…) is None` branches.
- **Judge it.** Checks 84 and 57.

### 75. The device knobs, only where they do something

- **Built.** A fresh preset, and every factory preset with no knobs of its
  own, gets D1–D4 = 4D depth, yaw, pitch, face pattern; D5–D8 dark.
  `hands-fx`, `hands-pinch` and `lfo-breathe` have their own sets. WAKE,
  TRACER, TRIP, ACID, MANDALA and NOITA keep their eight. A preset you
  saved before keeps its own desk.
- **Other option.** Make every scene preset "echo-ready" (look-back on,
  echo mix and fade on D5–D6): every party preset pays for a dream nobody
  sees.
- **To reverse.** One tuple in `preset.py` or `apc40.SCENE`, then
  `python -m hyperspace.preset`.
- **Rough edge.** D4 (pattern) changes nothing visible on a preset with
  faces off. Never turned on an APC40.
- **Judge it.** Check 85.

### 76. Hide, rename and the trash, in the preset list

- **Built.** In the preset list: × on every preset (yours go to the
  trash; a factory one is hidden via `<home>/hidden.json`), **rename** on
  yours, and at the foot "show hidden (n)" and "trash (n) ▸" with
  **restore** and **empty trash…**. Renaming a factory preset is refused
  ("save copy, then rename the copy"). Rename repoints every show of yours
  that names it, each copied to the trash first; it is not an undo step.
  Restore never writes over a file (a taken name restores as the next
  free one). Empty asks for a second click within 4 s.
- **Other options.** Rename a factory preset by copying and hiding it;
  put the trash under "more" on PRESETS, or a TRASH page.
- **To reverse.** A branch in `Library.rename`; two lines moved out of
  `ui_presets._list_popup`.
- **Rough edge.** **Empty trash is the one delete with no copy kept.** ×
  on yours leaves slots naming it in the warning colour until restored.
  No person has clicked these popups.
- **Judge it.** Checks 86–88.

### 77. The red dot and "save copy"

- **Built.** The dirty dot is a 12 px red disc on every strip and on
  ROUTING's head, and the save chip is solid red while there is something
  to save. On a factory preset the chip reads "save copy" (your copy takes
  its place in the list). The preset strip has no reset. Nothing prompts.
- **Other option.** "save copy" on every strip (a module strip would not
  fit).
- **To reverse.** `ui.DOT_R`; `ui_presets.save_label`; one condition in
  `ui_presets.strip`.
- **Rough edge.** On a module strip under "more" the save chip overlaps
  the name button (audit U10).
- **Judge it.** Check 89.

### 78. The home in git

- **Built.** With `[library] git = true` (off by default) the home folder
  is a local git repository: no remote, nothing pushed. The first save
  after launch makes it; every save, trash, rename, hide, unhide, restore
  and show write is a commit. The trash, `weights/`, logs, `last_show`,
  `windows.json` and the `*.bak-*` backups are ignored. A home inside
  another repository is never touched. Git runs on its own thread and
  never blocks or fails a save; a failed commit is said once and the next
  one picks up its files.
- **Other option.** Track the trash ("empty" recoverable; every overwrite
  stored twice).
- **To reverse.** One line of `homegit.IGNORE`; off is the config key.
- **Rough edge.** Emptying the trash makes no commit, and the app never
  restores from git (use git yourself).
- **Judge it.** Check 90.

## The outputs and the ghost hands

### 79. Where "hands through effects" puts the hands

- **Built.** With an output's "through effects" tick on, its hands go in
  after the look-back composite and before the first effect, so the
  effects bend them. The echoes and the dream are captured from the scene
  alone and never hold the hands. With the scene off and through on, the
  output shows the hands alone through the effects, on black.
- **Other options.** Hands onto the scene before the look-back (they
  trail and feed the dream, but then every output shows hand echoes); the
  scene off + through the same as "hands over".
- **To reverse.** A few lines in `Renderer._pipeline` (every output at
  once); per output needs a second history and dream worker (days).
- **Rough edge.** Two outputs that disagree run the effects twice a frame.
- **Judge it.** Checks 102 and 103.

```
   scene  hands  through   what the output shows (an effect on, a hand in the box)
    on     on     off      the scene with its effects, the hands clean on top   (default)
    on     on     on       the scene and the hands, both bent by the effects
    on     off    —        the scene with its effects
    off    on     off      the hands alone, clean, on black
    off    on     on       the hands alone, bent by the effects, on black
    off    off    —        black
   With no effect on, or no hand shown, "through" changes nothing.
```

### 80. The guide and the tethers' labels are never bent

- **Built.** When hands go through effects, the guide (balls, rings,
  pinch beads) and the tethers' text labels are drawn in a second layer
  laid on after the effects, so they stay legible. The second layer exists
  only while it is needed; otherwise the hands are one layer as before.
- **Other option.** Let them bend with the hands.
- **To reverse.** Delete the readout layer (`Ghost.readout`,
  `Ghost.composite_readout`), a few hours.
- **Judge it.** Check 103.

### 81. Each output's switches are rig settings

- **Built.** `output.N.scene`, `.hands`, `.through` and `.dim` are never
  saved, not performable, and untouched by presets, shows and undo. Every
  launch and ⌘R takes them from the `[[output.screens]]` entries in
  `config.toml`; a config `dim` under 0.1 is raised to 0.1 so the config
  cannot launch an output black (the fader still goes to 0). An output's
  own dim fader exists when two or more outputs are listed, or when a lone
  output's entry sets `dim` under 1. Each switch can be learned onto a
  desk button.
- **Other option.** Session params saved in the show (a show made on the
  rig would carry `output.2.*` to a laptop).
- **To reverse.** Flip `persist` in `overlay.register_switches`, an hour.
- **Judge it.** Checks 101 and 104.

### 82. An output of another shape is letterboxed

- **Built.** The frame is drawn once, at output 1's size. An output of
  another shape shows the whole frame, centred, with black bars; the hands
  sit on the same part of the shape on every output. List the larger
  screen first in the config.
- **Other options.** Cover (crop); stretch; render per output size (days).
- **To reverse.** `outputs.fit`, a few lines.
- **Judge it.** Check 106.

### 83. One window renders, the others copy; only output 1 waits

- **Built.** Output 1's GL context renders every distinct picture once;
  each later output copies it in its own context and adds its hands,
  guide and dim. Only output 1's swap waits for its screen; the others
  swap at once. The hands' layer has no size cap.
- **Other options.** Every output waits (no tearing anywhere); a hidden
  window renders and every output copies.
- **To reverse.** One `glfw.swap_interval` call per output
  (`app._open_presenters`); the hidden renderer is days.
- **Rough edge.** **The reason is unconfirmed**: the plan measured two
  waiting swaps halving the frame rate, but the build's launches ran
  unpaced. Never run with two screens or mixed refresh rates.
- **Judge it.** Check 107.

### 84. Ghost hands and each output's hands tick

- **Built.** Both stay. Ghost hands (`ghost.on`, HANDS page) says whether
  hands are drawn at all; each output's tick says where they show. The
  OUTPUT page names Ghost hands when it is the reason an output has none.
- **Other option.** The ticks replace Ghost hands (breaks saved shows and
  learned rows, no single off).
- **To reverse.** A migration of shows and rows on `ghost.on`, a day or
  two.
- **Judge it.** Checks 102 and 105.

### 85. The OUTPUT page says in words what each output shows

- **Built.** Each output has a "shows: …" line ("scene + hands over the
  effects", "black — dim 0", …), and the footer names a black output on
  every page ("output 2 black"). There is no picture of the render in the
  control window. With one output there is one block and no dim row of
  its own (the master dim is its dim).
- **Other option.** A small live picture per output (about 0.5 ms each).
- **To reverse.** About a day for the pictures.
- **Judge it.** Checks 102 and 105.

### 86. A screen not connected at launch; later outputs' screens

- **Built.** A later output whose screen is not connected at launch is not
  opened, with a note ("screen 2 is not connected" on the OUTPUT page).
  Output 1 always opens. Later outputs take their screen and fullscreen
  from `config.toml` only; the OUTPUT page's screen and fullscreen
  controls are output 1's.
- **Other options.** Open it anyway, where it was last or on the first
  screen (it would cover the controls); a screen and fullscreen control
  per output.
- **To reverse.** One branch in `app._later_rect`; per-output controls
  half a day.
- **Rough edge.** A screen plugged in after launch is not used until ⌘R or
  a relaunch (audit P6). What macOS does when a cable is pulled mid-run is
  unknown.
- **Judge it.** Checks 101, 111 and 112.

### 87. `ghost.style`: five drawn objects for the hands

- **Built.** One choice on the HANDS page, saved with the show, never
  performable (a desk button or knob can be learned onto it):

  | Style | What is drawn |
  |---|---|
  | HANDS | the capsule hands (the default, unchanged) |
  | JOINTS | a bead per joint, the fingertips largest |
  | PALMS | an orb that swells as the hand opens, a ring in the palm's plane, a spoke where the fingers point |
  | CAGE | a wire octahedron round each hand that turns with the palm, a small solid inside |
  | MARIONETTE | a bead per fingertip on strings from a bar above the hand |

  In the four new styles the guide is drawn on top.
- **Other option.** Five separate on/off switches.
- **To reverse.** One function in `ghost.PARTS` per style.
- **Judge it.** Check 109 — and say which styles to keep.

### 88. Ghost mirror, guide and tethers cannot follow a hand

- **Built.** `ghost.mirror`, `ghost.guide` and `ghost.tethers` (with
  `ghost.style`) are not performable. A hand Learn onto one is refused in
  words ("… can't follow a hand (not modulatable) — not learned; Learn
  desk puts it on a button"). A saved route onto one is dropped at load
  with a note; the file is not rewritten. `ghost.on` and `ghost.alpha`
  stay performable.
- **Other options.** Leave them performable (a route could flip the hands
  mid-set); not performable with no refusal (a Learn writes a dead row).
- **To reverse.** Three flags.
- **Judge it.** Check 110.
