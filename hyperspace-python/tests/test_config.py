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
    err = capsys.readouterr().err
    assert err.count("[overlay] is now [output]") == 1 and str(p) in err
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


def test_every_test_runs_with_its_own_home(tmp_path):
    assert os.environ["HYPERSPACE_HOME"] == str(tmp_path / "home")
    assert library.home() == tmp_path / "home"
    assert library.home() != Path("~/Hyperspace").expanduser()
    assert config.load()["output"] == config.DEFAULTS["output"]   # created under tmp_path
    assert (tmp_path / "home").is_dir()
