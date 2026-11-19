# Cloud agent prompt: plan 65, effect previews and the effect picker

Paste everything below the line into a new Claude Code cloud session on the
`hyperspace` repo.

---

You are building plan 65 of Hyperspace, a live-visuals app (Python + moderngl,
in `hyperspace-python/`). Build it as one draft PR to `main`. The owner reviews
and merges; you never merge.

## Why

There are 26 shader effects in `hyperspace/shaders/fx/`, and adding one means
walking a nested right-click menu on GRAPH (the owner calls it "Context Menu
Tree Hell"). Many names no longer say what the effect does. The owner and
Dillon want to *see* each effect before picking it. The effects will soon be
reorganized into families by a separate shader roundup, so nothing here may
hard-code today's list or grouping.

## Start from the test-card work

Branch `claude/lucid-maxwell-54j27i` (2026-11-14, no PR, level with `main`)
has two commits:
- **`shaders/fx/testcard.glsl`:** a generator that draws a grid, a circle and
  colour bars.
- **A "card" chip on each effect node's thumbnail on GRAPH:** lit, the
  thumbnail shows the test card through that one effect. The test is
  `tests/test_thumb_card.py`; see also `render.py`, `ui_graph.py` and the
  `DISTORTION.md` note.

Branch `plan-65-effect-previews` from it and keep its commits.

## The work, in order

1. **Preview renders.** A preview cache that renders each effect over the
   test card, off the frame's critical path:
   - a few per frame at most, made lazily;
   - a **still** at the effect's default values;
   - a **short loop** (about 2 s at its default speed, a small number of
     frames) rendered once and cached;
   - invalidated when the effect's file changes (hot reload,
     `docs/ENGINEERING.md` §15).

   Size it so all 26 fit in memory comfortably, and say what that is.
2. **The effect picker.** A dialog that replaces the nested effect submenu in
   GRAPH's right-click "add effect" path:
   - a grid of tiles, each the effect's preview with its label;
   - hovering a tile plays its loop and shows its tip;
   - a search box that filters on label and tip;
   - groups read from data, not code. Use the effect files' existing metadata
     for now and leave a clear hook (one table or one `@` directive) for the
     coming families;
   - click to insert, the same result the menu gives today, wired or
     unwired as the menu does.

   It must work on a trackpad on stage: big tiles, big click targets, little
   text. Use the dkit menu and popup patterns already on main (#452, the
   `_menu_up` guard) so it swallows the canvas under it.
3. **Previews for unwired nodes.** Today a node whose picture reaches no
   output isn't made (`graph.py`: "unreached", drawn faint as "reaches
   nothing"; `run_of`), so its thumbnail can't show anything. That defeats a
   preview node. Find out why it's built that way, and write the reason into
   the plan doc. Then give unwired effect nodes a thumbnail:
   - the test card through the effect, or its real input if it has one;
   - at thumbnail size, inside a per-frame budget;
   - nothing reaches an output, and the outputs stay the same bytes.

   If that can't be done without breaking a rule in `ARCHITECTURE.md`, stop
   and write it up as a register row with options.
4. **Exported loops (stretch).** A tool, `tools/effect_previews.py`, that
   writes every effect's loop as a GIF and a still PNG, for docs and for a
   future skill.

## Read first

- `REVIEW.md` (repo root), `hyperspace-python/docs/CHECKPOINT.md`,
  `docs/DECISIONS.md`, `docs/ARCHITECTURE.md` §3–§4 and `docs/GLOSSARY.md`.
- `docs/plans/37-pictures-and-faces.md`: how GRAPH thumbnails are made today
  (192 texels, at the frame's end, only for nodes on screen, with GPU time on
  hover).
- `hyperspace/fx.py` (`parse`, `EffectSpec`, the `@label`, `@tip` and
  `@order` directives) and `docs/DISTORTION.md`.
- `.claude/skills/drive-the-app/SKILL.md` for driving the panel by control id
  and capturing it.

## Rules

- **Goldens must not move.** `tests/fixtures/` needs `git add -f`.
- The picker and the previews are view state, never saved, unless you find a
  reason; if so, stop and report.
- Never run anything against `~/Hyperspace` or a Google Drive path.
- Don't modify `.github/workflows/`.
- Report faithfully: failures with their output, a skipped step as skipped.

## Your numbers (use only these)

- Plan doc: `docs/plans/65-effect-previews.md`, plus a line in
  `docs/plans/README.md`.
- Decision register rows **892–901** in `docs/DECISION-REGISTER.md`.
- Hand checks **689–698**, group **EA**, in `docs/plans/11-hand-checks.md`:
  - picking an effect on a trackpad;
  - the loops' smoothness on the rig;
  - an unwired node's thumbnail;
  - hot reload of an effect file updating its tile.

## Testing

- Cloud setup: `.claude/hooks/session-start.sh` (or drive-the-app §0).
- `uv run pytest -q` from `hyperspace-python/` must be green.
- New tests:
  - the cache's budget per frame and its invalidation on file change;
  - the picker inserting the same graph as the old menu, using
    `tests/ui_driver.py`;
  - search filtering;
  - unwired thumbnails leaving the outputs' bytes unchanged.
- Capture the picker open, searched and hovered with drive-the-app. Commit
  the shots under `docs/plans/assets/65-effect-previews/` and link them in
  the PR body.

## PR

Open a **draft** PR from `plan-65-effect-previews` to `main` with
`gh pr create --draft`. Credit the test-card branch. Body headings:
- **Why**
- **What**
- **Testing** (counts verbatim)
- **Screens**
- **Restart or hot reload**
- **Owner decisions pending**

When you finish, reply with: the PR URL, the head commit, what's done and not
done, test counts, the rows and checks used, and the open questions.
