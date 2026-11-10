"""Row 394: tools/migrate_library.py — a library's loadable patches rewritten as
the newest schema (plan 44 D3: `hyperspace.preset/10`) once, through the
app's own load and save, a picture check on the golden rig deciding what
is written.

Every test runs on a scratch library under tmp_path, the machine home
(`HYPERSPACE_HOME`, the backup's place) the conftest's tmp one."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "corpus" / "loadable"          # the shipped loadable patches, as test data
FIXTURES = ROOT / "tests" / "fixtures" / "presets"
SOURCES = ROOT / "tests" / "fixtures" / "factory-sources" / "presets"   # the corpus's /2s


def _tool():
    if "migrate_library" in sys.modules:
        return sys.modules["migrate_library"]
    spec = importlib.util.spec_from_file_location("migrate_library",
                                                  ROOT / "tools" / "migrate_library.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate_library"] = mod
    spec.loader.exec_module(mod)
    return mod


def _library(tmp_path: Path) -> Path:
    """A library shaped like the owner's: a `/2` loadable patch (party-trip's
    source, under a file name of its own), a `/5` with an old GRAPH layout
    (glimmer-bug), one already at the newest, one this build refuses (a value that
    will not land), a module preset, the trash and a backup beside them."""
    from hyperspace import headless

    lib = tmp_path / "Drive" / "Hyperspace"
    loadable_dir = lib / "presets"
    loadable_dir.mkdir(parents=True)
    shutil.copyfile(SOURCES / "party-trip.json", loadable_dir / "trip-night.json")
    shutil.copyfile(FIXTURES / "glimmer-bug.json", loadable_dir / "glimmer-bug.json")
    seven, _, _ = headless.resave(FIXTURES / "acid-scene.json", tmp_path / "seven")
    (loadable_dir / "acid-scene.json").write_bytes(seven)
    (loadable_dir / "broken.json").write_text(json.dumps(
        {"schema": "hyperspace.preset/2", "name": "broken", "values": {"view.bright": "fast"}}))
    (loadable_dir / "trip-night.json.bak-20261001").write_text("{}")
    (loadable_dir / ".tmp.json").write_text("{}")
    (lib / "trash" / "presets").mkdir(parents=True)
    (lib / "trash" / "presets" / "old.json").write_text(
        (CORPUS / "dial.json").read_text())
    (lib / "fx").mkdir()
    (lib / "fx" / "wobbly.json").write_text(json.dumps(
        {"schema": "hyperspace.preset/1", "group": "fx", "name": "wobbly",
         "values": {"fx.wobble.on": True}}))
    return lib


def _tree(root: Path) -> dict[str, tuple[bytes, int]]:
    return {str(p.relative_to(root)): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*")) if p.is_file()}


def same_picture(path, *, library=None, show=None):
    """A stand-in for the golden rig: every file draws one picture."""
    return ["x"] * 8, []


def test_the_loadables_it_finds(tmp_path):
    lib = _library(tmp_path)
    got = [p.name for p in _tool().loadable_files(lib)]
    assert got == ["acid-scene.json", "broken.json", "glimmer-bug.json", "trip-night.json"]


def test_a_dry_run_writes_nothing(tmp_path, capsys):
    lib = _library(tmp_path)
    home = Path(os.environ["HYPERSPACE_HOME"])
    before = _tree(lib)
    code = _tool().main(["--library", str(lib)], picture=same_picture)
    out = capsys.readouterr().out
    assert code == 1                                  # (broken would be skipped)
    assert _tree(lib) == before
    assert not home.exists() or not list(home.glob("library-backup-*"))
    assert "dry run, nothing is written" in out
    assert "trip-night.json" in out and "2 → 11" in out
    assert "glimmer-bug.json" in out and "5 → 11" in out
    assert "already /11, untouched" in out
    assert "broken: does not load" in out
    assert "would rewrite 2 as /11, leave 1 untouched (already /11), skip 1" in out


def test_apply_backs_up_migrates_and_leaves_seven_and_the_rest_alone(tmp_path, capsys):
    lib = _library(tmp_path)
    home = Path(os.environ["HYPERSPACE_HOME"])
    before = _tree(lib)
    code = _tool().main(["--library", str(lib), "--apply"], picture=same_picture)
    out = capsys.readouterr().out
    assert code == 1
    backups = list(home.glob("library-backup-*"))
    assert len(backups) == 1 and f"backup: {backups[0]}" in out
    assert _tree(backups[0]).keys() == before.keys()
    assert all(_tree(backups[0])[k][0] == before[k][0] for k in before)
    after = _tree(lib)
    # the folder moved; the trash and the retired group's folder went, deleted not converted
    assert after.keys() == {k.replace("presets/", "loadable/") for k in before
                            if not k.startswith(("trash/", "fx/"))}
    for name in ("trip-night.json", "glimmer-bug.json"):
        doc = json.loads(after[f"loadable/{name}"][0])
        assert doc["schema"] == "hyperspace.loadable/11", name
        assert doc["name"] == json.loads(before[f"presets/{name}"][0])["name"]
    for name in ("acid-scene.json", "broken.json", "trip-night.json.bak-20261001"):
        assert after[f"loadable/{name}"][0] == before[f"presets/{name}"][0], name
    assert "rewrote 2 as /11, left 1 untouched (already /11), skipped 1" in out
    assert not [p for p in (lib / "loadable").iterdir() if p.name.endswith(".tmp")]
    # and once more: everything is /10 now, so nothing to do but the refusal
    again = _tree(lib)
    assert _tool().main(["--library", str(lib)], picture=same_picture) == 1
    assert _tree(lib) == again
    assert "would rewrite 0 as /11, leave 3 untouched" in capsys.readouterr().out


def test_to_writes_each_seven_elsewhere_and_never_the_library(tmp_path, capsys):
    """Plan 36 T3: `--to FOLDER` writes every loadable patch that passed — the `/9`
    already there too — into FOLDER under its own name; the library is
    read, never written, and no backup is made (how the corpus's `/7` were
    made from their sources)."""
    lib = _library(tmp_path)
    home = Path(os.environ["HYPERSPACE_HOME"])
    before = _tree(lib)
    out_dir = tmp_path / "out"
    assert _tool().main(["--library", str(lib), "--to", str(out_dir)],
                        picture=same_picture) == 1               # (broken: skipped)
    assert _tree(lib) == before
    assert not home.exists() or not list(home.glob("library-backup-*"))
    assert sorted(p.name for p in out_dir.iterdir()) == [
        "acid-scene.json", "glimmer-bug.json", "trip-night.json"]
    for p in out_dir.iterdir():
        assert json.loads(p.read_text())["schema"] == "hyperspace.loadable/11", p.name
    assert (out_dir / "acid-scene.json").read_bytes() == before["presets/acid-scene.json"][0]
    assert "wrote 3 as /11 into" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        _tool().main(["--library", str(lib), "--to", str(out_dir), "--apply"])


def test_a_loadable_whose_picture_moves_is_not_written_unless_forced(tmp_path, capsys):
    lib = _library(tmp_path)
    (lib / "presets" / "broken.json").unlink()

    def moved(path, *, library=None, show=None):      # glimmer-bug's /9 draws another picture
        seven = "nine" in path.parts and path.stem == "glimmer-bug"
        return ["y" if seven else "x"] * 8, []

    before = _tree(lib)
    assert _tool().main(["--library", str(lib), "--apply"], picture=moved) == 1
    out = capsys.readouterr().out
    assert _tree(lib)["loadable/glimmer-bug.json"][0] == before["presets/glimmer-bug.json"][0]
    assert "glimmer-bug: round-trip picture differs (8 of 8 outputs)" in out
    assert json.loads((lib / "loadable" / "trip-night.json").read_text())["schema"] == \
        "hyperspace.loadable/11"
    assert _tool().main(["--library", str(lib), "--apply", "--force", "glimmer-bug"],
                        picture=moved) == 0
    assert json.loads((lib / "loadable" / "glimmer-bug.json").read_text())["schema"] == \
        "hyperspace.loadable/11"


def test_an_old_file_whose_section_is_not_read_is_never_written(tmp_path, capsys):
    """Final review: an old file whose graph section this build refuses
    loads black with a "not read" note; its /7 would keep the old words with
    the migration lost for good, so it is skipped — `--force` or not — and
    the round-trip check (both black) does not pass it."""
    lib = _library(tmp_path)
    (lib / "presets" / "broken.json").unlink()
    odd = {"schema": "hyperspace.preset/6", "name": "odd", "values": {},
           "graph": {"frame": "wired", "nodes": [{"kind": "warp-drive"}], "wires": []}}
    (lib / "presets" / "odd.json").write_text(json.dumps(odd))
    before = _tree(lib)
    assert _tool().main(["--library", str(lib), "--apply", "--force", "odd"],
                        picture=same_picture) == 1
    out = capsys.readouterr().out
    assert _tree(lib)["loadable/odd.json"][0] == before["presets/odd.json"][0]
    assert "odd: its graph section was not read by this build" in out
    assert json.loads((lib / "loadable" / "trip-night.json").read_text())["schema"] == \
        "hyperspace.loadable/11"


def test_a_file_that_raises_runtime_error_is_skipped_alone(tmp_path, capsys, monkeypatch):
    """Final review: `wired_section`'s "did not settle" (a RuntimeError)
    skips that one file; the run goes on to the rest."""
    from hyperspace import headless
    lib = _library(tmp_path)
    (lib / "presets" / "broken.json").unlink()
    real = headless.resave

    def resave(path, scratch, **kw):
        if Path(path).stem == "glimmer-bug":
            raise RuntimeError("wired_section: the frame did not settle in 64 rounds")
        return real(path, scratch, **kw)

    monkeypatch.setattr(headless, "resave", resave)
    before = _tree(lib)
    assert _tool().main(["--library", str(lib), "--apply"], picture=same_picture) == 1
    out = capsys.readouterr().out
    assert _tree(lib)["loadable/glimmer-bug.json"][0] == before["presets/glimmer-bug.json"][0]
    assert "glimmer-bug: does not load: wired_section: the frame did not settle" in out
    assert json.loads((lib / "loadable" / "trip-night.json").read_text())["schema"] == \
        "hyperspace.loadable/11"


def test_the_library_defaults_to_the_configs(tmp_path, capsys):
    lib = _library(tmp_path)
    home = Path(os.environ["HYPERSPACE_HOME"])
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.toml").write_text(f'[library]\npath = "{lib}"\n')
    assert _tool().configured_library(home) == lib.resolve()
    _tool().main([], picture=same_picture)
    assert f"library: {lib.resolve()}" in capsys.readouterr().out
    assert _tool().main(["--library", str(tmp_path / "nowhere")]) == 2


def test_the_real_picture_check_passes_an_old_loadable(tmp_path, capsys):
    """The golden rig itself (no stand-in): party-trip and glimmer-bug draw
    the same as their `/9`, so `--apply` writes both."""
    pytest.importorskip("moderngl")
    sys.path.insert(0, str(ROOT / "tools"))
    import golden_frames
    try:
        golden_frames.context()
    except Exception as e:  # noqa: BLE001 — any GL failure means skip
        pytest.skip(f"no standalone GL context available: {e}")
    lib = _library(tmp_path)
    (lib / "presets" / "broken.json").unlink()
    assert _tool().main(["--library", str(lib), "--apply"]) == 0
    out = capsys.readouterr().out
    assert out.count("round-trip picture: same") == 3
    for name in ("trip-night", "glimmer-bug", "acid-scene"):
        assert json.loads((lib / "loadable" / f"{name}.json").read_text())["schema"] == \
            "hyperspace.loadable/11"


def test_a_folder_made_after_the_last_run_is_migrated_too(tmp_path, capsys):
    """Plan 48 stage 2: the tool lists ``presets/`` every folder down, as
    the library does — ``party/`` and ``party/deep/`` migrated in place,
    a hidden folder (``.cache``) never read; ``--to`` keeps the folders."""
    lib = _library(tmp_path)
    loadable_dir = lib / "presets"
    (loadable_dir / "party" / "deep").mkdir(parents=True)
    shutil.copyfile(SOURCES / "party-trip.json", loadable_dir / "party" / "night.json")
    shutil.copyfile(FIXTURES / "glimmer-bug.json", loadable_dir / "party" / "deep" / "bug.json")
    (loadable_dir / ".cache").mkdir()
    shutil.copyfile(SOURCES / "party-trip.json", loadable_dir / ".cache" / "x.json")
    got = [p.relative_to(loadable_dir).as_posix() for p in _tool().loadable_files(lib)]
    assert got == ["acid-scene.json", "broken.json", "glimmer-bug.json", "trip-night.json",
                   "party/night.json", "party/deep/bug.json"]
    out_dir = tmp_path / "out"
    _tool().main(["--library", str(lib), "--to", str(out_dir)], picture=same_picture)
    assert json.loads((out_dir / "party" / "deep" / "bug.json").read_text())["schema"] \
        == "hyperspace.loadable/11"
    capsys.readouterr()
    hidden = (loadable_dir / ".cache" / "x.json").read_bytes()
    assert _tool().main(["--library", str(lib), "--apply"], picture=same_picture) == 1
    out = capsys.readouterr().out
    assert "party/night.json" in out and "party/deep/bug.json" in out
    loadable_dir = lib / "loadable"
    for rel in ("party/night.json", "party/deep/bug.json"):
        assert json.loads((loadable_dir / rel).read_text())["schema"] == "hyperspace.loadable/11", rel
    assert (loadable_dir / ".cache" / "x.json").read_bytes() == hidden
    assert "rewrote 4 as /11" in out
