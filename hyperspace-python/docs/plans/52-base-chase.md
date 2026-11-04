# Plan 52 — the base chase

**Status: built (2026-11-03)** as wave 3 B1 on `wave3/b1`. Register rows
654–656, every one (rec) pending the owner; hand checks 494–496, group BO.
**Restart, not hot reload** (`deck.chase` is declared when a registry is
built). The gamepad row is B2, wave 4.

The triage's phrase is "Base chase modifier". The verb: while held, what a
param shows with its modulation (the performer's motion) is written into its
base, so on release the look stays where the performer left it.

## What it does

`Registry.base_chase(on, steps=None)` flags every param it reaches once, at
the press. From then on each landing (`Param.apply`) also writes what it put
on the object into the base (`Param._commit`). `apply` already runs once a
frame for every modulated param, so there is **no per-frame hook** and no
scan. A param with no source on it has nothing to commit and stays as it is.

The verb changes nothing on screen while it is held. A chased param shows, on
every frame, what it would have shown with no verb
(`test_while_held_it_shows_what_it_would_have_shown`). Only the base moves.

A consequence to judge (row 654): a source that goes home **while the verb is
still held** takes the look home with it, because that is what shows. To keep
a stick's throw, let go of the verb first, then the stick.

## Which params

Continuous, modulatable and the deck's own (`params.chase_reaches`):

| Param | Reached | Why |
|---|---|---|
| a continuous look param, `rot.rate.*`, `camera.*`, an LFO's or modifier's knob | yes | |
| `rot.phase.*` | yes | The commit stays, but the turn is no base: no undo step, no dirty dot (row 573) |
| an enum, a toggle, a trigger, text | no | They move with hysteresis or fire; they have no between-values to commit |
| a session param, a session key (`ghost.mirror`) | no | One for every deck, the room's; a deck's verb never writes it |
| `macro.*` | no | A macro's base moves its base subscribers (`Router.follow_macros`), which an offset never did: a commit would jump them (row 655) |

`deck.chase` is the rig control: a toggle in group `deck`, in neither part of
the split, so every deck has its own and no file holds it. A param declared
under the verb (a preset loaded while it is held) is reached too
(`Registry._put`).

## Base, landed value and the routes' depth

No route is touched: a row's depth is the depth it was, and nothing about the
verb reaches a file but the bases. Writing the shown value into the base
would count the offset twice (base + offset, with the offset already in the
base), so `Param._trim` is the ledger: how much of the pushes' offset the base
already holds. The landing is `base + (pushes − trim) + position rows`.

- **While held:** the trim is the whole push each frame, less any part a
  range's end cut off (not in the base, so a source coming back off the end
  stop lands as it would have).
- **Let go:** the trim only falls (`params._came_home`). It follows the push
  on its way to zero and never passes it:
  - a source staying where it was moves nothing, so there is no jump;
  - a source going home moves nothing, so the look stays;
  - a source pushing further than it was moves the look on from there;
  - a source past zero rides in full, and the ledger is empty for good.
- **The source leaving** (out of view, gate shut): the ledger empties and the
  base shows, as any param let go.
- **A position row** is the fader: it lands an absolute value whatever the
  base is, computed against the base, so no trim applies to it.
  `Param.modulate(position=True)` keeps its share apart (`Router.modulate`
  says which; one line in `routing.py`). Its last value is what stays. A push
  beside it is counted in the ledger, so the row going away does not double it.

The ledger is runtime only. A knob turned on a chased or trimmed param moves
the base, with the look on it, as ever.

## Undo: one step per hold

The press opens one step named "base chase" and no quiet closes it
(`Undo.keep_open`), so a hold that pauses past `SETTLE_S` is still one step.
The release closes it at once (`Undo.let_close`), and a hold that moved
nothing leaves no step, as any empty step. This is the only change to
`undo.py`'s rule.

A restore lands through `Registry.restore`, which empties the ledger: the
route rides the restored base in full. Undoing with the source still out shows
exactly what would have shown with no verb. **Redo with the source still out**
shows the committed base plus the whole offset, the one place an offset is
counted on top; with the source home it is the committed look. A load empties
it the same way.

## Dirty

A commit moves a base, so it is an edit and the dot lights by the ordinary
compare. A save writes the committed value. A hold that moved nothing lights
nothing (`undo.alike` reads the round-off as no edit).

## The projector's hold (row 656)

Under plan 38's hold the operator's edits are the preview, and the performer
rides on both. `hold.program_value` reads the offset as `value − base`, and a
commit makes that 0, so the program would lose it and the projector would
jump. So a press under the hold is **refused** (`Registry.chase_guard`, set by
`hold.register`; the control stays dark), and `Hold.engage` lets go of the
verb first, so its step closes before the point Drop goes back to and
`Hold.values` holds the commit as the held base. A trim left over from a
release is harmless: the program adds what the object shows beyond the base.

D5 retires `hold.py`; the guard goes with it, and deck A's verb stays on air
while B is built.

## Session params and two decks

A session param is never flagged, so `deck.chase` on any deck leaves the room
alone. Each deck's verb reaches its own registry only
(`test_two_decks_chase_alone_and_leave_the_session_alone`).

## How it is called, and the seam

Today: `reg["deck.chase"].set(True / False)`, whose setter calls
`reg.base_chase`. A test presses it, and Learn lands a note or a pad button on
it as `momentary`, so it is held and not latched. A lost note-off is let go at
the desk's reconnect (`midi.HELD_PARAMS`).

**No frame hook is wanted.** While D4 holds `deck.py` frozen, the one seam
left is this method, for after D4:

```python
def chase(self, on: bool) -> bool:
    return self.reg.base_chase(on, steps=self.undo)
```

It names the deck's own `Undo`. Until it lands, `deck.chase` uses the
installed `Undo` (`undo.installed()`), which is the deck on air's, so a second
deck's hold would not be kept as one step on its own stack.

## Not done

- B2, the gamepad row (wave 4; the button is the owner's choice).
- A panel button or a light for the verb: `deck.chase` is reached through the
  desk's "all params ▾" menu.
- A `key:` row holds nothing: keys have no `momentary`, so one toggles it.
