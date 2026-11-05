# Plan 55 — players and duties

**Status: built (2026-11-04)** as wave 4 PL on `wave4/pl`. Register rows 733–736; hand
checks 563–565, group CL. **Restart, not hot reload:** a new module and new fields on
long-lived objects. The select screen is PS, next, by another builder.

The owner, 2026-11-04: "Controllers are generic; the actors are named: player 1, 2, 3,
4." A player "registers any number of controllers and holds a duty: on air or off air.
It stays until someone moves it." "An off-air player stays with the off-air preset."
And the absolute rule: "no preset can affect another preset", of which "a row acts only
on the `Deck` its player is on" is the performers' half.

## What a player is

`players.Players` holds the four, each a `Player(number, duty)`, and who holds which
controller (a `devices` role). `deck.MetaController.players` is the one in the app.

**A patch names a player, never a device.** Bare rows (`pad:A`, `axis:LX`) are player
1's, with no file change; `axis@p2:LX` is player 2's. Plan 27's roles were the seam: a
qualifier was a role, and it is now the holder's name. A player's first pad publishes
under that name, whatever the pad's role (`devices.qualifiers_of`). A player's second
pad keeps its role as its address, so no two feed one lane.

**`@p2` always means player 2.** A role can be spelled like a player's name, and that
must never make two controllers answer to one name, at any step of a swap. A role takes
the name only if that player holds it, ahead of any other pad of theirs, so it need not
reopen. Held as a second of a kind, it is addressed `p3-pad` (`players.second_address`).
A primary so spelled gives up its `@role` alias as soon as another device publishes that
name (`DeviceRegistry.primaries`). The readers (`graphview`, `devices.wants`) ask who
publishes an address before taking it for a role.

**The camera job is the first pad listed on each deck** (`PadDevice._steers`). With
everyone on air that is the first pad, as before. A player off air alone keeps a stick
that orbits their deck, and the only pad given to player 2 keeps its job. Two players on
one deck: the second pad's unrouted axes do nothing, as decision 24 has it. If no pad is
player 1's, the launch notes say so, and `devices.wants` names "player 1" as missing.

**The hands, a desk and the bridge have no player in their addresses.** A hand's forty
lanes cannot be qualified (plan 27 B6), and MIDI rows name their desk by role as before.
Their rows act wherever their holder is: the gate below reads the holder's pointer, not
the address.

**Who holds what, with nothing registered:** `p2`, `p3`, `p4` are those players'; every
other role is player 1's; a kind's primary is player 1's whatever its role, so a rig
whose first enabled pad is called `p2` reads the bare rows as it did. Under this rule
`qualifiers_of` gives what plan 27 B6 gave, role by role (a test holds them equal).
A change of the device list can change who holds a role (the first pad disabled, so the
next is the primary): `MetaController.reseat`, on the registry's listeners, sends that
controller to its new player's deck and leaves every other where it is.

## Where it is remembered

**The meta controller's, on this Mac: `<home>/players.json`,** beside `bindings.json`
(`library_home()`, so `~/Hyperspace`). Not the shared library, not a patch, and not a
show, since shows are going away. Only what differs from the defaults is written, and
only when someone moves or registers a player; no file means everyone on air. A file
that cannot be read is said, kept as `players.json.bad`, and everyone is on air. A
player left off air is said at launch, once, in the notes.

    {"schema": "players/1", "duties": {"2": "off_air"}, "controllers": {"edge": 2}}

This is a new local file, in no migration: no preset, patch or show changes.

## What a duty means

`MetaController.deck_for(duty)`: on air is `on_air`, off air is `off_air`. Until D5c,
deck 1 is on air, so a player off air points at deck 2. When D5c's crossfader moves
`on_air_pointer` it calls `place_players()`: on-air players go across at the middle, and
off-air players stay with the off-air `Deck`.

## The surface PS builds on

| Call | What it does |
| --- | --- |
| `meta.players` | iterate the four (`.number`, `.duty`) |
| `meta.players.active()` | the players holding a listed controller |
| `meta.players.controllers_of(n)` | the roles player `n` holds |
| `meta.move_player(n, duty)` | the player and all it holds, remembered |
| `meta.register(role, n)` | that controller to that player, remembered; `on_players` told |
| `meta.deck_of_player(n)`, `meta.pointer(role).deck` | where they are now |

Nothing in `app.main` moves a player. Status words for a role stay `devices.lines()`'s.

## A row acts only on its player's `Deck`

`Router.feeds` hides a shared scheme whose controller's pointer is on another deck
(`Sources.away_from`, asking `DeviceRegistry.holders`; kept on the router until a pointer
moves or the list changes, 186 ns a read against 683 ns rebuilt, over ten schemes). The pass, a gate, a modifier's
input and the panel's readings all read that one view, so a row on a player elsewhere
is dormant by the same road as a source not live: it does not act, it loses its follower
and its turn's reading, and GRAPH draws its cable faint. So a turn on the deck a player
left forgets its reading and closes its undo step after `TURN_GRACE_S`, and on the deck
it reached the first frame only reads: no jump. **This answers DQ4.**

Hidden from the view, not from a write: `Sources.feed` and an adapter's `del` still reach
the shared dict. The analyzer is nobody's: every patch may wire from it. A deck's own
lanes (`lfo`, `env`, `seq`, `mod`) were its own already. A cloud or a media feed is not
a lane and is not gated here.

**With every player on air** deck 1 reads what it read, to the bit, and deck 2's rows
on a controller wait for a player. Before this, those rows ran in deck 2's pass whoever
held the controller, which is exactly the leak. It shows only above `output.xfade` 0.

A row on a player with no controller has nothing feeding it: dormant, and drawn on a
grey placeholder named for that player (`device:p3`), and it is in `devices.wants` as
missing. It used to be drawn on the first pad's node, whichever pad that was.

**Let go.** A press across a move ends on the deck it was made on, through
`routing.let_go_lost`: `PadDevice.act` with `Router.pad_left`, `MidiIO._follow_pointer`
(both D5a's), and now OSC (`_pressed_on`). A held chase ends with it.

**One controller, one `Deck`; mapping it elsewhere moves it.** `Learn.mapped` reports
each row a learn makes; `DeviceRegistry.mapped` moves that controller to the Learn's
deck. The player's duty does not change, and moving or placing the player brings the
controller back to the player (row 736).

## The totem and the poi

One `TotemState` and one `PoiState` sit on both decks, one pad's, so their switches and
dials follow the pad across a duty change. What they hold of a look is now of one deck:
`on_reg` says which, for `ang`, `ref` and `pan_out` (the totem) and the homes and lasts
(the poi). A pad arriving on another deck gives the old deck its pan back (the poi sends
that deck's pan and zoom home) and takes over afresh, adopting the new deck's phases, so
nothing jumps. Switching off or resetting from the other deck acts on the right one.
`poi.owns_pan` is true only on the deck the poi is writing.

## Found, not changed

- **The poi's guide** (`renderer.poi_source`) is one wire handed over to deck 2's renderer
  (`hand_over`), so a fade draws the guide on both pictures. D5c's list.
- **`poi.reset`, `poi.*` dials and `totem.w.*` on the panel** act on the pad's one state
  from either deck. They are a controller's, never a look's.
- **The totem and the poi read one pad each,** not one per player: two players cannot
  each hold a totem at once. An experiment; say if it should be per player.
- **A second pad of one player** has a role as its address, so a row on it names a device
  until someone gives the pair of pads a meaning (row 736).
- **A row naming a pad by a role whose player has changed** (`axis@pad` once `pad` is player
  2's) is dormant, drawn on that pad's node. No such row is written by a learn after this.
