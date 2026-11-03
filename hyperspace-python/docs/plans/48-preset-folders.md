# Plan 48 — preset folders, stages 1 and 2

Wave 1 item L1 of the post-show plan (2026-11-02). Register rows 584–588,
hand checks 440–443 (group BC). Stage 2 is wave 2 item L2 (2026-11-03),
**built**: register rows 636–638, hand checks 481–483 (group BL).

## The ask

After the 2026-10-30 show the library held some sixty presets in one flat
list, on two Macs, through one Drive folder. The owner wants to sort them
into folders in Finder (`presets/party/`, `presets/ambient/`) and have
the app follow. Folders were on the "decided not to build" list ("Preset
folders. Hide and trash instead."); one tier (plan 41) removed hiding, so
that row is overturned here.

The second half of the ask came from the same triage: the trash lived in
the library, so a × on one Mac filled the other Mac's Drive with copies.
The trash is a machine thing.

## What stage 1 does

- **The library lists every folder down.** `Library._files("presets")`
  walks `presets/**/*.json`, less hidden folders (`.cache`, a cloud
  client's own) and never through a link to a folder. The library's own
  folders (`projects/`, `trash/`, `patches/`, `desk/`, the module groups)
  are siblings of `presets/`, so they never were presets and are not now.
- **A name is folder-qualified.** `presets/party/trip.json` whose own
  `name` is `TRIP` is listed as `party/TRIP`; a top-level file's name is
  bare, as before. The file keeps the leaf; the folder is the path. A
  name also resolves by its file key, `party/trip` (`path_slug`: the
  folder as it is on disk, the leaf through `slug`). `slug` itself stays
  flat — shows, module presets and patches have no folders, and a `/` in
  their names is still a `-`. `path_slug` refuses a segment that is
  empty, `.`, `..` or hidden, and so an absolute path: a name never
  reaches outside `presets/`. Two files of one folder with the same
  inner name (a conflict copy) keep plan 25's rule, per folder.
- **A `/` in a listed name always means a folder.** A top-level file
  whose own `name` holds one (`AC/DC`, from before folders) is listed as
  `AC - DC` (`library.harmless`); a save writes that back. Names compare
  by one fold (`library.fold`: folder segments stripped and lowered, the
  leaf slugged), so `Party/Trip` finds `presets/party/trip.json` as APFS
  would, and a name whose folder is not on disk falls back to its `slug`
  among the top-level files (an old show's `Ac/Dc`) — on a read only:
  a save, a delete or a rename never takes that road. The walk is kept
  until a folder's mtime moves, the library writes or one second passes
  (`Library._walked`, `WALK_TTL`).
- **The bank names a preset by that name.** A slot holds `party/TRIP`; a
  bare name is a top-level file, so every show written before reads as
  it did. `cycle`, `walk`, `home`, `load_startup`, `still_named`, the
  `preset.*` triggers and a rename's repoint all go through `path_of`.
- **Saves land where the preset came from.** A save writes back to the
  file the name resolves to. **as…** with a folder in the name writes
  into that folder (made if need be). The two-handed save (SAVE + a
  pad), `preset.save_new` and the hold on an empty pad name the new
  preset from the loaded one and put it **beside** it — in its folder,
  at the top for a top-level one or none loaded. ⇧F on an empty slot
  (`PRESET <n>`) is at the top: it is not grown from the loaded one.
- **A rename keeps the folder.** The field is seeded with the leaf; a
  `/` in the new name is refused ("a rename keeps the folder").
- **The trash is this Mac's.** `to_trash` writes under
  `<machine>/trash/<origin>/`, `<origin>` the folder the file came from
  relative to the library (`presets/party`), the stamp-and-suffix names
  and the never-overwrite rule as before. A restore puts the file back
  into that folder. **Empty trash** empties this Mac's only. With no
  `[library] path` the machine home is the library and nothing moves.
- **The old library trash** (`<library>/trash/`, what every Mac wrote
  into before) is left where it is: listed at the end of the trash
  popup, marked old; a restore copies a file back and leaves it there; never written to, never emptied by the
  app, with one dim line saying so. Clear it in Finder.
- **The PRESETS page** draws a folder's preset as `party / TRIP`, the
  folder dim, the name bright; a top-level preset is drawn as before.
  The flat list stays (plan 41). A folder emptied by × or a rename is
  left on disk.
- **The watcher** (`Library._scan`, the hot reload's library poll) walks
  the same folders, so an edit to `presets/party/trip.json` re-applies
  it like any other.

## Stage 2 — built (wave 2 L2, 2026-11-03)

The stage 1 names (`folder/leaf`) are what stage 2 moves; nothing in the
file format changes, and no schema moves.

- **The tree** (row 636). `ui_presets.preset_list` draws the list as a
  tree: the top-level presets first, then a folding header per folder
  (`party  ·  12`), alphabetically, each holding its presets (in the
  list's order, drawn by their leaf) and then its own folders, indented.
  Every folder on disk is a header, empty ones too (`Library.folders`).
  A click folds a header; the fold is this Mac's — `presets.folded` in
  `<machine>/ui.json`, through `ui_pane`'s `read_doc` / `write_doc`, the
  pane's keys kept. Folded with the loaded preset inside, the header ends
  with its leaf. The PRESETS page and GRAPH's pane section are one
  drawing. The strip, rename, ×, the trash and the show line are as in
  stage 1.
- **Move** (row 637). A row's right-click: **move to ▸** — *top level*
  and every folder. A row dragged onto a header moves into that folder.
  `Library.move(name, folder)`: the file whole, its bytes and stem kept
  (`_move_file`: a hard link then an unlink, else an exclusive copy),
  never over a file; then, as `rename` does (`_follow_many` over
  `_repoint_by`), the loaded preset's name follows and every show in the
  home that names it is copied to the trash and rewritten, the open one
  through its `Project`. No undo step, as a rename has none.
- **Folders** (row 638). **new folder** at the list's foot makes one at
  the top; a header's right-click makes one inside, renames the folder
  (`Library.rename_folder`: one rename on disk, every preset keeps its
  leaf, the shows follow, the folds follow) or removes it
  (`Library.remove_folder`: empty only, a `.DS_Store` aside).
- **The tools** walk `presets/` every folder down as the library does
  (`library._walk`): `tools/move_library.py` copies `presets/party/…`,
  `tools/migrate_library.py` migrates it in place and names a preset by
  its path under `presets/` (`party/trip.json`, also for `--force`;
  `--to` keeps the folders).

Not done: the bank's slot menu offering folders (the pads are the desk's,
with no page UI, row 458's rule); the "grand cleanup pass" of the owner's
library (the owner's, some day).

## The file layout

```
<library>/presets/a.json                 listed "A"            (bare: top level)
<library>/presets/party/trip.json        listed "party/TRIP"
<library>/presets/party/deep/c.json      listed "party/deep/C"
<library>/presets/.cache/x.json          not listed (hidden folder)
<machine>/trash/presets/party/trip.20261102-221500.json
<library>/trash/…                        the old shared trash: listed, never emptied
```

## Decisions

- **584** — recursive listing; folder-qualified names; `path_slug` beside
  a flat `slug`.
- **585** — the bank by folder-qualified name; no `hyperspace.project`
  schema bump: an older build looks a slot's name up as a listed name,
  then as `slug(name)` — `party-trip` — and finds neither, so the slot is
  filled and loads nothing, with "no preset 'party/TRIP'" on the footer.
  Nothing is dropped, and the show is not rewritten by a load. Saving
  that show on the older build keeps the string as it was (the bank is
  written as held).
- **586** — the trash on the machine; the old library trash listed, not
  migrated.
- **587** — where a save, an as… and a two-handed save land.
- **588** — the PRESETS page's reading of folders (under stage 2's
  header a row is its leaf; row 636).
- **636** — the tree, the fold this Mac's (stage 2).
- **637** — move to ▸ and the drag; the shows follow as on a rename.
- **638** — making, renaming, removing a folder; the tools walk folders.

## Not done in stage 1

`tools/move_library.py` and `tools/migrate_library.py` read
`presets/*.json` only in stage 1; stage 2 made them walk every folder
down (row 638).
