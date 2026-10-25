# D2 — the FX page, the `VALUE` port, the faces exception (plan 30, stream D)

You are the implementer of work package **D2**. Read first, in full:
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md` (your rules and your
first three git commands: fetch `origin plan-28-30-integration`, `git reset --hard
FETCH_HEAD`, `git branch -m plan-30-d2-fx-page`; one plain git command per shell
call). Your base must be the SHA in your dispatch or later (D0 and D1 are merged).

Then, in your worktree under `hyperspace-python/`:
- `docs/plans/28-30-orchestrator-prompt.md` lines 81–242 (stream D today, D0, D1 —
  built; what you stand on), **243–270 (your section D2)**, 673–763, 764–839,
  840–900. Also 477–533 (N2) only for the sentence about `patch.py` being told the
  `VALUE` type name.
- `docs/plans/30-shader-nodes.md` in full ("The FX page, the OUTPUT page, SYSTEM",
  "The faces target stays an inner chain", "Designed, not built: the auxiliary
  ports").
- D0's and D1's decisions and reports in `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/{D0,D1}.md`
  and `.../reports/`.
- `hyperspace/ui_fx.py` (`page`, `_chip`, `_strip_header`, `strip_rows`, the status
  line, the drag-to-reorder), `hyperspace/graph.py` (`IMAGE`, `MASK`, `GEOMETRY`,
  `EffectAt`, `GraphSpec`, placements), `hyperspace/fx.py` (`declare`, the `target`
  param's tip, `TARGETS`), `hyperspace/patch.py` (where a port type name may be
  mentioned), `tests/test_fx.py`, `tests/test_graph_effects.py`,
  `tests/test_graph_placement.py`, `tests/test_graph.py`'s import test.

Build exactly what D2's section says:
- The FX page stays the editor of the **default chain**. A placed instance's chip
  shows where it sits ("after hands", "into output 2") and is not draggable in the
  order; its strip is as any effect's. The status line counts placed effects
  separately ("3 in the chain · 1 placed"). The page needs the loaded `GraphSpec`
  (find how `ui_fx` reaches the renderer / the preset's graph; the renderer holds
  `Wiring` and the spec today).
- `graph.VALUE = "value"`: a third port type beside `IMAGE`, `MASK`, `GEOMETRY`,
  with a docstring naming its two intended uses — a palette's value out (centre,
  width, the sat and val ranges, the ramp anchors) for a lights sink (plan 29), and
  an image-in `sample` port that would set a palette's params from a bitmap — and
  **no node publishes or reads one** in this plan. `patch.py` is told the type name
  (a constant or docstring line) so a `VALUE` port can be a modulation source later;
  `patch.py` stays a leaf (it must not import `graph`).
- `fx.<name>.target`'s tip says the faces target still runs inside the shape's face
  drawing and is the one shader run the graph does not show. Draft the register
  row: the faces stay an inner chain; the other option is the lift ("faces as a
  layer").

Tests: `test_a_placed_effects_chip_says_where_it_sits_and_is_not_reorderable`,
`test_the_value_port_type_exists_and_no_node_uses_it` (and the FX status line in
`tests/test_fx.py` — the one allowed change there: the placed count). Goldens
unmoved. Base gates in your dispatch.

Decisions (the chip's words, the `VALUE` port's shape, the faces decision) as
register-row drafts into `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/D2.md`
with hand-check drafts (X.n: the FX page's placed chip; the faces target still
bending the faces) and as-built notes; report to
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/D2-report.md`.

PR: `gh pr create --base plan-28-30-integration` titled `Plan 30 D2: the FX page's
placed chips, the VALUE port, the faces exception`. Reply with the short contract.
