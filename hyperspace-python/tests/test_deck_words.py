"""What the panel says about the two `Deck`s (plan 44 D5e, rows 703, 704): a person can
always read which `Deck` they are looking at and which is on air, and the words about a
load, a dormant row and undo match what the code does since #380, #386 and #388."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture
from test_undo import boot

from hyperspace import lfo, routing, ui, ui_desk, ui_kit, ui_loadable, ui_players, ui_routing, undo
from hyperspace.deck import Deck, MetaController
from hyperspace.pointer import deck_number
from hyperspace.routing import Binding


@pytest.fixture
def rig(tmp_path):
    r = boot(tmp_path / "home")
    two = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    meta = MetaController(r.deck, two, mix=r.mix)
    yield NS(r=r, meta=meta, one=r.deck, two=two)
    undo.install(None)


# ---------------------------------------------------------------- ROUTING's dormant line

def _away(monkeypatch, router, *schemes):
    monkeypatch.setattr(type(router.sources), "away_from", lambda self, r: frozenset(schemes))


def test_a_row_onto_a_meta_param_says_it_is_dormant_off_air_and_on_air_it_is_not(rig):
    """Row 650's rough edge: the words follow `Registry.lands`, whichever deck is on air."""
    b = Binding("lfo:0", "master.gain", "push", 0.5)
    words = ui_routing.dormant_words
    p = rig.two.reg["master.gain"]
    assert not rig.two.reg.lands(p)
    assert words(rig.two.reg, rig.two.router, b, p) == ui_routing.DORMANT_OFF_AIR
    assert rig.one.reg.lands(p) and words(rig.one.reg, rig.one.router, b, p) is None


def test_a_row_of_a_controller_on_the_other_deck_says_so(rig, monkeypatch):
    """Plan 55: the reading is hidden from this deck; the line says why it reads nothing."""
    router = rig.two.router
    b = Binding("axis:LX", "view.bright", "push", 0.5)
    p = rig.two.reg["view.bright"]
    words = ui_routing.dormant_words
    _away(monkeypatch, router, "axis")
    assert words(rig.two.reg, router, b, p) == ui_routing.DORMANT_AWAY
    _away(monkeypatch, router, "hand")
    assert words(rig.two.reg, router, b, p) is None      # a deck off air's other rows act


def test_a_row_qualified_with_a_player_reads_its_own_scheme(rig, monkeypatch):
    router = rig.two.router
    b = Binding("axis@p2:LX", "view.bright", "push", 0.5)
    p = rig.two.reg["view.bright"]
    words = ui_routing.dormant_words
    _away(monkeypatch, router, "axis@p2")
    assert words(rig.two.reg, router, b, p) == ui_routing.DORMANT_AWAY
    _away(monkeypatch, router, "axis")
    assert words(rig.two.reg, router, b, p) is None


def test_a_row_qualified_with_the_primarys_own_role_reads_the_bare_scheme(rig, monkeypatch):
    """Review 2: `axis@pad:RT` on the primary pad is the bare scheme's lanes (B6)."""
    router = rig.two.router
    monkeypatch.setattr(router.table, "primaries", {"axis": "pad"}, raising=False)
    _away(monkeypatch, router, "axis")
    b = Binding("axis@pad:RT", "view.bright", "push", 0.5)
    assert ui_routing.dormant_words(rig.two.reg, router, b, rig.two.reg["view.bright"]) \
        == ui_routing.DORMANT_AWAY


def test_a_row_off_or_with_no_target_does_not_say_it_twice(rig, monkeypatch):
    router = rig.two.router
    _away(monkeypatch, router, "axis")
    words = ui_routing.dormant_words
    off = Binding("axis:LX", "view.bright", "push", 0.5, enabled=False)
    assert words(rig.two.reg, router, off, rig.two.reg["view.bright"]) is None
    assert words(rig.two.reg, router, Binding("axis:LX", "x", "push", 0.5), None) is None


def test_the_real_router_answers_the_line(rig):
    """With no devices nothing is away."""
    b = Binding("axis:LX", "view.bright", "push", 0.5)
    assert ui_routing.dormant_words(rig.two.reg, rig.two.router, b, rig.two.reg["view.bright"]) is None


# ---------------------------------------------------------------- the desk's line

def _table(role="apc40"):
    return NS(primary_role=lambda: role)


def _devices(status="connected", role="apc40"):
    return NS(get=lambda r: NS(status=status) if r == role else None)


def test_the_desk_says_which_deck_it_plays_while_the_panel_is_on_the_other(rig):
    meta = rig.meta
    panel = NS(meta=meta, devices=_devices())
    meta.pointer("apc40")
    assert ui_routing.desk_elsewhere(panel, _table()) is None
    assert ui_desk._deck_words(panel, _table()) == ("deck 1 · on air", "", False)
    meta.point_panel(rig.two)
    assert ui_routing.desk_elsewhere(panel, _table()) == "the desk plays deck 1"
    assert ui_desk._deck_words(panel, _table()) == (
        "deck 2 · off air", "the desk plays deck 1", True)


@pytest.mark.parametrize("status", ["lost", "off", "error: boom"])
def test_a_desk_unplugged_plays_nothing_though_its_pointer_stands(rig, status):
    """Review 5: every listed device has a pointer (`DeviceRegistry._point`)."""
    meta = rig.meta
    meta.pointer("apc40")
    meta.point_panel(rig.two)
    panel = NS(meta=meta, devices=_devices(status))
    assert ui_routing.desk_elsewhere(panel, _table()) is None
    assert ui_desk._deck_words(panel, _table()) == ("deck 2 · off air", "", True)


def test_the_desks_line_needs_a_desk(rig):
    """No such controller on this Mac: nothing plays anything, and asking creates no pointer."""
    meta = rig.meta
    meta.point_panel(rig.two)
    panel = NS(meta=meta, devices=_devices())
    assert ui_routing.desk_elsewhere(panel, _table("")) is None
    assert ui_routing.desk_elsewhere(panel, _table("nothing")) is None
    assert "nothing" not in meta.pointers
    assert ui_routing.desk_elsewhere(panel, None) is None
    assert ui_routing.desk_elsewhere(NS(meta=meta), _table()) is None     # no device registry
    assert ui_routing.desk_elsewhere(NS(), _table()) is None
    assert ui_desk._deck_words(NS(), _table()) == ("", "", False)


def test_the_desk_on_the_deck_off_air_with_the_panel_there_is_red_and_quiet(rig):
    meta = rig.meta
    meta.pointer("apc40").deck = rig.two
    meta.point_panel(rig.two)
    assert ui_desk._deck_words(NS(meta=meta, devices=_devices()), _table()) == (
        "deck 2 · off air", "", True)


def test_a_narrow_header_drops_the_clause_first_and_keeps_the_name(shell_rig):  # noqa: F811
    """Review 6: the look's name is never left a bare ellipsis for the deck's words."""
    w = lambda t: 10.0 * len(t)
    deck, away, name = "deck 2 · off air", "the desk plays deck 1", "TUMBLE"
    assert ui_desk.fit_deck(deck, away, name, 1000.0, w) == f"{deck} · {away}"
    room = w(deck) + w(name) + 8.0
    assert ui_desk.fit_deck(deck, away, name, room, w) == deck
    # past that, the name keeps its minimum and the deck is cut (real font metrics)
    from imgui_bundle import imgui

    imgui.new_frame()
    try:
        said = ui_desk.fit_deck(deck, away, "A LONG LOOK NAME", 90.0)
        assert said.endswith("…") and imgui.calc_text_size(said).x <= 90.0 - ui_desk.NEIGHBOUR_MIN
    finally:
        imgui.end_frame()


def _header_says(panel, table, monkeypatch):
    from imgui_bundle import imgui

    said = []
    real = imgui.text_colored
    monkeypatch.setattr(imgui, "text_colored", lambda c, s: (said.append(s), real(c, s))[1])
    imgui.new_frame()
    imgui.set_next_window_size(imgui.ImVec2(420, 80))
    imgui.begin("probe")
    try:
        ui_desk._header(panel, table)
    finally:
        imgui.end()
        imgui.end_frame()
    return said


def test_a_pick_with_the_header_to_itself_still_says_the_deck(rig, shell_rig, monkeypatch):  # noqa: F811
    """Review 3: a person about to rebind sees which deck it lands on."""
    meta = rig.meta
    meta.point_panel(rig.two)
    panel = shell_rig.panel
    monkeypatch.setattr(panel, "meta", meta, raising=False)
    table = ui_routing.router_of(panel).table
    monkeypatch.setattr(ui_desk, "picked", lambda p: NS(glyph="K1"))
    monkeypatch.setattr(ui_desk, "pick_line", lambda p, t, c: ("K1 " + "next click maps it " * 12, True))
    monkeypatch.setattr(ui_desk, "left", lambda p: 3.0)
    said = _header_says(panel, table, monkeypatch)
    assert said[0].startswith("deck 2") and len(said) == 2 and said[1].startswith("K1")


def test_no_table_still_says_the_deck(rig, shell_rig, monkeypatch):  # noqa: F811
    meta = rig.meta
    meta.point_panel(rig.two)
    panel = shell_rig.panel
    monkeypatch.setattr(panel, "meta", meta, raising=False)
    assert "deck 2 · off air" in _header_says(panel, None, monkeypatch)


# ---------------------------------------------------------------- the strip

def _page_draws(panel, monkeypatch):
    from imgui_bundle import imgui

    buttons, micro = [], []
    real_button, real_micro = imgui.button, ui._micro
    monkeypatch.setattr(imgui, "button", lambda s, *a: (buttons.append(s), real_button(s, *a))[1])
    monkeypatch.setattr(ui, "_micro", lambda s, *a: (micro.append(s), real_micro(s, *a))[1])
    imgui.new_frame()
    imgui.begin("probe")
    try:
        ui_loadable.page(panel)
    finally:
        imgui.end()
        imgui.end_frame()
    if ui_kit.ready():          # the kit strip (ui_strip): its name and the button's width
        st = ui_loadable._state(panel)
        r = st["rects"]["strip.loadable.name"]
        return (st["names"]["loadable"], round(r[2] - r[0], 3)), micro
    return next(b for b in buttons if b.endswith("##name")), micro


def test_the_deck_is_said_over_the_strip_and_costs_the_name_nothing(rig, shell_rig, monkeypatch):  # noqa: F811
    """Review 1: the name's button is NAME_MAX wide; two looks sharing first letters stay
    two names on the main readout, whichever deck."""
    panel = shell_rig.panel
    bare, micro = _page_draws(panel, monkeypatch)
    assert "off air" not in " ".join(micro)
    rig.meta.point_panel(rig.two)
    monkeypatch.setattr(panel, "meta", rig.meta, raising=False)
    named, micro = _page_draws(panel, monkeypatch)
    assert named == bare and "deck" not in str(named)
    assert "deck 2 · off air" in micro


def test_the_strips_hover_says_the_deck(rig):
    meta = rig.meta
    assert ui_loadable._on_deck(None) == ""
    assert ui_loadable._on_deck(meta) == "  ·  deck 1 · on air"
    meta.point_panel(rig.two)
    assert ui_loadable._on_deck(meta) == "  ·  deck 2 · off air"


def test_one_deck_number_everywhere():
    """Review 10: `deck_name`, the players' screen and SYSTEM ask one helper."""
    one, two = object(), object()
    assert deck_number((one, two), one) == 1 and deck_number((one, two), two) == 2
    assert ui_players._deck_no(NS(decks=(one, two)), two) == 2


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
    """`pad:E` went to `view.points` (factory rows), and no pad row walks the list."""
    words = dict(ui.CHEATSHEET)
    assert "pad's B" not in words["APC40 QUANT"] and "off air" in words["APC40 QUANT"]
    assert "off air" in words["APC40 clip pads"]
    assert "change" in words["Cmd+Z"]       # the undo latch (row 753)


@pytest.mark.parametrize("pid", ["preset.select", "preset.next", "preset.prev", "preset.load.0",
                                 "preset.list.next", "preset.list.prev", "preset.home"])
def test_every_load_from_a_row_says_off_air(rig, pid):
    assert "off air" in rig.one.reg[pid].tip


def test_homes_tip_promises_no_undo_the_latch_can_refuse(rig):
    """Review 4: the latch goes by focus, so the tip points at the line that knows."""
    tip = rig.one.reg["preset.home"].tip
    assert "brings back" not in tip and "whether ⌘Z takes it back" in tip


def test_a_person_s_control_is_not_called_tuning():
    """Row 746: a load or a save is not "tuned before the show". Review 7: and a per-`Deck`
    meta param may be a slider, as `poi.length`, so nothing says "press"."""
    assert "tuned" not in ui_routing.PER_DECK_LINE and "press" not in ui_routing.PER_DECK_LINE
    assert "press" not in routing.PER_DECK_WORDS
    assert "tuned" in ui_routing.META_LINE


def test_the_line_is_drawn_under_the_row(shell_rig, monkeypatch):  # noqa: F811
    """The side pane's row (`ui_graph._route_row` draws `_row`), on the real widgets."""
    from imgui_bundle import imgui

    panel = shell_rig.panel
    router = ui_routing.router_of(panel)
    _away(monkeypatch, router, "axis")
    said = []
    real = imgui.text_colored
    monkeypatch.setattr(imgui, "text_colored", lambda c, s: (said.append(s), real(c, s))[1])
    imgui.new_frame()
    imgui.begin("probe")
    try:
        ui_routing._row(panel, router, Binding("axis:LX", "view.bright", "push", 0.5), 0)
        assert ui_routing.DORMANT_AWAY in said
        said.clear()
        ui_routing._row(panel, router, Binding("lfo:0", "view.bright", "push", 0.5), 1)
        assert ui_routing.DORMANT_AWAY not in said
    finally:
        imgui.end()
        imgui.end_frame()
