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
import os
from types import SimpleNamespace

import pytest
from conftest import CORPUS

from hyperspace import library
from hyperspace.analysis import Analyser
from hyperspace.analyzer import Analyzer
from hyperspace.control import Control
from hyperspace.library import (
    LOADABLE,
    PROJECT_SCHEMA,
    Library,
    LibraryError,
    path_slug,
    slug,
)
from hyperspace.params import build_registry
from hyperspace.preset import LoadedPatch
from hyperspace.routing import Bindings, Router
from hyperspace.view import ViewState

DIAL = CORPUS / LOADABLE / "dial.json"


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
    p = root / LOADABLE
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
    return SimpleNamespace(root=root, machine=machine, loaded_patch=p)


def make(d):
    chain = Analyzer(Analyser())
    control = Control(chain)
    lib = Library(d.root, machine=d.machine, period=0.0)
    reg = build_registry(ViewState(), control, SimpleNamespace(chain=chain), lib.project)
    lib.attach(reg)
    loaded_patch = LoadedPatch(lib, reg, Router(reg, Bindings()))
    return SimpleNamespace(lib=lib, reg=reg, loaded_patch=loaded_patch)


# ---------------------------------------------------------------- the listing

def test_the_list_is_every_folder_down_by_qualified_name(lib_dirs):
    r = make(lib_dirs)
    listing = r.lib.list(LOADABLE)
    assert "A" in listing and "party/B" in listing and "party/deep/C" in listing
    # the conflict copy keeps plan 25's rule, in its folder: listed by its stem
    assert "party/b (Dan's conflicted copy)" in listing
    assert not [n for n in listing if "X" in n or "cache" in n]   # a hidden folder is no preset
    assert len(listing) == 4
    p = lib_dirs.loaded_patch
    assert r.lib.path_of(LOADABLE, "A") == p / "a.json"
    assert r.lib.path_of(LOADABLE, "party/B") == p / "party" / "b.json"
    assert r.lib.path_of(LOADABLE, "party/b") == p / "party" / "b.json"       # by its path
    assert r.lib.path_of(LOADABLE, "party/deep/C") == p / "party" / "deep" / "c.json"
    assert r.lib.path_of(LOADABLE, "B") is None                 # a bare name is the top level
    # module groups, shows and the trash are not presets: none is listed
    assert r.lib.groups().count(LOADABLE) == 1 and "party" not in r.lib.groups()


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
    assert r.lib.path_of(LOADABLE, "../a") is None
    assert r.lib.path_of(LOADABLE, "/etc/passwd") is None
    with pytest.raises(LibraryError):
        r.loaded_patch.save_as("../escape")
    assert not (lib_dirs.root / "escape.json").exists()


def test_a_load_and_save_round_trip_in_place(lib_dirs):
    r = make(lib_dirs)
    r.loaded_patch.load("party/deep/C")
    assert r.lib.current(LOADABLE) == "party/deep/C"
    before = tree(lib_dirs.loaded_patch)
    path = r.lib.overwrite(LOADABLE)
    assert path == lib_dirs.loaded_patch / "party" / "deep" / "c.json"
    assert json.loads(path.read_text())["name"] == "C"      # the file keeps the leaf
    assert tree(lib_dirs.loaded_patch) == before
    assert r.lib.current(LOADABLE) == "party/deep/C" and not r.lib.is_dirty(LOADABLE)


def test_a_save_as_a_qualified_name_writes_into_its_folder(lib_dirs):
    r = make(lib_dirs)
    path = r.loaded_patch.save_as("party/NEW ONE")
    assert path == lib_dirs.loaded_patch / "party" / "new-one.json"
    assert json.loads(path.read_text())["name"] == "NEW ONE"
    assert "party/NEW ONE" in r.lib.list(LOADABLE)


def test_the_watcher_sees_a_subfolder(lib_dirs):
    r = make(lib_dirs)
    r.loaded_patch.load("party/B")
    path = lib_dirs.loaded_patch / "party" / "b.json"
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
    dst = r.lib.rename(LOADABLE, "party/B", "BEE")
    assert dst == lib_dirs.loaded_patch / "party" / "bee.json"
    assert json.loads(dst.read_text())["name"] == "BEE"
    assert pr.bank[1] == "party/BEE" and pr.bank[0] == "A"
    shown = json.loads((lib_dirs.root / "projects" / "night.hyp.json").read_text())
    assert shown["bank"][1] == "party/BEE"
    # the folder may be spelled, as the list spells it; a move is refused
    assert r.lib.rename(LOADABLE, "party/BEE", "party/BUZZ").name == "buzz.json"
    with pytest.raises(LibraryError, match="keeps the folder"):
        r.lib.rename(LOADABLE, "party/BUZZ", "other/BUZZ")
    # a top-level name the same as a folder's leaf is not taken by it
    r.lib.rename(LOADABLE, "A", "BUZZ")
    assert (lib_dirs.loaded_patch / "buzz.json").is_file()


# ---------------------------------------------------------------- the bank

def test_the_bank_holds_a_folder_preset_and_cycle_and_walk_reach_it(lib_dirs):
    r = make(lib_dirs)
    pr = r.lib.project
    pr.load_slot(1)
    assert r.lib.current(LOADABLE) == "party/B" and pr.active == 1
    pr.cycle(1)
    assert r.lib.current(LOADABLE) == "A" and pr.active == 0
    pr.cycle(1)
    assert r.lib.current(LOADABLE) == "party/B"
    seen = {pr.walk(1) for _ in range(len(r.lib.list(LOADABLE)))}
    assert {"party/deep/C", "party/B", "A"} <= seen
    pr.put_slot(2, "party/deep/C")
    assert pr.bank[2] == "party/deep/C"
    pr.load_slot(2)
    assert r.lib.current(LOADABLE) == "party/deep/C"
    assert r.lib.still_named("party/deep/C") == ["F3"]
    assert r.lib.still_named("C") == []          # a bare C would be a top-level preset


def test_an_old_show_with_a_bare_name_still_loads_its_top_level_preset(lib_dirs):
    r = make(lib_dirs)
    pr = r.lib.project
    pr.load_startup()
    assert r.lib.current(LOADABLE) == "A"
    pr.load_slot(0)
    assert r.lib.current(LOADABLE) == "A" and pr.active == 0


def test_a_folder_slot_on_an_older_build_is_a_filled_slot_that_loads_nothing(lib_dirs):
    """What an older build does with ``party/B``: its lookup is the listed
    name, then the flat slug ``party-b`` — neither is a file, so the slot
    is filled and says "no preset" (the reason no schema bump is needed)."""
    files = {p.name[:-5]: p for p in lib_dirs.loaded_patch.glob("*.json")}     # the old, flat walk
    index = {json.loads(p.read_text())["name"]: p for p in files.values()}

    def old_path_of(name):                       # library.path_of before plan 48
        return index.get(name) or files.get(slug(name))

    assert old_path_of("party/B") is None and old_path_of("party/deep/C") is None
    assert old_path_of("A") == lib_dirs.loaded_patch / "a.json"     # a bare name: as ever


def test_the_two_handed_save_lands_beside_the_loaded_preset(lib_dirs):
    r = make(lib_dirs)
    pr = r.lib.project
    r.loaded_patch.load("party/deep/C")
    assert pr.save_into(5)
    assert pr.bank[5] == "party/deep/C 2"
    assert (lib_dirs.loaded_patch / "party" / "deep" / "c-2.json").is_file()
    assert r.lib.current(LOADABLE) == "party/deep/C 2"
    # a top-level one lands at the top
    r.loaded_patch.load("A")
    assert pr.save_new()
    assert (lib_dirs.loaded_patch / "a-2.json").is_file() and "A 2" in pr.bank


# ---------------------------------------------------------------- the trash

def test_the_trash_is_this_macs_and_restore_returns_to_the_folder(lib_dirs):
    r = make(lib_dirs)
    lib = r.lib
    library_before = set(tree(lib_dirs.root)) - {"presets/party/deep/c.json"}
    assert lib.delete(LOADABLE, "party/deep/C")
    kept = list((lib_dirs.machine / "trash" / "presets" / "party" / "deep").glob("c.*.json"))
    assert len(kept) == 1
    assert not (lib_dirs.root / "trash").exists()            # nothing under the library
    assert set(tree(lib_dirs.root)) == library_before
    (item,) = lib.trash()
    assert item.group == LOADABLE and item.folder == "party/deep" and not item.old
    assert item.name == "party/deep/C"
    assert lib.restore_trash(item) == "party/deep/C"
    assert (lib_dirs.loaded_patch / "party" / "deep" / "c.json").is_file()
    assert lib.trash() == []
    # a save over a folder preset keeps the old text on this Mac too
    r.loaded_patch.load("party/B")
    path = lib_dirs.loaded_patch / "party" / "b.json"
    path.write_text(path.read_text() + "\n")       # its text is not what a save writes
    lib._sync(path)
    lib.overwrite(LOADABLE)
    assert list((lib_dirs.machine / "trash" / "presets" / "party").glob("b.*.json"))
    assert not (lib_dirs.root / "trash").exists()


def test_a_restore_into_a_taken_name_takes_the_next_in_its_folder(lib_dirs):
    r = make(lib_dirs)
    lib = r.lib
    lib.delete(LOADABLE, "party/deep/C")
    _put(lib_dirs.loaded_patch / "party" / "deep" / "c.json", "C")    # a new C since
    (item,) = lib.trash()
    assert lib.restore_trash(item) == "party/deep/C 2"
    assert (lib_dirs.loaded_patch / "party" / "deep" / "c-2.json").is_file()


def test_empty_removes_only_this_macs_trash_and_lists_the_old_one(lib_dirs):
    r = make(lib_dirs)
    lib = r.lib
    old = lib_dirs.root / "trash" / "presets" / "gone.20261001-120000.json"
    old.parent.mkdir(parents=True)
    old.write_text(json.dumps({"name": "GONE"}))
    lib.delete(LOADABLE, "party/B")
    listed = lib.trash()
    assert [t.old for t in listed] == [False, True]
    assert listed[1].name == "GONE"
    assert lib.empty_trash() == 1
    assert old.is_file()                                     # the library's own: left
    assert not (lib_dirs.machine / "trash" / "presets" / "party").exists()
    # the old one restores as a copy: the shared folder's trash is never written
    before = old.read_bytes()
    assert lib.restore_trash(lib.trash()[0]) == "GONE"
    assert (lib_dirs.loaded_patch / "gone.json").is_file()
    assert old.read_bytes() == before and lib.trash()[0].old


# ---------------------------------------------------------------- review fixes

def test_a_slash_in_a_files_own_name_is_never_a_folder(lib_dirs):
    """Review 1, 5, 6 (the ruling): a top-level file whose own name holds a
    `/` is listed with it made " - "; the row, the rename seed and the
    two-handed save all read it as top-level; an old show naming it
    `Ac/Dc` still finds it."""
    _put(lib_dirs.loaded_patch / "ac-dc.json", "AC/DC")
    r = make(lib_dirs)
    lib, pr = r.lib, r.lib.project
    assert "AC - DC" in lib.list(LOADABLE) and "AC/DC" not in lib.list(LOADABLE)
    assert lib.folder_of(LOADABLE, "AC - DC") == ("", "AC - DC")
    # an old show's spelling: a read finds it, a writer never does (review 2, item 1)
    assert lib.path_of(LOADABLE, "Ac/Dc", loose=True) == lib_dirs.loaded_patch / "ac-dc.json"
    assert lib.path_of(LOADABLE, "Ac/Dc") is None
    pr.bank[3] = "Ac/Dc"
    pr.load_slot(3)
    assert lib.current(LOADABLE) == "AC - DC"
    assert pr.save_into(4)
    assert pr.bank[4] == "AC - DC 2" and (lib_dirs.loaded_patch / "ac-dc-2.json").is_file()
    assert not (lib_dirs.loaded_patch / "AC").exists() and not (lib_dirs.loaded_patch / "ac").exists()
    lib.overwrite(LOADABLE)                                  # writes the shown name back
    assert json.loads((lib_dirs.loaded_patch / "ac-dc-2.json").read_text())["name"] == "AC - DC 2"
    lib.rename(LOADABLE, "AC - DC", "AC - DC LIVE")
    assert (lib_dirs.loaded_patch / "ac-dc-live.json").is_file()


def test_one_fold_a_folder_with_a_trailing_space_counts_on(lib_dirs):
    """Review 2: the two-handed save in a folder whose name ends in a space
    makes TRIP 3 when TRIP 2 is there, never writes over TRIP 2."""
    folder = lib_dirs.loaded_patch / "late "
    _put(folder / "trip.json", "TRIP")
    _put(folder / "trip-2.json", "TRIP 2")
    r = make(lib_dirs)
    r.loaded_patch.load("late /TRIP")
    two = (folder / "trip-2.json").read_text()
    assert r.lib.project.save_into(6)
    assert (folder / "trip-3.json").is_file() and (folder / "trip-2.json").read_text() == two


def test_a_conflict_loser_is_listed_in_its_own_folder(lib_dirs):
    """Review 3: the loser of a name clash is re-listed under its own
    folder's prefix, and resolves to its own file."""
    r = make(lib_dirs)
    loser = lib_dirs.loaded_patch / "party" / "b (Dan's conflicted copy).json"
    assert r.lib.path_of(LOADABLE, "party/b (Dan's conflicted copy)") == loser


def test_a_folder_named_in_another_case_is_the_folder_on_disk(lib_dirs):
    """Review 4: `Party/B` finds `party/b.json`; a save as `Party/NEW` lands
    in `party/` and is listed with the folder as it is on disk."""
    r = make(lib_dirs)
    assert r.lib.path_of(LOADABLE, "Party/B") == lib_dirs.loaded_patch / "party" / "b.json"
    assert r.lib.path_of(LOADABLE, "PARTY/DEEP/c") == lib_dirs.loaded_patch / "party" / "deep" / "c.json"
    r.loaded_patch.save_as("Party/NEW")
    assert r.lib.current(LOADABLE) == "party/NEW" and "party/NEW" in r.lib.list(LOADABLE)
    assert sorted(p.name for p in lib_dirs.loaded_patch.iterdir() if p.is_dir()) == [".cache", "party"]


def test_the_presets_walk_is_kept_until_a_folder_moves(lib_dirs, monkeypatch):
    """Review 8: two listings in a row walk the tree once; a file added
    in a subfolder is seen on the next."""
    r = make(lib_dirs)
    walks = []
    real = library.os.walk
    monkeypatch.setattr(library.os, "walk", lambda *a, **k: (walks.append(a[0]), real(*a, **k))[1])
    r.lib._walks.clear()
    r.lib.list(LOADABLE)
    r.lib.list(LOADABLE)
    r.lib.path_of(LOADABLE, "party/B")
    r.lib.is_dirty(LOADABLE)
    assert len(walks) == 1
    _put(lib_dirs.loaded_patch / "party" / "deep" / "d.json", "D")
    assert "party/deep/D" in r.lib.list(LOADABLE)


def test_one_folder_is_one_library_and_trash(tmp_path):
    """No [library] path: the machine home is the library, and its trash is
    the one there always was — no "old" trash."""
    _put(tmp_path / LOADABLE / "party" / "b.json", "B")
    lib = Library(tmp_path, period=0.0)
    assert lib._old_trash() is None and lib._trash_dir() == tmp_path / "trash"
    assert library.to_trash(tmp_path / LOADABLE / "party" / "b.json", tmp_path,
                            "presets/party").parent == tmp_path / "trash" / "presets" / "party"


# ---------------------------------------------------------------- review, second pass

def test_a_save_into_a_folder_not_there_never_writes_over_a_flat_file(lib_dirs):
    """Second pass 1: as… "nope/TRIP" with no `nope/` but a top-level
    `nope-trip.json` makes `presets/nope/trip.json`; NOPE TRIP is left
    alone, and a delete or rename of the folder name finds nothing."""
    _put(lib_dirs.loaded_patch / "nope-trip.json", "NOPE TRIP")
    r = make(lib_dirs)
    flat = (lib_dirs.loaded_patch / "nope-trip.json").read_text()
    assert not r.lib.delete(LOADABLE, "nope/TRIP")
    with pytest.raises(LibraryError, match="no preset"):
        r.lib.rename(LOADABLE, "nope/TRIP", "X")
    path = r.loaded_patch.save_as("nope/TRIP")
    assert path == lib_dirs.loaded_patch / "nope" / "trip.json"
    assert (lib_dirs.loaded_patch / "nope-trip.json").read_text() == flat


def test_a_kept_walk_is_trusted_one_tick_at_most(lib_dirs, monkeypatch):
    """Second pass 2: a file whose folder's mtime did not move (a coarse
    filesystem) is seen once WALK_TTL has passed."""
    r = make(lib_dirs)
    clock = [1000.0]
    monkeypatch.setattr(library, "_now", lambda: clock[0])
    r.lib._walks.clear()
    r.lib.list(LOADABLE)
    folder = lib_dirs.loaded_patch / "party"
    stamp = folder.stat().st_mtime_ns
    _put(folder / "e.json", "E")
    os.utime(folder, ns=(stamp, stamp))                   # as HFS+ might leave it
    assert "party/E" not in r.lib.list(LOADABLE)           # within the tick: kept
    clock[0] += library.WALK_TTL
    assert "party/E" in r.lib.list(LOADABLE)


def test_a_rename_repoints_a_slot_that_named_it_by_an_old_spelling(lib_dirs):
    """Second pass 3: a slot `Ac/Dc` (resolved by the loose read) follows
    a rename, and the show file says the new name."""
    _put(lib_dirs.loaded_patch / "ac-dc.json", "AC/DC")
    r = make(lib_dirs)
    pr = r.lib.project
    pr.bank[2] = "Ac/Dc"
    pr.write()
    assert r.lib.still_named("AC - DC") == ["F3"]
    r.lib.rename(LOADABLE, "AC - DC", "THUNDER")
    assert pr.bank[2] == "THUNDER"
    shown = json.loads((lib_dirs.root / "projects" / "night.hyp.json").read_text())
    assert shown["bank"][2] == "THUNDER"


def test_a_restore_into_a_folder_spelled_otherwise_takes_the_next_name(lib_dirs):
    """Second pass 4: the trash kept the file under `Party/` (the folder
    as it was spelled then) and `party/b.json` is there again: it is
    restored as B 2, not refused."""
    r = make(lib_dirs)
    lib = r.lib
    lib.delete(LOADABLE, "party/B")
    trash = lib_dirs.machine / "trash" / "presets"
    (kept,) = (trash / "party").glob("b.*.json")
    (trash / "Party-tmp").mkdir()
    kept.rename(trash / "Party-tmp" / kept.name)
    (trash / "party").rmdir()
    (trash / "Party-tmp").rename(trash / "Party")       # (two steps: APFS folds case)
    _put(lib_dirs.loaded_patch / "party" / "b.json", "B")
    (item,) = lib.trash()
    assert item.folder == "Party"
    assert lib.restore_trash(item) == "party/B 2"
    assert (lib_dirs.loaded_patch / "party" / "b-2.json").is_file()


def test_a_restore_clears_the_delete_warning_of_a_slashed_name(lib_dirs):
    """Second pass 5: × said "AC - DC is in the trash …"; the restore
    clears it, matching by the listed name."""
    _put(lib_dirs.loaded_patch / "ac-dc.json", "AC/DC")
    r = make(lib_dirs)
    lib = r.lib
    lib.project.bank[5] = "AC - DC"
    lib.delete(LOADABLE, "AC - DC")
    assert lib.warning.startswith("AC - DC is in the trash")
    (item,) = lib.trash()
    assert item.name == "AC - DC"
    lib.restore_trash(item)
    assert lib.warning == ""


def test_a_miss_reuses_the_kept_fold_map(lib_dirs, monkeypatch):
    """Second pass 6: a name with no file, asked every frame, folds the
    files once per walk, not once per ask."""
    r = make(lib_dirs)
    calls = []
    real = library.fold
    monkeypatch.setattr(library, "fold", lambda n: (calls.append(n), real(n))[1])
    r.lib._walks.clear()
    r.lib.path_of(LOADABLE, "untitled")
    first = len(calls)
    assert first >= 4                                     # every file folded once
    r.lib.path_of(LOADABLE, "untitled")
    assert len(calls) - first <= 2                        # then the name alone


def test_a_save_says_a_files_own_slash_went(lib_dirs):
    """Second pass 9: the first save over `AC/DC` says it, the next does not."""
    _put(lib_dirs.loaded_patch / "ac-dc.json", "AC/DC")
    r = make(lib_dirs)
    r.loaded_patch.load("AC - DC")
    r.lib.overwrite(LOADABLE)
    assert r.lib.status == "presets: saved AC - DC (was AC/DC)"
    r.lib.overwrite(LOADABLE)
    assert r.lib.status == "presets: saved AC - DC"


# ---------------------------------------------------------------- review, third pass

def test_a_folder_with_no_name_is_refused(lib_dirs):
    """Third pass 1: as… "party/" or "party/   " saves nothing."""
    r = make(lib_dirs)
    before = tree(lib_dirs.loaded_patch)
    for name in ("party/", "party/   "):
        with pytest.raises(LibraryError, match="needs a name"):
            r.loaded_patch.save_as(name)
    assert tree(lib_dirs.loaded_patch) == before and r.lib.current(LOADABLE) is None


def test_a_pad_naming_its_preset_by_another_spelling_lights(lib_dirs):
    """Third pass 2: slots `Ac/Dc` and `Party/B` load through the loose
    read and their pads light, as an exact spelling's does."""
    _put(lib_dirs.loaded_patch / "ac-dc.json", "AC/DC")
    r = make(lib_dirs)
    pr = r.lib.project
    pr.bank[4], pr.bank[5] = "Ac/Dc", "Party/B"
    pr.load_slot(4)
    assert r.lib.current(LOADABLE) == "AC - DC" and pr.active == 4
    pr.load_slot(5)
    assert r.lib.current(LOADABLE) == "party/B" and pr.active == 5
    r.loaded_patch.load("A")
    assert pr.active == 0
    r.loaded_patch.load("Ac/Dc")                    # the strip: the first slot that names it
    assert pr.active == 4


def test_a_symlinked_home_lists_its_trash_once(tmp_path):
    """Third pass 3: `[library] path` written through a link to the
    machine home is the same folder — its trash is this Mac's, not old."""
    machine = tmp_path / "M"
    _put(machine / LOADABLE / "a.json", "A")
    (tmp_path / "link").symlink_to(machine, target_is_directory=True)
    lib = Library(tmp_path / "link", machine=machine, period=0.0)
    assert lib._old_trash() is None
    lib.delete(LOADABLE, "A")
    listed = lib.trash()
    assert len(listed) == 1 and not listed[0].old


def test_a_non_preset_file_kept_deeper_goes_back_to_its_group(lib_dirs):
    """Third pass 4: only the presets have folders — a module preset the
    trash holds a folder down restores to its group's own folder."""
    r = make(lib_dirs)
    deep = lib_dirs.machine / "trash" / "camera" / "odd"
    deep.mkdir(parents=True)
    (deep / "wide.20261001-120000.json").write_text(
        json.dumps({"schema": "hyperspace.preset/1", "group": "camera", "name": "Wide",
                    "values": {}}))
    (item,) = r.lib.trash()
    r.lib.restore_trash(item)
    assert (lib_dirs.root / "patches" / "camera" / "wide.json").is_file()
    assert not (lib_dirs.root / "patches" / "camera" / "odd").exists()


def test_two_files_of_one_spelling_are_never_picked_by_sort_order(lib_dirs):
    """Third pass 5: `trip_2.json` and `trip-2.json` both fold to
    `trip-2`; a loose read of `Trip 2` resolves to neither and says
    which two, while the exact key still finds its own."""
    _put(lib_dirs.loaded_patch / "trip_2.json", "TRIP TWO")
    _put(lib_dirs.loaded_patch / "trip-2.json", "TRIP 2B")
    r = make(lib_dirs)
    assert r.lib.path_of(LOADABLE, "trip-2") == lib_dirs.loaded_patch / "trip-2.json"
    assert r.lib.path_of(LOADABLE, "trip_2", loose=True) == lib_dirs.loaded_patch / "trip_2.json"
    assert r.lib.path_of(LOADABLE, "Trip! 2", loose=True) is None
    assert "two presets answer to that name" in r.lib.warning
    assert "trip-2.json" in r.lib.warning and "trip_2.json" in r.lib.warning
