"""Plan 53 N1a: node mode on a desk, over two `Deck`s and fake ports.

The rows come from what the patch saved (`nodemode`), for the player's first desk, on the
deck that desk is on. They are never in the table's rows, never in the file, and no patch
reaches another through them.
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import mido
import numpy as np
import pytest
from test_meta_controller import DESK, _pointed
from test_midi import FakeIn, FakeOut
from test_undo import boot

from hyperspace import apc40, app, devices, generic, learn, node_desk, nodemode, routing, undo
from hyperspace.bands import CEIL
from hyperspace.midi import MidiIO
from hyperspace.players import Duty
from hyperspace.routing import Binding

K1, K2, K3 = 0x30, 0x31, 0x32
D1, D5 = 0x10, 0x14
FADER = apc40.CC_FADER


def cc(control, value, channel=0):
    return mido.Message("control_change", channel=channel, control=control, value=value)


def note(n, vel=127, channel=0):
    return mido.Message("note_on" if vel else "note_off", channel=channel, note=n, velocity=vel)


@pytest.fixture()
def rig(tmp_path):
    p = _pointed(boot(tmp_path / "home"))
    ctx = devices.Context(reg=p.one.reg, table=p.one.table)
    p.midi = p.r.midi
    p.desk = devices.MidiDevice(DESK, {"profile": "apc40"}, ctx, io=p.midi)
    p.devs = devices.DeviceRegistry(devices=[p.desk], ctx=ctx)
    p.one.table.midi_roles = (DESK,)
    p.devs.point(p.meta.pointer, p.meta.panel_pointer)
    node_desk.install(p.meta, p.devs)
    p.nd1, p.nd2 = p.one.table.node_desk, p.two.table.node_desk

    def push(*msgs):
        p.r.inp.queue.extend(msgs)
        p.midi.poll()

    p.push = push
    p.push()
    yield p
    undo.install(None)


def pick_node(deck, want: int = 4) -> tuple[str, list[str]]:
    """A node of `deck`'s patch with at least `want` params to fill, on no row of the desk's."""
    patch = deck.loaded_patch
    for n in sorted(patch._pointable()):
        params = nodemode.fillable(deck.reg, patch.node_params(n))
        if len(params) >= want and not any(b.target in params for b in deck.table.bindings):
            return n, params
    raise AssertionError("no node with params in the corpus patch")


def make_small(deck, *pids) -> None:
    """Every node of `deck`'s patch holds only `pids`, for a test of a small node."""
    deck.loaded_patch.node_params = lambda _node: list(pids)


# ---------------------------------------------------------------- the rows


def test_rows_come_from_the_saved_state_and_nothing_else(rig):
    node, params = pick_node(rig.one)
    assert rig.nd1.rows() == []
    assert rig.one.loaded_patch.point_node_mode(1, "midi", node) is None
    rows = rig.nd1.rows()
    assert [b.target for b in rows] == params[:len(rows)]
    assert rows[0].source == f"cc:0:{K1}" and rows[0].feedback == "ring"
    assert all(a is b for a, b in zip(rows, rig.nd1.rows(), strict=True))   # the same objects
    rig.one.loaded_patch.leave_node_mode(1, "midi")
    assert rig.nd1.rows() == []


def test_rows_are_not_in_the_table_the_file_or_the_routes(rig):
    t, patch = rig.one.table, rig.one.loaded_patch
    node, _ = pick_node(rig.one)
    desk = [b.to_json() for b in t.desk()]
    routes = [b.to_json() for b in t.routes()]
    file_rows = t.to_json()
    assert patch.point_node_mode(1, "midi", node) is None
    assert rig.nd1.rows()
    assert not any(b is x for b in rig.nd1.rows() for x in t.bindings)
    assert [b.to_json() for b in t.desk()] == desk
    assert [b.to_json() for b in t.routes()] == routes
    assert t.to_json() == file_rows
    doc = patch.document("x")
    assert doc[nodemode.KEY] == [{"player": 1, "controller": "midi", "node": node}]
    assert not {b.target for b in rig.nd1.rows()} & {r["target"] for r in doc.get("desk") or ()}


def test_a_knob_moves_the_nodes_param_and_its_ring_says_so(rig):
    node, params = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    rig.push()
    mark = len(rig.r.out.sent)
    p = rig.one.reg[params[0]]
    rig.push(cc(K1, 127))
    for _ in range(40):
        rig.r.t += 0.05
        rig.push()
    assert p.norm == pytest.approx(1.0, abs=0.02)
    rings = [m.value for m in rig.r.out.sent[mark:]
             if m.type == "control_change" and m.control == K1]
    assert rings and rings[-1] == 127


def test_a_row_shadowed_comes_back_and_a_control_not_filled_keeps_its_row(rig):
    node, params = pick_node(rig.one)
    make_small(rig.one, *params[:2])
    t = rig.one.table
    k3_saved = next(b for b in t.desk() if b.source == f"cc:0:{K3}")
    k1_saved = next(b for b in t.desk() if b.source == f"cc:0:{K1}")
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert [b.target for b in t.dispatch("cc", 0, K1, DESK)] == [params[0]]
    assert [b.target for b in t.dispatch("cc", 0, K3, DESK)] == [k3_saved.target]
    assert k1_saved not in t.active(DESK)
    assert rig.nd1.under(k1_saved) and not rig.nd1.under(k3_saved)
    rig.one.loaded_patch.leave_node_mode(1, "midi")
    assert [b.target for b in t.dispatch("cc", 0, K1, DESK)] == [k1_saved.target]
    assert not rig.nd1.under(k1_saved)


def test_shift_is_the_global_layer_as_it_was(rig):
    node, _ = pick_node(rig.one)
    t = rig.one.table
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    rig.push(note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))
    assert t.layer_of(DESK) == "global"
    assert [b.target for b in t.dispatch("cc", 0, K1, DESK)] == ["hands.smooth"]
    assert "tempo.bpm" in {b.target for b in t.active(DESK)}
    assert not any(b is x for b in t.active(DESK) for x in rig.nd1.rows())
    rig.push(note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))
    assert any(b is rig.nd1.rows()[0] for b in t.active(DESK))


def test_a_mapping_already_on_the_node_stays_and_the_rest_fill(rig):
    node, params = pick_node(rig.one)
    t = rig.one.table
    t.bind(Binding(f"cc:0:{D5}", params[0], "abs", layer="preset"), write=False)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    rows = rig.nd1.rows()
    assert params[0] not in {b.target for b in rows}
    assert rows[0].target == params[1] and rows[0].source == f"cc:0:{K1}"
    assert f"cc:*:{D5}" not in {b.source for b in rows}      # its freedom is taken
    assert [b.target for b in t.dispatch("cc", 0, D5, DESK)] == [params[0]]
    assert rig.nd1._follow(DESK).fit.kept == (params[0],)


def test_a_route_from_a_modulator_does_not_keep_its_param_from_filling_but_a_pads_does(rig):
    node, params = pick_node(rig.one)
    t = rig.one.table
    make_small(rig.one, *params[:2])
    t.bind(Binding("lfo:0", params[0], "push", 0.5), write=False)
    t.bind(Binding("axis:LX", params[1], "push", 0.5), write=False)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert [b.target for b in rig.nd1.rows()] == [params[0]]
    assert rig.nd1._follow(DESK).fit.kept == (params[1],)


def test_what_does_not_fit_is_listed_and_not_paged(rig, monkeypatch):
    node, params = pick_node(rig.one, 4)
    monkeypatch.setattr(apc40, "degrees_of_freedom", lambda: [(f"cc:0:{K1}",), (f"cc:0:{K2}",)])
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    fit = rig.nd1._follow(DESK).fit
    assert len(rig.nd1.rows()) == 2
    assert fit.over == tuple(params[2:])
    assert fit.too_many(node) == nodemode.TOO_MANY.format(
        node=node.removeprefix("render:"), params=", ".join(params[2:]))


def test_no_meta_param_is_ever_a_row(rig):
    deck = rig.one
    for node in sorted(deck.loaded_patch._pointable()):
        if rig.nd1.refusal(DESK, node) is None:
            deck.loaded_patch.point_node_mode(1, "midi", node)
            for b in rig.nd1.rows():
                assert routing.meta_refusal(b.target) is None, b.target
                assert routing.meta_row_refusal(b) is None
    deck.loaded_patch.leave_node_mode(1, "midi")


def test_a_fader_filled_picks_up_and_a_full_desk_is_knobs_then_faders(rig, monkeypatch):
    knobs = apc40.degrees_of_freedom()
    assert knobs[0] == (f"cc:0:{K1}",) and knobs[8] == (f"cc:*:{D1}",) and len(knobs) == 24
    assert knobs[16] == (f"cc:0:{FADER}",) and knobs[23] == (f"cc:7:{FADER}",)
    assert not {f[0] for f in knobs} & set(apc40.META_CONTROLS)
    node, _ = pick_node(rig.one, 2)
    monkeypatch.setattr(apc40, "degrees_of_freedom", lambda: [(f"cc:3:{FADER}",)])
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    rig.push()
    b = rig.nd1.rows()[0]
    assert b.source == f"cc:3:{FADER}" and b.feedback is None
    p = rig.one.reg[b.target]
    p.set_norm(0.5)
    before = p.norm
    rig.push(cc(FADER, 0, channel=3))       # parked away: nothing yet
    assert p.norm == before
    rig.push(cc(FADER, 127, channel=3))     # a crossing catches it
    assert b.caught


# ---------------------------------------------------------------- row 609: FINE


def test_fine_and_node_mode_on_the_same_knob(rig):
    """Row 609: SEND B stays FINE. A knob node mode fills creeps while held, and takes up
    from where it is when let go: the ring goes out again, so no jump."""
    node, params = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    rig.one.table.slew = 0.0
    rig.push()
    p, row = rig.one.reg[params[0]], rig.nd1.rows()[0]
    p.set_norm(0.5)
    rig.push()
    at = p.norm
    fine = note(apc40.N_SEND_B)
    rig.push(fine)
    assert rig.one.reg[routing.FINE_PARAM].value
    was = round(at * 127)
    rig.push(cc(K1, was + 10))
    moved = p.norm - at
    assert 0 < moved < 10 / 127 / 2         # a tenth as far
    mark = len(rig.r.out.sent)
    rig.push(note(apc40.N_SEND_B, 0))
    rig.push()
    ring = [m.value for m in rig.r.out.sent[mark:]
            if m.type == "control_change" and m.control == K1]
    assert ring == [round(p.norm * 127)]    # re-based onto the param
    assert row.caught
    rest = p.norm
    rig.push(cc(K1, ring[0] + 1))           # the next detent is a detent
    assert abs(p.norm - rest) < 3 / 127


# ---------------------------------------------------------------- the desk's lights


def test_leaving_restores_the_rings_of_the_layers(rig):
    node, params = pick_node(rig.one)
    make_small(rig.one, params[0])
    t = rig.one.table
    saved = next(b for b in t.desk() if b.source == f"cc:0:{K1}")
    rig.one.reg[params[0]].set_norm(1.0)
    rig.one.reg[saved.target].set_norm(0.0)
    rig.push()
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    mark = len(rig.r.out.sent)
    rig.push()
    rings = [m.value for m in rig.r.out.sent[mark:]
             if m.type == "control_change" and m.control == K1]
    assert rings[-1] == 127
    mark = len(rig.r.out.sent)
    rig.one.loaded_patch.leave_node_mode(1, "midi")
    rig.push()
    rings = [m.value for m in rig.r.out.sent[mark:]
             if m.type == "control_change" and m.control == K1]
    assert rings[-1] == 0


def test_a_saved_fader_under_node_mode_does_not_jump_when_it_comes_back(rig):
    node, params = pick_node(rig.one)
    t = rig.one.table
    make_small(rig.one, params[0])
    free = next(p for p in rig.one.reg if p.modulatable and p.id not in params
                and routing.meta_refusal(p.id) is None and p.kind.name == "CONTINUOUS")
    saved = Binding(f"cc:0:{FADER}", free.id, "abs", feedback=None, ring=0, layer="preset")
    t.bind(saved, write=False)
    rig.push()
    free.set_norm(0.25)
    rig.push(cc(FADER, 32))                 # caught at about a quarter
    assert saved.caught or saved.last_hw is not None
    apc40_rows = apc40.degrees_of_freedom
    try:
        apc40.degrees_of_freedom = lambda: [(f"cc:0:{FADER}",)]
        rig.one.loaded_patch.point_node_mode(1, "midi", node)
        rig.push()
        rig.push(cc(FADER, 127))            # moved for node mode: the saved param stays
        assert free.norm == pytest.approx(0.25, abs=0.02)
        rig.one.loaded_patch.leave_node_mode(1, "midi")
        rig.push()
        assert not saved.caught             # it picks up: the fader is at the top
        rig.push(cc(FADER, 126))
        assert free.norm == pytest.approx(0.25, abs=0.02)
    finally:
        apc40.degrees_of_freedom = apc40_rows


def test_an_armed_learn_lands_on_a_filled_knob_and_says_it_is_under(rig):
    node, params = pick_node(rig.one)
    t = rig.one.table
    patch = rig.one.loaded_patch
    patch.point_node_mode(1, "midi", node)
    rig.push()
    other = next(p.id for p in rig.one.reg if p.modulatable and p.id not in params
                 and routing.meta_refusal(p.id) is None and p.kind.name == "CONTINUOUS")
    rig.one.learn.arm(other)
    rig.push(cc(K2, 64))
    assert any(b.target == other and b.source == f"cc:0:{K2}" for b in t.desk())
    assert "under node mode" in rig.one.learn.last
    patch.leave_node_mode(1, "midi")
    assert [b.target for b in t.dispatch("cc", 0, K2, DESK)] == [other]


def test_a_learned_device_knob_takes_the_freedom_whatever_its_channel_says(rig):
    node, params = pick_node(rig.one)
    t = rig.one.table
    t.bind(Binding(f"cc:0:{D1}", params[0], "abs", layer="preset"), write=False)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert f"cc:*:{D1}" not in {b.source for b in rig.nd1.rows()}


def test_a_pairs_consent_does_not_ask_about_a_derived_row(rig):
    node, _ = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    t = rig.one.table
    assert rig.nd1.rows()
    new = Binding("pair:UP/DOWN", rig.nd1.rows()[0].target, "push", 1.0)
    assert not [x for x in learn.pole_rows(t, new) if any(x is r for r in rig.nd1.rows())]
    landed = []
    assert learn.propose_row(t, Binding("cc:0:48", "x", "abs", layer="preset"),
                             lambda: landed.append(1)) is None and landed == [1]


def test_a_learn_is_not_invariant_on_a_filled_knob(rig):
    node, _ = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert not rig.one.table.is_invariant(Binding(f"cc:0:{K1}", ""))
    assert learn.blocked(rig.one.table, f"cc:0:{K1}") is None


# ---------------------------------------------------------------- per player, per `Deck`


def test_a_patch_on_the_other_deck_reaches_no_knob_and_no_param(rig):
    """Deck 2 points player 1 while the desk is on deck 1: its rows wait, nothing moves
    there, and deck 1's desk is its own."""
    node, params = pick_node(rig.two)
    assert rig.two.loaded_patch.point_node_mode(1, "midi", node) is None
    assert rig.nd2.rows() and not rig.nd2.on_here(DESK)
    assert rig.nd1.rows() == []
    saved = next(b for b in rig.one.table.desk() if b.source == f"cc:0:{K1}")
    p = rig.two.reg[params[0]]
    was = p.norm
    assert [b.target for b in rig.one.table.dispatch("cc", 0, K1, DESK)] == [saved.target]
    rig.push(cc(K1, 127), cc(K1, 126))
    assert p.norm == was


def test_enter_is_an_edit_of_the_patch_looked_at_and_brings_the_desk(rig):
    node, params = pick_node(rig.two)
    assert rig.meta.pointer(DESK).deck is rig.one
    assert rig.nd2.enter(DESK, node) is None
    assert rig.meta.pointer(DESK).deck is rig.two
    assert rig.two.loaded_patch.node_mode.of(1, "midi") == node
    assert not rig.one.loaded_patch.node_mode
    assert rig.meta.players.get(1).duty == Duty.ON_AIR      # the duty stays
    rig.push()
    mine, theirs = rig.two.reg[params[0]], rig.one.reg[params[0]]
    theirs_was = theirs.norm
    rig.push(cc(K1, 127))
    for _ in range(40):
        rig.r.t += 0.05
        rig.push()
    assert mine.norm == pytest.approx(1.0, abs=0.02)
    assert theirs.norm == theirs_was
    rig.meta.move_player(1, Duty.ON_AIR)                    # moving the player brings it back
    assert rig.meta.pointer(DESK).deck is rig.one


def test_entering_where_it_is_already_saved_brings_the_desk_and_edits_nothing(rig):
    """The operator's attach: the patch already says this node, its player is elsewhere."""
    node, _ = pick_node(rig.two)
    patch = rig.two.loaded_patch
    patch.point_node_mode(1, "midi", node)
    steps = len(rig.two.undo.stack)
    assert not rig.nd2.on_here(DESK)
    assert rig.nd2.enter(DESK, node) is None
    assert rig.nd2.on_here(DESK) and len(rig.two.undo.stack) == steps


def test_two_patches_point_the_desk_each_on_its_own_deck(rig):
    node, params = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    make_small(rig.two, params[-1])
    rig.two.loaded_patch.point_node_mode(1, "midi", node)
    assert rig.nd1.rows()[0].target == params[0]
    assert rig.nd2.rows()[0].target == params[-1]
    assert rig.nd1.rows()[0] is not rig.nd2.rows()[0]


def test_a_load_moves_no_pointer(rig, tmp_path):
    node, _ = pick_node(rig.one)
    patch = rig.two.loaded_patch
    patch.point_node_mode(1, "midi", node)
    path = Path(patch.save_as("pointing"))
    patch.leave_node_mode(1, "midi")
    assert rig.meta.pointer(DESK).deck is rig.one
    patch.load(path.stem)
    assert patch.node_mode.of(1, "midi") == node
    assert rig.meta.pointer(DESK).deck is rig.one
    assert rig.nd2.rows() and rig.nd1.rows() == []


def test_a_held_desk_is_player_twos_on_its_own_address(rig):
    """A second desk, given to player 2: its rows carry its address, and player 1's entry
    does not reach it."""
    t = rig.one.table
    io2 = MidiIO(rig.one.reg, t, inp=FakeIn(), out=FakeOut(), learner=rig.one.learn, role="launch")
    second = devices.MidiDevice("launch", {"profile": "apc40"},
                                devices.Context(reg=rig.one.reg, table=t), io=io2)
    rig.devs.devices.append(second)
    t.midi_roles = (DESK, "launch")
    rig.meta.players.hold("launch", 2)
    second.point(rig.meta.pointer("launch"), rig.meta.panel_pointer)
    node, params = pick_node(rig.one)
    assert rig.nd1.enter("launch", node) is None
    assert rig.one.loaded_patch.node_mode.of(2, "midi") == node
    assert rig.nd1.rows(DESK) == []
    rows = rig.nd1.rows("launch")
    assert rows[0].source == f"cc@launch:0:{K1}"
    assert [b.target for b in t.dispatch("cc", 0, K1, "launch")] == [params[0]]


def test_a_players_second_desk_is_refused_in_words(rig):
    t = rig.one.table
    io2 = MidiIO(rig.one.reg, t, inp=FakeIn(), out=FakeOut(), learner=rig.one.learn, role="launch")
    rig.devs.devices.append(devices.MidiDevice("launch", {"profile": "apc40"},
                            devices.Context(reg=rig.one.reg, table=t), io=io2))
    t.midi_roles = (DESK, "launch")
    node, _ = pick_node(rig.one)
    assert rig.nd1.refusal("launch", node) == node_desk.NOT_FIRST.format(role="launch", player=1)


def test_a_desk_of_no_known_shape_and_a_node_with_nothing_are_refused(rig):
    node, _ = pick_node(rig.one)
    rig.desk.entry = {"profile": "generic"}
    assert rig.nd1.refusal(DESK, node) == node_desk.NO_SHAPE.format(role=DESK)
    rig.desk.entry = {"profile": "apc40"}
    assert rig.nd1.refusal(DESK, None) == nodemode.NO_NODE
    assert rig.nd1.enter(DESK, None) == nodemode.NO_NODE
    assert rig.meta.pointer(DESK).deck is rig.one


def test_a_copy_on_air_carries_the_pointing_and_its_rows_wait(rig):
    node, _ = pick_node(rig.one)
    rig.nd1.enter(DESK, node)
    rig.meta.copy_on_air()
    assert rig.two.loaded_patch.node_mode.of(1, "midi") == node
    assert rig.meta.pointer(DESK).deck is rig.one
    assert not rig.nd2.on_here(DESK) and rig.nd2.rows()


def test_re_pointing_is_one_undo_step_and_the_rows_follow(rig):
    node, _ = pick_node(rig.one)
    other = next(n for n in sorted(rig.one.loaded_patch._pointable())
                 if n != node and rig.nd1.refusal(DESK, n) is None)
    undo.install(rig.one.undo)
    rig.r.t += 10
    rig.one.undo.tick(rig.r.t)
    rig.nd1.enter(DESK, node)
    first = [b.target for b in rig.nd1.rows()]
    rig.r.t += 10
    rig.one.undo.tick(rig.r.t)
    rig.nd1.enter(DESK, other)
    second = [b.target for b in rig.nd1.rows()]
    assert first != second
    rig.r.t += 10
    rig.one.undo.tick(rig.r.t)
    sig = rig.one.loaded_patch.node_mode
    assert rig.one.undo.undo()
    assert sig != rig.one.loaded_patch.node_mode
    assert [b.target for b in rig.nd1.rows()] == first


def test_the_seq_page_and_node_mode_stand_together(rig):
    node, _ = pick_node(rig.one)
    t = rig.one.table
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    page = SimpleNamespace(rows=lambda: [Binding("note:0:53", "seq.1.1", "toggle")])
    t.set_page(page)
    try:
        controls = {b.control for b in t.active(DESK)}
        assert ("note", 0, 53) in controls and ("cc", 0, K1) in controls
        assert t.dispatch("cc", 0, K1, DESK)[0] is rig.nd1.rows()[0]
    finally:
        t.set_page(None)


# ---------------------------------------------------------------- review of #396


def _generic_above(rig):
    t = rig.one.table
    io = MidiIO(rig.one.reg, t, inp=FakeIn(), out=FakeOut(), learner=rig.one.learn,
                role="box", profile="generic")
    box = devices.MidiDevice("box", {"profile": "generic"},
                             devices.Context(reg=rig.one.reg, table=t), io=io)
    rig.devs.devices.insert(0, box)
    t.midi_roles = rig.devs.midi_roles()
    return box


def test_a_generic_box_listed_above_the_apc40_is_not_its_players_first_desk(rig):
    _generic_above(rig)
    node, _ = pick_node(rig.one)
    assert rig.nd1.is_first(DESK) and not rig.nd1.is_first("box")
    assert rig.nd1.refusal(DESK, node) is None
    assert rig.nd1.enter(DESK, node) is None
    assert rig.nd1.rows(DESK) and rig.nd1.rows("box") == []


def test_an_entry_switched_off_was_never_a_first_desk(rig):
    """Half of a review finding, disproved: an off entry is an `OffDevice`, no `MidiDevice`."""
    t = rig.one.table
    off = devices.OffDevice("old", "midi", {"role": "old", "kind": "midi", "enabled": False})
    rig.devs.devices.insert(0, off)
    t.midi_roles = rig.devs.midi_roles()
    assert rig.nd1.is_first(DESK)


def test_a_first_desks_row_spelling_its_own_role_takes_its_freedom(rig):
    node, params = pick_node(rig.one)
    t = rig.one.table
    mine = Binding(f"cc@{DESK}:0:{K1}", params[0], "abs", layer="preset")
    t.bind(mine, write=False)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert f"cc:0:{K1}" not in {b.source for b in rig.nd1.rows()}
    assert rig.nd1._follow(DESK).fit.kept == (params[0],)
    assert rig.nd1.rows()[0].target == params[1]


def test_an_invariant_row_spelling_its_own_role_keeps_its_control(rig):
    node, params = pick_node(rig.one)
    t = rig.one.table
    t.bind(Binding(f"cc@{DESK}:0:{K1}", "view.speed", "abs"), write=False)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert f"cc:0:{K1}" not in {b.source for b in rig.nd1.rows()}
    assert rig.nd1.rows()[0].target == params[0]


def test_under_reads_a_row_spelling_its_own_role(rig):
    node, params = pick_node(rig.one)
    t = rig.one.table
    t.remove(next(b for b in t.desk() if b.source == f"cc:0:{K1}"))
    other = next(p.id for p in rig.one.reg if p.modulatable and p.id not in params
                 and routing.meta_refusal(p.id) is None and p.kind.name == "CONTINUOUS")
    saved = Binding(f"cc@{DESK}:0:{K1}", other, "abs", layer="preset")
    t.bind(saved, write=False)
    assert not rig.nd1.under(saved)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert rig.nd1.rows()[0].source == f"cc:0:{K1}"
    assert rig.nd1.under(saved)


def test_an_adapter_from_before_a_hot_reload_holds_a_shorter_tuple(rig):
    rig.midi._seen = rig.midi._seen[:4]
    rig.push()                              # (a slice, not an index)
    assert len(rig.midi._seen) == 5


def test_the_desks_map_moves_when_the_rows_do(rig):
    pytest.importorskip("imgui_bundle")
    from hyperspace import ui, ui_desk  # noqa: F401 — (`ui` first: ui_desk imported cold trips)
    t = rig.one.table
    node, params = pick_node(rig.one)
    before = ui_desk._key(t)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert ui_desk._key(t) != before
    assert ui_desk.lit(t)["K1"].target == params[0]


def test_install_is_once_in_main_and_no_device_listener_replaces_it(rig):
    """A review finding, disproved: `node_desk.install` is in `main`'s own body, not in the
    `point_at_devices` listener, so a pad reconnecting keeps each deck's rows and catches."""
    tree = ast.parse(inspect.getsource(app.main))
    main = tree.body[0]

    def calls(n):
        return [x for x in ast.walk(n) if isinstance(x, ast.Call)
                and ast.unparse(x.func) == "node_desk.install"]
    nested = [f for f in ast.walk(main) if isinstance(f, ast.FunctionDef | ast.Lambda)
              and f is not main]
    assert len(calls(main)) == 1 and not any(calls(f) for f in nested)
    node, _ = pick_node(rig.one)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    row, keeper = rig.nd1.rows()[0], rig.one.table.node_desk
    rig.devs.entries = [{"role": DESK, "kind": "midi", "profile": "apc40", "enabled": True}]
    rig.devs.apply([dict(e) for e in rig.devs.entries])         # nothing changed: it stays
    for told in rig.devs.listeners:
        told()
    assert rig.one.table.node_desk is keeper and rig.nd1.rows()[0] is row


def test_enter_goes_through_the_meta_controllers_door(rig):
    node, _ = pick_node(rig.one)
    went = []
    real = rig.meta.point
    rig.meta.point = lambda role, deck: (went.append((role, deck)), real(role, deck))
    assert rig.nd2.refusal(DESK, node) is None
    assert rig.nd2.enter(DESK, node) is None
    assert went == [(DESK, rig.two)]
    rig.meta.point = real
    with pytest.raises(ValueError):                 # …which checks the deck is one of its two
        rig.meta.point(DESK, object())


def test_a_new_built_in_lane_counts_as_a_modulator_by_import():
    from hyperspace.routing_sources import BUILTIN_LANES, DECK_SCHEMES
    assert node_desk.MODULATORS == set(BUILTIN_LANES) | DECK_SCHEMES
    assert node_desk.freedoms_of(generic) == []


def test_a_row_takes_the_profiles_whole_feedback_as_a_learn_does(rig):
    b = Binding("note:0:53", "x", "toggle")
    b.feedback_from(apc40)
    assert (b.feedback, b.on, b.off) == ("led", apc40.GREEN, 0)
    k = Binding(f"cc:0:{K1}", "x", "abs")
    k.feedback_from(apc40)
    assert (k.feedback, k.ring) == ("ring", apc40.RING_VOLUME)
    was = Binding(f"cc:0:{K1}", "x", "abs")
    was.feedback_from(None)
    assert was.feedback is None


def _dispatch_agrees(rig, b, faders=range(8)) -> bool:
    """Does `dispatch` send every channel of fader row `b` to something other than `b`?"""
    t = rig.one.table
    return all(not any(x is b for x in t.dispatch("cc", ch, FADER, DESK)) for ch in faders)


def test_under_asks_what_dispatch_does_on_an_any_channel_row(rig, monkeypatch):
    node, params = pick_node(rig.one, 8)
    t = rig.one.table
    other = next(p.id for p in rig.one.reg if p.modulatable and p.id not in params
                 and routing.meta_refusal(p.id) is None and p.kind.name == "CONTINUOUS")
    saved = Binding(f"cc:*:{FADER}", other, "abs", ring=0, layer="preset")
    t.bind(saved, write=False)
    monkeypatch.setattr(apc40, "degrees_of_freedom", lambda: [(f"cc:0:{FADER}",)])
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert any(x is saved for x in t.dispatch("cc", 1, FADER, DESK))    # S2 still fires it
    assert not rig.nd1.under(saved) and not _dispatch_agrees(rig, saved)
    every = [(f"cc:{k}:{FADER}",) for k in range(8)]
    monkeypatch.setattr(apc40, "degrees_of_freedom", lambda: every)
    t.rows_serial += 1
    assert rig.nd1.under(saved) and _dispatch_agrees(rig, saved)


# ---------------------------------------------------------------- second review of #396:
# what the fill counts as taken is what `dispatch` does


def _fader_row(params, invariant=False):
    return Binding(f"cc:*:{FADER}", params[0], "abs", ring=0,
                   layer=None if invariant else "preset")


AWKWARD = {
    "disabled invariant": lambda ps: [Binding(f"cc:0:{K1}", "view.speed", "abs", enabled=False)],
    "invariant": lambda ps: [Binding(f"cc:0:{K2}", "view.speed", "abs")],
    "any-channel invariant": lambda ps: [Binding(f"cc:*:{FADER}", "view.speed", "abs", ring=0)],
    "any-channel mapping": lambda ps: [_fader_row(ps)],
    "qualified mapping": lambda ps: [Binding(f"cc@{DESK}:0:{K1}", ps[0], "abs", layer="preset")],
    "qualified invariant": lambda ps: [Binding(f"cc@{DESK}:0:{K3}", "view.speed", "abs")],
    "qualified any-channel": lambda ps: [Binding(f"cc@{DESK}:*:{FADER}", "view.speed", "abs")],
    "one channel of a device knob": lambda ps: [Binding(f"cc:3:{D1}", "view.speed", "abs")],
    "disabled mapping": lambda ps: [Binding(f"cc:0:{K1}", ps[0], "abs", layer="preset",
                                            enabled=False)],
    "global row on the node": lambda ps: [Binding(f"cc:0:{K1}", ps[0], "abs", layer="global")],
    "a pad's row on the node": lambda ps: [Binding("axis:LX", ps[0], "push", 0.5)],
    "an other desk's row": lambda ps: [Binding(f"cc@launch:0:{K1}", ps[0], "abs", layer="preset")],
}


def _channels(source):
    b = Binding(source, "")
    return range(16) if b.channel is None else (b.channel,)


def _reaches_what_it_says(rig, params, added):
    """By `dispatch`: every filled control reaches its param and nothing else, on every
    channel it can arrive on; every param is filled, kept or listed; a row kept stays."""
    t = rig.one.table
    now = rig.nd1._follow(DESK)
    for b in now.rows:
        for ch in _channels(b.bare):
            assert [x.target for x in t.dispatch(b.kind, ch, b.number, DESK)] == [b.target], b
    assert sorted((*[s.param for s in now.fit.slots], *now.fit.kept, *now.fit.over)) == sorted(params)
    assert len({b.control for b in now.rows}) == len(now.rows)
    for b in added:
        if b.enabled and b.is_midi and t.serves(DESK, b) and b.layer in (None, "preset"):
            for ch in _channels(b.bare):
                assert any(x is b for x in t.dispatch(b.kind, ch, b.number, DESK)), (b, ch)
            assert not rig.nd1.under(b)


@pytest.mark.parametrize("which", sorted(AWKWARD))
def test_every_filled_control_reaches_its_param_over_an_awkward_table(rig, which):
    node, params = pick_node(rig.one, 4)
    t = rig.one.table
    added = AWKWARD[which](params)
    t.bindings.extend(added)
    t.rows_serial += 1
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert rig.nd1.rows()
    _reaches_what_it_says(rig, params, added)


def test_a_reserved_control_is_no_freedom_whatever_the_profile_lists(rig, monkeypatch):
    node, params = pick_node(rig.one, 2)
    every = [(apc40.META_CONTROLS[0],), *apc40.degrees_of_freedom()]
    monkeypatch.setattr(apc40, "degrees_of_freedom", lambda: every)
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert apc40.META_CONTROLS[0] not in {b.source for b in rig.nd1.rows()}
    _reaches_what_it_says(rig, params, [])


def test_a_disabled_invariant_row_gives_its_knob_to_the_fill(rig):
    """A review finding, disproved for a knob: only SHIFT and a reserved control stay no
    layer's with their row off. `dispatch` reads no disabled row on any other control."""
    node, params = pick_node(rig.one)
    t = rig.one.table
    off = Binding(f"cc:0:{K1}", "view.speed", "abs", enabled=False)
    t.bindings.append(off)
    t.rows_serial += 1
    assert t.above_layers("cc", 0, K1, DESK) is None
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert rig.nd1.rows()[0].source == f"cc:0:{K1}" and rig.nd1.rows()[0].target == params[0]
    assert t.dispatch("cc", 0, K1, DESK) == [rig.nd1.rows()[0]]


def test_an_any_channel_row_keeps_all_eight_faders(rig):
    node, params = pick_node(rig.one, 4)
    t = rig.one.table
    inv = Binding(f"cc:*:{FADER}", "view.speed", "abs", ring=0)
    t.bindings.append(inv)
    t.rows_serial += 1
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert not {b.source for b in rig.nd1.rows()} & {f"cc:{k}:{FADER}" for k in range(8)}
    t.bindings.remove(inv)
    mapping = _fader_row(params)
    t.bindings.append(mapping)
    t.rows_serial += 1
    assert not {b.source for b in rig.nd1.rows()} & {f"cc:{k}:{FADER}" for k in range(8)}
    assert rig.nd1._follow(DESK).fit.kept == (params[0],)
    for k in range(8):
        assert t.dispatch("cc", k, FADER, DESK) == [mapping]


def test_above_layers_is_what_dispatch_answers_first(rig):
    t = rig.one.table
    inv = Binding(f"cc:0:{K1}", "view.speed", "abs")
    t.bindings.append(inv)
    t.rows_serial += 1
    assert t.above_layers("cc", 0, K1, DESK) == [inv] == t.dispatch("cc", 0, K1, DESK)
    number = int(apc40.META_CONTROLS[0].rpartition(":")[2])
    t.bindings[:] = [b for b in t.bindings if not (b.kind == "cc" and b.number == number)]
    t.rows_serial += 1
    assert t.above_layers("cc", 0, number, DESK) == [] == t.dispatch("cc", 0, number, DESK)
    assert t.above_layers("cc", 0, K2, DESK) is None


def test_a_narrower_list_gives_above_layers_the_same_answer(rig):
    t = rig.one.table
    t.bindings.append(Binding(f"cc:*:{FADER}", "view.speed", "abs", ring=0))
    t.rows_serial += 1
    pool = [b for b in t.bindings if b.is_midi and b.layer is None]
    for number in (K1, D1, FADER, int(apc40.META_CONTROLS[0].rpartition(":")[2])):
        for ch in range(16):
            assert (t.above_layers("cc", ch, number, DESK, pool)
                    == t.above_layers("cc", ch, number, DESK))


# ---------------------------------------------------------------- the owner, 2026-11-06, row 711:
# "LFOs and audio routes be allowed to be overwritten for node mode, as long as they come back
# when you disengage node mode"


def _modulated(rig, deck=None):
    """A node, the param its K1 fills, and an analyzer route on that param, on `deck`."""
    deck = deck or rig.one
    node, params = pick_node(deck)
    pid = next(p for p in params[:24] if deck.reg[p].modulatable)
    deck.loaded_patch.node_params = lambda _n: [pid, *[p for p in params if p != pid]]
    route = Binding("lane:0", pid, "push", 0.5)
    deck.table.set_routes([*deck.table.routes(), route])
    deck.reg[pid].set_norm(0.25)
    return node, pid, route


def _pass(deck) -> float:
    """One pass with the analyzer's first lane full up: the param's value after it."""
    lanes = np.zeros(32)
    lanes[:] = CEIL
    deck.router.modulate(SimpleNamespace(lanes=lanes), 1 / 60, 100.0)
    deck.reg.apply()


def _rides(deck, pid) -> bool:
    """Does the route move the param, over a few frames (a follower may ease in)?"""
    for _ in range(6):
        _pass(deck)
    return deck.reg[pid].value != pytest.approx(deck.reg[pid].base)


def test_a_filled_param_rests_its_modulators_and_they_come_back_on_leave(rig):
    node, pid, route = _modulated(rig)
    deck = rig.one
    assert _rides(deck, pid)
    assert rig.nd1.enter(DESK, node) is None
    assert deck.table.node_holds(route)
    assert not _rides(deck, pid)                # the knob is the param
    assert any(b is route for b in deck.table.routes())     # the row is where it was
    rig.nd1.leave(DESK)
    assert not deck.table.node_holds(route)
    assert _rides(deck, pid)


def test_undo_and_re_pointing_bring_them_back(rig):
    node, pid, _route = _modulated(rig)
    deck = rig.one
    other = next(n for n in sorted(deck.loaded_patch._pointable()) if n != node
                 and n != "render:camera")
    undo.install(deck.undo)
    rig.r.t += 10
    deck.undo.tick(rig.r.t)
    rig.nd1.enter(DESK, node)
    assert not _rides(deck, pid)
    rig.r.t += 10
    deck.undo.tick(rig.r.t)
    assert deck.undo.undo()
    assert not deck.loaded_patch.node_mode
    assert _rides(deck, pid)
    rig.nd1.enter(DESK, node)
    assert not _rides(deck, pid)
    params = deck.loaded_patch.node_params
    deck.loaded_patch.node_params = lambda n: params(n) if n == node else []
    deck.loaded_patch.point_node_mode(1, "midi", other)     # another node holds other params
    assert _rides(deck, pid)


def test_a_load_rests_them_again_and_another_load_lets_go(rig):
    node, pid, _route = _modulated(rig)
    deck, patch = rig.one, rig.one.loaded_patch
    patch.point_node_mode(1, "midi", node)
    path = Path(patch.save_as("held"))
    patch.leave_node_mode(1, "midi")
    plain = Path(patch.save_as("plain"))
    assert not _rides_after_load(deck, patch, path.stem, pid)
    assert _rides_after_load(deck, patch, plain.stem, pid)


def _rides_after_load(deck, patch, stem, pid) -> bool:
    patch.load(stem)
    deck.reg[pid].set_norm(0.25)
    return _rides(deck, pid)


def test_the_saved_file_is_byte_identical_and_only_the_key_differs(rig):
    node, _pid, route = _modulated(rig)
    patch = rig.one.loaded_patch
    before = Path(patch.save_as("a")).read_bytes()
    want = route.to_json()
    patch.point_node_mode(1, "midi", node)
    _rides(rig.one, _pid)
    pointed = json.loads(Path(patch.save_as("b")).read_text())
    assert want in pointed["routes"]
    patch.leave_node_mode(1, "midi")
    _rides(rig.one, _pid)
    after = Path(patch.save_as("a")).read_bytes()
    assert after == before
    was = json.loads(before)
    del pointed[nodemode.KEY]
    pointed["name"] = was["name"]
    assert {k: v for k, v in pointed.items() if k != "values"} == {
        k: v for k, v in was.items() if k != "values"}


def test_a_pads_route_stays_and_its_param_never_rests(rig):
    node, params = pick_node(rig.one)
    pid = params[0]
    pad = Binding("axis:LX", pid, "push", 0.5)
    rig.one.table.set_routes([*rig.one.table.routes(), pad])
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert pid in rig.nd1._follow(DESK).fit.kept and not rig.one.table.node_holds(pad)


def test_a_param_past_the_desk_keeps_its_modulators(rig, monkeypatch):
    node, params = pick_node(rig.one, 3)
    monkeypatch.setattr(apc40, "degrees_of_freedom", lambda: [(f"cc:0:{K1}",)])
    route = Binding("lane:0", params[1], "push", 0.5)
    rig.one.table.set_routes([*rig.one.table.routes(), route])
    rig.one.loaded_patch.point_node_mode(1, "midi", node)
    assert params[1] in rig.nd1._follow(DESK).fit.over
    assert not rig.one.table.node_holds(route)


def test_a_desk_that_does_not_act_here_holds_nothing(rig):
    node, _pid, route = _modulated(rig, rig.two)
    patch = rig.two.loaded_patch
    patch.point_node_mode(1, "midi", node)
    assert not rig.nd2.on_here(DESK) and not rig.two.table.node_holds(route)   # the other Deck
    assert rig.nd2.enter(DESK, node) is None
    assert rig.two.table.node_holds(route)
    assert rig.one.table.node_held() == frozenset()         # no patch reaches another
    real, rig.desk.io.ports.inp, rig.desk.io.ports.out = (rig.desk.io.ports.inp, rig.desk.io.ports.out), None, None
    assert not rig.two.table.node_holds(route)              # the cable's out: they come back
    rig.desk.io.ports.inp, rig.desk.io.ports.out = real
    assert rig.two.table.node_holds(route)


def test_shift_does_not_let_a_held_param_go(rig):
    node, _pid, route = _modulated(rig)
    rig.nd1.enter(DESK, node)
    rig.push(note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))
    assert rig.one.table.layer_of(DESK) == "global"
    assert rig.one.table.node_holds(route)


def test_nothing_changes_for_a_table_with_nothing_pointed(rig):
    t = rig.one.table
    assert t.node_held() == frozenset()
    before = rig.one.router._modgraph_key()
    assert rig.one.router._modgraph_key() == before


# ---------------------------------------------------------------- Dillon's desk (2026-11-06):
# he "cares mostly about the clip launch buttons" and "the meta controls on the APC"


def test_node_mode_never_takes_a_clip_pad_master_the_crossfader_or_a_meta_control(rig):
    t, deck = rig.one.table, rig.one

    def desk():
        out = {}
        for c in apc40.LAYOUT:
            b = Binding(c.source, "")
            if c.source in {f[0] for f in apc40.degrees_of_freedom()}:
                continue
            out[c.source] = [id(x) for x in t.dispatch(b.kind, b.channel or 0, b.number, DESK)]
        return out
    was = desk()
    freedoms = {f[0] for f in apc40.degrees_of_freedom()}
    assert all(s.startswith("cc:") for s in freedoms)               # no pad, no button
    assert not freedoms & set(apc40.META_CONTROLS)
    assert not any(f"cc:{apc40.CC_CUE}" in s or s.endswith(f":{apc40.CC_CUE}") for s in freedoms)
    pointed = 0
    for node in sorted(deck.loaded_patch._pointable()):
        if rig.nd1.refusal(DESK, node) is None:
            deck.loaded_patch.point_node_mode(1, "midi", node)
            pointed += 1
            assert desk() == was, node
            assert all(b.kind == "cc" for b in rig.nd1.rows())
            shadowed = {b.control for b in rig.nd1.rows()}
            for b in t.invariant_rows():
                assert b.control not in shadowed, b
    assert pointed > 5
    # …and the SHIFT layer's own controls, node mode or not
    rig.push(note(apc40.N_SHIFT), note(apc40.N_SHIFT, 0))
    assert not any(any(x is b for x in rig.nd1.rows()) for b in t.active(DESK))
