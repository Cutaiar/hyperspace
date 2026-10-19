# The review pass — plans 28 and 30 on `plan-28-30-integration`

You are the whole-branch reviewer. Read-only: do not change any working tree,
index, HEAD or branch; do not dispatch sub-agents; never read or touch
`~/Hyperspace` or `~/My Drive/Hyperspace`. You may run focused tests and small
probes from the worktree your dispatch names, with `HYPERSPACE_HOME` at a scratch
folder under `/Users/dallman/.claude/jobs/7e5d0255/tmp/` whose `config.toml` has no
`[library]` and lists the APC40 disabled.

Read first: `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/reviewer-common.md`,
`/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/briefs/common.md`, then in the worktree
`docs/plans/28-30-orchestrator-prompt.md` in full (the checklist is at lines
764–839 under "A review pass", the gates 840–900, the invariants after them), and
the ledger `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/progress.md` (every ruling,
every deferred minor — search "review pass").

The diff package in your dispatch is the whole branch against the base 5d18192
(goldens' PNGs, `ARCHITECTURE.html` and the lock file excluded). The per-WP
reports and decisions are under `/Users/dallman/.claude/jobs/7e5d0255/tmp/sdd/reports/`
and `.../decisions/`; the per-WP reviews' deferred minors are in the ledger.

## The checklist (each item: hold / fail, with the evidence you used)
1. **A golden that moved.** Diff every hash in `tests/golden/frames/frames.json`
   against the base recording (`git show 5d18192:hyperspace-python/tests/golden/frames/frames.json`
   from the worktree is read-only and fine): the 556 base hashes identical; the only
   new hashes are the five fixtures' (D1: palette-hands, palette-glass, acid-scene;
   N4: hands-glass-only, wired-outputs). Account for every difference.
2. **The lag's removal changing a value, not just its timing.** Read
   `tests/test_routing.py::test_every_factory_preset_lands_the_same_values_one_frame_earlier`:
   is the oracle faithful, does it cover every factory preset, and does any param's
   sequence differ other than by the shift? Run it.
3. **A param applied twice in a frame**: every path to `Param.apply` (grep the
   package); the frame mark's reset; base restore / offsets / toggles once a frame;
   `ViewState.integrate`'s adoption.
4. **An LFO stepping twice or not at all** after the move into the patch; an LFO
   with no cables still steps; `app.main` calls `router.use_lfos`; the three tools
   that keep the old shape (named in N0's notes) — harmless or not.
5. **A modifier in `bindings.json`, or a session row in the preset**: `is_session_row`
   and the preset's keys (`modifiers`, `layout`, `wires`/`graph`) — load a pre-run
   preset and `bindings.json` fixture: no note, no dirt; a preset saved by this run
   loads on the base build with only the new keys ignored (reason it from the base's
   `load_doc`).
6. **A cycle the sorter misses** (through a macro's depth sub, through a `scale`
   param, through a modifier-only loop) or one it refuses that a `delay` breaks.
7. **The GRAPH page and ROUTING disagreeing**: one table, two views — a route added
   on one is on the other next frame; the N3 edits all go through the table's
   methods (grep `graphview`/`ui_graph` for any direct write to `Binding`/
   `Bindings.bindings`/`Param`).
8. **An off effect costing a pass**, or two consumers of one effect running it
   twice; the SYSTEM per-effect lines summing against the old `fx` line.
9. **A placed effect's texture reused while still read** (the pool and the `avoid`
   rule, D0 row 3 / D1); the presenter path (a half-float Handoff).
10. **A wire into an output changing another output**, or the session's switches
    written by a preset load (N4).
11. **The imgui node editor's context** created once, destroyed on close and ⌘R,
    not leaking across a hot reload of `ui_graph`.
12. **`apc40.py`, `midi.py` and `hyperspace/library/`** unchanged
    (`git diff --stat 5d18192 -- hyperspace-python/hyperspace/apc40.py hyperspace-python/hyperspace/midi.py hyperspace-python/hyperspace/library/` empty).
13. **The invariants**: the render stack writes no param; `Router.modulate` the only
    `Param.modulate` caller; `Param.apply` only from `Registry.apply`/`remove` and
    `Router.modulate` under the mark; `graph.py` imports no `params`/`routing`/
    `library`/`preset`/`undo`/`control`/`devices`; `patch.py`/`modifiers.py` leaves;
    no `torch` outside `dream.py`; the boundary tests of the gates list untouched
    except the named changes.
14. **The deferred minors** from the per-WP reviews (the ledger lists them per WP:
    D0's `_program` twice a frame; N1's same-pick no-op untested; N0's early delay
    passing ±inf; N2's redo test and `route_said` per frame; …): which are worth
    a fix in the fix wave, which stay registered.
15. **Docs vs code** (if D3 / N6 have landed when you run): ten claims sampled from
    the two plan files, ENGINEERING §2/§6/§9/§10, ARCHITECTURE §2/§3, checked
    against the code; any that the code does not do.

## Output
The format of reviewer-common.md, plus a triage list: **Fix wave** (what, where,
why, the test), **Register** (rough edges to record, where), **Hold** (checked,
nothing to do). Name the commands you ran and their last lines.
