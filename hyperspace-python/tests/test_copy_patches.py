"""`tools/copy_patches.py`: a patch set goes into the library, never anywhere else,
and never over a patch the library already has.

Each case runs the tool as the READMEs do (`readme_copy`), with the home under
`tmp_path`. The library's rules it keeps: no `[library] path` is no library
(2026-11-23); a missing shared folder is never created (D5); the machine home
is never a library; nothing is overwritten (as `tools/move_library.py`, D8);
a patch lands whole or not at all (as the library writes).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import readme_copy

from hyperspace import library

KINETIC = readme_copy.ROOT / "loadable" / "kinetic"
README = KINETIC / "README.md"
FILES = sorted(KINETIC.glob("*.json"))


def _library(tmp_path: Path) -> tuple[Path, Path]:
    drive, machine = tmp_path / "drive", tmp_path / "machine"
    (drive / library.LOADABLE).mkdir(parents=True)
    return drive, machine


def _jsons(root: Path) -> list[Path]:
    return sorted(root.rglob("*.json"))


def test_no_library_set_copies_nothing(tmp_path):
    done = readme_copy.run(README, tmp_path / "machine", None)
    assert done.returncode != 0
    assert "no [library] path" in done.stderr
    assert not _jsons(tmp_path)


def test_a_library_folder_that_is_not_there_is_not_created(tmp_path):
    """A mistyped Drive folder: the patches would land where the app never reads."""
    typo = tmp_path / "Shared drives" / "Hyperspce"
    done = readme_copy.run(README, tmp_path / "machine", typo)
    assert done.returncode != 0
    assert "is not there" in done.stderr
    assert not typo.exists() and not typo.parent.exists()
    assert not _jsons(tmp_path)


def test_the_machine_home_is_never_the_library(tmp_path):
    """`path = "."` is the config's own folder, the home: startup never lists there."""
    machine = tmp_path / "machine"
    done = readme_copy.run(README, machine, ".")
    assert done.returncode != 0
    assert "home, never a library" in done.stderr
    assert not (machine / library.LOADABLE).exists()
    assert not _jsons(tmp_path)


def test_a_patch_the_library_has_is_never_overwritten(tmp_path):
    """Copied, edited and saved in the app, copied again: the edit stays."""
    drive, machine = _library(tmp_path)
    assert readme_copy.run(README, machine, drive).returncode == 0
    landed = drive / library.LOADABLE / "kinetic"
    edited = landed / FILES[0].name
    edited.write_text(edited.read_text().replace("}", ' , "edited": true}', 1))
    mine = edited.read_bytes()
    done = readme_copy.run(README, machine, drive)
    assert done.returncode == 0, done.stderr
    assert edited.read_bytes() == mine
    assert f"KEPT THEIRS {FILES[0].name}" in done.stdout
    assert f"{len(FILES) - 1} have, 1 KEPT THEIRS" in done.stdout
    for f in FILES[1:]:
        assert (landed / f.name).read_bytes() == f.read_bytes()


def test_a_library_not_yet_moved_gets_the_set_in_presets(tmp_path):
    """A library still on `presets/` (plan 57): where `library.loadable_dir` says."""
    drive, machine = tmp_path / "drive", tmp_path / "machine"
    (drive / library.OLD_LOADABLE).mkdir(parents=True)
    assert readme_copy.run(README, machine, drive).returncode == 0
    assert len(list((drive / library.OLD_LOADABLE / "kinetic").glob("*.json"))) == len(FILES)
    assert not (drive / library.LOADABLE).exists()


def _tool():
    spec = importlib.util.spec_from_file_location(
        "copy_patches", readme_copy.ROOT / "tools" / "copy_patches.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("links", [True, False], ids=["links", "cloud-no-links"])
def test_a_failed_write_leaves_nothing_and_a_retry_installs_it(tmp_path, monkeypatch, links):
    """A disk error halfway through one patch: no truncated patch is left for the
    next run to keep as KEPT THEIRS, and no temp file; the next run copies it."""
    drive, machine = _library(tmp_path)
    machine.mkdir()
    (machine / "config.toml").write_text(f'[library]\npath = "{drive}"\n')
    monkeypatch.setenv("HYPERSPACE_HOME", str(machine))
    tool = _tool()
    if not links:
        def no_link(src, dst):
            raise PermissionError(1, "Operation not permitted")
        monkeypatch.setattr(tool.os, "link", no_link)
    victim = FILES[0].name
    real = tool._write_all

    def half(fh, data):
        if Path(fh.name).name.lstrip(".").startswith(victim):
            fh.write(data[: len(data) // 2])
            raise OSError(28, "No space left on device")
        real(fh, data)
    monkeypatch.setattr(tool, "_write_all", half)
    with pytest.raises(SystemExit, match="nothing half-written"):
        tool.copy("kinetic", out=lambda _s: None)
    landed = drive / library.LOADABLE / "kinetic"
    assert not (landed / victim).exists()
    assert not [q for q in landed.iterdir() if q.name.startswith(".")]
    monkeypatch.setattr(tool, "_write_all", real)
    done = {n: w for w, n in tool.copy("kinetic", out=lambda _s: None)}
    assert done[victim] == "copied"
    assert "KEPT THEIRS" not in done.values()
    for f in FILES:
        assert (landed / f.name).read_bytes() == f.read_bytes()
