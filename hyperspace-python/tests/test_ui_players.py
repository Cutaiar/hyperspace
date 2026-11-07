"""The player select screen (wave 4 PS, plan 55): mouse-driven, by control id,
through the real panel and the real `MetaController`. Its decks stand in: what a
pointer's move does to a row is `test_players.py`'s; here, that the board moved it."""

import json
from types import SimpleNamespace

import pytest
from imgui_bundle import imgui
from test_ui_shell import build_rig, frame
from ui_driver import Driver

from hyperspace import deck as deck_mod
from hyperspace import devicelist, devices, routing, ui_graph, ui_pane, ui_players, undo
from hyperspace.deck import MetaController
from hyperspace.midiports import PortNames
from hyperspace.pads import models
from hyperspace.params import Registry
from hyperspace.players import FILE, Duty, Players
from hyperspace.ui import PAGE_KEYS

WIDE = (1600, 900)


class Fake(devices.Base):
    """A controller of `kind` with a status to read."""

    def __init__(self, role, kind="gamepad", said="connected", ctx=None):
        super().__init__(role, None, ctx)
        self.kind, self.said, self.io = kind, said, object()

    @property
    def status(self):
        return self.said


def _with_meta(r, tmp_path, monkeypatch, roles=("pad", "p2", "apc40", "leap")):
    """The real meta controller over stand-in decks, and a list of controllers."""
    monkeypatch.setattr(deck_mod, "meta_stack", lambda first, moves=None: SimpleNamespace())
    monkeypatch.setattr(deck_mod.undos, "install_meta", lambda u: None)
    meta = MetaController(SimpleNamespace(name="one", undo=SimpleNamespace()),
                          SimpleNamespace(name="two", undo=SimpleNamespace()),
                          Players.load(tmp_path))
    ctx = devices.Context(players=meta.players)
    kinds = {"apc40": "midi", "leap": "hands"}
    devs = [Fake(role, kinds.get(role, "gamepad"), ctx=ctx) for role in roles]
    regs = devices.DeviceRegistry(devices=devs, ctx=ctx)
    meta.players.tell(roles, ("pad", "apc40"))
    regs.point(meta.pointer, meta.panel_pointer)
    r.panel.meta, r.panel.devices = meta, regs
    return meta


@pytest.fixture()
def rig(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        r.meta = _with_meta(r, tmp_path, monkeypatch)
        d = Driver(step=lambda: frame(r.panel))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        r.reg["ui.page"].set(PAGE_KEYS.index("players"))
        d.run(d.wait(3))
        r.d = d
        yield r


def _corner(d, key):
    """A point on the lane its tokens leave free: its heading."""
    x0, y0, x1, _y1 = d.rect(key)
    return (x0 + x1) / 2, y0 + 4


def _head(d, key):
    """A token's own head, its number: its controllers are their own controls."""
    x0, y0, _x1, _y1 = d.rect(key)
    return x0 + 8, y0 + 8


def _drag(d, grip, to):
    """Press on `grip` (an id, or a point) and drop on `to` (a point, or a function
    of the driver, read once the press has scrolled what it needs into view)."""
    d.run(d.move(grip), d.wait(1), d.press(True), d.wait(1))
    d.run(d.move(to() if callable(to) else to, frames=6), d.wait(1), d.press(False), d.wait(1),
          d.park(), d.wait(1))


def _click(d, to):
    d.run(d.move(to), d.wait(1), d.press(True), d.press(False), d.wait(1))


def _said(r):
    return ui_players._state(r.panel)["said"]


# ---------------------------------------------------------------- a duty

def test_dragging_a_token_across_changes_duty_and_says_so(rig, tmp_path):
    r, d, meta = rig, rig.d, rig.meta
    _drag(d, _head(d, "players.p2"), _corner(d, "players.lane.off_air"))
    assert meta.players.get(2).duty == Duty.OFF_AIR
    assert meta.pointer("p2").deck is meta.off_air, "what it holds went with it"
    assert meta.pointer("pad").deck is meta.on_air, "nobody else moved"
    assert (tmp_path / FILE).exists(), "it stays: remembered"
    assert _said(r) == ("Player 2 off air: p2 now on deck 2; rows on deck 1 go quiet. "
                        "Stays until moved.")
    assert r.lib.status == _said(r), "on the footer too, the moment it happens"
    _drag(d, _head(d, "players.p2"), _corner(d, "players.lane.on_air"))
    assert meta.players.get(2).duty == Duty.ON_AIR
    assert meta.pointer("p2").deck is meta.on_air


def test_a_click_on_the_token_then_the_lane_changes_duty(rig):
    r, d, meta = rig, rig.d, rig.meta
    _click(d, _head(d, "players.p1"))
    assert ui_players._state(r.panel)["sel"] == (ui_players.SEL_PLAYER, 1)
    assert meta.players.get(1).duty == Duty.ON_AIR, "a click on a token alone moves nobody"
    _click(d, _corner(d, "players.lane.off_air"))
    assert meta.players.get(1).duty == Duty.OFF_AIR
    assert meta.pointer("pad").deck is meta.off_air and meta.pointer("leap").deck is meta.off_air


def test_a_click_on_a_lane_with_nobody_picked_moves_nobody_and_says_how(rig):
    r, d, meta = rig, rig.d, rig.meta
    before = [p.duty for p in meta.players]
    _click(d, _corner(d, "players.lane.off_air"))
    assert [p.duty for p in meta.players] == before
    assert "first" in _said(r)


def test_a_drop_on_nothing_moves_nobody(rig, tmp_path):
    r, d, meta = rig, rig.d, rig.meta
    x0, y0, _x1, _y1 = d.rect("players.lane.on_air")
    _drag(d, _head(d, "players.p2"), (x0 - 200, y0 + 10))
    assert meta.players.get(2).duty == Duty.ON_AIR and not (tmp_path / FILE).exists()
    assert ui_players._state(r.panel)["drag"] is None


def test_a_drag_whose_board_went_away_never_lands(rig, tmp_path):
    """Picked up, the section hidden, the mouse let go unseen: back in view with the
    mouse over a lane, nobody moves."""
    r, d, meta = rig, rig.d, rig.meta
    d.run(d.move(_head(d, "players.p2")), d.wait(1), d.press(True), d.wait(1))
    aim = _corner(d, "players.lane.off_air")
    d.run(d.move(aim, frames=4), d.wait(1))
    assert ui_players._state(r.panel)["drag"] is not None
    r.reg["ui.page"].set(PAGE_KEYS.index("view"))
    d.run(d.press(False), d.wait(3))
    r.reg["ui.page"].set(PAGE_KEYS.index("players"))
    d.run(d.wait(3))
    assert ui_players._state(r.panel)["drag"] is None
    assert meta.players.get(2).duty == Duty.ON_AIR and not (tmp_path / FILE).exists()


def test_a_token_dropped_in_its_own_lane_is_no_move(rig, tmp_path):
    r, d = rig, rig.d
    _drag(d, _head(d, "players.p2"), _corner(d, "players.lane.on_air"))
    assert not (tmp_path / FILE).exists() and not _said(r)


def test_an_empty_seat_takes_a_duty_and_says_it_holds_nothing(rig):
    r, d, meta = rig, rig.d, rig.meta
    _drag(d, _head(d, "players.p3"), _corner(d, "players.lane.off_air"))
    assert meta.players.get(3).duty == Duty.OFF_AIR
    assert _said(r) == "Player 3 off air: holds no controller yet. Stays until moved."


# ---------------------------------------------------------------- a controller

def test_dragging_a_controller_to_a_token_registers_it(rig, tmp_path):
    r, d, meta = rig, rig.d, rig.meta
    told = []
    meta.on_players.append(lambda: told.append(1))
    meta.move_player(2, Duty.OFF_AIR)
    d.run(d.wait(2))
    _drag(d, "players.ctl.leap", lambda: _head(d, "players.p2"))
    assert meta.players.player_of("leap").number == 2 and told == [1]
    assert meta.pointer("leap").deck is meta.off_air, "it goes to its new player's deck"
    assert "leap" in meta.players.controllers_of(2)
    assert "leap" not in meta.players.controllers_of(1)
    assert _said(r) == "leap to player 2, on deck 2."


def test_a_controller_clicked_then_a_token_registers_it(rig):
    r, d, meta = rig, rig.d, rig.meta
    _click(d, "players.ctl.leap")
    assert ui_players._state(r.panel)["sel"] == (ui_players.SEL_CTL, "leap")
    assert meta.players.player_of("leap").number == 1
    _click(d, _head(d, "players.p4"))
    assert meta.players.player_of("leap").number == 4
    assert ui_players._state(r.panel)["sel"] is None


def test_a_press_on_a_controller_is_not_a_press_on_its_token(rig):
    """A drag starts on what is under the mouse: the controller, not its player."""
    d, meta = rig.d, rig.meta
    _drag(d, "players.ctl.leap", _corner(d, "players.lane.off_air"))
    assert meta.players.get(1).duty == Duty.ON_AIR


def test_the_words_when_a_pad_is_given_away():
    words = ui_players.give_words("pad", 2, 1, True, "p2", True)
    assert "@p2" in words and "reopened" in words and "bare pad rows wait" in words
    assert "the bare ones" in ui_players.give_words("edge", 1, 1, False, "", False)


# ---------------------------------------------------------------- what is drawn

def test_a_token_shows_each_controller_as_itself_and_whether_it_is_there(rig):
    r, meta = rig, rig.meta
    r.panel.devices.get("leap").said = "lost"
    r.panel.devices.get("apc40").said = "off"
    meta.players.hold("gone", 3)
    held = {h.role: h for n in (1, 2, 3, 4) for h in ui_players.held(r.panel, n)}
    assert held["pad"].state == "on" and held["leap"].state == "lost"
    assert held["apc40"].state == "off" and held["gone"].state == "gone"
    assert held["leap"].glyph == "hands" and held["gone"].glyph == "unknown"


@pytest.mark.parametrize("model,glyph", [("xbox", "xbox"), ("x360", "xbox"), ("edge", "sony"),
                                         ("dualsense", "sony"), ("joycon-l", "joycon-l"),
                                         ("joycon-r", "joycon-r"), ("procon", "procon"),
                                         ("generic", "pad")])
def test_every_pad_has_its_own_glyph(model, glyph):
    assert ui_players.glyph_of_model(models.MODELS[model]) == glyph
    assert glyph in ui_players.GLYPHS


def test_every_glyph_draws_in_every_state(rig, monkeypatch):
    r, d = rig, rig.d
    real = ui_players.held

    def many(panel, number):
        if number != 1:
            return real(panel, number)
        return [ui_players.Held(f"r{k}", g, g, tuple(ui_players.STATE_WORDS)[k % 5])
                for k, g in enumerate(ui_players.GLYPHS)]
    monkeypatch.setattr(ui_players, "held", many)
    d.run(d.wait(2))
    assert "players" in ui_graph._state(r.panel)["pane_drawn"]


def test_the_tray_shows_a_pad_no_entry_reads(rig):
    r = rig
    claims = SimpleNamespace(taken={}, hub=SimpleNamespace(
        readers={"a": SimpleNamespace(name="DualSense", model=models.MODELS["dualsense"]),
                 "b": SimpleNamespace(name="Joy-Con (L)", model=models.MODELS["joycon-l"])},
        held={"b": object()}))
    r.panel.devices.ctx.pads = claims
    loose = ui_players.loose(r.panel)
    assert [(h.role, h.glyph) for h in loose] == [("DualSense", "sony")]
    st = ui_players._state(r.panel)
    assert ui_players._tray(r.panel, st, now=1e9) == loose
    r.d.run(r.d.wait(2))
    assert "players.tray.0" in r.d.rects


def test_the_header_and_the_footer_say_who_is_where(rig):
    r, d, meta = rig, rig.d, rig.meta
    assert ui_players.summary(r.panel) == "on air 1 2  ·  off air —"
    meta.move_player(2, Duty.OFF_AIR)
    assert ui_players.summary(r.panel) == "on air 1  ·  off air 2"
    assert ui_pane._said(r.panel, "players", "") == ui_players.summary(r.panel)
    assert "players.open" in d.rects


# ---------------------------------------------------------------- the fit rule

@pytest.mark.parametrize("width", [150.0, 178.0, 240.0, 320.0, 700.0, 960.0, 1900.0])
@pytest.mark.parametrize("s", [1.0, 1.6, 2.4])
@pytest.mark.parametrize("n", [0, 1, 5, 9])
def test_nothing_passes_the_edge_at_any_width(width, s, n):
    roles = [f"r{k}" for k in range(n)]
    duties = {1: Duty.ON_AIR, 2: Duty.OFF_AIR, 3: Duty.ON_AIR, 4: Duty.ON_AIR}
    bd = ui_players.lay_out(width, duties, {1: roles, 2: roles}, s, tray=n)
    for c in bd.cards.values():
        lane = bd.lanes[duties[c.number]]
        assert lane[0] <= c.rect[0] and c.rect[2] <= lane[2] + 0.01
        assert lane[1] <= c.rect[1] and c.rect[3] <= lane[3] + 0.01
        for _role, cell in c.cells:
            assert c.rect[0] <= cell[0] and cell[2] <= c.rect[2] + 0.01
            assert c.rect[1] <= cell[1] and cell[3] <= c.rect[3] + 0.01
    for b in (*bd.lanes.values(), bd.tray, *bd.tray_cells):
        assert 0 <= b[0] and b[2] <= width + 0.01
        assert b[3] <= bd.h + 0.01


def test_tokens_do_not_overlap():
    duties = dict.fromkeys((1, 2, 3, 4), Duty.ON_AIR)
    bd = ui_players.lay_out(240.0, duties, {1: ["a", "b", "c"]})
    rects = [c.rect for c in bd.cards.values()]
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]


def test_at_the_narrowest_two_tokens_sit_side_by_side():
    duties = dict.fromkeys((1, 2, 3, 4), Duty.ON_AIR)
    # the pane's 240, less its padding and two scrollbars: 178 measured in the app
    bd = ui_players.lay_out(178.0, duties, {1: ["a", "b", "c", "d"]})
    assert bd.cards[1].rect[1] == bd.cards[2].rect[1] < bd.cards[3].rect[1]
    cells = bd.cards[1].cells
    assert cells[0][1][1] == cells[1][1][1] < cells[2][1][1], "two controllers a row"
    assert bd.lanes[Duty.ON_AIR][3] < bd.lanes[Duty.OFF_AIR][1], "one lane over the other"


@pytest.mark.parametrize("side", [ui_graph.SIDE_MIN, ui_graph.SIDE_W])
def test_the_section_fits_the_pane(tmp_path, monkeypatch, side):
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        _with_meta(r, tmp_path, monkeypatch,
                   roles=("pad", "p2", "p3", "p4", "edge", "apc40", "leap", "osc1"))
        d = Driver(step=lambda: frame(r.panel))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        st = ui_graph._state(r.panel)
        st["side_w"] = side
        r.reg["ui.page"].set(PAGE_KEYS.index("players"))
        d.run(d.wait(4))
        (x, _y), (w, _h) = st["details_rect"]
        ids = [k for k in d.rects if k.startswith("players.") and k != "players.open"]
        assert len(ids) > 8
        for k in ids:
            assert d.rects[k][2] <= x + w + 1, (k, d.rects[k], x + w)


def test_the_band_under_the_canvas_draws_it(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        r.panel.desk = True
        imgui.get_io().display_size = imgui.ImVec2(960, 900)
        _with_meta(r, tmp_path, monkeypatch)
        d = Driver(step=lambda: frame(r.panel))
        d.record(monkeypatch.setattr)
        d.run(d.wait(2))
        r.reg["ui.page"].set(PAGE_KEYS.index("players"))
        d.run(d.wait(4))
        assert "players.lane.off_air" in d.rects


# ---------------------------------------------------------------- reaching it

def test_the_footer_chip_opens_it_large_and_it_moves_people_too(rig):
    r, d, meta = rig, rig.d, rig.meta
    _click(d, "players.open")
    assert ui_players._state(r.panel)["large"]
    d.run(d.wait(2))
    small, big = d.rect("players.p1"), d.rect("players.big.p1")
    assert big[2] - big[0] > (small[2] - small[0]) * 1.5, "large is large"
    _drag(d, _head(d, "players.big.p2"), _corner(d, "players.big.lane.off_air"))
    assert meta.players.get(2).duty == Duty.OFF_AIR


def test_the_section_chip_opens_it_large(rig):
    r, d = rig, rig.d
    _click(d, "players.large")
    assert ui_players._state(r.panel)["large"]


def test_the_key_opens_it_and_esc_closes_it_and_a_modifier_does_neither(rig):
    r, d = rig, rig.d
    st = ui_players._state(r.panel)
    d.run(d.key(imgui.Key.o))
    assert st["large"]
    d.run(d.key(imgui.Key.o))
    assert not st["large"]
    d.run(d.key(imgui.Key.o))
    assert st["large"]
    d.run(d.key(imgui.Key.escape), d.wait(1))
    assert not st["large"]
    d.run(d.key(imgui.Key.o, d.ctrl))
    assert not st["large"], "a modified O is not O"


def test_the_key_has_no_row_so_it_changes_nothing_on_the_output():
    """`Keys` polls the control window for every row whenever imgui is not typing: a
    key with a row opens the board and changes the look in one press."""
    taken = {b.source.removeprefix("key:") for b in routing.keymap()}
    assert ui_players.KEY not in taken
    assert not any(k.endswith(f"+{ui_players.KEY}") for k in taken)
    assert hasattr(imgui.Key, ui_players.KEY.lower())


def test_a_row_learned_onto_the_key_keeps_it(rig):
    r, d = rig, rig.d
    st = ui_players._state(r.panel)
    table = r.panel.router.table
    table.set_routes([*table.routes(), routing.Binding(f"key:{ui_players.KEY}", "view.bright", "push", 1.0)])
    d.run(d.key(imgui.Key.o))
    assert not st["large"]


def test_esc_in_a_text_field_leaves_the_board_open(rig):
    """The field has the key: `ui_graph.escaped`. A slider being typed into, for one."""
    r, d = rig, rig.d
    st = ui_players._state(r.panel)
    r.reg["ui.page"].set(PAGE_KEYS.index("view"))
    d.run(d.wait(3))
    st["large"] = True
    d.run(d.wait(2))
    io = imgui.get_io()
    d.run(d.move("view.instances"), d.wait(1))
    io.add_key_event(d.ctrl, True)
    d.run(d.press(True), d.press(False))
    io.add_key_event(d.ctrl, False)
    d.run(d.wait(2))
    assert io.want_text_input, "the field is open"
    d.run(d.key(imgui.Key.escape), d.wait(1))
    assert st["large"], "only the field closed"
    d.run(d.key(imgui.Key.escape), d.wait(1))
    assert not st["large"], "the next one is the board's"


def test_esc_closing_the_board_does_not_also_reach_graph(rig, monkeypatch):
    """The board draws first; GRAPH, asking after it in that frame, is told no."""
    r, d = rig, rig.d
    st = ui_players._state(r.panel)
    st["large"] = True
    d.run(d.wait(2))
    seen = []
    real = ui_players.window

    def spying(panel):
        pressed = imgui.is_key_pressed(imgui.Key.escape, False)
        real(panel)
        if pressed:
            seen.append((ui_players.took_escape(), ui_graph.escaped()))
    monkeypatch.setattr(ui_players, "window", spying)
    d.run(d.key(imgui.Key.escape), d.wait(1))
    assert not st["large"] and seen == [(True, False)]
    assert ui_players.took_escape() is False, "only for the frame it was taken"


def test_esc_drops_a_carried_token_and_the_release_moves_nobody(rig, tmp_path):
    r, d, meta = rig, rig.d, rig.meta
    st = ui_players._state(r.panel)
    d.run(d.move(_head(d, "players.p2")), d.wait(1), d.press(True), d.wait(1))
    aim = _corner(d, "players.lane.off_air")
    d.run(d.move(aim, frames=4), d.wait(1))
    assert st["drag"] is not None
    d.run(d.key(imgui.Key.escape), d.wait(2))
    assert st["drag"] is None, "and it is not picked straight back up"
    d.run(d.press(False), d.wait(2))
    assert meta.players.get(2).duty == Duty.ON_AIR and not (tmp_path / FILE).exists()
    assert st["sel"] is None, "the release is no click either"
    _drag(d, _head(d, "players.p2"), _corner(d, "players.lane.off_air"))
    assert meta.players.get(2).duty == Duty.OFF_AIR, "the next press drags as ever"


def test_esc_with_no_board_on_screen_is_graphs(rig, monkeypatch):
    """A pick survives no fold: GRAPH's Esc is neither lost to it nor spent on it."""
    r, d = rig, rig.d
    st = ui_players._state(r.panel)
    _click(d, _head(d, "players.p2"))
    assert st["sel"] == (ui_players.SEL_PLAYER, 2)
    r.reg["ui.page"].set(PAGE_KEYS.index("graph"))
    ui_pane.set_open(ui_graph._state(r.panel), "players", False)
    d.run(d.park(), d.wait(3))
    assert "players" not in ui_graph._state(r.panel)["pane_drawn"]
    assert st["sel"] is None, "it went with its board"
    seen = []
    real = ui_players.window

    def spying(panel):
        pressed = imgui.is_key_pressed(imgui.Key.escape, False)
        real(panel)
        if pressed:
            seen.append((ui_players.took_escape(), ui_graph.escaped()))
    monkeypatch.setattr(ui_players, "window", spying)
    d.run(d.key(imgui.Key.escape), d.wait(1))
    assert seen == [(False, True)], "the board took nothing: GRAPH has it"


def test_a_stamp_from_another_imgui_context_never_takes_graphs_esc(rig, monkeypatch):
    """A frame count starts again with a context (a relaunch, a test): an old stamp
    that happens to match must not swallow the key, with or without a meta controller."""
    r, d = rig, rig.d
    r.panel.meta = None
    seen = []
    real = ui_players.window

    def spying(panel):
        ui_players._esc_frame = imgui.get_frame_count()      # the coincidence
        real(panel)
        seen.append(ui_players.took_escape())
    monkeypatch.setattr(ui_players, "window", spying)
    d.run(d.wait(1))
    assert seen and not any(seen)


def test_esc_with_a_board_on_screen_still_lets_go_of_the_pick(rig):
    r, d = rig, rig.d
    st = ui_players._state(r.panel)
    _click(d, _head(d, "players.p2"))
    d.run(d.key(imgui.Key.escape), d.wait(1))
    assert st["sel"] is None


def test_a_stray_click_on_a_lane_after_a_move_moves_nobody(rig):
    d, meta = rig.d, rig.meta
    _click(d, _head(d, "players.p2"))
    _click(d, _corner(d, "players.lane.off_air"))
    assert meta.players.get(2).duty == Duty.OFF_AIR
    _click(d, _corner(d, "players.lane.on_air"))
    assert meta.players.get(2).duty == Duty.OFF_AIR, "it stays until someone moves it"


def test_a_large_boards_drag_does_not_outlive_it_while_the_pane_draws(rig, tmp_path):
    """The pane's board draws on: the large one's drag still goes when it closes."""
    r, d, meta = rig, rig.d, rig.meta
    st = ui_players._state(r.panel)
    st["large"] = True
    d.run(d.wait(2))
    d.run(d.move(_head(d, "players.big.p2")), d.wait(1), d.press(True), d.wait(1))
    d.run(d.move(_corner(d, "players.big.lane.off_air"), frames=4), d.wait(1))
    assert st["drag"] is not None and st["drag"][0] == ".big"
    st["large"] = False
    d.run(d.wait(3))
    assert st["drag"] is None
    d.run(d.press(False), d.wait(2))
    st["large"] = True
    d.run(d.wait(3))
    assert meta.players.get(2).duty == Duty.ON_AIR and not (tmp_path / FILE).exists()


def test_a_click_on_the_targets_controller_gives_the_picked_one(rig, tmp_path, monkeypatch):
    """Cells cover most of a token: a click on one is a click on that player."""
    d, meta = rig.d, rig.meta
    _click(d, "players.ctl.leap")
    _click(d, "players.ctl.p2")
    assert meta.players.player_of("leap").number == 2


def test_a_click_on_the_same_players_other_controller_picks_that_one(rig):
    r, d, meta = rig, rig.d, rig.meta
    _click(d, "players.ctl.leap")
    _click(d, "players.ctl.pad")
    assert ui_players._state(r.panel)["sel"] == (ui_players.SEL_CTL, "pad")
    assert meta.players.player_of("leap").number == 1


def test_a_move_the_file_did_not_keep_says_so(rig, tmp_path):
    r, d, meta = rig, rig.d, rig.meta
    meta.players.path = tmp_path / "no-such-folder" / FILE
    _drag(d, _head(d, "players.p2"), _corner(d, "players.lane.off_air"))
    assert meta.players.get(2).duty == Duty.OFF_AIR
    said = _said(r)
    assert "not remembered" in said and "Stays until moved" not in said
    assert ui_players._state(r.panel)["said_warn"] and r.lib.warning == said


def test_a_pad_an_entry_is_off_for_or_waits_for_is_not_loose(rig):
    r = rig
    edge = models.MODELS["edge"]
    ctx = r.panel.devices.ctx
    r.panel.devices.devices.append(devices.OffDevice("spare", "gamepad", {"controller": "edge"}, ctx))
    ctx.pads = SimpleNamespace(taken={}, hub=SimpleNamespace(
        readers={"a": SimpleNamespace(name="DualSense Edge", model=edge, vid=None, pid=None),
                 "b": SimpleNamespace(name="DualSense Edge", model=edge, vid=None, pid=None)},
        held={}))
    assert [h.role for h in ui_players.loose(r.panel)] == ["DualSense Edge"], "one is spoken for"


def test_an_entry_that_is_off_still_draws_as_itself():
    apc = devices.OffDevice("desk", "midi", {})
    keys = devices.OffDevice("keys", "midi", {"profile": "generic"})
    edge = devices.OffDevice("edge", "gamepad", {"controller": "edge"})
    assert ui_players._glyph_key(apc)[0] == "apc40"
    assert ui_players._glyph_key(keys)[0] == "midi"
    assert ui_players._glyph_key(edge) == ("sony", "DualSense Edge")
    assert ui_players._state_of(apc) == "off"


def test_no_stack_installed_says_nothing_of_where_no_stack_answers(monkeypatch):
    """Two ways to no stack: only the playlist's section speaks."""
    said = []
    monkeypatch.setattr(undo, "_meta", SimpleNamespace(_say=said.append))
    monkeypatch.setattr(undo, "_installed", None)
    monkeypatch.setattr(undo, "_where", lambda: False)
    assert undo.here() is None
    undo.undo()
    undo.redo()
    assert said == []
    monkeypatch.setattr(undo, "_where", lambda: None)
    assert undo.here() is None
    undo.undo()
    assert said == [undo.NOTHING_HERE]


def _real_stack(r, monkeypatch):
    """The board's moves on a real meta stack: the fixture's decks stand in, so the
    stack is over nothing else. `tick` is its frames, and the meta controller's."""
    meta = r.meta
    stack = undo.Undo(Registry(), deck_mod.MetaRows(SimpleNamespace(rows=[])),
                      moves=deck_mod.MetaPlayers(meta), called="on the meta controller")
    meta.undo = stack
    meta.presence = r.panel.devices.presence
    deck = undo.Undo(Registry(), deck_mod.MetaRows(SimpleNamespace(rows=[])), called="on deck 1")
    monkeypatch.setattr(undo, "_meta", stack)
    monkeypatch.setattr(undo, "_installed", deck)
    monkeypatch.setattr(undo, "_focused", deck)
    monkeypatch.setattr(undo, "_where", r.panel.in_meta_section)
    clock = [0.0]

    def tick(n=30):
        for _ in range(n):
            clock[0] += 1 / 60
            stack.tick(clock[0])
            deck.tick(clock[0])
            meta.tick(clock[0], 1 / 60)
        r.d.run(r.d.wait(2))
    r.tick = tick
    return stack


def _over(d, key="players.lane.on_air"):
    d.run(d.move(_corner(d, key)), d.wait(2))


def _drop(d, grip, to):
    """As `_drag`, with the mouse left where it dropped: over the board."""
    d.run(d.move(grip), d.wait(1), d.press(True), d.wait(1))
    d.run(d.move(to(), frames=6), d.wait(1), d.press(False), d.wait(1))


def test_cmd_z_over_the_board_is_the_meta_stack_s_and_the_latch_holds(rig, monkeypatch):
    """Row 740, amended, under row 753: coming to it takes nothing back until a move."""
    r, d, meta = rig, rig.d, rig.meta
    stack = _real_stack(r, monkeypatch)
    _over(d)
    assert ui_players.over(r.panel) and r.panel.in_meta_section() == undo.BOARD
    assert undo.here() is stack
    undo.undo()
    assert stack.status == "nothing to undo here yet: make a change on the meta controller first"
    _drop(d, _head(d, "players.p2"), lambda: _corner(d, "players.lane.off_air"))
    assert meta.players.get(2).duty == Duty.OFF_AIR
    assert not stack.latched or stack._will_open()


def test_cmd_z_over_the_board_takes_a_duty_back(rig, monkeypatch, tmp_path):
    r, d, meta = rig, rig.d, rig.meta
    stack = _real_stack(r, monkeypatch)
    _drop(d, _head(d, "players.p2"), lambda: _corner(d, "players.lane.off_air"))
    assert meta.players.get(2).duty == Duty.OFF_AIR
    assert _said(r) == ("Player 2 off air: p2 now on deck 2; rows on deck 1 go quiet. "
                        "Stays until moved. ⌘Z takes it back.")
    r.tick()
    assert [s.label for s in stack.stack] == ["player 2 to off air"]
    _over(d)
    undo.undo()
    r.tick()
    assert meta.players.get(2).duty == Duty.ON_AIR
    assert meta.pointer("p2").deck is meta.on_air
    assert json.loads((tmp_path / FILE).read_text())["duties"] == {}
    state = ui_players._state(r.panel)
    assert _said(r) == "undid player 2 to off air", "the line under the lanes follows"
    assert not state["said_warn"]
    undo.redo()
    r.tick()
    assert meta.players.get(2).duty == Duty.OFF_AIR and _said(r) == "redid player 2 to off air"


def test_cmd_z_over_the_large_board_takes_a_controller_back(rig, monkeypatch):
    r, d, meta = rig, rig.d, rig.meta
    stack = _real_stack(r, monkeypatch)
    told = []
    meta.on_players.append(lambda: told.append(1))
    ui_players._state(r.panel)["large"] = True
    d.run(d.wait(3))
    _drop(d, "players.big.ctl.leap", lambda: _head(d, "players.big.p2"))
    assert meta.players.player_of("leap").number == 2 and told == [1]
    assert _said(r) == "leap to player 2, on deck 1. ⌘Z takes it back."
    r.tick()
    _over(d, "players.big.lane.on_air")
    assert undo.here() is stack
    undo.undo()
    assert meta.players.player_of("leap").number == 1 and told == [1], "the list waits for the tick"
    r.tick()
    assert told == [1, 1] and _said(r) == "undid leap to player 2"


def test_a_controller_unplugged_since_stays_and_the_board_says_why(rig, monkeypatch):
    r, d, meta = rig, rig.d, rig.meta
    stack = _real_stack(r, monkeypatch)
    _drop(d, "players.ctl.leap", lambda: _head(d, "players.p2"))
    r.tick()
    r.panel.devices.get("leap").said = "lost"
    _over(d)
    undo.undo()
    r.tick()
    assert meta.players.player_of("leap").number == 2 and len(stack.stack) == 1
    assert _said(r) == ("not undone: leap unplugged since that move. Plug it back in and "
                        "try again")
    assert ui_players._state(r.panel)["said_warn"], "a refusal looks like one"
    r.panel.devices.get("leap").said = "connected"
    undo.undo()
    assert meta.players.player_of("leap").number == 1


def test_a_file_that_did_not_follow_the_undo_is_a_warning_on_the_line(rig, monkeypatch, tmp_path):
    r, d, meta = rig, rig.d, rig.meta
    _real_stack(r, monkeypatch)
    _drop(d, _head(d, "players.p2"), lambda: _corner(d, "players.lane.off_air"))
    r.tick()
    meta.players.path = tmp_path / "no" / "such" / FILE
    _over(d)
    undo.undo()
    r.tick()
    assert "not remembered after this run" in _said(r)
    assert ui_players._state(r.panel)["said_warn"]


def test_what_the_stack_says_elsewhere_stays_off_the_line(rig, monkeypatch):
    """An analyzer's undo minutes later is not the board's; nor a playlist's NOTHING_HERE."""
    r, d = rig, rig.d
    stack = _real_stack(r, monkeypatch)
    _drop(d, _head(d, "players.p2"), lambda: _corner(d, "players.lane.off_air"))
    r.tick()
    said = _said(r)
    stack._say("undid Attack 0.2 → 0.3")
    r.tick()
    assert _said(r) == said
    monkeypatch.setattr(undo, "_where", lambda: None)
    undo.undo()
    r.tick()
    assert stack.status == undo.NOTHING_HERE and _said(r) == said


def test_no_promise_of_cmd_z_when_it_would_not_answer(rig):
    """The rig's stand-in stack: not the one ⌘Z reaches, so the words do not say it."""
    r, d = rig, rig.d
    _drop(d, _head(d, "players.p2"), lambda: _corner(d, "players.lane.off_air"))
    assert "⌘Z" not in _said(r)


def test_off_the_board_a_deck_s_section_keeps_its_own_stack(rig, monkeypatch):
    r, d = rig, rig.d
    stack = _real_stack(r, monkeypatch)
    _over(d)
    assert undo.here() is stack
    d.run(d.park(), d.wait(2))
    assert not ui_players.over(r.panel) and undo.here() is undo._installed


def test_it_opens_with_the_panel_folded(rig):
    r, d = rig, rig.d
    r.panel.open = False
    d.run(d.wait(1), d.key(imgui.Key.o), d.wait(2))
    assert "players.big.p1" in d.rects


def test_a_panel_with_no_meta_controller_draws_no_board(tmp_path, monkeypatch):
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(*WIDE)
        d = Driver(step=lambda: frame(r.panel))
        d.record(monkeypatch.setattr)
        r.reg["ui.page"].set(PAGE_KEYS.index("players"))
        d.run(d.wait(4), d.key(imgui.Key.o))
        assert "players.open" not in d.rects and "players.lane.on_air" not in d.rects


def test_players_is_a_section_at_the_end_of_the_page_keys():
    """Append-only: every saved binding keeps its slot."""
    assert PAGE_KEYS.index("players") == 16 and PAGE_KEYS.index("system") == 15   # append-only
    assert "players" in ui_pane.KEYS


def test_the_section_is_folded_at_first():
    assert not ui_pane.DEFAULT_OPEN["players"] and not ui_pane.DEFAULT_BELOW["players"]


# ---------------------------------------------------------------- the pad's lights

def test_a_pads_lights_show_its_player():
    players = Players()
    ctx = devices.Context(players=players)
    pad = devices.PadDevice("edge", None, ctx)
    assert pad.identity == (devices.PLAYER_LIGHTS[0], 1)
    players.hold("edge", 3)
    assert pad.identity == (devices.PLAYER_LIGHTS[2], 3)
    own = devices.PadDevice("edge", {"light": "#102030", "player": 5}, ctx)
    assert own.identity == ((16, 32, 48), 5), "the entry's own word still wins"


def test_the_app_hands_the_panel_its_meta_controller():
    import inspect

    from hyperspace import app
    assert "panel.meta = meta" in inspect.getsource(app)


# ---------------------------------------------------------------- adopting (CT1)

class Opened:
    """A stand-in's adapter, as a port that opened."""

    on, error, name, last, bindings = True, "", "", "", ()

    def close(self):
        pass


@pytest.fixture()
def tray(rig, tmp_path, monkeypatch):
    """The board over a real registry and a real list in a scratch library, with what a
    Mac would see stood in: a MIDI port, and a pad a hub reads."""
    r = rig
    monkeypatch.setattr(devices.MidiDevice, "open", lambda self: setattr(self, "io", Opened()))
    monkeypatch.setattr(devices.PadDevice, "open", lambda self: setattr(self, "io", Opened()))
    monkeypatch.setattr(ui_players, "port_names", lambda: PortNames(r.ports, [], r.why))
    r.ports, r.why = ["Launch Control XL"], ""
    r.root = tmp_path / "Drive"
    r.root.mkdir()
    (tmp_path / "home").mkdir()
    seed = [{"role": "pad", "kind": "gamepad", "enabled": False}, {"role": "apc40", "kind": "midi", "enabled": False}]
    r.store = devicelist.DeviceList(r.root, tmp_path / "home", seed=seed)
    r.store.sync()
    ctx = devices.Context(players=r.meta.players, notes=[])
    regs = devices.DeviceRegistry(r.store.checked()[0], ctx, store=r.store)
    regs.point(r.meta.pointer, r.meta.panel_pointer)
    r.meta.on_players.append(lambda: regs.apply(regs.entries))
    r.panel.devices = regs
    ui_players._state(r.panel)["loose_at"] = -1e9
    r.d.run(r.d.wait(3))
    return r


def _lands(r, raw):
    """The other Mac changes the list, and the registry sees it."""
    (r.root / devicelist.FILE).write_text(json.dumps({"schema": devicelist.SCHEMA, "devices": raw}))
    r.store.waiting.clear()     # (the seed's hold, long over by then)
    r.store.sync()
    assert r.panel.devices.watch()


def _on_disk(r):
    r.store.sync()
    return {e["role"]: e for e in json.loads((r.root / devicelist.FILE).read_text())["devices"]}


def test_a_midi_port_nobody_lists_waits_in_the_tray_and_adopts_nothing_by_itself(tray):
    r = tray
    assert [h.role for h in ui_players.loose(r.panel)] == ["Launch Control XL"]
    r.d.run(r.d.wait(5))
    assert "players.tray.0" in r.d.rects
    assert set(_on_disk(r)) == {"pad", "apc40"}, "plugged in, and nothing is written"
    assert r.panel.devices.get("launch-control-xl") is None


def test_dragging_from_the_tray_adopts_it_for_that_player(tray):
    r, d, meta = tray, tray.d, tray.meta
    meta.move_player(2, Duty.OFF_AIR)
    d.run(d.wait(2))
    _drag(d, "players.tray.0", lambda: _head(d, "players.p2"))
    role = "launch-control-xl"
    assert _on_disk(r)[role] == {"role": role, "kind": "midi", "profile": "generic", "port": "Launch Control XL"}
    assert list(_on_disk(r)) == ["pad", "apc40", role], "at the end: nothing else moves"
    assert meta.players.player_of(role).number == 2
    assert meta.pointer(role).deck is meta.off_air
    assert r.panel.devices.get(role).status == "connected"
    assert _said(r) == ("Launch Control XL adopted as launch-control-xl: player 2 holds it here, "
                        "on deck 2. It goes on the list both Macs share.")
    assert json.loads(r.meta.players.path.read_text())["controllers"] == {role: 2}, "who holds it is this Mac's"
    assert "controllers" not in json.loads((r.root / devicelist.FILE).read_text())
    ui_players._state(r.panel)["loose_at"] = -1e9
    d.run(d.wait(2))
    assert not ui_players._state(r.panel)["loose"], "and it has left the tray"


def test_a_drag_dropped_on_nothing_adopts_nothing(tray):
    r, d = tray, tray.d
    _drag(d, "players.tray.0", (1, 1))
    assert set(_on_disk(r)) == {"pad", "apc40"} and not _said(r)


def test_a_tray_item_clicked_then_a_token_adopts_it(tray):
    r, d, meta = tray, tray.d, tray.meta
    _click(d, "players.tray.0")
    assert ui_players._state(r.panel)["sel"][0] == ui_players.SEL_TRAY
    _click(d, _head(d, "players.p3"))
    assert meta.players.player_of("launch-control-xl").number == 3
    assert ui_players._state(r.panel)["sel"] is None


def test_a_pad_from_the_tray_is_adopted_by_its_model_and_named_for_rows(tray):
    r, d, meta = tray, tray.d, tray.meta
    r.ports = []
    r.panel.devices.ctx.pads = SimpleNamespace(taken={}, hub=SimpleNamespace(
        readers={"a": SimpleNamespace(name="Joy-Con (L)", model=models.MODELS["joycon-l"])}, held={}))
    # (the list's own pad entry, off, would take this one: one that takes only an Edge)
    _lands(r, [{"role": "pad", "kind": "gamepad", "controller": "edge", "enabled": False},
               {"role": "apc40", "kind": "midi", "enabled": False}])
    ui_players._state(r.panel)["loose_at"] = -1e9
    d.run(d.wait(3))
    _drag(d, "players.tray.0", lambda: _head(d, "players.p2"))
    assert _on_disk(r)["joycon-l"]["controller"] == "joycon-l"
    assert r.panel.devices.get("joycon-l").qualifier == "p2", "player 2's first pad: @p2's rows"
    assert meta.players.player_of("joycon-l").number == 2


def test_a_port_an_entry_names_or_our_own_is_not_loose(tray):
    r = tray
    r.ports = ["Akai APC40", "Hyperspace Hands", "My Box", "Launch Control XL"]
    _lands(r, [*r.store.raw, {"role": "box", "kind": "midi", "profile": "generic", "port": "my box", "enabled": False}])
    assert [h.role for h in ui_players.loose(r.panel)] == ["Launch Control XL"]


def test_an_apc40_with_no_entry_is_drawn_as_itself_and_is_apc40(tray):
    r, d = tray, tray.d
    r.ports = ["Akai APC40"]
    _lands(r, [e for e in r.store.raw if e["kind"] != "midi"])
    ui_players._state(r.panel)["loose_at"] = -1e9
    d.run(d.wait(3))
    assert [(h.glyph, h.entry["role"]) for h in ui_players._state(r.panel)["loose"]] == [("apc40", "apc40")]
    _drag(d, "players.tray.0", lambda: _head(d, "players.p1"))
    assert _on_disk(r)["apc40"]["profile"] == "apc40"
    assert r.panel.devices.midi_roles() == ("apc40",)


def test_midi_off_on_this_mac_is_no_look(tray, monkeypatch):
    r = tray
    r.store.no_midi_look = True
    monkeypatch.setattr(ui_players, "port_names", lambda: pytest.fail("looked"))
    assert not ui_players.loose(r.panel)


def test_the_tray_looks_once_a_second_however_often_the_board_is_drawn(tray, monkeypatch):
    r = tray
    looks = []
    monkeypatch.setattr(ui_players, "port_names", lambda: looks.append(1) or PortNames([], [], ""))
    st = ui_players._state(r.panel)
    st["loose_at"] = 0.0
    for t in (0.5, 0.9, 1.1, 1.2, 2.2):
        ui_players._tray(r.panel, st, now=t)
    assert len(looks) == 2


def test_why_there_is_no_midi_is_said_on_the_board_not_a_crash(tray):
    r, d = tray, tray.d
    r.ports, r.why = [], "CoreMIDI refused a client (-10833)"
    ui_players._state(r.panel)["loose_at"] = -1e9
    d.run(d.wait(3))
    assert ui_players._state(r.panel)["midi_why"] == r.why


def test_a_board_with_no_list_is_read_only_as_it_was(rig):
    r, d, meta = rig, rig.d, rig.meta
    r.panel.devices.ctx.pads = SimpleNamespace(taken={}, hub=SimpleNamespace(
        readers={"a": SimpleNamespace(name="DualSense", model=models.MODELS["dualsense"])}, held={}))
    ui_players._state(r.panel)["loose_at"] = -1e9
    d.run(d.wait(3))
    _drag(d, "players.tray.0", lambda: _head(d, "players.p2"))
    assert not meta.players.controllers_of(2) or "dualsense" not in meta.players.controllers_of(2)


def test_the_board_says_the_library_is_not_there_and_an_adopt_still_lands_this_run(tray, tmp_path):
    r, d, meta = tray, tray.d, tray.meta
    (r.root / devicelist.FILE).unlink()
    r.root.rmdir()
    r.store.sync()
    d.run(d.wait(2))
    assert "isn't there" in r.store.said
    _drag(d, "players.tray.0", lambda: _head(d, "players.p2"))
    assert meta.players.player_of("launch-control-xl").number == 2
    assert r.panel.devices.get("launch-control-xl").status == "connected"
    said = _said(r)
    assert said.endswith(r.store.said) and "isn't there" in said
    assert ui_players._state(r.panel)["said_warn"]
    assert not r.root.exists()


def test_the_same_cell_clicked_again_is_no_second_seat(tray):
    """Review 5: a pad has no same-check, as two of a model are two seats. What stops a
    phantom is the tray: it's gone from there the moment it's adopted."""
    r, d = tray, tray.d
    r.ports = []
    joy = models.MODELS["joycon-l"]
    held = ui_players.Held(joy.name, "joycon-l", joy.name, "on", devicelist.pad_entry(joy))
    st = ui_players._state(r.panel)
    st["loose"], st["loose_at"] = [held], 1e12
    d.run(d.wait(2))
    _click(d, "players.tray.0")
    _click(d, _head(d, "players.p2"))
    assert held not in st["loose"], "not drawn again, this second or any other"
    d.run(d.wait(1))
    assert "players.tray.0" not in {k for k in d.rects if st["loose"]}
    assert [role for role in _on_disk(r) if role.startswith("joycon")] == ["joycon-l"]


def test_two_pads_of_one_model_loose_are_two_seats_one_drag_each(tray):
    r = tray
    joy = models.MODELS["joycon-l"]
    one = ui_players.Held(joy.name, "joycon-l", joy.name, "on", devicelist.pad_entry(joy))
    st = ui_players._state(r.panel)
    st["loose"] = [one, one]
    ui_players.adopt(r.panel, one, 2)
    assert st["loose"] == [one]
    ui_players.adopt(r.panel, one, 3)
    assert [k for k in _on_disk(r) if k.startswith("joycon")] == ["joycon-l", "joycon-l-2"]


def test_a_desk_like_another_is_still_loose_and_gets_a_port_of_its_own(tray):
    r = tray
    r.ports = ["Akai APC40", "APC40 mkII"]
    got = ui_players.loose(r.panel)
    assert [h.role for h in got] == ["APC40 mkII"], "the entry reads the first; the second is free"
    assert got[0].entry["port"] == "APC40 mkII"
    ui_players.adopt(r.panel, got[0], 2)
    assert _on_disk(r)["apc40-2"]["port"] == "APC40 mkII"
    assert not ui_players.loose(r.panel)


def test_the_tray_says_two_desks_of_one_name_show_as_one():
    assert "show as one" in ui_players.TWINS_TIP


def test_the_chip_turns_a_controller_on_or_off_on_this_mac_alone(tray):
    r, d = tray, tray.d
    before = (r.root / devicelist.FILE).read_text()
    assert r.panel.devices.get("pad").status.startswith("off")
    _click(d, "players.ctl.pad")
    d.run(d.wait(2))
    _click(d, "players.here")
    assert r.store.is_on("pad") and "on, on this Mac only" in _said(r)
    assert not r.panel.devices.get("pad").status.startswith("off")
    r.store.sync()
    assert (r.root / devicelist.FILE).read_text() == before
    assert json.loads((r.store.base / devicelist.HERE).read_text())["on"] == {"pad": True}


def test_an_earlier_moves_undo_leaves_an_adopted_controller_with_its_holder(tray):
    r, d = tray, tray.d
    calls = []
    real = deck_mod.undos.push_meta
    deck_mod.undos.push_meta = lambda words: (calls.append(words), real(words))
    try:
        _drag(d, "players.tray.0", lambda: _head(d, "players.p2"))
    finally:
        deck_mod.undos.push_meta = real
    assert calls == ["launch-control-xl to player 2"], "a step of its own, like any move"
    assert "⌘Z" not in _said(r), "it stays on the shared list, so ⌘Z isn't promised"


def test_a_tray_that_cannot_look_for_midi_says_why_and_still_finds_pads(tray, monkeypatch):
    r = tray
    r.panel.devices.ctx.pads = SimpleNamespace(taken={}, hub=SimpleNamespace(
        readers={"a": SimpleNamespace(name="Joy-Con (L)", model=models.MODELS["joycon-l"])}, held={}))
    _lands(r, [{"role": "apc40", "kind": "midi", "enabled": False}])

    def boom():
        raise RuntimeError("no backend")
    monkeypatch.setattr(ui_players, "port_names", boom)
    st = ui_players._state(r.panel)
    assert [h.name for h in ui_players.loose(r.panel, st)] == ["Joy-Con (L)"]
    assert "no backend" in st["midi_why"]
    st["loose_at"] = -1e9
    r.d.run(r.d.wait(3))            # a frame of the board draws through it


def test_a_bad_entry_in_the_walk_doesnt_reach_the_board(tray, monkeypatch):
    r = tray
    monkeypatch.setattr(devicelist, "midi_entry", lambda *a, **k: 1 / 0)
    r.ports = ["Somebody's Box"]
    assert ui_players.loose(r.panel) == []
