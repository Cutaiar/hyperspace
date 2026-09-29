"""config.toml: [output] is the one section, [overlay] its pre-split alias
(audit L4); a bad file is reported, not fatal; tests never see ~/Hyperspace
(audit L7)."""

import os
from pathlib import Path

from hyperspace import config, library


def test_output_defaults_fill_and_a_file_overrides(tmp_path):
    p = tmp_path / "config.toml"
    cfg = config.load(p)
    assert cfg["output"] == config.DEFAULTS["output"]
    assert "overlay" not in cfg
    p.write_text("[output]\nmonitor = 1\nbg = 0.5\n")
    cfg = config.load(p)
    assert cfg["output"]["monitor"] == 1 and cfg["output"]["bg"] == 0.5
    assert cfg["output"]["alpha"] == 1.0                       # the defaults fill the rest


def test_overlay_is_an_alias_merged_under_output_and_noted_once(tmp_path, capsys):
    p = tmp_path / "config.toml"
    p.write_text("[overlay]\non_start = true\nbg = 0.3\n")
    cfg = config.load(p)
    assert cfg["output"]["on_start"] is True and cfg["output"]["bg"] == 0.3
    assert cfg["output"]["monitor"] == -1
    assert "overlay" not in cfg                                # folded, not kept beside
    err = capsys.readouterr().err
    assert err.count("[overlay] is now [output]") == 1 and str(p) in err
    assert cfg["notes"] == [err.strip()]                       # the SYSTEM page shows it too
    # a real [output] wins over the alias, key by key — the owner's file
    # today has both: [output] commented out, [overlay] with the look
    p.write_text("[output]\nmonitor = 1\nbg = 0.9\n[overlay]\non_start = true\nbg = 0.3\n")
    cfg = config.load(p)
    assert cfg["output"] == {**config.DEFAULTS["output"], "monitor": 1, "bg": 0.9,
                             "on_start": True}


def test_a_file_with_only_output_says_nothing(tmp_path, capsys):
    p = tmp_path / "config.toml"
    p.write_text("[output]\nfullscreen = true\n")
    config.load(p)
    assert capsys.readouterr().err == ""


def test_a_bad_file_keeps_the_defaults_and_carries_the_error(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[midi\nenabled = true\n")
    cfg = config.load(p)
    assert cfg["error"].startswith("config:")
    assert cfg["midi"]["enabled"] is True and cfg["output"] == config.DEFAULTS["output"]
    p.write_text("[midi]\nenabled = false\n")
    assert "error" not in config.load(p)


def test_a_scalar_in_place_of_any_section_is_an_error_and_the_defaults_stand(tmp_path):
    """`gamepad = false` or `midi = true` instead of a table must not crash
    the _open_* gates: every section is guarded, each bad one is named."""
    p = tmp_path / "config.toml"
    p.write_text("midi = true\noutput = 3\n[bridge]\nenabled = true\n")
    cfg = config.load(p)
    assert cfg["midi"] == {**config.DEFAULTS["midi"], "map": str(tmp_path / "midi_map.json")}
    assert cfg["output"] == config.DEFAULTS["output"]
    assert cfg["bridge"]["enabled"] is True                    # the good section still lands
    assert "[midi] must be a table" in cfg["error"] and "[output] must be a table" in cfg["error"]
    assert cfg["error"].startswith("config:")


def test_a_scalar_output_beside_a_legacy_overlay_is_reported_not_dropped(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("output = true\n[overlay]\nbg = 0.2\n")
    cfg = config.load(p)
    assert cfg["output"]["bg"] == 0.2                          # the alias table still lands
    assert "[output] must be a table" in cfg["error"]          # …and the scalar is named
    assert cfg["notes"] and "overlay" not in cfg


def test_every_test_runs_with_its_own_home(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)   # ensure_home migrates a cwd config.toml; none here
    assert os.environ["HYPERSPACE_HOME"] == str(tmp_path / "home")
    assert library.home() == tmp_path / "home"
    assert library.home() != Path("~/Hyperspace").expanduser()
    assert config.load()["output"] == config.DEFAULTS["output"]   # created under tmp_path
    assert (tmp_path / "home").is_dir()
