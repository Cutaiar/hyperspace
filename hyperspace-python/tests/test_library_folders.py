"""Plan 48 stage 2: the library's folder operations — `Library.move` (a
preset into another folder, its bytes kept, the bank and every show
following), `make_folder`, `rename_folder` (every preset inside keeps its
leaf, the slots follow) and `remove_folder` (an empty folder only), and
`folders` (every folder down, empty ones too, hidden ones never).

Over test_preset_folders' temp library and temp machine home: nothing
here touches ~/Hyperspace or a Drive folder."""

import json
import os

import pytest
from test_loadable_folders import _put, lib_dirs, make  # noqa: F401 — the fixture

from hyperspace.library import LOADABLE, PROJECT_SCHEMA, LibraryError


def _show(d, name="night"):
    return json.loads((d.root / "projects" / f"{name}.hyp.json").read_text())


def _second_show(d, bank):
    doc = {"schema": PROJECT_SCHEMA, "name": "other", "startup": None, "bank": bank}
    (d.root / "projects" / "other.hyp.json").write_text(json.dumps(doc))


def test_folders_lists_every_folder_down_empty_ones_too_never_hidden(lib_dirs):  # noqa: F811
    (lib_dirs.loaded_patch / "empty").mkdir()
    r = make(lib_dirs)
    assert r.lib.folders() == ["empty", "party", "party/deep"]


def test_a_move_keeps_the_bytes_and_the_bank_and_the_shows_follow(lib_dirs):  # noqa: F811
    _second_show(lib_dirs, ["A", "a", None])
    r = make(lib_dirs)
    lib, pr = r.lib, r.lib.project
    lib.load(LOADABLE, "A")
    before = (lib_dirs.loaded_patch / "a.json").read_bytes()
    dst = lib.move("A", "party")
    assert dst == lib_dirs.loaded_patch / "party" / "a.json"
    assert dst.read_bytes() == before and not (lib_dirs.loaded_patch / "a.json").exists()
    assert "party/A" in lib.list(LOADABLE) and "A" not in lib.list(LOADABLE)
    assert lib.current(LOADABLE) == "party/A" and not lib.is_dirty(LOADABLE)
    assert pr.bank[0] == "party/A" and pr.startup == "party/A" and pr.bank[1] == "party/B"
    assert _show(lib_dirs)["bank"][0] == "party/A" and _show(lib_dirs)["startup"] == "party/A"
    # another show naming it — by its name and by its file key — follows too
    assert _show(lib_dirs, "other")["bank"][:2] == ["party/A", "party/A"]
    assert {t.name for t in lib.trash() if t.group == "projects"} >= {"night", "other"}
    assert lib.status == "moved A → party/A (2 shows updated)"
    # and back to the top, by the folder-qualified name
    lib.move("party/A", "")
    assert (lib_dirs.loaded_patch / "a.json").read_bytes() == before
    assert pr.bank[0] == "A" and lib.current(LOADABLE) == "A"


def test_a_move_into_a_nested_folder_and_its_refusals(lib_dirs):  # noqa: F811
    r = make(lib_dirs)
    lib = r.lib
    lib.move("party/B", "party/deep")
    assert "party/deep/B" in lib.list(LOADABLE)
    assert lib.project.bank[1] == "party/deep/B"
    assert lib.move("party/deep/B", "Party/Deep") == lib_dirs.loaded_patch / "party/deep/b.json"
    with pytest.raises(LibraryError, match="no folder"):
        lib.move("A", "nowhere")
    with pytest.raises(LibraryError, match="no preset"):
        lib.move("ZZZ", "party")
    _put(lib_dirs.loaded_patch / "party" / "deep" / "a.json", "A")
    lib._sync()
    with pytest.raises(LibraryError, match="already has a preset by that name"):
        lib.move("A", "party/deep")
    assert (lib_dirs.loaded_patch / "a.json").is_file()              # nothing moved


def test_make_folder_at_the_top_and_inside_and_its_refusals(lib_dirs):  # noqa: F811
    r = make(lib_dirs)
    lib = r.lib
    assert lib.make_folder("", "ambient") == "ambient"
    assert lib.make_folder("party", " late ") == "party/late"
    assert (lib_dirs.loaded_patch / "party" / "late").is_dir()
    assert {"ambient", "party/late"} <= set(lib.folders())
    for bad, why in (("a/b", "no '/'"), (".cache", "may not start"), ("", "needs a name"),
                     ("Ambient", "already there")):
        with pytest.raises(LibraryError, match=why):
            lib.make_folder("", bad)
    with pytest.raises(LibraryError, match="no folder"):
        lib.make_folder("nowhere", "x")


def test_a_folder_rename_keeps_every_leaf_and_the_slots_follow(lib_dirs):  # noqa: F811
    r = make(lib_dirs)
    lib, pr = r.lib, r.lib.project
    pr.put_slot(2, "party/deep/C")
    lib.load(LOADABLE, "party/deep/C")
    b = (lib_dirs.loaded_patch / "party" / "b.json").read_bytes()
    assert lib.rename_folder("party", "crowd") == "crowd"
    assert not (lib_dirs.loaded_patch / "party").exists()
    assert (lib_dirs.loaded_patch / "crowd" / "b.json").read_bytes() == b
    assert {"crowd/B", "crowd/deep/C"} <= set(lib.list(LOADABLE))
    assert pr.bank[1] == "crowd/B" and pr.bank[2] == "crowd/deep/C" and pr.bank[0] == "A"
    assert lib.current(LOADABLE) == "crowd/deep/C"
    assert _show(lib_dirs)["bank"][1:3] == ["crowd/B", "crowd/deep/C"]
    assert lib.status.startswith("renamed the folder party → crowd")
    # a nested one keeps its parent
    assert lib.rename_folder("crowd/deep", "deeper") == "crowd/deeper"
    assert pr.bank[2] == "crowd/deeper/C"
    lib.make_folder("", "ambient")
    with pytest.raises(LibraryError, match="taken"):
        lib.rename_folder("crowd", "Ambient")
    with pytest.raises(LibraryError, match="top level"):
        lib.rename_folder("", "x")


def test_remove_folder_takes_an_empty_folder_only(lib_dirs):  # noqa: F811
    r = make(lib_dirs)
    lib = r.lib
    lib.make_folder("", "ambient")
    (lib_dirs.loaded_patch / "ambient" / ".DS_Store").write_bytes(b"finder")
    lib.remove_folder("ambient")
    assert not (lib_dirs.loaded_patch / "ambient").exists() and "ambient" not in lib.folders()
    with pytest.raises(LibraryError, match="not empty"):
        lib.remove_folder("party")
    lib.make_folder("", "keep")
    (lib_dirs.loaded_patch / "keep" / ".notes").write_text("a hidden file of yours")
    with pytest.raises(LibraryError, match="not empty — it holds .notes"):
        lib.remove_folder("keep")
    assert (lib_dirs.loaded_patch / "keep" / ".notes").is_file()
    assert lib.held("keep") == [".notes"] and lib.held("ambient") == []
    assert lib.held("party") == ["b (Dan's conflicted copy).json", "b.json", "deep/"]


# ---------------------------------------------------------------- review of #349

def test_a_folder_named_like_a_loadable_file_is_refused_and_never_listed(lib_dirs):  # noqa: F811
    r = make(lib_dirs)
    lib = r.lib
    with pytest.raises(LibraryError, match="may not end in '.json'"):
        lib.make_folder("", "mix.json")
    (lib_dirs.loaded_patch / "made-in-finder.JSON.json").mkdir()     # a folder made elsewhere
    lib._sync()
    assert not [n for n in lib.list(LOADABLE) if "made-in-finder" in n]
    assert "made-in-finder.JSON.json" in lib.folders()          # a folder, as it is


def test_a_control_character_in_a_folder_name_is_refused(lib_dirs):  # noqa: F811
    r = make(lib_dirs)
    for bad in ("a\0b", "tab\there", "x\x7f"):
        with pytest.raises(LibraryError, match="control character"):
            r.lib.make_folder("", bad)
        with pytest.raises(LibraryError, match="control character"):
            r.lib.rename_folder("party", bad)
    assert (lib_dirs.loaded_patch / "party").is_dir()


def test_a_case_change_renames_and_another_folder_by_that_name_is_refused(
        lib_dirs, monkeypatch):  # noqa: F811
    r = make(lib_dirs)
    lib = r.lib
    assert lib.rename_folder("party", "Party") == "Party"     # this very folder: allowed
    assert "Party/B" in lib.list(LOADABLE) and lib.project.bank[1] == "Party/B"
    # a case-sensitive volume: `party` beside `Party` is another folder — the
    # disk says so (samefile), not the fold, and nothing is replaced. Where
    # the disk allows it (Linux CI) the sibling is real; where it folds case
    # (APFS) there can be no sibling, so samefile is faked to say "another"
    p = lib_dirs.loaded_patch
    folds = (p / "party").exists() and os.path.samefile(p / "party", p / "Party")
    if folds:
        monkeypatch.setattr(type(p), "samefile", lambda self, other: False)
    else:
        (p / "party").mkdir()                                     # the sibling, empty
        lib._sync()
    with pytest.raises(LibraryError, match="taken"):
        lib.rename_folder("Party", "party")
    assert (p / "Party" / "b.json").is_file()
    assert folds or not any((p / "party").iterdir())            # the sibling untouched
