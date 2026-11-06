"""The undo latch, register row 753; the owner, 2026-11-06: "before you can start popping
from that stack, you should have to push to that stack at least once after a focus event".

Every rig is `test_undo_stacks`'s: `boot`, deck 2 and the real `MetaController`. `press` is
⌘Z through the `edit.undo` trigger, the road the key row takes.
"""

import pytest
import test_undo_stacks
from test_undo_stacks import bases, go, here_is_meta

from hyperspace import undo

BRIGHT = "view.bright"
META = "hands.smooth"
rig = test_undo_stacks.rig  # the fixture


def press(rig) -> None:
    rig.reg["edit.undo"].fire()


def change(reg, pid: str = BRIGHT, n: int = 3) -> None:
    reg[pid].step(n)


def refused_on(u, verb: str, where: str) -> None:
    assert u.latched
    assert u.status == f"nothing to {verb} here yet: make a change {where} first"


def test_coming_to_a_deck_latches_it_and_a_push_opens_it_all_the_way_down(rig):
    """The owner's whole story: a step from ten minutes ago, the panel comes to the deck,
    ⌘Z refuses and leaves the history; a minor action, then double undo, reaches it."""
    p = rig.two.reg[BRIGHT]
    was = p.base
    rig.meta.point_panel(rig.two)
    change(rig.two.reg)
    go(rig)
    rig.meta.point_panel(rig.one)
    rig.meta.point_panel(rig.two)  # the old step; away and back
    old, n = p.base, len(rig.two.undo.stack)
    press(rig)
    refused_on(rig.two.undo, "undo", "on deck 2")
    assert p.base == old and len(rig.two.undo.stack) == n == 1

    change(rig.two.reg, "view.speed", 1)  # the minor action
    go(rig)
    assert not rig.two.undo.latched
    press(rig)
    assert p.base == old
    press(rig)
    assert p.base == was and rig.two.undo.stack == []


def test_launch_is_as_any_focus_event(rig):
    """A deck just built has no history and is latched: the first change opens it and
    is taken back at once, with no sign of the latch."""
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    p = rig.one.reg[BRIGHT]
    was = p.base
    change(rig.one.reg)
    go(rig)
    press(rig)
    assert p.base == was and rig.one.undo.status.startswith("undid ")


def test_a_refusal_is_one_line_and_each_press_says_it_once(rig):
    """The words are one `_say` per press: nothing is said on a frame with no press."""
    press(rig)
    said = rig.one.undo.said_at
    go(rig)
    assert rig.one.undo.said_at == said


def test_a_redo_is_refused_on_a_latched_stack_and_a_new_push_clears_it_as_ever(rig):
    p = rig.one.reg[BRIGHT]
    change(rig.one.reg)
    go(rig)
    press(rig)
    go(rig)
    back = p.base
    assert rig.one.undo.redos
    rig.meta.point_panel(rig.two)
    rig.meta.point_panel(rig.one)
    rig.reg["edit.redo"].fire()
    refused_on(rig.one.undo, "redo", "on deck 1")
    assert p.base == back and rig.one.undo.redos, "nothing moved, and the history is kept"
    change(rig.one.reg, "view.speed", 1)
    go(rig)
    assert not rig.one.undo.redos


def test_a_redo_straight_after_an_undo_with_no_focus_change_is_as_it_was(rig):
    p = rig.one.reg[BRIGHT]
    change(rig.one.reg)
    go(rig)
    moved = p.base
    press(rig)
    rig.reg["edit.redo"].fire()
    assert p.base == moved


def test_a_change_out_of_focus_opens_nothing(rig):
    """Rule 4: what lands on deck 2 with the panel on deck 1 does not open deck 2 for
    later, and coming to it latches it whatever happened in between."""
    rig.meta.point_panel(rig.two)
    change(rig.two.reg)
    go(rig)
    assert not rig.two.undo.latched
    rig.meta.point_panel(rig.one)
    change(rig.two.reg, "view.speed", 1)  # a player's knob on deck 2
    go(rig)
    rig.meta.point_panel(rig.two)
    held = bases(rig.two)
    press(rig)
    refused_on(rig.two.undo, "undo", "on deck 2")
    assert bases(rig.two) == held


def test_a_step_still_open_when_focus_comes_opens_nothing(rig):
    """The same, inside the settle time: the panel arrives before the step has closed."""
    change(rig.two.reg)
    go(rig, 1)
    assert rig.two.undo._open is not None
    rig.meta.point_panel(rig.two)
    held = bases(rig.two)
    press(rig)
    refused_on(rig.two.undo, "undo", "on deck 2")
    assert bases(rig.two) == held


def _pad_rig(rig):
    """A filled pad 1, with deck 2 holding a look of its own, every stack quiet."""
    rig.one.presets.lib.project.bank[0] = "party-wake"
    rig.two.presets.load("party-trip")
    go(rig)


def test_a_mis_pressed_pad_then_cmd_z_takes_nothing_from_the_room(rig):
    """The panel on air, with a step of the room's a moment ago, opened and ready. A pad
    lands off air. ⌘Z takes nothing back: the room's step stays where it was."""
    _pad_rig(rig)
    p = rig.one.reg[BRIGHT]
    change(rig.one.reg)
    go(rig)
    assert not rig.one.undo.latched and undo.here() is rig.one.undo
    moved, steps = p.base, len(rig.one.undo.stack)
    loaded = len(rig.two.undo.stack)
    rig.one.reg["preset.load.0"].fire()
    go(rig)
    assert len(rig.two.undo.stack) == loaded + 1
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    assert p.base == moved and len(rig.one.undo.stack) == steps
    change(rig.one.reg, "view.speed", 1)  # as the owner: touch it, then double
    go(rig)
    press(rig)
    press(rig)
    assert p.base != moved


def test_copy_on_air_then_cmd_z_takes_nothing_from_the_room(rig):
    """The head's copy lands on the deck off air, just as a pad's load."""
    rig.two.presets.load("party-trip")
    go(rig)
    p = rig.one.reg[BRIGHT]
    change(rig.one.reg)
    go(rig)
    moved = p.base
    rig.meta.copy_on_air()
    go(rig)
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    assert p.base == moved


def test_a_pad_then_the_panel_on_that_deck_is_still_latched(rig):
    """Rule 4 in the case that made it: the load is on deck 2's stack, the panel comes
    after it, and ⌘Z refuses. Touch it, double undo, and the load goes back."""
    _pad_rig(rig)
    was = rig.two.presets.current
    rig.one.reg["preset.load.0"].fire()
    go(rig)
    assert rig.two.presets.current != was
    loaded = rig.two.presets.current
    rig.meta.point_panel(rig.two)
    press(rig)
    refused_on(rig.two.undo, "undo", "on deck 2")
    assert rig.two.presets.current == loaded
    change(rig.two.reg)
    go(rig)
    press(rig)
    press(rig)
    assert rig.two.presets.current == was


def test_the_same_inside_the_settle_time(rig):
    """The panel arriving before the pad's step has closed changes nothing."""
    _pad_rig(rig)
    rig.one.reg["preset.load.0"].fire()
    rig.meta.point_panel(rig.two)
    loaded = rig.two.presets.current
    press(rig)
    refused_on(rig.two.undo, "undo", "on deck 2")
    assert rig.two.presets.current == loaded


def test_a_pad_with_the_panel_on_that_deck_is_a_push_where_you_are(rig):
    """Rule 4 for the words "⌘Z takes it back": the push comes after the focus event."""
    _pad_rig(rig)
    rig.meta.point_panel(rig.two)
    was = rig.two.presets.current
    rig.one.reg["preset.load.0"].fire()
    assert rig.lib.status.endswith("; ⌘Z takes it back")
    press(rig)
    assert rig.two.presets.current == was


def test_meta_is_one_rule_with_the_decks(rig):
    """A press in a meta section, from the deck in focus, latches the meta stack; a change
    there opens it, down to the old step; a press back on the deck latches the deck."""
    m, q = rig.meta.undo, rig.reg[META]
    undo.by_hand(True)
    here_is_meta(rig)
    was = q.base
    change(rig.reg, META)
    go(rig)
    here_is_meta(rig, False)
    change(rig.one.reg)  # the deck takes the focus
    go(rig)
    moved, steps = q.base, len(m.stack)

    here_is_meta(rig)
    press(rig)
    refused_on(m, "undo", "on the meta controller")
    assert q.base == moved and len(m.stack) == steps

    rig.reg["master.gain"].step(1)
    go(rig)
    press(rig)
    press(rig)
    assert q.base == was

    held = bases(rig.one)
    here_is_meta(rig, False)
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    assert bases(rig.one) == held


def _meta_step(rig):
    """An old meta step, made by hand; then the person lets go."""
    undo.by_hand(True)
    here_is_meta(rig)
    change(rig.reg, META)
    go(rig)
    undo.by_hand(False)
    here_is_meta(rig, False)


def test_the_mouse_passing_over_is_no_focus_event(rig):
    """A change in a meta section, the mouse across the canvas and back, with no press and
    no change on the way: ⌘Z takes the change back."""
    q = rig.reg[META]
    was = q.base
    _meta_step(rig)
    go(rig, 3)
    here_is_meta(rig)
    press(rig)
    assert q.base == was and not rig.meta.undo.latched


def test_the_mouse_passing_over_a_section_leaves_the_deck_open(rig):
    p = rig.one.reg[BRIGHT]
    was = p.base
    change(rig.one.reg)
    go(rig)
    here_is_meta(rig)
    go(rig, 3)
    here_is_meta(rig, False)
    press(rig)
    assert p.base == was


def test_the_mouse_passing_then_a_press_is_where_the_latch_bites(rig):
    """The mouse goes by no event, but where it is at the press decides: the old meta
    step cannot be had by wandering into a section and pressing."""
    q = rig.reg[META]
    _meta_step(rig)
    moved = q.base
    press(rig)  # on the canvas: the deck, latched
    here_is_meta(rig)
    press(rig)  # and back: latched again
    refused_on(rig.meta.undo, "undo", "on the meta controller")
    assert q.base == moved


@pytest.mark.parametrize("back_in_time", [True, False])
def test_a_change_from_a_popup_is_the_persons_wherever_the_mouse_is(rig, back_in_time):
    """Finding 3. A combo's choice with `here` on the deck, the list hanging over another
    section. It opens by the step's own stack, however long the mouse takes to come back."""
    q = rig.reg[META]
    was = q.base
    undo.by_hand(True)
    change(rig.reg, META)
    go(rig, 1)
    undo.by_hand(False)
    go(rig, 2)
    if back_in_time:
        here_is_meta(rig)
    go(rig)
    here_is_meta(rig)
    press(rig)
    assert q.base == was


def test_riding_a_meta_fader_then_crossing_a_section_opens_nothing(rig):
    """Finding 1, the owner's hazard. `master.gain` on the APC, with the mouse crossing the
    analyzer inside the settle time. Focus stays on the deck, whose own step is still
    open to ⌘Z, and the meta stack's old step is out of reach."""
    q = rig.reg[META]
    _meta_step(rig)
    moved = q.base
    p = rig.one.reg[BRIGHT]
    undo.by_hand(True)
    change(rig.one.reg)  # the deck has the focus, and a step
    go(rig)
    undo.by_hand(False)
    rig.reg["master.gain"].step(2)
    go(rig, 2)
    here_is_meta(rig)  # crossing
    go(rig)
    here_is_meta(rig, False)
    assert not rig.one.undo.latched and undo._focused is rig.one.undo
    deck_moved = p.base
    press(rig)
    assert p.base != deck_moved, "the deck's own step, not latched by the crossing"
    here_is_meta(rig)
    press(rig)
    refused_on(rig.meta.undo, "undo", "on the meta controller")
    assert q.base == moved


def test_a_show_loaded_then_crossing_a_section_opens_nothing(rig):
    """Finding 1, a show: no sample of the mouse as its steps close."""
    pr = rig.lib.project
    pr.load("house")
    go(rig, 2)
    here_is_meta(rig)
    go(rig)
    assert undo._focused is rig.one.undo
    press(rig)
    refused_on(rig.meta.undo, "undo", "on the meta controller")
    assert pr.name == "house"


def test_a_controllers_change_opens_the_stack_in_focus_and_moves_no_focus(rig):
    """Finding 2, (rec). A real change on the focused deck opens it: the owner's "some minor
    action on that deck" is often on the APC. On another stack it opens nothing there,
    moves no focus and leaves what the focused stack can do, whatever `here` says."""
    p = rig.one.reg[BRIGHT]
    press(rig)
    assert rig.one.undo.latched
    was = p.base
    change(rig.one.reg)  # a knob, no hand on the panel
    go(rig)
    assert not rig.one.undo.latched
    rig.reg["master.gain"].step(1)  # another layer's fader, the mouse in its section
    here_is_meta(rig)
    go(rig)
    assert undo._focused is rig.one.undo and rig.meta.undo.stack
    here_is_meta(rig, False)
    press(rig)
    assert p.base == was


def test_within_the_tolerance_is_no_change_and_opens_nothing(rig):
    """Finding 2: a performer's last-bits round-off, under `REL_TOL`, makes no step."""
    press(rig)
    p = rig.one.reg[BRIGHT]
    p.set(p.base * (1.0 + undo.REL_TOL / 10))
    go(rig)
    assert rig.one.undo.latched and rig.one.undo.stack == []


def test_a_held_step_opens_nothing_and_a_refusal_does_not_end_it(rig):
    """Findings 2 and 6. A base chase held on a latched deck: its writes open nothing, and
    a refused ⌘Z leaves the hold on and the step open."""
    u, ended = rig.one.undo, []
    press(rig)
    u.keep_open("base chase", on_end=lambda: ended.append(1))
    change(rig.one.reg)
    go(rig)
    press(rig)
    refused_on(u, "undo", "on deck 1")
    assert u._kept is not None and not ended, "still held"
    change(rig.one.reg, "view.speed", 1)
    go(rig)
    assert len(u.stack) == 1, "one hold, one step"
    u.let_close()
    assert ended and u.latched, "and it opened nothing"
    change(rig.one.reg)  # a change of its own does
    go(rig)
    assert not u.latched


def test_a_refusal_does_not_cut_a_gesture_in_two(rig):
    """Finding 6. A step begun out of focus, still open: the press that finds it latched
    leaves it open, so the knob still turning is one step."""
    rig.meta.point_panel(rig.two)
    change(rig.one.reg)
    go(rig, 1)
    rig.meta.point_panel(rig.one)
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    assert rig.one.undo._open is not None
    change(rig.one.reg)
    go(rig)
    assert len(rig.one.undo.stack) == 1


def test_a_load_of_the_look_already_there_opens_nothing_for_a_press_inside_the_settle(rig):
    """Second review. The step is open and will close empty, so it is no push: the press
    refuses, and the older step, the first load, is not popped in its place."""
    _pad_rig(rig)
    rig.meta.point_panel(rig.two)
    rig.one.reg["preset.load.0"].fire()
    go(rig)
    loaded, steps = rig.two.presets.current, len(rig.two.undo.stack)
    rig.meta.point_panel(rig.one)
    rig.meta.point_panel(rig.two)
    rig.one.reg["preset.load.0"].fire()
    assert rig.two.undo._open is not None
    press(rig)
    refused_on(rig.two.undo, "undo", "on deck 2")
    assert rig.two.presets.current == loaded
    go(rig)
    assert rig.two.undo.latched and len(rig.two.undo.stack) == steps


def test_a_knob_turned_and_brought_back_inside_the_settle_opens_nothing(rig):
    """Second review. The same with a gesture, and the press does not cut it: the knob
    turned on from there is one step, which opens the latch."""
    u, p = rig.one.undo, rig.one.reg[BRIGHT]
    change(rig.one.reg)
    go(rig)
    rig.meta.point_panel(rig.two)
    rig.meta.point_panel(rig.one)
    old, steps = p.base, len(u.stack)
    change(rig.one.reg)
    go(rig, 1)
    p.set(old)
    go(rig, 1)
    assert u._open is not None
    press(rig)
    refused_on(u, "undo", "on deck 1")
    assert p.base == old and u._open is not None and len(u.stack) == steps + 1
    go(rig)
    assert u.latched and len(u.stack) == steps
    rig.reg["edit.redo"].fire()
    refused_on(u, "redo", "on deck 1")


def test_a_step_that_will_land_still_goes_back_at_the_press(rig):
    """The other side: inside the settle time, a real change is the push, and ⌘Z takes it."""
    u, p = rig.one.undo, rig.one.reg[BRIGHT]
    press(rig)
    assert u.latched
    was = p.base
    change(rig.one.reg)
    go(rig, 1)
    press(rig)
    assert p.base == was and not u.latched


def _room_step(rig):
    """A step of the room's, open to ⌘Z. Returns the param and its value before."""
    p = rig.one.reg[BRIGHT]
    was = p.base
    change(rig.one.reg)
    go(rig)
    assert not rig.one.undo.latched
    return p, was


@pytest.mark.parametrize("settled", [True, False])
def test_a_failed_load_shuts_nothing(rig, settled):
    """Third review. A load that changes nothing on the other deck: the room's ⌘Z is as
    it was, at the press inside the settle time and after it."""
    p, was = _room_step(rig)
    undo.push_on(rig.two.reg, "load that failed", load=True)
    if settled:
        go(rig)
    assert not rig.one.undo.latched
    press(rig)
    assert p.base == was


def test_a_pad_whose_file_will_not_load_shuts_nothing(rig):
    """The same by the pad's road, with a file that is not there."""
    rig.one.presets.lib.project.bank[0] = "party-wake"
    p, was = _room_step(rig)
    moved = p.base
    rig.one.presets.lib.project.bank[0] = "no-such-look"
    rig.one.reg["preset.load.0"].fire()
    go(rig)
    assert p.base == moved and not rig.one.undo.latched
    press(rig)
    assert p.base == was


@pytest.mark.parametrize("settled", [True, False])
def test_a_pad_of_the_look_already_there_shuts_nothing(rig, settled):
    _pad_rig(rig)
    rig.one.reg["preset.load.0"].fire()
    go(rig)
    p, was = _room_step(rig)
    steps = len(rig.two.undo.stack)
    rig.one.reg["preset.load.0"].fire()
    if settled:
        go(rig)
        assert len(rig.two.undo.stack) == steps, "it closed empty"
    press(rig)
    assert p.base == was


def test_a_real_load_with_cmd_z_inside_the_settle_takes_nothing_from_the_room(rig):
    """The step is still open at the press and will land: the room's stack shuts then."""
    _pad_rig(rig)
    p, _was = _room_step(rig)
    moved, steps = p.base, len(rig.one.undo.stack)
    rig.one.reg["preset.load.0"].fire()
    assert rig.two.undo._open is not None and not rig.one.undo.latched
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    assert p.base == moved and len(rig.one.undo.stack) == steps
    go(rig)
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    change(rig.one.reg, "view.speed", 1)  # the press settled it: a touch now opens it
    go(rig)
    assert not rig.one.undo.latched


def test_a_real_load_latches_the_room_as_it_lands(rig):
    _pad_rig(rig)
    _room_step(rig)
    rig.one.reg["preset.load.0"].fire()
    assert not rig.one.undo.latched, "not until it lands"
    go(rig)
    assert rig.one.undo.latched


def test_a_copy_onto_an_empty_deck_latches_the_room_though_its_step_is_cleared(rig):
    """`copy_on_air` clears the step it opened: the look landed all the same."""
    assert rig.two.presets.current is None and not rig.two.undo.stack
    p, _was = _room_step(rig)
    moved = p.base
    rig.meta.copy_on_air()
    assert rig.two.undo.stack == []
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    assert p.base == moved


def test_a_pad_leaves_a_meta_stack_in_focus_alone(rig):
    """Finding 4. An analyzer nudge, a pad, ⌘Z with the mouse unmoved: the nudge goes back."""
    _pad_rig(rig)
    q = rig.reg[META]
    undo.by_hand(True)
    here_is_meta(rig)
    was = q.base
    change(rig.reg, META)
    go(rig)
    undo.by_hand(False)
    rig.one.reg["preset.load.0"].fire()
    go(rig)
    press(rig)
    assert q.base == was


def test_a_pad_with_the_mouse_over_a_section_still_shuts_the_room(rig):
    """The room's deck open, the mouse passing a meta section as the pad lands."""
    _pad_rig(rig)
    p = rig.one.reg[BRIGHT]
    change(rig.one.reg)
    go(rig)
    moved = p.base
    here_is_meta(rig)
    rig.one.reg["preset.load.0"].fire()
    go(rig)
    here_is_meta(rig, False)
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    assert p.base == moved


def test_moving_the_panel_with_the_mouse_in_a_meta_section_leaves_meta_as_it_was(rig):
    """Finding 5. The stack ⌘Z reaches never changed. But the deck left is still left:
    coming back to it, even so, is coming back."""
    q = rig.reg[META]
    p = rig.one.reg[BRIGHT]
    change(rig.one.reg)
    go(rig)
    moved = p.base
    undo.by_hand(True)
    here_is_meta(rig)
    was = q.base
    change(rig.reg, META)
    go(rig)
    undo.by_hand(False)
    rig.meta.point_panel(rig.two)
    assert not rig.meta.undo.latched
    press(rig)
    assert q.base == was

    change(rig.one.reg, "view.speed", 1)  # (nothing here on deck 1 opens: panel elsewhere)
    go(rig)
    here_is_meta(rig, False)
    rig.meta.point_panel(rig.one)
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    assert p.base == moved


def test_away_and_back_with_the_mouse_in_a_meta_section_relatches_the_deck(rig):
    """Finding 5's other side: focus on the deck, the mouse resting in a meta section while
    the panel goes away and back, then to the canvas."""
    change(rig.one.reg)
    go(rig)
    moved = rig.one.reg[BRIGHT].base
    here_is_meta(rig)
    rig.meta.point_panel(rig.two)
    rig.meta.point_panel(rig.one)
    here_is_meta(rig, False)
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    assert rig.one.reg[BRIGHT].base == moved


def test_the_words_promise_cmd_z_only_where_a_load_is_a_push(rig):
    """Finding 7. The pad of the unedited look already loaded is no push: on a latched
    stack the words name no ⌘Z, and ⌘Z refuses."""
    _pad_rig(rig)
    rig.one.reg["preset.load.0"].fire()
    go(rig)
    rig.meta.point_panel(rig.two)
    rig.one.reg["preset.load.0"].fire()
    assert "⌘Z" not in rig.lib.status
    go(rig)
    press(rig)
    refused_on(rig.two.undo, "undo", "on deck 2")


def test_a_pad_with_focus_on_meta_names_no_cmd_z(rig):
    """The panel on that deck, focus on meta, the mouse in its section: ⌘Z is elsewhere."""
    _pad_rig(rig)
    rig.meta.point_panel(rig.two)
    undo.by_hand(True)
    here_is_meta(rig)
    change(rig.reg, META)
    go(rig)
    undo.by_hand(False)
    rig.one.reg["preset.load.0"].fire()
    assert "⌘Z" not in rig.lib.status


def _fade_across(rig):
    rig.meta.mix.xfade = 1.0
    assert rig.meta.follow_fader()


def test_a_fade_latches_the_panels_deck(rig):
    """Finding 8. A tweak off air long ago, fade across: that tweak is now the room's look."""
    rig.meta.point_panel(rig.two)
    p = rig.two.reg[BRIGHT]
    change(rig.two.reg)
    go(rig)
    moved = p.base
    assert not rig.two.undo.latched
    _fade_across(rig)
    assert rig.meta.on_air is rig.two
    press(rig)
    refused_on(rig.two.undo, "undo", "on deck 2")
    assert p.base == moved
    change(rig.two.reg, "view.speed", 1)  # no focus moved: a knob opens it
    go(rig)
    assert not rig.two.undo.latched


def test_a_fade_off_air_latches_it_too_and_leaves_meta_alone(rig):
    p = rig.one.reg[BRIGHT]
    change(rig.one.reg)
    go(rig)
    moved = p.base
    q = rig.reg[META]
    undo.by_hand(True)
    here_is_meta(rig)
    was = q.base
    change(rig.reg, META)
    go(rig)
    undo.by_hand(False)
    _fade_across(rig)
    press(rig)
    assert q.base == was, "meta in focus is as it was"
    here_is_meta(rig, False)
    press(rig)
    refused_on(rig.one.undo, "undo", "on deck 1")
    assert p.base == moved


def test_one_check_on_the_road_every_load_takes(rig):
    """Finding 9. Any `push_on(load=True)` onto the other deck with the panel on air shuts
    it; a push that is no load, or with the panel off air, does not."""
    change(rig.one.reg)
    go(rig)
    undo.push_on(rig.two.reg, "a verb that is no load")
    assert not rig.one.undo.latched
    go(rig)
    undo.push_on(rig.two.reg, "a future verb", load=True)
    change(rig.two.reg)  # a load that changes something
    go(rig)
    assert rig.one.undo.latched

    rig.meta.point_panel(rig.two)
    change(rig.two.reg)
    go(rig)
    undo.push_on(rig.one.reg, "panel off air", load=True)
    change(rig.one.reg)
    go(rig)
    assert not rig.two.undo.latched


def test_the_words_name_each_stack_from_birth(rig):
    """Finding 10: `called` is given at construction, with no fallback words."""
    assert (rig.one.undo.called, rig.two.undo.called, rig.meta.undo.called) == (
        "on deck 1",
        "on deck 2",
        "on the meta controller",
    )


def test_over_the_player_screen_nothing_moves_the_focus(rig):
    """No stack answers there (`NOTHING_HERE`), so a press there is no focus event."""
    p = rig.one.reg[BRIGHT]
    was = p.base
    change(rig.one.reg)
    go(rig)
    rig.inside["meta"] = None
    press(rig)
    assert rig.meta.undo.status == undo.NOTHING_HERE and p.base != was
    rig.inside["meta"] = False
    press(rig)
    assert p.base == was


def test_a_clear_is_no_push_and_no_focus_event(rig):
    """Rule 7. A stack reset (copy onto an empty deck) leaves the latch as it was, shut or
    open: an open one just has nothing left to say."""
    press(rig)
    assert rig.one.undo.latched
    rig.one.undo.clear()
    assert rig.one.undo.latched
    change(rig.one.reg)
    go(rig)
    rig.one.undo.clear()
    assert not rig.one.undo.latched
    press(rig)
    assert rig.one.undo.status == "nothing to undo"


def test_pointing_the_panel_at_the_deck_it_is_on_moves_nothing(rig):
    """No change of stack, no latch."""
    change(rig.one.reg)
    go(rig)
    rig.meta.point_panel(rig.one)
    assert not rig.one.undo.latched


def test_a_show_load_is_a_push_where_you_are_and_no_door_past_the_rule(rig):
    """A show's load steps on two stacks: the deck, where you are, opens; the meta
    stack, where you are not, stays shut, and the file's show is not rewound."""
    pr = rig.lib.project
    pr.load("house")
    go(rig)
    assert not rig.one.undo.latched and rig.meta.undo.stack
    here_is_meta(rig)
    press(rig)
    refused_on(rig.meta.undo, "undo", "on the meta controller")
    assert pr.name == "house"
    rig.reg["hands.smooth"].step(1)
    go(rig)
    press(rig)
    press(rig)
    assert pr.name == "party"


def test_the_instances_own_undo_knows_no_latch(rig):
    """The latch is the press's, in `undo.undo`: a tool or a test driving a stack directly
    goes by its history."""
    change(rig.one.reg)
    go(rig)
    rig.meta.point_panel(rig.two)
    rig.meta.point_panel(rig.one)
    assert rig.one.undo.latched and rig.one.undo.undo()


def test_uninstalling_lets_go_of_the_focus(rig):
    rig.meta.point_panel(rig.two)
    undo.install_meta(None)
    undo.install(None)
    assert undo.here() is None
    undo.undo()  # nothing installed: says nothing
    undo.install(rig.one.undo)
    assert rig.one.undo.latched


@pytest.mark.parametrize("pid", [BRIGHT, "view.speed"])
def test_an_edit_this_frames_tick_has_not_seen_is_taken_back_by_the_press(rig, pid):
    """The press brings the watcher up to date first: an edit in the frame of the press
    opens the latch and goes back, as it always has."""
    p = rig.one.reg[pid]
    was = p.base
    change(rig.one.reg, pid)
    press(rig)
    assert p.base == was
