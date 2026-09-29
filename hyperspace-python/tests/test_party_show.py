"""Plan 14 WP3, decision 22: the party show is what the rig opens.

A fresh home opens the factory party show; the last show opened is
remembered (`<home>/last_show`) and opens next time; the eight house
moods are the factory `house` show; and a home plan 13 migrated — the
owner's, whose user `projects/default.hyp.json` holds `MIGRATED` and the
house moods — has that file renamed `mine` once, with a backup, so it no
longer stands where the rig used to look. Headless, over tmp homes (never
~/Hyperspace), the app's construction order (`test_presets.boot`).
"""

import json

from test_presets import boot

from hyperspace import library
from hyperspace.library import FACTORY

HOUSE = json.loads((FACTORY / "projects" / "house.hyp.json").read_text())["bank"]


def owners_home(home):
    """The owner's home after plan 13's migration (2026-09-28): a user
    `default` show — MIGRATED on F1, seven house moods behind it, starting
    on MIGRATED — and the MIGRATED preset itself."""
    (home / "projects").mkdir(parents=True, exist_ok=True)
    (home / "presets").mkdir(parents=True, exist_ok=True)
    doc = {"schema": "hyperspace.project/2", "name": "default", "startup": "MIGRATED",
           "bank": ["MIGRATED", *HOUSE[:7]], "session": {"master.gain": 1.5},
           "modules": {}}
    (home / "projects" / "default.hyp.json").write_text(json.dumps(doc, indent=1))
    migrated = {"schema": "hyperspace.preset/2", "name": "MIGRATED",
                "values": {"view.shape": 7}, "routes": [], "macros": {}, "modules": {}}
    (home / "presets" / "migrated.json").write_text(json.dumps(migrated))
    return doc


def tree(home) -> dict:
    return {p.relative_to(home).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(home.rglob("*")) if p.is_file()}


def test_the_factory_shows_are_party_and_house():
    party = json.loads((FACTORY / "projects" / "party.hyp.json").read_text())
    assert library.DEFAULT_PROJECT == "party" and party["name"] == "party"
    assert HOUSE[0] == "BIG BLUE WAVE" and len(HOUSE) == 8
    assert not (FACTORY / "projects" / "default.hyp.json").exists()


def test_a_fresh_home_opens_the_party_show(tmp_path):
    r = boot(tmp_path, show=None)
    assert r.lib.project.name == "party" and r.lib.project.path is None
    assert r.lib.current("presets") == "TUMBLE" and r.lib.project.active == 0
    assert r.lib.project.list() == ["house", "party"]
    assert not r.lib.error and not r.lib.warning


def test_the_last_show_opened_is_the_one_that_opens(tmp_path):
    r = boot(tmp_path, show=None)
    r.lib.project.load("house")
    assert (tmp_path / "last_show").read_text() == "house\n"
    again = boot(tmp_path, show=None)
    assert again.lib.project.name == "house"
    assert again.lib.current("presets") == "BIG BLUE WAVE"
    # a show saved as a new name is remembered too
    again.lib.project.save("Friday")
    assert boot(tmp_path, show=None).lib.project.name == "Friday"


def test_a_remembered_show_that_is_gone_falls_back_to_the_party(tmp_path):
    (tmp_path / "last_show").write_text("vanished\n")
    r = boot(tmp_path, show=None)
    assert r.lib.project.name == "party" and r.lib.current("presets") == "TUMBLE"


def test_the_owners_home_is_renamed_with_a_backup_and_opens_the_party(tmp_path, capsys):
    before = owners_home(tmp_path)
    raw = (tmp_path / "projects" / "default.hyp.json").read_bytes()
    r = boot(tmp_path, show=None)
    # renamed: mine holds the bank and startup as they were, MIGRATED first
    assert not (tmp_path / "projects" / "default.hyp.json").exists()
    mine = json.loads((tmp_path / "projects" / "mine.hyp.json").read_text())
    assert mine == dict(before, name="mine")
    assert mine["bank"][0] == "MIGRATED" and mine["startup"] == "MIGRATED"
    assert (tmp_path / "projects" / "default.hyp.json.bak-v2").read_bytes() == raw
    # said on stderr and on the panel's warning line
    assert "your show 'default' is now 'mine'" in capsys.readouterr().err
    assert "now 'mine'" in r.lib.warning
    # the party opens; MIGRATED is still a preset, and mine still opens on it
    assert r.lib.project.name == "party" and r.lib.current("presets") == "TUMBLE"
    assert "MIGRATED" in r.lib.list("presets")
    assert r.lib.project.list() == ["house", "mine", "party"]
    r.lib.project.load("mine")
    assert r.lib.current("presets") == "MIGRATED" and r.view.shape == 7


def test_the_rename_runs_once_and_never_over_a_backup(tmp_path, capsys):
    owners_home(tmp_path)
    (tmp_path / "projects" / "default.hyp.json.bak-v2").write_text("an older backup")
    boot(tmp_path, show=None)
    assert (tmp_path / "projects" / "default.hyp.json.bak-v2").read_text() == "an older backup"
    dated = sorted((tmp_path / "projects").glob("default.hyp.json.bak-v2-*"))
    assert len(dated) == 1 and json.loads(dated[0].read_text())["name"] == "default"
    capsys.readouterr()
    after = tree(tmp_path)
    again = boot(tmp_path, show=None)
    assert tree(tmp_path) == after                      # nothing written the second time
    assert capsys.readouterr().err == "" and not again.lib.warning
    assert again.lib.project.name == "party"


def test_a_mine_already_there_leaves_both_shows_alone(tmp_path):
    owners_home(tmp_path)
    (tmp_path / "projects" / "mine.hyp.json").write_text(json.dumps(
        {"schema": "hyperspace.project/2", "name": "mine", "bank": [], "startup": None}))
    after = tree(tmp_path)
    r = boot(tmp_path, show=None)
    assert {k: v for k, v in tree(tmp_path).items() if k.startswith("projects/")} == \
        {k: v for k, v in after.items() if k.startswith("projects/")}
    assert r.lib.project.name == "party"
    assert r.lib.project.list() == ["default", "house", "mine", "party"]
