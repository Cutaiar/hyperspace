"""Plan 44 D3 — desk templates retired, and the migration that retires them.

Plan 24 C3's desk templates (decision 19: a named set of preset-layer rows
in ``<library>/desk/``, a preset naming one keeping only its overrides) are
gone: neither the Drive library nor ``~/Hyperspace`` held one (the owner,
2026-11-03), so the inlining plan 43 §6 item 4 asked for is a no-op and the
template code went (`preset.TEMPLATE_KEY`, `expand_desk`, `compact_desk`,
`library.DESK`, `desk_template`). What is left is the migration's word on
an old file that still names one, proven on plan 24's fixture preset
(tests/fixtures/desk-templates/):

- a load says the template is retired and lands the file's own desk rows
  (a `dark` row, which only covered a template row, is dropped);
- the save is `/10` with no ``desk_template`` and no ``modules``, and it
  is a fixed point;
- tools/migrate_library.py rewrites such a file the same way on a scratch
  copy, leaving ``desk/`` as it found it;
- the library has no `desk` group: a `desk/default.json` is never a
  group default.
"""

import json
import shutil
from pathlib import Path

from test_loadable import boot

from hyperspace import graphmigrate, library, loadable
from hyperspace.loadable import desk_json

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "desk-templates"
TEMPLATE = FIXTURES / "desk" / "fixture-shape.json"
LOADABLE = FIXTURES / "presets" / "templated.json"


def put_fixtures(home: Path) -> None:
    for src, group in ((LOADABLE, "presets"), (TEMPLATE, "desk")):
        (home / group).mkdir(parents=True, exist_ok=True)
        shutil.copy(src, home / group / src.name)


def test_the_template_code_is_gone():
    for name in ("TEMPLATE_KEY", "expand_desk", "compact_desk", "merge_modifiers",
                 "template_doc"):
        assert not hasattr(loadable, name), name
    for name in ("DESK", "DESK_SCHEMA"):
        assert not hasattr(library, name), name
    assert not hasattr(library.Library, "desk_template")
    for name in ("template_of_loaded", "template_at_load", "_at_load", "_mods_at_load"):
        assert not hasattr(loadable.LoadedPatch, name), name
    assert graphmigrate.TEN_RETIRED == ("modules", "desk_template")


def test_ten_drops_the_template_and_its_dark_rows_and_the_labels():
    doc = json.loads(LOADABLE.read_text())
    out = graphmigrate.ten(doc)
    assert "desk_template" not in out and "modules" not in out
    assert [r["source"] for r in out["desk"]] == ["cc:*:17", "cc:0:50"]
    assert doc["desk_template"] == "fixture shape"            # pure: the input is untouched
    # a /10 comes back as it is
    ten = {"schema": graphmigrate.LOOK_SCHEMA, "desk_template": "x"}
    assert graphmigrate.ten(ten) is ten


def test_an_old_templated_loadable_loads_its_own_rows_and_saves_without_the_key(tmp_path):
    rig = boot(tmp_path)
    put_fixtures(rig.home)
    rig.lib._sync()
    assert rig.loaded_patch.load("TEMPLATED") == []
    assert loadable.TEMPLATE_RETIRED.format(name="fixture shape") in rig.loaded_patch.notes
    desk = desk_json(rig.router.table.desk())
    assert [r["source"] for r in desk] == ["cc:*:17", "cc:0:50"]
    assert {r["target"] for r in desk} == {"dream.mix", "view.pattern_mix"}
    doc = rig.loaded_patch.document("TEMPLATED")
    assert doc["schema"] == "hyperspace.preset/10"
    assert "desk_template" not in doc and "modules" not in doc
    path = rig.loaded_patch.save_as("TEMPLATED")
    first = path.read_bytes()
    rig.loaded_patch.load("TEMPLATED")
    assert rig.loaded_patch.notes == [] and not rig.lib.is_dirty("presets")
    assert rig.loaded_patch.save_as("TEMPLATED").read_bytes() == first      # a fixed point
    # the template file is never read, never written
    assert (rig.home / "desk" / TEMPLATE.name).read_bytes() == TEMPLATE.read_bytes()


def test_the_tool_rewrites_a_templated_loadable_on_a_scratch_copy(tmp_path, monkeypatch):
    """tools/migrate_library.py --apply over a scratch library (never the
    owner's): the templated preset is /10 without the key, the library was
    backed up first, `desk/` is left as it was."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import migrate_library as tool

    lib = tmp_path / "lib"
    put_fixtures(lib)
    home = tmp_path / "machine"
    home.mkdir()
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))
    code = tool.main(["--library", str(lib), "--apply"], picture=lambda p, **kw: ([], []))
    assert code == 0
    doc = json.loads((lib / "presets" / LOADABLE.name).read_text())
    assert doc["schema"] == tool.NEWEST == "hyperspace.preset/10"
    assert "desk_template" not in doc and "modules" not in doc
    backups = list(home.glob("library-backup-*"))
    assert len(backups) == 1
    assert json.loads((backups[0] / "presets" / LOADABLE.name).read_text()) == json.loads(
        LOADABLE.read_text())
    assert (lib / "desk" / TEMPLATE.name).read_bytes() == TEMPLATE.read_bytes()


def test_no_desk_group_default(tmp_path):
    """A `desk/default.json` (a template once called "default") is no group's
    default: the `desk` param group has no module presets and the folder no
    meaning."""
    rig = boot(tmp_path)
    (rig.home / "desk").mkdir(exist_ok=True)
    (rig.home / "desk" / "default.json").write_text(json.dumps(
        {"schema": "hyperspace.desk/1", "name": "default", "desk": []}))
    rig.lib._sync()
    assert rig.lib.defaults("desk") == rig.lib._fresh_of("desk")
