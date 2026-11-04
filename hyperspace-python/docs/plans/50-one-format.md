# Plan 50 — one saved format: patch, group and preset

**Status: built (2026-11-03)** as wave 2 F1 on `wave2/f1`, stacked on D3
(PR #351). Register rows 639–647, every one (rec) pending the owner; hand
checks 484–488, group BM. **Restart, not hot reload** (`patches`,
`library` and `graphmigrate` change shape). **Both Macs on this build,
between shows, and the library migrated once** (`tools/migrate_library.py
--apply`, a backup first): an older build refuses a `patch/2` and finds
no module presets where this one keeps them.

From the build order (`tier-2-3-build-order.md`, F1): *one format: patch =
group not yet saved = preset with no open pins, one loader, one conflict
sheet; module presets and desk templates retired as separate ideas*; and
DECISIONS "The preset contract (plan 43)", its last row: *a preset is then
a patch that fills the whole frame; a module preset is a patch of one
group (row 540)*. Inside it, the rest of harden-node-groups (split from
G0): *a group holds any node, checked at save*. Not here: P1 (frame kinds
in groups and patches: **built since**, [below](#p1-frame-kinds-in-patches-wave-3)),
P2 (replace the host's dream: **built since**, [below](#p2-replace-the-hosts-dream-wave-3)), P3 (wire-as-saved
take-over, row 524) — wave 3; Dillon's #314 and #287 rebase on this in
wave 4 (pad rows can ride in a patch: a patch's `desk` rows are any desk
control's, unchanged).

## The one shape

One document, read three ways (`patches.shape_of`):

| reading | what it is | schema | opening it |
|---|---|---|---|
| **preset** | a patch that fills the whole frame: no `ports` | `hyperspace.preset/10` | replaces every part; nothing to collide with, so no sheet (`Presets.load_doc`) |
| **patch** | a fragment of the canvas and its boundary (`ports`, rig rows) | `hyperspace.patch/2` | spawned into the open preset under fresh ids, one undo step, plan 40's conflict sheet (`Edit.spawn`) |
| **patch of one group** | one param group's values (`"group": "dream"`; the analyzer's also its band `layout`) — what a module preset was | `hyperspace.patch/2` | from its group's strip: a spawn that replaces that group's values (`patches.spawn` → `Landing.replaces`), no sheet |

A **group** is a patch not yet saved: its entry in the preset's `groups`
(members, the folded pins the boundary classifier draws) — unchanged
since plan 40 D4; the group node draws as it did and `build_graph` sees
the flat graph.

**The schema (row 639, (rec)): two names over the one shape, no `/11`.**
The name says what opening does — replace the frame or spawn into it —
and the library already routes by schema family; keeping the preset's
name moves no preset on either Mac, and a preset never writes `ports`.
`patch/2` is `/1` plus the optional `group` key. Every save writes the
newest; an older build refuses a `/2`.

## One reader, one loader, one sheet

- **One reader with per-version steps** (row 640): `graphmigrate.forward`
  is the preset's ladder (`seven`, `nine`, `ten`, the steps `load_doc` ran
  inline); `patches.forward` is every fragment's (`patch/1` → `/2`; a
  module preset `hyperspace.preset/1` → a patch of its group). The
  library reads every module group, every patch and the band scenes
  through it.
- **One loader, one sheet — as built** (row 641): the reader, the shape and
  the doors are one; the sheet is plan 40's and the only one (a load and a
  group patch have nothing to collide with). `Presets.load_doc`
  (replace, refused whole, byte-for-byte re-save) and `Edit.spawn` (merge
  under fresh ids) stay two landings. The literal "load = spawn into an
  empty frame" waited for frame kinds in patches (wave 3 P1), where a
  preset could be spawned into another; done now it would put the load's
  round trip at risk for no change a user sees. **A deviation from the
  ask, said** (P1 proved the graph half and kept the two landings: row 660,
  below).

## A group holds any node, checked at save

Row 642. `patches.groupable` (the canvas's rule: Group, a load's
`read_groups`, the drawing) holds any node the preset file saves — the
frame's singletons, the camera, a lane envelope too — and refuses only
the rig's render kinds (`patches.RIG_KINDS`, `graphview.RIG_KINDS` the
same list: a window, All outputs, a media channel, a cloud), a device,
the analyzer, the sequencer, a node the preset lacks and a group. `patches.select` (the
lift's rule) runs at **Save as patch** and refuses in words, the group
kept, nothing written: "group 1 not saved as a patch: scene is the
frame's; left out". Hands 1 is always held by a wired frame, so a delete
leaves it a member (row 647).

## Module presets and desk templates retired as separate ideas

Desk templates went with D3. A module preset is now a patch of one group
(rows 643–644): `<library>/patches/<group>/<slug>.json` with `"group"` —
the folder keeps a group's names its own and out of GRAPH's spawnable
list (`patches/*.json`, one level); the field is what a read checks —
anything else in a group's folder (a whole preset, a canvas patch,
another group's, an empty `group`) is refused, the mismatch named; only
an old module preset that never said its group takes the folder's.
Every strip (view, rot, camera, output, master, band, dream, tempo, lfo,
seq, env) lists, steps, loads, saves, resets, deletes and restores them
from the trash as before; no strip code changed (`Library.group_dir`
is the one place). The corpus's three dream presets are
`tests/corpus/patches/dream/*.json`, `patch/2`.

Not done (row 646): the **show's** `modules` key (a session group's band
preset by name) stays — renaming it is a show schema move;
`RETIRED_MODULES` and `_fresh_of` are already what the fallback needs;
the band scene files (code data) stay `preset/1`, read through the
ladder.

## The migration

Row 645. `tools/migrate_library.py`: dry run by default; `--apply`
backs the library up first, retapers, rewrites presets and shows as
before, then writes every module preset to `patches/<group>/` as
`patch/2` (its old file removed, the backup holds it) and every
`patch/1` as `/2` in place; `fx/` (retired) and an unreadable file are
left, said; `--to` moves none. Never run against the owner's library by
the PR. Goldens: expected unmoved (no preset, graph or shader changes).

## Tests

`tests/test_patches_one_format.py` (new): the ladder and the shape; a
group patch's spawn; the corpus in the shape; a corpus preset
round-tripping byte for byte; a module preset living and loading as a
patch of its group; an old module preset and an old `patch/1` opened end
to end; the tool's step on a scratch library, dry run and `--apply`.
`tests/test_graph_groups.py`: the scene grouped and refused at save
(`test_a_group_holds_the_scene_and_the_save_refuses_it_in_words`), the
one selector with two rules (`test_one_selector_two_rules_the_save_and_the_canvas`,
was `test_patches_select_is_the_one_rule_for_lift_and_group`), the
corpus property test with hands 1 a member. Plan 40's spawn tests run
unchanged on the `patch/1` fixture (read as its `/2`). The library,
analyzer, undo, camera, preset-folder and shared-library tests that wrote
module presets into `<home>/<group>/` write them into
`<home>/patches/<group>/`.

## P1: frame kinds in patches (wave 3)

**Status: built (2026-11-03)**, register rows 657–660, every one (rec)
pending the owner; hand checks 497–499, group BP. **Hot reload is enough**;
no schema moves, **no `patch/3`** (row 657), no migration: `patch/2` as it
was, an older build refusing a file with a frame kind in words.

What changed in the build:

- **What a save refuses.** `patches.select` (**Save as patch**, `lift`,
  `check`) now holds the scene, the shape, the backdrop, the pattern, a
  look-back, the dream, hands 1, its layer and its guide. It refuses the
  rig's kinds (`RIG_KINDS`, unchanged), the look's one camera, a lane
  envelope, a copy without its original and, new, a second dream and a
  hands' layer or guide without its hands. Only the save refuses a layer
  alone: a file an older build saved with one still reads and spawns as it
  did (files on disk are a format). The words at the save above ("scene is the frame's")
  are gone; `groupable` is unchanged.
- **A spawn into a host that has one** (row 658). `patches.ONE_PER_FRAME`
  keep their names (`scene.2` is no node; a wire to `dream.2` is refused,
  one live dream). One the host already has goes in `Landing.taken`, and
  `Landing.refusal` refuses the whole spawn in words, before any sheet and
  in `Edit._spawn_refusal` (what only the output hold keeps says to drop the
  hold, `Landing.held_taken`). The dream's is P2's sheet row since, below. Hands 1 lands as the next hands, a look-back as the
  next look-back.
- **Whose params** (row 659). `patches._param_rows` replaces the one-prefix
  rule, the canvas's owners held equal by a test: the shape's `rot.*` and
  `view.*`, the pattern's `view.pattern*`, the look-back's `LOOKBACK_KEYS`
  and the dream the rest of `dream.*` — a dream patch never sets the host's
  look-back. A member that keeps its name keeps its ids. The canvas drew the
  dream's params on the look-back until P2.
- **Fixes the kinds needed.** `read` keeps the order of the wires into
  `scene.geometry` (the draw order) and orders ports by number; an inlet into
  it says where it drew (a port's optional `before`), **wire as saved**
  honours it, and that port stays open beside its other wires;
  `graphview._node_name` names
  `lookback.2` and `dream.2` (it said `lookback` and `dream`) and `_land`
  keeps `lookback.2`'s entry when a wire names it, the entry being what
  declares it (`graph.entry_declares`). `LOOKBACK_KEYS` moved to `lookback.py`,
  where `params` and `patches` both read it.
- **The empty frame** (row 660). Every corpus preset lifted whole and spawned
  into an empty frame, its pins wired as saved, is the section again, hands one
  number on. `Presets.load_doc` is **not** rewritten as a spawn, and a preset
  file is not spawned directly. A new preset holds the scene chain, so it is
  not an empty frame.
- **The "not done" list above (row 646) is unchanged**: none of it waited
  on frame kinds.

Tests: `tests/test_patches_frame_kinds.py` (new); the tests that named the
scene as the refused thing now name what still is.

## P2: replace the host's dream (wave 3)

**Status: built (2026-11-03)**, register rows 661–664, every one (rec) pending
the owner; hand checks 500–502, group BQ. **Hot reload is enough**; no schema
moves, no param renamed, stacked on P1.

What changed in the build:

- **The sheet's row** (row 661). `patches.REPLACEABLE` is `("dream",)`;
  `Landing.replacing` is what of `taken` it may replace, and `Landing.refusal`
  no longer counts it. `ui_graph.spawn` puts up the sheet for it, with or without
  a control in question, and `ui_routing._sheet` draws the row, what the host's
  loses and what stays (`Landing.loses`, `keeps`, from `Edit.replace_said`, the leaf having no registry)
  and **Replace and spawn**. The answer travels in `choices` under
  `patches.replace_key`, and `Edit.spawn` refuses a replace nobody answered. No
  two-way row: Cancel is what keeps the preset's. The conflict sheet lives in
  `ui_routing.py`, not `ui_graph.py`.
- **What goes and stays** (row 662). `graphview._take_out`, now shared with
  `render_drop`, takes the entry and the wires; D2 stands, so the new dream's
  pins are open; values are the patch's over fresh, by what the node owns; a
  macro's base subscribers on them let go, since one would overwrite them at the
  next re-landing; routes, desk rows and depth subscribers stay; a host group lets
  the node and its open pins go. A sheet whose preset changed under it refuses
  (`Landing.asked`, `SPAWN_STALE`): the modal stops the panel, not a bank press.
- **The door.** Adding a kind to `REPLACEABLE` is the whole of the sheet's
  change; which kind should go next is the owner's.
- **Whose params** (row 663). `patches.dream_owner`, over `lookback.is_lookback_key`,
  is asked by `graphview.OWNERS["dream"]` and `ui_graph.node_params`, and is the
  split `patches._param_rows` already had. `ui_lookback.py` needed no change: `SECTIONS` was already the
  split, now tested to be.
- **The edges** (row 664). A splice onto the replaced dream's own cable is refused,
  and the drag's hover does not light it;
  the dream buffer is not cleared (`render.py` untouched).

Tests: `tests/test_patches_replace_dream.py` (new); P1's tests that named the
dream as refused now name the shape, and the registry-wide owners test lost its
exception for the dream.

## P3: wire-as-saved take-over (wave 3)

**Status: built (2026-11-04)**. The owner answered row 524: "yes, the take-over
chip". Details are rows 665–667, (rec) pending the owner; hand checks 503–505,
group BR. **Hot reload is enough**; no schema moves, stacked on P2.

What changed in the build:

- **The second chip** (rows 524, 665). `ui_graph._take_over_chip` under **wire as
  saved**, drawn only while `Edit.take_over_of` has a plan. Its label names each cut
  on a line of its own, breaking after the arrow and then ending in an ellipsis to fit
  `SIDE_MIN`, in the canvas's names (`label_of`); past three it says the count; the
  hover lists every cut, wire and refusal. `Edit.wire_taking_over` lands every pin
  the plain chip would and each taken outlet, one undo step, then "cut huecycle → All
  outputs" on the head. The plan is cached by the section's identity, so a frame pays
  for no trial read.
- **The plain chip never cuts.** `Edit.wire_as_saved` and the new press share
  `Edit._saved_pins`; only `take_over=True` cuts. Two bugs on its path were fixed at
  the review's word (row 665): an outlet's pin is per port (`open_ports`), and a free
  All outputs takes a wire (`ALWAYS_KINDS`).
- **What is not taken** (row 666). A taken inlet is no open pin; `scene.geometry` has
  nothing to cut and keeps its `before`; another refusal stays refused; the rig's bus
  cable is not a preset wire; a cut the read refuses draws no chip.
- **WYSIWYG.** The cut's source stays on the canvas (`_keep_declared`), not re-wired.
- **Staleness** (row 667). The chip's plan is taken at the mouse-down and the press
  compares it, section by identity, or refuses in `TAKE_OVER_STALE`, nothing cut. A
  release where the chip was, once it is no longer drawn, says the same.

Tests: `tests/test_wire_take_over.py` (new). `tests/test_graph_groups.py`'s plain
chip tests pass untouched.

## Review fixes (PR #352)

1. A group refuses the rig's media channel too: `patches.RIG_KINDS`
   (window, All outputs, channel, cloud) is the one list, and
   `graphview.RIG_KINDS` is it.
2. `headless.SHARED_FOLDERS` is `("patches",)`, every folder down, so a
   headless resave sees the module groups' patches where the migration
   put them.
3. A strip load lands a group patch's values directly; "a module load is
   a spawn" stays the docs' story, not the hot path.
4. The migration's file list is `retaper_routes.json_files`.
5. An unreadable `patches/*.json` is said by the migration.
6. An empty or non-text `group` is a group patch's key that names
   nothing: `shape_of` reads it as a group patch, `check` refuses it in
   one line.
7. `Library.read` refuses anything in a group's folder that is no patch
   of that group, the mismatch named.
8. `library.migrate_doc` serves the shows alone; the preset entry and
   `PRESET_SCHEMA` are gone.
9. The corpus layout is one table, `library.group_folder`, used by
   conftest's `seed` and `tools/desk_coverage.py`.
