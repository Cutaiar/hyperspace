"""Plan 24 C3 — desk templates (decision 19).

A desk template is a named set of preset-layer rows in its own JSON, a file
of the library's `desk` group (``hyperspace.desk/1``; the factory's
hyperspace/library/desk/ ships empty, the user's lives in the library root,
which plan 25's `[library] path` shares). A preset's desk is a template
plus its own overrides: the file names the template (``desk_template``) and
keeps only the overrides in ``desk``. Proven on a fixture template and a
fixture preset under tests/fixtures/desk-templates/, loaded through a
scratch library:

- the loaded desk is the template's rows with the overrides on top (an
  override replaces the template's row on its control; a dark row leaves
  the control unmapped);
- a save writes the reference and the overrides again, never the expanded
  rows, and a fix to the template reaches every preset that names it;
- a template the library lacks is a note, and the overrides alone;
- a preset with a plain desk section — every factory one — loads and
  saves exactly as before.
"""

import json
import shutil
from pathlib import Path

import pytest
from test_presets import boot

from hyperspace import preset
from hyperspace.library import DESK, DESK_SCHEMA, FACTORY, Library, LibraryError
from hyperspace.preset import TEMPLATE_KEY, compact_desk, desk_json, expand_desk
from hyperspace.routing import Binding

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "desk-templates"
TEMPLATE = FIXTURES / "desk" / "fixture-shape.json"
PRESET = FIXTURES / "presets" / "templated.json"


def knob(src: str, target: str) -> dict:
    return {"source": src, "target": target, "op": "abs", "feedback": "ring"}


# the fixture preset's desk once loaded: the template's rows less D2 (an
# override) and K2 (a dark row), then the overrides in the file's order
EXPANDED = [knob("cc:*:16", "view.depth4"), knob("cc:*:18", "camera.pitch"),
            knob("cc:*:19", "view.pattern"), knob("cc:0:48", "view.bright"),
            {"source": "cc:0:7", "target": "view.lines_alpha", "op": "abs", "ring": 0},
            knob("cc:*:17", "dream.mix"), knob("cc:0:50", "view.pattern_mix")]


@pytest.fixture()
def rig(tmp_path):
    return boot(tmp_path)


def put_fixtures(lib, template: bool = True) -> None:
    for src, group in ((PRESET, "presets"), *(((TEMPLATE, DESK),) if template else ())):
        (lib.home / group).mkdir(parents=True, exist_ok=True)
        shutil.copy(src, lib.home / group / src.name)


def desk_of(rig) -> list[dict]:
    return desk_json(rig.router.table.desk())


# ---------------------------------------------------------------- the group

def test_the_desk_group_ships_empty_and_lists_the_users_templates(rig):
    """No factory template: hyperspace/library/desk/ has no file (git keeps
    no empty folder, and the group needs none to list). A template in the
    library root is listed and read; a file of another format is refused."""
    lib = rig.lib
    assert not list((FACTORY / DESK).glob("*.json"))
    assert lib.list(DESK) == []
    put_fixtures(lib)
    assert lib.list(DESK) == ["fixture shape"]
    doc = lib.desk_template("fixture shape")
    assert doc["schema"] == DESK_SCHEMA and len(doc["desk"]) == 7
    assert lib.desk_template("fixture-shape") == doc               # by its slug too
    with pytest.raises(LibraryError, match="no desk template"):
        lib.desk_template("nothing")
    (lib.home / DESK / "wrong.json").write_text(json.dumps(
        {"schema": "hyperspace.preset/1", "name": "wrong", "desk": []}))
    with pytest.raises(LibraryError, match="is not hyperspace.desk/1"):
        lib.desk_template("wrong")


def test_a_template_in_the_shared_library_is_found(tmp_path):
    """Plan 25: the templates live in the library root, so a shared folder
    (`[library] path`) carries them; the machine home holds none."""
    shared, machine = tmp_path / "shared", tmp_path / "machine"
    (shared / DESK).mkdir(parents=True)
    machine.mkdir()
    shutil.copy(TEMPLATE, shared / DESK / TEMPLATE.name)
    lib = Library(shared, machine=machine, period=0.0)
    assert lib.desk_template("fixture shape")["name"] == "fixture shape"
    assert not (machine / DESK).exists()


def test_the_template_file_is_the_fixtures_shape():
    """`template_doc` writes what `desk_template` reads: the fixture is that
    text, a row a line (`dumps`)."""
    doc = json.loads(TEMPLATE.read_text())
    rows = [Binding.from_json(r) for r in doc["desk"]]
    assert preset.dumps(preset.template_doc(doc["name"], rows, doc["note"])) == \
        TEMPLATE.read_text()


# ---------------------------------------------------------------- expand / compact

def test_expand_puts_the_overrides_on_the_template():
    tmpl = json.loads(TEMPLATE.read_text())["desk"]
    over = json.loads(PRESET.read_text())["desk"]
    assert desk_json(expand_desk(tmpl, over)) == EXPANDED
    assert desk_json(expand_desk(tmpl, [])) == tmpl
    assert desk_json(expand_desk([], over)) == over[:2]          # a dark row adds nothing
    # an override on any channel covers a one-channel template row, and back
    wide = expand_desk([knob("cc:0:16", "view.bright")], [knob("cc:*:16", "camera.zoom")])
    assert desk_json(wide) == [knob("cc:*:16", "camera.zoom")]


def test_compact_is_expands_inverse():
    tmpl = json.loads(TEMPLATE.read_text())["desk"]
    over = json.loads(PRESET.read_text())["desk"]
    live = expand_desk(tmpl, over)
    assert compact_desk(tmpl, live) == over
    assert compact_desk(tmpl, expand_desk(tmpl, [])) == []
    assert desk_json(expand_desk(tmpl, compact_desk(tmpl, live))) == desk_json(live)
    # a template row a load would drop is no difference, so it is no dark row
    bad = [*tmpl, knob("cc:0:14", "view.speed")]
    assert compact_desk(bad, live, keeps=lambda b: b.source != "cc:0:14") == over


# ---------------------------------------------------------------- a load and a save

def test_a_preset_naming_a_template_loads_its_rows_with_the_overrides_on_top(rig):
    lib = rig.lib
    put_fixtures(lib)
    lib.presets.load("TEMPLATED")
    assert desk_of(rig) == EXPANDED
    assert lib.presets.notes == [] and lib.warning == ""
    assert not lib.is_dirty("presets")
    assert lib.presets.template_of_loaded() == "fixture shape"


def test_a_save_round_trips_the_reference_not_the_expanded_rows(rig):
    """Saved as a new preset, the file names the template and keeps the
    fixture's overrides, row for row; loaded again it is the same desk. An
    edit after the load is an override. A fix to the template lands in
    every preset that names it."""
    lib = rig.lib
    put_fixtures(lib)
    fixture = json.loads(PRESET.read_text())
    lib.presets.load("TEMPLATED")
    lib.presets.save_as("TEMPLATED 2")
    saved = json.loads((lib.home / "presets" / "templated-2.json").read_text())
    assert saved[TEMPLATE_KEY] == "fixture shape"
    assert saved["desk"] == fixture["desk"]
    keys = list(saved)
    assert keys.index("routes") < keys.index(TEMPLATE_KEY) < keys.index("desk") \
        < keys.index("macros")
    lib.presets.load("TEMPLATED")
    lib.presets.load("TEMPLATED 2")
    assert desk_of(rig) == EXPANDED and lib.presets.notes == []
    # an edit after the load (a learn onto D6) is one more override
    rig.router.table.bind(Binding("cc:*:21", "view.speed", "abs", feedback="ring",
                                  layer="preset"), write=False)
    assert lib.is_dirty("presets")
    lib.presets.save_as("TEMPLATED 3")
    saved = json.loads((lib.home / "presets" / "templated-3.json").read_text())
    assert saved["desk"] == [*fixture["desk"][:2], knob("cc:*:21", "view.speed"),
                             fixture["desk"][2]]
    # the template fixed: D5 added there lands in both presets that name it
    tdoc = json.loads(TEMPLATE.read_text())
    tdoc["desk"].append(knob("cc:*:20", "camera.zoom"))
    (lib.home / DESK / TEMPLATE.name).write_text(json.dumps(tdoc))
    for name in ("TEMPLATED", "TEMPLATED 2"):
        lib.presets.load(name)
        assert knob("cc:*:20", "camera.zoom") in desk_of(rig), name


def test_a_missing_template_is_a_note_and_the_overrides_alone(rig):
    lib = rig.lib
    put_fixtures(lib, template=False)
    lib.presets.load("TEMPLATED")
    assert desk_of(rig) == EXPANDED[-2:]
    (note,) = lib.presets.notes
    assert note.startswith("desk template 'fixture shape' not loaded")
    assert "TEMPLATED" in lib.warning and "desk template" in lib.warning
    # a save keeps the reference: with no template every row is an override
    lib.presets.save_as("TEMPLATED 2")
    saved = json.loads((lib.home / "presets" / "templated-2.json").read_text())
    assert saved[TEMPLATE_KEY] == "fixture shape" and saved["desk"] == EXPANDED[-2:]


def test_every_factory_preset_loads_and_saves_its_plain_desk_as_before(rig):
    """No factory preset names a template: each loads with no template
    note, and what a save would write is its whole desk under ``desk``
    with no ``desk_template`` key, the keys in the order they always were."""
    lib = rig.lib
    for path in sorted((FACTORY / "presets").glob("*.json")):
        assert TEMPLATE_KEY not in json.loads(path.read_text()), path.name
    for name in lib.list("presets"):
        lib.presets.load(name)
        assert not any("desk template" in n for n in lib.presets.notes), name
        assert lib.presets.template_of_loaded() is None
        doc = lib.presets.document(name)
        assert TEMPLATE_KEY not in doc
        assert doc["desk"] == desk_of(rig)
        assert [k for k in doc if k != "note"] == ["schema", "name", "values", "routes",
                                                   "desk", "macros", "modules"]
