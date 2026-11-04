# Plan 56 — paired axes

**Status: built (2026-11-04)** as wave 4 PA on `wave4/pa`. Register rows 748–751;
hand checks 575–577, group CQ. **Restart, not hot reload** for a pad's ports; the
rows and lanes are read each frame.

The owner, 2026-11-04: "toggle controls need to be able to be paired into a
polarized axis: pressing one of the toggle controls moves you along one pole of
the axis, and pressing the other moves you on the other pole." Whether a press
steps or nudges a spring "is immaterial": the point is the pairing.

## How a pair is declared

**By being named.** A pair is an address, `pair:<+ pole>/<− pole>`, its poles any
two different discrete controls of one pad, in the names rows already use:
`pair:UP/DOWN`, `pair:RB/LB`, `pair:A/UP`, and on a second pad `pair@p2:UP/DOWN`.
There is no table of pairs to keep and no file field. A preset that reads a pair
carries it in the row's `source`, so the look plays on any machine.

**A model's natural pairs are published by default** (`pads/models.py`, `PAIRS`,
filtered by what the model has, `natural_pairs`): the D-pad's two, the bumpers,
the back buttons, the Fn buttons and the face's two. A single Joy-Con has no
D-pad, so its four arrows are its natural pairs. A pair nobody published is
published the first time a row names it (`Sources.resolve`).

Up and right are high, as on a stick, and the first pole is the positive one.

## What a pair publishes

**One lane**: `0.5` at rest, `1.0` on the + pole, `0.0` on the − pole, `0.5` with
both held. It rests where a stick does and is read by the one path a stick is
(`Router.modulate`): a route on it pushes, positions and takes a feel like any
other. No pad: the feed is `None` and the routes let go. A pole the totem or the
poi holds reads as not pressed.

## Step or spring

**The row's op is the parameter.** There are two shapes and no new field.

| | The row | Where it lives | A press |
| --- | --- | --- | --- |
| **step, the neutral default** | `pair:UP/DOWN → p`, op `step`, value n | the meta controller's table, like every pad button row | + pole `p.step(+n)`, − pole `p.step(−n)`, once per press |
| **spring** | `pair:UP/DOWN → p`, op `push`, a feel | the preset, like any route | moves the lane; the row's feel carries it |

A `step` row acts exactly as two `hat:` rows would: same frame, same order, each
edge once, so both poles pressed together cancel. Other button ops on a pair are
refused.

**The factory rows stay two rows.** `hat:UP/DOWN → view.bright ±3` and
`pad:LB/RB → view.shape ±1` are not rewritten and act exactly as they did; a test
holds them to it. They are pairs in the published sense: their two poles are one
lane and one degree of freedom.

## Where a person sees it

- **Learn:** the param menu's **Learn pair** (a step row) and **Learn pair
  (spring)** (a route). Press the + pole, then the − pole. A plain Learn pad is
  unchanged: one press, one row.
- **GRAPH:** a pad's node has a **pairs** port group, bipolar. A cable from one
  makes a route, as a stick's does.
- **Pad window:** a pair row lights both poles, with + and −; the hover names the
  control's partner; the lanes view has a **pairs** group.

## For later

- **Node mode (plan 53):** `gamepad.degrees_of_freedom(model, pairs)` is the
  count: a pair is one entry, a lone button one, a stick's axis one.
- **NSEW** renames control names. A pair's address holds only those names, so it
  migrates by the same table and adds no spelling of its own.
- **Not built: poles on keys or MIDI notes.** Their rows are dispatched by
  `Router.keys` and `midi.py`; the address has room for them.
- **A route on a pair leaves its poles' own rows alone.** A preset's route may not
  edit the meta controller's table, so both act, and both are drawn.

## An older build

No format change. A `pair:` route is a continuous row with no feed, so an older
build reads it as dormant, keeps it and writes it back, as it does a row naming a
device its machine lacks. A `pair:` `step` row in `bindings.json` loads inert the
same way, because a file load does not referee button ops. An older build's GRAPH
draws a grey `pair` placeholder.
