# N4 — editing the render graph: nodes and a wire list (plan 28, stream N)

You are the implementer of work package **N4**. Read first, in full:
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md` (your rules and your
first three git commands: fetch `origin plan-28-30-integration`, `git reset --hard
FETCH_HEAD`, `git branch -m plan-28-n4-edit-render`; one plain git command per shell
call). Your base must be the SHA in your dispatch or later (D0, D1, N0, N1, N2
merged).

Then, in your worktree under `hyperspace-python/`:
- `docs/plans/28-30-orchestrator-prompt.md` lines 81–242 (stream D, D0 and D1 as
  built — the effect node, placement `after`/`into`, the pool, the fixtures and their
  goldens), 477–533 (N2 as built), 534–575 (N3, built in parallel on the same files
  `graphview.py` / `ui_graph.py`: N3 adds modulation edits (`connect`/`disconnect`/
  `insert_modifier` for `value`/`trigger` ports, Learn from a port); you add render
  edits. The seam: one dispatch by port type — `image`/`geometry`/`mask` → yours.
  Keep your `Edit` methods and your `begin_create`/`begin_delete` handling in
  functions N3 can add beside; name the seam in your report), **576–628 (your
  section N4)**, 673–763, 764–839, 840–900.
- `docs/plans/28-node-editor.md` §5; `docs/plans/30-shader-nodes.md` "Placement".
- D0/D1/N2's decisions and reports in `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/`
  and `.../reports/` — D1's especially (the vocabulary, the refusal words and
  granularity, the dormant words, `opaque`, and the **presenter gap** if D1's review
  left it registered: an output drawn through a presenter and what its `hands` port
  receives).
- `hyperspace/graph.py` (`EffectAt`, `HandsAt`, `GraphSpec`, `NODE_KINDS`,
  `read_graph`, `to_json`, `default_graph(views, wiring, clouds)`, the placement
  code, `graph_words`, `Output`, `Composite`), `hyperspace/render.py` (`_graph_for`
  and its key), `hyperspace/outputs.py` (`View`, the switches, `route`, `Handoff`,
  `Presenter`), `hyperspace/preset.py` (`GraphSection`), `hyperspace/graphview.py`,
  `hyperspace/ui_graph.py`, `hyperspace/ui.py` (OUTPUT/LOOKBACK words),
  `tools/golden_frames.py` (`FIXTURE_PRESETS`, the fixture states),
  `tests/test_golden_frames.py` (completeness 580 after D1), `tests/test_graph_json.py`
  (every test stays), `tests/test_graph_placement.py`, `tests/fixtures/presets/`
  (`hands-lines.json`, D1's three).

Build exactly what N4's section says: the preset's `graph` section becomes nodes
plus wires — `{"nodes": [...], "wires": [{"from": "hands.2", "to":
"output.2.hands"}, {"from": "palette", "to": "output.1.image"}]}`; a wire names a
node's output and a `node.port`; an absent wire is the default graph's; D1's
`after`/`into` are read as wires (and still written short when a spec has only
those); `read_graph` refuses a wire into a port of another type, a port that does
not exist, two wires into one single-input port, and a cycle — each a note and the
default, the section kept. **Outputs as nodes**: a wire into `output.<n>.image`,
`.hands` or `.readout` overrides that output's switch-derived input for this
preset; an output no wire names keeps the session's switches (the rig's, not the
look's); `Renderer._graph_for`'s key gains the spec's wires; a preset load never
writes an output switch. On the canvas: `begin_create` between image/geometry/mask
ports type-checked in the drag (a wrong type refuses with the note's words); a
right-click picker adds an effect instance (`EffectAt(file, n+1)`), a hands node
(`HandsAt(n+1)`), or a composite; deleting a node or a wire edits the spec; the
preset is dirty; `Renderer` rebuilds from the new `GraphSpec` with the same
refusals. `graphview.Edit.wire(src_port, dst_port)`, `unwire`, `add_node(kind, …)`.
OUTPUT / LOOKBACK words say the wires.

Fixtures: `tests/fixtures/presets/hands-glass-only.json` (two hands nodes: `ghost`
in the scene, `ghost.2` wired to `output.2.hands` only) and `wired-outputs.json`
(the palette wired into `output.1.image`, a second acid wired after the history
into `output.2.image`); goldens recorded once, "N4 fixture, new"; force-added; the
completeness count grows by exactly their states; **none of the 580 existing hashes
may change**.

Tests (`tests/test_graph_wires.py`): at least the eight named in your section,
`test_hands_as_lines_through_the_acid_with_tracers_by_wires_alone` reproducing the
fixture `hands-lines.json`'s picture from a spec built by `Edit` calls. Base gates
in your dispatch.

Decisions (the wire list's exact keys, which output ports a preset may wire, how
`after`/`into` map onto wires and when the short form is written, the picker's
list, the refusal words) as register-row drafts into
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/decisions/N4.md` with hand-check
drafts (Y.n: "hands as lines through the acid with tracers" made by dragging and
seen on the projector; a hands node wired to the glass alone) and as-built notes;
report to `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/N4-report.md`.

PR: `gh pr create --base plan-28-30-integration` titled `Plan 28 N4: the render
graph edited as nodes and a wire list, outputs as nodes`. Reply with the short
contract.
