"""tools/move_library.py (plan 25 D8): an existing library copied into a
shared folder — never over a file, the machine files left behind, nothing
in the home touched. All on tmp_path. (The hidden lists' union went with
hidden loadable patches, 2026-10-28: a `hidden.json` is a machine file now.)"""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("move_library", ROOT / "tools" / "move_library.py")
ml = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ml)


def a_home(tmp_path) -> Path:
    h = tmp_path / "home"
    for d in ("loadable", "installs", "fx", "band", "trash/loadable", "weights", "bindings",
              ".git", "loadable/.hidden"):
        (h / d).mkdir(parents=True, exist_ok=True)
    (h / "loadable" / "hi-frek.json").write_text('{"name": "HI FREK"}')
    (h / "loadable" / "mine.json").write_text('{"name": "MINE", "v": 1}')
    (h / "loadable" / "mine.json.bak-v2").write_text("a backup")
    (h / "loadable" / ".DS_Store.json").write_text("dot")
    (h / "installs" / "mine.json").write_text('{"name": "mine"}')
    (h / "fx" / "acid.json").write_text('{"name": "acid"}')
    (h / "band" / "wide.json").write_text('{"name": "Wide"}')
    (h / "trash" / "loadable" / "old.20261004-011203.json").write_text("{}")
    (h / "weights" / "big.json").write_text("{}")
    (h / "bindings" / "show-a.json").write_text("{}")
    (h / ".git" / "config.json").write_text("{}")
    for f in ("config.toml", "bindings.json", "bindings.json.bak-v2", "hands.json",
              "windows.json", "last_install", "stall.log", ".gitignore"):
        (h / f).write_text(f)
    (h / "hidden.json").write_text(json.dumps({"schema": "hyperspace.hidden/1",
                                               "loadable": ["party-trip", "house"]}))
    return h                        # (hidden.json: a leftover of the two-tier library)


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def run(tmp_path, dest, home):
    lines = []
    done = ml.move(dest, home, out=lines.append)
    return done, lines


def test_a_fresh_copy_takes_the_library_and_leaves_the_machine(tmp_path):
    home = a_home(tmp_path)
    before = snapshot(home)
    dest = tmp_path / "Dropbox" / "Hyperspace"
    done, _ = run(tmp_path, dest, home)
    assert sorted(snapshot(dest)) == ["band/wide.json", "fx/acid.json", "installs/mine.json",
                                      "loadable/hi-frek.json", "loadable/mine.json"]
    assert {w for w, _ in done} == {"copied"}
    assert (dest / "loadable" / "mine.json").read_text() == '{"name": "MINE", "v": 1}'
    assert snapshot(home) == before                  # nothing in the home touched


def test_a_second_run_changes_nothing(tmp_path):
    home = a_home(tmp_path)
    dest = tmp_path / "shared"
    run(tmp_path, dest, home)
    first = snapshot(dest)
    done, _ = run(tmp_path, dest, home)
    assert snapshot(dest) == first
    assert {w for w, _ in done} == {"have"}


def test_a_conflict_keeps_theirs_and_says_where_yours_is(tmp_path):
    home = a_home(tmp_path)
    dest = tmp_path / "shared"
    (dest / "loadable").mkdir(parents=True)
    (dest / "loadable" / "mine.json").write_text('{"name": "MINE", "v": 2}')    # Dan's
    done, lines = run(tmp_path, dest, home)
    assert ("KEPT THEIRS", Path("loadable/mine.json")) in done
    assert (dest / "loadable" / "mine.json").read_text() == '{"name": "MINE", "v": 2}'
    said = next(line for line in lines if line.startswith("KEPT THEIRS"))
    assert str(home / "loadable" / "mine.json") in said


def test_machine_files_trash_git_and_backups_stay_behind(tmp_path):
    home = a_home(tmp_path)
    dest = tmp_path / "shared"
    run(tmp_path, dest, home)
    got = set(snapshot(dest))
    for left in ("config.toml", "bindings.json", "bindings.json.bak-v2", "hands.json",
                 "windows.json", "last_install", "stall.log", ".gitignore", ".git/config.json",
                 "hidden.json", "weights/big.json", "bindings/show-a.json",
                 "loadable/mine.json.bak-v2", "loadable/.DS_Store.json",
                 "trash/loadable/old.20261004-011203.json"):
        assert left not in got
    assert not (dest / "trash").exists()


def test_a_dry_run_writes_nothing(tmp_path, capsys):
    home = a_home(tmp_path)
    dest = tmp_path / "shared"
    assert ml.main([str(dest), "--from", str(home), "--dry-run"]) == 0
    assert not dest.exists()
    out = capsys.readouterr().out
    assert "copied      loadable/hi-frek.json" in out and "dry run:" in out


def test_main_prints_the_config_lines_and_never_edits_config(tmp_path, capsys, monkeypatch):
    home = a_home(tmp_path)
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))      # --from defaults to the home
    dest = tmp_path / "shared"
    assert ml.main([str(dest)]) == 0
    out = capsys.readouterr().out
    assert f'[library]\npath = "{dest.resolve()}"' in out
    assert (home / "config.toml").read_text() == "config.toml"
    assert (dest / "loadable" / "hi-frek.json").is_file()


def test_a_loadable_folder_is_copied_every_folder_down_hidden_ones_not(tmp_path):
    """Plan 48 stage 2: ``loadable/`` is walked as the library lists it —
    ``party/`` and ``party/deep/`` copied, ``loadable/.hidden/`` never; the
    other groups stay one level down."""
    home = a_home(tmp_path)
    (home / "loadable" / "party" / "deep").mkdir(parents=True)
    (home / "loadable" / "party" / "trip.json").write_text('{"name": "TRIP"}')
    (home / "loadable" / "party" / "deep" / "c.json").write_text('{"name": "C"}')
    (home / "loadable" / ".hidden" / "x.json").write_text("{}")
    (home / "fx" / "sub").mkdir()
    (home / "fx" / "sub" / "y.json").write_text("{}")
    dest = tmp_path / "shared"
    run(tmp_path, dest, home)
    got = set(snapshot(dest))
    assert {"loadable/party/trip.json", "loadable/party/deep/c.json"} <= got
    assert not [k for k in got if ".hidden" in k or k.startswith("fx/sub")]
    assert (dest / "loadable" / "party" / "deep" / "c.json").read_text() == '{"name": "C"}'


# ---------------------------------------------------------------- the home cleared (2026-11-23)

def test_main_moves_the_copied_folders_out_of_the_home(tmp_path, capsys):
    """The shared folder is the one place: after the copy, every folder the copy drew from
    goes, whole, into HOME/old-local-library-<stamp>/ — nothing deleted, the machine
    files, the trash and weights where they were, and the app finds no stray library."""
    from hyperspace import library
    home = a_home(tmp_path)
    (home / "media").mkdir()
    (home / "media" / "clip.json").write_text("{}")
    dest = tmp_path / "shared"
    assert ml.main([str(dest), "--from", str(home)]) == 0
    archives = [p for p in home.iterdir() if p.name.startswith(ml.ARCHIVE)]
    assert len(archives) == 1
    archive = archives[0]
    assert sorted(p.name for p in archive.iterdir()) == ["band", "fx", "installs", "loadable"]
    assert (archive / "loadable" / "mine.json.bak-v2").read_text() == "a backup"   # all of it
    for gone in ("loadable", "installs", "fx", "band"):
        assert not (home / gone).exists()
    for kept in ("config.toml", "bindings.json", "trash/loadable/old.20261004-011203.json",
                 "weights/big.json", "bindings/show-a.json", "media/clip.json"):
        assert (home / kept).is_file()
    assert not (dest / "media").exists()
    assert library.strays(home) == []
    assert "moved       loadable/" in capsys.readouterr().out
    # a second run finds nothing to copy, and never walks into the archive
    assert ml.main([str(dest), "--from", str(home)]) == 0
    assert "nothing to copy" in capsys.readouterr().out


def test_a_conflict_says_where_yours_went(tmp_path, capsys):
    home = a_home(tmp_path)
    dest = tmp_path / "shared"
    (dest / "loadable").mkdir(parents=True)
    (dest / "loadable" / "mine.json").write_text('{"name": "MINE", "v": 2}')
    assert ml.main([str(dest), "--from", str(home)]) == 0
    out = capsys.readouterr().out
    (archive,) = [p for p in home.iterdir() if p.name.startswith(ml.ARCHIVE)]
    assert f"yours is now at {archive / 'loadable' / 'mine.json'}" in out
    assert (archive / "loadable" / "mine.json").read_text() == '{"name": "MINE", "v": 1}'
    assert (dest / "loadable" / "mine.json").read_text() == '{"name": "MINE", "v": 2}'


def test_keep_and_dry_run_leave_the_home_as_it_was(tmp_path):
    home = a_home(tmp_path)
    before = snapshot(home)
    assert ml.main([str(tmp_path / "a"), "--from", str(home), "--dry-run"]) == 0
    assert ml.main([str(tmp_path / "b"), "--from", str(home), "--keep"]) == 0
    assert snapshot(home) == before


def test_group_patches_are_copied_before_their_folder_is_cleared(tmp_path):
    """Review of #480: a patch of one group sits in ``patches/<group>/`` (plan 50) — copied,
    in a mixed folder and in one of group patches alone, before the folder goes aside."""
    for only_groups in (False, True):
        home = a_home(tmp_path / str(only_groups))
        (home / "patches" / "camera").mkdir(parents=True)
        (home / "patches" / "camera" / "wide.json").write_text('{"name": "Wide"}')
        if not only_groups:
            (home / "patches" / "glow.json").write_text('{"name": "Glow"}')
        dest = home.parent / "shared"
        assert ml.main([str(dest), "--from", str(home)]) == 0
        assert (dest / "patches" / "camera" / "wide.json").read_text() == '{"name": "Wide"}'
        assert (dest / "patches" / "glow.json").is_file() != only_groups
        assert not (home / "patches").exists()


def test_an_old_layout_home_is_refused_and_left_alone(tmp_path):
    """Review of #480: `presets/` copied into a library that reads `loadable/` would never
    show — the tool says to run the one migration first and touches nothing."""
    home = a_home(tmp_path)
    (home / "presets").mkdir()
    (home / "presets" / "trip.json").write_text('{"name": "TRIP"}')
    before = snapshot(home)
    dest = tmp_path / "shared"
    (dest / "loadable").mkdir(parents=True)
    with pytest.raises(SystemExit, match="migrate_library.py"):
        ml.main([str(dest), "--from", str(home)])
    assert snapshot(home) == before
    assert list((dest / "loadable").iterdir()) == []
