"""The CAMERA section on dkit (`ui_kit`, `ui_fields`): the orbit's five
params and the eye's two as slider fields, Reset view as the kit's Button
with its key beside it as a Kbd.

The first section ported (the kit's HANDOFF item 5); the fields it needed
are `ui_fields` now, and what is left here is the section's layout:
`box.flex` on `tokens.SPACE`'s steps (REVIEW: space is a scale). Without
the kit (``HYPERSPACE_KIT=0``, or no `tools/dkit`), the section is drawn as
before (`Panel._camera_stock`). `Panel._page_camera` is the section's
entry, as every section's is its `_page_<key>`.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui, ui_fields, ui_kit

ORBIT = ("camera.zoom", "camera.yaw", "camera.pitch", "camera.pan.x", "camera.pan.y")
EYE = ("eye.fov", "eye.distance")    # plan 43 C2: the eye the world is seen through
RESET = "camera.reset"
HINT_KEY = "R"                       # the key bound to Reset view (bindings.default.json)
HINT = "· stick click"               # … and the pad's (gamepad.py)


def page(panel, dt: float) -> None:
    """The CAMERA section: on the kit when it is there, else as it was."""
    if not ui_kit.ready():
        panel._camera_stock(dt)
        return
    panel._section("camera", "camera")
    k = ui_kit.begin(panel)
    with ui_kit.mod("uictx").chrome(k):
        draw(panel, k)


def layout(w: float, field_h: float, row_h: float) -> list[tuple[str, tuple]]:
    """The body, `w` wide from (0, 0): ("field:<id>", rect) for each param,
    then ("actions", rect). The orbit's five and the eye's two are a step
    further apart than the fields in each."""
    B, T = ui_kit.mod("box"), ui_kit.mod("tokens")
    sp = T.SPACE
    items, keys = [], []
    for g, group in enumerate((ORBIT, EYE)):
        if g:
            items.append(B.Item(h=sp[1], shrink=0))
            keys.append("gap")
        for pid in group:
            items.append(B.Item(h=field_h, shrink=0))
            keys.append(f"field:{pid}")
    items += [B.Item(h=sp[1], shrink=0), B.Item(h=row_h, shrink=0)]
    keys += ["gap", "actions"]
    total = sum(i.h for i in items) + sp[3] * (len(items) - 1)
    rows = B.flex(B.Rect(0.0, 0.0, w, total), items, direction="column", gap=sp[3])
    return [(key, (r.x, r.y, r.w, r.h)) for key, r in zip(keys, rows) if key != "gap"]


def draw(panel, k) -> None:
    """The body, on the kit `Ui` `k`, in the window's flow at the cursor."""
    x, y, w, _ = ui_kit.block(0.0)
    rows = layout(w, ui_fields.slider_h(), ui_fields.ROW_H)
    h = max(r[1] + r[3] for _, r in rows)
    for what, (rx, ry, rw, rh) in rows:
        rect = (x + rx, y + ry, rw, rh)
        if what.startswith("field:"):
            ui_fields.slider(panel, k, what[len("field:"):], rect)
        else:
            _actions(panel, k, rect)
    ui_kit.end_block((x, y, w, h))


def _actions(panel, k, rect) -> None:
    """Reset view, then its key and the pad's click beside it while they fit."""
    B, T, D = (ui_kit.mod(n) for n in ("box", "tokens", "draw"))
    x, y, w, h = rect
    tbl = k.anim.store.setdefault("kbd_tbl", {}).get(k.theme_name)
    if tbl is None:
        tbl = k.anim.store["kbd_tbl"][k.theme_name] = T.kbd_table(k.theme_name)
    kw, kh = D.kbd_size(HINT_KEY, k.faces, tbl)
    imgui.push_font(ui._FONTS["ui"], ui.FONT_BASE)
    hw = imgui.calc_text_size(HINT).x
    imgui.pop_font()
    bw = ui_fields.button_w(k, panel.reg[RESET].label)
    button, key, hint = B.flex(
        B.Rect(x, y, w, h),
        [B.Item(w=bw, shrink=0), B.Item(w=kw, h=kh, shrink=0), B.Item(w=hw, shrink=0)],
        direction="row", gap=T.SPACE[2], align="center")
    ui_fields.button(panel, k, RESET, (button.x, y, button.w, h))
    if hint.x + hint.w <= x + w:              # the words only where they fit the pane
        D.kbd(k.dl, key.x, key.y, HINT_KEY, k.faces, k.theme, tbl)
        ui_fields.text(k.dl, hint.x, y, h, HINT, "ui", ui.FONT_BASE, ui.FAINT)
    elif key.x + key.w <= x + w:
        D.kbd(k.dl, key.x, key.y, HINT_KEY, k.faces, k.theme, tbl)
