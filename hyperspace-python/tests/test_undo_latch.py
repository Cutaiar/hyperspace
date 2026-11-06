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


def test_the_mouse_passing_over_is_no_focus_event(rig):
    """A change in a meta section, the mouse across the canvas and back, with no press and
    no change on the way: ⌘Z takes the change back."""
    q = rig.reg[META]
    here_is_meta(rig)
    was = q.base
    change(rig.reg, META)
    go(rig)
    here_is_meta(rig, False)
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
    here_is_meta(rig)
    change(rig.reg, META)
    go(rig)
    moved = q.base
    here_is_meta(rig, False)
    press(rig)  # on the canvas: the deck, latched
    here_is_meta(rig)
    press(rig)  # and back: latched again
    refused_on(rig.meta.undo, "undo", "on the meta controller")
    assert q.base == moved


def test_a_change_made_with_a_popup_over_the_section_lands_as_a_change_there(rig):
    """A combo's choice is made with nothing under the mouse: the step begins with `here`
    on the deck and closes with the mouse back in its section."""
    q = rig.reg[META]
    was = q.base
    change(rig.reg, META)
    go(rig, 1)
    here_is_meta(rig)
    go(rig)
    press(rig)
    assert q.base == was


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
