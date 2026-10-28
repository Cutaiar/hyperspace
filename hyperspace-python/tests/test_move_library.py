"""tools/move_library.py (plan 25 D8): an existing library copied into a
shared folder — never over a file, the machine files left behind, nothing
in the home touched. All on tmp_path. (The hidden lists' union went with
hidden presets, 2026-10-28: a `hidden.json` is a machine file now.)"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("move_library", ROOT / "tools" / "move_library.py")
ml = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ml)


def a_home(tmp_path) -> Path:
    h = tmp_path / "home"
    for d in ("presets", "projects", "fx", "band", "trash/presets", "weights", "bindings",
              ".git", "presets/.hidden"):
        (h / d).mkdir(parents=True, exist_ok=True)
    (h / "presets" / "hi-frek.json").write_text('{"name": "HI FREK"}')
    (h / "presets" / "mine.json").write_text('{"name": "MINE", "v": 1}')
    (h / "presets" / "mine.json.bak-v2").write_text("a backup")
    (h / "presets" / ".DS_Store.json").write_text("dot")
    (h / "projects" / "mine.hyp.json").write_text('{"name": "mine"}')
    (h / "fx" / "acid.json").write_text('{"name": "acid"}')
    (h / "band" / "wide.json").write_text('{"name": "Wide"}')
    (h / "trash" / "presets" / "old.20261004-011203.json").write_text("{}")
    (h / "weights" / "big.json").write_text("{}")
    (h / "bindings" / "show-a.json").write_text("{}")
    (h / ".git" / "config.json").write_text("{}")
    for f in ("config.toml", "bindings.json", "bindings.json.bak-v2", "hands.json",
              "windows.json", "last_show", "stall.log", ".gitignore"):
        (h / f).write_text(f)
    (h / "hidden.json").write_text(json.dumps({"schema": "hyperspace.hidden/1",
                                               "presets": ["party-trip", "house"]}))
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
    assert sorted(snapshot(dest)) == ["band/wide.json", "fx/acid.json",
                                      "presets/hi-frek.json", "presets/mine.json",
                                      "projects/mine.hyp.json"]
    assert {w for w, _ in done} == {"copied"}
    assert (dest / "presets" / "mine.json").read_text() == '{"name": "MINE", "v": 1}'
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
    (dest / "presets").mkdir(parents=True)
    (dest / "presets" / "mine.json").write_text('{"name": "MINE", "v": 2}')    # Dan's
    done, lines = run(tmp_path, dest, home)
    assert ("KEPT THEIRS", Path("presets/mine.json")) in done
    assert (dest / "presets" / "mine.json").read_text() == '{"name": "MINE", "v": 2}'
    said = next(line for line in lines if line.startswith("KEPT THEIRS"))
    assert str(home / "presets" / "mine.json") in said


def test_machine_files_trash_git_and_backups_stay_behind(tmp_path):
    home = a_home(tmp_path)
    dest = tmp_path / "shared"
    run(tmp_path, dest, home)
    got = set(snapshot(dest))
    for left in ("config.toml", "bindings.json", "bindings.json.bak-v2", "hands.json",
                 "windows.json", "last_show", "stall.log", ".gitignore", ".git/config.json",
                 "hidden.json", "weights/big.json", "bindings/show-a.json",
                 "presets/mine.json.bak-v2", "presets/.DS_Store.json",
                 "trash/presets/old.20261004-011203.json"):
        assert left not in got
    assert not (dest / "trash").exists()


def test_a_dry_run_writes_nothing(tmp_path, capsys):
    home = a_home(tmp_path)
    dest = tmp_path / "shared"
    assert ml.main([str(dest), "--from", str(home), "--dry-run"]) == 0
    assert not dest.exists()
    out = capsys.readouterr().out
    assert "copied      presets/hi-frek.json" in out and "dry run:" in out


def test_main_prints_the_config_lines_and_never_edits_config(tmp_path, capsys, monkeypatch):
    home = a_home(tmp_path)
    monkeypatch.setenv("HYPERSPACE_HOME", str(home))      # --from defaults to the home
    dest = tmp_path / "shared"
    assert ml.main([str(dest)]) == 0
    out = capsys.readouterr().out
    assert f'[library]\npath = "{dest.resolve()}"' in out
    assert (home / "config.toml").read_text() == "config.toml"
    assert (dest / "presets" / "hi-frek.json").is_file()
