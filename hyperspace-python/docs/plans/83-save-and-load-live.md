# Plan 83: save and load live

Built 2026-11-22 from plan 66's post-install wave ([`66-post-install.md`](66-post-install.md) on branch
`plans/66-post-install`, renumbered from 70 by [`66-launch.md`](66-launch.md)). Register rows 1030–1035, hand
checks 830–835, group FD. No file format changes: no new saved key, no new param.

## The two pains

1. **Saving took three or four clicks**, and the meta controller could load a patch (GRAPH's **load…**) but
   not save one.
2. **The playlist did not scroll**: its popup grew with its entries and ran off the bottom of the screen.

## What was built

### Save as (rows 1030–1033)

- A **save as** chip on GRAPH's deck row, right of **load…** (`ui_loadable.save_as_chip`, drawn from
  `ui_graph._deck_row`).
- One press fires `preset.save_new` on the deck the panel is on. That is the param START held on a pad already
  presses (`Install.save_new`), so the chip and the pad do one thing:
  - the name grows from the loaded patch's (moo → moo 2, then moo 3);
  - it lands in the loaded patch's folder (`4-install-nov/distort/moo 2`), or at the top with nothing loaded,
    as `PATCH <n>`;
  - it never writes over a file (the name is free among every file stem, listed name and pad);
  - the new patch becomes the loaded one, so a second press counts on;
  - it takes the next empty pad (row 1031, pending).
- For 4 s the chip reads "saved moo 2", lit red; the full name is on its hover and on the footer.
- The chip's right-click is `preset.save_new`'s menu, so **Learn** puts the same press on a desk or pad button.
  No new param was needed: `preset.save_new` was already learnable and never a patch's row (row 752).

### The playlist scrolls (rows 1034–1035)

- The entries are a child list of their own (`ui_playlist._entries`), as tall as the screen leaves under the
  popup and never under three rows. The add list sits under it, always in view.
- Each entry is one row, 34 px tall (`ROW_H`): ▸ and its place and name (elided, the full name on hover), its
  dwell field and a square ×. They used to be two lines per entry with chip-sized targets.
- The entry on air is scrolled to the list's middle when the popup opens and each time it changes. Between
  those moments, a hand's scroll stays where it was put.

## Files

`ui_loadable.py` and `ui_playlist.py` are this plan's. **`ui_graph.py` is not**: it got four lines in
`_deck_row` (the chip beside **load…**) and an import, because the deck row is drawn there. `deck.py` and
`playlist.py` were not changed: the save is the bank's (`library.Install.save_new`, unchanged) and the
playlist's model needed nothing.

## Tests

`tests/test_save_live.py`, driven with `tests/ui_driver.py`:

- one click saves a new file in the loaded patch's era folder, and it loads back equal (the registry's patch
  part);
- a second press never overwrites;
- with nothing loaded, the save lands at the top;
- the chip shows the name, then "save as" again;
- 40 entries: the popup ends on screen, the row on air is inside the list at 0, 31 and 39, the rows are `ROW_H`
  tall, the wheel scrolls the list, a new entry on air is scrolled to once, and a click far down lands on its
  row.

## Goldens

None can move. Golden frames render the outputs, and this changes only the control window's panel.
