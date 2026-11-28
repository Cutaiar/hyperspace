"""Plan 93's demo (tools/app_driver.py's script): a point cloud added on GRAPH, its
device named, wired into the scene, then four copies of it on the shape's lattice.

Needs a home whose config.toml lists the fixture as a cloud device, role ``scan``
(``tests/fixtures/clouds/knot.npz`` copied to ``<home>/clouds/``), the corpus seeded
into ``<home>/library``:

    uv run python tools/app_driver.py tools/drive_cloud.py --out <scratch>/run --home <home>

The pictures in ``docs/plans/assets/93-point-cloud-node/`` are its last frames."""

from hyperspace import ui_graph


def script(d, panel):
    reg = panel.reg
    yield from d.wait(30)
    e = ui_graph.render_edit(panel)
    print("add:", e.add_node("cloud"), e.added)
    print("device:", e.set_cloud_device("cloud", "scan"))
    print("wire:", e.wire("rout:cloud", "rin:scene/geometry"))
    yield from d.wait(20)
    reg["camera.zoom"].set_value(0.6)
    reg["cloud.scale"].set_value(0.12)
    reg["cloud.size"].set_value(2.0)
    reg["cloud.yaw"].set_value(0.6)
    yield from d.wait(40)
    reg["cloud.instances"].set_value(4)
    reg["cloud.inst_spacing"].set_value(2.0)
    yield from d.wait(60)
    print("clouds drawn:", getattr(getattr(panel, "renderer", None), "stats", {}).get("clouds"))
