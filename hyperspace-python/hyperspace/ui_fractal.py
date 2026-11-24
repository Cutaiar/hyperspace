"""The FRACTAL section (plan 64): what a self-similar shape shows, and where
the view is inside it.

- what the shape is and where the view is: how many cells in, whether the
  fist holds the shape (outside) or the space (inside, plan 64 part 2), the
  zoom;
- **Dive** (`view.frac_dive`, plan 81): a dive rate in levels a second,
  signed — it dives for good, or climbs out to the whole shape;
- **Detail** (`view.frac_detail`), **Reach** (`view.frac_far`) and **Near**
  (`view.frac_near`): how small a cell splits on screen, how far into the
  shape cells are drawn and how near the eye before they dissolve — the
  look's own, saved and routable;
- **Additive** (`view.frac_additive`, not saved) and **To the top**
  (`view.frac_top`).

On any other shape it says how to pick one. On the kit (`ui_fields`) where
it is there, else the stock widgets.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import fractal, ui, ui_fields, ui_kit
from .geometry import SHAPES

SLIDERS = ("view.frac_dive", "view.frac_detail", "view.frac_far", "view.frac_near")


def lines(view) -> list[str]:
    """What the section says of the view: the shape, the depth, inside or out."""
    if fractal.spec_of(view.shape) is None:
        return [f"{SHAPES[int(view.shape)].name} is not a fractal.",
                "Pick one in VIEW's shape menu: 3D → Fractals, or 4D → 4D fractals."]
    d = getattr(view, "dive", None)
    depth = len(d.path) if d is not None else 0
    inside = bool(getattr(d, "inside", False))
    where = ("inside: a grab holds the space" if inside
             else "outside: a grab holds the shape")
    return [SHAPES[int(view.shape)].name,
            f"{depth} level{'s' if depth != 1 else ''} in · zoom {float(view.zoom):.2f}",
            where]


def spec() -> list:
    fh, rh = ui_fields.slider_h(), ui.FIELD_ROW_H
    return [[("view.frac_dive", fh)],                       # plan 81
            [("view.frac_detail", fh)], [("view.frac_far", fh), ("view.frac_near", fh)],
            [None], [("view.frac_additive", rh), ("view.frac_top", rh)]]


def page(panel, dt: float) -> None:
    view = panel.view
    panel._section("fractal")
    said = lines(view)
    for i, s in enumerate(said):
        if i == 0:
            imgui.text(s)
        else:
            imgui.text_disabled(s)
    if fractal.spec_of(view.shape) is None:
        return
    if not ui_kit.ready():
        for pid in SLIDERS:
            ui_fields.inline_slider(panel, pid)
        ui_fields.inline_check(panel, "view.frac_additive")
        ui_fields.inline_button(panel, "view.frac_top")
        return
    k = ui_kit.begin(panel)
    with ui_kit.mod("uictx").chrome(k):
        ui_fields.form(panel, k, spec(), lambda key, r: ui_fields.any_param(panel, k, key, r))
