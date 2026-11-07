"""The per-frame context every primitive takes, and the sandwich's two halves.

`State` is what a stock widget reported this frame; `Ui` is everything a
primitive needs, threaded in one object and rebuilt every frame; `chrome`
holds the imgui style overrides for a whole frame; `_sandwich_begin` and
`_sandwich_end` push the stock widget's colours transparent and put the dkit
chrome on the channel under it. Everything in `interact.py` depends on these
and none of them depends on anything there.

Moved out of `interact.py` by `HANDOFF.md` item 3b, which re-exports every
name a caller uses - `I.Ui`, `I.chrome`, `I._sandwich_end` keep working.

Named `uictx` rather than the handoff's `ui.py` on purpose: eight places in
this kit cite Hyperspace's own `ui.py` by bare file name and line number
(`ui.py:1311-1357`, `ui.py:317-329`), and a kit module of the same name
would quietly make every one of them point at the wrong file.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field

from imgui_bundle import imgui

import tokens as T
from ease import Anim


@dataclass
class State:
    """What the stock widget reported this frame."""
    hovered: bool = False
    held: bool = False
    clicked: bool = False
    focused: bool = False   # raw imgui focus - see Ui.focus_f for the ring
    hot: float = 0.0        # eased hover, 0..1
    down: float = 0.0       # eased press, 0..1


@dataclass
class Ui:
    """Everything a primitive needs, threaded in one object.

    `dl` must be a real window's draw list, not the background list:
    replay.keep (hyperspace/replay.py:91) only carries the page window's own
    list into the canvas tap, so background-list chrome would vanish from
    `panel:graph`.
    """
    dl: object
    faces: dict
    theme: dict
    anim: Anim
    grad_tex: int | None = None
    theme_name: str = "light"
    _seen: set = field(default_factory=set)

    # Per-widget state that outlives the frame lives on `anim`, because a Ui
    # is rebuilt every frame (dashboard.py:569) and anything kept here would
    # be thrown away before it could be read back.
    @property
    def drag(self) -> dict:
        return self.anim.store["drag"]

    @property
    def texting(self) -> dict:
        return self.anim.store["texting"]

    @property
    def scroll(self) -> dict:
        return self.anim.store.setdefault("scroll", {})

    @property
    def focus_visible(self) -> bool:
        """Whether a focus ring should show at all - CSS `:focus-visible`.

        ImGui has one notion of focus and a mouse click sets it, so a button
        clicked with the pointer kept its ring for ever and the ring walked
        from one button to the next as you clicked them. The browser does
        not do that: `:focus-visible` rings a control reached by KEYBOARD
        and never one reached by pointer.

        So the kit tracks which the last input was. Any mouse button press
        turns it off; Tab or an arrow turns it on. That is the same
        heuristic browsers use, and it is the whole of the difference.
        """
        return bool(self.anim.store.get("kbd", False))

    # -- the measured component tables, resolved for this theme ----------
    def __post_init__(self):
        self.slider_tbl = T.slider_table(self.theme_name)
        self.switch_tbl = T.switch_table(self.theme_name)
        self.input_tbl = T.input_table(self.theme_name)
        self.select_tbl = T.select_table(self.theme_name)
        self.tooltip_tbl = T.tooltip_table(self.theme_name)

    @property
    def viewport(self):
        import box as B
        vp = imgui.get_main_viewport()
        return B.Rect(vp.work_pos.x, vp.work_pos.y,
                      vp.work_size.x, vp.work_size.y)

    def hover_clock(self, key: str, hovered: bool) -> float:
        """Seconds this id has been hovered without a break."""
        h = self.anim.store["hover"]
        if not hovered:
            h.pop(key, None)
            return 0.0
        h[key] = h.get(key, 0.0) + self._dt
        return h[key]

    # -- state ------------------------------------------------------------
    def hit(self, key: str, x, y, w, h, *, allow_overlap: bool = False,
            nav: bool = True) -> State:
        """Place an invisible_button over the rect and read it back.

        `allow_overlap` lets a later, smaller control on top of this one take
        the hover — a row with a kebab in it, for instance. Without it the
        row swallows the button.

        `nav=False` keeps the target out of the Tab order. It is for a
        target that exists only to catch a POINTER: a range slider's track
        is one, and left navigable it swallowed the Tab that belongs to the
        thumbs, so the keyboard could focus a slider and ring nothing.
        """
        if w <= 0 or h <= 0:
            return State()
        if key in self._seen:
            raise ValueError(f"duplicate dkit widget id: {key!r}")
        self._seen.add(key)
        imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
        if allow_overlap:
            imgui.set_next_item_allow_overlap()
        # `enable_nav`, and without it NONE of the kit's focus rings can ever
        # appear. Measured in ImGui 1.92.9: an `invisible_button` submitted
        # plainly is added with `ImGuiItemFlags_NoNav`, so `is_item_focused`
        # is False for ever - under an arrow key, under Tab, and even after
        # `set_keyboard_focus_here`, which is the one case that proves it is
        # the item and not the input. `ImGuiButtonFlags_EnableNav` (1.91) is
        # the supported way back in, and with it focus lands on the frame the
        # window is navigated.
        clicked = imgui.invisible_button(
            f"##{key}", imgui.ImVec2(w, h),
            imgui.ButtonFlags_.enable_nav if nav else 0)
        # AND the pointer is actually inside the rect, which is not
        # redundant. This comment used to say that a real `imgui.button`
        # "reports is_item_hovered True while merely nav-focused" and that
        # `invisible_button` + `enable_nav` was the way to avoid it. It is
        # not: measured in 1.92.9 with the pointer parked at (5, 5) and a
        # 28x28 button at (80, 60), `is_item_hovered()` turns True on the
        # frame after a Tab reaches it and stays True.
        #
        # Every control that reads `State.hot` was therefore lighting its
        # HOVER tint off the keyboard - the sidebar item, the tabs trigger,
        # the table row, the kebab, and `comp_button.ui_button` too. It is
        # RETRO row 37 one level up: there the menus' highlight turned out to
        # be ImGui's nav leaking through `is_item_hovered`, and the lesson
        # was to ask what paints a thing before believing it is yours. The
        # same call was still being believed here.
        #
        # Narrowing it cannot lose a real hover: ImGui's own answer still
        # decides occlusion and overlap, and this only removes the case where
        # the pointer is somewhere else entirely. A drag that leaves a held
        # control correctly goes un-hovered while `held` stays, which is the
        # behaviour comp_button.button documents for `hot` versus `down`.
        mp = imgui.get_io().mouse_pos
        hovered = (imgui.is_item_hovered()
                   and x <= mp.x < x + w and y <= mp.y < y + h)
        held = imgui.is_item_active()
        # read here or not at all: `is_item_focused` answers for the LAST
        # submitted item, so a caller that asks two draw calls later gets
        # whatever was submitted since. Ring strength is `Ui.focus_f`.
        focused = imgui.is_item_focused()
        return State(
            hovered=hovered, held=held, clicked=clicked, focused=focused,
            hot=self.anim.to(f"{key}:hot", 1.0 if hovered else 0.0),
            down=self.anim.to(f"{key}:down", 1.0 if held else 0.0),
        )

    @property
    def _dt(self) -> float:
        return self.anim.store.get("dt", 1.0 / 60.0)

    _NAV_KEYS = ("tab", "left_arrow", "right_arrow", "up_arrow",
                 "down_arrow", "home", "end", "enter", "space")

    def frame_done(self, dt: float) -> None:
        self.anim.step(dt)
        self.anim.store["dt"] = dt
        self._seen.clear()
        # see `focus_visible`: the last input decides whether a ring shows
        io = imgui.get_io()
        if any(imgui.is_mouse_clicked(b) for b in (0, 1, 2)):
            self.anim.store["kbd"] = False
        else:
            for name in self._NAV_KEYS:
                k = getattr(imgui.Key, name, None)
                if k is not None and imgui.is_key_pressed(k):
                    self.anim.store["kbd"] = True
                    break

    def focus_f(self, key: str, focused: bool, *, disabled: bool = False
                ) -> float:
        """The eased `:focus-visible` ring strength for one control, 0..1.

        The same three lines `comp_button.ui_button` writes out, which every
        ringed control in the kit needs and four of them were missing:

          * the ring is `:focus-visible`, so a control reached with the
            POINTER never gets one - `focus_visible` is the gate;
          * a `disabled` control never rings;
          * it eases on shadcn's 150ms curve rather than snapping.

        The Input is the one measured exception and does not come through
        here: a text field matches `:focus-visible` from a pointer click too.
        See `text_input` and tokens.INPUT.
        """
        on = bool(focused) and self.focus_visible and not disabled
        return self.anim.to(f"{key}:focus", 1.0 if on else 0.0)

    def col(self, name, a: float = 1.0):
        return T.rgba(name, a, theme=self.theme)


@contextmanager
def chrome(ui: Ui):
    """Hold the imgui style settings the kit overrides, for a whole frame.

    Two of ImGui's stock colours are visible through every widget the kit
    wraps and neither has any counterpart in shadcn:

      * **`nav_cursor`** — the blue rectangle ImGui draws around whatever
        has keyboard focus. shadcn's focus affordance is the ring this kit
        draws itself (`draw.ring`), on `:focus-visible` only, and the two
        on screen together read as a bug.
      * **`text_selected_bg`** — ImGui's is `(0.26, 0.59, 0.98, 0.35)`. The
        browser's, measured, is `tokens.SELECTION`.

    Putting them here rather than in each component is the point: a widget
    that forgets is still right, and there is one place to change when a
    measurement moves.
    """
    imgui.push_style_color(imgui.Col_.nav_cursor, imgui.ImVec4(0, 0, 0, 0))
    imgui.push_style_color(imgui.Col_.text_selected_bg,
                           imgui.ImVec4(*T.SELECTION))
    try:
        yield ui
    finally:
        imgui.pop_style_color(2)


def _sandwich_begin(ui: Ui, clear_grab: bool = True) -> list:
    """Split the draw list and make the stock widget's own chrome invisible.

    Returns the pushed colour list so `_sandwich_end` can pop the right
    number - the same bookkeeping ui.py:1327-1332 does by hand.
    """
    ui.dl.channels_split(2)
    ui.dl.channels_set_current(1)
    cols = [imgui.Col_.frame_bg, imgui.Col_.frame_bg_hovered,
            imgui.Col_.frame_bg_active]
    if clear_grab:
        cols += [imgui.Col_.slider_grab, imgui.Col_.slider_grab_active]
    clear = imgui.ImVec4(0, 0, 0, 0)
    for c in cols:
        imgui.push_style_color(c, clear)
    # `nav_cursor` is ImGui's blue focus rectangle. No shadcn component has
    # one: focus is a ring the kit draws itself, and only on `focus-visible`.
    # It is cleared here as well as in `chrome()` so a component used on its
    # own - in a test, in the gallery - is never ringed in blue either.
    imgui.push_style_color(imgui.Col_.nav_cursor, clear)
    cols = cols + [imgui.Col_.nav_cursor]
    return cols


def _sandwich_end(ui: Ui, cols: list) -> None:
    imgui.pop_style_color(len(cols))
    ui.dl.channels_set_current(0)
