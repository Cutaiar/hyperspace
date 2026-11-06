"""What the panel says about the two `Deck`s (plan 44 D5e, rows 703, 704): a person can
always read which `Deck` they are looking at and which is on air, and the words about a
load, a dormant row and undo match what the code does since #380, #386 and #388."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest
from test_undo import boot

from hyperspace import lfo, ui, ui_desk, ui_loadable, ui_routing, undo
from hyperspace.deck import Deck, MetaController
from hyperspace.routing import Binding


@pytest.fixture
def rig(tmp_path):
    r = boot(tmp_path / "home")
    two = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    meta = MetaController(r.deck, two, mix=r.mix)
    yield NS(r=r, meta=meta, one=r.deck, two=two)
    undo.install(None)


# ---------------------------------------------------------------- ROUTING's dormant line

def _away_from(*heads):
    return NS(sources=NS(away_from=lambda router: frozenset(heads)))


def test_a_row_onto_a_meta_param_says_it_is_dormant_off_air_and_on_air_it_is_not(rig):
    """Row 650's rough edge: the words follow `Registry.lands`, whichever deck is on air."""
    b = Binding("lfo:0", "master.gain", "push", 0.5)
    words = ui_routing.dormant_words
    p = rig.two.reg["master.gain"]
    assert not rig.two.reg.lands(p)
    assert words(rig.two.reg, _away_from(), b, p) == ui_routing.DORMANT_OFF_AIR
    assert rig.one.reg.lands(p) and words(rig.one.reg, _away_from(), b, p) is None


def test_a_row_of_a_controller_on_the_other_deck_says_so(rig):
    """Plan 55: the reading is hidden from this deck; the line says why it reads nothing."""
    b = Binding("axis:LX", "view.bright", "push", 0.5)
    p = rig.two.reg["view.bright"]
    words = ui_routing.dormant_words
    assert words(rig.two.reg, _away_from("axis"), b, p) == ui_routing.DORMANT_AWAY
    assert words(rig.two.reg, _away_from("hand"), b, p) is None      # a deck off air's rows act


def test_a_row_qualified_with_a_player_reads_its_own_head(rig):
    b = Binding("axis@p2:LX", "view.bright", "push", 0.5)
    p = rig.two.reg["view.bright"]
    words = ui_routing.dormant_words
    assert words(rig.two.reg, _away_from("axis@p2"), b, p) == ui_routing.DORMANT_AWAY
    assert words(rig.two.reg, _away_from("axis"), b, p) is None


def test_a_row_off_or_with_no_target_does_not_say_it_twice(rig):
    b = Binding("axis:LX", "view.bright", "push", 0.5, enabled=False)
    words = ui_routing.dormant_words
    assert words(rig.two.reg, _away_from("axis"), b, rig.two.reg["view.bright"]) is None
    assert words(rig.two.reg, _away_from("axis"), Binding("axis:LX", "x", "push", 0.5), None) is None


def test_the_real_router_answers_the_line(rig):
    """The stand-in above has the real one's surface; with no devices nothing is away."""
    b = Binding("axis:LX", "view.bright", "push", 0.5)
    assert ui_routing.dormant_words(rig.two.reg, rig.two.router, b, rig.two.reg["view.bright"]) is None


# ---------------------------------------------------------------- the desk diagram's line

def _table(role="apc40"):
    return NS(primary_role=lambda: role)


def test_the_desk_says_which_deck_it_plays_while_the_panel_is_on_the_other(rig):
    meta = rig.meta
    panel = NS(meta=meta)
    meta.pointer("apc40")
    assert ui_routing.desk_elsewhere(panel, _table()) is None
    assert ui_desk._deck_words(panel, _table()) == ("deck 1 · on air", False)
    meta.point_panel(rig.two)
    assert ui_routing.desk_elsewhere(panel, _table()) == "the desk plays deck 1"
    assert ui_desk._deck_words(panel, _table()) == (
        "deck 2 · off air · the desk plays deck 1", True)


def test_the_desks_line_needs_a_desk(rig):
    """No such controller on this Mac: nothing plays anything, and asking creates no pointer."""
    meta = rig.meta
    meta.point_panel(rig.two)
    panel = NS(meta=meta)
    assert ui_routing.desk_elsewhere(panel, _table("")) is None
    assert ui_routing.desk_elsewhere(panel, _table("nothing")) is None
    assert "nothing" not in meta.pointers
    assert ui_routing.desk_elsewhere(panel, None) is None
    assert ui_routing.desk_elsewhere(NS(), _table()) is None
    assert ui_desk._deck_words(panel, _table("")) == ("deck 2 · off air", True)
    assert ui_desk._deck_words(NS(), _table()) == ("", False)


def test_the_desk_on_the_deck_off_air_with_the_panel_there_is_red_and_quiet(rig):
    meta = rig.meta
    meta.pointer("apc40").deck = rig.two
    meta.point_panel(rig.two)
    assert ui_desk._deck_words(NS(meta=meta), _table()) == ("deck 2 · off air", True)


# ---------------------------------------------------------------- the strip's hover

def test_the_strips_hover_says_the_deck(rig):
    meta = rig.meta
    assert ui_loadable._on_deck(None) == ""
    assert ui_loadable._on_deck(meta) == "  ·  deck 1 · on air"
    meta.point_panel(rig.two)
    assert ui_loadable._on_deck(meta) == "  ·  deck 2 · off air"


# ---------------------------------------------------------------- SYSTEM

def _fade(rig, stats_one, stats_two, on_air_two=False):
    one, two = (NS(renderer=NS(stats=stats_one, mix_error="")), NS(renderer=NS(stats=stats_two, mix_error="")))
    on, off = (two, one) if on_air_two else (one, two)
    return NS(on_air=on, off_air=off, decks=(one, two), drew=True, previewed=False, error="", warm_error="")


def test_system_names_each_gpu_block_by_its_deck_whichever_the_panel_is_on():
    """The panel's own renderer is the deck off air's when the panel is there: the block
    would read that deck twice and never the deck on air."""
    one = {"gpu_ms": {"scene": 1.0}}
    two = {"gpu_ms": {"dream": 9.0}}
    for on_air_two, head, lower in ((False, "deck 1 (on air) gpu", "deck 2 gpu"),
                                    (True, "deck 2 (on air) gpu", "deck 1 gpu")):
        p = NS(fade=_fade(None, one, two, on_air_two), renderer=NS(stats=two))
        lines = ui.Panel.gpu_lines(p)
        assert lines[0].startswith(head) and ("dream" in lines[1]) == on_air_two
        assert ui.Panel.deck2_gpu_lines(p)[0].startswith(lower)


# ---------------------------------------------------------------- what is true now

def test_the_sheet_has_no_pad_b_on_the_list_and_says_where_a_pad_loads():
    """`pad:B` went to `view.points` (factory rows), and no pad row walks the list."""
    words = dict(ui.CHEATSHEET)
    assert "pad's B" not in words["APC40 QUANT"] and "off air" in words["APC40 QUANT"]
    assert "off air" in words["APC40 clip pads"]
    assert "change" in words["Cmd+Z"]       # the undo latch (row 753)


@pytest.mark.parametrize("pid", ["preset.select", "preset.next", "preset.prev", "preset.load.0",
                                 "preset.list.next", "preset.list.prev", "preset.home"])
def test_every_load_from_a_row_says_off_air(rig, pid):
    assert "off air" in rig.one.reg[pid].tip


def test_homes_tip_does_not_promise_an_undo_the_latch_refuses(rig):
    tip = rig.one.reg["preset.home"].tip
    assert "takes nothing back" in tip and "Undo brings back" in tip


def test_a_person_s_control_is_not_called_tuning():
    """Row 746: a load or a save is not "tuned before the show"; the refusal says the same."""
    assert "tuned" not in ui_routing.PER_DECK_LINE
    assert "tuned" in ui_routing.META_LINE
