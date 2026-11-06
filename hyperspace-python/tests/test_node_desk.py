"""Plan 53 N1a: node mode on a desk, over two `Deck`s and fake ports.

The rows come from what the patch saved (`nodemode`), for the player's first desk, on the
deck that desk is on. They are never in the table's rows, never in the file, and no patch
reaches another through them.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import mido
import pytest
from test_meta_controller import DESK, _pointed
from test_midi import FakeIn, FakeOut
from test_undo import boot

from hyperspace import apc40, devices, learn, node_desk, nodemode, routing, undo
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


def test_a_route_from_a_modulator_is_no_mapping_but_a_pads_is(rig):
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
