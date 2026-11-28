"""Plan 93: an old show still draws its point clouds, end to end.

Before `hyperspace.loadable/13` a loadable patch's scene drew one cloud per cloud device
this Mac listed, by the meta controller's standing wire (`cloud[.n] → scene.geometry`),
unless the patch's ``bus`` cut it. A load now says that as the patch's own cloud nodes and
wires (`graphmigrate.thirteen`): each opened here through the library, onto a renderer
holding a real `cloud` device (the fixture recording), drawn, saved as `/13`, loaded again
— the same picture as the same look written by hand in `/13` words — and the first save
over the old file keeps it beside itself (`library.CLOUDS_BACKUP`, `routing.backup`)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from test_cloud_node import registry
from test_outputs import H, W, px, views

from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace.headless import make_app
from hyperspace.library import CLOUDS_BACKUP, LibraryError
from hyperspace.outputs import Switches

CORPUS = Path(__file__).parent / "corpus" / "loadable"


def _old(home: Path, name: str, cut: list[int] = (), roles: int = 0) -> Path:
    """party-trip as a `/12` (the build before plan 93): no cloud node, its bus
    cutting the old cloud wires `cut` (instances), its look the clouds' shared one."""
    doc = json.loads((CORPUS / "party-trip.json").read_text())
    doc["schema"], doc["name"] = M.TWELVE_SCHEMA, name
    doc["values"].update({"cloud.size": 3.0, "cloud.scale": 0.4, "cloud.bright": 0.8,
                          "cloud.colors": True})
    if cut:
        doc["bus"] = {"cut": [{"from": G.cloud_name(n), "to": "scene.geometry"} for n in cut]}
    path = home / "loadable" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1) + "\n")
    return path


def _app(tmp_path, ctx=None, roles=("scan",)):
    """The headless app over a scratch library, with a renderer whose device
    registry lists `roles` as recorded clouds (the fixture)."""
    home = tmp_path / "home"
    (home / "loadable").mkdir(parents=True, exist_ok=True)
    app = make_app(home)
    devs = None
    if roles:
        from hyperspace import devices
        devs = registry(tmp_path / "dev", role=roles[0])
        if len(roles) > 1:
            devs = devices.DeviceRegistry(
                [{"role": r, "kind": "cloud", "file": "clouds/knot.npz"} for r in roles],
                devices.Context(home=tmp_path / "dev"), clock=lambda: 0.0)
            devs.open_all()
    if ctx is not None:
        from hyperspace.render import Renderer
        r = Renderer(ctx, fx=app.loaded_patch.graph.fx)
    else:
        from types import SimpleNamespace
        r = SimpleNamespace(wiring=None)
    r.cloud_source = devs
    app.loaded_patch.graph.attach(r)
    return app, r, home


def test_an_old_show_gets_a_cloud_node_and_wire_per_device_it_drew(tmp_path):
    app, _, home = _app(tmp_path, roles=("scan", "desk"))
    _old(home, "old")
    assert app.loaded_patch.load("old") == []
    spec = app.loaded_patch.graph.spec
    assert [(c.name, c.device) for c in spec.clouds] == [("cloud", "scan"), ("cloud.2", "desk")]
    geo = [w.src for w in spec.wires if w.dst == "scene.geometry"]
    assert geo[:2] == ["cloud", "cloud.2"]                 # first: the clouds drew first
    # the shared look, each cloud's now
    reg = app.reg
    for name in ("cloud", "cloud.2"):
        assert (reg[f"{name}.size"].value, reg[f"{name}.scale"].value,
                reg[f"{name}.bright"].value) == (3.0, 0.4, 0.8)
    assert "point clouds the meta controller drew" in app.loaded_patch.migrated
    doc = app.loaded_patch.document("old")
    assert doc["schema"] == M.THIRTEEN_SCHEMA and "bus" not in doc


def test_a_cut_cloud_wire_stays_cut(tmp_path):
    app, _, home = _app(tmp_path, roles=("scan", "desk"))
    _old(home, "cut", cut=[1])
    assert app.loaded_patch.load("cut") == []
    spec = app.loaded_patch.graph.spec
    assert [(c.name, c.device) for c in spec.clouds] == [("cloud.2", "desk")]
    assert G.Wire("cloud", "scene.geometry") not in spec.wires
    assert app.loaded_patch.bus.cut == frozenset()          # no fixture wire left to cut
    _old(home, "all", cut=[1, 2])
    assert app.loaded_patch.load("all") == []
    assert app.loaded_patch.graph.spec.clouds == ()
    assert "cloud.size" not in app.reg                      # its look belongs to no node


def test_no_cloud_listed_makes_no_cloud_and_says_nothing(tmp_path):
    app, _, home = _app(tmp_path, roles=())
    _old(home, "bare")
    assert app.loaded_patch.load("bare") == []
    assert app.loaded_patch.graph.spec.clouds == () and app.loaded_patch.migrated == ""


def test_the_first_save_over_an_old_file_backs_it_up_once(tmp_path, monkeypatch):
    app, _, home = _app(tmp_path)
    path = _old(home, "old")
    before = path.read_bytes()
    assert app.loaded_patch.load("old") == []
    app.loaded_patch.save_as("old")
    bak = path.with_name(f"{path.name}.bak-v{CLOUDS_BACKUP}")
    assert bak.read_bytes() == before
    saved = json.loads(path.read_text())
    assert saved["schema"] == M.THIRTEEN_SCHEMA
    assert {"kind": "cloud", "device": "scan"} in saved["graph"]["nodes"]
    # a second save makes no second copy: the file is /13 now
    app.reg["cloud.size"].set(5.0)
    app.loaded_patch.save_as("old")
    assert [p.name for p in path.parent.glob(f"{path.name}.bak-*")] == [bak.name]
    # no backup, no write
    other = _old(home, "other")
    assert app.loaded_patch.load("other") == []
    from hyperspace import routing
    monkeypatch.setattr(routing, "backup", lambda p, s: None)
    with pytest.raises(LibraryError, match="no backup"):
        app.loaded_patch.save_as("other")
    assert json.loads(other.read_text())["schema"] == M.TWELVE_SCHEMA


moderngl = pytest.importorskip("moderngl")


def _draw(ctx, r, app, frames=3):
    vs = views(ctx, Switches())
    s = r_view(app)
    for k in range(frames):
        r.cloud_source.poll(1 / 60, 2.0 + k / 60)
        r.draw_outputs(s, W, H, 1.0, vs, t_now=2.0)
    assert ctx.error == "GL_NO_ERROR"
    return px(ctx, vs[0].target)


def r_view(app):
    """The view state the app's params write (the registry's `cloud_state`'s owner)."""
    from hyperspace.view import ViewState
    s = ViewState()
    s.clouds = app.reg.cloud_state
    return s


def test_an_old_show_draws_its_cloud_as_the_same_look_written_in_13(ctx, tmp_path):
    """End to end: the old file loaded, drawn, saved and loaded again draws the
    picture its `/13` twin, written by hand with the cloud node, draws — with the
    cloud's points in it."""
    app, r, home = _app(tmp_path, ctx)
    _old(home, "old")
    assert app.loaded_patch.load("old") == []
    old = _draw(ctx, r, app)
    assert r.stats["clouds"]["cloud"] > 0
    app.loaded_patch.save_as("old")
    assert app.loaded_patch.load("old") == []
    again = _draw(ctx, r, app)
    twin = json.loads((CORPUS / "party-trip.json").read_text())
    twin["name"] = "twin"
    twin["values"].update({"cloud.size": 3.0, "cloud.scale": 0.4, "cloud.bright": 0.8,
                           "cloud.colors": True})
    twin["graph"]["nodes"].append({"kind": "cloud", "device": "scan"})
    twin["graph"]["wires"].insert(0, {"from": "cloud", "to": "scene.geometry"})
    (home / "loadable" / "twin.json").write_text(json.dumps(twin, indent=1))
    assert app.loaded_patch.load("twin") == []
    assert app.loaded_patch.migrated == ""
    new = _draw(ctx, r, app)
    assert (old == again).all() and (old == new).all()
    # and without its cloud the picture is another
    twin["graph"]["wires"].pop(0)
    (home / "loadable" / "twin.json").write_text(json.dumps(twin, indent=1))
    assert app.loaded_patch.load("twin") == []
    assert not (_draw(ctx, r, app) == old).all()
    assert np.isfinite(old).all()


def test_thirteen_is_pure_and_says_the_rows_on_the_shared_look():
    section = {"frame": "wired", "nodes": [],
               "wires": [{"from": "shape", "to": "scene.geometry"},
                         {"from": "scene", "to": "output.all.image"}]}
    doc = {"schema": M.TWELVE_SCHEMA, "graph": section, "values": {"cloud.size": 4.0},
           "routes": [{"source": "band:bass", "target": "cloud.size"}]}
    was = json.dumps(doc, sort_keys=True)
    out, notes, n = M.thirteen(doc, ("scan", "desk"))
    assert json.dumps(doc, sort_keys=True) == was                     # pure
    assert n == 2 and out["values"] == {"cloud.size": 4.0, "cloud.2.size": 4.0}
    assert notes == [M.CLOUD_ROWS_NOTE.format(rows="cloud.size", others="cloud.2")]
    # a section that never names the scene draws no cloud, and gains none
    bare = {**doc, "graph": {"frame": "wired", "nodes": [], "wires": []}}
    assert M.thirteen(bare, ("scan",))[2] == 0
    # a `/13` is never migrated again
    fwd = M.forward({**out, "schema": M.THIRTEEN_SCHEMA}, {}, clouds=("scan", "desk", "x"))
    assert [e for e in fwd.doc["graph"]["nodes"] if e["kind"] == "cloud"] == \
        [e for e in out["graph"]["nodes"] if e["kind"] == "cloud"]
