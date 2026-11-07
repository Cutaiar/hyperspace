"""What counts as the person's hand on the panel, row 757: on real ImGui with the app's io, the
real `Panel` and its real writers, over the real three stacks. A text field stays live with nobody
at it, so it is no hand; its writers report their own write. Row 753's rule depends on the
difference: a controller's change never moves focus.
"""

import pytest
import test_undo_stacks
from conftest import seed
from imgui_bundle import imgui
from test_graph_groups import ENTRY, noita, watch
from test_ui_shell import build_rig, frame
from test_undo_stacks import go, here_is_meta
from ui_driver import Driver

from hyperspace import ui_graph, ui_loadable, ui_pane, ui_routing, undo
from hyperspace.library import LOADABLE
from hyperspace.ui import Panel, apply_style, load_fonts

rig = test_undo_stacks.rig  # the fixture
BRIGHT = "view.bright"
META = "hands.smooth"
RIDE = "master.gain"
IDLE = 30
SETTLE = 40


def ctrl():
    """The key the app's imgui reads as Ctrl (`Driver.ctrl`): Cmd on a Mac."""
    return imgui.Key.mod_super if imgui.get_io().config_mac_osx_behaviors else imgui.Key.mod_ctrl


def click_for_text(step, at, *mods):
    """A click, with `mods` held; then the mouse goes and the cursor sits."""
    io = imgui.get_io()
    io.add_mouse_pos_event(*at)
    for m in mods:
        io.add_key_event(m, True)
    step()
    io.add_mouse_button_event(0, True)
    step()
    io.add_mouse_button_event(0, False)
    for m in mods:
        io.add_key_event(m, False)
    for _ in range(2 + IDLE):
        step()
    assert io.want_text_input and not undo._hand, "the text field, and nobody at it"


def tap(step, key):
    io = imgui.get_io()
    io.add_key_event(key, True)
    step()
    io.add_key_event(key, False)
    step()


def typed(step, text):
    for ch in text:
        imgui.get_io().add_input_character(ord(ch))
        step()


class Screen:
    """Frames as the app runs them: the stacks tick, then `left`, then `body`, in a window, on
    the real `Panel`. `Driver` is only here for where each control was drawn."""

    def __init__(self, rig, monkeypatch):
        self.rig = rig
        self.panel = Panel(rig.r.control, rig.r.audio, rig.r.view, bank=rig.lib.install,
                           registry=rig.one.reg, library=rig.lib)
        self.d = Driver()
        self.d.record(monkeypatch.setattr)
        self.body = lambda: None
        self.text = ""

    def frame(self, n: int = 1):
        for _ in range(n):
            go(self.rig, 1)
            imgui.new_frame()
            ui_pane.left(self.panel)
            self.panel._fine_frame()
            imgui.set_next_window_pos(imgui.ImVec2(0, 0))
            imgui.set_next_window_size(imgui.ImVec2(900, 700))
            imgui.begin("screen")
            self.body()
            imgui.end()
            imgui.end_frame()

    def field(self):
        """A find field: writes nothing, as ROUTING's filter and the media search."""
        def body():
            _, self.text = imgui.input_text_with_hint("##find", "find", self.text)
        self.body = body
        self.frame(2)
        click_for_text(self.frame, self.d.centre("find"))
        assert imgui.is_any_item_active(), "still live"

    def slider(self, pid):
        self.body = lambda: self.panel._slider(pid)
        self.frame(2)
        click_for_text(self.frame, self.d.centre(pid), ctrl())

    def enter(self, pid, value: str):
        self.slider(pid)
        typed(self.frame, value)
        tap(self.frame, imgui.Key.enter)
        assert not imgui.get_io().want_text_input, "committed: the field has gone"


@pytest.fixture()
def screen(rig, monkeypatch):
    ctx = imgui.create_context()
    imgui.set_current_context(ctx)
    io = imgui.get_io()
    io.display_size = imgui.ImVec2(1000, 800)
    io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
    apply_style()
    load_fonts()
    s = Screen(rig, monkeypatch)
    yield s
    s.panel.close()
    imgui.destroy_context(ctx)


def meta_has_the_focus(rig):
    undo.by_hand(True)
    rig.reg[META].step(2)
    go(rig)
    undo.by_hand(False)
    assert undo._focused is rig.meta.undo


def deck_has_the_focus(rig):
    undo.by_hand(True)
    rig.one.reg[BRIGHT].step(3)
    go(rig)
    undo.by_hand(False)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched


def meta_latched_and_out_of_focus(rig):
    """A press at the meta stack latches it, a person's change on the deck takes focus off."""
    here_is_meta(rig)
    rig.reg["edit.undo"].fire()
    here_is_meta(rig, False)
    deck_has_the_focus(rig)
    assert rig.meta.undo.latched


# ------------------------------------------------ the cursor in a field, and a controller

def test_a_cursor_left_in_a_text_field_is_no_hand(screen):
    screen.field()
    screen.frame(300)
    assert not undo._hand


def test_a_controller_with_the_cursor_in_a_field_leaves_focus_and_the_meta_stack(screen):
    """The reproduction. The APC rides a meta fader, the cursor left in a find field. It took
    focus to the meta stack and opened it, and ⌘Z in the analyzer took the ride back."""
    rig = screen.rig
    deck_has_the_focus(rig)
    screen.field()
    q = rig.reg[RIDE]
    q.step(2)
    moved = q.base
    screen.frame(SETTLE)
    assert undo._focused is rig.one.undo, "a controller's change never moves focus"
    here_is_meta(rig)
    rig.reg["edit.undo"].fire()                         # coming here latches it: nothing opened it
    assert q.base == moved and "on the meta controller" in rig.meta.undo.status


def test_after_that_ride_the_deck_you_were_on_still_answers(screen):
    """The other half of the same bug: focus gone to meta, ⌘Z on the canvas refused."""
    rig = screen.rig
    deck_has_the_focus(rig)
    p = rig.one.reg[BRIGHT]
    moved = p.base
    screen.field()
    rig.reg[RIDE].step(2)
    screen.frame(SETTLE)
    rig.reg["edit.undo"].fire()
    assert p.base != moved and rig.one.undo.status.startswith("undid ")


def test_a_controller_with_the_cursor_in_a_field_leaves_a_deck_latched(screen):
    """The same the other way: focus on the meta stack, a deck moved from the desk."""
    rig = screen.rig
    meta_has_the_focus(rig)
    screen.field()
    assert rig.one.undo.latched
    rig.one.reg[BRIGHT].step(3)
    screen.frame(SETTLE)
    assert undo._focused is rig.meta.undo and rig.one.undo.latched


def test_a_controller_with_the_cursor_in_a_field_opens_the_stack_in_focus(screen):
    """Row 753: a controller's change opens the stack in focus, with or without a field."""
    rig = screen.rig
    deck_has_the_focus(rig)
    rig.meta.point_panel(rig.two)
    rig.meta.point_panel(rig.one)                       # coming back latches it
    assert rig.one.undo.latched
    screen.field()
    rig.one.reg[BRIGHT].step(3)
    screen.frame(SETTLE)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched


@pytest.mark.parametrize(("mod", "side"), [(imgui.Key.mod_super, imgui.Key.left_super),
                                           (imgui.Key.mod_shift, imgui.Key.left_shift)],
                         ids=["super", "shift"])
def test_a_modifier_held_in_a_field_is_no_hand(screen, mod, side):
    """A held ⌘ or ⇧, say on the way to ⌘Z, while the APC rides. Key activity is not a write."""
    rig = screen.rig
    deck_has_the_focus(rig)
    screen.field()
    io = imgui.get_io()
    io.add_key_event(mod, True)
    io.add_key_event(side, True)
    hands = []
    rig.reg[RIDE].step(2)
    for _ in range(90):
        screen.frame()
        hands.append(undo._hand)
    io.add_key_event(mod, False)
    io.add_key_event(side, False)
    assert not any(hands)
    assert undo._focused is rig.one.undo


def test_a_scroll_in_a_field_is_no_hand(screen):
    """The wheel is a named key to ImGui. Scrolling a list with the cursor in its find field."""
    rig = screen.rig
    deck_has_the_focus(rig)
    screen.field()
    rig.reg[RIDE].step(2)
    hands = []
    for _ in range(10):
        imgui.get_io().add_mouse_wheel_event(0.0, 1.0)
        screen.frame()
        hands.append(undo._hand)
    assert not any(hands) and undo._focused is rig.one.undo


def test_a_key_landing_on_a_controllers_frame_is_no_hand(screen):
    """A find field has no write to report: typing in it, with the APC riding on those very
    frames, moves no focus. The limit row 757 first shipped with."""
    rig = screen.rig
    deck_has_the_focus(rig)
    screen.field()
    hands = []
    for ch in "ab":
        rig.reg[RIDE].step(1)
        imgui.get_io().add_input_character(ord(ch))
        screen.frame()
        hands.append(undo._hand)
    assert screen.text == "ab" and not any(hands) and undo._focused is rig.one.undo


# ------------------------------------------------ the writers report

@pytest.mark.parametrize("pid", [BRIGHT, META], ids=["deck", "meta"])
def test_a_value_typed_into_a_slider_is_the_persons_own_change(screen, pid):
    """Enter commits it, with the mouse long gone, and it takes focus to the param's own stack
    and opens it, from wherever focus was."""
    rig = screen.rig
    stack = rig.meta.undo if pid == META else rig.one.undo
    if pid == META:
        meta_latched_and_out_of_focus(rig)
    else:
        meta_has_the_focus(rig)
    assert undo._focused is not stack and stack.latched
    p = rig.one.reg[pid]
    was = p.base
    screen.enter(pid, "0.5")
    assert p.base != was, "the typed value landed"
    screen.frame(SETTLE)
    assert undo._focused is stack and not stack.latched
    here_is_meta(rig, pid == META)
    rig.reg["edit.undo"].fire()
    assert p.base == pytest.approx(was), stack.status


def test_a_slider_field_writes_at_enter_and_the_keys_before_it_move_nothing(screen):
    """It holds what's typed and only Enter writes it."""
    rig = screen.rig
    p = rig.one.reg[BRIGHT]
    meta_has_the_focus(rig)
    screen.slider(BRIGHT)
    was = p.base
    typed(screen.frame, "0.7")
    screen.frame(SETTLE)
    assert p.base == was and undo._focused is rig.meta.undo, "nothing written, nothing moved"
    tap(screen.frame, imgui.Key.enter)
    assert p.base != was, "the Enter wrote it"
    screen.frame(SETTLE)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched


def test_tab_out_of_a_slider_field(screen):
    """Tab goes on to the next control, as it does with no keyboard navigation set."""
    rig = screen.rig
    p = rig.one.reg[BRIGHT]
    meta_has_the_focus(rig)

    def body():
        screen.panel._slider(BRIGHT)
        screen.panel._slider("view.inst_persp")
    screen.body = body
    screen.frame(2)
    click_for_text(screen.frame, screen.d.centre(BRIGHT), ctrl())
    was = p.base
    typed(screen.frame, "0.7")
    tap(screen.frame, imgui.Key.tab)
    screen.frame(SETTLE)
    assert p.base != was, "Tab wrote it"
    assert imgui.get_io().want_text_input, "and the next slider is the field now"
    assert undo._focused is rig.one.undo and not rig.one.undo.latched


def test_a_tapered_slider_typed_reports_too(screen):
    """`Panel._slider` over a taper's detents, typed."""
    rig = screen.rig
    pid = "view.instances"
    meta_has_the_focus(rig)
    p = rig.one.reg[pid]
    assert p.taper is not None
    was = p.base
    screen.enter(pid, "12")
    assert p.base != was
    screen.frame(SETTLE)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched


def test_a_fader_typed_reports_too(screen):
    """`Panel._fader`, the strip's big tapered slider: its own writer."""
    rig = screen.rig
    pid = "view.instances"
    meta_has_the_focus(rig)
    p = rig.one.reg[pid]
    was = p.base
    screen.body = lambda: screen.panel._fader(pid)
    screen.frame(2)
    click_for_text(screen.frame, screen.d.centre(pid), ctrl())
    typed(screen.frame, "5")
    tap(screen.frame, imgui.Key.enter)
    assert p.base != was
    screen.frame(SETTLE)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched


def test_a_raw_slider_typed_reports_before_its_caller_writes(screen):
    """`_raw_slider`, the road with no `Param` (a route's depth): the caller writes, after."""
    panel, rig = screen.panel, screen.rig
    deck_has_the_focus(rig)
    wrote = []

    def body():
        changed, v = panel._raw_slider("depth", 0.25, 0.0, 1.0, "%.2f", "a tip", -1)
        if changed:
            wrote.append((v, undo._hand))
    screen.body = body
    screen.frame(2)
    click_for_text(screen.frame, screen.d.centre("depth"), ctrl())
    typed(screen.frame, "0.5")
    tap(screen.frame, imgui.Key.enter)
    assert wrote == [(pytest.approx(0.5), True)]


def test_a_typed_commit_joining_a_controllers_open_step_still_counts(screen):
    """The APC moves this deck out of focus, and inside its settle time the person types a value
    into the deck. The step was begun by the controller and opened nothing, but this is the
    person's: focus comes here, and ⌘Z takes it."""
    rig = screen.rig
    meta_has_the_focus(rig)
    p = rig.one.reg[BRIGHT]
    screen.slider(BRIGHT)
    was = p.base
    typed(screen.frame, "0.7")
    p.step(1)                                           # the APC, the field still open
    go(rig, 1)
    assert rig.one.undo._open is not None and not rig.one.undo._opens
    tap(screen.frame, imgui.Key.enter)
    screen.frame(SETTLE)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched
    rig.reg["edit.undo"].fire()
    assert p.base == pytest.approx(was), rig.one.undo.status


def test_a_held_step_is_still_not_opened_by_a_hand(screen):
    """Row 753: a held step (`keep_open`) opens nothing, a hand on the panel or not."""
    rig = screen.rig
    deck_has_the_focus(rig)
    rig.meta.point_panel(rig.two)
    rig.meta.point_panel(rig.one)
    assert rig.one.chase(True)
    rig.one.reg[BRIGHT].step(2)
    go(rig, 1)
    undo.by_hand(True)
    rig.one.reg[BRIGHT].step(2)
    go(rig, 1)
    undo.by_hand(False)
    assert rig.one.undo._kept is not None and rig.one.undo.latched and not rig.one.undo._opens
    rig.one.chase(False)


def test_a_macro_label_typed_counts(screen):
    """The real `ui_routing.macros`: a label writes per keystroke and is in the fingerprint."""
    rig = screen.rig
    meta_has_the_focus(rig)
    screen.body = lambda: ui_routing.macros(screen.panel, rig.one.router)
    screen.frame(2)
    click_for_text(screen.frame, screen.d.centre("label"))
    assert undo._focused is rig.meta.undo
    typed(screen.frame, "kick")
    screen.frame(SETTLE)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched
    assert "kick" in [m.label for m in rig.one.table.macros.values()]


def _name_field(screen, commit):
    """The real save-as and rename field, opened by its own road."""
    panel = screen.panel
    ui_loadable._begin_naming(panel, "k", "")
    screen.body = lambda: ui_loadable._name_field(panel, "k", commit)
    screen.frame(IDLE)
    assert imgui.get_io().want_text_input and not undo._hand


def test_a_name_field_reports_before_its_commit_runs(screen):
    """A commit that pushes does it in the draw, so the hand has to be up first."""
    rig = screen.rig
    meta_has_the_focus(rig)
    seen = []

    def commit(name):
        seen.append(undo._hand)
        undo.push(f"rename {name}", load=True)
        rig.one.reg[BRIGHT].step(3)
    _name_field(screen, commit)
    typed(screen.frame, "x")
    tap(screen.frame, imgui.Key.enter)
    screen.frame(SETTLE)
    assert seen == [True]
    assert undo._focused is rig.one.undo and not rig.one.undo.latched
    assert rig.one.undo.stack[-1].label == "rename x"


def test_a_save_as_by_enter_moves_nothing_it_never_did(screen):
    """A save writes a file and makes no step, by the chip or by Enter: nothing to open, and the
    stack in focus stays as it was."""
    rig = screen.rig
    deck_has_the_focus(rig)
    steps = len(rig.one.undo.stack)
    _name_field(screen, lambda name: rig.lib.save_as(LOADABLE, name))
    typed(screen.frame, "kept")
    tap(screen.frame, imgui.Key.enter)
    screen.frame(SETTLE)
    assert "kept" in rig.lib.list(LOADABLE)
    assert undo._focused is rig.one.undo and len(rig.one.undo.stack) == steps


def test_the_mouse_and_a_live_item_still_count(screen):
    """What `left` always read: a button down, its release, a slider held."""
    screen.body = lambda: screen.panel._slider(BRIGHT)
    screen.frame(2)
    io = imgui.get_io()
    io.add_mouse_pos_event(*screen.d.centre(BRIGHT))
    screen.frame()
    assert not undo._hand
    io.add_mouse_button_event(0, True)
    screen.frame()
    assert undo._hand
    screen.frame(5)
    assert undo._hand and imgui.is_any_item_active() and not io.want_text_input
    io.add_mouse_button_event(0, False)
    screen.frame()
    assert undo._hand, "the release frame"
    screen.frame(2)
    assert not undo._hand


# ------------------------------------------------ the whole panel, with focus elsewhere

def _another_stack_has_the_focus(r):
    elsewhere = undo.Undo(r.reg, r.router.table, only=lambda p: False)
    undo.install_meta(elsewhere)
    undo._focus(elsewhere)
    return elsewhere


def test_the_real_panel_a_slider_typed_takes_the_focus(tmp_path, monkeypatch):
    """The real `Panel.draw`, by control id. Focus starts on another stack, so this can only
    pass by the slider's own report: Enter's frame has no mouse and no live non-text item."""
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(1600, 900)
        frame(r.panel, "view")
        stack = undo.Undo(r.reg, r.router.table)
        undo.install(stack)
        elsewhere = _another_stack_has_the_focus(r)
        clock = [0.0]

        def step():
            clock[0] += 1 / 60
            stack.tick(clock[0])
            frame(r.panel)
        d = Driver(step=step)
        d.record(monkeypatch.setattr)
        d.run(d.wait(3), d.reveal("view.instances"), d.park())
        assert undo._focused is elsewhere
        p = r.reg["view.instances"]
        click_for_text(step, d.centre("view.instances"), ctrl())
        assert undo._focused is elsewhere
        typed(step, "12")
        tap(step, imgui.Key.enter)
        assert p.value == 12
        for _ in range(60):
            step()
        assert undo._focused is stack and not stack.latched


def test_the_real_group_rename_takes_the_focus(tmp_path, monkeypatch):
    """The real `_group_side` and the real `Edit.rename_group`: Enter pushes in the draw."""
    with build_rig(tmp_path) as r:
        seed(r.lib.home)
        st = noita(r, [ENTRY])
        u = watch(r)
        elsewhere = _another_stack_has_the_focus(r)
        view = st["view"]
        g = ui_graph.group_at(view, "group.1")
        clock = [10.0]

        def step():
            clock[0] += 1 / 60
            u.tick(clock[0])
            imgui.new_frame()
            ui_pane.left(r.panel)
            imgui.set_next_window_pos(imgui.ImVec2(0, 0))
            imgui.set_next_window_size(imgui.ImVec2(600, 600))
            imgui.begin("side")
            ui_graph._group_side(r.panel, st, view, g)
            imgui.end()
            imgui.end_frame()
        d = Driver(step=step)
        d.record(monkeypatch.setattr)
        d.run(d.wait(3))
        click_for_text(step, d.centre("graph.group.name"))
        assert undo._focused is elsewhere
        typed(step, "core")
        tap(step, imgui.Key.enter)
        assert u.stack[-1].label.startswith("rename noita core to ") and undo._focused is u
        for _ in range(60):
            step()
        assert not u.latched
