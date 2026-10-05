"""tools/shared_presets.py: taking someone's shared presets never writes
over a file, and the folders committed under shared/ are well-formed."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"

spec = importlib.util.spec_from_file_location("shared_presets", ROOT / "tools" / "shared_presets.py")
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)


def a_shared(tmp_path) -> Path:
    s = tmp_path / "shared"
    (s / "presets").mkdir(parents=True)
    (s / "projects").mkdir()
    (s / "fx").mkdir()
    (s / "presets" / "mine.json").write_text('{"name": "MINE", "v": 1}')
    (s / "presets" / "new.json").write_text('{"name": "NEW"}')
    (s / "presets" / "new.json.bak-v2").write_text("a backup")
    (s / "projects" / "party.hyp.json").write_text('{"name": "party"}')     # a factory show's name
    (s / "fx" / "acid.json").write_text('{"name": "acid"}')                 # a factory module preset's
    (s / "weights").mkdir()
    (s / "weights" / "big.json").write_text("{}")
    return s


def test_install_never_writes_over_a_file(tmp_path):
    s, home = a_shared(tmp_path), tmp_path / "home"
    (home / "presets").mkdir(parents=True)
    (home / "presets" / "mine.json").write_text('{"name": "MINE", "v": 2}')  # yours, different
    before = (home / "presets" / "mine.json").read_bytes()
    done = dict(sp.install(s, home))
    assert done[Path("presets/mine.json")] == "kept yours"
    assert (home / "presets" / "mine.json").read_bytes() == before
    assert done[Path("presets/new.json")] == "copy"
    assert (home / "presets" / "new.json").read_text() == '{"name": "NEW"}'
    # a second run copies nothing and changes nothing
    again = dict(sp.install(s, home))
    assert again[Path("presets/new.json")] == "have" and "copy" not in again.values()


def test_install_skips_what_would_shadow_a_factory_file_unless_asked(tmp_path):
    s, home = a_shared(tmp_path), tmp_path / "home"
    done = dict(sp.install(s, home))
    assert done[Path("projects/party.hyp.json")] == "factory"
    assert done[Path("fx/acid.json")] == "factory"
    assert not (home / "projects" / "party.hyp.json").exists()
    done = dict(sp.install(s, home, shadow=True))
    assert done[Path("projects/party.hyp.json")] == "copy"
    assert (home / "projects" / "party.hyp.json").exists()


def test_a_dry_run_writes_nothing_and_backups_and_weights_are_never_shared(tmp_path):
    s, home = a_shared(tmp_path), tmp_path / "home"
    todo = sp.install(s, home, dry_run=True)
    assert not home.exists()
    rels = {str(rel) for rel, _ in todo}
    assert "presets/new.json" in rels
    assert not any(".bak-" in r or r.startswith("weights") for r in rels)


def test_export_copies_a_home_and_refuses_a_folder_that_is_not_empty(tmp_path):
    home = a_shared(tmp_path)                       # shaped like a home too
    (home / "config.toml").write_text("[midi]\n")
    (home / "bindings.json").write_text("{}")
    out = tmp_path / "out"
    done = sp.export(home, out)
    assert Path("presets/new.json") in done and (out / "presets" / "new.json").exists()
    assert not (out / "config.toml").exists() and not (out / "bindings.json").exists()
    assert not (out / "weights").exists()
    with pytest.raises(SystemExit):
        sp.export(home, out)


@pytest.mark.parametrize("folder", sorted(p for p in SHARED.iterdir() if p.is_dir()) if SHARED.exists() else [])
def test_every_shared_folder_is_well_formed(folder):
    """Each committed shared folder: every file parses, a preset is a
    `hyperspace.preset/2` with a name, a show a `hyperspace.project/2`,
    and nothing names a path on someone's machine."""
    rels = sp.files(folder)
    assert rels, folder
    for rel in rels:
        text = (folder / rel).read_text()
        doc = json.loads(text)
        assert "/Users/" not in text and "/home/" not in text, rel
        if rel.parts[0] == "presets":
            assert doc["schema"] == "hyperspace.preset/2" and doc.get("name"), rel
        elif rel.parts[0] == "projects":
            assert doc["schema"] == "hyperspace.project/2" and doc.get("name"), rel
