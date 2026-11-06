"""The sandwich: stock ImGui widgets for behaviour, dkit chrome for looks.

This is `Panel._track` (hyperspace/ui.py:1311-1357) generalized. That function
is the one place in 20,800 lines of UI code that already does the right thing
— run the real widget, push its own colours to transparent, and paint custom
chrome on a lower draw channel — and the whole kit hangs off making it the
normal way to build a widget rather than a one-off.

Two rules it has to keep:

* **Every interactive primitive carries an `invisible_button` with its
  `##id`.** `tests/ui_driver.py:43-46` finds controls by wrapping stock imgui
  widgets and reading the text after `##`, and twenty-two `test_ui_*.py` files
  drive the panel that way. A widget drawn purely into a draw list is
  invisible to all of them.
* **Chrome is drawn from eased state, not from the raw boolean.** ImGui holds
  nothing between frames, so the 150ms shadcn transition lives in `ease.Anim`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from imgui_bundle import imgui

import draw as D
import tokens as T
from ease import Anim, mix


@dataclass
class State:
    """What the stock widget reported this frame."""
    hovered: bool = False
    held: bool = False
    clicked: bool = False
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
    scale: float = 1.0
    _seen: set = field(default_factory=set)

    # -- state ------------------------------------------------------------
    def hit(self, key: str, x, y, w, h) -> State:
        """Place an invisible_button over the rect and read it back."""
        if w <= 0 or h <= 0:
            return State()
        if key in self._seen:
            raise ValueError(f"duplicate dkit widget id: {key!r}")
        self._seen.add(key)
        imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
        clicked = imgui.invisible_button(f"##{key}", imgui.ImVec2(w, h))
        hovered = imgui.is_item_hovered()
        held = imgui.is_item_active()
        return State(
            hovered=hovered, held=held, clicked=clicked,
            hot=self.anim.to(f"{key}:hot", 1.0 if hovered else 0.0),
            down=self.anim.to(f"{key}:down", 1.0 if held else 0.0),
        )

    def frame_done(self, dt: float) -> None:
        self.anim.step(dt)
        self._seen.clear()

    def col(self, name, a: float = 1.0):
        return T.rgba(name, a, theme=self.theme)


# --------------------------------------------------------------------------
# interactive primitives
# --------------------------------------------------------------------------

def button(ui: Ui, key, x, y, w, h, s, *, variant="outline") -> State:
    st = ui.hit(key, x, y, w, h)
    r = T.RADII["md"]
    # shadcn hovers `bg-primary/90`, `bg-accent`; press is the same colour a
    # touch further along, which is what `down` adds on top of `hot`.
    f = min(1.0, st.hot + st.down * 0.35)
    if variant == "default":
        base = ui.col("primary")
        hov = mix(base, ui.col("background"), 0.10)
        D.box(ui.dl, x, y, w, h, fill_col=mix(base, hov, f), radius=r)
        ink = "primary-foreground"
    else:
        rest = ui.col("transparent")
        hov = ui.col("accent")
        D.box(ui.dl, x, y, w, h, fill_col=mix(rest, hov, f),
              border_col=ui.col("border") if variant == "outline" else None,
              radius=r)
        ink = "foreground"
    D.label(ui.dl, x, y, s, ui.faces, "medium", 14, ui.col(ink),
            align="center", box_w=w, baseline_box=h)
    return st


def sidebar_item(ui: Ui, key, x, y, w, h, s, *, active=False, icon=None) -> State:
    st = ui.hit(key, x, y, w, h)
    rest = ui.col("accent") if active else ui.col("transparent")
    hov = ui.col("accent")
    f = min(1.0, st.hot + st.down * 0.4)
    D.fill(ui.dl, x, y, w, h, mix(rest, hov, f), T.RADII["md"])
    ink = mix(ui.col("muted-foreground"), ui.col("foreground"),
              1.0 if active else f)
    tx = x + 10
    if icon and D.icon(ui.dl, icon, x + 10, y + h / 2.0 - 8, 16, ink):
        tx = x + 34
    D.label(ui.dl, tx, y, s, ui.faces, "medium", 14, ink, baseline_box=h)
    return st


def tabs(ui: Ui, key, x, y, h, items, active, *, pad=3.0) -> tuple:
    """Returns (clicked_index_or_None, total_width)."""
    ih = h - 2 * pad
    widths = [D.text_w(s, ui.faces, "medium", 14) + 20 for s in items]
    total = sum(widths) + 2 * pad
    D.fill(ui.dl, x, y, total, h, ui.col("muted"), T.RADII["lg"])
    hit_idx, cx = None, x + pad
    for i, (s, w) in enumerate(zip(items, widths)):
        st = ui.hit(f"{key}.{i}", cx, y + pad, w, ih)
        if st.clicked:
            hit_idx = i
        sel = ui.anim.to(f"{key}:sel{i}", 1.0 if i == active else 0.0)
        if sel > 0.01:
            D.shadow(ui.dl, cx, y + pad, w, ih, (0, 0, 0, 0.10 * sel),
                     T.RADII["md"], dy=1.0, blur=3.0)
            D.fill(ui.dl, cx, y + pad, w, ih,
                   mix(ui.col("transparent"), ui.col("card"), sel),
                   T.RADII["md"])
        ink = mix(ui.col("muted-foreground"), ui.col("foreground"),
                  max(sel, st.hot * 0.7))
        D.label(ui.dl, cx, y + pad, s, ui.faces, "medium", 14, ink,
                align="center", box_w=w, baseline_box=ih)
        cx += w
    return hit_idx, total


def row(ui: Ui, key, x, y, w, h) -> State:
    """A table row: hover tints the whole band, as shadcn's `hover:bg-muted/50`."""
    st = ui.hit(key, x, y, w, h)
    if st.hot > 0.01:
        D.fill(ui.dl, x, y, w, h, mix(ui.col("transparent"),
                                      ui.col("muted", 0.5), st.hot))
    return st


def icon_button(ui: Ui, key, x, y, size, icon, *, glyph=16) -> State:
    """A square ghost button holding one icon — the kebab trigger's shape."""
    st = ui.hit(key, x, y, size, size)
    f = min(1.0, st.hot + st.down * 0.4)
    D.fill(ui.dl, x, y, size, size,
           mix(ui.col("transparent"), ui.col("accent"), f), T.RADII["md"])
    ink = mix(ui.col("muted-foreground"), ui.col("foreground"), f)
    D.icon(ui.dl, icon, x + (size - glyph) / 2, y + (size - glyph) / 2,
           glyph, ink)
    return st
