# Plan 48 — preset folders, stage 1

Wave 1 item L1 of the post-show plan (2026-11-02). Register rows 584–588,
hand checks 440–443 (group BC).

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
  popup, marked old, restorable, never written to, never emptied by the
  app, with one dim line saying so. Clear it in Finder.
- **The PRESETS page** draws a folder's preset as `party / TRIP`, the
  folder dim, the name bright; a top-level preset is drawn as before.
  The flat list stays (plan 41). A folder emptied by × or a rename is
  left on disk.
- **The watcher** (`Library._scan`, the hot reload's library poll) walks
  the same folders, so an edit to `presets/party/trip.json` re-applies
  it like any other.

## What stage 2 might do

Not built, not promised: moving a preset between folders from the page
(drag a row onto a folder header, or a "move to ▸" on the row); making,
renaming and removing a folder from the page; the list grouped under a
folding header per folder; the bank's slot menu offering folders. The
stage 1 names (`folder/leaf`) are what stage 2 would move, so nothing in
the format changes.

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
- **588** — the PRESETS page's reading of folders.

## Not done here

`tools/move_library.py` and `tools/migrate_library.py` still read
`presets/*.json` only. Both have already run on the owner's library;
a folder made after that is not moved or migrated by them. Their walk can
follow when a stage 2 or a new schema needs it.
