"""NDI between two Macs from the panel (2026-11-22): an output's sender
turned on and off while the app runs, remembered per Mac, and the device
list's `ndi` entry made from MEDIA ▸ Live — no config.toml edit, no restart."""

from __future__ import annotations

import json
from types import SimpleNamespace

from hyperspace import ui_media
from hyperspace.media import publish
from hyperspace.outputs import Slot


class FakeNdi:
    kind = "ndi"

    def __init__(self, name, ctx):
        self.name, self.ctx, self.closed = name, ctx, False
        self.notes = None

    def close(self):
        self.closed = True


class FakeTap:
    def __init__(self, ctx):
        self.released = False

    def release(self):
        self.released = True


def test_default_name_carries_the_mac(monkeypatch):
    monkeypatch.setattr(publish.socket, "gethostname", lambda: "Rig-Mac.local")
    assert publish.default_ndi_name(1) == "Rig-Mac out 1"


def test_an_ask_opens_then_closes_a_sender_and_its_tap(monkeypatch):
    monkeypatch.setattr(publish.socket, "gethostname", lambda: "A")
    sl = Slot(1)
    assert publish.ask_ndi(sl, True) == "A out 1"
    assert sl.publishers == [] and publish.ndi_of(sl) == "A out 1"   # nothing until the frame
    assert publish.take_ask(sl, "ctx", FakeTap, make_ndi=FakeNdi)
    (p,) = sl.publishers
    assert p.name == "A out 1" and sl.ndi == "A out 1" and isinstance(sl.tap, FakeTap)
    assert not publish.take_ask(sl, "ctx", FakeTap, make_ndi=FakeNdi)   # no ask, nothing
    tap = sl.tap
    publish.ask_ndi(sl, False)
    publish.take_ask(sl, "ctx", FakeTap, make_ndi=FakeNdi)
    assert p.closed and sl.publishers == [] and sl.tap is None and tap.released
    assert sl.ndi == ""


def test_turning_ndi_off_keeps_a_syphon_publisher_and_the_tap():
    syphon = SimpleNamespace(kind="syphon", name="s", close=lambda: None)
    sl = Slot(1, ndi="x", publishers=[syphon, FakeNdi("x", None)], tap=FakeTap(None))
    publish.ask_ndi(sl, False)
    publish.take_ask(sl, "ctx", FakeTap, make_ndi=FakeNdi)
    assert sl.publishers == [syphon] and sl.tap is not None and not sl.tap.released


def test_on_again_keeps_the_configs_name():
    sl = Slot(2, ndi="td")
    assert publish.ask_ndi(sl, True) == "td"


def test_a_publish_only_output_is_configs_alone():
    sl = Slot(2, window=False, ndi="td")
    assert not publish.can_ask(sl)
    assert publish.ask_ndi(sl, False) == "td" and sl.ndi_asked is None
    publish.apply_here([sl], {2: ""})
    assert sl.ndi == "td"


def test_the_choice_is_this_macs_file_and_wins_at_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(publish.pool, "submit", lambda fn, *a: fn(*a))
    monkeypatch.setattr(publish.socket, "gethostname", lambda: "B")
    one, two = Slot(1, ndi="from config"), Slot(2)
    publish.ask_ndi(two, True, tmp_path, [one, two])
    publish.ask_ndi(one, False, tmp_path, [one, two])
    assert json.loads((tmp_path / publish.HERE).read_text()) == {"ndi": {"1": "", "2": "B out 2"}}
    fresh = [Slot(1, ndi="from config"), Slot(2)]
    publish.apply_here(fresh, publish.load_here(tmp_path))
    assert [s.ndi for s in fresh] == ["", "B out 2"]


def test_a_missing_or_bad_file_is_no_choice(tmp_path):
    assert publish.load_here(tmp_path) == {}
    (tmp_path / publish.HERE).write_text("{half")
    assert publish.load_here(tmp_path) == {}
    assert publish.load_here(None) == {}


# ---- the receiving side: MEDIA ▸ Live's Find NDI ----

class FakeStore:
    def __init__(self, raw=()):
        self.raw, self.here = list(raw), {}

    def adopt(self, entry):
        self.raw.append(entry)
        return entry["role"]

    def is_on(self, role):
        return self.here.get(role, True)

    def set_here(self, role, on):
        self.here[role] = on


def _panel(store):
    relisted = []
    regs = SimpleNamespace(store=store, relist=lambda: relisted.append(1))
    return SimpleNamespace(devices=regs), relisted


def test_find_ndi_adds_the_entry_once_and_turns_it_on_here():
    store = FakeStore()
    panel, relisted = _panel(store)
    assert not ui_media.ndi_listening(panel)
    ui_media.listen_ndi(panel, True)
    assert store.raw == [ui_media.NDI_ENTRY] and ui_media.ndi_listening(panel) and relisted
    ui_media.listen_ndi(panel, False)
    assert not ui_media.ndi_listening(panel) and len(store.raw) == 1
    ui_media.listen_ndi(panel, True)
    assert len(store.raw) == 1 and ui_media.ndi_listening(panel)


def test_find_ndi_uses_an_entry_already_listed_under_another_role():
    store = FakeStore([{"role": "net-video", "kind": "ndi"}])
    store.here["net-video"] = False
    panel, _ = _panel(store)
    ui_media.listen_ndi(panel, True)
    assert len(store.raw) == 1 and store.here["net-video"] is True


def test_find_ndi_without_a_device_list_says_so():
    assert ui_media.listen_ndi(SimpleNamespace(devices=None), True) == "no device list"
