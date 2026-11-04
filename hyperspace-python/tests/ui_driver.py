"""Drive the panel the way a person does: the mouse and the keys, through
imgui's own input queue, finding each control by its id — not by where a
test guessed it was drawn.

One driver for both places the panel draws:

- the headless rig (`tests/test_ui_*.py`): ``Driver(step=lambda:
  frame(panel))``, then ``d.run(d.click("view.inst_fit"))`` — `run` draws a
  frame for every step of the action;
- the real app under Xvfb (a `tools/` demo): the actions are generators,
  one ``yield`` a frame, so the app's own loop steps them — call
  ``next(action)`` once a frame from a patched `Panel.draw`, after the draw.

A control is found by what follows ``##`` in its imgui label (the param id,
for every widget `ui.py` draws for a param: ``view.inst_fit``) or by its
whole label, from the rectangles the last frame drew: `record` wraps
imgui's widget functions to note each one's rect as it is drawn.

Input arrives a frame late (imgui reads the queue at `new_frame`), and imgui
trickles one change per frame, so every action yields between a move, a
press and a release. Picking from a combo and typing a value use the
keyboard (`nav_enable_keyboard`): no row height or grab position is
guessed. Ctrl is `ctrl`, the key imgui reads as Ctrl: under
`config_mac_osx_behaviors` (on by default on a Mac) imgui swaps Ctrl and
Cmd as they enter its queue, so there Ctrl+click is Cmd+click, as it is
for a person. Why not Dear ImGui's Test Engine, which does all this by label:
from Python it runs only under imgui-bundle's own runners (HelloImGui,
ImmApp) — its scripts run on a second thread and need the GIL handed over
from C++, and the app runs its own GLFW loop.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from imgui_bundle import imgui

Rect = tuple[float, float, float, float]       # x0, y0, x1, y1 in screen (= mouse) coordinates
Action = Iterator[None]

# the widgets whose rect a driver can find (the ones ui.py and its pages draw)
WIDGETS = ("button", "small_button", "invisible_button", "checkbox", "combo", "begin_combo",
           "slider_int", "slider_float", "drag_int", "drag_float", "selectable",
           "input_text", "input_int", "input_float")


class Driver:
    def __init__(self, step: Callable[[], None] | None = None):
        self.step = step
        # every control drawn, by id and label: (its rect, imgui's frame count
        # when drawn) — only the latest frame's are there now
        self.drawn: dict[str, tuple[Rect, int]] = {}
        self.mouse = (-1.0, -1.0)
        self.revealing: str | None = None    # `reveal`: the control to scroll into view

    # ---- finding controls ----

    def record(self, patch: Callable[[object, str, object], None] | None = None) -> None:
        """Wrap imgui's widgets so each notes its rect under its id (after
        ``##``) and its whole label. `patch` is `monkeypatch.setattr` in a
        test, so the wrap is undone after it; plain `setattr` otherwise.
        Needs no imgui context: the app makes its own after this."""
        patch = patch or setattr
        for name in WIDGETS:
            real = getattr(imgui, name, None)
            if real is None:
                continue
            patch(imgui, name, self._wrap(real))

    def _wrap(self, real):
        seen = self.drawn

        def drawn(label, *a, **k):
            out = real(label, *a, **k)
            lo, hi = imgui.get_item_rect_min(), imgui.get_item_rect_max()
            r = ((lo.x, lo.y, hi.x, hi.y), imgui.get_frame_count())
            seen[label] = r
            key = label.split("##", 1)[1] if "##" in label else label
            if "##" in label:
                seen[key] = r
            if self.revealing in (label, key) and not imgui.is_item_visible():
                imgui.set_scroll_here_y(0.5)
            return out
        return drawn

    @property
    def rects(self) -> dict[str, Rect]:
        """The controls the latest frame drew: one drawn earlier and not
        since is gone, not found where it was (another may be there now)."""
        last = max((f for _, f in self.drawn.values()), default=0)
        return {k: r for k, (r, f) in self.drawn.items() if f == last}

    def rect(self, key: str) -> Rect:
        rects = self.rects
        try:
            return rects[key]
        except KeyError:
            raise KeyError(f"no control {key!r} drawn last frame "
                           f"(drawn: {', '.join(sorted(rects)[:12])}…)") from None

    def centre(self, key: str) -> tuple[float, float]:
        x0, y0, x1, y1 = self.rect(key)
        return (x0 + x1) / 2, (y0 + y1) / 2

    # ---- running ----

    def run(self, *actions: Action) -> None:
        """Run actions to the end, one frame (`step`) a yield — the headless way."""
        for action in actions:
            for _ in action:
                self.step()
        self.step()

    # ---- actions: generators, one yield a frame ----

    def wait(self, frames: int = 1) -> Action:
        for _ in range(frames):
            yield

    def reveal(self, key: str) -> Action:
        """Scroll a control into view if its section's body has it scrolled
        out (plan 49: a section can be taller than the pane; a control out
        of view is drawn, but takes no click)."""
        self.revealing = key
        yield
        self.revealing = None
        yield

    def move(self, to: str | tuple[float, float], frames: int = 1) -> Action:
        """Glide the mouse to a control's centre (or a point) over `frames`,
        scrolling it into view first."""
        if isinstance(to, str):
            yield from self.reveal(to)
        x, y = self.centre(to) if isinstance(to, str) else to
        x0, y0 = self.mouse if self.mouse[0] >= 0 else (x, y)
        io = imgui.get_io()
        for i in range(1, frames + 1):
            u = i / frames
            self.mouse = (x0 + (x - x0) * u, y0 + (y - y0) * u)
            io.add_mouse_pos_event(*self.mouse)
            yield

    def press(self, down: bool, button: int = 0) -> Action:
        imgui.get_io().add_mouse_button_event(button, down)
        yield

    def click(self, to: str | tuple[float, float], button: int = 0, frames: int = 1) -> Action:
        """Move to a control and click it (a right-click with ``button=1``)."""
        yield from self.move(to, frames)
        yield from self.press(True, button)
        yield from self.press(False, button)

    def park(self) -> Action:
        """The mouse off every control, so no tooltip or hover lingers."""
        self.mouse = (-1.0, -1.0)
        imgui.get_io().add_mouse_pos_event(-1.0, -1.0)
        yield

    @property
    def ctrl(self) -> imgui.Key:
        """The key imgui reads as Ctrl: Cmd where `config_mac_osx_behaviors`
        swaps the two at the queue (a Mac, by default), Ctrl elsewhere."""
        if imgui.get_io().config_mac_osx_behaviors:
            return imgui.Key.mod_super
        return imgui.Key.mod_ctrl

    def key(self, key: imgui.Key, *mods: imgui.Key) -> Action:
        """Tap a key, holding the modifiers (``imgui.Key.mod_ctrl`` …).
        Keyboard navigation goes on with the first key: a combo's rows and
        a slider's text field answer the keys only with it."""
        io = imgui.get_io()
        io.config_flags |= imgui.ConfigFlags_.nav_enable_keyboard
        for m in mods:
            io.add_key_event(m, True)
        io.add_key_event(key, True)
        yield
        io.add_key_event(key, False)
        for m in mods:
            io.add_key_event(m, False)
        yield

    def type(self, text: str) -> Action:
        io = imgui.get_io()
        for ch in text:
            io.add_input_character(ord(ch))
        yield

    def pick(self, combo: str, index: int, frames: int = 1) -> Action:
        """Choose entry `index` of a combo: a click opens it, then the keys —
        to the top, down `index` rows, Enter."""
        yield from self.click(combo, frames=frames)
        yield from self.wait(2)
        yield from self.key(imgui.Key.home)
        for _ in range(index):
            yield from self.key(imgui.Key.down_arrow)
        yield from self.key(imgui.Key.enter)
        yield from self.wait(1)

    def enter(self, slider: str, value: float, frames: int = 1) -> Action:
        """Type a value into a slider: Ctrl+click makes it a text field,
        Ctrl+A, the number, Enter. The number is the slider's own — a
        tapered slider's is its detent, as its readout is not."""
        yield from self.move(slider, frames)
        io, ctrl = imgui.get_io(), self.ctrl
        io.add_key_event(ctrl, True)
        yield
        yield from self.press(True)
        yield from self.press(False)
        io.add_key_event(ctrl, False)
        yield
        yield from self.key(imgui.Key.a, ctrl)
        yield from self.type(str(value))
        yield from self.key(imgui.Key.enter)
        yield from self.wait(1)

    def slide(self, slider: str, frac: float, frames: int = 12) -> Action:
        """Press on a slider and drag to `frac` of its track (0 left, 1
        right) — a slider jumps to where it is pressed, so this shows the
        drag; `enter` lands an exact value."""
        yield from self.reveal(slider)
        x0, y0, x1, y1 = self.rect(slider)
        pad = imgui.get_style().grab_min_size / 2 + imgui.get_style().frame_padding.x / 2
        y = (y0 + y1) / 2
        yield from self.move(slider)
        yield from self.press(True)
        yield from self.move((x0 + pad + (x1 - x0 - 2 * pad) * frac, y), frames)
        yield from self.press(False)
