"""Wave 5 CT1: `<library>/devices.json`, the controllers both Macs share.

A role is a row's address, so most of this holds one thing against every way a list can
come about: no order of adopting, plugging in or syncing renames a role a saved row names.
Two Macs are two `DeviceList`s with their own homes over one library folder; Drive is a test
writing into that folder. Nothing here reaches a real library.
"""

import ast
import importlib.util
import inspect
import itertools
import json
import sys
from pathlib import Path

import pytest

import hyperspace
from hyperspace import app, config, devicelist, devices
from hyperspace.devicelist import (
    COPY,
    DEFAULTS,
    FILE,
    HOLD_S,
    SCHEMA,
    DeviceList,
    midi_entry,
    pad_entry,
)
from hyperspace.library import Library
from hyperspace.pads import models
from hyperspace.players import Players

PKG = Path(hyperspace.__file__).parent
TOOLS = PKG.parent / "tools"
LIST = [{"role": "pad", "kind": "gamepad", "controller": "any"},
        {"role": "apc40", "kind": "midi", "port": "APC40"},
        {"role": "p2", "kind": "gamepad", "controller": "edge", "light": "#ff0000"}]
LAUNCH = midi_entry("Launch Control XL")
XBOX, EDGE = pad_entry(models.MODELS["xbox"]), pad_entry(models.MODELS["edge"])


class Clock:
    t = 100.0

    def __call__(self):
        return self.t


@pytest.fixture()
def macs(tmp_path):
    """The library, and two homes."""
    root, one, two = tmp_path / "Drive", tmp_path / "one", tmp_path / "two"
    for d in (root, one, two):
        d.mkdir()
    return root, one, two


def on_disk(root) -> list[dict]:
    doc = json.loads((root / FILE).read_text())
    assert doc["schema"] == SCHEMA
    return doc["devices"]


def roles(raw) -> list[str]:
    return [e["role"] for e in raw]


def lands(root, raw) -> None:
    """Drive puts a list in the folder, from the other Mac."""
    (root / FILE).write_text(json.dumps({"schema": SCHEMA, "devices": raw}))


def toml(home, text) -> dict:
    p = home / "config.toml"
    p.write_text(text)
    return config.load(p)


LISTED = """
[library]
path = "{root}"

[[devices]]
role = "pad"
kind = "gamepad"

[[devices]]
role = "launch"
kind = "midi"
profile = "generic"
port = "Launch Control"
"""


# ---------------------------------------------------------------- the seed

def test_config_toml_is_read_once_and_then_says_nothing(macs):
    root, one, _ = macs
    cfg = toml(one, LISTED.format(root=root))
    DeviceList.open(cfg, one)
    assert roles(on_disk(root)) == ["pad", "launch"]
    assert {e["role"]: e["enabled"] for e in config.devices(cfg)} == {"pad": True, "launch": True}
    assert any("made from" in n for n in cfg["notes"])
    # an edit to config.toml afterwards lands nowhere, and is told so
    cfg = toml(one, LISTED.format(root=root) + '\n[[devices]]\nrole = "later"\nkind = "gamepad"\n')
    DeviceList.open(cfg, one)
    assert roles(on_disk(root)) == ["pad", "launch"]
    assert [e["role"] for e in config.devices(cfg)] == ["pad", "launch"]
    assert any("is not read" in n for n in cfg["notes"])


def test_the_seed_is_held_as_it_was_written_and_a_bad_entry_stays_out(macs):
    root, one, _ = macs
    cfg = toml(one, LISTED.format(root=root) + '\nlight = "#00ff00"\n[[devices]]\nrole = "no:colon"\nkind = "gamepad"\n')
    DeviceList.open(cfg, one)
    assert on_disk(root) == [{"role": "pad", "kind": "gamepad"},
                             {"role": "launch", "kind": "midi", "profile": "generic",
                              "port": "Launch Control", "light": "#00ff00"}]


def test_the_other_mac_adds_only_what_the_list_lacks_and_only_once(macs):
    root, one, two = macs
    DeviceList.open(toml(one, LISTED.format(root=root)), one)
    second = LISTED.format(root=root).replace('"Launch Control"', '"Other"') + (
        '\n[[devices]]\nrole = "joy"\nkind = "gamepad"\ncontroller = "joycon-l"\n')
    cfg = toml(two, second)
    DeviceList.open(cfg, two)
    got = on_disk(root)
    assert roles(got) == ["pad", "launch", "joy"]
    assert next(e for e in got if e["role"] == "launch")["port"] == "Launch Control", "the file's stands"
    assert any("says otherwise of launch" in n for n in cfg["notes"])
    assert (two / COPY).exists()
    # it was read once on this Mac: gone from the list by hand, it stays gone
    lands(root, [e for e in got if e["role"] != "joy"])
    DeviceList.open(toml(two, second), two)
    assert roles(on_disk(root)) == ["pad", "launch"]


def test_a_file_that_says_nothing_seeds_the_defaults_that_cl3_needs(tmp_path):
    empty = config.load(tmp_path / "config.toml")
    assert empty["device_seed"] == [dict(e) for e in DEFAULTS]
    assert not empty["device_seed_listed"]
    entries, problems, _ = config.listed_devices(DEFAULTS, tmp_path)
    assert not problems
    assert entries == config.devices(empty), "the same devices as the old tables translated"


def test_a_table_saying_off_is_this_macs_and_stays_out_of_the_list(macs):
    root, one, two = macs
    cfg = toml(one, f'[library]\npath = "{root}"\n[gamepad]\nenabled = false\ndial_left = "blend"\n[hands]\nenabled = true\n')
    DeviceList.open(cfg, one)
    got = {e["role"]: e for e in on_disk(root)}
    assert "enabled" not in got["pad"] and got["pad"]["dial_left"] == "blend"
    assert got["leap"]["enabled"] is True, "off unless said, so the list must say"
    assert next(e for e in config.devices(cfg) if e["role"] == "pad")["enabled"] is False
    assert cfg["gamepad"]["enabled"] is False
    # …and the other Mac, whose file says nothing of it, has its pad on
    cfg = toml(two, f'[library]\npath = "{root}"\n')
    DeviceList.open(cfg, two)
    assert next(e for e in config.devices(cfg) if e["role"] == "pad")["enabled"] is True


def test_midi_off_on_this_mac_means_no_look_even_with_a_list(macs):
    root, one, _ = macs
    store = DeviceList.open(toml(one, f'[library]\npath = "{root}"\n[midi]\nenabled = false\n'), one)
    assert store.no_midi_look
    lst = LISTED.format(root=root)
    assert not DeviceList.open(toml(one, lst), one).no_midi_look
    # a list with no MIDI folds [midi] off; that isn't this Mac saying so
    store = DeviceList.open(toml(one, f'[library]\npath = "{root}"\n[[devices]]\nrole = "pad"\nkind = "gamepad"\n'), one)
    assert not store.no_midi_look


def test_a_relative_path_means_this_macs_home_and_stays_relative_in_the_file(macs):
    root, one, two = macs
    raw = [{"role": "pad", "kind": "gamepad", "tape": "tapes/a.jsonl"}]
    lands(root, raw)
    assert on_disk(root) == raw
    for home in (one, two):
        entries, _, _ = DeviceList(root, home).checked()
        assert entries[0]["tape"] == str(home / "tapes/a.jsonl")
    assert on_disk(root) == raw


# ---------------------------------------------------------------- stable roles

ALL = {"APC40": midi_entry("Akai APC40"), "Launch": LAUNCH, "IAC 1": midi_entry("IAC Driver Bus 1"),
       "IAC 2": midi_entry("IAC Driver Bus 2"), "edge": EDGE, "xbox": XBOX,
       "joy": pad_entry(models.MODELS["joycon-l"]), "usb": pad_entry(models.MODELS["generic"], 0x1234, 0xabcd)}


def _mapping(store) -> dict[tuple, str]:
    return {tuple(sorted((k, str(v)) for k, v in e.items() if k != "role")): e["role"] for e in store.raw}


def test_any_order_of_adopting_gives_every_controller_the_same_role(tmp_path):
    want = None
    for i, order in enumerate(itertools.permutations(ALL)):
        if i % 97:                      # (8! orders: a spread of them)
            continue
        root = tmp_path / str(i)
        root.mkdir()
        store = DeviceList(root, seed=LIST)
        for name in order:
            store.adopt(ALL[name])
        got = _mapping(store)
        want = want if want is not None else got
        assert got == want, order
        assert roles(store.raw)[:3] == roles(LIST), "what was there stays first, as it was"
        assert store.raw[:3] == LIST


def test_both_macs_name_one_controller_alike_with_nothing_between_them(macs, tmp_path):
    root, one, two = macs
    other = tmp_path / "other"
    other.mkdir()
    for entry in ALL.values():
        assert DeviceList(root, one, seed=LIST).role_for(entry) == DeviceList(other, two, seed=LIST).role_for(entry)


@pytest.mark.parametrize(("port", "role"), [
    ("Akai APC40", "apc40"), ("APC40 mkII", "apc40"), ("Launch Control XL", "launch-control-xl"),
    ("IAC Driver Bus 1", "iac-driver-bus-1"), ("IAC Driver Bus 2", "iac-driver-bus-2"),
    ("a:b@c", "a-b-c"), ("???", "controller")])
def test_a_ports_role_is_from_its_name(port, role):
    assert midi_entry(port)["role"] == role


def test_a_role_is_never_a_players_name_nor_one_taken(tmp_path):
    store = DeviceList(tmp_path, seed=[{"role": "launch", "kind": "midi", "profile": "generic", "port": "x"}])
    assert store.adopt(midi_entry("P2")) == "p2-2", "@p2 always means player 2"
    assert store.adopt(midi_entry("Launch")) == "launch-2"
    assert store.adopt(midi_entry("Hands DAW")) == "hands-daw-2"


def test_the_same_port_twice_is_one_controller_and_the_same_pad_twice_is_two_seats(tmp_path):
    store = DeviceList(tmp_path, seed=[])
    assert store.adopt(LAUNCH) == store.adopt(LAUNCH) == "launch-control-xl"
    assert roles(store.raw) == ["launch-control-xl"]
    assert [store.adopt(XBOX), store.adopt(XBOX)] == ["xbox", "xbox-2"]
    assert store.role_for(XBOX) == "xbox-3"
    assert all(e["controller"] == "xbox" for e in store.raw if e["kind"] == "gamepad")


def test_adopting_moves_no_saved_rows_address(tmp_path):
    """What a row names is the role and, for a pad, its qualifier: a second pad on one
    player must not take the first's name."""
    seed = [{"role": "pad", "kind": "gamepad"}, {"role": "apc40", "kind": "midi"},
            {"role": "p2", "kind": "gamepad"}]
    def names(raw):
        players = Players()
        entries, _, _ = config.listed_devices(raw, tmp_path)
        return devices.qualifiers_of(entries, players)
    before = names(seed)
    assert before == {"pad": "", "p2": "p2"}
    for order in itertools.permutations([XBOX, EDGE, LAUNCH]):
        root = tmp_path / "-".join(e["role"] for e in order)
        root.mkdir()
        store = DeviceList(root, seed=seed)
        for e in order:
            store.adopt(e)
        got = names(store.raw)
        assert {k: got[k] for k in before} == before, order
        assert got["xbox"] == "xbox" and got["edge"] == "edge", "held by player 1 second: by role"


def test_a_generic_desk_beside_the_apc40_never_takes_its_rows(tmp_path):
    store = DeviceList(tmp_path, seed=[])
    store.adopt(LAUNCH)
    store.adopt(midi_entry("Akai APC40"))
    entries, _, _ = store.checked()
    reg = devices.DeviceRegistry(entries, devices.Context())
    assert reg.midi_roles()[0] == "apc40"


# ---------------------------------------------------------------- the library not there

def test_an_unmounted_drive_starts_on_this_macs_seed_and_creates_nothing(tmp_path):
    root, home = tmp_path / "Drive", tmp_path / "home"
    home.mkdir()
    notes: list[str] = []
    store = DeviceList(root, home, seed=LIST, listed=True, notes=notes)
    assert store.raw == LIST and not root.exists()
    assert "isn't there" in store.said and "config.toml" in store.said
    assert any("isn't there" in n for n in notes)


def test_an_unmounted_drive_starts_on_the_last_list_seen(macs):
    root, home, _ = macs
    lands(root, LIST)
    DeviceList(root, home, seed=[])
    (root / FILE).unlink()
    root.rmdir()
    store = DeviceList(root, home, seed=[{"role": "other", "kind": "gamepad"}])
    assert store.raw == LIST
    assert "last list" in store.said and not root.exists()


def test_an_adopt_with_no_drive_stands_survives_a_restart_and_lands_when_it_is_back(tmp_path):
    root, home = tmp_path / "Drive", tmp_path / "home"
    home.mkdir()
    store = DeviceList(root, home, seed=LIST)
    assert store.adopt(XBOX) == "xbox"
    assert roles(store.raw)[-1] == "xbox" and not root.exists()
    assert store.said
    assert not store.look(), "still not there"
    again = DeviceList(root, home, seed=LIST)
    assert roles(again.raw)[-1] == "xbox", "kept in this Mac's copy"
    # the Drive mounts, with the other Mac's list in it, and no restart
    root.mkdir()
    lands(root, [*LIST, EDGE])
    assert again.look()
    assert roles(on_disk(root)) == [*roles(LIST), "edge", "xbox"]
    assert again.said == "" and roles(again.raw) == [*roles(LIST), "edge", "xbox"]


def test_this_macs_seed_still_reaches_the_list_after_a_first_launch_with_no_drive(tmp_path):
    root, home = tmp_path / "Drive", tmp_path / "home"
    home.mkdir()
    DeviceList(root, home, seed=[{"role": "mine", "kind": "gamepad"}], listed=True)
    root.mkdir()
    lands(root, LIST)
    store = DeviceList(root, home, seed=[{"role": "mine", "kind": "gamepad"}], listed=True)
    assert roles(store.raw) == [*roles(LIST), "mine"]
    assert roles(on_disk(root)) == [*roles(LIST), "mine"]


def test_the_drive_going_away_mid_run_leaves_the_list_alone(macs):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    (root / FILE).unlink()
    root.rmdir()
    assert not store.look()
    assert store.raw == LIST and "isn't there" in store.said


def test_a_folder_with_no_file_gets_the_list_back(macs):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    (root / FILE).unlink()
    assert not store.look()
    assert on_disk(root) == LIST


# ---------------------------------------------------------------- the other Mac

def test_a_change_from_the_other_mac_lands_and_our_own_write_does_not_read_as_one(macs):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    assert not store.look()
    store.adopt(XBOX)
    assert not store.look(), "our own write"
    lands(root, [*store.raw, EDGE])
    assert store.look()
    assert roles(store.raw)[-1] == "edge"
    assert not store.look()


def test_drive_touching_the_file_is_no_change(macs):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    lands(root, LIST)
    assert not store.look()


@pytest.mark.parametrize("text", ['{"schema": "devices/1", "devi', '{"schema": "devices/2", "devices": []}',
                                  '{"schema": "devices/1", "devices": 3}', '[]', ''])
def test_a_list_that_will_not_read_is_never_written_over_and_is_read_again(macs, text):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    (root / FILE).write_text(text)
    assert not store.look()
    assert store.raw == LIST and "could not be read" in store.said
    assert store.adopt(XBOX) == "xbox", "an adopt still stands for this run"
    assert (root / FILE).read_text() == text
    lands(root, LIST)
    assert not store.look(), "the sync finished, and the list this Mac has is what it says"
    assert store.said == ""
    assert roles(on_disk(root)) == [*roles(LIST), "xbox"], "and the adopt reached it"


def test_a_file_landing_without_our_adopt_gets_it_back_and_no_one_fights(macs):
    root, one, two = macs
    clock = Clock()
    a = DeviceList(root, one, seed=LIST, clock=clock)
    b = DeviceList(root, two, seed=LIST, clock=clock)
    before = (root / FILE).read_text()
    assert a.adopt(XBOX) == "xbox"
    # Mac B's adopt, from a file before A's: Drive's last writer drops A's
    (root / FILE).write_text(before)
    assert b.adopt(EDGE) == "edge"
    assert roles(on_disk(root)) == [*roles(LIST), "edge"]
    assert a.look(), "A's is put back"
    assert set(roles(on_disk(root))) == {*roles(LIST), "xbox", "edge"}
    assert b.look()
    settled = (root / FILE).read_text()
    for _ in range(4):
        assert not a.look() and not b.look()
    assert (root / FILE).read_text() == settled
    assert set(roles(a.raw)) == set(roles(b.raw)) == {*roles(LIST), "xbox", "edge"}


def test_a_removal_by_hand_stands_once_the_hold_is_over(macs):
    root, home, _ = macs
    clock = Clock()
    store = DeviceList(root, home, seed=LIST, clock=clock)
    store.adopt(XBOX)
    clock.t += HOLD_S + 1
    lands(root, LIST)
    assert store.look()
    assert roles(store.raw) == roles(LIST) and roles(on_disk(root)) == roles(LIST)


def test_one_name_for_two_controllers_keeps_the_files_and_ours_moves(macs):
    root, one, two = macs
    a = DeviceList(root, one, seed=[])
    b = DeviceList(root, two, seed=[])
    before = (root / FILE).read_text()
    a.adopt(midi_entry("Foo Bar"))
    (root / FILE).write_text(before)
    b.adopt(midi_entry("foo-bar"))
    assert a.look()
    got = {e["role"]: e["port"] for e in on_disk(root)}
    assert got == {"foo-bar": "foo-bar", "foo-bar-2": "Foo Bar"}
    assert any("the other Mac named" in n for n in a.notes)


def test_a_write_that_fails_is_said_kept_and_tried_again(macs, monkeypatch):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    real = devicelist.DeviceList._write
    monkeypatch.setattr(devicelist.DeviceList, "_write", lambda self, raw: self._say("not written") or False)
    assert store.adopt(XBOX) == "xbox"
    assert roles(on_disk(root)) == roles(LIST) and store.said == "not written"
    monkeypatch.setattr(devicelist.DeviceList, "_write", real)
    assert not store.look()
    assert roles(on_disk(root))[-1] == "xbox" and store.said == ""


# ---------------------------------------------------------------- where it stands

def test_a_root_file_is_safe_in_the_library(tmp_path):
    root, home = tmp_path / "Drive", tmp_path / "home"
    root.mkdir()
    home.mkdir()
    lib = Library(root, machine=home)
    groups = lib.groups()
    DeviceList(root, home, seed=LIST)
    (root / f"{FILE}.123.tmp").write_text("half")
    assert lib.groups() == groups
    spec = importlib.util.spec_from_file_location("migrate_library_ct1", TOOLS / "migrate_library.py")
    tool = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = tool
    try:
        spec.loader.exec_module(tool)
        todo, said = tool.group_plan(root)
        assert not todo and not any(FILE in s for s in said)
        assert not tool.loadable_files(root) and not tool.show_files(root)
    finally:
        del sys.modules[spec.name]


def test_this_macs_own_files_stay_in_its_home(macs):
    root, home, _ = macs
    DeviceList(root, home, seed=LIST)
    assert sorted(p.name for p in home.iterdir()) == [COPY]
    assert sorted(p.name for p in root.iterdir()) == [FILE]


def test_with_the_library_in_the_home_there_is_no_copy(tmp_path):
    DeviceList(tmp_path, tmp_path, seed=LIST)
    assert sorted(p.name for p in tmp_path.iterdir()) == [FILE]


def test_no_patch_reaches_the_list():
    """Two layers: the list is the meta controller's. Only the app, the registry's owner,
    and the board import it, and it holds none of a patch's words."""
    importers = set()
    for path in PKG.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if (isinstance(node, ast.ImportFrom) and node.level and (
                    node.module == "devicelist" or (not node.module and any(a.name == "devicelist" for a in node.names)))):
                importers.add(path.name)
    assert importers == {"app.py", "ui_players.py"}
    assert not {"library", "loadable", "patches", "deck", "graph"} & {
        n.name for node in ast.walk(ast.parse(inspect.getsource(devicelist)))
        if isinstance(node, ast.ImportFrom) for n in node.names}


def test_main_reads_the_list_before_the_windows_and_the_library():
    src = inspect.getsource(app.main)
    at = src.index("DeviceList.open(cfg, home)")
    assert at < src.index("_windows(") and at < src.index("Library(")
    assert at < src.index("Players.load(home") < src.index("_open_devices(cfg")
    assert "store=device_list" in src
