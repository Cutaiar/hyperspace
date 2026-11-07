"""The one migration's library road (plan 57 §7, §7a; rows 830–834): the new kinds, the old
folders still read, and the tool's steps over a library shaped like the Drive."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

from hyperspace import graphmigrate, loadable, patches, playlist
from hyperspace.library import (
    INSTALL_SCHEMA,
    LAST_INSTALL,
    LAST_SHOW,
    LOADABLE,
    NEWER_WORDS,
    Library,
    LibraryError,
    install_doc,
    install_files,
    installs_dir,
    loadable_dir,
    not_moved,
    without_unsaved,
)

ROOT = Path(__file__).resolve().parents[1]
SHOW = {"schema": "hyperspace.project/3", "name": "party", "note": "n", "startup": "TRIP",
        "bank": ["TRIP", "gone", None],
        "session": {"tempo.bpm": 128.0, "tempo.nudge": 0.2, "ghost.mirror": True,
                    "ghost.2.mirror": True, "output.bg": 0.5, "output.alpha": 0.9,
                    "scene.select": 3, "master.gain": 1.0},
        "modules": {"band": "Balanced"}, "layout": {"group:output": [1, 2]}}


def _tool():
    if "migrate_library" in sys.modules:
        return sys.modules["migrate_library"]
    spec = importlib.util.spec_from_file_location("migrate_library", ROOT / "tools/migrate_library.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate_library"] = mod
    spec.loader.exec_module(mod)
    return mod


def _put(path: Path, doc) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc if isinstance(doc, str) else json.dumps(doc))
    return path


def _old_library(root: Path) -> Path:
    """Shaped as the Drive was read on 2026-11-07, Icon files and all."""
    corpus = ROOT / "tests/corpus/loadable/dial.json"
    doc = {**json.loads(corpus.read_text()), "schema": "hyperspace.preset/10", "name": "TRIP"}
    _put(root / "presets/trip.json", doc)
    _put(root / "projects/party.hyp.json", SHOW)
    _put(root / "projects/party.hyp.json.bak-v2-look", SHOW)
    _put(root / "projects/mine.hyp.json", {"schema": "hyperspace.project/3", "name": "mine",
                                           "startup": "MIGRATED", "bank": ["TRIP"], "session": {},
                                           "modules": {}})
    _put(root / "trash/presets/old.20261030-180459.json", {"schema": "hyperspace.preset/7"})
    _put(root / "trash/Icon\r", "")
    _put(root / "presets-backup-2026-10-14/x.json", {"schema": "hyperspace.preset/2"})
    _put(root / "fx/wobbly-pinch.json", {"schema": "hyperspace.preset/1", "group": "fx"})
    _put(root / "tempo/Icon\r", "")
    _put(root / "media/still.PNG", "picture")
    _put(root / "media/empty/Icon\r", "")
    _put(root / "venues/laptop.toml", "x = 1")
    _put(root / "displays.json", {"schema": "displays/1"})
    return root


def _pictureless(path, *, library=None, show=None):
    return ["x"], []


@pytest.fixture
def tool(tmp_path, monkeypatch):
    monkeypatch.setenv("HYPERSPACE_HOME", str(tmp_path / "home"))
    return _tool()


def _run(tool, lib, *args):
    return tool.main(["--library", str(lib), *args], picture=_pictureless,
                     running=lambda: (False, "not open"))


def _tree(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


# ---------------------------------------------------------------- the kinds


def test_the_kinds_say_one_thing():
    assert loadable.SAVE_SCHEMA == graphmigrate.ELEVEN_SCHEMA == "hyperspace.loadable/11"
    assert patches.LOADABLE_KIND == graphmigrate.LOADABLE_KIND == loadable.KIND
    assert loadable.VERSIONS[-1] == graphmigrate.ELEVEN
    assert patches.shape_of({"schema": "hyperspace.loadable/11"}) == patches.LOADABLE_SHAPE
    assert patches.shape_of({"schema": "hyperspace.preset/10"}) == patches.LOADABLE_SHAPE
    with pytest.raises(ValueError):
        patches.forward({"schema": "hyperspace.loadable/11", "group": "view"})


def test_no_scene_says_preset():
    """§7a: the last `hyperspace.preset/1` files; analyzer tunings, so a patch of the band group."""
    from hyperspace.library import scene_doc
    files = sorted((ROOT / "hyperspace/scenes/band").glob("*.json"))
    assert len(files) == 11
    for f in files:
        assert json.loads(f.read_text())["schema"] == patches.SCHEMA, f.name
        assert scene_doc(f)["group"] == "band"


# ---------------------------------------------------------------- the install file


def test_a_show_as_its_install_keeps_every_live_value():
    """§7a: `modules`, `layout`, `startup` and `scene.select` each reach the file; the bank too.
    `output.bg` and `.alpha` stay in the tuning (rec: one overlay window, not one display)."""
    out = install_doc(SHOW)
    assert out["schema"] == INSTALL_SCHEMA and out["name"] == "party" and out["note"] == "n"
    assert out["modules"] == {"band": "Balanced"} and out["layout"] == {"group:output": [1, 2]}
    assert out["startup"] == "TRIP" and out["bank"] == ["TRIP", "gone", None]
    assert out["tuning"]["scene.select"] == 3 and out["tuning"]["output.bg"] == 0.5
    assert out["tuning"]["output.alpha"] == 0.9
    assert "session" not in out
    assert install_doc(out) == out


def test_what_a_save_stopped_writing_goes():
    assert without_unsaved(SHOW["session"]).keys() == SHOW["session"].keys() - {
        "tempo.nudge", "ghost.2.mirror"}
    assert "ghost.mirror" in install_doc(SHOW)["tuning"]


def test_an_install_round_trips_through_the_project(tmp_path):
    lib = Library(tmp_path, period=0.0)
    path = _put(tmp_path / "installs/room.json", {**install_doc(SHOW), "plays": "cart"})
    pr = lib.install
    pr._take(json.loads(path.read_text()), path, path.name)
    assert (pr.stem, pr.startup, pr.plays) == ("room", "TRIP", "cart")
    assert pr.session["output.bg"] == 0.5 and pr.modules == {"band": "Balanced"}
    assert "tempo.nudge" not in pr.session and "ghost.2.mirror" not in pr.session
    doc = pr.to_doc()
    assert doc["schema"] == INSTALL_SCHEMA and doc["plays"] == "cart" and doc["tuning"] == pr.session
    assert "session" not in doc


def test_a_newer_install_says_what_to_do(tmp_path):
    lib = Library(tmp_path, period=0.0)
    with pytest.raises(LibraryError, match="git pull and uv sync"):
        lib.install._take({"schema": "hyperspace.install/2"}, None, "room.json")
    assert "uv sync" in NEWER_WORDS


def test_a_newer_loadable_says_what_to_do(tmp_path):
    from conftest import boot_home  # the app's own road
    rig = boot_home(tmp_path / "h", corpus=False)
    _put(tmp_path / "h/loadable/next.json", {"schema": "hyperspace.loadable/12", "name": "next"})
    with pytest.raises(LibraryError, match="git pull and uv sync"):
        rig.lib.read(LOADABLE, "next")


# ---------------------------------------------------------------- old folders


def test_a_fresh_library_is_the_new_folders(tmp_path):
    lib = Library(tmp_path, period=0.0)
    assert (tmp_path / "installs").is_dir() and not (tmp_path / "projects").exists()
    assert loadable_dir(tmp_path) == tmp_path / "loadable" and lib.not_moved == ""


def test_a_library_not_moved_opens_and_says_so(tmp_path):
    """Plan 58 §2a: the new code on an old library doesn't strand it."""
    _old_library(tmp_path)
    before = _tree(tmp_path)
    lib = Library(tmp_path, period=0.0)
    assert not (tmp_path / "installs").exists() and not (tmp_path / "loadable").exists()
    assert installs_dir(tmp_path) == tmp_path / "projects"
    assert loadable_dir(tmp_path) == tmp_path / "presets"
    assert not_moved(tmp_path) == ["presets/", "projects/"]
    assert "presets/ and projects/" in lib.not_moved and "migrate_library.py --apply" in lib.not_moved
    assert lib.install.list() == ["mine", "party"]
    assert lib.install.path_for("party") == tmp_path / "projects/party.hyp.json"
    assert lib.install.path_for("new-one") == tmp_path / "projects/new-one.hyp.json"
    assert list(lib._files(LOADABLE)) == ["trip"]
    assert "presets" not in lib.groups() and "projects" not in lib.groups()
    assert _tree(tmp_path) == before                 # opening rewrites nothing


def test_a_save_on_a_library_not_moved_stays_in_its_folder_at_the_newest(tmp_path):
    _old_library(tmp_path)
    lib = Library(tmp_path, period=0.0)
    path = tmp_path / "projects/party.hyp.json"
    lib.install._take(json.loads(path.read_text()), path, path.name)
    lib.install.write()
    doc = json.loads((tmp_path / "projects/party.hyp.json").read_text())
    assert doc["schema"] == INSTALL_SCHEMA and "tuning" in doc


def test_last_show_is_read_until_last_install_is_written(tmp_path):
    lib = Library(tmp_path, period=0.0)
    (tmp_path / LAST_SHOW).write_text("party\n")
    assert lib.last_show() == "party"
    lib.remember("room")
    assert (tmp_path / LAST_INSTALL).read_text() == "room\n"
    assert lib.last_show() == "room"


def test_what_was_trashed_under_the_old_names_comes_back_under_the_new(tmp_path):
    machine = tmp_path / "machine"
    _put(machine / "trash/presets/trip.20261030-180459.json",
         {"schema": "hyperspace.preset/10", "name": "TRIP"})
    _put(machine / "trash/projects/room.hyp.20261030-180459.json", SHOW)
    root = tmp_path / "lib"
    root.mkdir()
    lib = Library(root, machine=machine, period=0.0)
    items = {t.group: t for t in lib.trash()}
    assert set(items) == {LOADABLE, "installs"}
    lib.restore_trash(items[LOADABLE])
    assert (root / "loadable/trip.json").is_file()
    lib.restore_trash(items["installs"])
    assert (root / "installs/room.json").is_file()
    assert [p.name for p in install_files(root)] == ["room.json"]


# ---------------------------------------------------------------- the tool


def test_a_dry_run_says_it_all_and_writes_nothing(tool, tmp_path, capsys):
    lib = _old_library(tmp_path / "lib")
    before = _tree(lib)
    assert _run(tool, lib) == 0
    out = capsys.readouterr().out
    assert _tree(lib) == before and not list((tmp_path / "home").glob("library-backup-*"))
    assert "dry run, nothing is written" in out
    assert "show party.hyp.json → installs/party.json" in out
    assert "its startup 'MIGRATED' names no file: cleared" in out
    assert "bank slots naming nothing, left as they are: 2" in out
    assert "it holds no tuning" in out
    for gone in ("delete: trash/", "delete: fx/", "delete: presets-backup-2026-10-14/",
                 "delete: projects/party.hyp.json.bak-v2-look", "delete, nothing in it: tempo/"):
        assert gone in out, gone
    assert "move: presets/ → loadable/" in out
    assert "media/empty" not in out                   # the media folder is never tidied


def test_apply_backs_up_first_then_moves_and_a_second_run_does_nothing(tool, tmp_path, capsys):
    lib = _old_library(tmp_path / "lib")
    before = _tree(lib)
    assert _run(tool, lib, "--apply") == 0
    out = capsys.readouterr().out
    (backup,) = (tmp_path / "home").glob("library-backup-*")
    assert f"backup: {backup}" in out and _tree(backup) == before
    after = _tree(lib)
    assert sorted(after) == sorted([
        "displays.json", "installs/mine.json", "installs/party.json", "loadable/trip.json",
        "media/empty/Icon\r", "media/still.PNG", "venues/laptop.toml"])
    assert json.loads(after["loadable/trip.json"])["schema"] == loadable.SAVE_SCHEMA
    party = json.loads(after["installs/party.json"])
    assert party["schema"] == INSTALL_SCHEMA and party["modules"] == {"band": "Balanced"}
    assert party["tuning"]["scene.select"] == 3 and party["startup"] == "TRIP"
    assert json.loads(after["installs/mine.json"])["startup"] is None
    # opens in the new reader
    fresh = Library(lib, machine=tmp_path / "m2", period=0.0)
    assert fresh.not_moved == "" and fresh.install.list() == ["mine", "party"]
    fresh.install._take(party, lib / "installs/party.json", "party.json")
    assert fresh.path_of(LOADABLE, "TRIP", loose=True) == lib / "loadable/trip.json"
    # once more: nothing, and no second backup
    assert _run(tool, lib, "--apply") == 0
    assert "nothing to do" in capsys.readouterr().out
    assert _tree(lib) == after and len(list((tmp_path / "home").glob("library-backup-*"))) == 1


def test_apply_refuses_while_the_app_is_open(tool, tmp_path, capsys):
    lib = _old_library(tmp_path / "lib")
    before = _tree(lib)
    code = tool.main(["--library", str(lib), "--apply"], picture=_pictureless,
                     running=lambda: (True, "Hyperspace is open on this Mac: 123 hyperspace"))
    assert code == 2 and _tree(lib) == before
    assert "quit Hyperspace on both Macs" in capsys.readouterr().err
    assert not list((tmp_path / "home").glob("library-backup-*"))


def test_it_says_if_it_cant_tell(tool, monkeypatch):
    import subprocess

    def fails(*_a, **_k):
        raise OSError("no ps")
    monkeypatch.setattr(subprocess, "run", fails)
    is_open, words = tool.app_running()
    assert is_open is None and "can't tell" in words


def test_the_app_is_seen_by_its_command_line(tool, monkeypatch):
    import subprocess

    class Out:
        stdout = "  1 /usr/bin/uv run pytest\n  2 /x/.venv/bin/hyperspace --laptop\n"
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: Out)
    assert tool.app_running()[0] is True

    class Quiet:
        stdout = "  1 /usr/bin/uv run pytest\n"
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_k: Quiet)
    assert tool.app_running()[0] is False


def test_an_old_builds_save_after_the_run_is_taken_in(tool, tmp_path, capsys):
    """Plan 58 §2a: saving from the old build puts old files in the old folder; another run
    takes them, and never over a file."""
    lib = _old_library(tmp_path / "lib")
    assert _run(tool, lib, "--apply") == 0
    keep = json.loads((lib / "loadable/trip.json").read_text())
    _put(lib / "presets/new.json", {**keep, "schema": "hyperspace.preset/10", "name": "NEW"})
    _put(lib / "presets/trip.json", {**keep, "schema": "hyperspace.preset/10", "name": "TRIP"})
    capsys.readouterr()
    assert _run(tool, lib, "--apply") == 1
    out = capsys.readouterr().out
    assert json.loads((lib / "loadable/new.json").read_text())["schema"] == loadable.SAVE_SCHEMA
    assert "presets/trip.json: loadable/ holds a file of that name" in out
    assert (lib / "presets/trip.json").is_file()


def test_a_library_that_is_the_home_keeps_this_macs_trash(tool, tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))
    _old_library(home)
    _put(home / "bindings.json.bak-v2-20260929", "a Mac's own backup")
    assert _run(tool, home, "--apply") == 0
    assert (home / "trash/presets/old.20261030-180459.json").is_file()
    assert (home / "bindings.json.bak-v2-20260929").is_file()


# ---------------------------------------------------------------- SM6


class _Playing:
    def __init__(self, ok=True):
        self.ok, self.on, self.chose = ok, False, None

    def select(self, name):
        self.chose = name
        return self.ok

    def play(self):
        self.on = True


class _Install:
    def __init__(self, plays):
        self.plays = plays


def test_a_cart_starts_by_itself_when_its_install_says():
    p = _Playing()
    assert playlist.at_launch(p, _Install("cart")) is True and p.on and p.chose == "cart"
    q = _Playing()
    assert playlist.at_launch(q, _Install(None)) is False and not q.on and q.chose is None
    gone = _Playing(ok=False)
    assert playlist.at_launch(gone, _Install("gone")) is False and not gone.on


def test_the_install_keeps_which_list_at_once(tmp_path):
    lib = Library(tmp_path, period=0.0)
    lib.install.path = tmp_path / "installs/room.json"
    lib.install.play_at_launch("cart")
    assert json.loads(lib.install.path.read_text())["plays"] == "cart"
    lib.install.play_at_launch(None)
    assert "plays" not in json.loads(lib.install.path.read_text())


# ---------------------------------------------------------------- NSEW and `bindings/4` (rows 836–839)

def test_nsew_is_one_idempotent_word_map():
    from hyperspace.routing_sources import nsew
    cases = {"pad:A": "pad:S", "pad:B": "pad:E", "pad:X": "pad:W", "pad:Y": "pad:N",
             "hat:UP": "hat:N", "hat@p2:LEFT": "hat@p2:W", "pad@p2:Y": "pad@p2:N",
             "pair:UP/DOWN": "pair:hat.N/hat.S", "pair:RIGHT/LEFT": "pair:hat.E/hat.W",
             "pair:Y/A": "pair:N/S", "pair@p2:B/X": "pair@p2:E/W", "pair:RB/LB": "pair:RB/LB",
             "pad:LB": "pad:LB", "axis:LX": "axis:LX", "axis:L.N": "axis:L.N", "key:A": "key:A"}
    for old, new in cases.items():
        assert nsew(old) == new and nsew(new) == new, old


def test_the_d_pad_and_the_cluster_are_two_namespaces():
    """FQ7's `pair:N/S` is the cluster; the D-pad's pair says so (row 836, rec)."""
    from hyperspace.routing_sources import pair_poles
    hat, face = pair_poles("hat.N/hat.S"), pair_poles("N/S")
    assert [p.source for p in hat] == ["hat:N", "hat:S"] and all(p.hat for p in hat)
    assert [p.source for p in face] == ["pad:N", "pad:S"] and not any(p.hat for p in face)


def test_eleven_moves_a_pair_routes_poles():
    doc = {"schema": "hyperspace.preset/10", "routes": [
        {"source": "pair:UP/DOWN", "target": "view.bright", "op": "push"},
        {"source": "lane:0", "target": "view.zoom", "op": "push"}, "junk"]}
    out = graphmigrate.eleven(doc)
    assert out["schema"] == loadable.SAVE_SCHEMA
    assert [r["source"] if isinstance(r, dict) else r for r in out["routes"]] == [
        "pair:hat.N/hat.S", "lane:0", "junk"]
    assert doc["routes"][0]["source"] == "pair:UP/DOWN"       # a copy


def test_the_owners_bindings_move_at_the_first_launch_with_a_backup(tmp_path):
    """Plan 58 §2a: each Mac's own file, by its own road: renamed once, kept first."""
    from hyperspace import routing
    src = ROOT / "tests/fixtures/desk-findings/owner-bindings.json"
    path = tmp_path / "bindings.json"
    path.write_bytes(src.read_bytes())
    old = path.read_bytes()
    t = routing.Bindings.load(path, legacy_midi=None)
    doc = json.loads(path.read_text())
    assert doc["schema"] == routing.SCHEMA == "hyperspace.bindings/4"
    assert doc[routing.PAD_LAYOUT_KEY] == routing.PAD_LAYOUT_NEWEST
    text = path.read_text()
    assert not re.search(r'"(pad|hat)(@\w+)?:(A|B|X|Y|UP|DOWN|LEFT|RIGHT)"', text)
    assert '"overlay.' not in text and '"output.overlay"' in text
    assert path.with_name("bindings.json.bak-v3").read_bytes() == old
    assert any(n.startswith("renamed ") for n in t.notes)
    again = routing.Bindings.load(path, legacy_midi=None)
    assert again.notes == [] and path.read_text() == text


def test_the_factory_names_no_alias_and_no_old_pad_word():
    from hyperspace import routing
    text = routing.FACTORY_FILE.read_text()
    assert '"overlay.' not in text
    assert not re.search(r'"(pad|hat)(@\w+)?:(A|B|X|Y|UP|DOWN|LEFT|RIGHT)"', text)
    assert all(b.target not in routing.OVERLAY_ALIASES for b in routing.Bindings.factory().bindings)


# ---------------------------------------------------------------- review of #434


def test_a_skipped_patch_keeps_the_shows_it_reads(tool, tmp_path, capsys):
    """A patch not written still takes the show's eye and looks at load: the shows and their
    .bak-v2-* files stay until it is fixed or forced."""
    lib = _old_library(tmp_path / "lib")
    calls = iter(range(10_000))

    def differs(path, *, library=None, show=None):
        return [str(next(calls))], []
    code = tool.main(["--library", str(lib), "--apply"], picture=differs,
                     running=lambda: (False, "not open"))
    out = capsys.readouterr().out
    assert code == 1 and "shows and .bak-v2-* files left as they are" in out
    assert (lib / "projects/party.hyp.json").is_file()
    assert (lib / "projects/party.hyp.json.bak-v2-look").is_file()
    assert not (lib / "installs").exists()


def test_a_config_that_wont_parse_is_never_the_home(tool, tmp_path, capsys):
    home = tmp_path / "home"
    _old_library(home)
    (home / "config.toml").write_text("[library\npath = 'x'")
    before = _tree(home)
    code = tool.main(["--apply"], picture=_pictureless, running=lambda: (False, "not open"))
    assert code == 2 and "does not read" in capsys.readouterr().err
    assert _tree(home) == before


def test_apply_refuses_when_it_cant_tell_unless_told(tool, tmp_path, capsys):
    lib = _old_library(tmp_path / "lib")
    before = _tree(lib)
    cant = (None, "can't tell whether Hyperspace is open")
    code = tool.main(["--library", str(lib), "--apply"], picture=_pictureless,
                     running=lambda: cant)
    assert code == 2 and _tree(lib) == before and "--closed" in capsys.readouterr().err
    assert tool.main(["--library", str(lib), "--apply", "--closed"], picture=_pictureless,
                     running=lambda: cant) == 0


def test_a_backup_short_of_files_stops_the_run(tool, tmp_path, monkeypatch, capsys):
    lib = _old_library(tmp_path / "lib")
    before = _tree(lib)
    real = tool._file_count
    monkeypatch.setattr(tool, "_file_count",
                        lambda root, ignore: real(root, ignore) - ("backup" in root.name))
    assert _run(tool, lib, "--apply") == 2
    assert "the backup failed" in capsys.readouterr().err and _tree(lib) == before


def test_an_empty_folder_the_owner_made_under_presets_moves(tool, tmp_path):
    lib = _old_library(tmp_path / "lib")
    (lib / "presets/later").mkdir()
    assert _run(tool, lib, "--apply") == 0
    assert (lib / "loadable/later").is_dir()


def test_start_at_launch_on_an_unsaved_show_writes_nothing(tmp_path):
    lib = Library(tmp_path, period=0.0)
    lib.install.path = None
    lib.install.play_at_launch("cart")
    assert not (tmp_path / "installs").exists() or not any((tmp_path / "installs").iterdir())


def test_a_linked_folder_counts_the_same_in_the_backup(tool, tmp_path):
    lib = _old_library(tmp_path / "lib")
    outside = tmp_path / "drive" / "clips"
    _put(outside / "a.mov", "x")
    (lib / "media" / "clips").symlink_to(outside, target_is_directory=True)
    assert _run(tool, lib, "--apply") == 0
