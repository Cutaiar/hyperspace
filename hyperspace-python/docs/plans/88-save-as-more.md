# Plan 88: save as ▾ — by name and to a place

Built 2026-11-23 on top of plan 83's **save as** ([`83-save-and-load-live.md`](83-save-and-load-live.md)).
Register rows 1075–1080, hand checks 868–872, group FI. No file format change, no new param.

## The ask

**save as** on the meta controller's deck row saves in one press with a name it picks (moo → moo 2). That stays.
Two more ways to save, behind a dropdown arrow joined to it:

- **save as name…**: type the name;
- **save to location…**: the file picker, a name and a place, opening on the Google Drive library's loadable
  patches folder.

## What was built

- **The ▾** (`ui_loadable._more`, row 1075): a small chip joined to **save as**'s right, lit while its menu or
  the save dialog is up. Its menu holds the two items. The chip itself is as plan 83 left it: one press is
  `preset.save_new`, its right-click is that param's menu (Learn).
- **save as name…** (row 1076): the chip's place on the deck row becomes the name field the strips' **as…** use
  (`_name_field`, 200 px here, with **ok** and **×**; Enter and Esc). It holds the name one press would give
  (`Install.next_save_name`), selected. The name is saved in the loaded patch's folder.
- **save to location…** (rows 1078–1080): **load…**'s dialog (`ui_browse`) in save mode (`open_save`):
  ImFileDialog's `save`, else the native `pfd.save_file` with the one-press name typed in. It opens on the
  loaded patch's folder, else the library's patches folder (`start_dir`). On the owner's Mac the library is
  `~/My Drive/Hyperspace` by `config.toml`, so that is Google Drive's `loadable/`; no Drive path is in the code.
  The folder picked is the patch's folder, the file name its name (`save_name`).
- **One save under both** (`library.Install.save_named`): `save_new` under a given name — the new patch
  becomes the loaded one, takes the next empty pad, the show is written, a new folder is made. It never writes
  over a file (row 1077): a taken name (file stem, listed name or pad, folded as the library folds) or one that
  names no file is refused on the footer, and the name field stays open.
- **Only inside the library** (row 1079): a place outside the patches folder is refused in words. A patch there
  would be found by no load, pad or list.

## Review fixes (Devin, on the PR)

- A library not yet moved (`presets/` only): a new name is written in `presets/`, by `group_dir`, never in a new
  `loadable/` that would hide every patch already there. This was true of every new-name save before this plan
  too (one press, the strips' **as…**). Its folders stay no part of a name there (review of #444).
- `save_named` also asks the disk (`Install._on_disk`): on a Mac's case-folding disk `moo.JSON`, which the
  list does not see, is the file `moo.json` would be. The dialog refuses a picked file that is already there.
- A `/` typed in the name field is part of the name (`harmless`: `AC/DC` → `AC - DC`), never a folder.

## Files

`library.py` (`Install.save_named`, `next_save_name`; `_save_new` takes a name), `ui_loadable.py` (the ▾, the
field, `save_named`), `ui_browse.py` (the dialog's save mode), `ui_graph.py` (one line: the deck row wraps for
`save_as_w`).

## Tests

`tests/test_save_live.py`, plan 88's part: the ▾ and its items by the mouse; a typed name in the loaded patch's
folder, loaded back equal, on a pad; a taken name refused with the field open; the dialog's place mapped to a
name, a new folder, a place outside the library and a file already there refused; the native dialog asked on the
loaded patch's folder and its answer saved; one press beside the ▾ unchanged.

## Not seen

ImFileDialog's save mode (no GL dialog headless; the native stand-in is what the test drives), and the native
dialog's "Replace?" on the Mac: hand checks 871 and 872.

## Goldens

None can move: only the control window's panel changed.
