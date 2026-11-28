"""tools/app_driver.py script: saved dreams in the real app — the
corpus's party-wake (its dream opens as its chain, folded as **dream**,
`graphmigrate.dreams`) and the example `dream-wake`, each loaded as a performer
loads it, GRAPH on it with the dream selected; then the starter **dream on a
picture** on the scene chain. What the load said, `graphview.unreached`,
`ui_fx.groups`, the loadable patch's groups and what the dream's node says
(no worker in a cloud run: "no dream worker …") are printed beside the frames.

    uv run python tools/app_driver.py tools/drive_dream.py --home <h> --out <out>

with `dream-wake` copied into `<h>/library/loadable/field-examples/` first."""

from hyperspace import graphview, ui_fx, ui_graph

PATCHES = ("party-wake", "field-examples/dream-wake")


def _say(panel, name, n, notes):
    lp = panel.library.loaded_patch
    spec = lp.graph.spec
    r = panel.renderer if hasattr(panel, "renderer") else None
    graph = getattr(r, "_graph", None)
    said = getattr(graph.nodes.get("dream"), "said", "") if graph is not None else ""
    print(f"[dream] {name} frame {n}: notes {notes} groups "
          f"{[(g['name'], g['open'], len(g['nodes'])) for g in lp.groups]} "
          f"unreached {sorted(graphview.unreached(spec))} fx groups {ui_fx.groups(spec)} "
          f"graph notes {list(spec.notes)} dream says {said!r} "
          f"dream's knobs {panel.graph_selected_params()}", flush=True)


def script(d, panel):
    n = 20                                     # app_driver's settle
    for name in PATCHES:
        lp = panel.library.loaded_patch
        missing = lp.load(name)
        assert missing == [], missing
        notes = [x[:90] for x in getattr(lp, "notes", [])]
        yield from d.wait(60)
        n += 60
        panel.select_graph_node("render:dream")
        yield from d.park()
        yield from d.wait(40)
        n += 42
        _say(panel, name, n, notes)
    # the starter on a fresh scene chain
    lp = panel.library.loaded_patch
    lp.new((0.0, 0.0))
    yield from d.wait(20)
    e = ui_graph.render_edit(panel)
    e.loaded_patch = lp
    why = e.starter("dream")
    print(f"[dream] starter: {why or e.said}", flush=True)
    yield from d.wait(60)
    n += 80
    panel.select_graph_node("render:dream")
    yield from d.park()
    yield from d.wait(40)
    n += 42
    _say(panel, "starter: dream on a picture", n, [])
