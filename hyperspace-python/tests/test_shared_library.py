"""Plan 25: the shared library folder — `[library] path` puts the library
(loadable patches, shows, module groups, the trash) in a folder of its own, the machine files stay in the home, a missing folder is never created
and refuses every write, writes are atomic, and a cloud client's conflict
copy is listed beside the file it copies.

Every test is on tmp_path; nothing here touches ~/Hyperspace.
"""

import json
from types import SimpleNamespace

import pytest
from conftest import CORPUS

from hyperspace import library
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.library import LAST_INSTALL, LOADABLE, Library, LibraryError
from hyperspace.loadable import LoadedPatch
from hyperspace.params import build_registry
from hyperspace.routing import Bindings, Router
from hyperspace.view import ViewState


def make(root, machine=None):
    chain = Analyzer(Analyser())
    control = Control(chain)
    view = ViewState()
    lib = Library(root, machine=machine, period=0.0)
    reg = build_registry(view, control, SimpleNamespace(chain=chain), lib.install)
    lib.attach(reg)
    loaded_patch = LoadedPatch(lib, reg, Router(reg, Bindings()))
    return SimpleNamespace(lib=lib, reg=reg, loaded_patch=loaded_patch, chain=chain)


def files(folder):
    return sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if p.is_file())


# ---------------------------------------------------------------- the split

def test_no_machine_is_todays_library(tmp_path):
    """`Library(home)` alone: the machine home is the library root."""
    lib = Library(tmp_path, period=0.0)
    assert lib.machine == lib.home == tmp_path and lib.missing is None
    lib.remember("party")
    assert (tmp_path / LAST_INSTALL).read_text() == "party\n"


def test_a_save_lands_in_the_library_and_last_show_in_the_machine_home(tmp_path):
    """The acceptance demo: machine home A plus library L — a loadable patch save
    writes L/presets and nothing new in A but last_show; then L is gone, a
    relaunch warns, refuses saves, and creates nothing."""
    a, lib_root = tmp_path / "A", tmp_path / "L"
    a.mkdir()
    lib_root.mkdir()
    before = files(a)
    rig = make(lib_root, machine=a)
    assert rig.lib.home == lib_root and rig.lib.machine == a and rig.lib.missing is None
    path = rig.loaded_patch.save_as("HI FREK")
    assert path == lib_root / LOADABLE / "hi-frek.json" and path.is_file()
    rig.lib.install.save("mine")
    assert (lib_root / "installs" / "mine.json").is_file()
    assert sorted(set(files(a)) - set(before)) == [LAST_INSTALL]
    assert (a / LAST_INSTALL).read_text() == "mine\n"
    assert not (lib_root / LAST_INSTALL).exists()

    # the folder goes away (a cloud drive unmounted): relaunch
    for p in sorted(lib_root.rglob("*"), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
    lib_root.rmdir()
    rig = make(lib_root, machine=a)
    assert rig.lib.missing == lib_root
    assert "shared library not found at" in rig.lib.warning
    # an unsaved show stands in: nothing read, nothing to list
    assert rig.lib.install.name == "untitled" and rig.lib.install.path is None
    assert rig.lib.list(LOADABLE) == [] and rig.lib.install.list() == []
    with pytest.raises(LibraryError, match="not saved; fix \\[library\\] path"):
        rig.loaded_patch.save_as("HI FREK 2")
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


def test_a_missing_library_lists_nothing(gone):
    """One tier (2026-10-28): nothing ships with the app, so a missing
    library lists nothing and opens the unsaved `untitled` show."""
    lib = gone.lib
    assert lib.list(LOADABLE) == [] and all(lib.list(g) == [] for g in lib.groups())
    assert lib.install.name == "untitled" and lib.install.path is None
    assert lib.install.bank == [None] * 24 and lib.install.startup is None
    assert lib.install.list() == []
    assert lib.current(LOADABLE) is None


def test_every_write_into_a_missing_library_is_refused(gone):
    lib, rig = gone.lib, gone.rig
    name = "TUMBLE"                     # (refused before it is even looked for)
    for call in (lambda: rig.loaded_patch.save_as("NEW"),
                 lambda: lib.save_as("camera", "Wide"),
                 lambda: lib.delete(LOADABLE, name),
                 lambda: lib.rename(LOADABLE, name, "other"),
                 lambda: lib.empty_trash(),
                 lambda: lib.install.save("mine"),
                 lambda: lib.install.write(),
                 lambda: library._write_json(gone.root / "loadable" / "x.json", {})):
        with pytest.raises(LibraryError, match="shared library not found at"):
            call()
    assert library.to_trash(CORPUS / LOADABLE / "party-trip.json", gone.root) is None
    assert not (gone.tmp / "Dropbox").exists()
    assert sorted(files(gone.machine)) == []                 # nothing in the home either


def test_a_bank_save_into_a_missing_library_is_said_not_raised(gone):
    """The bank's ⇧F-key save reports on the footer, as a full disk does."""
    lib = gone.lib
    lib.install.save_slot(0)
    assert "shared library not found" in (lib.error + lib.warning)
    assert not (gone.tmp / "Dropbox").exists()


def test_a_library_given_alone_is_created_as_today(tmp_path):
    """Only a library named beside a different machine home is 'missing':
    `Library(path)` alone makes its folder, as every existing test expects."""
    lib = Library(tmp_path / "new", period=0.0)
    assert lib.missing is None and (tmp_path / "new" / "installs").is_dir()


def test_the_system_page_says_where_the_library_is(tmp_path, gone):
    from hyperspace.ui import Panel

    def lines(lib):
        return Panel.library_lines(SimpleNamespace(library=lib))

    assert lines(Library(tmp_path / "home", period=0.0)) == [
        (f"library: {tmp_path / 'home'}", False)]
    (tmp_path / "L").mkdir()
    assert lines(Library(tmp_path / "L", machine=gone.machine, period=0.0)) == [
        (f"library: {tmp_path / 'L'}", False), (f"machine: {gone.machine}", False)]
    assert lines(gone.lib) == [
        (f"library: {gone.root} — NOT FOUND, saves are off (restart once it is there)", True),
        (f"machine: {gone.machine}", False)]


# ---------------------------------------------------------------- atomic writes

def test_a_write_is_atomic_and_leaves_no_temp_file(tmp_path, monkeypatch):
    path = tmp_path / "loadable" / "a.json"
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


def test_the_temp_file_is_never_a_loadable(tmp_path, monkeypatch):
    """Mid-write, the temp file is dot-named and not ``*.json``: the
    library's globs (and a cloud client's filters) pass it by."""
    seen = []
    real = library.os.replace

    def spy(src, dst):
        seen.append(src)
        assert list((tmp_path / "loadable").glob("*.json")) == []
        real(src, dst)

    monkeypatch.setattr(library.os, "replace", spy)
    library._write_text(tmp_path / "loadable" / "a.json", "{}\n")
    assert seen[0].name.startswith(".a.json.") and seen[0].suffix == ".tmp"


# ---------------------------------------------------------------- conflict copies

def test_a_cloud_conflict_copy_is_listed_beside_its_file(tmp_path):
    rig = make(tmp_path)
    lib = rig.lib
    path = rig.loaded_patch.save_as("HI FREK")
    doc = json.loads(path.read_text())
    copy = path.parent / "hi-frek (Dan's conflicted copy 2026-10-14).json"
    copy.write_text(json.dumps({**doc, "note": "Dan's"}))
    names = lib.list(LOADABLE)
    assert "HI FREK" in names and copy.stem in names
    assert lib.path_of(LOADABLE, "HI FREK") == path
    assert lib.path_of(LOADABLE, copy.stem) == copy
    # it loads, renames and deletes as its own entry
    rig.loaded_patch.load(copy.stem)
    lib.rename(LOADABLE, copy.stem, "HI FREK DAN")
    assert "HI FREK DAN" in lib.list(LOADABLE) and not copy.exists()
    assert lib.delete(LOADABLE, "HI FREK DAN")
    assert lib.list(LOADABLE).count("HI FREK") == 1


def test_two_files_of_one_name_neither_canonical_both_list(tmp_path):
    rig = make(tmp_path)
    folder = tmp_path / "patches" / "camera"
    folder.mkdir(parents=True)
    for stem in ("b-copy", "a-copy"):
        (folder / f"{stem}.json").write_text(json.dumps(
            {"schema": "hyperspace.preset/1", "group": "camera", "name": "Wide",
             "values": {}}))
    idx = rig.lib._index("camera")
    assert idx["Wide"] == folder / "a-copy.json" and idx["b-copy"] == folder / "b-copy.json"
