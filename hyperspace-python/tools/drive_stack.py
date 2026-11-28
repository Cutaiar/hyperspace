"""tools/app_driver.py script: the stack examples in the real app —
each loaded as a performer loads it, GRAPH framed on it with the delay
selected (its rate and Depth on the side pane), and what the canvas and the FX
pane mark unreached printed beside the frames.

    uv run python tools/app_driver.py tools/drive_stack.py --home <h> --out <out>

with `stack-echo`, `stack-trail` and `stack-slit` copied into
`<h>/library/loadable/field-examples/` first. Prints one line per example:
its frame, `graphview.unreached` and `ui_fx.groups`."""

from hyperspace import graphview, ui_fx

EXAMPLES = ("stack-echo", "stack-echoes", "stack-trail", "stack-slit")


def script(d, panel):
    n = 20                                     # app_driver's settle
    for name in EXAMPLES:
        missing = panel.library.loaded_patch.load(f"field-examples/{name}")
        assert missing == [], missing
        yield from d.wait(30)
        n += 30
        panel.select_graph_node("render:delay")
        yield from d.park()
        yield from d.wait(40)
        n += 42
        spec = panel.library.loaded_patch.graph.spec
        print(f"[stack] {name} frame {n}: unreached {sorted(graphview.unreached(spec))} "
              f"groups {ui_fx.groups(spec)} notes {list(spec.notes)} "
              f"delay's knobs {panel.graph_selected_params()}", flush=True)
