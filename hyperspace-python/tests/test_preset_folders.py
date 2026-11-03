"""Plan 48: preset folders, stage 1 — the library lists presets every
folder down under ``presets/``, a preset's name is folder-qualified
(``party/B``), the bank points at a preset by that name (a bare name is a
top-level file, so every older show reads as it did), a save writes back
where the preset came from and a two-handed save lands beside it, and the
trash is this Mac's (``<machine>/trash``), never in the synced library.

Every test runs over a temp library and a temp machine home; nothing here
touches ~/Hyperspace or a Drive folder.
"""

import json
from types import SimpleNamespace

import pytest
from conftest import CORPUS

from hyperspace import library
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.library import (
    PRESETS,
    PROJECT_SCHEMA,
    Library,
    LibraryError,
    path_slug,
    slug,
)
from hyperspace.params import build_registry
from hyperspace.preset import Presets
from hyperspace.routing import Bindings, Router
from hyperspace.view import ViewState

DIAL = CORPUS / PRESETS / "dial.json"


def _put(path, name):
    doc = json.loads(DIAL.read_text())
    doc["name"] = name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1) + "\n")


def tree(folder):
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file())


@pytest.fixture()
def lib_dirs(tmp_path):
    """A library L (the "Drive" folder) and a machine home M: presets
    ``a``, ``party/B``, ``party/deep/C``, a hidden ``.cache/x.json``, and a
    cloud client's conflict copy of ``party/B``; a show whose bank names
    ``A`` bare and ``party/B``."""
    root, machine = tmp_path / "L", tmp_path / "M"
    machine.mkdir()
    p = root / PRESETS
    _put(p / "a.json", "A")
    _put(p / "party" / "b.json", "B")
    _put(p / "party" / "b (Dan's conflicted copy).json", "B")
    _put(p / "party" / "deep" / "c.json", "C")
    _put(p / ".cache" / "x.json", "X")
    (root / "projects").mkdir(parents=True)
    show = {"schema": PROJECT_SCHEMA, "name": "night", "startup": "A",
            "bank": ["A", "party/B", None, None, None, None, None, None]}
    (root / "projects" / "night.hyp.json").write_text(json.dumps(show))
    (machine / "last_show").write_text("night\n")
    return SimpleNamespace(root=root, machine=machine, presets=p)


def make(d):
    chain = Analyzer(Analyser())
    control = Control(chain)
    lib = Library(d.root, machine=d.machine, period=0.0)
    reg = build_registry(ViewState(), control, SimpleNamespace(chain=chain), lib.project)
    lib.attach(reg)
    presets = Presets(lib, reg, Router(reg, Bindings()))
    return SimpleNamespace(lib=lib, reg=reg, presets=presets)


# ---------------------------------------------------------------- the listing

def test_the_list_is_every_folder_down_by_qualified_name(lib_dirs):
    r = make(lib_dirs)
    listing = r.lib.list(PRESETS)
    assert "A" in listing and "party/B" in listing and "party/deep/C" in listing
    # the conflict copy keeps plan 25's rule, in its folder: listed by its stem
    assert "party/b (Dan's conflicted copy)" in listing
    assert not [n for n in listing if "X" in n or "cache" in n]   # a hidden folder is no preset
    assert len(listing) == 4
    p = lib_dirs.presets
    assert r.lib.path_of(PRESETS, "A") == p / "a.json"
    assert r.lib.path_of(PRESETS, "party/B") == p / "party" / "b.json"
    assert r.lib.path_of(PRESETS, "party/b") == p / "party" / "b.json"       # by its path
    assert r.lib.path_of(PRESETS, "party/deep/C") == p / "party" / "deep" / "c.json"
    assert r.lib.path_of(PRESETS, "B") is None                 # a bare name is the top level
    # module groups, shows and the trash are not presets: none is listed
    assert r.lib.groups().count(PRESETS) == 1 and "party" not in r.lib.groups()


def test_a_name_never_reaches_outside_the_presets_folder(lib_dirs):
    with pytest.raises(LibraryError):
        path_slug("../x")
    with pytest.raises(LibraryError):
        path_slug("/etc/passwd")
    with pytest.raises(LibraryError):
        path_slug("party/../../x")
    with pytest.raises(LibraryError):
        path_slug(".cache/x")
    assert path_slug("party/TRIP 2") == "party/trip-2" and path_slug("TRIP 2") == "trip-2"
    assert slug("party/TRIP") == "party-trip"               # slug itself stays flat
    r = make(lib_dirs)
    assert r.lib.path_of(PRESETS, "../a") is None
    assert r.lib.path_of(PRESETS, "/etc/passwd") is None
    with pytest.raises(LibraryError):
        r.presets.save_as("../escape")
    assert not (lib_dirs.root / "escape.json").exists()


def test_a_load_and_save_round_trip_in_place(lib_dirs):
    r = make(lib_dirs)
    r.presets.load("party/deep/C")
    assert r.lib.current(PRESETS) == "party/deep/C"
    before = tree(lib_dirs.presets)
    path = r.lib.overwrite(PRESETS)
    assert path == lib_dirs.presets / "party" / "deep" / "c.json"
    assert json.loads(path.read_text())["name"] == "C"      # the file keeps the leaf
    assert tree(lib_dirs.presets) == before
    assert r.lib.current(PRESETS) == "party/deep/C" and not r.lib.is_dirty(PRESETS)


def test_a_save_as_a_qualified_name_writes_into_its_folder(lib_dirs):
    r = make(lib_dirs)
    path = r.presets.save_as("party/NEW ONE")
    assert path == lib_dirs.presets / "party" / "new-one.json"
    assert json.loads(path.read_text())["name"] == "NEW ONE"
    assert "party/NEW ONE" in r.lib.list(PRESETS)


def test_the_watcher_sees_a_subfolder(lib_dirs):
    r = make(lib_dirs)
    r.presets.load("party/B")
    path = lib_dirs.presets / "party" / "b.json"
    assert path in r.lib._scan()
    doc = json.loads(path.read_text())
    doc["note"] = "edited in an editor"
    path.write_text(json.dumps(doc))
    import os
    os.utime(path, (1, 1))
    assert r.lib.poll(now=10.0)
    assert "party/B" in r.lib.status


def test_rename_keeps_the_folder_and_repoints_the_show(lib_dirs):
    r = make(lib_dirs)
    pr = r.lib.project
    assert pr.bank[1] == "party/B"
    dst = r.lib.rename(PRESETS, "party/B", "BEE")
    assert dst == lib_dirs.presets / "party" / "bee.json"
    assert json.loads(dst.read_text())["name"] == "BEE"
    assert pr.bank[1] == "party/BEE" and pr.bank[0] == "A"
    shown = json.loads((lib_dirs.root / "projects" / "night.hyp.json").read_text())
    assert shown["bank"][1] == "party/BEE"
    # the folder may be spelled, as the list spells it; a move is refused
    assert r.lib.rename(PRESETS, "party/BEE", "party/BUZZ").name == "buzz.json"
    with pytest.raises(LibraryError, match="keeps the folder"):
        r.lib.rename(PRESETS, "party/BUZZ", "other/BUZZ")
    # a top-level name the same as a folder's leaf is not taken by it
    r.lib.rename(PRESETS, "A", "BUZZ")
    assert (lib_dirs.presets / "buzz.json").is_file()


# ---------------------------------------------------------------- the bank

def test_the_bank_holds_a_folder_preset_and_cycle_and_walk_reach_it(lib_dirs):
    r = make(lib_dirs)
    pr = r.lib.project
    pr.load_slot(1)
    assert r.lib.current(PRESETS) == "party/B" and pr.active == 1
    pr.cycle(1)
    assert r.lib.current(PRESETS) == "A" and pr.active == 0
    pr.cycle(1)
    assert r.lib.current(PRESETS) == "party/B"
    seen = {pr.walk(1) for _ in range(len(r.lib.list(PRESETS)))}
    assert {"party/deep/C", "party/B", "A"} <= seen
    pr.put_slot(2, "party/deep/C")
    assert pr.bank[2] == "party/deep/C"
    pr.load_slot(2)
    assert r.lib.current(PRESETS) == "party/deep/C"
    assert r.lib.still_named("party/deep/C") == ["F3"]
    assert r.lib.still_named("C") == []          # a bare C would be a top-level preset


def test_an_old_show_with_a_bare_name_still_loads_its_top_level_preset(lib_dirs):
    r = make(lib_dirs)
    pr = r.lib.project
    pr.load_startup()
    assert r.lib.current(PRESETS) == "A"
    pr.load_slot(0)
    assert r.lib.current(PRESETS) == "A" and pr.active == 0


def test_a_folder_slot_on_an_older_build_is_a_filled_slot_that_loads_nothing(lib_dirs):
    """What an older build does with ``party/B``: its lookup is the listed
    name, then the flat slug ``party-b`` — neither is a file, so the slot
    is filled and says "no preset" (the reason no schema bump is needed)."""
    files = {p.name[:-5]: p for p in lib_dirs.presets.glob("*.json")}     # the old, flat walk
    index = {json.loads(p.read_text())["name"]: p for p in files.values()}

    def old_path_of(name):                       # library.path_of before plan 48
        return index.get(name) or files.get(slug(name))

    assert old_path_of("party/B") is None and old_path_of("party/deep/C") is None
    assert old_path_of("A") == lib_dirs.presets / "a.json"     # a bare name: as ever


def test_the_two_handed_save_lands_beside_the_loaded_preset(lib_dirs):
    r = make(lib_dirs)
    pr = r.lib.project
    r.presets.load("party/deep/C")
    assert pr.save_into(5)
    assert pr.bank[5] == "party/deep/C 2"
    assert (lib_dirs.presets / "party" / "deep" / "c-2.json").is_file()
    assert r.lib.current(PRESETS) == "party/deep/C 2"
    # a top-level one lands at the top
    r.presets.load("A")
    assert pr.save_new()
    assert (lib_dirs.presets / "a-2.json").is_file() and "A 2" in pr.bank


# ---------------------------------------------------------------- the trash

def test_the_trash_is_this_macs_and_restore_returns_to_the_folder(lib_dirs):
    r = make(lib_dirs)
    lib = r.lib
    library_before = set(tree(lib_dirs.root)) - {"presets/party/deep/c.json"}
    assert lib.delete(PRESETS, "party/deep/C")
    kept = list((lib_dirs.machine / "trash" / "presets" / "party" / "deep").glob("c.*.json"))
    assert len(kept) == 1
    assert not (lib_dirs.root / "trash").exists()            # nothing under the library
    assert set(tree(lib_dirs.root)) == library_before
    (item,) = lib.trash()
    assert item.group == PRESETS and item.folder == "party/deep" and not item.old
    assert item.name == "party/deep/C"
    assert lib.restore_trash(item) == "party/deep/C"
    assert (lib_dirs.presets / "party" / "deep" / "c.json").is_file()
    assert lib.trash() == []
    # a save over a folder preset keeps the old text on this Mac too
    r.presets.load("party/B")
    path = lib_dirs.presets / "party" / "b.json"
    path.write_text(path.read_text() + "\n")       # its text is not what a save writes
    lib._sync(path)
    lib.overwrite(PRESETS)
    assert list((lib_dirs.machine / "trash" / "presets" / "party").glob("b.*.json"))
    assert not (lib_dirs.root / "trash").exists()


def test_a_restore_into_a_taken_name_takes_the_next_in_its_folder(lib_dirs):
    r = make(lib_dirs)
    lib = r.lib
    lib.delete(PRESETS, "party/deep/C")
    _put(lib_dirs.presets / "party" / "deep" / "c.json", "C")    # a new C since
    (item,) = lib.trash()
    assert lib.restore_trash(item) == "party/deep/C 2"
    assert (lib_dirs.presets / "party" / "deep" / "c-2.json").is_file()


def test_empty_removes_only_this_macs_trash_and_lists_the_old_one(lib_dirs):
    r = make(lib_dirs)
    lib = r.lib
    old = lib_dirs.root / "trash" / "presets" / "gone.20261001-120000.json"
    old.parent.mkdir(parents=True)
    old.write_text(json.dumps({"name": "GONE"}))
    lib.delete(PRESETS, "party/B")
    listed = lib.trash()
    assert [t.old for t in listed] == [False, True]
    assert listed[1].name == "GONE"
    assert lib.empty_trash() == 1
    assert old.is_file()                                     # the library's own: left
    assert not (lib_dirs.machine / "trash" / "presets" / "party").exists()
    # the old one restores as a copy: the shared folder's trash is never written
    before = old.read_bytes()
    assert lib.restore_trash(lib.trash()[0]) == "GONE"
    assert (lib_dirs.presets / "gone.json").is_file()
    assert old.read_bytes() == before and lib.trash()[0].old


# ---------------------------------------------------------------- review fixes

def test_a_slash_in_a_files_own_name_is_never_a_folder(lib_dirs):
    """Review 1, 5, 6 (the ruling): a top-level file whose own name holds a
    `/` is listed with it made " - "; the row, the rename seed and the
    two-handed save all read it as top-level; an old show naming it
    `Ac/Dc` still finds it."""
    _put(lib_dirs.presets / "ac-dc.json", "AC/DC")
    r = make(lib_dirs)
    lib, pr = r.lib, r.lib.project
    assert "AC - DC" in lib.list(PRESETS) and "AC/DC" not in lib.list(PRESETS)
    assert lib.folder_of(PRESETS, "AC - DC") == ("", "AC - DC")
    assert lib.path_of(PRESETS, "Ac/Dc") == lib_dirs.presets / "ac-dc.json"   # an old show
    pr.bank[3] = "Ac/Dc"
    pr.load_slot(3)
    assert lib.current(PRESETS) == "AC - DC"
    assert pr.save_into(4)
    assert pr.bank[4] == "AC - DC 2" and (lib_dirs.presets / "ac-dc-2.json").is_file()
    assert not (lib_dirs.presets / "AC").exists() and not (lib_dirs.presets / "ac").exists()
    lib.overwrite(PRESETS)                                  # writes the shown name back
    assert json.loads((lib_dirs.presets / "ac-dc-2.json").read_text())["name"] == "AC - DC 2"
    lib.rename(PRESETS, "AC - DC", "AC - DC LIVE")
    assert (lib_dirs.presets / "ac-dc-live.json").is_file()


def test_one_fold_a_folder_with_a_trailing_space_counts_on(lib_dirs):
    """Review 2: the two-handed save in a folder whose name ends in a space
    makes TRIP 3 when TRIP 2 is there, never writes over TRIP 2."""
    folder = lib_dirs.presets / "late "
    _put(folder / "trip.json", "TRIP")
    _put(folder / "trip-2.json", "TRIP 2")
    r = make(lib_dirs)
    r.presets.load("late /TRIP")
    two = (folder / "trip-2.json").read_text()
    assert r.lib.project.save_into(6)
    assert (folder / "trip-3.json").is_file() and (folder / "trip-2.json").read_text() == two


def test_a_conflict_loser_is_listed_in_its_own_folder(lib_dirs):
    """Review 3: the loser of a name clash is re-listed under its own
    folder's prefix, and resolves to its own file."""
    r = make(lib_dirs)
    loser = lib_dirs.presets / "party" / "b (Dan's conflicted copy).json"
    assert r.lib.path_of(PRESETS, "party/b (Dan's conflicted copy)") == loser


def test_a_folder_named_in_another_case_is_the_folder_on_disk(lib_dirs):
    """Review 4: `Party/B` finds `party/b.json`; a save as `Party/NEW` lands
    in `party/` and is listed with the folder as it is on disk."""
    r = make(lib_dirs)
    assert r.lib.path_of(PRESETS, "Party/B") == lib_dirs.presets / "party" / "b.json"
    assert r.lib.path_of(PRESETS, "PARTY/DEEP/c") == lib_dirs.presets / "party" / "deep" / "c.json"
    r.presets.save_as("Party/NEW")
    assert r.lib.current(PRESETS) == "party/NEW" and "party/NEW" in r.lib.list(PRESETS)
    assert sorted(p.name for p in lib_dirs.presets.iterdir() if p.is_dir()) == [".cache", "party"]


def test_the_presets_walk_is_kept_until_a_folder_moves(lib_dirs, monkeypatch):
    """Review 8: two listings in a row walk the tree once; a file added
    in a subfolder is seen on the next."""
    r = make(lib_dirs)
    walks = []
    real = library.os.walk
    monkeypatch.setattr(library.os, "walk", lambda *a, **k: (walks.append(a[0]), real(*a, **k))[1])
    r.lib._walks.clear()
    r.lib.list(PRESETS)
    r.lib.list(PRESETS)
    r.lib.path_of(PRESETS, "party/B")
    r.lib.is_dirty(PRESETS)
    assert len(walks) == 1
    _put(lib_dirs.presets / "party" / "deep" / "d.json", "D")
    assert "party/deep/D" in r.lib.list(PRESETS)


def test_one_folder_is_one_library_and_trash(tmp_path):
    """No [library] path: the machine home is the library, and its trash is
    the one there always was — no "old" trash."""
    _put(tmp_path / PRESETS / "party" / "b.json", "B")
    lib = Library(tmp_path, period=0.0)
    assert lib._old_trash() is None and lib._trash_dir() == tmp_path / "trash"
    assert library.to_trash(tmp_path / PRESETS / "party" / "b.json", tmp_path,
                            "presets/party").parent == tmp_path / "trash" / "presets" / "party"
