# Plan 89 — an effect's slots, in place of the copy node

**Built** 2026-11-23 on `effect-slots`. Register rows 1081–1086, hand checks
873–875 (group FJ). Schema moves: a loadable patch `hyperspace.loadable/12`,
a patch fragment `hyperspace.patch/3`. No golden moved (below). Row 1081 is
the owner's; the rest are the build's, "(rec)", to keep or overturn.

## Why

A **copy** (plan 35 F, row 377: `copy`, `copy.<n>`, `{"kind": "copy", "of":
"acid"}`) drew effect instance `of` again on another picture with its knobs
and its clock. It was what the retired per-output pipelines' own run was,
said as a node (plan 35, row 350). But it was a node that owned nothing:
selected on GRAPH its side panel was empty (`graphview.params_of` pointed it
at `fx.<of>`, which the panel lists on the original's node), node mode on it
had to land its cables on a pin of its own (`NODE_PIN`), Save as patch had a
refusal just for it ("a copy without its original"), deleting the original
had to sweep its copies (R16), and two nodes on the canvas said one effect.
The owner (2026-11-23): the wrong shape, a sharp edge — fix it now.

## The shape

**An effect node has slots.** Slot 1 is the effect itself — its name, its
`image` and `aux`, its picture out — as it always was. Slot *k* (2 … 8,
`graph.MAX_SLOTS`) is `<effect>.slot.<k>`: `acid.slot.2`, `acid.2.slot.3`.
Each slot has its own `image` and `aux` in and its own picture out, and is
processed separately with **the one set of knobs and the one clock**: a
slot's pass is `FxChain.run_one(effect, …)` on its own input, exactly what a
copy's was (`graph.Slot` is what `graph.Copy` was, renamed; `signature`
counts it as the `Effect` it runs).

- **Declared by its effect.** The effect's entry says `"slots": n` (written
  only above 1): `{"kind": "effect", "file": "acid", "slots": 3}`. A wire
  naming a slot its entry does not declare is a note
  (`graph.SLOT_NOT_DECLARED`); `slots` out of 1 … 8 is refused
  (`SLOTS_RANGE`). An instance 1 named only by wires gets an entry to say its
  `slots` on.
- **Named like a pin.** `acid.slot.2` is an output of `acid`'s node as
  `lookback.echo.3` is of the look-back's (`graph.slot_of`, `effect_of`,
  `slot_name`); kind `"slot"` (`WIRED_MAKES`, `WIRED_TAKES`: an effect's).
  It is not a pin to the graph's reach and loop analysis (`pin_node` is
  unchanged): a slot depends on its own input, never on its effect's
  picture, so `acid → acid.slot.2.image` is a chain (what a copy after its
  original was), not a loop.
- **One node on the canvas.** The effect's node draws a row of ports per
  slot — `image 2`, `aux 2` in, `2` out (`rin:acid.slot.2/image`,
  `rout:acid.slot.2`) — so selecting it shows its one set of controls, node
  mode lands on its own params, a group holds it whole and Save as patch
  carries it whole. `graphview.canvas_node` maps a wire's end to the node it
  is drawn on (a pin's node, a slot's effect); the effect is drawn reached
  while any of its slots is (`unreached`).
- **Edits.** The picker's **slot on ▸** (was **copy of ▸**), an effect's menu
  **add slot** and **remove slot k** (`graphview.add_slot`, `drop_slot`),
  and ⌘V after ⌘C on an effect (one more slot on it, the effect selected).
  Removing a slot lifts it (what fed it goes on to what it fed, as a delete
  does) and numbers the later ones down, their wires with them
  (`drop_slots`); deleting the effect takes its slots (R16 as it was).
  OUTPUT's **hands through the effects** writes a new slot of each effect of
  the run (`graphmigrate.through_wires`, `_next_slots`, `merge_entries`) and
  takes it off again (`_drop_through`), the section as it was.

## The migration (one way, on load)

`graphmigrate.slots_of_copies(section)` → (section, copy → slot, notes):

1. A section's copies of one effect instance, **lowest copy instance first**,
   become that effect's **next slots**: with `acid` holding one slot, `copy`
   of `acid` is `acid.slot.2`, the next copy of `acid` `acid.slot.3`.
2. The effect's entry says the new `slots` (an entry is added for an
   instance only its wires named); the copy's entry goes.
3. Every wire end that named the copy — its picture out, its `image` and
   `aux` in — and a `keys` member (plan 87) name the slot.
4. A copy whose `of` is no effect instance of the section (one the old read
   already dropped, `COPY_BAD_OF`) is dropped with its wires and said
   (`COPY_DROPPED`); one past `MAX_SLOTS` the same (`COPY_PAST_SLOTS`).

Where it runs:

- **A loadable patch**, `/11` → `/12` (`graphmigrate.twelve`, first in the
  ladder `forward`, before anything reads the section — a `/6` wired frame
  could hold a copy): the graph as above, and the copies' GRAPH places
  (`layout["render:copy"]`) and group memberships dropped — a slot is drawn
  on its effect's node, which has its own place. Said once on the strip
  (`SLOTS_MIGRATED_NOTE`) when there was a copy; a `/11` with none comes out
  as it was but for its schema. Every save writes `/12` (`SAVE_SCHEMA`); an
  older build refuses a `/12` as newer (it cannot read a slot).
- **A patch fragment**, `patch/2` → `patch/3` (`patches._slots_step`): the
  same rule over its nodes, wires and `keys`, a boundary port's own end
  (`to` / `from`) renamed, the copy's canvas place dropped.
- `tools/migrate_library.py` writes `/12` (`NEWEST`).

**The picture is the same.** A slot runs the pass its copy ran, on the
picture the copy took, with the same knobs and clock; only the node's name
changes (`copy` → `acid.slot.2`, its end `shown(copy)` → `shown(acid.slot.2)`).
`through-one-output` (plan 35 T3's copy fixture) and every golden whose rig
wires "hands through" were recorded with copy nodes. **No golden moved**: no
PNG or hash was touched. The manifest's recorded node names and
`through-one-output`'s landed section were rewritten in the new names
(`tools/golden_frames.py`'s `record_names`, which asserts no hash or PNG is
touched). The checked-in `/11` corpus, presets and fixtures (58 files) and the
band scenes (`patch/2`, 11 files) are bumped to the new schema — none held a
copy, so the bump is their whole migration and they still resave byte for
byte; `docs/plans/assets/37-faces/migration-map.md` regenerated (its schema
column alone moved).

How it was checked: the goldens are recorded on the owner's Apple M3 Max, so
in the build's container (llvmpipe) the byte-for-byte golden test skips. In
its place, every corpus patch and fixture (51) was drawn through the golden
rig in all eight states, hands present (`golden_frames.picture`), on the base
commit (copies) and on this build (slots), on the same renderer: all 408
frame hashes equal. On the Mac, the golden tier (`pytest -m golden`) is the
check that remains to run (hand check 875).

## Not changed

Composites and blends (being unified elsewhere), and who owns the hands',
the scene's and the shape's params (another change), are untouched. The
stand-down (`Shown.fallback`, row 378) reads a chain of slots where it read
a chain of copies.

## Files

`graph.py` (`SlotAt`, `Slot`, `EffectAt.slots`, `slot_of` / `slot_name` /
`effect_of`, the wire checks, the builder), `graphmigrate.py`
(`slots_of_copies`, `twelve`, `merge_entries`, `_next_slots`, `/12`),
`graphview.py` (slot ports, `canvas_node`, `add_slot` / `drop_slot` /
`drop_slots`, the picker, labels, `params_of` without `of`), `ui_graph.py`
(the effect's menu, ⌘C / ⌘V), `patches.py` (`/3`, `_slots_step`, a slot
renamed with its effect, no copy refusal), `loadable.py` (`/12`,
`node_params`), `render.py` (`unwired_through`), `ui_fx.py`,
`tools/migrate_library.py`.

## Tests

`tests/test_effect_slots.py`: the migration rule (renames, entries, keys,
dropped copies, `MAX_SLOTS`), `/11` → `/12` through the ladder with layout
and groups, a `/6` fixture up the whole ladder, a `patch/2` fragment, the
round trip and a spawn's rename, two migrated copies building node for node
the slots' frame, and — on GL — three slots of one effect in one frame
(slot 3 and slot 1 on the scene byte for byte, slot 2 on the hands' layer
its own, acid off: every slot reads through). `tests/test_graph_wired.py`
(the copy entry refused, a slot's declaration), `test_graph_edit.py` (add,
remove and close up, delete with its slots, the picker), and the existing
copy tests across `test_graph_frame`, `test_graph_effects`, `test_graph`,
`test_ui_output`, `test_node_mode_graph`, `test_graph_copy_paste`,
`test_aux_ports`, `test_patches*`, `test_format_lane` rewritten for slots.

## Not seen

The slot ports' layout and hit areas on the real canvas with a trackpad, and
an old library with copies migrated on the owner's Mac: hand checks 873–875.
