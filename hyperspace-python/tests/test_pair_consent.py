"""Register row 754 (plan 56): a person makes a row on a pair whose pole is
already mapped, and it asks. The owner, 2026-11-06: "when you create the pair in
general, it should tell you that part of this pair is already mapped. Then you
should have to explicitly consent to either keeping both mappings on that control
or the option to remove the existing mapping and let the pair take over that axis."

Each road over the real table, router, Learn and Edit; the panel's modal over
the headless panel; the undo over `boot`'s real three stacks.
"""

import json
from types import SimpleNamespace as NS

import pytest
from imgui_bundle import imgui
from test_paired_axes import ScriptedPad, clear_pad_rows, press
from test_paired_axes import rig as axes_rig  # noqa: F401 — the fixture, under its name
from test_ui_shell import frame
from test_ui_shell import rig as shell_rig  # noqa: F401 — the headless panel fixture
from test_undo import DT, SETTLE, boot

from hyperspace import devices, graphview, lfo, routing, ui_routing, undo
from hyperspace import gamepad as gp
from hyperspace.deck import Deck, MetaController
from hyperspace.learn import (
    CANCEL,
    KEEP_BOTH,
    META_UNDO,
    PAIR_SPRING_WANT,
    PAIR_WANT,
    TAKE_OVER,
    Learn,
    PairAsk,
    pair_lines,
    settle_pair,
)
from hyperspace.routing import Binding, Bindings, Router

UP_DOWN = "pair:UP/DOWN"
TARGET = "view.speed"
UP = gp.HATS["UP"]
DOWN = gp.HATS["DOWN"]


@pytest.fixture()
def rig(axes_rig):  # noqa: F811
    return axes_rig


def edit(rig) -> graphview.Edit:
    devs = devices.DeviceRegistry(devices=[devices.PadDevice("pad", io=ScriptedPad())])
    view = graphview.build(rig.table, rig.reg, rig.router, devs, None, None)
    return graphview.Edit(rig.table, rig.reg, rig.router, view)


def stepped(rig) -> str:
    return next(q.id for q in rig.reg
                if q.modulatable and q.integer and q.kind.name == "CONTINUOUS")


def two_presses(rig, want, pid=TARGET) -> PairAsk | None:
    rig.learn.arm(pid, want)
    rig.learn.learn_pad_button("hat:UP")
    rig.learn.learn_pad_button("hat:DOWN")
    return rig.learn.pair_ask


def by_learn_pair(rig):
    return two_presses(rig, PAIR_WANT)


def by_learn_spring(rig):
    return two_presses(rig, PAIR_SPRING_WANT)


def by_learn_source(rig):                    # any adapter's road (`want` None: a Learn pad)
    rig.learn.arm(TARGET, "pad")
    rig.learn.learn_source(UP_DOWN, centred=True)
    return rig.learn.pair_ask


def by_cable(rig):
    return edit(rig).connect(f"out:{UP_DOWN}", f"mod:{TARGET}")


def by_cable_stepped(rig):
    return edit(rig).connect(f"out:{UP_DOWN}", f"mod:{stepped(rig)}")


ROADS = [by_learn_pair, by_learn_spring, by_learn_source, by_cable, by_cable_stepped]


@pytest.mark.parametrize("road", ROADS)
def test_each_road_asks_when_a_pole_is_mapped_and_nothing_moves(rig, road):
    before = [(b.source, b.target, b.op) for b in rig.table.bindings]
    file = rig.path.read_text() if rig.path.exists() else None
    asked = road(rig)
    assert isinstance(asked, PairAsk) and asked.new.source == UP_DOWN
    assert [(b.source, b.target, b.op) for b in rig.table.bindings] == before
    assert (rig.path.read_text() if rig.path.exists() else None) == file
    lines = pair_lines(asked, rig.reg)
    assert any("d-pad up" in line and rig.reg["view.bright"].label in line for line in lines)
    assert any("d-pad down" in line and "meta controller" in line for line in lines)


@pytest.mark.parametrize("road", ROADS)
def test_each_road_lands_at_once_when_the_poles_are_free(rig, road):
    clear_pad_rows(rig.table)
    got = road(rig)
    assert not isinstance(got, PairAsk)
    assert rig.learn.pair_ask is None
    assert any(b.source == UP_DOWN for b in rig.table.bindings)


@pytest.mark.parametrize("road", ROADS)
def test_keep_both_lands_it_and_leaves_the_poles_rows(rig, road):
    asked = road(rig)
    said = settle_pair(asked, KEEP_BOTH, rig.reg)
    assert "both act" in said
    assert any(b.source == UP_DOWN for b in rig.table.bindings)
    assert {b.source for b in rig.table.of("hat")} >= {"hat:UP", "hat:DOWN"}


@pytest.mark.parametrize("road", ROADS)
def test_take_over_lands_it_and_the_poles_rows_go(rig, road):
    asked = road(rig)
    said = settle_pair(asked, TAKE_OVER, rig.reg)
    assert "took over" in said and rig.reg["view.bright"].label in said
    assert any(b.source == UP_DOWN for b in rig.table.bindings)
    assert not {b.source for b in rig.table.of("hat")} & {"hat:UP", "hat:DOWN"}
    held = {r["source"] for r in json.loads(rig.path.read_text())["bindings"]}
    assert not held & {"hat:UP", "hat:DOWN"}          # the meta row is gone from its file


@pytest.mark.parametrize("road", ROADS)
def test_cancel_lands_nothing(rig, road):
    before = [(b.source, b.target, b.op) for b in rig.table.bindings]
    asked = road(rig)
    assert "nothing landed" in settle_pair(asked, CANCEL, rig.reg)
    assert [(b.source, b.target, b.op) for b in rig.table.bindings] == before


def test_keep_both_acts_on_both_a_press_moves_each(rig):
    settle_pair(by_learn_pair(rig), KEEP_BOTH, rig.reg)
    speed, bright = rig.reg[TARGET], rig.reg["view.bright"]
    s0, b0 = speed.position(), bright.position()
    pad = ScriptedPad()
    pad.frame()
    press(rig, pad, 0.0, hat=UP)
    assert speed.position() == s0 + 1 and bright.position() > b0


def test_take_over_moves_only_the_pair(rig):
    settle_pair(by_learn_pair(rig), TAKE_OVER, rig.reg)
    speed, bright = rig.reg[TARGET], rig.reg["view.bright"]
    s0, b0 = speed.position(), bright.position()
    pad = ScriptedPad()
    pad.frame()
    press(rig, pad, 0.0, hat=UP)
    assert speed.position() == s0 + 1 and bright.position() == b0


def test_a_row_the_pair_does_not_conflict_with_does_not_ask(rig):
    clear_pad_rows(rig.table)
    rig.table.add(Binding("hat:LEFT", "view.bright", "step", 1.0))       # no pole of it
    rig.table.add(Binding("hat@p2:UP", "view.bright", "step", 1.0))      # another pad's
    rig.table.add(Binding("hat:UP", "view.bright", "step", 1.0, enabled=False))  # off
    assert by_learn_pair(rig) is None
    assert any(b.source == UP_DOWN for b in rig.table.bindings)


def test_the_same_pair_on_the_same_param_again_does_not_ask(rig):
    clear_pad_rows(rig.table)
    two_presses(rig, PAIR_WANT)
    assert two_presses(rig, PAIR_WANT) is None
    assert [b.source for b in rig.table.of("pair")] == [UP_DOWN]


def test_another_pairs_row_on_a_pole_asks_and_takes_over_splits_it(rig):
    clear_pad_rows(rig.table)
    rig.table.add(Binding("pair:UP/LEFT", "view.bright", "step", 3.0))
    asked = by_learn_pair(rig)
    assert any("pair UP / LEFT" in line for line in pair_lines(asked, rig.reg))
    said = settle_pair(asked, TAKE_OVER, rig.reg)
    assert [b.source for b in rig.table.of("pair")] == [UP_DOWN]
    assert [(b.source, b.value) for b in rig.table.of("hat")] == [("hat:LEFT", -3.0)]
    assert "keeps" in said


def test_a_learn_that_moves_its_lane_does_not_count_its_own_route(rig):
    """Learn's one-axis-one-param moves the pair's route off the old param, as it
    always did: that row is no overlap."""
    clear_pad_rows(rig.table)
    rig.table.add(Binding(UP_DOWN, "camera.zoom", "push", 0.5))
    assert by_learn_spring(rig) is None
    assert rig.table.owner(TARGET).source == UP_DOWN and rig.table.owner("camera.zoom") is None


def test_a_taken_target_is_one_question_and_one_answer(rig):
    """The referee's Replace / Keep does not stack on top: the answer that lands
    replaces the performer, read at that moment, and the words said so."""
    rig.table.add(Binding("lfo:0", TARGET, "push", 0.5))
    asked = by_cable(rig)
    assert isinstance(asked, PairAsk)
    settle_pair(asked, KEEP_BOTH, rig.reg)
    assert rig.table.owner(TARGET).source == UP_DOWN


def test_a_row_refused_at_the_answer_leaves_the_poles_alone(rig):
    asked = by_cable(rig)

    def refuse():
        raise ValueError("no")
    asked.land = refuse
    assert "nothing landed" in settle_pair(asked, TAKE_OVER, rig.reg)
    assert {b.source for b in rig.table.of("hat")} >= {"hat:UP", "hat:DOWN"}


def test_arming_forgets_the_question(rig):
    assert by_learn_pair(rig) is not None
    rig.learn.arm("view.bright", PAIR_WANT)
    assert rig.learn.pair_ask is None


# ---- review of #387 ----

def test_the_same_pair_on_another_param_is_one_lane_and_asks_nothing(rig):
    clear_pad_rows(rig.table)
    rig.table.add(Binding(UP_DOWN, "camera.zoom", "push", 0.5))
    got = by_cable(rig)                                # a cable fans it out
    assert isinstance(got, Binding)
    assert rig.table.owner("camera.zoom") is not None and rig.table.owner(TARGET) is got


def test_a_step_row_on_the_same_pair_elsewhere_stands(rig):
    clear_pad_rows(rig.table)
    rig.table.add(Binding(UP_DOWN, "view.bright", "step", 1.0))
    assert by_learn_pair(rig) is None
    assert {b.target for b in rig.table.of("pair")} == {"view.bright", TARGET}


def test_take_over_leaves_the_same_pair_elsewhere(rig):
    rig.table.add(Binding(UP_DOWN, "camera.zoom", "push", 0.5))
    settle_pair(by_cable(rig), TAKE_OVER, rig.reg)
    assert rig.table.owner("camera.zoom").source == UP_DOWN
    assert not {"hat:UP", "hat:DOWN"} & {b.source for b in rig.table.of("hat")}


def test_a_performer_on_the_target_alone_is_the_referees_question(rig):
    """Keep both could not keep it: `replace_owner` takes it. So this is Replace /
    Keep, and no pair question offers what the landing would undo."""
    clear_pad_rows(rig.table)
    theirs = rig.table.add(Binding("pair:UP/LEFT", TARGET, "push", 0.5))
    got = by_cable(rig)
    assert isinstance(got, graphview.Ask) and got.old is theirs
    assert rig.table.owner(TARGET) is theirs


def test_keep_both_says_only_what_still_stands(rig):
    theirs = rig.table.add(Binding("pair:UP/LEFT", TARGET, "push", 0.5))
    asked = by_cable(rig)
    assert not any(x is theirs for x in asked.rows)
    said = settle_pair(asked, KEEP_BOTH, rig.reg)
    assert "pair UP / LEFT" not in said and "d-pad up" in said
    assert rig.table.owner(TARGET).source == UP_DOWN


def test_an_unknown_answer_is_no_keep_both(rig):
    asked = by_cable(rig)
    with pytest.raises(ValueError):
        settle_pair(asked, "maybe", rig.reg)
    assert rig.table.owner(TARGET) is None or rig.table.owner(TARGET).source != UP_DOWN


@pytest.mark.parametrize("choice", [KEEP_BOTH, TAKE_OVER])
def test_poles_emptied_under_the_question_withdraw_it(rig, choice):
    asked = by_cable(rig)
    clear_pad_rows(rig.table)                          # as a meta undo's `set_rows` does
    assert asked.stale
    said = settle_pair(asked, choice, rig.reg)
    assert "nothing landed" in said and "as it was" not in said
    assert not any(b.source == UP_DOWN for b in rig.table.bindings)


def test_a_split_keeps_the_rows_gate(rig):
    clear_pad_rows(rig.table)
    rig.table.add(Binding("pair:UP/LEFT", "view.bright", "step", 3.0, when="hand:right.pinch.index",
                          scale=0.5))
    settle_pair(by_learn_pair(rig), TAKE_OVER, rig.reg)
    left = next(b for b in rig.table.of("hat") if b.source == "hat:LEFT")
    assert (left.value, left.when, left.scale) == (-3.0, "hand:right.pinch.index", 0.5)
    saved = next(r for r in json.loads(rig.path.read_text())["bindings"] if r["source"] == "hat:LEFT")
    assert saved["when"] == "hand:right.pinch.index"


def test_a_step_rows_take_over_writes_the_file_once(rig, monkeypatch):
    asked = by_learn_pair(rig)
    written = []
    real = routing.SessionTable.write

    def write(self, rows=None):
        written.append(1)
        real(self, rows)
    monkeypatch.setattr(routing.SessionTable, "write", write)
    settle_pair(asked, TAKE_OVER, rig.reg)
    assert len(written) == 1


@pytest.mark.parametrize("choice", [KEEP_BOTH, TAKE_OVER])
def test_a_step_rows_words_say_which_stack(rig, choice):
    said = settle_pair(by_learn_pair(rig), choice, rig.reg)
    assert META_UNDO in said


def test_a_route_kept_beside_a_meta_row_names_no_other_stack(rig):
    assert META_UNDO not in settle_pair(by_cable(rig), KEEP_BOTH, rig.reg)


def test_a_step_row_with_no_question_says_which_stack_too(rig):
    clear_pad_rows(rig.table)
    assert by_learn_pair(rig) is None and META_UNDO in rig.learn.last


# ---- only people get asked ----

def test_a_file_load_does_not_ask_and_both_act(rig, tmp_path):
    path = tmp_path / "with-pair.json"
    path.write_text(json.dumps({"schema": routing.SCHEMA, "profile": "apc40", "bindings": [
        {"source": "hat:UP", "target": "view.bright", "op": "step", "value": 3.0},
        {"source": UP_DOWN, "target": TARGET, "op": "step", "value": 1.0}]}))
    table = Bindings.load(path, legacy_midi=None)
    assert {b.source for b in table.bindings} >= {"hat:UP", UP_DOWN}
    # a patch's route on a mapped pole, as a load sets it
    rig.table.set_routes([Binding(UP_DOWN, TARGET, "push", 0.5)])
    assert rig.learn.pair_ask is None and rig.table.owner(TARGET).source == UP_DOWN
    assert any(b.source == "hat:UP" for b in rig.table.bindings)


def test_a_patch_loaded_under_the_question_withdraws_it(rig):
    asked = by_cable(rig)
    assert not asked.stale
    rig.table.set_routes([])
    assert asked.stale


# ---- the panel ----

@pytest.fixture()
def shell(shell_rig, tmp_path):  # noqa: F811
    table = Bindings.factory(path=routing.bindings_path(tmp_path))
    shell_rig.panel.router = Router(shell_rig.reg, table)
    shell_rig.panel.learn = Learn(shell_rig.reg, table)
    return NS(panel=shell_rig.panel, reg=shell_rig.reg, table=table,
              learn=shell_rig.panel.learn)


def test_routings_add_asks_and_the_modal_holds_it_until_answered(shell):
    panel, table = shell.panel, shell.table
    assert ui_routing.add_route(panel, TARGET, source=UP_DOWN, depth=0.5) is None
    assert table.owner(TARGET) is None
    frame(panel)
    assert ui_routing._state(panel)["modal"]
    assert ui_routing.pair_question_up(panel) is not None
    assert shell.learn.held                                   # no source completes a learn
    frame(panel)
    assert ui_routing.pair_question_up(panel) is not None     # no timer: still up
    ui_routing.answer_pair(panel, KEEP_BOTH)
    assert table.owner(TARGET).source == UP_DOWN
    assert any(b.source == "hat:UP" for b in table.bindings)
    frame(panel)
    assert not ui_routing._state(panel)["modal"] and not shell.learn.held
    assert "both act" in shell.learn.last


def test_enter_answers_nothing(shell):
    panel = shell.panel
    ui_routing.add_route(panel, TARGET, source=UP_DOWN, depth=0.5)
    frame(panel)
    io = imgui.get_io()
    assert not io.config_flags & imgui.ConfigFlags_.nav_enable_keyboard
    for down in (True, False):
        io.add_key_event(imgui.Key.enter, down)
        frame(panel)
    assert ui_routing.pair_question_up(panel) is not None
    assert shell.table.owner(TARGET) is None


def test_routings_source_combo_asks(shell):
    panel, table = shell.panel, shell.table
    b = table.add(Binding("lfo:0", TARGET, "push", 0.5))
    ui_routing._move_source(panel, panel.router, b, UP_DOWN)
    assert b.source == "lfo:0"
    asked = ui_routing.pair_question_up(panel)
    assert asked is not None and asked.new.source == UP_DOWN
    ui_routing.answer_pair(panel, TAKE_OVER)
    assert b.source == UP_DOWN and table.owner(TARGET) is b
    assert not any(x.source in ("hat:UP", "hat:DOWN") for x in table.bindings)


def test_routings_source_combo_lands_on_a_free_pair(shell):
    panel, table = shell.panel, shell.table
    for x in table.of("hat"):
        table.remove(x)
    b = table.add(Binding("lfo:0", TARGET, "push", 0.5))
    ui_routing._move_source(panel, panel.router, b, UP_DOWN)
    assert b.source == UP_DOWN and ui_routing.pair_question_up(panel) is None


def test_routes_replaced_under_the_modal_withdraw_it_in_plain_words(shell):
    panel, table = shell.panel, shell.table
    ui_routing.add_route(panel, TARGET, source=UP_DOWN, depth=0.5)
    table.set_routes([])                                # a load, or an undo
    frame(panel)
    assert ui_routing.pair_question_up(panel) is None
    assert not ui_routing._state(panel)["modal"]
    said = shell.learn.last
    assert "nothing landed" in said and "pair UP / DOWN" in said and table.owner(TARGET) is None
    assert "loaded" not in said and UP_DOWN not in said


def test_picking_the_source_a_row_has_asks_nothing(shell):
    panel, table = shell.panel, shell.table
    b = table.add(Binding(UP_DOWN, TARGET, "push", 0.5))     # as a file put it, poles mapped
    ui_routing._move_source(panel, panel.router, b, UP_DOWN)
    assert ui_routing.pair_question_up(panel) is None
    assert any(x.source == "hat:UP" for x in table.bindings)


def test_a_switched_off_route_moved_onto_a_pair_asks_nothing(shell):
    panel, table = shell.panel, shell.table
    b = table.add(Binding("lfo:0", TARGET, "push", 0.5, enabled=False))
    ui_routing._move_source(panel, panel.router, b, UP_DOWN)
    assert ui_routing.pair_question_up(panel) is None
    assert b.source == UP_DOWN and not b.enabled
    assert any(x.source == "hat:UP" for x in table.bindings)


def test_a_stepped_cable_says_which_stack_on_the_panel(shell):
    from hyperspace import ui_graph
    ui_graph._settle(shell.panel, Binding(UP_DOWN, TARGET, "step", 1.0))
    assert META_UNDO in shell.learn.last


def test_the_learn_road_comes_up_in_the_panels_modal(shell):
    shell.learn.arm(TARGET, PAIR_WANT)
    shell.learn.learn_pad_button("hat:UP")
    shell.learn.learn_pad_button("hat:DOWN")
    frame(shell.panel)
    assert ui_routing._state(shell.panel)["modal"]
    ui_routing.answer_pair(shell.panel, CANCEL)
    assert shell.learn.pair_ask is None
    assert not shell.table.of("pair")


def test_the_graph_page_puts_its_question_in_the_modal(shell):
    from hyperspace import ui_graph
    panel = shell.panel
    asked = PairAsk(shell.table, Binding(UP_DOWN, TARGET, "push", 0.5), lambda: None)
    ui_graph._settle(panel, asked)
    assert ui_routing.pair_question_up(panel) is asked


# ---- undo: one step on the stack it belongs to ----

@pytest.fixture()
def stacks(tmp_path):
    r = boot(tmp_path / "home")
    second = Deck.beside(r.deck, lfos=lfo.LFOs(seed=1))
    meta = MetaController(r.deck, second)
    r.lib.pointer = meta.panel_pointer
    inside = {"meta": False}
    undo.where(lambda: inside["meta"])
    table = r.deck.table
    for b in table.of("pair"):
        table.remove(b)
    return NS(r=r, reg=r.reg, table=table, meta=meta, inside=inside, two=second,
              learn=Learn(r.reg, table, lane=r.deck.router.lane))


def go(s, n: int = SETTLE) -> None:
    for _ in range(n):
        s.r.t += DT
        for u in s.meta.stacks:
            u.tick(s.r.t)


def depth(s) -> tuple[int, int]:
    return len(s.r.deck.undo.stack), len(s.meta.undo.stack)


def z(s, meta: bool) -> None:
    """A step taken off that stack, whichever a press would reach: the latch's
    answer to a press (row 753) has its own test below."""
    (s.meta.undo if meta else s.r.deck.undo).undo()
    go(s)


def press_z(s, meta: bool) -> None:
    s.inside["meta"] = meta
    undo.undo()
    go(s)


def hat_rows(table) -> set[str]:
    return {b.source for b in table.of("hat")}


def spring(s) -> PairAsk:
    s.learn.arm(TARGET, PAIR_SPRING_WANT)
    s.learn.learn_pad_button("hat:UP")
    s.learn.learn_pad_button("hat:DOWN")
    return s.learn.pair_ask


def test_keep_both_on_a_route_is_one_step_on_the_decks_stack(stacks):
    s = stacks
    go(s)
    was = depth(s)
    settle_pair(spring(s), KEEP_BOTH, s.reg)
    go(s)
    assert depth(s) == (was[0] + 1, was[1])
    z(s, meta=False)
    assert s.table.owner(TARGET).source != UP_DOWN and {"hat:UP", "hat:DOWN"} <= hat_rows(s.table)


def test_a_cancel_is_no_step(stacks):
    s = stacks
    go(s)
    was = depth(s)
    settle_pair(spring(s), CANCEL, s.reg)
    go(s)
    assert depth(s) == was


def test_a_meta_row_taken_over_comes_back_on_the_meta_stack_and_in_its_file(stacks):
    """A patch's route takes a meta row at a person's word. The route is one step
    on the deck's stack, the row one on the meta controller's, and neither stack
    reaches into the other."""
    s = stacks
    go(s)
    was = depth(s)
    said = settle_pair(spring(s), TAKE_OVER, s.reg)
    assert META_UNDO in said                         # which stack, in words
    go(s)
    assert depth(s) == (was[0] + 1, was[1] + 1)
    assert not {"hat:UP", "hat:DOWN"} & hat_rows(s.table)
    assert not {"hat:UP", "hat:DOWN"} & hat_rows(s.two.table)     # the meta layer: every deck's
    z(s, meta=True)
    assert {"hat:UP", "hat:DOWN"} <= hat_rows(s.table)
    assert {"hat:UP", "hat:DOWN"} <= hat_rows(s.two.table)
    assert s.table.owner(TARGET).source == UP_DOWN   # the deck's own step not taken with it
    held = {r["source"] for r in json.loads(s.table.path.read_text())["bindings"]}
    assert {"hat:UP", "hat:DOWN"} <= held
    z(s, meta=False)
    assert s.table.owner(TARGET).source != UP_DOWN


def test_a_step_row_on_a_meta_pole_is_one_step_on_the_meta_stack(stacks):
    s = stacks
    go(s)
    was = depth(s)
    s.learn.arm(TARGET, PAIR_WANT)
    s.learn.learn_pad_button("hat:UP")
    s.learn.learn_pad_button("hat:DOWN")
    settle_pair(s.learn.pair_ask, TAKE_OVER, s.reg)
    go(s)
    assert depth(s) == (was[0], was[1] + 1)
    z(s, meta=True)
    assert {"hat:UP", "hat:DOWN"} <= hat_rows(s.table)
    assert not s.table.of("pair")


def test_a_patches_route_taken_by_a_step_row_comes_back_on_the_decks_stack(stacks):
    """The other way about: a meta row's answer takes this patch's route."""
    s = stacks
    for b in s.table.of("hat"):
        s.table.remove(b)
    s.table.add(Binding("pair:UP/LEFT", "camera.zoom", "push", 0.5))
    go(s)
    was = depth(s)
    s.learn.arm(TARGET, PAIR_WANT)
    s.learn.learn_pad_button("hat:UP")
    s.learn.learn_pad_button("hat:DOWN")
    asked = s.learn.pair_ask
    assert any("this patch's" in line for line in pair_lines(asked, s.reg))
    settle_pair(asked, TAKE_OVER, s.reg)
    go(s)
    assert depth(s) == (was[0] + 1, was[1] + 1)
    assert s.table.owner("camera.zoom") is None
    z(s, meta=False)
    assert s.table.owner("camera.zoom").source == "pair:UP/LEFT"
    assert any(b.source == UP_DOWN for b in s.table.bindings)     # the meta step not taken


def test_a_meta_answer_leaves_the_other_decks_patch_alone(stacks):
    """No patch can affect another: the question reads this deck's rows, and its
    answer takes only those and the meta controller's."""
    s = stacks
    for b in s.table.of("hat"):
        s.table.remove(b)
    theirs = s.two.table.add(Binding("pair:UP/LEFT", "camera.zoom", "push", 0.5))
    s.learn.arm(TARGET, PAIR_WANT)
    s.learn.learn_pad_button("hat:UP")
    s.learn.learn_pad_button("hat:DOWN")
    assert s.learn.pair_ask is None                               # nothing of this deck's
    assert any(x is theirs for x in s.two.table.bindings)


def test_under_the_latch_a_taken_meta_row_comes_back_over_a_meta_section(stacks):
    """Row 753 shuts a stack you come to. The answer's meta push comes last, so that
    stack is in focus and open: the person's own click, then ⌘Z over a meta section."""
    s = stacks
    go(s)
    undo.by_hand(True)
    settle_pair(spring(s), TAKE_OVER, s.reg)
    go(s)
    press_z(s, meta=True)
    undo.by_hand(False)
    assert {"hat:UP", "hat:DOWN"} <= hat_rows(s.table)
    assert s.table.owner(TARGET).source == UP_DOWN
    press_z(s, meta=False)                           # the deck is shut: it says so
    assert s.table.owner(TARGET).source == UP_DOWN


def test_one_answer_on_the_step_road_is_one_press_of_z(stacks):
    """`settle_pair` and `_land_step` both push on the meta stack, in one frame: the
    inner push is the same action (`Undo.push`), so one press takes the whole answer."""
    s = stacks
    go(s)
    was = depth(s)
    undo.by_hand(True)
    s.learn.arm(TARGET, PAIR_WANT)
    s.learn.learn_pad_button("hat:UP")
    s.learn.learn_pad_button("hat:DOWN")
    settle_pair(s.learn.pair_ask, TAKE_OVER, s.reg)
    go(s)
    assert depth(s) == (was[0], was[1] + 1)
    press_z(s, meta=True)
    undo.by_hand(False)
    assert depth(s) == was
    assert {"hat:UP", "hat:DOWN"} <= hat_rows(s.table) and not s.table.of("pair")


def stacks_as_they_are(s) -> tuple:
    """Everything a refused landing must leave alone, of all three stacks."""
    return (undo._focused, *((len(u.stack), len(u.redos), u.latched, u._opens, u._open)
                             for u in s.meta.stacks))


@pytest.mark.parametrize("choice", [KEEP_BOTH, TAKE_OVER])
@pytest.mark.parametrize("hand", [False, True])
def test_a_refused_landing_leaves_every_stack_and_latch_as_it_was(stacks, choice, hand):
    """The referee refuses at the answer (row 743: a preset's row on a meta param):
    nothing is pushed, focus does not move, and no latch opens or shuts."""
    s = stacks
    go(s)
    undo.by_hand(hand)
    s.meta.undo.latched = True           # a shut stack is the case a push could open
    row = Binding(UP_DOWN, "master.gain", "push", 0.5)
    asked = PairAsk(s.table, row, lambda: s.table.replace_owner(row))
    asked.replaced = s.table.routes_replaced_n
    before, rows = stacks_as_they_are(s), list(s.table.bindings)
    said = settle_pair(asked, choice, s.reg)
    assert "nothing landed" in said
    assert stacks_as_they_are(s) == before
    go(s)
    undo.by_hand(False)
    assert stacks_as_they_are(s) == before and s.table.bindings == rows
