# Plan 52 — the base chase

**Status: built (2026-11-03)** as wave 3 B1 on `wave3/b1`. Register rows
654–656, every one (rec) pending the owner; hand checks 494–496, group BO.
**Restart, not hot reload** (`deck.chase` is declared when a registry is
built). The gamepad row is B2, wave 4: BACK (`pad:VIEW`), register rows 723–724.

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

The exception is a source dropping out for a frame: the look holds rather than
falling back to the base, since the base is what it showed.

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
- **The source dropping out** (a lane gone NaN, a shut gate, a pad off): the
  base shows, as any param let go, and the ledger **stays**. The offset that
  comes back is the one the base holds, so a flickering gate commits nothing
  twice, under the verb or after it. One coming back at or below where it left
  is still on its way home.
- **The rows going:** a param none of whose rows is left has lost the source the
  ledger was about, so it empties (`Router._forget_lost_rows`, at the plan's
  rebuild, no frame cost). A row made later rides in full. The referee keeps one
  performer on a param, so a second row can only come beside the first where the
  referee allows it (rows it does not call overlapping). Those share the ledger,
  which is on the param's sum, and if the first source goes home first the other's
  offset is absorbed until the sum reads zero. That is the one stale case left,
  and it has no test.
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

**Anything else that closes the step ends the verb** (`Undo.keep_open`'s
`on_end`): an undo, an action's push (a load, a learn), a band reshape, a
`clear`. So one hold is never more than one step: an undo under the verb takes
the hold back and the verb lets go, however long the button stays down, and
the redo stands. Pressing again is a new hold. A press closes whatever was
open first, so no other action's step is pinned. The step belongs to the `Undo`
the press named (`Registry._chase_steps`), and any let-go closes that one.

A base goes back with its own ledger. Each undo state holds the trims as they
stood (`State.trims`), and a restore lands both (`Registry.restore(trims=)`):

- **Undoing a hold with a push still out** shows the old base plus the push, as if
  the verb had never been held. **Redo** shows the commit, not counted twice.
- **Undoing a later knob turn** on a committed param lands the commit and its
  ledger, with no double count. **Drop** the same, with no jump. A second hold
  undone stands as it stood before that hold.
- **A state's ledger can be late:** a source that came home after the state was
  taken and has pushed out since is absorbed up to that much at the undo, until
  it next falls. The trim only ever falls from there.

**A load holds no commit.** `Registry.restore` with no `trims` empties the ledger
on every value it lands, so the look shows its saved base plus the route's whole
offset, even if the value is the same number as the commit. The pose a load sets
does the same (`Registry.forget_commits(POSE_IDS)`). Undoing the load brings the
commit back with its ledger.

## Dirty

A commit moves a base, so it is an edit and the dot lights by the ordinary
compare. A save writes the committed value. A hold that moved nothing lights
nothing (`undo.alike` reads the round-off as no edit).

## The projector's hold (row 656)

There is one hold for the rig, built by the first deck only, so its guard lives
on the session: a press on **any** deck is refused under it, and `Hold.engage`
lets the verb go on every deck. A deck beside has no program to protect today,
so that is the rule kept whole, not a jump prevented there.

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

`reg["deck.chase"].set(True / False)`, whose setter calls `reg.base_chase`.
The pad's factory row holds it on BACK (`pad:VIEW`, `momentary`; the owner,
2026-11-04, register row 723). An older file's factory tap-tempo row on BACK
moves there at the next load; a file with nothing on BACK stays so, as the owner
may have deleted it; and a row of the owner's on BACK stays, leaving that pad
without a chase. It stays on until every source holding it has let go
(`routing.press_momentary`), and a pad device closed lets go (`Router.pad_lost`). A Joy-Con (R) has
no BACK, so it is the same (row 724); the (L)'s − has it. Learn pad is armed from a
widget and this param has none, so a second pad button today is a line in the file.
A test presses it, and Learn lands a note or a pad button on
it as `momentary`, so it is held and not latched, and a knob is refused in
words. A row that could latch it (a `key` row, a `toggle`, a `set`, by hand in
a file) is refused and dropped on load, as for the desk's SAVE
(`routing.latch_refusal` over `routing.HELD_ONLY`). `HELD_ONLY` is by id, not an
attribute on `Param`, because the referee has a row and no registry.

A release that will never come lets go at once: the desk's cable pulled
(`MidiIO._let_go_held`, on the frame it is lost, and at a reconnect as before),
a pad gone to sleep or unplugged, or the totem taking its button (`Router.pad`,
only for what that pad holds).

**No frame hook is wanted.** The deck's operation is `Deck.chase(on)`, added
once D4 merged: `self.reg.base_chase(on, steps=self.undo)`. `Deck.build` hands
each registry its own undo (`Registry.chase_undo`), so the `deck.chase` control
takes the same road. A chase on deck 2 keeps its step on deck 2's stack and
writes nothing on deck 1 (`test_a_chase_on_deck_2_keeps_its_step_there_and_writes_nothing_on_deck_1`).
A bare registry, with no deck, has no steps.

## Not done

- A panel button or a light for the verb: `deck.chase` is reached through the
  desk's "all params ▾" menu.
- A key cannot press it: keys have no `momentary`, and a key row that would
  toggle it is refused.
