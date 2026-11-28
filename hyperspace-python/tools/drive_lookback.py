"""tools/app_driver.py script (plan 90 H2): saved look-backs in the real app —
the corpus's party-tracer and party-wake (each opens with its look-back made
public parts, `graphmigrate.lookbacks`) and the example `stack-lookback`, each
loaded as a performer loads it, GRAPH framed on it with the Trail selected,
and what the load said, what the canvas and the FX pane mark unreached
printed beside the frames.

    uv run python tools/app_driver.py tools/drive_lookback.py --home <h> --out <out>

with `stack-lookback` copied into `<h>/library/loadable/field-examples/` first.
Prints one line per patch: its frame, its load notes, `graphview.unreached`
and `ui_fx.groups`; first, folded, the loadable patch's groups (the look-back's one)."""

from hyperspace import graphview, ui_fx

PATCHES = ("party-tracer", "party-wake", "field-examples/stack-lookback")


def script(d, panel):
    n = 20                                     # app_driver's settle
    for name in PATCHES:
        lp = panel.library.loaded_patch
        missing = lp.load(name)
        assert missing == [], missing
        notes = [x[:90] for x in getattr(lp, "notes", [])]
        yield from d.wait(60)
        n += 60
        print(f"[lookback] {name} frame {n}: folded, groups "
              f"{[(g['name'], g['open'], len(g['nodes'])) for g in lp.groups]}", flush=True)
        panel.select_graph_node("render:trail")
        yield from d.park()
        yield from d.wait(40)
        n += 42
        spec = lp.graph.spec
        print(f"[lookback] {name} frame {n}: notes {notes} "
              f"unreached {sorted(graphview.unreached(spec))} groups {ui_fx.groups(spec)} "
              f"graph notes {list(spec.notes)} trail's knobs {panel.graph_selected_params()}",
              flush=True)
