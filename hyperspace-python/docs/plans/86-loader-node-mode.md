# Plan 86: the loader's units note, and node mode's dropdowns

Built 2026-11-22, wave 1 of the post-install wave ([`66-post-install.md`](https://github.com/cutaiar/hyperspace/blob/plans/66-post-install/hyperspace-python/docs/plans/66-post-install.md) on branch `plans/66-post-install`, renumbered from 73 by `66-launch.md`). Register rows 1060–1062, hand checks 855–858, group FG. No schema move, no saved key, no golden frame touched.

## 1. A note for a missing units marker (row 1060)

**What happened.** A loadable patch whose `units` lacks `"fx.depth": "taper"` is read as a file from before wave 0 T1, and every depth onto an effect's `speed` or `amount` param is moved from the linear range onto the param's taper, about its base (`params.retaper_depths`). Right for an old file. Two agents writing patches by hand on 2026-11-19 left the key out: their 0.12 became 0.28 and 0.25 became 0.8. `retaper_depths` already returned a line for every row it moved; `LoadedPatch.load_doc` threw the list away (`doc, _ = …`), so nothing was said.

**What changed.** The rescale is as it was. The load keeps the list and adds one note (`loadable.retaper_note`):

> no "units" marker, so read as a file from before the effect tapers: 1 depth rescaled (routes lfo:1 → fx.wobble.amount: push 0.12 → 0.1322 about 0.004). A save writes the marker; a file written by hand wants "units": {"fx.depth": "taper"}

The strip shows a load's first note, "(+n more)" after it; the patch's notes list shows it whole. A save writes the marker, so the next load says nothing. Only `loadable.py` changed. The meta table's rows already said theirs (`Bindings` reads them into its notes). A patch fragment (`patches/`, read by `Library`'s patch door in `library.py`) still rescales silently: `library.py` is outside this plan's files, so it is a follow-up for the owner to assign, the same one-line change.

## 2. Node mode and dropdowns (rows 1061, 1062)

**Why it mapped none.** `nodemode.fillable` kept `Kind.CONTINUOUS` only. The filter came from plan 53's latch page (§2, "Filter: `Kind.CONTINUOUS`, no alias"), written for knobs and carried into plan 57's fill. Nothing gave a reason for leaving enums out.

**What a dropdown is, underneath.** The program holds two ideas of one:

- **A position on a line.** The panel's combo writes a choice, but a desk knob, its ring and soft pickup read the dropdown as a fader with detents: `Param.set_norm` lands `round(u × (n − 1))`, `norm` is `choice / (n − 1)`. A knob learned onto a dropdown is an `abs` row today (`Learn.learn_control`), and FINE and the knob slew already step aside for a discrete param.
- **A state.** The modulation layer lands a dropdown through `_snap` with a deadband (`Param.apply`), and the base chase's ledger (`Param._commit`, plan 52) is kept in the continuous branch only. A route can move a dropdown while it runs; nothing can leave one moved.

A desk's node-mode rows edit the base, so they sit on the first idea, and a dropdown fits cleanly. A pad's node-mode rows are `push` routes that come back on release, with the chase as the way to keep a move, so they sit on the second, where a dropdown can be flicked and never left. That is the line that doesn't meet. A smaller one: a knob makes a list ordinal. An LFO's sync or Wave Table's profile sweeps sensibly; `view.shape`'s 109 shapes are a walk through unrelated shapes.

**Built (row 1061): a desk fills dropdowns.** `fillable` now keeps, after every continuous param, each dropdown with a fixed list (`choices` not a callable; the three that are, are meta) of two choices or more. Its row is the desk's usual `abs` knob row with a ring: a choice per stretch of the throw. The dropdowns come after the continuous params, as `graphview.param_ids` already lists them, so they take only the knobs the continuous params leave and every existing map stays the same. A knob that was empty may now hold a dropdown, and a patch-layer desk row on it is shadowed while node mode points there (`NodeDesk._free`, as for any filled knob): hand check 857 asks whether that is fine. Nothing saved changes, and GRAPH draws a node-mode cable to a dropdown as to any param.

**Not built (row 1062): a pad fills no dropdown.** `fillable(routed=True)` leaves them out. Options for the owner:

- **A. Leave it** (built; recommended now).
- **B. A pair steps a dropdown:** `step` rows ±1 on a free pair, an edit of the base, kept. A pad's Learn pair already makes this row on a dropdown, but node mode's pad rows would stop being only routes (`NodeDesk._pad_rows`, `Router`'s pad plan, `Router.claimed`, the cable).
- **C. The chase commits a dropdown:** `Param.apply`'s enum branch keeps the chase's ledger as integers do; then a pad fills dropdowns with pushes like any param. One meaning for every pad row, and the chase fixed for dropdowns everywhere. Touches `params.py`, outside this plan's files. Recommended if pads should reach dropdowns.

Toggles are left out of the fill for both, as before; nobody asked.

## Files

`hyperspace/loadable.py` (the note), `hyperspace/nodemode.py` (the fill). Tests: `tests/test_retaper.py`, `tests/test_nodemode.py`, `tests/test_node_desk.py`. Docs: this file, `DECISION-REGISTER.md`, `plans/11-hand-checks.md`, `plans/README.md`, `ARCHITECTURE.md`'s component table.

## Goldens

None can move. Neither change reaches a frame: the note is words, and node mode's rows act only on a controller's input, which no golden frame feeds.
