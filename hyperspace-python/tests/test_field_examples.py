"""The field examples: every effect that changes for fields
ships a loadable patch and a short Markdown beside it. Their home is the
Drive library's `loadable/field-examples/`; these are the repository's copies,
test fixtures (`tests/fixtures/field-examples/`), kept equal to the Drive's.

Each must open through the library's own load with no unknown id and no note,
draw the picture its note describes (a field moves something), and its
Markdown must name only nodes and knobs that exist."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from hyperspace import headless, library

HERE = Path(__file__).resolve().parent / "fixtures" / "field-examples"
FILES = sorted(HERE.glob("*.json"))


def test_each_example_has_its_markdown_and_names_itself():
    assert len(FILES) >= 3
    for p in FILES:
        doc = json.loads(p.read_text())
        # (`stack-lookback` was saved by a build writing `/12`)
        assert doc["name"] == p.stem and doc["schema"] in ("hyperspace.loadable/11",
                                                           "hyperspace.loadable/13")
        assert p.with_suffix(".md").is_file(), p.stem
        # every example wires a field into a field port, or a stack
        assert any(w["to"].endswith((".field", ".stack")) for w in doc["graph"]["wires"]), p.stem


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_an_example_opens_with_no_note(path, tmp_path):
    doc = json.loads(path.read_text())
    folder = tmp_path / library.LOADABLE / "field-examples"
    folder.mkdir(parents=True)
    shutil.copy(path, folder / path.name)
    app = headless.make_app(tmp_path)
    missing = app.loaded_patch.load(f"field-examples/{path.stem}")
    assert missing == []
    assert not app.lib.warning
    spec = app.loaded_patch.graph.spec
    assert not spec.notes, spec.notes
    live = {(b.source, b.target) for b in app.router.table.routes()}
    for row in doc["routes"]:
        assert (row["source"], row["target"]) in live, row
    for pid, value in doc["values"].items():
        assert app.reg[pid].base == pytest.approx(value), pid


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_the_markdown_names_only_what_exists(path):
    """Every `fx.<file>.<knob>` id the Markdown spells is a knob of a file the
    example holds, and every node it names in backticks is in its graph."""
    from hyperspace.fx import FxState

    doc = json.loads(path.read_text())
    text = path.with_suffix(".md").read_text()
    specs = FxState().specs
    held = {n["file"] for n in doc["graph"]["nodes"] if n.get("kind") == "effect"}
    for file, knob in re.findall(r"fx\.([a-z_]+)\.([a-z_]+)", text):
        assert file in held, (file, path.stem)
        assert knob in {"on", "mix", "speed"} | {p.key for p in specs[file].params}, (file, knob)
    for name in re.findall(r"`([a-z_]+)\.(?:image|field|aux|stack)`", text):
        assert name in held or name in ("scene",), name


def test_an_example_draws_a_moved_picture(ctx):
    """The rings lens, drawn: with its Amount the picture differs from the
    same patch at Amount 0 (the field moves it)."""
    from test_field_wire import _views
    from test_graph_faces import _faces, _px

    from hyperspace import graph as G
    from hyperspace.render import Renderer

    doc = json.loads((HERE / "field-rings-lens.json").read_text())

    def draw(amount):
        r = Renderer(ctx)
        r.ghost.state.on = False
        # (a bare renderer has no meta controller's bus: the picture straight
        # into output 1, the hands' wires left out)
        graph = {**doc["graph"], "wires": [
            {**w, "to": w["to"].replace("output.all.image", "output.1.image")}
            for w in doc["graph"]["wires"] if not w["to"].startswith("output.all.")
            or w["to"] == "output.all.image"]}
        spec = G.read_graph(graph, effects=set(r.fx.state.specs))
        assert not spec.notes, spec.notes
        r.wiring = spec.wiring()
        for pid, v in doc["values"].items():
            if pid.startswith("fx."):
                _, file, key = pid.split(".")
                r.fx.state.values[file][key] = v
        r.fx.state.values["displace"]["amount"] = amount
        vs = _views(ctx, 1)
        r.draw_outputs(_faces(), 160, 120, 1.0, vs, t_now=2.0)
        return _px(vs[0].target).astype(int)

    assert np.abs(draw(0.05) - draw(0.0)).max() > 30


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_no_node_of_an_example_reaches_nothing(path):
    """A field ends in a field port, so the FX pane follows field wires as well as
    picture wires. Every node of an example reaches an output, on the canvas
    (`graphview.unreached`) and on the FX pane (`ui_fx.groups`) alike."""
    from hyperspace import graph as G
    from hyperspace import graphview, ui_fx
    from hyperspace.fx import FxState

    spec = G.read_graph(json.loads(path.read_text())["graph"], effects=set(FxState().specs))
    assert not spec.notes, spec.notes
    effects = {n["file"] + (f".{n['instance']}" if "instance" in n else "")
               for n in json.loads(path.read_text())["graph"]["nodes"] if n["kind"] == "effect"}
    assert not effects & graphview.unreached(spec)
    groups = dict(ui_fx.groups(spec))
    assert ui_fx.UNREACHED not in groups, groups
    # (an effect's path may end at a node that is no effect — `stack-lookback`: a Fade into a Resize, a Trail into a Cut — and the
    # pane groups it there, `→ resize`; it still reaches an output)
    ends = {e for k, v in groups.items() if k not in (ui_fx.UNREACHED, ui_fx.UNFED) for e in v}
    assert effects <= ends, groups


def test_the_knob_example_draws_the_field_on_the_knob(ctx):
    """`field-knob`: Rings into Wave's Amount at its depth moves
    the picture; with that wire gone (Amount 0, no field) Wave moves nothing."""
    from test_field_wire import _views
    from test_graph_faces import _faces, _px

    from hyperspace import graph as G
    from hyperspace.render import Renderer

    doc = json.loads((HERE / "field-knob.json").read_text())

    def draw(knob: bool):
        r = Renderer(ctx)
        r.ghost.state.on = False
        graph = {**doc["graph"], "wires": [
            {**w, "to": w["to"].replace("output.all.image", "output.1.image")}
            for w in doc["graph"]["wires"]
            if (not w["to"].startswith("output.all.") or w["to"] == "output.all.image")
            and (knob or w["to"] != "wave.amount")]}
        spec = G.read_graph(graph, effects=set(r.fx.state.specs))
        assert not spec.notes, spec.notes
        r.wiring = spec.wiring()
        for pid, v in doc["values"].items():
            if pid.startswith("fx."):
                _, file, key = pid.split(".")
                r.fx.state.values[file][key] = v
        vs = _views(ctx, 1)
        r.draw_outputs(_faces(), 160, 120, 1.0, vs, t_now=2.0)
        return _px(vs[0].target).astype(int)

    assert np.abs(draw(True) - draw(False)).max() > 30
