# Plan 85: the hands' show look, BONES, PLAIN, 50%

Written 2026-11-22. One item of the post-install wave ([`66-post-install.md`](66-post-install.md) on branch `plans/66-post-install`, §1 row 85, launched as 72 and renumbered by [`66-launch.md`](66-launch.md)). Register rows 1050–1053, hand checks 850–852, group FF. Built on PR #459's branch, `worktree-ghost-bones-default`, with `main` merged in.

## The ask

The owner changed the ghost hands' show look on 2026-11-18: on, BONES style, PLAIN material, opacity 0.5. PR #459 had set it on 2026-11-15 as BONES in GLASS at 0.35, in the code and, by hand, in the Drive library.

## What is built

1. **The code default** (row 1050). `ghost.SHOW_LOOK` is now `{"on": True, "alpha": 0.5, "style": BONES, "material": PLAIN}`. #459's wiring stays: `app.main` applies it to the on-air renderer's hands at startup and gives deck 2's sibling one, and `GraphSection.land` starts every extra hands node's state from it. So a fresh patch, and **New patch**, carry the look. `GhostState()` keeps its neutral defaults (off, HANDS, PLAIN, 60%): the ghost and render tests measure that draw, and the goldens draw the corpus with it.
2. **`tools/set_hands_look.py`** (rows 1051–1052), for the owner to run once on the library:
   - walks `loadable/` and `presets/` every folder down, so the era folders are covered (`migrate_library.loadable_files`);
   - loads each patch in the app, headless, and leaves (and names) any file that isn't a loadable patch or doesn't load;
   - sets `ghost.*` and each extra hands node's `ghost.<n>.*` `on`, `alpha`, `style` and `material`; nothing else;
   - gives a hands layer that reaches no output the standard wires (`hands → hands.layer.hands`, `hands.layer → output.all.hands`, `hands.layer → output.all.guide`), each only where missing, as the 2026-11-15 run did;
   - loads each changed patch again from what it would write and doesn't write one whose load notes change;
   - is a dry run by default; `--apply` refuses while the app is open on this Mac, backs the whole library up to `<home>/library-backup-<stamp>/` first, then writes atomically in the app's own layout. A second run finds nothing to do.
3. **The corpus stays neutral** (row 1053): the tool is tested on tmp copies, so no golden frame moves.

## The command (the owner, on one Mac, after this merges)

```bash
cd hyperspace-python
uv run python tools/set_hands_look.py "/Users/dallman/My Drive/Hyperspace/loadable"
uv run python tools/set_hands_look.py "/Users/dallman/My Drive/Hyperspace/loadable" --apply
```

The folder may be the library or its `loadable/` folder; with none, the library is `config.toml`'s `[library] path`. The backup goes in the machine home (`~/Hyperspace`), never inside the library.

## Goldens

None should move, though one would have without a fix:

- `GhostState()`'s defaults are unchanged and the corpus isn't rewritten, so every corpus golden draws the hands as before.
- **`hands-glass-only`** (a fixture) has a second hands node and sets no `ghost.2.*` values. Since #459, an extra hands node's state starts from the show look, so that node would draw BONES at 50% instead of HANDS at 60%. #459 alone would have moved this golden too, with GLASS at 35%. The golden rig already forces `ghost.<n>.on` on, standing in for the meta controller. It now also sets that node's `alpha`, `style` and `material` to `GhostState()`'s values wherever the file sets none (`tools/golden_frames.py`, outside this plan's files; a minimal change). Checked on Mesa: the rig's `ghost.2.*` read 0.6, HANDS, PLAIN, as on `main`.

## Owner answers

Rows 1051–1053 accepted as built by the owner on 2026-11-23.

## Not done

- The tool was never run on a real library (the brief).
- No hand check was done: they need the rig.
