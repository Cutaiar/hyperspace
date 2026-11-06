"""The playlist (plan 44 D6, rows 705–709): for installs, with no guards against the operator.

D6a: the file, and `Playing.tick` over stand-in decks and a stand-in meta controller.
D6b: the same over the real two decks, the triggers and the frame.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from test_loadable import put
from test_on_off_air import rig as on_off_air_rig
from test_ui_pane import _only, _spills, _st, _tall_driver
from test_ui_shell import build_rig

from hyperspace import app, hotreload, playlist, ui_graph, ui_playlist, undo
from hyperspace.library import PLAYLISTS, Library, LibraryError, group_folder
from hyperspace.params import is_shared_meta_id, part_of
from hyperspace.playlist import LEAD_S, Entry, Playing, Playlist
from hyperspace.render import SceneTarget
from hyperspace.routing import meta_refusal
from hyperspace.ui import PAGE_KEYS

ROOT = Path(app.__file__).resolve().parents[1]
air = on_off_air_rig     # the fixture: two decks, the desk, the library


class StandInMeta:
    """Two stand-in decks, a fader and the fade asked for."""

    def __init__(self, broken=()):
        self.broken = broken
        self.decks = (self._deck(1), self._deck(2))
        self.on_air, self.off_air = self.decks
        self.fades: list = []
        self.mixing = False
        for d in self.decks:
            d.undo = NS(open=True)         # an open step, always: no guard asks

    def _deck(self, n: int):
        deck = NS(n=n, loads=[])

        def load(name):
            if name in self.broken:
                raise LibraryError(f"{name}.json is not a preset")
            deck.loads.append(name)

        deck.loaded_patch = NS(load=load)
        return deck

    def crossfade(self, to=None, seconds=None):
        self.fades.append(seconds)

    def across(self):
        """What a fade's end leaves: the deck faded to on air."""
        self.on_air, self.off_air = self.off_air, self.on_air


class StandInLib:
    """A library's say, and every file there is but those named gone."""

    def __init__(self, playlist_doc=None, gone=()):
        self.doc, self.gone = playlist_doc, gone
        self.status, self.warnings = [], []

    def say(self, status=None, *, warning=None):
        if status:
            self.status.append(status)
        if warning:
            self.warnings.append(warning)

    def path_of(self, group, name, *, loose=False):
        return None if name in self.gone else Path(f"{name}.json")

    def read(self, group, name):
        if self.doc is None:
            raise LibraryError(f"no playlist {name}")
        return json.loads(json.dumps(self.doc))


def lst(*entries, name="cart"):
    return Playlist(name, [Entry(*e) if isinstance(e, tuple) else Entry(e, 10.0) for e in entries])


def playing(*entries, gone=(), broken=(), fade=None):
    pl = lst(*entries)
    lib, meta = StandInLib(pl.to_doc(), gone), StandInMeta(broken)
    p = Playing(meta, lib, fade)
    assert p.select("cart")
    return p, meta, lib


# ------------------------------------------------------------------ the file

def test_the_file_round_trips(tmp_path):
    lib = Library(tmp_path / "home", period=0.0)
    pl = Playlist("The Cart", [Entry("party/trip", 300.0), Entry("party-acid", 60.0, 8.0),
                               Entry("cut", 5.0, 0.0)])
    playlist.save(lib, pl)
    path = tmp_path / "home" / "playlists" / "the-cart.json"
    doc = json.loads(path.read_text())
    assert doc["schema"] == "hyperspace.playlist/1"
    assert doc["entries"][0] == {"loadable": "party/trip", "dwell_s": 300.0}   # no fade: the panel's
    assert lib.list(PLAYLISTS) == ["The Cart"]
    assert playlist.read(lib, "The Cart") == pl


def test_a_playlist_is_never_landed_and_says_so(tmp_path):
    lib = Library(tmp_path / "home", period=0.0)
    playlist.save(lib, lst("a"))
    with pytest.raises(LibraryError, match="played, not loaded"):
        lib.load(PLAYLISTS, "cart")
    assert group_folder(PLAYLISTS, lib.kinds) == "playlists"     # not under patches/


def test_a_file_of_another_kind_or_a_newer_build_is_refused(tmp_path):
    lib = Library(tmp_path / "home", period=0.0)
    folder = tmp_path / "home" / "playlists"
    folder.mkdir(parents=True)
    (folder / "newer.json").write_text(json.dumps(
        {"schema": "hyperspace.playlist/2", "name": "newer", "entries": []}))
    (folder / "preset.json").write_text(json.dumps(
        {"schema": "hyperspace.preset/2", "name": "preset", "entries": []}))
    for name in ("newer", "preset"):
        with pytest.raises(LibraryError, match="is not a hyperspace.playlist"):
            playlist.read(lib, name)


@pytest.mark.parametrize(("row", "words"), [
    ({"dwell_s": 3}, "names no loadable patch"),
    ({"loadable": "a", "dwell_s": 0.25}, "dwell_s must be a number of seconds"),
    ({"loadable": "a", "dwell_s": "long"}, "dwell_s must be"),
    ({"loadable": "a", "fade_s": -1}, "fade_s must be"),
    ({"loadable": "a", "dwell_s": True}, "dwell_s must be"),
])
def test_a_bad_entry_is_said_in_words(tmp_path, row, words):
    lib = Library(tmp_path / "home", period=0.0)
    folder = tmp_path / "home" / "playlists"
    folder.mkdir(parents=True)
    (folder / "bad.json").write_text(json.dumps(
        {"schema": playlist.SCHEMA, "name": "bad", "entries": [row]}))
    with pytest.raises(LibraryError, match=words):
        playlist.read(lib, "bad")


def test_a_missing_dwell_is_five_minutes():
    assert Playlist.from_doc({"entries": [{"loadable": "a"}]}).entries[0].dwell_s == 300.0


def test_the_library_lists_playlists_as_a_kind_and_never_as_a_module_group(tmp_path):
    lib = Library(tmp_path / "home", period=0.0)
    playlist.save(lib, lst("a"))
    assert PLAYLISTS in lib.kinds
    assert not (tmp_path / "home" / "patches" / "playlists").exists()
    lib.poll(1.0)                                 # the file watch reads the folder, lands nothing
    assert not lib.is_dirty(PLAYLISTS)


def _tool():
    spec = importlib.util.spec_from_file_location("migrate_library_playlist",
                                                  ROOT / "tools" / "migrate_library.py")
    tool = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = tool            # (its dataclasses ask for their module)
    spec.loader.exec_module(tool)
    return tool


def test_library_tool_ignores_playlists(tmp_path):
    tool = _tool()
    root = tmp_path / "library"
    (root / PLAYLISTS).mkdir(parents=True)
    (root / PLAYLISTS / "cart.json").write_text(json.dumps(lst("a").to_doc()))
    assert tool.group_plan(root) == ([], [])


# ------------------------------------------------------------------ an advance

def test_play_lands_the_entry_on_the_deck_off_air_and_fades():
    p, meta, _ = playing("a", "b")
    p.play()
    p.tick(100.0)
    assert meta.decks[1].loads == ["a"] and meta.decks[0].loads == [] and meta.fades == []
    p.tick(100.1)                                 # a frame later: warm is done
    assert meta.fades == [None]                   # `output.xfade_s`, read by the meta controller
    assert p.at == 0


def test_the_next_look_loads_lead_seconds_before_its_fade_and_the_dwell_runs_fade_to_fade():
    p, meta, _ = playing(("a", 300.0), ("b", 60.0), ("c", 60.0))
    p.play()
    p.tick(100.0)
    p.tick(100.0)
    meta.across()
    p.tick(100.0 + 300.0 - LEAD_S - 0.01)
    assert meta.decks[0].loads == []              # not yet
    p.tick(100.0 + 300.0 - LEAD_S)
    assert meta.decks[0].loads == ["b"] and len(meta.fades) == 1
    p.tick(100.0 + 300.0 - 0.01)
    assert len(meta.fades) == 1                   # loaded, warmed, and waiting
    p.tick(100.0 + 300.0)
    assert len(meta.fades) == 2 and p.at == 1
    assert p.fade_at == 100.0 + 300.0 + 60.0      # b's dwell, from b's fade


def test_it_wraps_and_runs_on_through_many_advances():
    p, meta, _ = playing(("a", 10.0), ("b", 10.0))
    p.play()
    t = 0.0
    went: list[str] = []
    for _ in range(4000):                         # 400 s at 10 Hz
        before = len(meta.fades)
        p.tick(t)
        if len(meta.fades) > before:
            went.append(p.playlist.entries[p.at].loadable)
            meta.across()
        t += 0.1
    assert went[:4] == ["a", "b", "a", "b"] and len(went) in (39, 40, 41)
    assert meta.decks[0].loads and meta.decks[1].loads


def test_fade_seconds_come_from_the_entry_and_zero_is_a_cut():
    p, meta, _ = playing(("a", 5.0, 8.0), ("b", 5.0, 0.0))
    p.play()
    p.tick(0.0)
    p.tick(0.0)
    meta.across()
    p.tick(5.0)
    p.tick(5.0)
    assert meta.fades == [8.0, 0.0]


def test_no_guard_a_deck_with_an_open_step_is_written_over():
    """Overrules plan 44 §6's "never written with an open step": the owner, 2026-11-04,
    "it needs no guards against the operator"."""
    p, meta, _ = playing("a")
    assert meta.off_air.undo.open
    p.play()
    p.tick(0.0)
    assert meta.off_air.loads == ["a"]


def test_a_missing_patch_is_skipped_and_said_and_the_next_plays():
    p, meta, lib = playing("gone", "b", gone=("gone",))
    p.play()
    p.tick(0.0)
    assert meta.off_air.loads == ["b"]
    assert any("skipped gone: there is no such patch" in w for w in lib.warnings)
    p.tick(0.0)
    assert p.at == 1 and p.on


def test_a_bad_file_is_skipped_too():
    p, meta, lib = playing("bad", "b", broken=("bad",))
    p.play()
    p.tick(0.0)
    assert meta.off_air.loads == ["b"] and any("skipped bad" in w for w in lib.warnings)


def test_every_entry_missing_stops_and_what_is_on_air_stays():
    p, meta, lib = playing("x", "y", gone=("x", "y"))
    p.play()
    p.tick(0.0)
    assert not p.on and meta.fades == [] and meta.off_air.loads == []
    assert "none of its 2 entries will play" in lib.warnings[-1]


def test_an_advance_waits_for_a_fade_or_a_fader_between_its_ends():
    p, meta, lib = playing("a")
    meta.mixing = True
    p.play()
    p.tick(0.0)
    p.tick(1.0)
    assert meta.off_air.loads == [] and meta.fades == []
    assert lib.status.count("playlist: waiting for the crossfader to reach an end") == 1
    meta.mixing = False
    p.tick(2.0)
    assert meta.off_air.loads == ["a"]


def test_on_air_moved_by_hand_after_a_load_loads_again_on_the_new_deck_off_air():
    p, meta, _ = playing(("a", 10.0), ("b", 10.0))
    p.play()
    p.tick(0.0)
    assert meta.decks[1].loads == ["a"]
    meta.across()                                 # a hand on the fader, past the middle
    p.tick(0.0)
    assert meta.decks[0].loads == ["a"]           # …never fades back to what was on air
    p.tick(0.0)
    assert len(meta.fades) == 1


def test_step_goes_on_or_back_now():
    p, meta, _ = playing(("a", 100.0), ("b", 100.0), ("c", 100.0))
    p.play()
    p.tick(0.0)
    p.tick(0.0)
    meta.across()
    p.step(1)
    p.tick(1.0)
    p.tick(1.0)
    assert p.at == 1 and meta.decks[0].loads == ["b"]
    meta.across()
    p.step(-1)
    p.tick(2.0)
    p.tick(2.0)
    assert p.at == 0 and meta.decks[1].loads == ["a", "a"]


def test_an_edit_to_the_file_lands_at_the_next_load():
    p, meta, lib = playing(("a", 10.0), ("b", 10.0))
    p.play()
    p.tick(0.0)
    p.tick(0.0)
    meta.across()
    lib.doc = lst(("a", 10.0), ("z", 10.0)).to_doc()
    p.tick(10.0 - LEAD_S)
    assert meta.off_air.loads == ["z"]


def test_a_file_that_has_gone_keeps_the_last_list_and_says_so():
    p, meta, lib = playing(("a", 10.0), ("b", 10.0))
    p.play()
    p.tick(0.0)
    p.tick(0.0)
    meta.across()
    lib.doc = None
    p.tick(10.0 - LEAD_S)
    assert meta.off_air.loads == ["b"] and any("as it last read" in w for w in lib.warnings)


def test_stop_stops_and_play_goes_on():
    p, meta, _ = playing(("a", 10.0), ("b", 10.0))
    p.play()
    p.tick(0.0)
    p.tick(0.0)
    meta.across()
    p.stop()
    p.tick(100.0)
    assert meta.off_air.loads == [] and len(meta.fades) == 1 and p.left() is None
    p.play()
    p.tick(101.0)
    assert meta.off_air.loads == ["b"]


def test_play_with_nothing_chosen_says_so():
    lib = StandInLib()
    p = Playing(StandInMeta(), lib)
    p.play()
    assert not p.on and "choose one" in lib.warnings[-1]
    assert not p.select("nothing here") and lib.warnings[-1] == "no playlist nothing here"


def test_the_warm_draw_is_waited_for_and_a_look_that_will_not_draw_is_skipped():
    fade = NS(warm_deck=None, warm_error="")
    p, meta, lib = playing(("bad", 10.0), ("b", 10.0), fade=fade)
    p.play()
    p.tick(0.0)
    fade.warm_deck = meta.off_air                 # what `Fade.ask_warm` does at the load
    p.tick(0.0)
    assert meta.fades == []
    fade.warm_deck, fade.warm_error = None, "warm draw: no such shader"
    p.tick(0.0)
    assert meta.fades == [] and any("skipped bad: warm draw" in w for w in lib.warnings)
    p.tick(0.0)
    assert meta.off_air.loads == ["bad", "b"] and fade.warm_error == ""
    p.tick(0.0)
    assert p.at == 1 and len(meta.fades) == 1


# ------------------------------------------------------------------ what it is not

def _source() -> ast.Module:
    return ast.parse(Path(playlist.__file__).read_text())


def test_an_advance_is_one_mix_pass():
    """No second fade road, no draw and no worker: it asks `MetaController.crossfade` and
    `Fade`'s warm draw, and imports nothing that could do either itself (DQ8)."""
    tree = _source()
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level}
    imports |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert imports == {"library", "math"}
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    for road in ("xfade", "timed", "TimedFade", "mix_pass", "_write_fader", "draw", "draw_outputs",
                 "dreamer", "dream", "lend", "Renderer", "Thread", "follow_fader"):
        assert road not in names, road


def test_it_is_a_watched_module_after_the_library():
    assert hotreload.MODULES.index("library") < hotreload.MODULES.index("playlist")


# ------------------------------------------------------------------ the real decks (D6b)

def _write_list(lib, *entries, name="cart"):
    playlist.save(lib, lst(*entries, name=name))


def _on_real(air, *entries):
    _write_list(air.lib, *entries)
    p = Playing(air.meta, air.lib)
    air.meta.playing = p
    playlist.register(air.one.reg, p)
    assert p.select("cart")
    return p


def _run(air, t0: float, seconds: float, dt: float = 0.05) -> float:
    """Frames: the meta controller ticks, every undo stack ticks. The time at the end."""
    t = t0
    while t < t0 + seconds:
        t += dt
        air.meta.tick(t, dt)
        for stack in air.meta.stacks:
            stack.tick(t)
    return t


def test_on_the_real_decks_an_advance_loads_off_air_and_the_fader_takes_it_on_air(air):
    p = _on_real(air, ("party-tumble", 10.0, 1.0), ("party-wake", 10.0, 0.0))
    room = air.one.reg.snapshot(part="patch")
    air.one.reg["output.xfade_s"].set(4.0)
    air.one.reg["playlist.play"].toggle()
    air.meta.tick(100.0, 0.05)
    assert air.two.loaded_patch.current == "TUMBLE" and air.meta.on_air is air.one
    assert air.one.reg.snapshot(part="patch") == room       # the room saw nothing
    t = _run(air, 100.0, 1.5)
    assert air.meta.on_air is air.two and air.mix.xfade == 1.0 and air.meta.timed is None
    assert air.one.reg["output.xfade_s"].base == 4.0        # an entry's fade writes nothing over it
    t = _run(air, t, 8.0)
    assert air.one.loaded_patch.current != "ACID"           # the next look, loaded…
    assert air.meta.on_air is air.two                       # …and not yet on
    _run(air, t, 2.0)
    assert air.meta.on_air is air.one and air.mix.xfade == 0.0   # fade_s 0: a cut
    assert p.at == 1


def test_a_dirty_deck_off_air_is_written_over(air):
    """No guards (row 707): plan 44 §6's "the panel's deck is never touched while dirty" is
    overruled."""
    p = _on_real(air, ("party-tumble", 10.0))
    air.two.reg["view.bright"].set(0.123)
    assert air.two.loaded_patch.is_dirty()
    p.play()
    air.meta.tick(0.0, 0.05)
    assert air.two.loaded_patch.current == "TUMBLE" and not air.two.loaded_patch.is_dirty()


def test_it_ticks_after_the_fader_so_it_sees_the_frames_deck_on_air(air):
    seen = []
    air.meta.playing = NS(tick=lambda now: seen.append((now, air.meta.on_air)))
    air.mix.xfade = 1.0                           # past the middle: this tick moves on air
    air.meta.tick(5.0, 0.05)
    assert seen == [(5.0, air.two)]


def test_the_hot_reload_lists_it(air):
    p = _on_real(air, "party-tumble")
    assert (p, "playlist", "Playing") in air.meta.targets()


def test_no_patch_can_press_it_and_it_is_in_one_layer(air):
    _on_real(air, "party-tumble")
    for pid in ("playlist.play", "playlist.next", "playlist.prev"):
        param = air.one.reg[pid]
        assert meta_refusal(pid) is not None and is_shared_meta_id(pid)
        assert part_of(param) == "shared_meta"
        assert air.two.reg[pid] is param          # one object, both decks
        assert not param.persist and not param.modulatable


def test_a_patch_file_with_a_row_on_it_loses_the_row_and_says_so(air):
    """The doors a patch's row could come in by: a route and a desk row in a loadable patch."""
    _on_real(air, ("party-tumble", 10.0))
    put(air.lib.home, "PRESSING", routes=[
        {"source": "hand:left.y", "target": "playlist.next", "op": "push", "value": 0.5}],
        desk=[{"source": "note:0:48", "target": "playlist.play", "op": "abs"}])
    air.one.loaded_patch.load("PRESSING")
    table, notes = air.one.table, air.one.loaded_patch.notes
    assert any(n.startswith("dropped hand:left.y → playlist.next") for n in notes)
    assert any(n.startswith("dropped note:0:48 → playlist.play") for n in notes)
    assert not table.routes_to("playlist.next") and not table.desk()


def test_the_latch_on_an_install_load_and_fade_refuse_undo_until_a_change(air):
    """Row 709. The panel on the deck on air: the load latches its stack and the fade does
    again, so a ⌘Z at a cart left running takes nothing back."""
    p = _on_real(air, ("party-tumble", 5.0, 0.2), ("party-wake", 5.0, 0.2))
    assert undo.installed() is air.one.undo
    air.one.reg["view.bright"].set(0.7)
    t = _run(air, 10.0, 1.0)
    assert air.one.undo.stack
    p.play()
    t = _run(air, t, 1.0)                          # loaded on deck 2, and faded
    assert air.meta.on_air is air.two and air.one.undo.latched
    held = air.one.reg.snapshot(part="patch")
    undo.undo()
    assert air.one.reg.snapshot(part="patch") == held
    assert undo.here().status.startswith("nothing to undo here yet")
    # …and later: an advance loads deck 1 under the panel. A ⌘Z takes back no load
    t = _run(air, t, 5.0)
    assert air.meta.on_air is air.one
    held = air.one.reg.snapshot(part="patch")
    undo.undo()
    assert air.one.reg.snapshot(part="patch") == held and air.meta.on_air is air.one


def test_a_change_opens_the_stack_and_undo_can_then_reach_a_load_the_playlist_made(air):
    """Row 709, what the owner is asked: row 753's "all the way down", on an install."""
    p = _on_real(air, ("party-tumble", 5.0, 0.0), ("party-wake", 5.0, 0.0))
    p.play()
    t = _run(air, 10.0, 1.0)                       # TUMBLE, on deck 2
    t = _run(air, t, 5.0)                          # WAKE, on deck 1, the panel's, on air
    p.stop()
    assert air.meta.on_air is air.one and air.one.loaded_patch.current == "WAKE"
    undo.by_hand(True)
    air.one.reg["view.bright"].set(0.61)
    t = _run(air, t, 1.0)
    undo.by_hand(False)
    undo.undo()
    undo.undo()
    assert air.one.loaded_patch.current != "WAKE"   # the room's look went back: a person's ⌘Z


def test_a_long_run_keeps_the_undo_stacks_bounded(air):
    p = _on_real(air, ("party-tumble", 1.0, 0.0), ("party-wake", 1.0, 0.0))
    p.play()
    _run(air, 0.0, (undo.LIMIT + 20) * 2 * 1.1, dt=0.1)
    assert p.on
    for stack in air.meta.stacks:
        assert len(stack.stack) <= undo.LIMIT


# ------------------------------------------------------------------ the section (D6b)

@pytest.mark.parametrize("width", ["min", "default"])
def test_the_section_fits_the_pane_and_works(tmp_path, monkeypatch, width):
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        r.panel.page = PAGE_KEYS.index("graph")
        d = _tall_driver(r, monkeypatch)
        meta = StandInMeta()
        p = r.panel.playing = Playing(meta, r.panel.library)
        playlist.register(r.reg, p)
        playlist.save(r.panel.library, Playlist("A long name for a cart", [
            Entry("a-loadable-patch-with-rather-a-long-name", 300.0), Entry("party/b", 60.0)]))
        assert p.select("A long name for a cart")
        d.run(d.wait(2))
        st = _st(r)
        st["side_w"] = ui_graph.SIDE_MIN if width == "min" else ui_graph.SIDE_W
        _only(st, "playlist")
        d.run(d.wait(3))
        assert st["pane_drawn"] == ["playlist"]
        assert not _spills(d, st)
        d.run(d.click("chip.playlist.play", frames=3))
        assert p.on and r.reg["playlist.play"].get()
        d.run(d.click("playlist.out.1", frames=3))
        assert [e.loadable for e in p.playlist.entries] == ["a-loadable-patch-with-rather-a-long-name"]
        assert [e.loadable for e in playlist.read(r.panel.library, p.playlist.name).entries] == [
            "a-loadable-patch-with-rather-a-long-name"]
        d.run(d.click("playlist.next", frames=3))
        d.run(d.click("chip.playlist.play", frames=3))
        assert not p.on


def test_the_section_says_where_it_has_got_to():
    lib = StandInLib(lst(("a", 300.0), ("b", 10.0)).to_doc())
    p = Playing(StandInMeta(), lib)
    p.select("cart")
    assert ui_playlist.where(p) == "cart: stopped · 2 entries"
    p.play()
    assert ui_playlist.where(p) == "cart: starting"
    p.tick(0.0)
    p.tick(0.0)
    p.tick(55.0)
    assert ui_playlist.where(p) == "cart: 1 of 2, a · next in 4:05"


# ------------------------------------------------------------------ a cart left running (D6b)

@pytest.mark.parametrize("samples", [0, 4])
def test_a_scene_target_lets_go_of_all_it_made(samples):
    """Row 709. The colour renderbuffer was never kept, so never released: one a fade's rest,
    10–15 MB each on the Mac, a leak since 2026-09 that a playlist's fades made a cart's end."""
    made = []

    class Res:
        repeat_x = repeat_y = False

        def __init__(self):
            self.released = 0
            made.append(self)

        def release(self):
            self.released += 1

    def make(*_a, **_k):
        return Res()

    ctx = NS(texture=make, framebuffer=make, renderbuffer=make, depth_renderbuffer=make,
             depth_texture=make)
    target = SceneTarget(ctx)
    for size in ((64, 36), (128, 72), (64, 36)):
        target.ensure(size, samples)
    target.release()
    assert made and [r.released for r in made] == [1] * len(made)
