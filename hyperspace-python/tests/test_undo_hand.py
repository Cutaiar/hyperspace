"""What counts as the person's hand on the panel, row 757: `ui_pane.left` on real ImGui, over
the real three stacks. A text field stays live with nobody at it, so it counts only on a frame a
key reaches it. Row 753's rule depends on the difference: a controller's change never moves focus.
"""

from types import SimpleNamespace

import pytest
import test_undo_stacks
from imgui_bundle import imgui
from test_ui_shell import build_rig, frame
from test_undo_stacks import go, here_is_meta
from ui_driver import Driver

from hyperspace import ui_loadable, ui_pane, undo
from hyperspace.library import LOADABLE
from hyperspace.ui import apply_style, load_fonts
from hyperspace.ui_routing import _macro

rig = test_undo_stacks.rig  # the fixture
BRIGHT = "view.bright"
META = "hands.smooth"
IDLE = 30


class Screen:
    """Frames as the app runs them: the stacks tick, then the draw, `left` first, with
    the widgets `body` draws in one window. `at` is the last item's centre."""

    def __init__(self, rig):
        self.rig, self.panel, self.at = rig, SimpleNamespace(), (0.0, 0.0)
        self.body = lambda: None

    def frame(self, n: int = 1):
        for _ in range(n):
            go(self.rig, 1)
            imgui.new_frame()
            ui_pane.left(self.panel)
            imgui.set_next_window_pos(imgui.ImVec2(0, 0))
            imgui.set_next_window_size(imgui.ImVec2(600, 400))
            imgui.begin("screen")
            self.body()
            lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            self.at = ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2)
            imgui.end()
            imgui.end_frame()

    def click(self):
        self.frame()                    # `at` is where the body draws now
        io = imgui.get_io()
        io.add_mouse_pos_event(*self.at)
        self.frame()
        io.add_mouse_button_event(0, True)
        self.frame()
        io.add_mouse_button_event(0, False)
        self.frame(2)                   # the release, and the frame after it

    def key(self, key):
        io = imgui.get_io()
        io.add_key_event(key, True)
        self.frame()
        was = undo._hand
        io.add_key_event(key, False)
        self.frame()
        return was

    def type(self, text: str):
        for ch in text:
            imgui.get_io().add_input_character(ord(ch))
            self.frame()

    def field(self):
        """A find field, its cursor in place and the mouse long gone."""
        self.text = ""

        def body():
            _, self.text = imgui.input_text_with_hint("##find", "find", self.text)
        self.body = body
        self.click()
        self.frame(IDLE)

    def slider(self, p):
        """A slider as `Panel._slider` draws and writes one."""
        def body():
            changed, nv = imgui.slider_float("##s", float(p.base), p.lo, p.hi)
            if changed:
                p.set_value(nv)
        self.body = body

    def open_slider(self, p):
        """Ctrl+click makes the slider a text field; the mouse goes; the cursor sits."""
        self.slider(p)
        self.frame()
        io = imgui.get_io()
        io.add_mouse_pos_event(*self.at)
        io.add_key_event(imgui.Key.mod_ctrl, True)
        self.frame()
        io.add_mouse_button_event(0, True)
        self.frame()
        io.add_mouse_button_event(0, False)
        io.add_key_event(imgui.Key.mod_ctrl, False)
        self.frame(2 + IDLE)
        assert io.want_text_input and not undo._hand, "the text field, and nobody at it"

    def enter(self, p, value: str):
        """The value, then Enter, into a slider's text field."""
        self.open_slider(p)
        self.type(value)
        assert self.key(imgui.Key.enter)
        assert not imgui.get_io().want_text_input, "committed: the field has gone"


@pytest.fixture()
def screen(rig):
    ctx = imgui.create_context()
    imgui.set_current_context(ctx)
    io = imgui.get_io()
    io.display_size = imgui.ImVec2(800, 600)
    io.backend_flags |= imgui.BackendFlags_.renderer_has_textures
    io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard
    io.config_mac_osx_behaviors = False         # plain Ctrl, on the Mac and on CI alike
    apply_style()
    load_fonts()
    yield Screen(rig)
    imgui.destroy_context(ctx)


def meta_stack_is_where_focus_is(rig):
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


def test_a_cursor_left_in_a_text_field_is_no_hand(screen):
    screen.field()
    assert imgui.is_any_item_active() and imgui.get_io().want_text_input, "the field is still live"
    assert not undo._hand


def test_a_controller_with_the_cursor_in_a_field_leaves_focus_and_the_meta_stack(screen):
    """The reproduction. The APC rides a meta fader, the cursor left in a find field. It took
    focus to the meta stack and opened it, and ⌘Z in the analyzer took the ride back."""
    rig = screen.rig
    deck_has_the_focus(rig)
    screen.field()
    q = rig.reg["master.gain"]
    q.step(2)
    moved = q.base
    screen.frame(40)
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
    rig.reg["master.gain"].step(2)
    screen.frame(40)
    rig.reg["edit.undo"].fire()
    assert p.base != moved and rig.one.undo.status.startswith("undid ")


def test_a_controller_with_the_cursor_in_a_field_leaves_a_deck_latched(screen):
    """The same the other way: focus on the meta stack, a deck moved from the desk."""
    rig = screen.rig
    meta_stack_is_where_focus_is(rig)
    screen.field()
    latched = rig.one.undo.latched
    rig.one.reg[BRIGHT].step(3)
    screen.frame(40)
    assert undo._focused is rig.meta.undo and rig.one.undo.latched == latched and latched


def test_a_controller_with_the_cursor_in_a_field_opens_the_stack_in_focus(screen):
    """Row 753: a controller's change opens the stack in focus, with or without a field."""
    rig = screen.rig
    deck_has_the_focus(rig)
    rig.meta.point_panel(rig.two)
    rig.meta.point_panel(rig.one)                       # coming back latches it
    assert rig.one.undo.latched
    screen.field()
    rig.one.reg[BRIGHT].step(3)
    screen.frame(40)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched


@pytest.mark.parametrize(("pid", "reg_of", "stack_of"), [
    (BRIGHT, lambda rig: rig.one.reg, lambda rig: rig.one.undo),
    (META, lambda rig: rig.reg, lambda rig: rig.meta.undo),
], ids=["deck", "meta"])
def test_a_value_typed_into_a_slider_is_the_persons_own_change(screen, pid, reg_of, stack_of):
    """Enter commits it, nothing moved the mouse for half a second before, and it takes the
    focus to the param's own stack and opens it, from wherever the focus was."""
    rig = screen.rig
    stack = stack_of(rig)
    here_is_meta(rig)
    rig.reg["edit.undo"].fire()                         # a press at the meta stack latches it
    here_is_meta(rig, False)
    if stack is rig.meta.undo:
        deck_has_the_focus(rig)
    else:
        assert undo._focused is rig.meta.undo
    assert undo._focused is not stack and stack.latched
    p = reg_of(rig)[pid]
    was = p.base
    screen.enter(p, "0.5")
    assert p.base != was and p.base == pytest.approx(0.5), "the typed value landed"
    screen.frame(40)
    assert undo._focused is stack and not stack.latched
    here_is_meta(rig, stack is rig.meta.undo)
    rig.reg["edit.undo"].fire()
    assert p.base == pytest.approx(was), stack.status


def test_a_slider_field_writes_at_enter_so_enter_has_to_count(screen):
    """A slider's text field holds what's typed, and only Enter writes it: the road the plain
    "no text field" rule would have lost. So that frame's hand is what the step begins on."""
    rig = screen.rig
    p = rig.one.reg[BRIGHT]
    meta_stack_is_where_focus_is(rig)
    screen.open_slider(p)
    was = p.base
    screen.type("0.7")
    screen.frame(40)
    assert p.base == was and undo._focused is rig.meta.undo, "nothing written, nothing moved"
    assert screen.key(imgui.Key.enter)
    assert p.base != was, "the Enter wrote it"
    screen.frame(40)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched


def test_only_the_frame_a_key_lands_counts_in_a_plain_field(screen):
    screen.field()
    hands = []
    for ch in "ab":
        imgui.get_io().add_input_character(ord(ch))
        screen.frame()
        hands.append(undo._hand)
        screen.frame()
        hands.append(undo._hand)
    assert hands == [True, False, True, False] and screen.text == "ab"


def test_keys_that_type_no_character_count_too(screen):
    """Backspace and Tab write or leave as Enter does, with no character in the queue."""
    screen.field()
    screen.type("ab")
    assert screen.key(imgui.Key.backspace) and screen.text == "a"
    screen.frame(5)
    assert not undo._hand
    assert screen.key(imgui.Key.escape)


def _name_field(screen, commit):
    """The real save-as and rename field, opened by its own road."""
    panel = screen.panel
    ui_loadable._begin_naming(panel, "k", "")
    screen.body = lambda: ui_loadable._name_field(panel, "k", commit)
    screen.frame(IDLE)
    assert imgui.get_io().want_text_input and not undo._hand


def test_a_name_committed_with_enter_that_changes_the_look_is_the_persons_change(screen):
    """A group's rename is the road with an undo step: `Edit.rename_group` pushes, in the
    draw, on the Enter frame. The hand has to be up in that same frame."""
    rig = screen.rig
    meta_stack_is_where_focus_is(rig)

    def commit(name):
        undo.push(f"rename {name}", load=True)
        rig.one.reg[BRIGHT].step(3)                     # what it changed
    _name_field(screen, commit)
    screen.type("x")
    assert screen.key(imgui.Key.enter)
    screen.frame(40)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched
    assert rig.one.undo.stack[-1].label == "rename x"


def test_a_save_as_by_enter_moves_nothing_it_never_did(screen):
    """A save writes a file and makes no step, by the chip or by Enter: nothing to count.
    The hand is up, focus has nothing to go to, and the stack in focus stays as it was."""
    rig = screen.rig
    deck_has_the_focus(rig)
    steps = len(rig.one.undo.stack)
    saved = []

    def commit(name):
        rig.lib.save_as(LOADABLE, name)
        saved.append(name)
    _name_field(screen, commit)
    screen.type("kept")
    assert screen.key(imgui.Key.enter)
    screen.frame(40)
    assert saved == ["kept"] and "kept" in rig.lib.list(LOADABLE)
    assert undo._focused is rig.one.undo and len(rig.one.undo.stack) == steps


def test_a_macro_label_typed_counts_as_each_key_lands(screen):
    """A label is in the fingerprint and written per keystroke (`ui_routing`): a step, by hand."""
    rig = screen.rig
    meta_stack_is_where_focus_is(rig)
    table = rig.one.table
    mid = "macro.1"

    def body():
        m = table.macros.get(mid)
        changed, text = imgui.input_text_with_hint("##label", "label", m.label if m else "")
        if changed:
            _macro(table, mid).label = text
    screen.body = body
    screen.click()
    screen.frame(IDLE)
    assert undo._focused is rig.meta.undo and not undo._hand
    screen.type("kick")
    screen.frame(40)
    assert undo._focused is rig.one.undo and not rig.one.undo.latched


def test_the_mouse_and_a_live_item_still_count(screen):
    """What `left` always read: a button down, its release, a slider held."""
    rig = screen.rig
    screen.slider(rig.one.reg[BRIGHT])
    screen.frame()
    io = imgui.get_io()
    io.add_mouse_pos_event(*screen.at)
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


def test_the_real_panel_a_slider_typed_opens_its_stack(tmp_path, monkeypatch):
    """The real `Panel`, driven by control id: `Driver.enter` on a slider, Ctrl+click and all."""
    with build_rig(tmp_path) as r:
        r.panel.desk = False
        imgui.get_io().display_size = imgui.ImVec2(1600, 900)
        frame(r.panel, "view")
        stack = undo.Undo(r.reg, r.router.table)
        undo.install(stack)
        clock = [0.0]

        def step():
            clock[0] += 1 / 60
            stack.tick(clock[0])
            frame(r.panel)
        d = Driver(step=step)
        d.record(monkeypatch.setattr)
        d.run(d.wait(3))
        assert stack.latched
        p = r.reg["view.instances"]
        d.run(d.reveal("view.instances"), d.enter("view.instances", 12))
        assert p.value == 12
        d.run(d.wait(60))
        assert not stack.latched and undo._focused is stack
