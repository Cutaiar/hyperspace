# Plan 57 — the format lane, and node mode's saved form (wave 4 NM0, 2026-11-04)

**Status: NM0's data built; the lane is a plan, not started.** No schema moved and no
migration was written: the owner decides (§6). Register rows 715–717; hand checks 546–548,
group CF. Read at origin/main 4daa1b4. Tags: **[V]** run or read in the code, **[I]**
inferred, **[Rec]** a recommendation.

## 1. The recommendation

1. **NM0 lands now as an optional key.** No bump, no migration, no wait. A patch without it
   saves byte for byte, and no existing file changes meaning.
2. **The rest stays one migration, one bump, one backup,** after #365 and SEM, before the
   next show, once the owner has answered §6.
3. **`band.*` stays.** Nothing in §3's table is cheaper for renaming it, and the owner has
   since said the word is right for one band.
4. **The lane's two big items are open, and they are the owner's.** Patch words in the files
   and shows going away each need a design answer before a line is built.

## 2. NM0: the saved form

    "node_mode": [{"player": 2, "controller": "gamepad", "node": "render:acid"}]

Written only when something points, after `groups`, one entry a line. In `hyperspace/nodemode.py`
(`NodeMode`, `Pointing`), held by `Presets.node_mode`, one per `Deck`, in the dirty dot
(`signature`) and in a load's undo step (`library.Marks`). The owner: "It should just go in
the preset."

**`player`** is 1 to 4. A patch names a player, never a device (plan 55).

**`controller`, a word the brief did not name, for the owner to check (row 715).** It is a
device kind (`devices.Base.kind`: `midi`, `gamepad`, `hands`), read as a row's address reads:
that player's first controller of that kind (`devices.qualifiers_of`). "Player and node"
alone is not enough. Everything nobody has registered is player 1's, on purpose (plan 55), so
pointing "player 1" at a node would point the APC, the pad and the hands at once. The owner's
own words are per controller ("one controller points at one patch at a time"), and NQ7's chip
is per controller. A kind names no device, so the same file still works on another pad.

**The rows are not saved. They can all be derived [V].** `nodemode.fill(params, freedoms,
rows, qualifier, busy)` is pure:
- `params`: the node's (`ui_graph.node_params`), filtered by `nodemode.fillable`: continuous,
  no alias, no meta param (`meta_refusal`, row 743). A pad's, also modulatable.
- `freedoms`: the controller's, in its order. `gamepad.degrees_of_freedom(model)` for a pad,
  where a pair is one. N1 adds the desk's as a profile fact.
- `rows`: the patch's own. A mapping on the node's params stays, whoever's it is, and takes
  its freedom if it is this controller's. The rest fill what is left.
- What no freedom is left for is `Fit.over`, listed by `Fit.too_many`. No paging.

Saving rows would be wrong as well as redundant: a row says a controller's shape, and the
file names no device. On the same file a Joy-Con fills 10 degrees of freedom and an Xbox pad
17 (`tests/test_nodemode.py::test_one_file_fills_what_each_controller_has`).

**How the corpus fits [V].** Fillable params per node, over all 25 corpus presets, by
`params_of`'s prefix. `dream.*` was not split between a look-back and a dream here:

| Node | Fillable params |
| --- | --- |
| look-back, dream | 18 (an upper bound, see above) |
| envelope, pattern | 8 |
| fractals, zoomblur, glimmer | 7 |
| plasma, huecycle, acid | 6 |
| wobble, warp, doublevision, kaleido | 5 |
| deconverge, tripcolour | 4 |
| LFO | 3 |
| macro, hands | 1 |
| shape, scene, output, composite | 0: cannot be entered |

Of 38 nodes, 2 exceed 16 and none exceeds 24. Xbox: 17 degrees of freedom, 11 of them axes and
pairs; Edge 20; a Joy-Con 10. So "too many params" will be rare on the APC (16 knobs plus 8
faders [I, N1 sets it]) and real on a Joy-Con.

**The rest of the rule.** `enter_refusal`: a node must be selected, a node with no params
cannot be entered, and one with only meta params says so. A node the file names and the graph
lacks is said and left out at load; a node removed on GRAPH lets go at once
(`settle_groups`, as groups do). Choosing another node just switches, one undo step, the dot
lit. A cable naming a player on another `Deck` is dormant: nothing in the file changes,
N1b reads `MetaController.deck_of_player`.

**The cable.** `graphview.NODE_MODE`, a kind; `graphview.node_mode_cable`, labelled "node
mode: player 2, LX → Mix"; `ui_graph.KIND_COLOURS` holds its green, which `_cable` reads. No
view holds one yet: N1b draws them, gives them their own bundle, guards `_cable_menu`, and
adds them to `graphview.key`. Until then no UI writes the key, so nothing saved goes undrawn
unless a file is edited by hand. `ui_graph.DELETE` does not hold the kind, so ⌫ refuses it.

**What N1 and N2 still owe the data:** whether a pad's fill counts an axis a saved route on
another node reads as `busy` (NQ6's recommendation says yes; the owner's words cover the
node's own params only), and D5c's "copy on air to off air", which must carry
`Presets.node_mode`. D5c was not open when this was written: its builder should check.

## 3. What the lane carries

| Item | Saved where | What the move is | Bump? | Owner? |
| --- | --- | --- | --- | --- |
| **NM0** | preset | one optional key | **no**: absent means nothing points | one word (`controller`, row 715) |
| **NSEW** (row 545) | `bindings.json`, 11 lines of `bindings.default.json`; a preset only through a `pair:` route | `pad:A/B/X/Y` and `hat:UP/…` become N/S/E/W; old and new words do not overlap, so a word map is unambiguous | **`bindings/4`**, and preset `/11` for `pair:` | names; rows 546, 552 |
| **Layout stamp** (rows 723, 724) | `bindings.json` | `PAD_LAYOUTS` reads a stamp instead of recognising an exact row, so a hand-written twin of an old row stays | with `bindings/4` | no: [Rec] do it |
| **`band.*` ids** | a show's `session` and `modules`, `patches/band/`, `scenes/band`, `lane:` addresses, `group:band` layout keys, desk rows | the ids | not a preset's since row 743 | [Rec] **stays** |
| **`presets/` and `hyperspace.preset/…`** | every preset, the folder, the Drive | the word | **`/11`** and a folder move | **yes**: §4 |
| **Shows go; the meta controller file** | `projects/*.hyp.json`, `last_show` | a new file kind, the tuning moved | its own `/1`; the preset does not move | **yes**: §5 |

**NSEW is smaller in presets than the prompt assumed [V].** A load drops a discrete `pad:` or
`hat:` row from `routes` (not a performer row), `patches.check` refuses them, a desk row is
MIDI, and the corpus holds none. Only a `pair:` route (plan 56, merged today) names a pole in a
preset. **So NSEW is mostly `bindings.json`,** which is each Mac's own and has its own road:
read through on load, kept as `.bak-v<schema>-<stamp>` (`routing`). That needs no run on the
second Mac. The Drive library's count of `pair:` rows was not read, as instructed.

**`band.*` [Rec: stays].** Row 738 listed where it is saved, and it is everywhere the meta
controller keeps anything. The seventh round says "'Band' is right for one bin: EQ uses the
word", and `band.0.atk` is one band's attack. AZ fixed what a person reads. If it must go, it
goes when the tuning moves to its new file (§5), and no preset is touched.

## 4. Patch words in the files: what must be decided

The word is the owner's and settled for text. In files, three things collide [V]:
- **`patches.shape_of` tells a whole patch from a fragment by the schema's kind.** With one
  kind it must read something else. The owner's definition gives it: a loadable patch has no
  wires coming out, so no boundary. That is a change to `shape_of`, `check` and `patches.py`'s
  reading, not a rename.
- **`<library>/patches/` already holds fragments and `patches/<group>/`.** Preset folders
  (plan 48) are free names, so a folder called `dream` would land in a group's folder. So the
  loadable ones need their own root or a reserved name.
- **`presets` is a path in 109 lines of `hyperspace` and `tools`, and `hyperspace.preset/` is
  in 28 files of code, tools and tests.** It is also the Drive folder both Macs sync, so the move happens with both
  closed, and the bank's names, which are slugs, survive only if the slugs do.

**[Rec]** `hyperspace.patch` is at `/2` and the preset at `/10`, so one kind would mean merging
two ladders. Keep one kind per ladder: **`hyperspace.loadable/11`**, the old ladder read
through, in **`<library>/loadable/`**. It names what it is, collides with nothing, and `shape_of`
needs only one more word. The lighter option is to leave both as they are and let the glossary
say so, which its own rule allows ("if a saved name cannot change cheaply, it stays"). That
costs nothing and leaves the word `presets` in the Drive.

## 5. Shows going: what must be decided

The eighth round: "Shows and sessions go. Tuning moves to one meta controller file per
install, with the bank beside it. **Open:** where the bank belongs." `hyperspace.project/3` is
today `session` (the tuning), `modules` (the session groups' labels), `bank`, `startup` and
`layout` (the rig's nodes). Each needs a home, and:
- **Per install, on which disk?** The tuning is per room, and the Drive is shared. **[Rec]**
  `<library>/installs/<name>.json`, this Mac's choice in `<home>/last_install` as `last_show`
  is today.
- **The bank.** [Rec] In that file, as "beside it" reads. The pads are how a performance is
  laid out, not how a look is.
- **`startup`.** Set by nothing on the panel since 2026-10-28. [Rec] goes with the bank, or
  goes.
- **Several shows into one file.** The library holds more than one. [Rec] each becomes an
  install, and the owner deletes what he does not want. Merging by machine would guess.
- **#223 venues and `config.toml.rig`,** Dillon's and "probably" going. Ask him at the same time.

**Size:** L. `Project`, `MetaMarks`, the bank's callers, `last_show` and the shows tests all
move. It is the largest item here by far and shares no code with the others. **[Rec]** it
shares the run and the backup, not the bump: a new file kind starts at `/1`, and no preset
changes for it. If it would delay the show, it is the one item that can run as a second
migration, since it touches nothing the first writes. The owner said one; that is his call.

## 6. Questions for the owner

| | Question | Rec |
| --- | --- | --- |
| FQ1 | NM0 now as an optional key, no bump? An older build ignores the key on load, says nothing, and **drops it on its next save** [V]; both Macs on one build makes that moot (row 394) | **Yes** |
| FQ2 | The `controller` word in the saved form | **Yes**: player alone points everything player 1 holds |
| FQ3 | `band.*` ids | **Stay** |
| FQ4 | `presets/` and the schema in patch words | `hyperspace.loadable/11`, `loadable/`; or leave them and let the glossary say so |
| FQ5 | Shows: where the install file lives, the bank, `startup`, many shows | §5 |
| FQ6 | Is shows' move inside the one run, or may it be a second? | Inside if ready; a second rather than miss the show |
| FQ7 | NSEW's spellings (`pad:N`, `hat:N`, `pair:N/S`) and rows 546, 552 | Those spellings; 546, 552 per Q3 |

## 7. `/11`, if the owner says go

- Preset: `pair:` route poles in N/S/E/W (`graphmigrate.eleven`), and the kind and folder if
  FQ4 says so. `node_mode` is already legal and is simply part of the description. If FQ4
  says leave it, `/11` is only the pole words, and is still a bump: row 394's "saves in
  today's words" means a reader must know the old ones.
- `bindings/4`: the words, the stamp.
- `hyperspace.patch`: unmoved. Group and fragment patches name no pad button.
- A new file kind `/1`, if FQ5 is ready.

**The run, in this order, because of what reads what:**
1. Both Macs closed. One backup (`library-backup-<stamp>`, the tool's).
2. Retaper, a no-op after the first (`retaper_plan`).
3. Presets to `/11` by `headless.resave`, with the tool's three checks: it loads, a fixed point,
   the same picture. **Shows still exist here:** `rig_show`'s old eye, looks and cuts read them
   for any file not yet `/10`.
4. Shows to the install file, last of the file rewrites.
5. The folder move, last of all: a rename, so a failure before it leaves today's paths.
6. Each Mac's `bindings.json` moves at its own next launch, by the road it already has.
7. The corpus: `--to tests/corpus/presets`, then fixtures with `git add -f`. Goldens must not move.

**Before the show, after:** #365 (NSEW builds on it), SEM (code words first, so the lane writes
each file word once), N1 and N2 are free of it. Once `/11` lands, the older Mac refuses every
file. Row 521, closed by 576, and row 394 both say so and both accept it.

## 8. Not verified

The Drive library was not opened, as instructed: its counts of `pair:` rows, of folders that
would collide, and of shows are unknown, and the migration's dry run gives them. Whether
`copy on air to off air` carries the key waits for D5c. The desk's freedom count waits for N1.
Nothing here was hand-checked: the key has no UI until N1b.
