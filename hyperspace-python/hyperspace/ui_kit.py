"""The panel's bridge to dkit (`tools/dkit`), the measured shadcn kit — the
first place Hyperspace imports it (the kit's HANDOFF, item 5).

The kit is a directory of bare modules (`import tokens as T`), not a
package, so `_import` puts its folder on `sys.path` and then CHECKS that
every module it asked for came from there: a top-level `draw`, `tokens` or
`wheel` from anywhere else (`wheel` is a PyPI package's name) would be a
confident wrong import, and it fails here, by name, rather than as an
AttributeError mid-frame. A build without `tools/dkit` (or
``HYPERSPACE_KIT=0``) has no kit: `ready` says so and every section that
uses it draws as it did before (`ui_camera.page` → `Panel._camera_stock`).

What a section gets from here:

- `begin(panel)`: the frame's `uictx.Ui` — kept on the panel, so the kit's
  eased states (`ease.Anim`) and its focus model outlive the frame, its
  measured tables built once, not per frame; the draw list the current
  window's. The kit's clock steps once per imgui frame, however many
  sections ask (`_tick`).
- `block(h)`: a rectangle `h` tall in the window's flow at the cursor, for
  the kit to place into (the kit draws at screen positions: imgui's flow is
  told the block's size after, `end_block`).
- `THEME`: the kit's token names in Hyperspace's palette — the black
  ground, the three greys, the one red (`ui.py`'s, read from the style
  `ui.apply_style` sets), never shadcn's neutrals: the kit's measurements
  transfer, its palette does not (its ROADMAP's standing caution).
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from imgui_bundle import imgui

KIT_DIR = Path(__file__).resolve().parents[1] / "tools" / "dkit"
# what the panel imports, leaves first; each must come from KIT_DIR
KIT_MODULES = ("tokens", "ease", "rect", "flex", "tree", "box", "draw", "uictx", "wheel",
               "interact", "menu", "comp_button")
STATE = "_kit"           # the panel's attribute: survives a reload of this module
ENV = "HYPERSPACE_KIT"   # "0": no kit, every section as it was drawn before

# the kit's faces, loaded into the atlas once (`load_faces`): kept across a
# reload of this module, as the atlas keeps them
_FACES: dict = globals().get("_FACES", {})
_MODS: dict = globals().get("_MODS", {})


class KitError(ImportError):
    """The kit is there but a module of its name came from somewhere else."""


def _import() -> dict:
    """The kit's modules by name, imported from `KIT_DIR`; {} without one.
    Raises `KitError` when a name resolves outside the kit."""
    if _MODS or not (KIT_DIR / "interact.py").exists():
        return _MODS
    if str(KIT_DIR) not in sys.path:
        sys.path.insert(0, str(KIT_DIR))
    got = {}
    for name in KIT_MODULES:
        mod = importlib.import_module(name)
        where = Path(getattr(mod, "__file__", "") or "").resolve().parent
        if where != KIT_DIR:
            raise KitError(f"dkit: `{name}` is {mod.__file__}, not the kit's ({KIT_DIR})")
        got[name] = mod
    _MODS.update(got)
    return _MODS


def enabled() -> bool:
    """Is the kit wanted: not switched off by ``HYPERSPACE_KIT=0``."""
    return os.environ.get(ENV, "1") != "0"


def ready() -> bool:
    """Can a section draw on the kit this frame: wanted, importable, and
    its faces in the atlas (`load_faces` ran with `ui.load_fonts`)."""
    return enabled() and bool(_FACES) and bool(_import())


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
    if not enabled() or not _import():
        return
    _FACES.update(mod("draw").load_faces(io, KIT_DIR))


# ---------------------------------------------------------------- the theme

def _hex(c) -> str:
    """An imgui colour (ImVec4 or a 4-tuple) as the kit's "#rrggbbaa"."""
    r, g, b, a = (c.x, c.y, c.z, c.w) if hasattr(c, "x") else c
    return "#" + "".join(f"{round(min(max(v, 0.0), 1.0) * 255):02x}" for v in (r, g, b, a))


def theme() -> dict:
    """The kit's token names in the panel's palette: each from a name in
    `ui.py` or a colour `ui.apply_style` set, so a palette change there
    lands here. Built per call: `begin` keeps the panel's."""
    from . import ui   # (late: ui imports this module)
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


def _button_table(theme_name: str) -> dict:
    """The kit's Button variants with the one literal its dark table holds
    in shadcn's palette — `secondary`'s hover, an oklch mix rasterised on
    shadcn's neutral (#2f2f2f) — put back on the panel's own hovered
    button (`ui.apply_style`)."""
    t = mod("comp_button").button_table(theme_name)
    t["secondary"] = {**t["secondary"],
                      "hover_fill": (_hex(imgui.get_style().color_(imgui.Col_.button_hovered)), 1.0)}
    return t


# ---------------------------------------------------------------- per frame

def begin(panel):
    """The kit's `Ui` for what the current window draws next: kept on the
    panel (`STATE`) with its clock and theme, its draw list this window's.
    Call `ready` first."""
    st = panel.__dict__.get(STATE)
    if st is None:
        U, ease = mod("uictx"), mod("ease")
        ui = U.Ui(None, _FACES, theme(), ease.Anim(), theme_name="dark")
        # (the cache `comp_button._table_for` reads, filled with the panel's)
        ui.anim.store.setdefault("button_tbl", {})["dark"] = _button_table("dark")
        st = panel.__dict__[STATE] = {"ui": ui, "frame": None}
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
    corner, then one item its size, so what follows is laid out after it
    and the window's scroll knows its extent (the kit placed its own items
    by screen position)."""
    x, y, w, h = rect
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
    imgui.dummy(imgui.ImVec2(w, h))
