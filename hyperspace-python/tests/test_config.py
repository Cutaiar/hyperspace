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


# ---- plan 25: [library] path, the shared library folder ----

def test_library_path_is_empty_by_default(tmp_path, capsys):
    assert config.DEFAULTS["library"] == {"path": ""}
    p = tmp_path / "config.toml"
    cfg = config.load(p)                                         # no file
    assert cfg["library"] == {"path": ""} and "notes" not in cfg
    p.write_text('[library]\npath = ""\n')
    cfg = config.load(p)
    assert cfg["library"]["path"] == "" and "notes" not in cfg
    assert capsys.readouterr().err == ""


def test_library_path_expands_the_user(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "me"))
    p = tmp_path / "config.toml"
    p.write_text('[library]\npath = "~/Dropbox/Hyperspace"\n')
    cfg = config.load(p)
    assert cfg["library"]["path"] == str((tmp_path / "me" / "Dropbox" / "Hyperspace").resolve())
    assert "notes" not in cfg


def test_library_path_relative_to_the_config_folder(tmp_path):
    p = tmp_path / "home" / "config.toml"
    p.parent.mkdir()
    p.write_text('[library]\npath = "../shared"\n')
    assert config.load(p)["library"]["path"] == str((tmp_path / "shared").resolve())
    p.write_text(f'[library]\npath = "{tmp_path / "abs"}"\n')
    assert config.load(p)["library"]["path"] == str((tmp_path / "abs").resolve())


def test_library_path_not_text_stays_in_the_home(tmp_path, capsys):
    p = tmp_path / "config.toml"
    for text, value in (("true", True), ("1", 1), ('["a"]', ["a"])):
        p.write_text(f"[library]\npath = {text}\n")
        cfg = config.load(p)
        assert cfg["library"]["path"] == ""
        assert cfg["notes"] == [(f"config: [library] path = {value!r} is not text "
                                "— the library stays in the home")]
    assert "[library] path" in capsys.readouterr().err


def test_library_git_leftover_is_ignored_with_a_note(tmp_path, capsys):
    p = tmp_path / "config.toml"
    p.write_text("[library]\ngit = true\n")
    cfg = config.load(p)
    assert cfg["library"] == {"path": ""}
    assert cfg["notes"] == [("config: [library] git is gone (plan 25) — presets are shared "
                            "through [library] path; remove the line")]
    assert "[library] git is gone" in capsys.readouterr().err


# ---- plan 21 WP3: [[output.screens]], the list of render outputs ----

def test_no_screens_list_is_one_output_as_today(tmp_path, capsys):
    """An existing config.toml keeps working unedited: no `screens` key in
    cfg, nothing said, and `config.screens` is one output from the scalar
    monitor / fullscreen with the default switches."""
    p = tmp_path / "config.toml"
    for text in ("", "[output]\nmonitor = 1\nfullscreen = true\n"):
        p.write_text(text)
        cfg = config.load(p)
        assert "screens" not in cfg["output"] and "notes" not in cfg
        oc = cfg["output"]
        assert config.screens(cfg) == [{**config.SCREEN, "monitor": oc["monitor"],
                                        "fullscreen": oc["fullscreen"]}]
    assert config.screens(config.load(p))[0]["monitor"] == 1
    assert config.load(tmp_path / "none.toml")["output"] == config.DEFAULTS["output"]
    assert config.screens({}) == [config.SCREEN]                  # any cfg, never empty
    assert capsys.readouterr().err == ""


def test_a_screens_list_wins_over_the_scalar_keys_with_a_note(tmp_path, capsys):
    p = tmp_path / "config.toml"
    p.write_text('[output]\nmonitor = 0\nfullscreen = false\nbg = 0.4\n'
                 '[[output.screens]]\nname = "glass"\nmonitor = 1\nfullscreen = true\n'
                 '[[output.screens]]\nname = "projector"\nmonitor = 2\nscene = true\n'
                 'hands = false\nthrough = true\ndim = 0.6\n')
    cfg = config.load(p)
    oc = cfg["output"]
    glass, proj = config.screens(cfg)
    assert glass == {**config.SCREEN, "name": "glass", "monitor": 1, "fullscreen": True}
    assert proj == {**config.SCREEN, "name": "projector", "monitor": 2, "hands": False,
                    "through": True, "dim": 0.6}
    # output 1's entry is what the first window's readers see
    assert (oc["monitor"], oc["fullscreen"], oc["bg"]) == (1, True, 0.4)
    assert cfg["notes"] == [("config: [[output.screens]] is listed, so [output] monitor and "
                            "fullscreen are ignored — output 1's entry says")]
    assert capsys.readouterr().err.strip() == cfg["notes"][0]
    # no scalar keys in the file: nothing to say
    p.write_text('[[output.screens]]\nmonitor = 1\n[[output.screens]]\nmonitor = -1\n')
    cfg = config.load(p)
    assert "notes" not in cfg and len(config.screens(cfg)) == 2
    # every key checked: a wrong kind is the default, with a note, never a dead launch
    p.write_text('[[output.screens]]\nmonitor = "left"\nfullscreen = "yes"\nhands = 1\n'
                 'dim = "x"\nmonitr = 2\nname = 7\n')
    cfg = config.load(p)
    (one,) = config.screens(cfg)
    assert one == {**config.SCREEN, "name": "7"}
    assert len(cfg["notes"]) == 5 and all("output 1:" in n for n in cfg["notes"])
    assert "unknown key 'monitr'" in cfg["notes"][0]


def test_a_fifth_screen_is_dropped_with_a_note(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("".join(f'[[output.screens]]\nname = "s{k}"\n' for k in range(6)))
    cfg = config.load(p)
    assert [s["name"] for s in config.screens(cfg)] == ["s0", "s1", "s2", "s3"]
    assert cfg["notes"] == [("config: [[output.screens]] lists 6 outputs, 4 at most — "
                            "output 5 on dropped")]
    # an entry that is not a table is dropped, and an empty or non-list
    # `screens` is one output as [output] says
    p.write_text('[output]\nscreens = [{monitor = 1}, 3]\n')
    cfg = config.load(p)
    assert [s["monitor"] for s in config.screens(cfg)] == [1]
    assert cfg["notes"] == ["config: [[output.screens]] entry 2 is not a table (3) — dropped"]
    for text in ("screens = []", "screens = 3"):
        p.write_text(f"[output]\nmonitor = 1\n{text}\n")
        cfg = config.load(p)
        assert "screens" not in cfg["output"] and cfg["output"]["monitor"] == 1
        assert len(cfg["notes"]) == 1 and "one output, as [output] says" in cfg["notes"][0]


def test_a_config_dim_cannot_launch_an_output_black(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[[output.screens]]\ndim = 0.0\n[[output.screens]]\ndim = 0.05\n"
                 "[[output.screens]]\ndim = 3\n[[output.screens]]\ndim = 0.1\n")
    cfg = config.load(p)
    assert [s["dim"] for s in config.screens(cfg)] == [0.1, 0.1, 1.0, 0.1]
    assert cfg["notes"] == [
        "config: [[output.screens]] output 1: dim = 0 would launch it black — 0.1",
        "config: [[output.screens]] output 2: dim = 0.05 would launch it black — 0.1",
    ]


def test_a_ground_or_opacity_that_is_not_a_number_is_the_default_with_a_note(tmp_path):
    """`[output] bg = "x"` stopped the launch (app._make_output's float())."""
    p = tmp_path / "config.toml"
    p.write_text('[output]\nbg = "x"\nalpha = true\n')
    cfg = config.load(p)
    assert (cfg["output"]["bg"], cfg["output"]["alpha"]) == (0.0, 1.0)
    assert cfg["notes"] == ["config: [output] bg = 'x' is not a number — 0.0",
                            "config: [output] alpha = True is not a number — 1.0"]
    p.write_text("[output]\nbg = 0.5\nalpha = 1\n")
    cfg = config.load(p)
    assert (cfg["output"]["bg"], cfg["output"]["alpha"]) == (0.5, 1) and "notes" not in cfg


# ---- plan 27 B1: [[devices]], the device list ----

def test_no_devices_list_translates_the_old_tables_with_one_note_each(tmp_path, capsys):
    """A rig config from before plan 27 keeps working unedited: its
    `[midi]` / `[gamepad]` / `[hands]` / `[bridge]` tables become the
    equivalent entries, in today's poll order, and each table the file
    holds is asked to become an entry — once, on stderr and the SYSTEM
    page. No file at all: the four default entries, nothing said."""
    p = tmp_path / "config.toml"
    cfg = config.load(p)
    assert [(e["role"], e["kind"], e["enabled"]) for e in config.devices(cfg)] == [
        ("pad", "gamepad", True), ("apc40", "midi", True), ("leap", "hands", False),
        ("bridge", "bridge", False)]
    assert "notes" not in cfg and capsys.readouterr().err == ""
    pad, midi, leap, bridge = config.devices(cfg)
    assert pad == {"role": "pad", "kind": "gamepad", "enabled": True, "usb": True}
    assert midi == {"role": "apc40", "kind": "midi", "enabled": True, "port": None,
                    "profile": "apc40", "map": str(tmp_path / "midi_map.json")}
    assert {k for k in leap if k not in ("role", "kind", "enabled")} == set(cfg["hands"]) - {"enabled"}
    assert bridge["send"] == ["lane:*"] and bridge["in_lanes"] == 16
    p.write_text('[midi]\nport = "Launchpad"\n[hands]\nenabled = true\ntape = "t.json"\n'
                 '[gamepad]\nusb = false\n')
    cfg = config.load(p)
    pad, midi, leap, bridge = config.devices(cfg)
    assert (pad["usb"], midi["port"], leap["enabled"], leap["tape"]) == (
        False, "Launchpad", True, str(tmp_path / "t.json"))
    assert cfg["hands"]["tape"] == str(tmp_path / "t.json")
    assert cfg["notes"] == [
        "config: [gamepad] is now a [[devices]] entry (role = 'pad', kind = 'gamepad') — see config.py",
        "config: [midi] is now a [[devices]] entry (role = 'apc40', kind = 'midi') — see config.py",
        "config: [hands] is now a [[devices]] entry (role = 'leap', kind = 'hands') — see config.py",
    ]
    assert capsys.readouterr().err.strip().split("\n") == cfg["notes"]
    assert "problems" not in cfg


def test_a_devices_list_wins_and_is_checked_per_entry(tmp_path, capsys):
    """With a list, the list says: its entries are checked one by one (a
    bad role or kind drops the entry, a bad `enabled` is true, a known
    kind's own keys are filled from its defaults, an unknown kind is kept
    for the registry to refuse), the old tables are ignored with a note,
    and the first entry of each old kind is folded back into its table so
    `cfg["midi"]` / `cfg["hands"]` say what the entry says."""
    p = tmp_path / "config.toml"
    p.write_text(
        '[[devices]]\nrole = "apc40"\nkind = "midi"\nport = "APC"\n'
        '[[devices]]\nrole = "leap"\nkind = "hands"\ndofs = ["x"]\ncalibration = "c.json"\n'
        '[[devices]]\nrole = "phone"\nkind = "osc"\nhost = "0.0.0.0"\nenabled = "yes"\n'
        '[[devices]]\nrole = "x:y"\nkind = "midi"\n'
        '[[devices]]\nkind = "midi"\n'
        '[[devices]]\nrole = "apc40"\nkind = "midi"\n'
        '[[devices]]\nrole = "pad2"\n'
        '[[devices]]\nrole = "pad2"\nkind = 3\n'
        '[midi]\nport = "ignored"\n')
    cfg = config.load(p)
    got = config.devices(cfg)
    assert [(e["role"], e["kind"], e["enabled"]) for e in got] == [
        ("apc40", "midi", True), ("leap", "hands", True), ("phone", "osc", True)]
    assert got[0]["port"] == "APC" and got[0]["profile"] == "apc40"       # defaults filled
    assert got[1]["dofs"] == ["x"] and got[1]["calibration"] == str(tmp_path / "c.json")
    assert got[2] == {"role": "phone", "kind": "osc", "enabled": True, "host": "0.0.0.0"}
    assert cfg["midi"]["port"] == "APC" and cfg["midi"]["enabled"] is True
    assert cfg["hands"]["dofs"] == ["x"] and cfg["hands"]["enabled"] is True
    assert cfg["hands"]["calibration"] == str(tmp_path / "c.json")
    assert cfg["gamepad"]["enabled"] is False and cfg["bridge"]["enabled"] is False
    assert cfg["problems"] == [
        "config: [[devices]] entry 4: role = 'x:y' is not a name without ':' — dropped",
        "config: [[devices]] entry 5: role = None is not a name without ':' — dropped",
        "config: [[devices]] entry 6: role 'apc40' is listed twice — the second dropped",
        "config: [[devices]] entry 7: (pad2) kind = None is not a kind — dropped",
        "config: [[devices]] entry 8: (pad2) kind = 3 is not a kind — dropped",
    ]
    assert cfg["notes"] == [
        "config: [[devices]] entry 3: (phone) enabled = 'yes' is not true or false — true",
        "config: [[devices]] is listed, so [midi] is ignored — its midi entry says",
        *cfg["problems"],
    ]
    assert "error" not in cfg
    err = capsys.readouterr().err
    assert all(n in err for n in cfg["notes"])
    # `devices = 3`, or an entry that is not a table: a problem, the rest stand
    p.write_text("devices = 3\n")
    cfg = config.load(p)
    assert config.devices(cfg) == [] and "error" not in cfg
    assert cfg["problems"] == ["config: devices = 3 is not a list of [[devices]] tables"]
    p.write_text('devices = [{role = "a", kind = "midi"}, 7]\n')
    cfg = config.load(p)
    assert [e["role"] for e in config.devices(cfg)] == ["a"]
    assert cfg["problems"] == ["config: [[devices]] entry 2 is not a table (7) — dropped"]
    # any other top-level list is still an error, as before
    p.write_text("[[midi]]\nenabled = true\n")
    assert "[midi] must be a table" in config.load(p)["error"]


def test_read_devices_reports_problems_and_prints_nothing(tmp_path, capsys):
    """The registry's re-read: the checked entries and every reason to
    keep the old list — a file that will not parse first — with nothing
    on stderr (the launch said what there was to say)."""
    p = tmp_path / "config.toml"
    p.write_text('[midi]\nenabled = false\n[[devices]]\nrole = "a"\nkind = "midi"\n')
    entries, problems = config.read_devices(p)
    assert [e["role"] for e in entries] == ["a"] and problems == []
    p.write_text('[[devices]]\nrole = "a"\nkind = "midi"\n[[devices]]\nrole = "a"\nkind = "midi"\n')
    entries, problems = config.read_devices(p)
    assert [e["role"] for e in entries] == ["a"]
    assert problems == ["config: [[devices]] entry 2: role 'a' is listed twice — the second dropped"]
    p.write_text("[[devices\n")
    entries, problems = config.read_devices(p)
    assert len(problems) == 1 and problems[0].startswith("config: ")
    assert [e["role"] for e in entries] == ["pad", "apc40", "leap", "bridge"]   # the defaults
    assert capsys.readouterr().err == ""
