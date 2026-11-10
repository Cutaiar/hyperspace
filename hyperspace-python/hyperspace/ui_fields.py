"""A param as a kit control (`ui_kit`, tools/dkit): one function per kind of
param, each drawn into a rectangle a kit layout gave it, each keeping
everything a param widget is on the panel.

The rule every one of them keeps, and the reason the port is cheap: the
kit control's real imgui item — the slider_float, the invisible_button —
is the LAST item when the kit returns, and every panel behaviour on a param
widget acts on the last item. So the right-click menu (`Panel._ctx`, and
`_ctx_label` on a label), Learn's red frame (`_learn_frame`), the tooltip
(`_tip`, `_fine_tip`), ⇧-drag fine mode (`_fine`, `_fine_throw`), the
modulation dot (`_mod_dot`) and a picked desk control (`_ctx_pick`, through
`_ctx`) are the panel's own calls, made here exactly as `Panel._slider`,
`_check`, `_combo` and `_button` make them. Each control carries
``##<param id>``, so the panel driver (`tests/ui_driver.py`) finds it.

- `slider`: a CONTINUOUS param (log, tapered, integer, bipolar) — a header
  (label, readout) over the kit's slider; `slider_h` is its height;
- `switch`: a TOGGLE — its label, the kit's Switch at the row's end;
- `select`: an ENUM — the kit's Select, its rows the param's names;
- `toggles`: TOGGLEs side by side as one joined group, lit while on;
- `button`: a TRIGGER — the kit's Button.

A rectangle is (x, y, w, h) in screen pixels, as `ui_kit.block` gives one.
"""

from __future__ import annotations

from imgui_bundle import imgui

from . import ui, ui_kit, undo
from .params import Kind

SLIDER_H = 20.0          # a slider's row: the 12 px thumb, its ring, and room to press
ROW_H = 28.0             # a switch's, a select's, a button's row: the panel's frame height
SELECT_SIZE = "sm"       # 28 tall, as ROW_H
BUTTON_SIZE = "sm"
NOTCH = 3.0              # px a detent's tick stands off the track, above and below


def _m(name: str):
    return ui_kit._MODS.get(name) or ui_kit.mod(name)


def _dim(panel) -> bool:
    """A desk control is picked: every body but ROUTING's is disabled
    (`ui_pane._body`), and the kit draws its own disabled look."""
    return bool(getattr(panel, "_picking", False))


def head_h() -> float:
    """A field header's height: the taller of the label's line and the readout's."""
    out = 0.0
    for font, size in (("micro", ui.FONT_MICRO), ("num", ui.FONT_NUM)):
        imgui.push_font(ui._FONTS[font], size)
        out = max(out, imgui.get_text_line_height())
        imgui.pop_font()
    return out


def slider_h() -> float:
    """A slider field's height: its header, a step, its slider."""
    return head_h() + _m("tokens").SPACE[1] + SLIDER_H


def text(dl, x: float, y: float, h: float, s: str, font: str, size: float, col) -> float:
    """`s` in one of the panel's faces, centred on a row `h` tall; its width."""
    imgui.push_font(ui._FONTS[font], size)
    try:
        ext = imgui.calc_text_size(s)
        dl.add_text(imgui.ImVec2(round(x), round(y + (h - ext.y) / 2)), ui.u32(col), s)
        return ext.x
    finally:
        imgui.pop_font()


def _label_hit(panel, a, x: float, y: float, w: float, h: float) -> None:
    """The label as an item, so a right-click on it opens the param's menu
    (`Panel._ctx_label`, as `_label_cell`'s does)."""
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
    imgui.dummy(imgui.ImVec2(max(w, 1.0), max(h, 1.0)))
    panel._ctx_label(a)


# ---------------------------------------------------------------- slider

def slider(panel, k, pid: str, rect, label: str | None = None, *,
           head: bool = True) -> bool:
    """A CONTINUOUS param in `rect`: with `head` a header — its label (DIM,
    the label face, cut to fit) and readout (the readout face, `base →
    effective` in red while a lane rides it) — over the kit's slider; without,
    the slider alone, centred. A taper slides over its detents, with a tick
    at unity (`Panel._fader`'s notch); an integer over whole steps; a log
    range logarithmically, so Ctrl+click types a value. True when written."""
    B, T = _m("box"), _m("tokens")
    x, y, w, h = rect
    a = panel.reg[pid]
    p = panel._real(a)
    if head:
        hh = head_h()
        _head(panel, k, a, p, x, y, w, hh, label)
        sy = y + hh + T.SPACE[1]
    else:
        sy = y + (h - SLIDER_H) / 2
    return _slider(panel, k, a, p, x, sy, w, SLIDER_H)


def readout(label: str, value: str) -> str:
    """`value` without the words that repeat `label`: a param whose readout
    names itself for the stock slider's inside ("points 1.00", "12
    instance(s)") reads "1.00", "12" under a header that already says
    POINTS, INSTANCES. A word repeats the label when it shares its first
    four letters with one of the label's words; nothing left, `value` as
    it was."""
    words = {w.lower()[:4] for w in label.split() if len(w) >= 4}
    keep = [t for t in value.split(" ")
            if not (len(t) >= 4 and "".join(c for c in t.lower() if c.isalpha())[:4] in words)]
    out = " ".join(keep).strip()
    return out or value


def _head(panel, k, a, p, x, y, w, h, label) -> None:
    B, T = _m("box"), _m("tokens")
    value = panel._mod_text(p) if p.modulated else p.text()
    value = readout(a.label if label is None else label, value)
    tw = ui._readout_width(value)
    lab, val = B.flex(B.Rect(x, y, w, h), [B.Item(grow=1), B.Item(w=tw, shrink=0)],
                      direction="row", gap=T.SPACE[2])
    words = ui.fit_micro(a.label if label is None else label, lab.w)
    text(k.dl, lab.x, y, h, words, "micro", ui.FONT_MICRO, ui.DIM)
    text(k.dl, val.x, y, h, value, "num", ui.FONT_NUM, ui.RED if p.modulated else ui.TEXT)
    _label_hit(panel, a, lab.x, y, lab.w, h)


GRAB_PAD = 2.0            # px imgui's slider keeps between its frame and its grab, each end


def _value_box(k, x, y, w, h, frac, origin, words, font, size, col) -> None:
    """A slider too short to read as a track, drawn as a value box: the
    panel's frame grey, the value's words centred, and a thin bar along its
    foot from `origin` to `frac` in the one red — where the value sits."""
    dl = k.dl
    r = ui.ROUND
    dl.add_rect_filled(imgui.ImVec2(x, y), imgui.ImVec2(x + w, y + h),
                       imgui.get_color_u32(imgui.Col_.frame_bg), r)
    a, b = sorted((min(max(origin, 0.0), 1.0), min(max(frac, 0.0), 1.0)))
    inset = r / 2
    bx0, bx1 = x + inset + (w - 2 * inset) * a, x + inset + (w - 2 * inset) * b
    if bx1 - bx0 >= 1.0:
        dl.add_rect_filled(imgui.ImVec2(bx0, y + h - 3), imgui.ImVec2(bx1, y + h - 1),
                           ui.u32(ui.RED), 1.0)
    imgui.push_font(ui._FONTS[font], size)
    shown = ui.fit_text(words, w - 2 * _m("tokens").SPACE[1])
    tw = imgui.calc_text_size(shown).x
    imgui.pop_font()
    text(dl, x + (w - tw) / 2, y - 1, h, shown, font, size, col)


def _slider(panel, k, a, p, x, y, w, h, box=None) -> bool:
    """The kit slider for param `a` (reading and writing `p`) in (x, y, w, h);
    `box`: (words, colour) to draw it as a value box (`_value_box`) rather
    than a track."""
    I, tbl = _m("interact"), k.slider_tbl
    thumb = tbl["thumb"]
    span = w - thumb
    t0 = p.norm
    if box is not None:
        _value_box(k, x, y, w, h, t0, panel._origin(p), box[0], "num", ui.FONT_NUM, box[1])
    shown = (panel._mod_text(p) if p.modulated else p.text()).replace("%", "%%")
    if p.taper is not None:                 # the detents: the stock slider over positions
        steps = p.steps
        value, lo, hi, flags = float(p.position()), 0.0, float(steps), 0
    elif p.integer:
        steps = int(p.hi) - int(p.lo)
        value, lo, hi, flags = float(p.base), float(p.lo), float(p.hi), 0
    else:
        steps = 0
        value, lo, hi = float(p.base), float(p.lo), float(p.hi)
        flags = imgui.SliderFlags_.logarithmic if p.log else 0
    # the stock slider as tall as the row, its grab the kit thumb: a press
    # lands where the thumb is drawn (to imgui's 2 px grab padding)
    imgui.push_style_var(imgui.StyleVar_.frame_padding, imgui.ImVec2(0, (h - ui.FONT_NUM) / 2))
    imgui.push_style_var(imgui.StyleVar_.grab_min_size, thumb)
    imgui.push_font(ui._FONTS["num"], ui.FONT_NUM)
    try:
        changed, nv = I.slider(k, a.id, x, y, w, h, value, lo, hi, fine=False,
                               disabled=_dim(panel), fmt=shown, flags=flags, frac=t0,
                               origin=panel._origin(p), draw=box is None)
    finally:
        imgui.pop_font()
        imgui.pop_style_var(2)
    # a ⇧-drag measured over imgui's own throw — its grab padding inside the
    # frame at each end — so a fine drag is a tenth of a plain one exactly,
    # whatever the track's width (on a short one the 4 px were 20 %)
    own, t = panel._fine(p, t0, x + thumb / 2 + GRAB_PAD, span - 2 * GRAB_PAD)
    if own:
        changed = t is not None             # a frame the mouse did not move writes nothing
        if changed:
            nv = round(t * steps) if p.taper is not None else p._value_of_norm(t)
    panel._fine_tip(a, p)
    panel._ctx(a)
    panel._learn_frame(a)
    cy = y + h / 2
    if box is not None:
        pass                                # (a value box: no notch, no ghost on a track)
    elif p.taper is not None and p.taper.unity is not None and steps:
        nx = x + thumb / 2 + span * p.taper.unity / steps
        col = ui.u32(ui.FAINT)
        th = tbl["track_h"] / 2
        k.dl.add_line(imgui.ImVec2(nx, cy - th - NOTCH - 3), imgui.ImVec2(nx, cy - th - NOTCH), col, 1.5)
        k.dl.add_line(imgui.ImVec2(nx, cy + th + NOTCH), imgui.ImVec2(nx, cy + th + NOTCH + 3), col, 1.5)
    if p.modulated:                         # the effective value: a white tick on the track
        gx = x + thumb / 2 + span * min(max(p.eff_norm, 0.0), 1.0)
        k.dl.add_rect_filled(imgui.ImVec2(gx - 1.5, cy - 5), imgui.ImVec2(gx + 1.5, cy + 5),
                             ui.u32(ui.GHOST), 1.5)
        panel.ghosts += 1
    if not changed:
        return False
    undo.by_hand(True)                      # (typed into it, or dragged: row 757)
    if p.taper is not None:
        pos = int(round(nv))
        if pos == p.position():
            return False
        p.set_position(pos)
    elif p.integer:
        p.set_value(int(round(nv)))
    else:
        p.set_value(nv)
    return True


# ---------------------------------------------------------------- toggles

def switch_w() -> float:
    return _m("tokens").SWITCH_SIZES["default"][0]


def switch(panel, k, pid: str, rect, label: str | None = None) -> bool:
    """A TOGGLE in `rect`: its label (the panel's word face) and the kit's
    Switch at the row's end. A click on either flips it. True when flipped."""
    T = _m("tokens")
    x, y, w, h = rect
    a = panel.reg[pid]
    p = panel._real(a)
    sw, sh, _ = T.SWITCH_SIZES["default"]
    words = a.label if label is None else label
    imgui.push_font(ui._FONTS["ui"], ui.FONT_BASE)
    words = ui.fit_text(words, w - sw - T.SPACE[2])
    imgui.pop_font()
    text(k.dl, x, y, h, words, "ui", ui.FONT_BASE, ui.TEXT if p.base else ui.DIM)
    # the words take the click too, as a checkbox's label does (no id: the
    # switch is the param's one control the driver finds)
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
    word_hit = imgui.invisible_button(f"##words.{pid}", imgui.ImVec2(max(w - sw - T.SPACE[2], 1), h))
    panel._ctx_label(a)
    clicked, _on = _m("interact").switch(k, pid, x + w - sw, y + (h - sh) / 2, bool(p.base),
                                          disabled=_dim(panel))
    panel._tip(a)
    panel._ctx(a)
    panel._learn_frame(a)
    panel._mod_dot(p)
    if (clicked or word_hit) and not _dim(panel):
        p.set(not bool(p.base))
        return True
    return False


def toggles(panel, k, pids, labels, rect, inert=()) -> str | None:
    """TOGGLEs side by side as one joined group (`comp_button.button_group`),
    each lit — the one red — while on, the group sharing `rect`'s width
    evenly. `inert`: ids drawn at a third of their strength (still
    switchable). The id flipped, or None."""
    C = _m("comp_button")
    x, y, w, h = rect
    n = len(pids)
    each = w / n
    rects = [(x + i * each, y, each, h) for i in range(n)]
    joins = C.button_group(rects, "horizontal")
    hit = None
    for pid, words, (rx, ry, rw, rh), j in zip(pids, labels, rects, joins):
        a = panel.reg[pid]
        p = panel._real(a)
        on = bool(p.base)
        dull = pid in inert
        if dull:
            imgui.push_style_var(imgui.StyleVar_.alpha, 0.35)
        st = C.ui_button(k, pid, rx, ry, rw, rh, words, variant="default" if on else "outline",
                         size=BUTTON_SIZE, join=j, in_group=True, disabled=_dim(panel))
        if dull:
            imgui.pop_style_var()
        panel._tip(a)
        panel._ctx(a)
        panel._learn_frame(a)
        panel._mod_dot(p)
        if st.clicked:
            p.toggle()
            hit = pid
    return hit


# ---------------------------------------------------------------- enums, triggers

def select(panel, k, pid: str, rect, tip: str | None = None) -> bool:
    """An ENUM in `rect`: the kit's Select, a row per name, the current one
    checked. True when another is chosen."""
    M = _m("menu")
    x, y, w, h = rect
    a = panel.reg[pid]
    p = panel._real(a)
    names = p.names
    cur = int(p.base)
    items = [M.Item(id=str(i), label=n, checked=i == cur) for i, n in enumerate(names)]
    chosen, _open = _m("interact").select(
        k, pid, x, y + (h - ROW_H) / 2, w, names[cur] if 0 <= cur < len(names) else "",
        items, size=SELECT_SIZE, disabled=_dim(panel))
    # the trigger's item is the select's hit, submitted first: ask for it again
    panel._tip(a, tip)
    panel._ctx(a)
    panel._learn_frame(a)
    panel._mod_dot(p)
    if chosen is not None and int(chosen) != cur:
        p.set(int(chosen))
        return True
    return False


def button_w(k, words: str) -> float:
    """A kit Button's width for `words`: measured once per string and kept
    (`anim.store`; a strip asks for its four every frame)."""
    cache = k.anim.store.setdefault("button_w", {})
    got = cache.get(words)
    if got is None:
        got = cache[words] = _m("comp_button").button_size(BUTTON_SIZE, words, k.faces)[0]
    return got


def button(panel, k, pid: str, rect, label: str | None = None, *,
           variant: str = "secondary") -> bool:
    """A TRIGGER (or a toggle flipped by a press) as the kit's Button in
    `rect`, as wide as its words unless `rect` is narrower. True when pressed."""
    C = _m("comp_button")
    x, y, w, h = rect
    a = panel.reg[pid]
    words = a.label if label is None else label
    bw = min(button_w(k, words), w)
    bh = C.BUTTON_SIZES[BUTTON_SIZE]["h"]
    st = C.ui_button(k, pid, x, y + (h - bh) / 2, bw, bh, words, variant=variant,
                     size=BUTTON_SIZE, disabled=_dim(panel))
    panel._tip(a)
    panel._ctx(a)
    panel._learn_frame(a)
    if st.clicked:
        a.toggle()
        return True
    return False


def any_param(panel, k, pid: str, rect) -> bool:
    """`pid` drawn as its kind asks: a slider field, a switch, a select or
    a button."""
    kind = panel._real(panel.reg[pid]).kind
    if kind is Kind.CONTINUOUS:
        return slider(panel, k, pid, rect)
    if kind is Kind.TOGGLE:
        return switch(panel, k, pid, rect)
    if kind is Kind.ENUM:
        return select(panel, k, pid, rect)
    return button(panel, k, pid, rect)


def height(panel, pid: str) -> float:
    """The row `any_param` wants for `pid`."""
    return slider_h() if panel._real(panel.reg[pid]).kind is Kind.CONTINUOUS else ROW_H


# ---------------------------------------------------------------- forms

def rows(w: float, spec, *, gap_x: float | None = None, gap_y: float | None = None
         ) -> tuple[dict, float]:
    """Lay a form out `w` wide from (0, 0): `spec` is its rows down, each a
    list of cells across — (key, height) or (key, height, grow) — sharing
    the row's width by their grow (1 each by default), `gap_x` apart; the
    rows `gap_y` apart, each as tall as its tallest cell. A row of one
    ``None`` is a further step of space (the gap between groups). Returns
    ({key: (x, y, w, h)}, the form's height). `box.flex` both ways, on
    `tokens.SPACE`'s steps."""
    B, T = _m("box"), _m("tokens")
    gx = T.SPACE[3] if gap_x is None else gap_x
    gy = T.SPACE[3] if gap_y is None else gap_y
    heights = [T.SPACE[1] if row == [None] else max(c[1] for c in row) for row in spec]
    total = sum(heights) + gy * max(len(spec) - 1, 0)
    bands = B.flex(B.Rect(0.0, 0.0, w, total), [B.Item(h=h, shrink=0) for h in heights],
                   direction="column", gap=gy)
    out = {}
    for row, band in zip(spec, bands):
        if row == [None]:
            continue
        cells = B.flex(band, [B.Item(grow=c[2] if len(c) > 2 else 1.0, h=c[1]) for c in row],
                       direction="row", gap=gx, align="start")
        for c, r in zip(row, cells):
            out[c[0]] = (r.x, r.y, r.w, c[1])
    return out, total


def form(panel, k, spec, draw_cell, **gaps) -> None:
    """A form at the window's cursor: `rows(spec)` laid out the content's
    width, `draw_cell(key, rect)` for each cell, then imgui's flow told the
    block's size (`ui_kit.end_block`)."""
    x, y, w, _ = ui_kit.block(0.0)
    cells, h = rows(w, spec, **gaps)
    for key, (cx, cy, cw, ch) in cells.items():
        draw_cell(key, (x + cx, y + cy, cw, ch))
    ui_kit.end_block((x, y, w, h))


# ---------------------------------------------------------------- in imgui's flow
#
# The panel's own widget calls (`Panel._check`, `Panel._button`) drawn on the
# kit where they stand: at the cursor, exactly as wide and tall as the stock
# widget they replace, so a section's same_line / `ui.beside` arithmetic —
# written against `ui.check_w`, `ui.button_w`, `ui.chip_w` — holds unchanged,
# and every section that calls them is on the kit without its layout being
# touched.

def inline_check(panel, pid: str, label: str | None = None) -> bool:
    """`Panel._check` on the kit: the kit's small Switch centred in the box
    a stock checkbox has, its words after it, the whole of it `ui.check_w`
    wide and one frame tall — the stock checkbox's footprint, so a row of
    them keeps its arithmetic.

    One hit over the whole row, as a checkbox has, and NOT the kit Switch's
    own: shadcn stretches a switch's target 11 px past each end
    (`interact.switch`, `rect.stretched_hit`), which in a row of checks
    reaches into the next one's words and takes its clicks. The words are a
    real text item (the panel's word face; TEXT while on, DIM off), drawn
    after the hit, so whatever reads a section's text reads them. True
    when flipped."""
    k = ui_kit.begin(panel)
    D = _m("draw")
    a = panel.reg[pid]
    p = panel._real(a)
    on = bool(p.base)
    words = (a.label if label is None else label).split("##")[0]
    fh = imgui.get_frame_height()
    w = ui.check_w(words)
    x, y, _, _ = ui_kit.block(fh)
    sw, sh, _ = _m("tokens").SWITCH_SIZES["sm"]
    dim = _dim(panel)
    with _m("uictx").chrome(k):
        st = k.hit(pid, x, y, w, fh)
        panel._tip(a)
        panel._ctx(a)
        panel._learn_frame(a)
        panel._mod_dot(p)
        on_f = k.anim.to(f"{pid}:on", 1.0 if on else 0.0)
        D.switch(k.dl, x + (fh - sw) / 2, y + (fh - sh) / 2, on_f, k.theme, k.switch_tbl,
                 size="sm", focus_f=k.focus_f(pid, st.focused, disabled=dim), disabled=dim)
        if words:
            gap = imgui.get_style().item_inner_spacing.x
            imgui.set_cursor_screen_pos(imgui.ImVec2(x + fh + gap, y))
            imgui.align_text_to_frame_padding()
            imgui.text_colored(ui.TEXT if on else ui.DIM, words)
    ui_kit.end_block((x, y, w, fh))
    if st.clicked and not dim:
        p.set(not on)
        return True
    return False


def inline_button(panel, pid: str, label: str | None = None, small: bool = False) -> bool:
    """`Panel._button` on the kit: the kit's Button where the stock button (or,
    `small`, the chip) would be, as wide as it — the stock words' width and
    padding, so a row laid out with `ui.button_w` / `ui.chip_w` holds — and
    as tall. A press fires a trigger, flips a toggle. True when pressed."""
    k = ui_kit.begin(panel)
    a = panel.reg[pid]
    words = (a.label if label is None else label).split("##")[0]
    if small:
        w = ui.chip_w(words)
        h = imgui.get_text_line_height() + 2 * ui.CHIP_PAD.y
        size, variant = "xs", "secondary"
    else:
        w = imgui.calc_text_size(words).x + 2 * imgui.get_style().frame_padding.x
        h = imgui.get_frame_height()
        size, variant = BUTTON_SIZE, "secondary"
    x, y, _, _ = ui_kit.block(h)
    with _m("uictx").chrome(k):
        st = _m("comp_button").ui_button(k, pid, x, y, w, h, words, variant=variant, size=size,
                                         disabled=_dim(panel))
    panel._tip(a)
    panel._ctx(a)
    panel._learn_frame(a)
    ui_kit.end_block((x, y, w, h))
    if st.clicked:
        a.toggle()
        return True
    return False


def inline_fader(panel, pid: str) -> bool:
    """`Panel._fader` on the kit: the slider field (`slider`) the full width
    at the cursor — its label and readout over the kit's track, a tick at
    a taper's unity detent. True when written."""
    k = ui_kit.begin(panel)
    x, y, w, _ = ui_kit.block(0.0)
    h = slider_h()
    with _m("uictx").chrome(k):
        changed = slider(panel, k, pid, (x, y, w, h))
    ui_kit.end_block((x, y, w, h))
    return changed


SLIDER_TRACK_MIN = 60.0   # px: under this a track beside its readout is a value box (ui.SLIDER_MIN)


def _widest(panel, a, p, now: str) -> float:
    """The room an inline slider keeps for its readout: the widest it shows
    at either end of its range — the layout must not change shape while a
    drag moves the value under the pointer ("200 ms" to "1584 ms" turned a
    track into a value box mid-drag) — or now, while a lane makes it wider."""
    cache = panel.__dict__.setdefault("_kit_widest", {})
    w = cache.get(a.id)
    if w is None:
        try:
            ends = [readout(a.label, p.fmt(v)) for v in (p.lo, p.hi)]
        except Exception:  # noqa: BLE001 — a format that cannot say an end: today's words
            ends = [now]
        w = cache[a.id] = max(ui._readout_width(t) for t in ends)
    return max(w, ui._readout_width(now)) if p.modulated else w


def inline_slider(panel, pid: str, width: float = -1) -> bool:
    """`Panel._slider` on the kit, in the room the stock one had (`width`:
    -1 the rest of the line, under 0 that much short of it): the kit's track,
    its readout at the row's end in the readout face — the value alone, the
    label beside it already says what (`readout`); red while a lane rides
    it. One frame tall, so a row of them keeps its height. True when
    written."""
    k = ui_kit.begin(panel)
    a = panel.reg[pid]
    p = panel._real(a)
    avail = imgui.get_content_region_avail().x
    w = avail if width == -1 else (avail + width if width < 0 else width)
    fh = imgui.get_frame_height()
    x, y, _, _ = ui_kit.block(fh)
    value = readout(a.label, panel._mod_text(p) if p.modulated else p.text())
    rw = _widest(panel, a, p, value)
    gap = _m("tokens").SPACE[2]
    col = ui.RED if p.modulated else ui.TEXT
    beside = w - rw - gap >= SLIDER_TRACK_MIN
    track = w - rw - gap if beside else w
    with _m("uictx").chrome(k):
        # the hit is the whole row, as the stock slider's frame was: the
        # track is centred in it, and a row of controls keeps one top. Too
        # narrow for a readable track beside its readout (a cell of the 240 px
        # pane, the head's seconds): a value box, the whole room
        changed = _slider(panel, k, a, p, x, y, track, fh,
                          box=None if beside else (value, col))
        if beside:
            text(k.dl, x + track + gap, y, fh, value, "num", ui.FONT_NUM, col)
    ui_kit.end_block((x, y, w, fh))
    return changed


SELECT_ROWS_MAX = 12      # an enum longer than this keeps imgui's combo: the kit's menu has no scroll yet


def inline_select(panel, pid: str, width: float = -1, tip: str | None = None) -> bool | None:
    """`Panel._combo` on the kit, in the room the stock combo had (`width`
    as `inline_slider`'s): the kit's Select, one frame tall. None — draw
    the stock combo — for an enum of more than `SELECT_ROWS_MAX` names,
    which the kit's menu cannot scroll through (its HANDOFF: `menu.popup`
    has no height clamp). Else True when another name is chosen."""
    a = panel.reg[pid]
    p = panel._real(a)
    if len(p.names) > SELECT_ROWS_MAX:
        return None
    k = ui_kit.begin(panel)
    avail = imgui.get_content_region_avail().x
    w = avail if width == -1 else (avail + width if width < 0 else width)
    fh = imgui.get_frame_height()
    x, y, _, _ = ui_kit.block(fh)
    with _m("uictx").chrome(k):
        changed = select(panel, k, pid, (x, y, w, fh), tip=tip)
    ui_kit.end_block((x, y, w, fh))
    return changed


# ---------------------------------------------------------------- chips

def _chip_colours(k, variant: str) -> tuple:
    """(rest, hover, ring) of a kit Button variant's fill, as imgui colours —
    resolved once per variant and kept (`anim.store`): a chip is drawn ~70
    times a frame, and the Button's general path resolved and mixed five
    tokens for each (tools/profile_kit.py)."""
    cache = k.anim.store.setdefault("chip_cols", {})
    got = cache.get(variant)
    if got is None:
        T = _m("tokens")
        v = _m("comp_button")._table_for(k)[variant]
        got = cache[variant] = tuple(imgui.ImVec4(*T.rgba(tok, al, theme=k.theme))
                                     for tok, al in (v["fill"], v["hover_fill"], v["ring"]))
    return got


def _chip_chrome(k, dl, x, y, w, h, variant, hot, down, focus, dim, r) -> None:
    """The kit Button's chrome for a chip, lean: what `comp_button.button`
    paints for a variant with a transparent border — the fill inset by that
    border (`bg-clip-padding`), the hover tint, the press's 1 px nudge, the
    focus ring outside the box, half strength disabled — without its
    general path (joins, borders, glyphs), which a chip never uses."""
    C, D = _m("comp_button"), _m("draw")
    rest, hover, ring = _chip_colours(k, variant)
    t = 0.0 if dim else hot
    a = 0.5 if dim else 1.0
    fill = imgui.ImVec4(rest.x + (hover.x - rest.x) * t, rest.y + (hover.y - rest.y) * t,
                        rest.z + (hover.z - rest.z) * t, (rest.w + (hover.w - rest.w) * t) * a)
    by = round(y + down * C.NUDGE)
    bx, bw, bh = round(x), round(w), round(h)
    if focus > 0.01 and not dim:
        D.ring(dl, bx, by, bw, bh, (ring.x, ring.y, ring.z, ring.w * focus), r, _m("tokens").RING_W)
    b = C.BORDER_W
    dl.add_rect_filled(imgui.ImVec2(bx + b, by + b), imgui.ImVec2(bx + bw - b, by + bh - b),
                       imgui.color_convert_float4_to_u32(fill), max(r - b, 0.0))


def chip(label: str, size=None, lit: bool = False, color=None, *, pad=None,
         pill: bool = True, icon: str | None = None, variant: str | None = None,
         reveal: float = 1.0) -> bool:
    """`ui.chip` / `ui.lit_chip` on the kit — and, with `pill` off and its
    own `pad`, `ui.button` / `ui.small_button` / `ui.arrow_button`: the kit's
    Button chrome at the stock widget's size (its words and `pad`, by
    default `ui.CHIP_PAD`; or `size`), lit solid in the one red; the words
    in the panel's own face through imgui's RenderText — TEXT, or `color`
    (an unlit `lit_chip`'s DIM) — or a Lucide `icon` in their place.

    The hit is an `invisible_button` with the widget's own label, so its
    imgui id is the stock one's exactly (the label's hash), and the panel
    driver finds it by the same words and id. Disabled — inside
    `begin_disabled`, or drawn at a reduced style alpha as an inert key is —
    it dims as the kit's disabled Button does. `variant` overrides the kit
    Button variant (a row's actions are ``ghost``); `reveal` (0..1) fades the
    whole chip — a row action shown on the row's hover (`list_row`) — while
    its hit stays where it is, whole, so a pointer can reach it and the
    driver can click it. True when clicked."""
    k = ui_kit.begin(None)
    D = _m("draw")
    pad = ui.CHIP_PAD if pad is None else pad
    words = "" if icon else label.split("##")[0]
    sx = size.x if size is not None else 0.0
    sy = size.y if size is not None else 0.0
    line = imgui.get_text_line_height()
    w = sx if sx > 0 else (line + 2 * pad.y if icon else imgui.calc_text_size(words).x + 2 * pad.x)
    h = sy if sy > 0 else line + 2 * pad.y
    p = imgui.get_cursor_screen_pos()
    x, y = p.x, p.y
    dl = imgui.get_window_draw_list()
    hit = imgui.invisible_button(label, imgui.ImVec2(max(w, 1.0), max(h, 1.0)))
    key = imgui.get_item_id()
    dim = imgui.get_style().alpha < 0.99
    anim = k.anim
    hot = anim.to(f"chip:{key}:hot", 1.0 if imgui.is_item_hovered() and not dim else 0.0)
    down = anim.to(f"chip:{key}:down", 1.0 if imgui.is_item_active() else 0.0)
    focus = k.focus_f(f"chip:{key}", imgui.is_item_focused(), disabled=dim)
    reveal = max(reveal, hot, focus)            # its own hover or focus shows it whole
    if reveal > 0.01:
        _chip_chrome(k, dl, x, y, w, h, variant or ("default" if lit else "secondary"),
                     hot, down, focus, dim, h / 2 if pill else min(ui.ROUND, h / 2))
    # lit: white on the red; an unlit lit_chip: its colour; anything else: TEXT
    ink = imgui.ImVec4(1, 1, 1, 1) if lit else (color if color is not None else ui.TEXT)
    ink = imgui.ImVec4(ink.x, ink.y, ink.z, ink.w * reveal)
    if icon:
        g = min(16.0, h - 6.0)
        if reveal > 0.01:
            D.icon(dl, icon, x + (w - g) / 2, y + (h - g) / 2, g,
                   (ink.x, ink.y, ink.z, ink.w * (0.5 if dim else 1.0)))
    elif words and reveal > 0.01:
        tw = imgui.calc_text_size(words).x
        # through imgui's own RenderText, as a stock button draws its words:
        # no item, and nothing a reader of the draw list's add_text calls
        # (the desk's glyph tests) would take for a drawing of its own
        imgui.push_style_color(imgui.Col_.text, ink)
        imgui.internal.render_text(imgui.ImVec2(round(x + (w - tw) / 2), round(y + (h - line) / 2)),
                                   words)
        imgui.pop_style_color()
    return bool(hit)


def check(label: str, value: bool) -> tuple[bool, bool]:
    """`imgui.checkbox` on the kit, for a check with no param behind it (a
    route's on, a display's flips): the same contract — `(clicked, value)`
    — the same footprint (`ui.check_w`, one frame tall) and the same id
    (an `invisible_button` with the check's own label), the kit's small
    Switch in the box and the words after it through imgui's RenderText.
    Disabled (`begin_disabled`) it dims and takes no click, as imgui's."""
    k = ui_kit.begin(None)
    D = _m("draw")
    words = label.split("##")[0]
    fh = imgui.get_frame_height()
    w = ui.check_w(words)
    p = imgui.get_cursor_screen_pos()
    x, y = p.x, p.y
    k.dl = imgui.get_window_draw_list()
    sw, sh, _ = _m("tokens").SWITCH_SIZES["sm"]
    with _m("uictx").chrome(k):
        hit = imgui.invisible_button(label, imgui.ImVec2(w, fh))
        key = f"check:{imgui.get_item_id()}"
        dim = imgui.get_style().alpha < 0.99
        out = (not value) if hit else bool(value)
        on_f = k.anim.to(f"{key}:on", 1.0 if out else 0.0)
        D.switch(k.dl, x + (fh - sw) / 2, y + (fh - sh) / 2, on_f, k.theme, k.switch_tbl,
                 size="sm", focus_f=k.focus_f(key, imgui.is_item_focused(), disabled=dim),
                 disabled=dim)
    if words:
        gap = imgui.get_style().item_inner_spacing.x
        imgui.push_style_color(imgui.Col_.text, ui.TEXT if out else ui.DIM)
        imgui.internal.render_text(
            imgui.ImVec2(round(x + fh + gap), round(y + (fh - imgui.get_text_line_height()) / 2)),
            words)
        imgui.pop_style_color()
    return bool(hit), out


# ---------------------------------------------------------------- text fields

def text_field(label: str, hint: str, text: str, flags: int = 0) -> tuple[bool, str]:
    """`imgui.input_text_with_hint` on the kit: the kit's Input (its frame,
    focus ring, placeholder) over imgui's own `input_text`, which keeps the
    caret, the selection and the clipboard — same contract `(changed,
    text)`, same `flags` (Enter-returns-true, select-all…), same id (the
    label's ``##`` part), in the width the caller set (`calc_item_width`,
    which honours `set_next_item_width`) and one frame tall."""
    k = ui_kit.begin(None)
    key = label.split("##", 1)[1]
    w = imgui.calc_item_width()
    fh = imgui.get_frame_height()
    p = imgui.get_cursor_screen_pos()
    k.dl = imgui.get_window_draw_list()
    with _m("uictx").chrome(k):
        changed, out = _m("interact").text_input(k, key, p.x, p.y, w, text, h=fh,
                                                 placeholder=hint, flags=flags)
    ui_kit.end_block((p.x, p.y, w, fh))
    return changed, out


def inline_raw(panel, key: str, value: float, lo: float, hi: float, fmt: str, tip: str,
               width: float = -1, log: bool = False, dim: bool = False,
               num: bool = True) -> tuple[bool, float]:
    """`Panel._raw_slider` on the kit — a slider with no param behind it (a
    route's depth, GRAPH's backdrop) — in the room the stock one had: the
    kit's track, the readout (`fmt % value`, words and all) at the row's
    end, the panel's ⇧-drag fine mode, its tooltip and its undo report,
    exactly as `_raw_slider` makes them. `(changed, value)`."""
    import math
    k = ui_kit.begin(panel)
    I = _m("interact")
    value = float(value)
    log = log and lo > 0
    t0 = (math.log(max(value, lo) / lo) / math.log(hi / lo) if log
          else (value - lo) / ((hi - lo) or 1.0))
    origin = -lo / (hi - lo) if lo < 0 < hi else 0.0
    shown = fmt % value
    avail = imgui.get_content_region_avail().x
    w = avail if width == -1 else (avail + width if width < 0 else width)
    fh = imgui.get_frame_height()
    x, y, _, _ = ui_kit.block(fh)
    font, size = ("num", ui.FONT_NUM) if num else ("ui", ui.FONT_BASE)
    imgui.push_font(ui._FONTS[font], size)
    # the widest the readout gets, at either end: the layout holds still
    # through a drag (see `_widest`)
    rw = max(imgui.calc_text_size(fmt % v).x for v in (lo, hi))
    imgui.pop_font()
    gap = _m("tokens").SPACE[2]
    beside = w - rw - gap >= SLIDER_TRACK_MIN
    track = w - rw - gap if beside else w
    thumb = k.slider_tbl["thumb"]
    col = ui.DIM if dim else ui.TEXT
    if not beside:
        _value_box(k, x, y, w, fh, t0, origin, shown, font, size, col)
    imgui.push_style_var(imgui.StyleVar_.frame_padding, imgui.ImVec2(0, (fh - ui.FONT_NUM) / 2))
    imgui.push_style_var(imgui.StyleVar_.grab_min_size, thumb)
    imgui.push_font(ui._FONTS["num"], ui.FONT_NUM)
    try:
        with _m("uictx").chrome(k):
            changed, v = I.slider(k, key, x, y, track, fh, value, lo, hi, fine=False,
                                  fmt=shown.replace("%", "%%"),
                                  flags=imgui.SliderFlags_.logarithmic if log else 0,
                                  frac=min(max(t0, 0.0), 1.0), origin=origin, draw=beside)
    finally:
        imgui.pop_font()
        imgui.pop_style_var(2)
    own, t = panel._fine_throw(t0, track - thumb - 2 * GRAB_PAD)   # imgui's own throw
    if own:
        changed = t is not None             # a frame the mouse did not move writes nothing
        v = value if t is None else lo * (hi / lo) ** t if log else lo + t * (hi - lo)
    shift = getattr(panel, "_shift", False)
    st = getattr(panel, "_fine_drag", None)
    hovered = imgui.is_item_hovered()
    if shift and not hovered and st is not None and st["id"] == imgui.get_item_id():
        ui.tooltip(ui.FINE_TIP)
    elif hovered:
        ui.tooltip(f"{ui.FINE_TIP}\n{tip}" if shift else tip)
    if beside:
        text(k.dl, x + track + gap, y, fh, shown, font, size, col)
    ui_kit.end_block((x, y, w, fh))
    if changed:
        undo.by_hand(True)                  # (typed into it: row 757)
    return changed, v
