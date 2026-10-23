# N3 — editing the modulation on the canvas (plan 28, stream N)

You are the implementer of work package **N3**. Read first, in full:
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md` (your rules and your
first three git commands: fetch `origin plan-28-30-integration`, `git reset --hard
FETCH_HEAD`, `git branch -m plan-28-n3-edit-modulation`; one plain git command per
shell call). Your base must be the SHA in your dispatch or later (N0, N1, N2 merged).

Then, in your worktree under `hyperspace-python/`:
- `docs/plans/28-30-orchestrator-prompt.md` lines 279–345 (stream N today), 346–533
  (N0, N1, N2 — built; what you edit on), **534–575 (your section N3)**, 576–628
  (N4, built in parallel on the same files `graphview.py` / `ui_graph.py`: N4 adds
  render-graph edits (`Edit.wire`/`unwire`/`add_node`, image cables dragged, a node
  picker for effects/hands/composite); you add modulation edits. Keep your `Edit`
  requests and your `begin_create`/`begin_delete` handling in functions N4 can add
  beside — one dispatch by port type (`value`/`trigger` → yours; `image`/`geometry`/
  `mask` → N4's) is the seam; name it in your report), 629–666 (N5, after you),
  673–763, 764–839, 840–900.
- `docs/plans/28-node-editor.md` §4.
- N0/N1/N2's decisions and reports in `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/`
  and `.../reports/` — especially N2's: the `View` model, port ids, how the page
  holds its editor context, the side column.
- `hyperspace/graphview.py`, `hyperspace/ui_graph.py`, `hyperspace/routing.py`
  (`Bindings.add`, `bind`, `move_route`, `remove`, `replace_owner`, `Owned`,
  `referee`, `Sub`, `Macro.subs`, `depth_subs`, `modifiers`, `set_modifiers`),
  `hyperspace/learn.py` (`Learn.arm`, `wants`, `_row` — the op and depth it chooses
  per source), `hyperspace/ui_routing.py` (`add_route` — the `Owned` → ask →
  `replace_owner` prompt to reuse; `set_modifier_input`, `add_modifier`),
  `hyperspace/ui.py` (the param menu's Learn items), `hyperspace/undo.py`,
  `tests/test_graphview.py`, `tests/test_ui_routing.py`, `tests/test_learn.py`,
  `tests/test_modifiers.py`.

Build exactly what N3's section says, every edit through the table's own methods
(undo, dirt, the referee and the session/preset split untouched):
`graphview.Edit` requests `connect(src_port, dst_port)`, `disconnect(cable)`,
`insert_modifier(cable, kind)`, `add_modifier(kind)`, `remove_node(id)`, each
returning what the table method returned or a refusal in words. `connect` into a
`mod` port → `Bindings.add(Binding(src, pid, op, value))` with op and depth as
`learn._row` chooses (`push` at the hand learn's depth for a hand axis, else
`position` at 1); `Owned` → the same ask → `replace_owner` prompt `ui_routing.add_route`
shows (reuse it); dragging a cable's end to another port → `move_route`; into a
`base` port → a setter row only for a `pad` or MIDI source (`Binding(src, pid,
"abs", layer="preset")` through `bind(write=False)`), else refused in words ("a hand
sets no base; aim at mod"); from a macro → a `Sub` (`base` port: a base sub; a
cable's `depth` stub: a depth sub); onto a modifier's `in` port → that modifier's
input (N1's `set_modifier_input` path); a modifier dropped onto a cable →
`insert_modifier` (the cable's source becomes the modifier's input, `mod:<n>` the
cable's new source via `move_route`); `disconnect` → `remove` (its depth subs
follow). On the canvas: `begin_create` / `query_new_link` / `accept_new_item`,
`begin_delete` / `query_deleted_link`, drag-and-drop, a right-click node picker for
modifiers and macros. **Learn from a port**: right-click a `mod` port → the param
menu's Learn items (desk, pad, hand, a role — exactly as `ui.py`'s param menu
offers them, reuse the function); the completed `Binding` appears as a cable next
frame because the view is rebuilt from the table.

Tests (`tests/test_graph_edit.py`): at least the eight named in your section,
through `graphview.Edit` and the page's functions headless (as `test_graphview`
and `test_ui_routing` do). Goldens unmoved. Base gates in your dispatch.

Decisions you take (the picker's contents, the refusal words, how a drop on a
cable is detected, …) as register-row drafts into
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N3.md` with hand-check drafts
(Y.n: a cable dragged on the laptop screen at the control window's size; Learn from
a port completing with the APC40 and with a hand; the hand-energy → smooth →
combine → acid-mix patch built on the canvas and felt with a real hand) and
as-built notes; report to `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/N3-report.md`.

PR: `gh pr create --base plan-28-30-integration` titled `Plan 28 N3: editing the
modulation on the canvas, Learn from a port`. Reply with the short contract.
