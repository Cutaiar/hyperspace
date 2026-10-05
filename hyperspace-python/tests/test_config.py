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


def test_a_screen_that_is_not_a_number_is_minus_one_and_a_note(tmp_path, capsys):
    """Plan 16 WP7: `monitor = "left"` stopped the launch. A screen index
    that is not a number is −1 (where the window was last time), for both
    windows, said on stderr and in `cfg["notes"]` (the SYSTEM page); a
    number is read as `int()` reads it and nothing is said — whether that
    screen exists is placement's to say, at the launch."""
    p = tmp_path / "config.toml"
    p.write_text('[output]\nmonitor = "left"\ncontrol_monitor = [1]\n[overlay]\nbg = 0.3\n')
    cfg = config.load(p)
    assert cfg["output"]["monitor"] == cfg["output"]["control_monitor"] == -1
    assert cfg["output"]["bg"] == 0.3
    assert cfg["notes"] == [
        f"config: [overlay] is now [output] — rename the section in {p}",   # kept, first
        "config: [output] monitor = 'left' is not a screen index — using the last position",
        "config: [output] control_monitor = [1] is not a screen index — using the last position",
    ]
    err = capsys.readouterr().err
    assert all(n in err for n in cfg["notes"]) and "error" not in cfg
    p.write_text("[output]\nmonitor = nan\ncontrol_monitor = inf\n")
    cfg = config.load(p)
    assert cfg["output"]["monitor"] == cfg["output"]["control_monitor"] == -1
    assert len(cfg["notes"]) == 2
    capsys.readouterr()
    for text, want in (("monitor = 1\ncontrol_monitor = 0", (1, 0)), ('monitor = "1"', (1, -1)),
                       ("monitor = 2.0\ncontrol_monitor = -5", (2, -1)), ("monitor = 99", (99, -1))):
        p.write_text(f"[output]\n{text}\n")
        cfg = config.load(p)
        assert (cfg["output"]["monitor"], cfg["output"]["control_monitor"]) == want, text
        assert type(cfg["output"]["monitor"]) is int and "notes" not in cfg
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


# ---- plan 19 WP6: [library] git, off by default ----

def test_library_git_is_off_by_default_and_a_switch(tmp_path, capsys):
    assert config.DEFAULTS["library"] == {"git": False}
    p = tmp_path / "config.toml"
    assert config.load(p)["library"]["git"] is False             # no file
    p.write_text("[library]\ngit = true\n")
    cfg = config.load(p)
    assert cfg["library"]["git"] is True and "notes" not in cfg
    for text, value in (('"true"', "true"), ("1", 1), ("[true]", [True])):
        p.write_text(f"[library]\ngit = {text}\n")
        cfg = config.load(p)
        assert cfg["library"]["git"] is False
        assert cfg["notes"] == [(f"config: [library] git = {value!r} is not true or false "
                                 "— git stays off")]
    assert "[library] git" in capsys.readouterr().err
