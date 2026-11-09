"""The VIEW section on dkit (`ui_kit`, `ui_fields`).

What stays the panel's own: the head (`Panel._view_hero`, the big cell
count — the panel's identity), the patch strip (`Panel._section`), and the
shape menu (`Panel._shape_combo`, grouped 4D / 3D / Scenes by family: the
kit's Select has no scroll yet and the shapes are many).

What the kit draws, laid out as a form (`ui_fields.rows`, on
`tokens.SPACE`'s steps):

- brightness, speed and 4D depth as slider fields, a tick at each one's
  unity detent;
- the six rotation planes as one joined toggle group, a plane spinning lit
  in the one red; the W planes at a third while they can do nothing (a 3D
  shape, or the 3D switch holding w) — still switchable, as on the stock
  row;
- points, lines, rotate, faces and 3D as switches, two to a row;
- the two layers' opacities side by side, the screen-strokes switch under
  them;
- the copies: their count and Fit, then — with more than one — the layout
  and the motion as Selects, the motion's depth and rate, the spacing and
  a lattice's perspective;
- the six planes' rates, two to a row, under ROTATION's strip.

Without the kit, `Panel._view_stock`.
"""

from __future__ import annotations

from . import field, ui_fields, ui_kit
from .geometry import SHAPES
from .params import PLANES

SWITCHES = ("view.points", "view.lines", "view.rotate", "view.faces", "view.three_d")


def page(panel, dt: float) -> None:
    if not ui_kit.ready():
        panel._view_stock(dt)
        return
    panel._view_hero()
    panel._section("view", "view")
    panel._shape_combo()
    k = ui_kit.begin(panel)
    with ui_kit.mod("uictx").chrome(k):
        ui_fields.form(panel, k, spec(panel), lambda key, r: _cell(panel, k, key, r))
    panel._section("rotation", "rot")
    with ui_kit.mod("uictx").chrome(k):
        ui_fields.form(panel, k, rates_spec(),
                       lambda key, r: ui_fields.slider(panel, k, key, r, label=key[-2:]))


def spec(panel) -> list:
    """VIEW's form, as `ui_fields.rows` takes it: what shows depends on the
    copies (more than one: their rows) and on the layout (a lattice: its
    perspective)."""
    v = panel.view
    fh, rh = ui_fields.slider_h(), ui_fields.ROW_H
    out = [[("view.bright", fh)], [("view.speed", fh)], [("view.depth4", fh)],
           [None], [("planes", rh)]]
    sw = list(SWITCHES)
    while sw:
        out.append([(pid, rh) for pid in sw[:2]] + ([("blank", rh)] if len(sw) == 1 else []))
        sw = sw[2:]
    out += [[None], [("view.points_alpha", fh), ("view.lines_alpha", fh)],
            [("view.screen_strokes", rh)],
            [None], [("view.instances", fh, 2.0), ("view.inst_fit", fh, 1.0)]]
    if v.instances > 1:
        out.append([("view.inst_layout", rh), ("view.inst_motion", rh)])
        if v.inst_motion:
            out.append([("view.inst_amp", fh), ("view.inst_rate", fh)])
        if field.is_3d(v.inst_layout):
            out.append([("view.inst_spacing", fh), ("view.inst_persp", fh)])
        else:
            out.append([("view.inst_spacing", fh)])
    return out


def rates_spec() -> list:
    fh = ui_fields.slider_h()
    ids = [f"rot.rate.{name}" for name in PLANES]
    return [[(ids[i], fh), (ids[i + 1], fh)] for i in range(0, len(ids), 2)]


def _cell(panel, k, key: str, rect) -> None:
    if key == "blank":
        return
    if key == "planes":
        _planes(panel, k, rect)
    elif key == "view.inst_fit":            # beside the count: on the count's slider row
        x, y, w, h = rect
        sh = ui_fields.ROW_H
        ui_fields.switch(panel, k, key, (x, y + h - sh - (ui_fields.SLIDER_H - sh) / 2, w, sh))
    else:
        ui_fields.any_param(panel, k, key, rect)


def _planes(panel, k, rect) -> None:
    v = panel.view
    sh = SHAPES[v.shape]
    held = ("a 3D shape has no w" if sh.dims == 3
            else "the 3D switch holds w" if v.three_d else "")
    pids = [f"view.plane.{name}" for name in PLANES]
    inert = {f"view.plane.{n}" for n in PLANES if held and n.endswith("W")}
    ui_fields.toggles(panel, k, pids, list(PLANES), rect, inert=inert)
