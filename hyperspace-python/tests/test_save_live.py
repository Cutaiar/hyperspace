"""Plan 83: saving and the playlist, live, on a trackpad.

**save as** on GRAPH's deck row, beside **load…**: one press saves the deck the panel is
on as a new loadable patch (`preset.save_new`, START held on a pad), in the folder of the
patch loaded, never over a file; the chip shows the new name for a moment. The playlist's
entries scroll in a list of their own and keep the look on air in view.
"""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest
from imgui_bundle import imgui
from test_ui_pane import _st
from test_ui_shell import build_rig
from ui_driver import Driver

from hyperspace import playlist, ui_loadable, ui_players, ui_playlist
from hyperspace.library import LOADABLE
from hyperspace.playlist import Entry, Playing, Playlist
from hyperspace.ui import PAGE_KEYS

FOLDER = "4-install-nov/distort"


def _driver(r, monkeypatch, size=(1280, 900)) -> Driver:
    def step() -> None:
        imgui.get_io().display_size = imgui.ImVec2(*size)
        imgui.new_frame()
        r.panel.draw(1 / 60, 60.0)
        imgui.end_frame()
    d = Driver(step=step)
    d.record(monkeypatch.setattr)
    return d


def _stand_in_meta(r):
    """Enough of a meta controller for GRAPH's deck row: the panel on deck 1, on air."""
    one, two = NS(name="deck 1"), NS(name="deck 2")
    return NS(decks=(one, two), panel=one, on_air=one, timed=None,
              words=lambda deck: f"{deck.name} · on air", playing=None)


def _graph(r, monkeypatch, **kw) -> Driver:
    if getattr(r.panel, "meta", None) is not None:      # (the stand-in is the deck row's alone)
        monkeypatch.setattr(ui_players, "_meta", lambda _panel: None)
    r.panel.desk = False
    r.panel.page = PAGE_KEYS.index("graph")
    return _driver(r, monkeypatch, **kw)


# ------------------------------------------------------------------ save as

def _values(reg) -> dict:
    """What a loadable patch holds of the registry: its part of the split."""
    return reg.snapshot(part="patch")


def test_one_click_saves_a_new_patch_in_its_folder_that_loads_back_equal(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        lib = r.panel.library
        lib.loaded_patch.save_as(f"{FOLDER}/moo")
        r.panel.meta = _stand_in_meta(r)
        d = _graph(r, monkeypatch)
        d.run(d.wait(2))
        assert ui_loadable.SAVE_AS_ID in d.rects                     # beside load…
        load, save = d.rects["graph.load"], d.rects[ui_loadable.SAVE_AS_ID]
        assert save[0] > load[2] and abs(save[1] - load[1]) < 1      # on its line, right of it
        r.reg["view.bright"].set(0.37)
        want = _values(r.reg)
        files = set((lib.home / "loadable").rglob("*.json"))

        d.run(d.click(ui_loadable.SAVE_AS_ID, frames=2))

        made = set((lib.home / "loadable").rglob("*.json")) - files
        assert len(made) == 1
        new = made.pop()
        assert new.parent == lib.home / "loadable" / FOLDER          # the loaded one's folder
        assert lib.current(LOADABLE) == f"{FOLDER}/moo 2"
        assert ui_loadable.save_as_label(r.panel) == "saved moo 2"   # the name, for a moment
        d.run(d.wait(1))
        assert d.rects.get("saved moo 2##" + ui_loadable.SAVE_AS_ID)
        assert ui_loadable.save_as_label(r.panel, imgui.get_time() + ui_loadable.SAVED_S) == "save as"
        # loads back equal: move away, load it, every saved value as it was
        r.reg["view.bright"].set(0.9)
        lib.load(LOADABLE, f"{FOLDER}/moo 2")
        assert _values(r.reg) == want


def test_a_second_click_never_overwrites(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        lib = r.panel.library
        lib.loaded_patch.save_as(f"{FOLDER}/moo")
        r.panel.meta = _stand_in_meta(r)
        d = _graph(r, monkeypatch)
        d.run(d.wait(2))
        first = ui_loadable.save_as(r.panel)
        moo = (lib.home / "loadable" / FOLDER / "moo.json").read_text()
        second = ui_loadable.save_as(r.panel)
        assert (first, second) == (f"{FOLDER}/moo 2", f"{FOLDER}/moo 3")
        assert (lib.home / "loadable" / FOLDER / "moo.json").read_text() == moo
        assert len(list((lib.home / "loadable" / FOLDER).glob("*.json"))) == 3


def test_with_nothing_loaded_it_saves_at_the_top_named_as_the_pads_hold_names(tmp_path):
    """The launch sheet's recommendation for 83: the library's top level, ``PATCH <n>``."""
    with build_rig(tmp_path) as r:
        lib = r.panel.library
        assert lib.current(LOADABLE) is None
        name = ui_loadable.save_as(r.panel)
        assert name is not None and "/" not in name and name.startswith("PATCH ")
        assert lib.path_of(LOADABLE, name).parent == lib.home / "loadable"


def test_it_is_the_learnable_action_a_pad_presses(tmp_path):
    """The chip presses `preset.save_new`, the param START held on a pad presses: Learn
    puts the same press on a desk or pad button, and no patch's row can reach it."""
    with build_rig(tmp_path) as r:
        p = r.reg[ui_loadable.SAVE_PARAM]
        assert p.label == "Save as a new patch" and not p.modulatable
        before = r.panel.library.current(LOADABLE)
        p.fire()
        assert r.panel.library.current(LOADABLE) != before


def test_nothing_saved_shows_no_name(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        monkeypatch.setattr(r.reg[ui_loadable.SAVE_PARAM], "fire", lambda: None)   # a refused save
        assert ui_loadable.save_as(r.panel) is None
        assert ui_loadable.save_as_label(r.panel) == "save as"


# ------------------------------------------------------------------ the playlist scrolls

class _Meta:
    """Stand-in decks for `Playing`: nothing is loaded in these tests."""

    def __init__(self):
        self.on_air = self.off_air = NS(loaded_patch=NS(load=lambda name: None))
        self.mixing = False

    def crossfade(self, to=None, seconds=None):
        pass


def _forty(r, at: int | None):
    lib = r.panel.library
    p = r.panel.playing = Playing(_Meta(), lib)
    playlist.register(r.reg, p)
    playlist.save(lib, Playlist("long", [Entry(f"look {k}", 60.0) for k in range(40)]))
    assert p.select("long")
    if at is not None:
        p.on, p.at, p.fade_at, p.load_at = True, at, 1e9, 1e9
    return p


def _inside(rect, box) -> bool:
    return box[1] - 1 <= rect[1] and rect[3] <= box[3] + 1


@pytest.mark.parametrize("at", [0, 31, 39])
def test_forty_entries_stay_on_screen_and_the_playing_row_is_in_view(tmp_path, monkeypatch, at):
    with build_rig(tmp_path) as r:
        _forty(r, at)
        d = _graph(r, monkeypatch, size=(1280, 900))
        d.run(d.wait(2), d.click("graph.playlist", frames=2), d.wait(3))
        st = _st(r)
        y1 = st["playlist_rect"][3]
        assert y1 <= 900                                          # the popup ends on screen
        box = st["playlist_entries_rect"]
        assert box[3] <= y1
        assert _inside(d.rect(f"playlist.dwell.{at}"), box)       # the one on air, in view
        assert _inside(d.rect("playlist.add"), (0, 0, 0, 900))    # and the add list under it
        # rows big enough for a trackpad
        assert d.rect(f"playlist.out.{at}")[3] - d.rect(f"playlist.out.{at}")[1] >= ui_playlist.ROW_H - 0.5
        dwell = d.rect(f"playlist.dwell.{at}")
        assert dwell[3] - dwell[1] >= ui_playlist.ROW_H - 0.5


def test_the_list_scrolls_under_the_wheel_and_follows_the_look_on_air(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        p = _forty(r, 0)
        d = _graph(r, monkeypatch, size=(1280, 900))
        d.run(d.wait(2), d.click("graph.playlist", frames=2), d.wait(3))
        box = _st(r)["playlist_entries_rect"]
        assert not _inside(d.rect("playlist.dwell.39"), box)      # forty do not all fit
        # a trackpad's scroll over the list
        d.run(d.move(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)))
        for _ in range(40):
            imgui.get_io().add_mouse_wheel_event(0.0, -1.0)
            d.run(d.wait(1))
        assert _inside(d.rect("playlist.dwell.39"), box)
        assert not _inside(d.rect("playlist.dwell.0"), box)
        # the next look goes on air: the list goes to it, once
        p.at = 1
        d.run(d.wait(3))
        assert _inside(d.rect("playlist.dwell.1"), box)
        # and a hand's scroll after that is left alone
        for _ in range(40):
            imgui.get_io().add_mouse_wheel_event(0.0, -1.0)
            d.run(d.wait(1))
        assert _inside(d.rect("playlist.dwell.39"), box)


def test_a_click_on_a_row_far_down_lands_on_that_row(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        p = _forty(r, None)
        d = _graph(r, monkeypatch, size=(1280, 900))
        d.run(d.wait(2), d.click("graph.playlist", frames=2), d.wait(3))
        d.run(d.click("playlist.out.35", frames=2), d.wait(1))     # scrolled to, then clicked
        assert [e.loadable for e in p.playlist.entries][35] == "look 36"
        assert len(p.playlist.entries) == 39
