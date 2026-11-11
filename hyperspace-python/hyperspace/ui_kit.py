"""The panel's bridge to dkit (`hyperspace/dkit`), the measured shadcn kit
(its docs beside it, its tests, gallery and oracles in `hyperspace/dkit/dev`). ``HYPERSPACE_KIT=0``
switches it off: `ready` says so and every section that uses it draws as
it did before (`ui_camera.page` → `Panel._camera_stock`).

What a section gets from here:

- `begin(panel)`: the frame's `uictx.Ui` — kept on the panel, so the kit's
  eased states (`ease.Anim`) and its focus model outlive the frame, its
  measured tables built once, not per frame; the draw list the current
  window's. The kit's clock steps once per imgui frame, however many
  sections ask (`_tick`).
- `block(h)`: a rectangle `h` tall in the window's flow at the cursor, for
  the kit to place into (the kit draws at screen positions: imgui's flow is
  told the block's size after, `end_block`).
- `theme()`: the kit's token names in Hyperspace's palette — the black
  ground, the three greys, the one red (`ui.py`'s, read from the style
  `ui.apply_style` sets), never shadcn's neutrals: the kit's measurements
  transfer, its palette does not (its ROADMAP's standing caution).
"""

from __future__ import annotations

import importlib
import os

from imgui_bundle import imgui

# what the panel uses of the kit, leaves first (hotreload.MODULES has them in this order)
KIT_MODULES = ("tokens", "ease", "icons", "rect", "flex", "tree", "box", "draw", "uictx",
               "wheel", "comp_button", "interact", "menu", "comp_context_menu")
STATE = "_kit"           # the panel's attribute: survives a reload of this module
ENV = "HYPERSPACE_KIT"   # "0": no kit, every section as it was drawn before

# the kit's faces, loaded into the atlas once (`load_faces`): kept across a
# reload of this module, as the atlas keeps them
_FACES: dict = globals().get("_FACES", {})
_MODS: dict = {}         # (filled on first use: a reload of this module re-reads the kit's)


def _import() -> dict:
    """The kit's modules by name (`hyperspace.dkit`)."""
    if not _MODS:
        _MODS.update({n: importlib.import_module(f"hyperspace.dkit.{n}") for n in KIT_MODULES})
    return _MODS


def enabled() -> bool:
    """Is the kit wanted: not switched off by ``HYPERSPACE_KIT=0``."""
    return os.environ.get(ENV, "1") != "0"


def ready() -> bool:
    """Can a section draw on the kit this frame: its faces are in the atlas
    — which `load_faces` puts there only when the kit is wanted and
    imported (with `ui.load_fonts`, so ``HYPERSPACE_KIT`` is read when a
    context's fonts load, not on each of the few hundred calls a frame)."""
    return bool(_FACES)


def mod(name: str):
    """One of the kit's modules (`KIT_MODULES`), imported."""
    return _import()[name]


def load_faces(io) -> None:
    """Put the kit's faces (Geist, the symbol fallback behind each) in the
    atlas, beside the panel's own: every time `ui.load_fonts` builds one
    (a new imgui context is a new atlas — the test rigs make one each —
    and the old faces went with the old one). In place, so a `Ui` holding
    the dict sees the new ones. Nothing without the kit, or with it
    switched off."""
    _FACES.clear()
    if not enabled():
        return
    _FACES.update(mod("draw").load_faces(io))


# ---------------------------------------------------------------- the theme

def _hex(c) -> str:
    """An imgui colour (ImVec4 or a 4-tuple) as the kit's "#rrggbbaa"."""
    r, g, b, a = (c.x, c.y, c.z, c.w) if hasattr(c, "x") else c
    return "#" + "".join(f"{round(min(max(v, 0.0), 1.0) * 255):02x}" for v in (r, g, b, a))


def theme() -> dict:
    """The kit's token names in the panel's palette: each from a name in
    `ui.py` or a colour `ui.apply_style` set, so a palette change there
    lands here. Built per call: `begin` keeps the panel's."""
    from . import ui  # (late: ui imports this module)
    s, put = imgui.get_style(), imgui.Col_

    def style(c) -> str:
        return _hex(s.color_(c))

    return {
        "background": style(put.window_bg),
        "foreground": _hex(ui.TEXT),
        "card": style(put.popup_bg),
        "popover": style(put.popup_bg),
        "popover-foreground": _hex(ui.TEXT),
        "primary": _hex(ui.RED),                  # the one red: a fill, a range
        "primary-foreground": _hex(ui.TEXT),
        "secondary": style(put.button),           # the panel's grey button
        "secondary-foreground": _hex(ui.TEXT),
        "muted": style(put.frame_bg),             # a track, a key cap
        "muted-foreground": _hex(ui.DIM),
        "accent": style(put.header),
        "border": _hex(ui.LINE),
        "input": style(put.border),
        "ring": _hex(ui.RED),                     # the panel's nav colour
        "destructive": _hex(ui.WARN),
        "sidebar": style(put.title_bg),
        "transparent": "#00000000",
    }


def tables() -> dict:
    """The panel's own reading of the kit's measured tables (`uictx.Ui.tables`):
    what a token name cannot say.

    - ``slider.track``: the panel's line grey. The kit's `muted` — the
      panel's frame grey — all but vanished on the black ground, so a slider
      at its low end read as a lone dot (the crossfader, at 0).
    - ``button.secondary.hover_fill``: the panel's own hovered button
      (`ui.apply_style`), for the literal the kit's dark table holds — an
      oklch mix rasterised on shadcn's neutral (#2f2f2f)."""
    hover = _hex(imgui.get_style().color_(imgui.Col_.button_hovered))
    return {"slider": {"track": ("border", 1.0)},
            "button": {"secondary": {"hover_fill": (hover, 1.0)}}}


# ---------------------------------------------------------------- per frame

_SHARED: dict = globals().get("_SHARED", {})   # `begin(None)`'s state: kept across a reload


def begin(panel=None):
    """The kit's `Ui` for what the current window draws next: kept on the
    panel (`STATE`) with its clock and theme, its draw list this window's.
    With no panel (a module-level helper — `ui.chip` — has none), one Ui
    for the process. Call `ready` first."""
    if panel is None:
        holder = _SHARED
    else:
        holder = panel.__dict__
    st = holder.get(STATE)
    if st is None:
        U, ease = mod("uictx"), mod("ease")
        # imgui's id stack, not the kit's raw key, tells two items apart: the
        # panel draws one param in two scopes on purpose (a chip and a check
        # for one FX, under different ``push_id``s), and imgui's own conflict
        # check runs in the panel's tests (`test_ui_pane`'s "no conflicting ids")
        ui = U.Ui(None, _FACES, theme(), ease.Anim(), theme_name="dark", tables=tables(),
                  unique_keys=False)
        st = holder[STATE] = {"ui": ui, "frame": None}
    ui = st["ui"]
    _tick(st, ui)
    ui.dl = imgui.get_window_draw_list()
    return ui


def _tick(st: dict, ui) -> None:
    """Step the kit's clock once per imgui frame, at the first section that
    asks: its eases advance by the frame's dt, its duplicate-id check starts
    afresh, and the last input decides whether a focus ring shows
    (`Ui.frame_done`). A frame no section asks in is not counted: a folded
    section's eases hold, and pick up where they were."""
    fc = imgui.get_frame_count()
    if st["frame"] == fc:
        return
    if st["frame"] is not None:
        ui.frame_done(imgui.get_io().delta_time)
    st["frame"] = fc


def block(h: float) -> tuple[float, float, float, float]:
    """(x, y, w, h): a rectangle the full width of the window's content,
    `h` tall, at the cursor — the room a kit layout places into."""
    p = imgui.get_cursor_screen_pos()
    return p.x, p.y, imgui.get_content_region_avail().x, h


def end_block(rect: tuple[float, float, float, float]) -> None:
    """Tell imgui's flow the block `rect` was drawn: the cursor back to its
    corner, then the layout advanced by its size (`ItemSize`), so what
    follows is laid out after it and the window's scroll knows its extent
    (the kit placed its own items by screen position). No item is added:
    the kit control drawn last stays imgui's last item, which is what the
    panel's tooltip, menu and Learn calls after a widget act on — and a
    dummy over the block would be a second item on the same rect for
    anything that walks a section's items."""
    x, y, w, h = rect
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
    imgui.internal.item_size(imgui.ImVec2(w, h))
