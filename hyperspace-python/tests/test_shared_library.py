"""Plan 25: the shared library folder — `[library] path` puts the library
(presets, shows, module groups, hidden.json, the trash) in a folder of its
own, the machine files stay in the home, a missing folder is never created
and refuses every write, writes are atomic, and a cloud client's conflict
copy is listed beside the file it copies.

Every test is on tmp_path; nothing here touches ~/Hyperspace.
"""

import json
from types import SimpleNamespace

import pytest

from hyperspace import library
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.library import FACTORY, LAST_SHOW, PRESETS, Library, LibraryError
from hyperspace.params import build_registry
from hyperspace.preset import Presets
from hyperspace.routing import Bindings, Router
from hyperspace.view import ViewState


def make(root, machine=None):
    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    lib = Library(root, machine=machine, period=0.0)
    reg = build_registry(view, control, SimpleNamespace(chain=chain), lib.project)
    lib.attach(reg)
    presets = Presets(lib, reg, Router(reg, Bindings()))
    return SimpleNamespace(lib=lib, reg=reg, presets=presets, chain=chain)


def files(folder):
    return sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file())


# ---------------------------------------------------------------- the split

def test_no_machine_is_todays_library(tmp_path):
    """`Library(home)` alone: the machine home is the library root."""
    lib = Library(tmp_path, period=0.0)
    assert lib.machine == lib.home == tmp_path and lib.missing is None
    lib.remember("party")
    assert (tmp_path / LAST_SHOW).read_text() == "party\n"


def test_a_save_lands_in_the_library_and_last_show_in_the_machine_home(tmp_path):
    """The acceptance demo: machine home A plus library L — a preset save
    writes L/presets and nothing new in A but last_show; then L is gone, a
    relaunch warns, refuses saves, and creates nothing."""
    a, lib_root = tmp_path / "A", tmp_path / "L"
    a.mkdir()
    lib_root.mkdir()
    before = files(a)
    rig = make(lib_root, machine=a)
    assert rig.lib.home == lib_root and rig.lib.machine == a and rig.lib.missing is None
    path = rig.presets.save_as("HI FREK")
    assert path == lib_root / PRESETS / "hi-frek.json" and path.is_file()
    rig.lib.project.save("mine")
    assert (lib_root / "projects" / "mine.hyp.json").is_file()
    assert sorted(set(files(a)) - set(before)) == [LAST_SHOW]
    assert (a / LAST_SHOW).read_text() == "mine\n"
    assert not (lib_root / LAST_SHOW).exists()

    # the folder goes away (a cloud drive unmounted): relaunch
    for p in sorted(lib_root.rglob("*"), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
    lib_root.rmdir()
    rig = make(lib_root, machine=a)
    assert rig.lib.missing == lib_root
    assert "shared library not found at" in rig.lib.warning
    assert rig.lib.project.factory              # the factory show stands in
    with pytest.raises(LibraryError, match="not saved; fix \\[library\\] path"):
        rig.presets.save_as("HI FREK 2")
    assert not lib_root.exists()


# ---------------------------------------------------------------- D5: missing

@pytest.fixture()
def gone(tmp_path):
    a = tmp_path / "A"
    a.mkdir()
    rig = make(tmp_path / "Dropbox" / "Hyperspace", machine=a)
    yield SimpleNamespace(rig=rig, lib=rig.lib, root=tmp_path / "Dropbox" / "Hyperspace",
                          machine=a, tmp=tmp_path)
    library._missing.discard(tmp_path / "Dropbox" / "Hyperspace")


def test_a_missing_library_is_said_and_never_created(gone):
    lib = gone.lib
    assert lib.missing == gone.root
    text = library.missing_text(gone.root)
    assert lib.warning == text
    assert "fix [library] path or the folder, then restart" in text
    assert not (gone.tmp / "Dropbox").exists()


def test_a_missing_library_lists_only_the_factory(gone):
    lib = gone.lib
    factory = sorted((json.loads(p.read_text())["name"]
                      for p in (FACTORY / PRESETS).glob("*.json")), key=str.lower)
    assert lib.list(PRESETS, hidden=True) == factory
    assert all(lib.is_factory(PRESETS, n) for n in lib.list(PRESETS))
    assert lib.project.factory and lib.project.name == "party"
    assert "party" in lib.project.list()


def test_every_write_into_a_missing_library_is_refused(gone):
    lib, rig = gone.lib, gone.rig
    name = lib.list(PRESETS)[0]
    for call in (lambda: rig.presets.save_as("NEW"),
                 lambda: lib.save_as("camera", "Wide"),
                 lambda: lib.delete(PRESETS, name),
                 lambda: lib.rename(PRESETS, name, "other"),
                 lambda: lib.hide(PRESETS, name),
                 lambda: lib.empty_trash(),
                 lambda: lib.project.save("mine"),
                 lambda: lib.project.write(),
                 lambda: library._write_json(gone.root / "presets" / "x.json", {})):
        with pytest.raises(LibraryError, match="shared library not found at"):
            call()
    assert library.to_trash(FACTORY / PRESETS / "party-trip.json", gone.root) is None
    assert not (gone.tmp / "Dropbox").exists()
    assert sorted(files(gone.machine)) == []                 # nothing in the home either


def test_a_bank_save_into_a_missing_library_is_said_not_raised(gone):
    """The bank's ⇧F-key save reports on the footer, as a full disk does."""
    lib = gone.lib
    lib.project.save_slot(0)
    assert "shared library not found" in (lib.error + lib.warning)
    assert not (gone.tmp / "Dropbox").exists()


def test_a_library_given_alone_is_created_as_today(tmp_path):
    """Only a library named beside a different machine home is 'missing':
    `Library(path)` alone makes its folder, as every existing test expects."""
    lib = Library(tmp_path / "new", period=0.0)
    assert lib.missing is None and (tmp_path / "new" / "projects").is_dir()


# ---------------------------------------------------------------- atomic writes

def test_a_write_is_atomic_and_leaves_no_temp_file(tmp_path, monkeypatch):
    path = tmp_path / "presets" / "a.json"
    library._write_text(path, "one\n")
    library._write_text(path, "two\n")
    assert path.read_text() == "two\n"
    assert [p.name for p in path.parent.iterdir()] == ["a.json"]

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(library.os, "replace", boom)
    with pytest.raises(LibraryError, match="a.json: disk full"):
        library._write_text(path, "three\n")
    assert path.read_text() == "two\n"                       # never half-written
    assert [p.name for p in path.parent.iterdir()] == ["a.json"]


def test_the_temp_file_is_never_a_preset(tmp_path, monkeypatch):
    """Mid-write, the temp file is dot-named and not ``*.json``: the
    library's globs (and a cloud client's filters) pass it by."""
    seen = []
    real = library.os.replace

    def spy(src, dst):
        seen.append(src)
        assert list((tmp_path / "presets").glob("*.json")) == []
        real(src, dst)

    monkeypatch.setattr(library.os, "replace", spy)
    library._write_text(tmp_path / "presets" / "a.json", "{}\n")
    assert seen[0].name.startswith(".a.json.") and seen[0].suffix == ".tmp"


# ---------------------------------------------------------------- conflict copies

def test_a_cloud_conflict_copy_is_listed_beside_its_file(tmp_path):
    rig = make(tmp_path)
    lib = rig.lib
    path = rig.presets.save_as("HI FREK")
    doc = json.loads(path.read_text())
    copy = path.parent / "hi-frek (Dan's conflicted copy 2026-10-14).json"
    copy.write_text(json.dumps({**doc, "note": "Dan's"}))
    names = lib.list(PRESETS)
    assert "HI FREK" in names and copy.stem in names
    assert lib.path_of(PRESETS, "HI FREK") == path
    assert lib.path_of(PRESETS, copy.stem) == copy
    # it loads, renames and deletes as its own entry
    rig.presets.load(copy.stem)
    lib.rename(PRESETS, copy.stem, "HI FREK DAN")
    assert "HI FREK DAN" in lib.list(PRESETS) and not copy.exists()
    assert lib.delete(PRESETS, "HI FREK DAN")
    assert lib.list(PRESETS).count("HI FREK") == 1


def test_two_files_of_one_name_neither_canonical_both_list(tmp_path):
    rig = make(tmp_path)
    folder = tmp_path / "camera"
    folder.mkdir()
    for stem in ("b-copy", "a-copy"):
        (folder / f"{stem}.json").write_text(json.dumps(
            {"schema": "hyperspace.preset/1", "group": "camera", "name": "Wide",
             "values": {}}))
    idx = rig.lib._index("camera")
    assert idx["Wide"] == folder / "a-copy.json" and idx["b-copy"] == folder / "b-copy.json"


def test_a_user_file_still_shadows_the_factorys_of_its_name(tmp_path):
    """Across the roots nothing changes: one entry, the user's file."""
    rig = make(tmp_path)
    user = tmp_path / "band" / "balanced.json"
    user.parent.mkdir()
    user.write_text((FACTORY / "band" / "balanced.json").read_text())
    assert rig.lib.list("band").count("Balanced") == 1
    assert rig.lib.path_of("band", "Balanced") == user


# ---------------------------------------------------------------- migrations

def _boot_split(machine, root):
    """test_migration.boot's order, the library apart from the machine home."""
    from hyperspace import lfo, preset, tempo
    from hyperspace.fx import FxState
    from hyperspace.lookback import DreamState
    from hyperspace.routing import bindings_path

    chain = Analyzer(Analyser())
    control = Control(chain)
    lib = Library(root, machine=machine, period=0.0)
    reg = build_registry(ViewState(), control, SimpleNamespace(chain=chain), lib.project,
                         dream=DreamState(), fx=FxState())
    lib.on_layout("band", control.apply_layout)
    control.library = lib
    clock = tempo.Clock(now=lambda: 0.0)
    tempo.register(reg, clock)
    lfo.register(reg, lfo.LFOs(), clock)
    lib.attach(reg)
    router = Router(reg, Bindings.load(bindings_path(machine), legacy_midi=None))
    Presets(lib, reg, router)
    return lib, preset.migrate_home(lib, router)


def test_the_migration_reads_machine_files_and_writes_documents_to_the_library(tmp_path):
    """A legacy bindings/ folder and a schema-2 bindings.json in the machine
    home, the library elsewhere: the presets land in the library; in the
    machine home only bindings.json is rewritten (beside its backup, and
    the legacy folder's NOT-READ note) — no preset or show is written there."""
    from test_migration import owners_home

    machine, root = tmp_path / "A", tmp_path / "L"
    machine.mkdir()
    root.mkdir()
    owners_home(machine, project=False)
    (machine / "projects").rmdir()
    before = {p: p.read_bytes() for p in machine.rglob("*") if p.is_file()}
    lib, notes = _boot_split(machine, root)
    assert any("bindings/show-a.json → preset" in n for n in notes)
    assert (root / PRESETS / "show-a.json").is_file()
    assert (root / PRESETS / "migrated.json").is_file()
    after = {p: p.read_bytes() for p in machine.rglob("*") if p.is_file()}
    changed = {str(p.relative_to(machine)) for p in after if before.get(p) != after[p]}
    assert "bindings.json" in changed
    assert all(c == "bindings.json" or c.startswith("bindings.json.bak-")
               or c == "bindings/NOT-READ.txt" for c in changed), changed
    assert not (machine / PRESETS).exists() and not (machine / "projects").exists()
    assert {p for p in before if p not in after} == set()


def test_the_migration_does_nothing_when_the_library_is_missing(tmp_path):
    from test_migration import owners_home

    machine = tmp_path / "A"
    machine.mkdir()
    owners_home(machine, project=False)
    before = {p: p.read_bytes() for p in machine.rglob("*") if p.is_file()}
    lib, notes = _boot_split(machine, tmp_path / "gone")
    library._missing.discard(tmp_path / "gone")
    assert notes == []
    assert {p: p.read_bytes() for p in machine.rglob("*") if p.is_file()} == before
    assert not (tmp_path / "gone").exists()
