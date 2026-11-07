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
import time
from pathlib import Path

import pytest

import hyperspace
from hyperspace import app, config, devicelist, devices
from hyperspace.devicelist import (
    COPY,
    DEFAULTS,
    FILE,
    HERE,
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


def looked(store) -> bool:
    """A whole cycle of the worker, then what the registry's `watch` would ask."""
    store.sync()
    return store.look()


def opened(cfg, home) -> DeviceList:
    """A launch, and its own files written, as they are long before the next one."""
    store = DeviceList.open(cfg, home)
    store.sync()
    return store


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
    opened(cfg, one)
    assert roles(on_disk(root)) == ["pad", "launch"]
    assert {e["role"]: e["enabled"] for e in config.devices(cfg)} == {"pad": True, "launch": True}
    assert any("made from" in n for n in cfg["notes"])
    # an edit to config.toml afterwards lands nowhere, and is told so
    cfg = toml(one, LISTED.format(root=root) + '\n[[devices]]\nrole = "later"\nkind = "gamepad"\n')
    opened(cfg, one)
    assert roles(on_disk(root)) == ["pad", "launch"]
    assert [e["role"] for e in config.devices(cfg)] == ["pad", "launch"]
    assert any("is not read" in n for n in cfg["notes"])


def test_the_seed_is_held_as_it_was_written_and_a_bad_entry_stays_out(macs):
    root, one, _ = macs
    cfg = toml(one, LISTED.format(root=root) + '\nlight = "#00ff00"\n[[devices]]\nrole = "no:colon"\nkind = "gamepad"\n')
    opened(cfg, one)
    assert on_disk(root) == [{"role": "pad", "kind": "gamepad"},
                             {"role": "launch", "kind": "midi", "profile": "generic",
                              "port": "Launch Control", "light": "#00ff00"}]


def test_the_other_mac_adds_only_what_the_list_lacks_and_only_once(macs):
    root, one, two = macs
    opened(toml(one, LISTED.format(root=root)), one)
    second = LISTED.format(root=root).replace('"Launch Control"', '"Other"') + (
        '\n[[devices]]\nrole = "joy"\nkind = "gamepad"\ncontroller = "joycon-l"\n')
    cfg = toml(two, second)
    opened(cfg, two)
    got = on_disk(root)
    assert roles(got) == ["pad", "launch", "joy"]
    assert next(e for e in got if e["role"] == "launch")["port"] == "Launch Control", "the file's stands"
    assert any("says otherwise of launch" in n for n in cfg["notes"])
    assert (two / COPY).exists() and (two / HERE).exists()
    # it was read once on this Mac: gone from the list by hand, it stays gone
    lands(root, [e for e in got if e["role"] != "joy"])
    opened(toml(two, second), two)
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
    opened(cfg, one)
    got = {e["role"]: e for e in on_disk(root)}
    assert "enabled" not in got["pad"] and got["pad"]["dial_left"] == "blend"
    assert got["leap"]["enabled"] is True, "off unless said, so the list must say"
    assert next(e for e in config.devices(cfg) if e["role"] == "pad")["enabled"] is False
    assert cfg["gamepad"]["enabled"] is False
    # …and the other Mac, whose file says nothing of it, has its pad on
    cfg = toml(two, f'[library]\npath = "{root}"\n')
    opened(cfg, two)
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
    DeviceList(root, home, seed=[]).sync()
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
    assert not looked(store), "still not there"
    assert store.said
    again = DeviceList(root, home, seed=LIST)
    assert roles(again.raw)[-1] == "xbox", "kept in this Mac's copy"
    # the Drive mounts, with the other Mac's list in it, and no restart
    root.mkdir()
    lands(root, [*LIST, EDGE])
    assert looked(again)
    assert roles(on_disk(root)) == [*roles(LIST), "edge", "xbox"]
    assert again.said == "" and roles(again.raw) == [*roles(LIST), "edge", "xbox"]


def test_this_macs_seed_still_reaches_the_list_after_a_first_launch_with_no_drive(tmp_path):
    root, home = tmp_path / "Drive", tmp_path / "home"
    home.mkdir()
    DeviceList(root, home, seed=[{"role": "mine", "kind": "gamepad"}], listed=True).sync()
    root.mkdir()
    lands(root, LIST)
    store = DeviceList(root, home, seed=[{"role": "mine", "kind": "gamepad"}], listed=True)
    store.sync()
    assert roles(store.raw) == [*roles(LIST), "mine"]
    assert roles(on_disk(root)) == [*roles(LIST), "mine"]


def test_the_drive_going_away_mid_run_leaves_the_list_alone(macs):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    (root / FILE).unlink()
    root.rmdir()
    assert not looked(store)
    assert store.raw == LIST and "isn't there" in store.said


def test_a_folder_with_no_file_gets_the_list_back(macs):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    (root / FILE).unlink()
    assert not looked(store)
    store.sync()
    assert on_disk(root) == LIST


# ---------------------------------------------------------------- the other Mac

def test_a_change_from_the_other_mac_lands_and_our_own_write_does_not_read_as_one(macs):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    assert not looked(store)
    store.adopt(XBOX)
    store.sync()
    assert not store.look(), "adopting isn't news, and nor is our own write"
    assert not looked(store)
    lands(root, [*store.raw, EDGE])
    assert looked(store)
    assert roles(store.raw)[-1] == "edge"
    assert not looked(store)


def test_drive_touching_the_file_is_no_change(macs):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    lands(root, LIST)
    assert not looked(store)


@pytest.mark.parametrize("text", ['{"schema": "devices/1", "devi', '{"schema": "devices/2", "devices": []}',
                                  '{"schema": "devices/1", "devices": 3}', '[]', ''])
def test_a_list_that_will_not_read_is_never_written_over_and_is_read_again(macs, text):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    (root / FILE).write_text(text)
    assert not looked(store)
    assert store.raw == LIST and "could not be read" in store.said
    assert store.adopt(XBOX) == "xbox", "an adopt still stands for this run"
    assert (root / FILE).read_text() == text
    lands(root, LIST)
    assert not looked(store), "the sync finished, and the list this Mac has is what it says"
    assert store.said == ""
    assert roles(on_disk(root)) == [*roles(LIST), "xbox"], "and the adopt reached it"


def test_a_file_landing_without_our_adopt_gets_it_back_and_no_one_fights(macs):
    root, one, two = macs
    clock = Clock()
    a = DeviceList(root, one, seed=LIST, clock=clock)
    b = DeviceList(root, two, seed=LIST, clock=clock)
    a.sync()
    b.sync()
    before = (root / FILE).read_text()
    assert a.adopt(XBOX) == "xbox"
    a.sync()
    # Mac B's adopt, from a file before A's: Drive's last writer drops A's
    (root / FILE).write_text(before)
    assert b.adopt(EDGE) == "edge"
    b.sync()
    assert roles(on_disk(root)) == [*roles(LIST), "edge"]
    assert looked(a), "A's is put back"
    assert set(roles(on_disk(root))) == {*roles(LIST), "xbox", "edge"}
    assert looked(b)
    settled = (root / FILE).read_text()
    for _ in range(4):
        assert not looked(a) and not looked(b)
    assert (root / FILE).read_text() == settled
    assert set(roles(a.raw)) == set(roles(b.raw)) == {*roles(LIST), "xbox", "edge"}


def test_a_removal_by_hand_stands_once_the_hold_is_over(macs):
    root, home, _ = macs
    clock = Clock()
    store = DeviceList(root, home, seed=LIST, clock=clock)
    store.adopt(XBOX)
    store.sync()
    clock.t += HOLD_S + 1
    store.look()
    store.sync()
    lands(root, LIST)
    assert looked(store)
    assert roles(store.raw) == roles(LIST) and roles(on_disk(root)) == roles(LIST)


def test_one_name_for_two_controllers_keeps_the_files_and_ours_moves(macs):
    root, one, two = macs
    a = DeviceList(root, one, seed=[])
    b = DeviceList(root, two, seed=[])
    before = (root / FILE).read_text()
    a.adopt(midi_entry("Foo Bar"))
    a.sync()
    (root / FILE).write_text(before)
    b.adopt(midi_entry("foo-bar"))
    b.sync()
    assert looked(a)
    got = {e["role"]: e["port"] for e in on_disk(root)}
    assert got == {"foo-bar": "foo-bar", "foo-bar-2": "Foo Bar"}
    assert any("the other Mac named" in n for n in a.notes)


def test_a_write_that_fails_is_said_kept_and_tried_again(macs, monkeypatch):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    real = devicelist._put

    def refused(path, text, tmp=None):
        if path.name == FILE:
            raise OSError("read-only")
        real(path, text, tmp)
    monkeypatch.setattr(devicelist, "_put", refused)
    assert store.adopt(XBOX) == "xbox"
    store.sync()
    assert roles(on_disk(root)) == roles(LIST) and "not written (read-only)" in store.said
    monkeypatch.setattr(devicelist, "_put", real)
    store.sync()
    assert roles(on_disk(root))[-1] == "xbox" and store.said == ""


# ---------------------------------------------------------------- what's in the file (review 1)

BAD_BYTES = [b"", b"\xff\xfe\x00garbage", b'{"schema": "devices/1", "devi', b"[]", b"null", b"3", b"\x00" * 64,
             b'{"schema": "devices/1"}', b'{"schema": "devices/1", "devices": [1]}',
             b'{"schema": "devices/1", "devices": {"a": 1}}', b'{"schema": ["x"], "devices": []}',
             b"[" * 200_000, '{"schema": "devices/1", "devices": [{"role": "\u00e9'.encode("latin-1")]


@pytest.mark.parametrize("data", BAD_BYTES)
def test_no_bytes_in_the_file_reach_a_launch_or_a_look(macs, data):
    root, home, _ = macs
    (root / FILE).write_bytes(data)
    store = DeviceList(root, home, seed=LIST)
    assert store.raw == LIST and "could not be read" in store.said
    assert not looked(store)
    assert (root / FILE).read_bytes() == data, "never written over"
    (root / FILE).write_bytes(json.dumps({"schema": SCHEMA, "devices": LIST}).encode())
    assert not looked(store) and store.said == ""


@pytest.mark.parametrize("data", BAD_BYTES)
def test_no_bytes_in_this_macs_own_files_stop_a_launch(macs, data):
    root, home, _ = macs
    lands(root, LIST)
    (home / COPY).write_bytes(data)
    (home / HERE).write_bytes(data)
    assert DeviceList(root, home, seed=[]).raw == LIST


FUZZ = [{"role": 3, "kind": "gamepad"}, {"role": ["x"], "kind": []}, {"kind": "midi"}, {},
        {"role": "a", "kind": "gamepad", "controller": 5, "light": [], "player": "x", "joystick": {}, "tape": 1},
        {"role": "b", "kind": "midi", "port": 5, "profile": {}}, {"role": "c", "kind": "hands", "map": 3, "out": 9},
        {"role": "d", "kind": "bridge", "send": 7}, {"role": "e", "kind": "nonesuch", "enabled": "yes"},
        {"role": "f", "kind": "midi-out", "port": [], "carries": 1}, {"role": "x" * 5000, "kind": "osc"}]


@pytest.mark.parametrize("entry", FUZZ)
def test_no_entry_in_the_list_raises_out_of_a_watch(macs, entry):
    root, home, _ = macs
    store = DeviceList(root, home, seed=LIST)
    reg = devices.DeviceRegistry([], devices.Context(), store=store)
    lands(root, [*LIST, entry])
    store.sync()
    reg.watch()         # (the old list, or a new one with a device in error: neither raises)
    assert store.look() is False


@pytest.mark.parametrize("entry", FUZZ)
def test_no_entry_in_the_list_stops_a_launch(macs, entry):
    root, home, _ = macs
    lands(root, [*LIST, entry])
    cfg = toml(home, f'[library]\npath = "{root}"\n')
    store = DeviceList.open(cfg, home)
    devices.DeviceRegistry(config.devices(cfg), devices.Context(), store=store)


# ---------------------------------------------------------------- a config.toml that didn't read (review 2)

def test_a_config_that_did_not_read_seeds_nothing_and_spends_nothing(macs):
    root, home, _ = macs
    broken = LISTED.format(root=root).replace('[library]\npath = "', '[library\npath = "')
    cfg = toml(home, broken)
    assert cfg.get("error") and "device_seed" not in cfg
    # (it can't read [library] path either, so give it the library as the home's: the worst case)
    cfg["library"]["path"] = str(root)
    store = opened(cfg, home)
    assert "didn't read" in store.said and any("didn't read" in n for n in cfg["notes"])
    assert not (root / FILE).exists(), "defaults aren't written for both Macs"
    assert not (home / HERE).exists(), "and the read isn't spent"
    # the typo fixed: its list is read after all
    opened(toml(home, LISTED.format(root=root)), home)
    assert roles(on_disk(root)) == ["pad", "launch"]
    assert (home / HERE).exists()


def test_a_config_that_did_not_read_starts_on_the_list_there_is(macs):
    root, home, _ = macs
    lands(root, LIST)
    cfg = toml(home, "[library")
    cfg["library"]["path"] = str(root)
    store = opened(cfg, home)
    assert store.raw == LIST and [e["role"] for e in config.devices(cfg)] == roles(LIST)


def _broken(root, home):
    """A launch whose config.toml didn't read, though the library's path is known."""
    cfg = toml(home, "[library")
    cfg["library"]["path"] = str(root)
    return opened(cfg, home)


def test_an_adopt_with_a_config_that_did_not_read_makes_no_file_of_defaults(macs):
    root, home, _ = macs
    store = _broken(root, home)
    assert store.adopt(XBOX) == "xbox"
    store.sync()
    assert not (root / FILE).exists(), "third pass: it would bring pad and apc40 for both Macs"
    assert "xbox" in roles(store.raw) and "didn't read" in store.said, "it stands for this run"
    # the typo fixed: this Mac's own list, and the adopt
    opened(toml(home, LISTED.format(root=root)), home)
    assert roles(on_disk(root)) == ["pad", "launch", "xbox"]
    assert (home / HERE).exists()


def test_an_adopt_survives_two_launches_that_did_not_read(macs):
    root, home, _ = macs
    first = _broken(root, home)
    first.adopt(XBOX)
    first.close()          # (its copy, written on a worker: a quit waits for it)
    store = _broken(root, home)
    store.sync()
    assert "xbox" in roles(store.raw) and "pad" in roles(store.raw)
    assert not (root / FILE).exists()
    opened(toml(home, LISTED.format(root=root)), home)
    assert roles(on_disk(root)) == ["pad", "launch", "xbox"]


def test_an_old_tables_seed_is_not_lost_to_a_broken_launchs_copy(macs):
    root, home, _ = macs
    _broken(root, home).sync()
    text = f'[library]\npath = "{root}"\n[midi]\nprofile = "generic"\nport = "Box"\n'
    opened(toml(home, text), home)
    assert "generic" in roles(on_disk(root))


def test_an_adopt_with_a_config_that_did_not_read_lands_in_a_list_that_is_there(macs):
    root, home, _ = macs
    lands(root, LIST)
    store = _broken(root, home)
    store.adopt(XBOX)
    store.sync()
    assert roles(on_disk(root)) == [*roles(LIST), "xbox"], "no defaults to bring: it's the file's list"
    assert "didn't read" in store.said


# ---------------------------------------------------------------- a seed across a restart (review 3)

def test_a_seed_entry_stays_a_seed_across_a_restart_with_no_drive(tmp_path):
    root, home = tmp_path / "Drive", tmp_path / "home"
    home.mkdir()
    seed = [{"role": "pad", "kind": "gamepad", "controller": "edge"}]
    DeviceList(root, home, seed=seed, listed=True).sync()
    assert json.loads((home / COPY).read_text())["unwritten"][0]["adopted"] is False
    again = DeviceList(root, home, seed=seed, listed=True)
    assert again.waiting["pad"].adopted is False
    root.mkdir()
    lands(root, [{"role": "pad", "kind": "gamepad", "controller": "any"}])
    again.sync()
    assert roles(on_disk(root)) == ["pad"], "the file's stands: no pad-2 for a seed"


def test_an_adopt_stays_an_adopt_across_a_restart(tmp_path):
    root, home = tmp_path / "Drive", tmp_path / "home"
    home.mkdir()
    store = DeviceList(root, home, seed=[])
    store.adopt(XBOX)
    store.sync()
    again = DeviceList(root, home, seed=[])
    assert again.waiting["xbox"].adopted is True
    root.mkdir()
    lands(root, [{"role": "xbox", "kind": "midi", "profile": "generic", "port": "Other"}])
    again.sync()
    assert roles(on_disk(root)) == ["xbox", "xbox-2"], "a different controller: it takes a free name"


# ---------------------------------------------------------------- MIDI names (reviews 4, 6)

def test_an_apc40_named_or_not_is_one_controller(tmp_path):
    for listed in ({"role": "apc40", "kind": "midi", "port": "APC40"}, {"role": "apc40", "kind": "midi"},
                   {"role": "desk", "kind": "midi", "profile": "apc40", "port": "apc40"}):
        store = DeviceList(tmp_path, seed=[listed])
        assert store.adopt(midi_entry("Akai APC40")) == listed["role"]
        assert len(store.raw) == 1
        (tmp_path / FILE).unlink()


def test_a_desk_with_its_own_name_is_its_own_controller(tmp_path):
    store = DeviceList(tmp_path, seed=[{"role": "apc40", "kind": "midi"}])
    assert store.adopt(midi_entry("APC40 mkII", another=True)) == "apc40-2"
    assert store.raw[-1]["port"] == "APC40 mkII"
    assert store.adopt(midi_entry("Launch Control XL")) == "launch-control-xl"
    assert store.adopt(midi_entry("Launch Control XL 2")) == "launch-control-xl-2"


def test_an_exact_name_opens_that_port_not_one_it_is_part_of():
    from hyperspace.midi import find_port
    names = ["Launch Control XL 2", "Launch Control XL"]
    assert find_port(names, "launch control xl") == "Launch Control XL"
    assert find_port(names, "Launch Control XL 2") == "Launch Control XL 2"
    assert find_port(names, "Launch") == "Launch Control XL 2", "else the first it's part of"
    assert find_port(names, "APC") is None


def test_two_desks_of_one_name_are_one_to_mido_so_an_ordinal_could_open_nothing(monkeypatch):
    """Review finding 6's ordinal, disproved for a true twin: mido lists the name once, and
    opens the first port of that name, so "X #2" has nothing to reach. The words say so."""
    from mido.backends import rtmidi as backend

    class Twins:
        def __init__(self, **_):
            pass

        def get_ports(self):
            return ["Twin", "Twin"]

        def delete(self):
            pass

        def open_port(self, n):
            opened.append(n)
    opened: list[int] = []
    monkeypatch.setattr(backend.rtmidi, "MidiIn", Twins)
    monkeypatch.setattr(backend.rtmidi, "MidiOut", Twins)
    assert [d["name"] for d in backend.get_devices()] == ["Twin"]
    backend._open_port(Twins(), "Twin")
    assert opened == [0]


# ---------------------------------------------------------------- on or off, per Mac (review 7)

def test_on_or_off_is_each_macs_whatever_the_list_says(macs):
    root, one, two = macs
    cfg = toml(one, f'[library]\npath = "{root}"\n')
    a = opened(cfg, one)
    assert not next(e for e in config.devices(cfg) if e["role"] == "leap")["enabled"]
    cfg = toml(two, f'[library]\npath = "{root}"\n[hands]\nenabled = true\n')
    b = opened(cfg, two)
    assert next(e for e in config.devices(cfg) if e["role"] == "leap")["enabled"], "B has a Leap"
    assert not a.is_on("leap") and b.is_on("leap")
    assert next(e for e in on_disk(root) if e["role"] == "leap")["enabled"] is False, "the file didn't move"


def test_the_board_is_the_door_and_it_outlives_a_restart(macs):
    root, one, _ = macs
    cfg = toml(one, f'[library]\npath = "{root}"\n')
    store = opened(cfg, one)
    before = (root / FILE).read_text()
    store.set_here("leap", True)
    assert next(e for e in store.checked()[0] if e["role"] == "leap")["enabled"] is True
    store.sync()
    assert (root / FILE).read_text() == before, "on this Mac alone"
    cfg = toml(one, f'[library]\npath = "{root}"\n')
    opened(cfg, one)
    assert next(e for e in config.devices(cfg) if e["role"] == "leap")["enabled"] is True


def test_config_toml_disagreeing_later_is_said_and_the_board_stands(macs):
    root, one, _ = macs
    opened(toml(one, f'[library]\npath = "{root}"\n'), one)
    cfg = toml(one, f'[library]\npath = "{root}"\n[hands]\nenabled = false\n')
    opened(cfg, one)
    assert not any("leap" in n and "otherwise" in n for n in cfg["notes"]), "it agrees"
    (one / HERE).write_text(json.dumps({"schema": devicelist.HERE_SCHEMA, "on": {"leap": True}}))
    cfg = toml(one, f'[library]\npath = "{root}"\n[hands]\nenabled = false\n')
    opened(cfg, one)
    assert any("leap" in n and "otherwise" in n for n in cfg["notes"])
    assert next(e for e in config.devices(cfg) if e["role"] == "leap")["enabled"] is True


def test_a_second_mac_on_the_old_tables_adds_what_it_said_and_no_defaults(macs):
    root, _, two = macs
    lands(root, [{"role": "edge", "kind": "gamepad", "controller": "edge"}])
    cfg = toml(two, f'[library]\npath = "{root}"\n[midi]\nprofile = "generic"\nport = "Box"\n')
    opened(cfg, two)
    got = roles(on_disk(root))
    assert "generic" in got, "what its table said"
    assert "pad" not in got and "leap" not in got, "a default isn't saying anything"


# ---------------------------------------------------------------- a slow disk (review 8)

class Stalled:
    """The shared folder as a File Provider having a bad day: every touch of it blocks
    until `free` is set. This Mac's own folder answers at once."""

    def __init__(self, monkeypatch, root):
        import threading
        self.free = threading.Event()
        self.touches = 0
        real_stat, real_read = devicelist._stat, devicelist._read

        def stat(path, r):
            self.touches += 1
            self.free.wait(30)
            return real_stat(path, r)

        def read(path, r):
            self.touches += 1
            self.free.wait(30)
            return real_read(path, r)
        monkeypatch.setattr(devicelist, "_stat", stat)
        monkeypatch.setattr(devicelist, "_read", read)


def test_a_stalled_drive_never_touches_the_frame_thread(macs, monkeypatch):
    root, home, _ = macs
    lands(root, LIST)
    monkeypatch.setattr(devicelist, "LAUNCH_S", 0.05)
    clock = Clock()
    disk = Stalled(monkeypatch, root)
    t0 = time.perf_counter()
    store = DeviceList(root, home, seed=LIST, clock=clock)
    assert time.perf_counter() - t0 < 1.0, "the launch is bounded"
    assert "isn't answering" in store.said
    worst = 0.0
    for _ in range(200):
        clock.t += 0.5
        t0 = time.perf_counter()
        store.look()
        store.role_for(XBOX)
        worst = max(worst, time.perf_counter() - t0)
    t0 = time.perf_counter()
    assert store.adopt(XBOX) == "xbox"
    assert store.checked()[0][-1]["role"] != ""
    worst = max(worst, time.perf_counter() - t0)
    print(f"worst frame-thread call with a stalled library: {worst * 1000:.3f} ms")
    assert worst < 0.02
    assert disk.touches == 1, "one cycle out at a time, however long it takes"
    assert roles(store.raw)[-1] == "xbox", "the adopt stands"
    store._local.wait(5)
    assert "xbox" in (home / COPY).read_text(), "and this Mac's own file isn't held up"
    disk.free.set()
    store.sync()
    assert "xbox" in roles(on_disk(root))
    assert store.said == ""


def test_a_launch_that_gave_up_takes_the_file_when_it_answers(macs, monkeypatch):
    root, home, _ = macs
    lands(root, [*LIST, EDGE])
    monkeypatch.setattr(devicelist, "LAUNCH_S", 0.05)
    disk = Stalled(monkeypatch, root)
    store = DeviceList(root, home, seed=LIST)
    assert store.raw == LIST
    reg = devices.DeviceRegistry(store.checked()[0], devices.Context(), store=store)
    disk.free.set()
    store.sync()
    assert reg.watch()
    assert "edge" in [d.role for d in reg]


def test_what_fails_is_tried_less_and_less_often(tmp_path):
    root, home = tmp_path / "Drive", tmp_path / "home"
    home.mkdir()
    clock = Clock()
    store = DeviceList(root, home, seed=[], clock=clock)
    store.adopt(XBOX)
    given = []
    real = store._give
    store._give = lambda: (given.append(clock.t), real())
    store._shared.wait(5)
    for _ in range(600):
        clock.t += 0.5
        store.look()
        store._shared.wait(5)
    gaps = [b - a for a, b in itertools.pairwise(given)]
    assert len(given) < 25, "five minutes unmounted: not 600 tries"
    assert gaps[-1] <= devicelist.RETRY_MAX_S + 1 and gaps[-1] > gaps[0]
    root.mkdir()
    clock.t += devicelist.RETRY_MAX_S + 1
    store.look()
    store.sync()
    assert roles(on_disk(root)) == ["xbox"], "and it still lands"


def test_a_quiet_list_costs_one_stat_a_look_on_the_worker(macs, monkeypatch):
    root, home, _ = macs
    clock = Clock()
    store = DeviceList(root, home, seed=LIST, clock=clock)
    store.sync()
    reads = []
    real = devicelist._read
    monkeypatch.setattr(devicelist, "_read", lambda p, r: reads.append(1) or real(p, r))
    clock.t += HOLD_S + 1
    for _ in range(50):
        clock.t += devicelist.LOOK_S
        store.look()
        store._shared.wait(5)
    assert not reads


# ---------------------------------------------------------------- a rename's holders (review 10)

def test_a_rename_takes_who_holds_it_with_it(macs):
    root, one, two = macs
    a = DeviceList(root, one, seed=[])
    b = DeviceList(root, two, seed=[])
    before = (root / FILE).read_text()
    players = Players(one / "players.json")
    ctx = devices.Context(players=players)
    reg = devices.DeviceRegistry([], ctx, store=a)
    a.adopt(midi_entry("Foo Bar"))
    players.hold("foo-bar", 2)
    a.sync()
    (root / FILE).write_text(before)
    b.adopt(midi_entry("foo-bar"))
    b.sync()
    a.sync()
    assert reg.watch()
    assert players.held == {"foo-bar-2": 2}, "foo-bar is now the other Mac's controller"
    assert players.player_of("foo-bar").number == 1


def test_a_rename_takes_this_macs_on_or_off_with_it(macs):
    """Third pass: off belongs to the controller that was switched off, not to the name."""
    root, one, two = macs
    a = DeviceList(root, one, seed=[])
    b = DeviceList(root, two, seed=[])
    before = (root / FILE).read_text()
    a.adopt(midi_entry("Foo Bar"))
    a.set_here("foo-bar", False)
    a.sync()
    (root / FILE).write_text(before)
    b.adopt(midi_entry("foo-bar"))
    b.sync()
    a.sync()
    assert a.here == {"foo-bar-2": False}
    assert json.loads((one / HERE).read_text())["on"] == {"foo-bar-2": False}
    entries = {e["role"]: e["enabled"] for e in a.checked()[0]}
    assert entries == {"foo-bar": True, "foo-bar-2": False}


# ---------------------------------------------------------------- the second pass

def _a_rename_waiting_from_last_run(tmp_path):
    """An adopt kept in the copy with no Drive, and the Drive back with its name taken."""
    root, home = tmp_path / "Drive", tmp_path / "home"
    home.mkdir()
    store = DeviceList(root, home, seed=[])
    store.adopt(midi_entry("Foo Bar"))
    store.sync()
    root.mkdir()
    lands(root, [midi_entry("foo-bar")])
    return root, home, DeviceList(root, home, seed=[])


def test_a_rename_at_launch_waits_for_a_taker_though_the_list_says_no_change(tmp_path):
    _, home, store = _a_rename_waiting_from_last_run(tmp_path)
    assert store.renames == [("foo-bar", "foo-bar-2")]
    assert not store._dirty
    players = Players(home / "players.json")
    players.hold("foo-bar", 2)
    reg = devices.DeviceRegistry(store.checked()[0], devices.Context(players=players), store=store)
    reg.watch()
    assert players.held == {"foo-bar-2": 2}
    assert not store.renames


def test_main_takes_a_launchs_renames_before_the_devices_open():
    src = inspect.getsource(app.main)
    assert src.index("Players.load(home") < src.index("device_list.take_renames()") < src.index("_open_devices(cfg")


def test_a_hands_entrys_own_out_is_kept_through_the_list(tmp_path):
    """Second pass, finding 2, disproved: `_daw`'s `wrote_out` only chooses a note, so the
    DAW sink is there, on the port it asked for, through `devices.json` as through config.toml."""
    raw = [{"role": "leap", "kind": "hands", "enabled": True, "out": "My DAW"}]
    entries, problems, _ = config.listed_devices(raw, tmp_path)
    assert not problems
    daw = next(e for e in entries if e["role"] == config.DAW_ROLE)
    assert daw["port"] == "My DAW" and daw["carries"] == "leap" and daw["enabled"]
    p = tmp_path / "config.toml"
    p.write_text('[[devices]]\nrole = "leap"\nkind = "hands"\nenabled = true\nout = "My DAW"\n')
    assert next(e for e in config.devices(config.load(p)) if e["role"] == config.DAW_ROLE) == daw


def test_the_daw_sink_follows_on_or_off_on_this_mac(tmp_path):
    """Found checking that: `_daw` asks whether the hands are on, so this Mac's say comes first."""
    raw = [{"role": "leap", "kind": "hands", "enabled": False, "out": "My DAW"}]
    assert not any(e["role"] == config.DAW_ROLE for e in config.listed_devices(raw, tmp_path)[0])
    on = config.listed_devices(raw, tmp_path, {"leap": True})[0]
    assert any(e["role"] == config.DAW_ROLE for e in on)
    raw = [{"role": "leap", "kind": "hands", "enabled": True, "out": "My DAW"}]
    off = config.listed_devices(raw, tmp_path, {"leap": False})[0]
    assert not any(e["role"] == config.DAW_ROLE for e in off)


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
    DeviceList(root, home, seed=LIST).sync()
    assert sorted(p.name for p in home.iterdir()) == sorted([COPY, HERE])
    assert sorted(p.name for p in root.iterdir()) == [FILE]


def test_with_the_library_in_the_home_there_is_no_copy(tmp_path):
    DeviceList(tmp_path, tmp_path, seed=LIST).sync()
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([HERE, FILE])


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
