"""The playlist (plan 44 D6, rows 705–709): for installs, with no guards against the operator.

D6a: the file, and `Playing.tick` over stand-in decks and a stand-in meta controller.
D6b: the same over the real two decks, the triggers and the frame.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from test_on_off_air import rig as on_off_air_rig

from hyperspace import app, hotreload, playlist
from hyperspace.library import PLAYLISTS, Library, LibraryError, group_folder
from hyperspace.params import is_shared_meta_id
from hyperspace.playlist import LEAD_S, Entry, Playing, Playlist
from hyperspace.routing import meta_refusal

ROOT = Path(app.__file__).resolve().parents[1]
air = on_off_air_rig     # the fixture: two decks, the desk, the library


class StandInMeta:
    """Two stand-in decks, a fader and the fade asked for."""

    def __init__(self, broken=(), gone=()):
        self.broken, self.gone = broken, gone
        self.decks = (self._deck(1), self._deck(2))
        self.on_air, self.off_air = self.decks
        self.fades: list = []
        self.mixing = False
        for d in self.decks:
            d.undo = NS(open=True)         # an open step, always: no guard asks

    def _deck(self, n: int):
        deck = NS(n=n, loads=[])

        def load(name):
            if name in self.gone:
                raise LibraryError(f"presets: no preset {name!r}")
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
    """A library's say and one playlist's file, by the names it answers to."""

    def __init__(self, playlist_doc=None):
        self.doc, self.asked = playlist_doc, []
        self.status, self.warnings = [], []

    def say(self, status=None, *, warning=None):
        if status:
            self.status.append(status)
        if warning:
            self.warnings.append(warning)

    def read(self, group, name):
        self.asked.append(name)
        if self.doc is None:
            raise LibraryError(f"no playlist {name}")
        return json.loads(json.dumps(self.doc))


def lst(*entries, name="cart"):
    return Playlist(name, [Entry(*e) if isinstance(e, tuple) else Entry(e, 10.0) for e in entries])


def playing(*entries, gone=(), broken=(), fade=None):
    pl = lst(*entries)
    lib, meta = StandInLib(pl.to_doc()), StandInMeta(broken, gone)
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


def test_a_save_goes_over_the_file_the_name_resolves_to(tmp_path):
    """One file for one name (as `Library.save_as`), and never `<slug>.json` beside it."""
    lib = Library(tmp_path / "home", period=0.0)
    folder = tmp_path / "home" / "playlists"
    folder.mkdir(parents=True)
    named = folder / "my cart v2.json"
    named.write_text(json.dumps(lst("a", name="Cart").to_doc()))
    playlist.save(lib, lst("b", name="Cart"))
    assert [f.name for f in folder.glob("*.json")] == ["my cart v2.json"]
    assert playlist.read(lib, "Cart").entries[0].loadable == "b"


def test_a_save_by_the_key_keeps_a_conflict_copy_itself(tmp_path):
    lib = Library(tmp_path / "home", period=0.0)
    folder = tmp_path / "home" / "playlists"
    folder.mkdir(parents=True)
    (folder / "cart.json").write_text(json.dumps(lst("real").to_doc()))
    copy = "cart (Dan's conflicted copy)"
    (folder / f"{copy}.json").write_text(json.dumps(lst("theirs").to_doc()))
    listed = next(n for n in lib.list(PLAYLISTS) if n != "cart")
    pl = playlist.read(lib, listed)
    playlist.save(lib, Playlist(pl.name, [Entry("edited")]), listed)
    assert playlist.read(lib, "cart").entries[0].loadable == "real"
    assert playlist.read(lib, listed).entries[0].loadable == "edited"


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
    ({"loadable": "  "}, "names no loadable patch"),
    ("a line", "not an entry"),
    ({"loadable": "a", "dwell_s": 0.25}, "dwell_s must be seconds"),
    ({"loadable": "a", "dwell_s": "long"}, "dwell_s must be"),
    ({"loadable": "a", "dwell_s": True}, "dwell_s must be"),
    ({"loadable": "a", "dwell_s": math.inf}, "dwell_s must be"),
    ({"loadable": "a", "dwell_s": 10 ** 400}, "dwell_s must be"),
    ({"loadable": "a", "fade_s": -1}, "fade_s must be"),
    ({"loadable": "a", "fade_s": math.inf}, "fade_s must be"),
    ({"loadable": "a", "fade_s": math.nan}, "fade_s must be"),
    ({"loadable": "a", "fade_s": 31}, "fade_s must be"),
])
def test_a_bad_row_is_left_out_and_said_and_the_rest_plays(row, words):
    """A file that says `"fade_s": 1e999` must not fade for ever, or hang a cart in `mixing`."""
    doc = {"schema": playlist.SCHEMA, "name": "bad",
           "entries": [row, {"loadable": "good", "dwell_s": 9}]}
    pl = Playlist.from_doc(doc)
    assert [e.loadable for e in pl.entries] == ["good"]
    assert len(pl.skipped) == 1 and pl.skipped[0].startswith("entry 1: ") and words in pl.skipped[0]
    lib = StandInLib(doc)
    p = Playing(StandInMeta(), lib)
    assert p.select("bad")
    assert [w for w in lib.warnings if words in w and "left out entry 1" in w]
    p.play()
    p.tick(0.0)
    p.tick(0.0)
    assert p.meta.off_air.loads == ["good"] and len(lib.warnings) == 1     # said once


def test_it_cannot_write_what_it_will_not_read():
    for bad in ({"dwell_s": math.inf}, {"dwell_s": 0.0}, {"fade_s": 1e999}, {"fade_s": 31.0}):
        with pytest.raises(ValueError, match="must be seconds"):
            Entry("a", **bad)
    with pytest.raises(ValueError, match="names no"):
        Entry("")


def test_a_huge_number_in_a_real_file_is_only_a_row_left_out(tmp_path):
    lib = Library(tmp_path / "home", period=0.0)
    folder = tmp_path / "home" / "playlists"
    folder.mkdir(parents=True)
    (folder / "big.json").write_text('{"schema": "hyperspace.playlist/1", "name": "big", "entries": ['
                                     '{"loadable": "a", "fade_s": 1e999}, {"loadable": "b", "dwell_s": 1' +
                                     "0" * 400 + '}, {"loadable": "c"}]}')
    assert [e.loadable for e in playlist.read(lib, "big").entries] == ["c"]


def test_its_top_fade_is_the_crossfaders_own():
    from hyperspace.deck import Mix, register_xfade
    from hyperspace.params import Registry
    reg = Registry()
    register_xfade(reg, Mix())
    assert reg["output.xfade_s"].hi == playlist.FADE_MAX_S


def test_no_patchs_row_may_press_one_on_this_head_too():
    """The module's docstring says so: true by the group, before any param is made."""
    assert meta_refusal("playlist.next") is not None and is_shared_meta_id("playlist.play")


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
    assert any("skipped gone: presets: no preset 'gone'" in w for w in lib.warnings)
    p.tick(0.0)
    assert p.at == 1 and p.on


def test_a_bad_file_is_skipped_too():
    p, meta, lib = playing("bad", "b", broken=("bad",))
    p.play()
    p.tick(0.0)
    assert meta.off_air.loads == ["b"] and any("skipped bad" in w for w in lib.warnings)


def test_every_entry_missing_stays_on_says_once_and_plays_when_they_are_back():
    """Drive offline: an install runs on. It never stops itself."""
    p, meta, lib = playing(("x", 20.0), ("y", 20.0), gone=("x", "y"))
    p.play()
    p.tick(0.0)
    assert p.on and meta.fades == [] and meta.off_air.loads == []
    said = [w for w in lib.warnings if "none of its 2 entries will play" in w]
    assert len(said) == 1 and "What is on air stays" in said[0]
    count = len(lib.warnings)
    p.tick(19.9)
    assert p.load_at > 19.9                       # waits a dwell, with no spinning
    for t in (20.0, 40.0, 60.0):
        p.tick(t)
    assert len(lib.warnings) == count and p.on    # said once
    meta.gone = ()                                # …and Drive is back
    p.tick(80.0)
    p.tick(80.0)
    assert meta.off_air.loads and len(meta.fades) == 1 and not p.lost
    p.meta.across()
    meta.gone = ("x", "y")                        # lost again: said again
    p.tick(200.0)
    assert len([w for w in lib.warnings if "none of its 2" in w]) == 2


def test_an_empty_list_stays_on_and_plays_when_it_has_something():
    p, meta, lib = playing(("a", 10.0))
    lib.doc = lst().to_doc()
    p.play()
    p.tick(0.0)
    assert p.on and "it has nothing in it" in lib.warnings[-1]
    lib.doc = lst(("a", 10.0)).to_doc()
    p.tick(300.0)
    assert meta.off_air.loads == ["a"]


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


def test_a_hand_across_to_the_look_armed_has_played_it_and_it_moves_on():
    p, meta, _ = playing(("a", 10.0), ("b", 20.0), ("c", 10.0))
    p.play()
    p.tick(0.0)
    assert meta.decks[1].loads == ["a"]
    meta.across()                                 # a hand on the fader, past the middle
    p.tick(1.0)
    assert p.at == 0 and p.armed is None and meta.fades == []     # no fade into itself
    assert p.fade_at == 11.0                      # its dwell, from the hand
    assert meta.decks[0].loads == []
    p.tick(11.0 - LEAD_S)
    assert meta.decks[0].loads == ["b"]           # …and on to the next


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


def _on_b():
    """Four entries, b on air."""
    p, meta, _ = playing(("a", 100.0), ("b", 100.0), ("c", 100.0), ("d", 100.0))
    p.play()
    p.tick(0.0)
    p.tick(0.0)
    meta.across()
    p.step(1)
    p.tick(1.0)
    p.tick(1.0)
    meta.across()
    assert p.at == 1
    return p, meta


def test_two_quick_steps_back_go_back_two():
    p, meta = _on_b()
    p.step(-1)
    p.step(-1)
    p.tick(2.0)
    assert meta.off_air.loads[-1] == "d"          # b, a, d


def test_two_quick_steps_on_go_on_two():
    p, meta = _on_b()
    p.step(1)
    p.step(1)
    p.tick(2.0)
    assert meta.off_air.loads[-1] == "d"          # b, c, d


def test_a_step_when_a_look_is_armed_fades_to_it_and_a_second_goes_past():
    p, meta = _on_b()
    p.tick(100.0 - LEAD_S + 1.0)                  # c armed
    armed = meta.off_air.loads[-1]
    assert armed == "c"
    count = len(meta.off_air.loads)
    p.step(1)
    p.tick(100.0)
    assert len(meta.off_air.loads) == count and p.at == 2


def test_a_step_while_stopped_moves_where_play_goes_on_from():
    p, meta, _ = playing(("a", 10.0), ("b", 10.0), ("c", 10.0))
    p.step(1)
    p.step(1)
    assert meta.fades == [] and meta.off_air.loads == []
    p.play()
    p.tick(0.0)
    assert meta.off_air.loads == ["c"]
    p.stop()
    p.step(-1)
    p.play()
    p.tick(1.0)
    assert meta.off_air.loads == ["c", "b"]


def test_an_edit_to_the_file_lands_at_the_next_load():
    p, meta, lib = playing(("a", 10.0), ("b", 10.0))
    p.play()
    p.tick(0.0)
    p.tick(0.0)
    meta.across()
    lib.doc = lst(("a", 10.0), ("z", 10.0)).to_doc()
    p.tick(10.0 - LEAD_S)
    assert meta.off_air.loads == ["z"]


def test_it_reads_again_by_the_name_it_was_chosen_by_not_the_name_inside():
    """A Drive conflict copy holds the name `cart`: reading by that would swap files."""
    lib = StandInLib(lst(("a", 10.0), ("b", 10.0), name="cart").to_doc())
    p = Playing(StandInMeta(), lib)
    assert p.select("cart (Dan's conflicted copy)")
    p.play()
    p.tick(0.0)
    assert set(lib.asked) == {"cart (Dan's conflicted copy)"}


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
    assert meta.off_air.loads == [] and len(meta.fades) == 1 and p.left(100.0) is None
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


# ------------------------------------------------------------------ the real fader

def test_a_missing_patch_on_the_real_decks_is_the_librarys_own_refusal_and_is_skipped(air):
    lib = air.lib
    playlist.save(lib, lst(("not-a-patch", 10.0), ("party-tumble", 10.0)))
    p = Playing(air.meta, lib)
    assert p.select("cart")
    p.play()
    p.tick(0.0)
    assert air.two.loaded_patch.current == "TUMBLE" and air.one.loaded_patch.current == "ACID"
    assert "skipped not-a-patch" in lib.warning and "not-a-patch" in lib.warning


def test_crossfade_seconds_zero_is_a_cut_on_the_real_meta_controller(air):
    meta = air.meta
    air.one.reg["output.xfade_s"].set(5.0)
    meta.crossfade(seconds=0)
    meta.tick(1.0, 0.05)
    assert air.mix.xfade == 1.0 and meta.timed is None and meta.on_air is air.two


def test_crossfade_seconds_write_nothing_over_output_xfade_s(air):
    meta = air.meta
    air.one.reg["output.xfade_s"].set(5.0)
    meta.crossfade(seconds=1.0)
    assert meta.timed.seconds == 1.0 and air.one.reg["output.xfade_s"].base == 5.0
    meta.tick(1.0, 0.0)
    meta.tick(1.5, 0.5)
    assert 0.0 < air.mix.xfade < 1.0
    meta.tick(2.0, 0.5)
    assert air.mix.xfade == 1.0 and air.mix.seconds == 5.0
    meta.crossfade()                              # and with none, the param's
    assert meta.timed.seconds == 5.0


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
