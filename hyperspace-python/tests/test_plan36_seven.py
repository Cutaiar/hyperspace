"""Plan 36 T3 (W3, D5): nothing loads that isn't in the file — schema `/7`.

- A `/7` is read as it is: nothing is added, a section-less (or empty) one
  is black and the strip says so, a refused wire is dropped and said.
- An effect exists only where the section names it (`FxState.hold`):
  absent from the build, the FX page and the registry otherwise.
- D1's `into` / `after` are the wires they stood for (`placed_wires`); a
  `/7` frame reads no placement key.
- The hands entries and `laid` are always written.
- `/4`–`/6` are read only through the one-way migration to `/7`
  (`graphmigrate.seven`), with a note — and a `/7` is never migrated, so a
  migrated wire the owner cuts stays cut through a save and a reload.
- The corpus loadable patches are their sources' `/7`, fixed points.

The goldens (tests/test_golden_frames.py) prove the migrated pictures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import CORPUS

from hyperspace import graph as G
from hyperspace import graphmigrate as M
from hyperspace import graphview, headless, loadable, ui_fx
from hyperspace.headless import make_app
from hyperspace.outputs import Switches, View

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "presets"
# the corpus loadable patches' sources (plan 36 T3: the corpus files are their `/7`)
SOURCES = ROOT / "tests" / "fixtures" / "factory-sources" / "presets"
SIZE = (240, 150)
SEVEN = M.WIRED_SCHEMA
SAVED = M.SAVE_SCHEMA          # plan 43 C2: what a save writes (a /7 read, a /9 written)
# today's frame: what a section-less old loadable patch migrates to (`wired_of(Wiring())`;
# plan 36 T4: its look-back off in the old values — none drawn)
TODAY = [("shape", "scene.geometry"), ("scene", "output.all.image"),
         ("hands.layer", "output.all.hands"), ("hands.layer", "output.all.guide"),
         ("pattern", "shape.faces"), ("hands", "hands.layer.hands")]


def _views(n: int = 2) -> list[View]:
    return [View(Switches(), SIZE) for _ in range(n)]


def _pairs(section: dict) -> list[tuple[str, str]]:
    return [(w["from"], w["to"]) for w in section.get("wires") or []]


# the params whose shipped default moved with the calmer defaults of
# 2026-10-31 (DECISIONS, "Shipped effect defaults are calm"): every
# effect's speed, its amount-like faders and an LFO's depth. The corpus
# files were migrated before that, so where a source names none of these
# the corpus holds the old default and a migration today lands the new.
CALMED = {"fx.acid.bend", "fx.acid.twist", "fx.acid.breathe", "fx.deconverge.amount",
          "fx.deconverge.radial", "fx.displace.amount", "fx.doublevision.amount",
          "fx.fractals.amount", "fx.glimmer.amount", "fx.plasma.level",
          "fx.tripcolour.amount", "fx.warp.amount", "fx.wobble.amount", "fx.zoomblur.amount"}


def _calmed(key: str) -> bool:
    return (key in CALMED or (key.startswith("fx.") and key.endswith(".speed"))
            or (key.startswith("lfo.") and key.endswith(".depth")))


def _as_before_calming(made: bytes, source: Path, data: bytes) -> dict:
    """The fresh migration `made` of `source`, with each calmed default the
    source left unnamed put back to what the corpus file `data` holds —
    and nothing else may differ."""
    doc, want = json.loads(made), json.loads(data)
    named = json.loads(source.read_text()).get("values") or {}
    for key, value in doc["values"].items():
        if value != want["values"].get(key):
            assert _calmed(key) and key not in named, (source.name, key, value)
            doc["values"][key] = want["values"][key]
    return doc


def _app_with(tmp_path, name: str, doc: dict):
    """The headless app with `doc` as the user's loadable patch `name`, loaded."""
    app = make_app(tmp_path / "home")
    folder = tmp_path / "home" / loadable.GROUP
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.json").write_text(json.dumps({"name": name, **doc}))
    app.lib.load(loadable.GROUP, name)
    return app


def _build(app, n: int = 2) -> G.Graph:
    gs = app.loaded_patch.graph
    return G.build_graph(_views(n), gs.wiring, (), tuple(sorted(gs.fx.specs)))


# ---------------------------------------------------------------- a /7 is read as it is

@pytest.mark.parametrize("graph", [None, {}, {"frame": "wired"}])
def test_a_section_less_seven_loads_black_and_says_so(tmp_path, graph):
    """No section, an empty one or the bare marker: the empty frame — the
    outputs and nothing else, no effect held — and the strip's note says
    so. Nothing is filled in (the factory frame was, before W3)."""
    doc = {"schema": SEVEN, "values": {"view.bright": 1.0},
           **({"graph": graph} if graph is not None else {})}
    app = _app_with(tmp_path, "bare", doc)
    gs = app.loaded_patch.graph
    assert loadable.NO_GRAPH_SAID in app.loaded_patch.notes
    assert gs.wiring.wired and gs.wiring.wires == ()
    g = _build(app)
    assert all(isinstance(n, G.Output) for n in g.nodes.values()), list(g.nodes)
    assert gs.fx.specs == {}                           # no effect exists
    assert not [p.id for p in app.reg if p.id.startswith("fx.acid.")]
    saved = app.loaded_patch.document("bare")
    assert saved["schema"] == SAVED
    assert saved["graph"] == {"frame": "wired", "nodes": [{"kind": "hands", "laid": "over"}]}


def test_the_renderer_and_the_canvas_draw_nothing_unasked():
    """`Renderer.wiring`'s own is the empty frame (`EMPTY`); `build_graph`
    builds nothing for None and refuses an unwired `Wiring` (an old
    loadable patch's words: the migration wires it, `wired_wiring`); a GRAPH edit
    with nothing landed starts from the empty frame."""
    g = G.build_graph(_views(1), None)
    assert all(isinstance(n, G.Output) for n in g.nodes.values())
    with pytest.raises(ValueError, match="unwired Wiring"):
        G.build_graph(_views(1), G.Wiring())
    assert not hasattr(G, "wired")
    w = M.wired_wiring(G.Wiring())
    assert w.wired and sorted((x.src, x.dst) for x in w.wires) == sorted(TODAY)
    assert graphview._frame_doc(None) == G.read_graph({"frame": "wired"}).to_json()
    assert graphview.frame_of(None).wires == ()


@pytest.mark.empty_frame
def test_the_apps_renderer_starts_on_the_empty_frame():
    """The renderer's own wiring is `graph.EMPTY` until a loadable patch lands one
    (the tests' conftest hands bare renderers today's frame; this one is
    the app's)."""
    moderngl = pytest.importorskip("moderngl")
    try:
        ctx = moderngl.create_context(standalone=True)
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    from hyperspace.render import Renderer

    try:
        assert Renderer(ctx).wiring is G.EMPTY
    finally:
        ctx.release()


def test_a_refused_wire_in_a_seven_is_dropped_with_a_note_not_defaulted(tmp_path):
    """A wire this build refuses (no such port) is dropped and said; the
    port it went into is not given a default, and a save writes what runs."""
    section = {"frame": "wired", "nodes": [], "wires": [
        {"from": "shape", "to": "scene.geometry"},
        {"from": "scene", "to": "output.all.teapot"}]}
    app = _app_with(tmp_path, "refused", {"schema": SEVEN, "values": {}, "graph": section})
    notes = [n for n in app.loaded_patch.notes if n.startswith("graph: wire")]
    assert len(notes) == 1 and "teapot" in notes[0] and notes[0].endswith("; dropped")
    gs = app.loaded_patch.graph
    assert [(w.src, w.dst) for w in gs.wiring.wires] == [("shape", "scene.geometry")]
    assert _pairs(app.loaded_patch.document("refused")["graph"]) == [("shape", "scene.geometry")]


def test_a_seven_is_never_migrated_or_filled_in(tmp_path):
    """A `/7` frame with no pattern wire, no cover and no hands wire loads
    with none of them (the migration's hidden edges are an old file's);
    no note says it was migrated."""
    section = {"frame": "wired", "nodes": [], "wires": [
        {"from": "shape", "to": "scene.geometry"},
        {"from": "scene", "to": "lookback.image"},
        {"from": "lookback", "to": "output.all.image"}]}
    app = _app_with(tmp_path, "lean", {"schema": SEVEN, "values": {}, "graph": section})
    assert app.loaded_patch.migrated == "", app.loaded_patch.migrated
    got = _pairs(app.loaded_patch.document("lean")["graph"])
    assert got == _pairs(section)


# ---------------------------------------------------------------- effects only where named

def test_an_effect_not_in_a_seven_section_is_absent_everywhere(tmp_path):
    """Acid is wired; palette is not in the section, though the file holds
    its values: palette has no params (its values are unknown ids, said),
    no node in the build and no row on the FX page; acid has all three."""
    section = {"frame": "wired", "nodes": [], "wires": [
        {"from": "shape", "to": "scene.geometry"},
        {"from": "scene", "to": "acid.image"},
        {"from": "acid", "to": "output.all.image"}]}
    values = {"fx.acid.on": True, "fx.palette.on": True, "fx.palette.mix": 1.0}
    app = _app_with(tmp_path, "one-fx", {"schema": SEVEN, "values": values, "graph": section})
    gs = app.loaded_patch.graph
    assert set(gs.fx.specs) == {"acid"} and "palette" in gs.fx.files
    assert "fx.acid.on" in app.reg and "fx.palette.on" not in app.reg
    assert any("unknown id" in n and "fx.palette" in n for n in app.loaded_patch.notes)
    effects = {n.effect for n in _build(app).nodes.values() if isinstance(n, G.Effect)}
    assert effects == {"acid"}
    listed = {name for _, names in ui_fx.groups(gs.spec) for name in names}
    assert listed == {"acid"}
    assert not any(k.startswith("fx.palette.") for k in app.loaded_patch.document("one-fx")["values"])


def test_the_migration_drops_the_values_of_effects_not_in_the_section():
    """An old loadable patch's off effect is in no run: at migration its values go
    (it no longer exists); a live one keeps its values and its wires."""
    doc = {"schema": "hyperspace.preset/2", "values": {
        "fx.on": True, "fx.acid.on": True, "fx.acid.bend": 0.2,
        "fx.palette.on": False, "fx.palette.hue_from": 10.0}}
    out, _ = M.seven(doc, {"acid": (10, 1.0), "palette": (20, 1.0)})
    assert out["schema"] == SEVEN
    assert out["values"] == {"fx.on": True, "fx.acid.on": True, "fx.acid.bend": 0.2}
    assert ("scene", "acid.image") in _pairs(out["graph"])     # (plan 36 T4: no look-back)


# ---------------------------------------------------------------- old files, one way

def test_an_old_section_less_loadable_migrates_to_todays_frame():
    """A `/2` with no section (every corpus loadable patch's source) is today's
    frame, each hidden edge a wire, as `/7`."""
    out, notes = M.seven({"schema": "hyperspace.preset/2", "values": {}}, {})
    assert out["schema"] == SEVEN and notes == []
    assert sorted(_pairs(out["graph"])) == sorted(TODAY)
    spec = G.read_graph(out["graph"])
    assert spec.wired and spec.notes == ()


def test_an_old_file_loads_through_the_migration_with_a_note(tmp_path):
    doc = json.loads((FIXTURES / "acid-scene.json").read_text())
    app = _app_with(tmp_path, "acid-scene", doc)
    said = M.MIGRATED_NOTE.format(old="hyperspace.preset/2", new=SAVED)
    assert app.loaded_patch.migrated == said and app.loaded_patch.notes == []     # (not a problem)
    assert app.lib.warning == f"{app.lib.warning.split()[0]} acid-scene: {said}"              # (the strip says it)
    assert app.loaded_patch.document("acid-scene")["schema"] == SAVED


@pytest.mark.parametrize("slug, want", [
    # into output 2: on its picture, All outputs' by the bus cable it rode
    ("palette-glass", [("huecycle", "palette.image"), ("palette", "output.2.image")]),
    # after the scene: every picture wire from the scene reads acid.2 (plan
    # 36 T4: the look-back on — it records acid.2, and the trail and the
    # dream are added onto it)
    ("acid-scene", [("scene", "acid.2.image"), ("acid.2", "composite.under"),
                    ("acid.2", "lookback.image")]),
    # after the hands' layer: its picture into All outputs, not the guide
    ("palette-hands", [("hands.layer", "palette.image"), ("palette", "output.all.hands"),
                       ("hands.layer", "output.all.guide")]),
])
def test_placements_become_the_wires_they_stood_for(slug, want):
    from hyperspace.fx import FxState

    doc = json.loads((FIXTURES / f"{slug}.json").read_text())
    out, _ = M.seven(doc, M.specs_of(FxState()))
    section = out["graph"]
    assert not any(k in e for e in section["nodes"] for k in G.PLACE_KEYS)
    for pair in want:
        assert pair in _pairs(section), (slug, pair, _pairs(section))
    assert G.read_graph(section).notes == ()


def test_a_seven_frame_reads_no_placement():
    """`after` / `into` in a `/7` frame: not read — said, the effect where
    its wires put it (none here: unreached). The migration alone reads it."""
    section = {"frame": "wired", "nodes": [{"kind": "effect", "file": "palette",
                                            "after": "scene"}],
               "wires": [{"from": "shape", "to": "scene.geometry"},
                         {"from": "scene", "to": "output.all.image"}]}
    spec = G.read_graph(section)
    assert spec.notes and "not read since /7" in spec.notes[0]
    assert not any(e.placed for e in spec.effects) and spec.wiring().placed == ()
    assert G.read_graph(section, placements=True).effects[0].where == ("after", "scene")
    assert not hasattr(G, "_place") and not hasattr(G, "_place_one")


def test_the_hands_entries_and_laid_are_always_written():
    """A wired frame writes hands 1 and every declared hands node, and
    `laid` on the layer's — `over` too."""
    got = G.read_graph({"frame": "wired"}).to_json()
    assert got["nodes"] == [{"kind": "hands", "laid": "over"}]
    got = G.read_graph({"frame": "wired", "nodes": [
        {"kind": "hands", "instance": 2, "draw": "lines", "laid": "depth"}]}).to_json()
    assert got["nodes"] == [{"kind": "hands"},
                            {"kind": "hands", "instance": 2, "draw": "lines", "laid": "depth"}]


def test_a_cut_migrated_wire_stays_cut_through_a_save_and_a_reload(tmp_path):
    """The controller's acceptance: load a migrated loadable patch, cut a migrated
    wire (`pattern → shape.faces`, plain faces), save — a `/7` — and load
    it again: the wire is still cut (a `/7` is never migrated again)."""
    app = make_app(tmp_path / "home")
    folder = tmp_path / "home" / loadable.GROUP
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "trip.json").write_bytes(
        (SOURCES / "party-trip.json").read_bytes())                          # a /2
    app.lib.load(loadable.GROUP, "trip")
    assert ("pattern", "shape.faces") in _pairs(app.loaded_patch.graph.free_doc())
    e = graphview.Edit(graph=app.loaded_patch.graph, push=lambda label: None)
    assert e.unwire("pattern", "shape.faces") is None, e.said
    assert ("pattern", "shape.faces") not in _pairs(app.loaded_patch.graph.free_doc())
    path = app.loaded_patch.save_as("trip")
    assert json.loads(path.read_text())["schema"] == SAVED
    again = make_app(tmp_path / "home")
    again.lib.load(loadable.GROUP, "trip")
    assert ("pattern", "shape.faces") not in _pairs(again.loaded_patch.graph.free_doc())
    assert again.loaded_patch.migrated == ""


# ---------------------------------------------------------------- the corpus loadable patches

def test_every_corpus_loadable_is_its_sources_seven_and_round_trips(tmp_path):
    """Each corpus loadable patch (tests/corpus/loadable) is `/7`; loaded and saved
    untouched it is the same bytes; and it is exactly what
    tools/migrate_library.py makes of its source (`--to`: load the old file,
    save) — so the migration can be re-run from the sources and lands the
    same files, up to the defaults a source does not name that moved since
    (`_as_before_calming`)."""
    paths = sorted((CORPUS / "loadable").glob("*.json"))
    assert len(paths) == 25
    assert sorted(p.name for p in SOURCES.glob("*.json")) == [p.name for p in paths]
    for k, path in enumerate(paths):
        data = path.read_bytes()
        assert json.loads(data)["schema"] == SAVED, path.name
        again, notes, _ = headless.resave(path, tmp_path / f"f{k}")
        assert again == data and notes == [], path.name
        made, _, _ = headless.resave(SOURCES / path.name, tmp_path / f"s{k}")
        assert _as_before_calming(made, SOURCES / path.name, data) == json.loads(data), path.name
