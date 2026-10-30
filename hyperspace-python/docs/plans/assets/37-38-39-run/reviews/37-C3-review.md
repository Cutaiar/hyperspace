# Review — 37-C3 (the backward wire), PR #253

**Task quality: Approved.** Only `graphview.py` and `tests/test_graph_areas.py`
change. The reviewer re-ran the new tests against the base `graphview.py`:
exactly the acid-scene case (`wire:acid.2>lookback/occluder`) and the rule
test fail there. The rule (`laid_areas`) cannot place a node left of its
feeders (a fixed feeder sets a floor; a movable feeder's value is always
≤ its taker's) and cannot loop (pass 1 only raises, pass 2 only lowers,
both capped); it applies only to effect-area nodes; `_apply` takes the
saved position, then the remembered first-draw position, then the areas,
so nothing re-lays. The sweep: 25 factory presets + 22 fixtures, maker's
column < taker's for every cross-area cable, loops-by-design exempt. 48
new tests, ~12 s serially, a few seconds under `-n auto`.

Departure from the brief's tie-break accepted by the controller
(decisions 11). Minors applied before merge: the docstring's clause on
kept cables; a comment on the caps; the row's "reduces to D5 only for a
consumer area left of EFFECTS"; the chip/title-frame rough edge folded
into AH.7.
