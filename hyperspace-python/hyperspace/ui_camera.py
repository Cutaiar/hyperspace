"""The CAMERA section on dkit (`ui_kit`): the first of the pane's sections
drawn with the measured kit rather than imgui's stock widgets — the kit's
HANDOFF item 5, the test of whether the kit pays off where it is used.

The same seven params, the same button, the same ids: each slider is the
kit's `interact.slider` over a real `imgui.slider_float` carrying
``##<param id>``, and Reset view is the kit's Button over an
`invisible_button` carrying ``##camera.reset``, so the panel driver
(`tests/ui_driver.py`), Learn's frame, the right-click menu, ⇧-drag fine
mode and the tooltip find each one as they found the stock widget: every
one of those is the panel's own (`Panel._ctx`, `_learn_frame`,
`_fine_throw`, `_fine_tip`), hung off the kit widget's imgui item, which is
the last item when the kit returns. What the kit brings is the chrome — a
thin track, a round thumb, a ring on hover and on keyboard focus — and the
layout: a field is a header (the label, the readout) over its slider, laid
out by `box.flex` on `tokens.SPACE`'s steps (REVIEW: space is a scale),
not a label column beside a slider with the value printed inside it.

What stays the panel's: the palette (`ui_kit.theme`), the label and
readout faces (`ui._micro`'s, `ui._readout`'s — the kit's own text runs a
few percent wide of Chromium's, its RETRO row 61), the section's title and
preset strip (`Panel._section`), and every behaviour of a param widget.

Without the kit (``HYPERSPACE_KIT=0``, or no `tools/dkit`), the section is
drawn as before (`Panel._camera_stock`). `Panel._page_camera` is the
section's entry, as every section's is its `_page_<key>`.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui, ui_kit

ORBIT = ("camera.zoom", "camera.yaw", "camera.pitch", "camera.pan.x", "camera.pan.y")
EYE = ("eye.fov", "eye.distance")    # plan 43 C2: the eye the world is seen through
RESET = "camera.reset"
HINT_KEY = "R"                       # the key bound to Reset view (bindings.default.json)
HINT = "· stick click"               # … and the pad's (gamepad.py)
SLIDER_H = 20.0                      # a slider's hit row: the 12 px thumb and its ring
BUTTON_SIZE = "sm"                   # 28 tall: the panel's own frame height


def page(panel, dt: float) -> None:
    """The CAMERA section: on the kit when it is there, else as it was."""
    if not ui_kit.ready():
        panel._camera_stock(dt)
        return
    panel._section("camera", "camera")
    k = ui_kit.begin(panel)
    U = ui_kit.mod("uictx")
    with U.chrome(k):
        draw(panel, k)


def layout(w: float, head_h: float, button_h: float) -> list[tuple[str, tuple]]:
    """The section's body, `w` wide from (0, 0): (what, rect) down it — a
    field's header ("head:<id>") and slider ("slider:<id>") for each param,
    then the row of Reset view ("actions"). The orbit's five and the eye's
    two are a step further apart than the fields in each (`tokens.SPACE`)."""
    B, T = ui_kit.mod("box"), ui_kit.mod("tokens")
    sp = T.SPACE
    items, keys = [], []
    for g, group in enumerate((ORBIT, EYE)):
        if g:
            items.append(B.Item(h=sp[1], shrink=0))    # the gap between the groups
            keys.append("gap")
        for pid in group:
            items.append(B.Item(h=head_h + sp[1] + SLIDER_H, shrink=0))
            keys.append(f"field:{pid}")
    items.append(B.Item(h=sp[1], shrink=0))
    keys.append("gap")
    items.append(B.Item(h=button_h, shrink=0))
    keys.append("actions")
    total = sum(i.h for i in items) + sp[3] * (len(items) - 1)
    rows = B.flex(B.Rect(0.0, 0.0, w, total), items, direction="column", gap=sp[3])
    out = []
    for key, r in zip(keys, rows):
        if key.startswith("field:"):
            pid = key[len("field:"):]
            head, slider = B.flex(r, [B.Item(h=head_h, shrink=0), B.Item(h=SLIDER_H, shrink=0)],
                                  direction="column", gap=sp[1])
            out += [(f"head:{pid}", _xywh(head)), (f"slider:{pid}", _xywh(slider))]
        elif key == "actions":
            out.append(("actions", _xywh(r)))
    return out


def _xywh(r) -> tuple[float, float, float, float]:
    return r.x, r.y, r.w, r.h


def _line_h(font: str, size: float) -> float:
    imgui.push_font(ui._FONTS[font], size)
    try:
        return imgui.get_text_line_height()
    finally:
        imgui.pop_font()


def draw(panel, k) -> None:
    """The body, on the kit `Ui` `k`, in the window's flow at the cursor."""
    head_h = max(_line_h("micro", ui.FONT_MICRO), _line_h("num", ui.FONT_NUM))
    button_h = ui_kit.mod("comp_button").BUTTON_SIZES[BUTTON_SIZE]["h"]
    x, y, w, _ = ui_kit.block(0.0)
    rows = layout(w, head_h, button_h)
    h = max(r[1] + r[3] for _, r in rows)
    for what, (rx, ry, rw, rh) in rows:
        kind, _, pid = what.partition(":")
        if kind == "head":
            _head(panel, k, pid, x + rx, y + ry, rw, rh)
        elif kind == "slider":
            _slider(panel, k, pid, x + rx, y + ry, rw, rh)
        else:
            _actions(panel, k, x + rx, y + ry, rw, rh)
    ui_kit.end_block((x, y, w, h))


def _text(dl, x: float, y: float, h: float, s: str, font: str, size: float, col) -> float:
    """`s` in one of the panel's faces, centred on a row `h` tall; its width."""
    imgui.push_font(ui._FONTS[font], size)
    try:
        ext = imgui.calc_text_size(s)
        dl.add_text(imgui.ImVec2(round(x), round(y + (h - ext.y) / 2)), ui.u32(col), s)
        return ext.x
    finally:
        imgui.pop_font()


def _head(panel, k, pid: str, x: float, y: float, w: float, h: float) -> None:
    """A field's header: its label left in the label face (it opens the
    param's menu, as `Panel._label_cell`'s does), its readout right in the
    readout face — `base → effective` in red while a lane rides it."""
    B, T = ui_kit.mod("box"), ui_kit.mod("tokens")
    a = panel.reg[pid]
    p = panel._real(a)
    text = panel._mod_text(p) if p.modulated else p.text()
    tw = ui._readout_width(text)
    label, value = B.flex(B.Rect(x, y, w, h), [B.Item(grow=1), B.Item(w=tw, shrink=0)],
                          direction="row", gap=T.SPACE[2])
    words = ui.fit_micro(a.label, label.w)
    _text(k.dl, label.x, y, h, words, "micro", ui.FONT_MICRO, ui.DIM)
    _text(k.dl, value.x, y, h, text, "num", ui.FONT_NUM, ui.RED if p.modulated else ui.TEXT)
    imgui.set_cursor_screen_pos(imgui.ImVec2(label.x, y))
    imgui.dummy(imgui.ImVec2(max(label.w, 1.0), h))
    panel._ctx_label(a)


def _slider(panel, k, pid: str, x: float, y: float, w: float, h: float) -> bool:
    """A param's slider: the kit's chrome over the stock slider, the
    panel's behaviours on it. The thumb travels `w` less its own width, so
    that is the throw a ⇧-drag measures (`Panel._fine_throw`); a lane's
    effective value is a white tick on the track (`Panel._ghost`'s)."""
    I, tbl = ui_kit.mod("interact"), k.slider_tbl
    a = panel.reg[pid]
    p = panel._real(a)
    t0 = p.norm
    text = (panel._mod_text(p) if p.modulated else p.text()).replace("%", "%%")
    flags = imgui.SliderFlags_.logarithmic if p.log else 0
    dim = getattr(panel, "_picking", False)       # a desk control is picked (`ui_pane._body`)
    # the stock slider's height is the row's, and its grab the kit thumb's,
    # so where a press lands is where the thumb is drawn (to imgui's 2 px
    # grab padding); Ctrl+click types into the readout face
    pad = (h - ui.FONT_NUM) / 2
    imgui.push_style_var(imgui.StyleVar_.frame_padding, imgui.ImVec2(0, pad))
    imgui.push_style_var(imgui.StyleVar_.grab_min_size, tbl["thumb"])
    imgui.push_font(ui._FONTS["num"], ui.FONT_NUM)
    try:
        changed, nv = I.slider(k, pid, x, y, w, h, float(p.base), p.lo, p.hi, fine=False,
                               disabled=dim, fmt=text, flags=flags, frac=t0,
                               origin=panel._origin(p))
    finally:
        imgui.pop_font()
        imgui.pop_style_var(2)
    span = w - tbl["thumb"]
    own, t = panel._fine_throw(t0, span)
    if own:
        changed = t is not None            # a frame the mouse did not move writes nothing
        if changed:
            nv = p._value_of_norm(t)
    panel._fine_tip(a, p)
    panel._ctx(a)
    panel._learn_frame(a)
    if p.modulated:
        gx = x + tbl["thumb"] / 2 + span * min(max(p.eff_norm, 0.0), 1.0)
        cy = y + h / 2
        k.dl.add_rect_filled(imgui.ImVec2(gx - 1.5, cy - 5), imgui.ImVec2(gx + 1.5, cy + 5),
                             ui.u32(ui.GHOST), 1.5)
        panel.ghosts += 1
    if changed:
        p.set_value(nv)
    return changed


def _actions(panel, k, x: float, y: float, w: float, h: float) -> None:
    """Reset view, then its key and the pad's click beside it while they fit."""
    B, T, C, D = (ui_kit.mod(n) for n in ("box", "tokens", "comp_button", "draw"))
    p = panel.reg[RESET]
    bw, bh = C.button_size(BUTTON_SIZE, p.label, k.faces)
    tbl = k.anim.store.setdefault("kbd_tbl", {}).get(k.theme_name)
    if tbl is None:
        tbl = k.anim.store["kbd_tbl"][k.theme_name] = T.kbd_table(k.theme_name)
    kw, kh = D.kbd_size(HINT_KEY, k.faces, tbl)
    imgui.push_font(ui._FONTS["ui"], ui.FONT_BASE)
    hw = imgui.calc_text_size(HINT).x
    imgui.pop_font()
    button, key, hint = B.flex(
        B.Rect(x, y, w, h),
        [B.Item(w=bw, h=bh, shrink=0), B.Item(w=kw, h=kh, shrink=0), B.Item(w=hw, shrink=0)],
        direction="row", gap=T.SPACE[2], align="center")
    st = C.ui_button(k, RESET, button.x, button.y, button.w, button.h, p.label,
                     variant="secondary", size=BUTTON_SIZE,
                     disabled=getattr(panel, "_picking", False))
    panel._tip(p)
    panel._ctx(p)
    panel._learn_frame(p)
    if st.clicked:
        p.toggle()
    if hint.x + hint.w <= x + w:              # the words only where they fit the pane
        D.kbd(k.dl, key.x, key.y, HINT_KEY, k.faces, k.theme, tbl)
        _text(k.dl, hint.x, y, h, HINT, "ui", ui.FONT_BASE, ui.FAINT)
    elif key.x + key.w <= x + w:
        D.kbd(k.dl, key.x, key.y, HINT_KEY, k.faces, k.theme, tbl)
