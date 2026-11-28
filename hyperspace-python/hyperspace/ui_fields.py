"""A param as a kit control (`ui_kit`, hyperspace/dkit): one function per kind of
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
- `button`: a TRIGGER — the kit's Button;
- `pad`: two or three CONTINUOUS params as one XY pad (an XYZ volume with a
  third), a knob for each.

Every CONTINUOUS fader is drawn by its `Shape`: unipolar, filled
from the left; bipolar, filled from its zero with a detent there; unity, a
multiplier filled from its 1 with a detent there; and a stepped (integer)
one with a tick per step, thinned where they would crowd.

A rectangle is (x, y, w, h) in screen pixels, as `ui_kit.block` gives one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from imgui_bundle import imgui

from . import fx, ui, ui_kit, undo
from .params import Kind

SELECT_SIZE = "sm"       # 28 tall, as `ui.FIELD_ROW_H`
BUTTON_SIZE = "sm"


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
    return head_h() + _m("tokens").SPACE[1] + ui.FIELD_SLIDER_H


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
    T = _m("tokens")
    x, y, w, h = rect
    a = panel.reg[pid]
    p = panel._real(a)
    if head:
        hh = head_h()
        _head(panel, k, a, p, x, y, w, hh, label)
        sy = y + hh + T.SPACE[1]
    else:
        sy = y + (h - ui.FIELD_SLIDER_H) / 2
    return _slider(panel, k, a, p, x, sy, w, ui.FIELD_SLIDER_H)


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


def _box_words(k, x, y, w, h, words, font, size, col) -> None:
    """A value box's words (`interact.slider(box=True)` draws the box), in
    one of the panel's faces, centred, cut to fit."""
    imgui.push_font(ui._FONTS[font], size)
    shown = ui.fit_text(words, w - 2 * _m("tokens").SPACE[1])
    tw = imgui.calc_text_size(shown).x
    imgui.pop_font()
    text(k.dl, x + (w - tw) / 2, y - 1, h, shown, font, size, col)


def _slider(panel, k, a, p, x, y, w, h, box=None) -> bool:
    """The kit slider for param `a` (reading and writing `p`) in (x, y, w, h);
    `box`: (words, colour) to draw it as a value box (the kit's `slider(box=True)`) rather
    than a track."""
    I, tbl = _m("interact"), k.slider_tbl
    thumb = tbl["thumb"]
    span = w - thumb
    t0 = p.norm
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
    shape = shape_of(panel, p)
    # Ctrl+click: a typed value is not snapped. Last frame's answer, read
    # before the slider writes this frame's: Enter ends the text entry on
    # the frame the value lands
    typed = bool(k.texting.get(a.id, False))
    try:
        changed, nv = I.slider(k, a.id, x, y, w, h, value, lo, hi, fine=False,
                               disabled=_dim(panel), fmt=shown, flags=flags, frac=t0,
                               origin=shape.origin, box=box is not None)
    finally:
        imgui.pop_font()
        imgui.pop_style_var(2)
    if box is not None:
        _box_words(k, x, y, w, h, box[0], "num", ui.FONT_NUM, box[1])
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
    if box is None:                         # (a value box: no marks, no ghost on a track)
        marks(k.dl, shape, x + thumb / 2, span, cy, tbl["track_h"] / 2)
    if changed and not own and not typed:
        nv = _snap(p, shape, nv, span)      # a drag near a detent lands on it
    if p.modulated:                         # the effective value: a white tick on the track
        gx = x + thumb / 2 + span * min(max(p.eff_norm, 0.0), 1.0)
        k.dl.add_rect_filled(imgui.ImVec2(gx - 1.5, cy - 5), imgui.ImVec2(gx + 1.5, cy + 5),
                             ui.u32(ui.GHOST), 1.5)
        panel.ghosts += 1
    if not changed:
        return False
    undo.by_hand(True)                      # (typed into it, or dragged)
    if p.taper is not None:
        pos = round(nv)
        if pos == p.position():
            return False
        p.set_position(pos)
    elif p.integer:
        p.set_value(round(nv))
    else:
        p.set_value(nv)
    return True


# ---------------------------------------------------------------- shapes
#
# One abstraction draws every continuous fader: what kind of quantity it is
# says where its fill starts, where its detent is, and whether it has steps.

UNIPOLAR, BIPOLAR, UNITY = "unipolar", "bipolar", "unity"
TICK_STRIDES = (1, 2, 4, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000)


@dataclass(frozen=True)
class Shape:
    """How a CONTINUOUS param's fader is drawn.

    - `polarity`: UNIPOLAR (0..1-like, rests at 0 or the top: filled from
      the left), BIPOLAR (symmetric, neutral at 0: filled from the centre,
      a detent there) or UNITY (a multiplier neutral at 1: filled from 1, a
      detent there);
    - `origin`: the throw fraction the fill starts from;
    - `detent`: the throw fraction a drag snaps to (None: no detent), and
      `neutral` the value there — or, on a taper, the position;
    - `notches`: throw fractions marked above and below the track: the
      detent, and a taper's unity (an effect's speed at 1×);
    - `lo`, `hi`: a stepped (integer) param's whole range, ticked; 0, 0 for
      one without steps."""

    polarity: str = UNIPOLAR
    origin: float = 0.0
    detent: float | None = None
    neutral: float | None = None
    notches: tuple[float, ...] = ()
    lo: int = 0
    hi: int = 0


def _spec_of(panel, p):
    """The effect file's `@param` behind `p` (`fx.ParamSpec`), or None for
    a param that is not an effect's own uniform."""
    if not p.id.startswith("fx."):
        return None
    files = getattr(getattr(panel.reg, "fx_state", None), "files", None)
    got = fx.param_of(p.id, files) if files else None
    if got is None:
        return None
    spec, key = got
    return next((q for q in spec.params if q.key == key), None)


def polarity(lo: float, hi: float, log: bool, default: float | None, said: str = "") -> str:
    """A continuous range's class: `said` when the effect file says it
    (`bipolar` / `unipolar` on its `@param` line); else BIPOLAR for a range
    across 0 whose default is 0 (or unknown: a param that is no effect's
    has none to read); UNITY for
    a multiplier whose default is 1 in the middle of its range — linear
    about 1 (lo + hi = 2: Hue cycle's saturation) or log about 1 (lo · hi
    = 1: Kaleidoscope's zoom, Blocks' aspect); else UNIPOLAR."""
    if said in (BIPOLAR, UNIPOLAR):
        return said
    if not log and lo < 0 < hi and (default is None or default == 0):
        return BIPOLAR
    if default == 1 and lo < 1 < hi and (math.isclose(lo * hi, 1.0) if log
                                          else math.isclose(lo + hi, 2.0)):
        return UNITY
    return UNIPOLAR


def shape_of(panel, p) -> Shape:
    """`p`'s `Shape`, from its range, its taper, and — for an effect's own
    param — its file's `@param` line (its default and any marker)."""
    spec = _spec_of(panel, p)
    log = bool(p.log or (p.taper is not None and p.taper.log and p.lo > 0))
    pol = polarity(p.lo, p.hi, log, None if spec is None else spec.default,
                   "" if spec is None else spec.polarity)
    steps = p.taper.steps if p.taper is not None else 0
    lo = hi = 0
    if p.integer and p.taper is None:
        lo, hi = int(p.lo), int(p.hi)
    detent = neutral = None
    if pol != UNIPOLAR:
        neutral = 0.0 if pol == BIPOLAR else 1.0
        if not p.lo < neutral < p.hi:        # said bipolar on a range off zero: its middle
            neutral = (p.lo + p.hi) / 2
        try:
            detent = min(max(float(p._norm_of(neutral)), 0.0), 1.0)
        except Exception:  # noqa: BLE001 — a taper that cannot place it: no detent
            detent = None
        if detent is not None and steps:
            neutral = round(detent * steps)  # a taper snaps to a position
            detent = neutral / steps
        if detent is None:
            neutral = None
    notches = () if detent is None else (detent,)
    if p.taper is not None and p.taper.unity is not None and steps:
        u = p.taper.unity / steps
        if detent is None or abs(u - detent) > 1e-9:
            notches += (u,)
    return Shape(polarity=pol, origin=0.0 if detent is None else detent, detent=detent,
                 neutral=neutral, notches=notches, lo=lo, hi=hi)


def ticks(lo: int, hi: int, span: float, gap: float | None = None) -> list[float]:
    """The throw fractions of a stepped range's ticks, `lo`…`hi` over
    `span` px: one per step while they are `gap` (`ui.TICK_GAP`) apart or
    more; past that every 2nd, 4th, 5th, 10th … whole value — the first
    stride that leaves the gap — and both ends always, an inner tick too
    close to an end left out."""
    gap = ui.TICK_GAP if gap is None else gap
    n = hi - lo
    if n <= 0 or span <= 0:
        return []
    step = span / n
    stride = next((s for s in TICK_STRIDES if step * s >= gap), None)
    if stride is None:
        return [0.0, 1.0]
    first = -(-lo // stride) * stride       # the first multiple of the stride at or above lo
    inner = [(v - lo) / n for v in range(first, hi + 1, stride)
             if (v - lo) * step >= gap and (hi - v) * step >= gap]
    return [0.0, *inner, 1.0]


def marks(dl, shape: Shape, x0: float, span: float, cy: float, half: float) -> None:
    """A fader's marks over its throw (`x0`, `span` px; the track `half`
    tall each side of `cy`): a notch above and below at each of the
    shape's notches, and a stepped param's ticks under the track."""
    col = ui.u32(ui.FAINT)
    for t in shape.notches:
        nx = x0 + span * t
        dl.add_line(imgui.ImVec2(nx, cy - half - ui.FIELD_NOTCH - 3),
                    imgui.ImVec2(nx, cy - half - ui.FIELD_NOTCH), col, 1.5)
        dl.add_line(imgui.ImVec2(nx, cy + half + ui.FIELD_NOTCH),
                    imgui.ImVec2(nx, cy + half + ui.FIELD_NOTCH + 3), col, 1.5)
    if shape.hi > shape.lo:
        tc = ui.u32(ui.TICK)
        y0 = cy + half + ui.FIELD_NOTCH
        for t in ticks(shape.lo, shape.hi, span):
            tx = round(x0 + span * t) + 0.5
            dl.add_line(imgui.ImVec2(tx, y0), imgui.ImVec2(tx, y0 + ui.TICK_H), tc, 1.0)


def _snap(p, shape: Shape, nv: float, span: float) -> float:
    """A dragged fader's new value `nv` (a taper's position) moved onto
    the shape's detent when it lands within `ui.DETENT_PX` of it."""
    if shape.detent is None or shape.neutral is None or span <= 0:
        return nv
    try:
        t = nv / p.taper.steps if p.taper is not None else float(p._norm_of(nv))
    except Exception:  # noqa: BLE001 — a value the param cannot place
        return nv
    return shape.neutral if abs(t - shape.detent) * span <= ui.DETENT_PX else nv


# ---------------------------------------------------------------- pads
#
# An XY pad replaces a pair of sliders (`@pair` in an effect file), an XYZ
# volume a triple (`@volume`): a square a click or a drag sets X and Y on,
# the depth drawn as a halo about the dot, and a knob per axis. Each param
# keeps its own id, routes and learn: the knob is the param's control (its
# `##<id>`, menu, learn frame and tooltip); the square writes the bases, as
# a slider does. Modelled on the X/Y pads of Harmor and FL Studio.

PAD_LABEL_GAP = 4.0       # px between a knob and its words under it


def _write_norm(p, t: float) -> bool:
    """Write throw fraction `t` (0..1) to `p`'s base as its slider would:
    a taper's detent, an integer's whole value, else the range's own
    (log) mapping. True when the base moved."""
    t = min(max(float(t), 0.0), 1.0)
    if p.taper is not None:
        pos = round(t * p.taper.steps)
        if pos == p.position():
            return False
        p.set_position(pos)
        return True
    v = p._value_of_norm(t)
    if p.integer:
        v = round(v)
    if v == p.base:
        return False
    p.set_value(v)
    return True


def _held(panel, key: str, active: bool, start):
    """The unrounded state of the drag on item `key` (a pad's or a knob's):
    started from `start()` (the throw fractions it moves) on the frame it
    is pressed, kept while it is held, gone once it is let go — so a slow
    drag over a taper's detents adds up, rather than rounding back to the
    detent it began on every frame. None while `key` is not held."""
    store = panel.__dict__.setdefault("_kit_held", {})
    if not active:
        store.pop(key, None)
        return None
    got = store.get(key)
    if got is None:
        got = store[key] = {"t": list(start()), "fine": False}
    return got


def _knob_layout(w: float, n: int) -> tuple[float, bool]:
    """The square's side in a pad `w` wide with `n` knobs, and whether the
    knobs stand in a column beside it (else in a row under it)."""
    T = _m("tokens")
    if w - ui.KNOB_COL - T.SPACE[3] >= ui.PAD_MIN:
        return min(w - ui.KNOB_COL - T.SPACE[3], ui.PAD_MAX), True
    return min(w, ui.PAD_MAX), False


def knob_h() -> float:
    """A knob with its readout under it: two lines, its letter and value,
    and under them where a lane rides it the effective value (`knob`)."""
    return 2 * ui.KNOB_R + PAD_LABEL_GAP + 2 * head_h()


def pad_h(w: float, n: int) -> float:
    """A pad's height `w` wide with `n` (2 or 3) params: its header, the
    square, and the knobs under it where they do not fit beside."""
    T = _m("tokens")
    side, beside = _knob_layout(w, n)
    body = max(side, n * knob_h() + (n - 1) * T.SPACE[2]) if beside else side + T.SPACE[3] + knob_h()
    return head_h() + T.SPACE[1] + body


def pad(panel, k, pids, label: str, rect) -> dict:
    """Two params (an XY pad) or three (an XYZ volume) in `rect`: a header
    (the pad's label), the square, and a knob per axis, its value under it.
    Returns {param id: (its knob's min, max)} for a caller that frames them
    again (`ui_fx._relearn_frame`)."""
    T = _m("tokens")
    x, y, w, _h = rect
    acts = [panel.reg[pid] for pid in pids]
    ps = [panel._real(a) for a in acts]
    hh = head_h()
    # the head is the label alone: each knob says its value under it
    text(k.dl, x, y, hh, ui.fit_micro(label, w), "micro", ui.FONT_MICRO, ui.DIM)
    top = y + hh + T.SPACE[1]
    side, beside = _knob_layout(w, len(pids))
    _square(panel, k, acts, ps, x, top, side, label)
    out = {}
    kw = 2 * ui.KNOB_R
    for i, (a, p) in enumerate(zip(acts, ps)):
        if beside:
            kx = x + side + T.SPACE[3] + (w - side - T.SPACE[3] - kw) / 2
            ky = top + i * (knob_h() + T.SPACE[2])
        else:
            cell = w / len(pids)
            kx, ky = x + i * cell + (cell - kw) / 2, top + side + T.SPACE[3]
        room = ui.KNOB_COL if beside else w / len(pids)
        out[a.id] = knob(panel, k, a, p, kx, ky, "xyz"[i], room)   # its tooltip names it in full
    return out


def _square(panel, k, acts, ps, x, y, side, label) -> None:
    """The pad's square: X right, Y up, a click or a drag sets both bases
    at the pointer (⇧ held: a tenth of the drag, from where they were); the
    dot at the bases, the effective values a white dot while a lane rides
    either, and a volume's depth a halo about each."""
    dl = k.dl
    px, py = ps[0], ps[1]
    shapes = [shape_of(panel, p) for p in ps]
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
    imgui.invisible_button(f"##pad.{acts[0].id}", imgui.ImVec2(side, side))
    active, hovered = imgui.is_item_active(), imgui.is_item_hovered()
    if hovered:
        ui.tooltip(f"{label}: x {acts[0].label}, y {acts[1].label}"
                   + (f", z (the halo) {acts[2].label}" if len(acts) > 2 else "")
                   + f"\ndrag to set x and y together\n{ui.FINE_TIP}")
    st = _held(panel, f"pad.{acts[0].id}", active and not _dim(panel), lambda: (px.norm, py.norm))
    if st is not None:
        io = imgui.get_io()
        st["fine"] = st["fine"] or io.key_shift
        if st["fine"]:
            # relative from the moment ⇧ joins until the button comes up, a
            # tenth while it is held and whole once it is let go — never a
            # jump to the pointer (as `Panel._fine` keeps a slider's drag)
            rate = ui.FINE if io.key_shift else 1.0
            st["t"][0] = min(max(st["t"][0] + io.mouse_delta.x / side * rate, 0.0), 1.0)
            st["t"][1] = min(max(st["t"][1] - io.mouse_delta.y / side * rate, 0.0), 1.0)
        else:
            m = imgui.get_mouse_pos()
            st["t"] = [(m.x - x) / side, 1.0 - (m.y - y) / side]
        moved = _write_norm(px, st["t"][0])
        moved = _write_norm(py, st["t"][1]) or moved
        if moved:
            undo.by_hand(True)
    # the ground, a frame, the neutral cross and the quarters
    r0, r1 = imgui.ImVec2(x, y), imgui.ImVec2(x + side, y + side)
    dl.add_rect_filled(r0, r1, ui.u32(ui.PAD_BG), ui.ROUND)
    dl.add_rect(r0, r1, ui.u32(ui.RED if active else ui.LINE), ui.ROUND, 1.5 if active else 1.0)
    for q in (0.25, 0.75):
        c = ui.u32(ui.LINE)
        dl.add_line(imgui.ImVec2(x + side * q, y + 2), imgui.ImVec2(x + side * q, y + side - 2), c, 1.0)
        dl.add_line(imgui.ImVec2(x + 2, y + side * q), imgui.ImVec2(x + side - 2, y + side * q), c, 1.0)
    nx = shapes[0].detent if shapes[0].detent is not None else 0.5
    ny = shapes[1].detent if shapes[1].detent is not None else 0.5
    c = ui.u32(ui.FAINT)
    dl.add_line(imgui.ImVec2(x + side * nx, y + 2), imgui.ImVec2(x + side * nx, y + side - 2), c, 1.0)
    dl.add_line(imgui.ImVec2(x + 2, y + side * (1 - ny)), imgui.ImVec2(x + side - 2, y + side * (1 - ny)),
                c, 1.0)

    def at(tx, ty):
        return imgui.ImVec2(x + side * min(max(tx, 0.0), 1.0), y + side * (1 - min(max(ty, 0.0), 1.0)))

    def halo(t):                            # a volume's depth: a ring about the dot
        return ui.PAD_DOT_R + 4 + t * side * 0.15

    dot = at(px.norm, py.norm)
    # the crosshair through the dot, the value fill's red
    fill = ui.u32(ui.FILL)
    dl.add_line(imgui.ImVec2(dot.x, y + 1), imgui.ImVec2(dot.x, y + side - 1), fill, 2.0)
    dl.add_line(imgui.ImVec2(x + 1, dot.y), imgui.ImVec2(x + side - 1, dot.y), fill, 2.0)
    dl.push_clip_rect(r0, r1, True)
    if len(ps) > 2:
        dl.add_circle_filled(dot, halo(ps[2].norm), ui.u32(ui.FILL), 48)
        dl.add_circle(dot, halo(ps[2].norm), ui.u32(ui.RED), 48, 1.5)
    if any(p.modulated for p in ps):        # where the lanes have it now
        g = at(px.eff_norm, py.eff_norm)
        dl.add_line(dot, g, ui.u32(ui.GHOST), 1.5)
        if len(ps) > 2:
            dl.add_circle(g, halo(ps[2].eff_norm), ui.u32(ui.GHOST), 48, 1.5)
        dl.add_circle_filled(g, ui.PAD_DOT_R * 0.6, ui.u32(ui.GHOST), 24)
        panel.ghosts += 1
    dl.pop_clip_rect()
    dl.add_circle_filled(dot, ui.PAD_DOT_R, ui.u32(ui.RED), 32)
    dl.add_circle(dot, ui.PAD_DOT_R + (3 if active or hovered else 1.5),
                  ui.u32(ui.TEXT), 32, 2.0 if active or hovered else 1.5)


KNOB_SWEEP = 1.5 * math.pi     # radians the knob turns over its throw, the gap at the bottom


def knob(panel, k, a, p, x, y, words: str, room: float | None = None):
    """A small knob for param `a` (reading and writing `p`) at (x, y): a
    vertical drag turns it, a full throw over `ui.KNOB_THROW` px (⇧ held, a
    tenth); a double-click returns it to its detent. Its arc fills from
    the shape's origin; a lane's effective value is a white tick. Its
    words — `words`, its value — under it. It is the param's control: its
    `##<id>` (the driver finds it), menu, learn frame and tooltip. Returns
    its rect."""
    r = ui.KNOB_R
    cx, cy = x + r, y + r
    shape = shape_of(panel, p)
    imgui.set_cursor_screen_pos(imgui.ImVec2(x, y))
    imgui.invisible_button(f"##{a.id}", imgui.ImVec2(2 * r, 2 * r))
    active, hovered = imgui.is_item_active(), imgui.is_item_hovered()
    rect = (imgui.get_item_rect_min(), imgui.get_item_rect_max())
    if not _dim(panel):
        moved = False
        st = _held(panel, f"knob.{a.id}", active, lambda: (p.norm,))
        if st is not None:
            io = imgui.get_io()
            dt = -io.mouse_delta.y / ui.KNOB_THROW * (ui.FINE if io.key_shift else 1.0)
            if dt:
                st["t"][0] = min(max(st["t"][0] + dt, 0.0), 1.0)
                moved = _write_norm(p, st["t"][0])
        if hovered and imgui.is_mouse_double_clicked(0) and shape.detent is not None:
            moved = _write_norm(p, shape.detent) or moved
            if st is not None:              # the second press held on into a drag: from the detent
                st["t"][0] = shape.detent
        if moved:
            undo.by_hand(True)
    panel._tip(a)
    panel._ctx(a)
    panel._learn_frame(a)
    dl = k.dl
    start = math.pi / 2 + (2 * math.pi - KNOB_SWEEP) / 2     # bottom-left, clockwise

    def ang(t):
        return start + KNOB_SWEEP * min(max(t, 0.0), 1.0)

    ring = r - 3
    dl.path_arc_to(imgui.ImVec2(cx, cy), ring, ang(0), ang(1), 40)
    dl.path_stroke(ui.u32(ui.LINE), thickness=4.0)
    a0, a1 = sorted((ang(shape.origin), ang(p.norm)))
    if a1 - a0 > 1e-3:
        dl.path_arc_to(imgui.ImVec2(cx, cy), ring, a0, a1, 40)
        dl.path_stroke(ui.u32(ui.RED), thickness=4.0)
    for t in shape.notches:                 # a detent: a tick outside the ring
        u = ang(t)
        dl.add_line(imgui.ImVec2(cx + math.cos(u) * (r + 1), cy + math.sin(u) * (r + 1)),
                    imgui.ImVec2(cx + math.cos(u) * (r + 4), cy + math.sin(u) * (r + 4)),
                    ui.u32(ui.FAINT), 1.5)
    u = ang(p.norm)
    dl.add_circle_filled(imgui.ImVec2(cx, cy), ring - 5,
                         ui.u32(ui.LINE if not (active or hovered) else ui.FAINT), 24)
    dl.add_line(imgui.ImVec2(cx + math.cos(u) * 3, cy + math.sin(u) * 3),
                imgui.ImVec2(cx + math.cos(u) * (ring - 1), cy + math.sin(u) * (ring - 1)),
                ui.u32(ui.TEXT), 2.5)
    if p.modulated:
        g = ang(p.eff_norm)
        dl.add_line(imgui.ImVec2(cx + math.cos(g) * (ring - 4), cy + math.sin(g) * (ring - 4)),
                    imgui.ImVec2(cx + math.cos(g) * (ring + 3), cy + math.sin(g) * (ring + 3)),
                    ui.u32(ui.GHOST), 3.0)
        panel.ghosts += 1
    hh = head_h()
    # the readout, each line inside the knob's column `room`: its letter and
    # the base, then — a lane riding it — "→ effective" on a line of its own
    # (`base → effective` on one line runs past the column)
    room = ui.KNOB_COL if room is None else room
    col = ui.RED if p.modulated else ui.TEXT
    value = p.text()
    ty = y + 2 * r + PAD_LABEL_GAP
    lw = ui._micro_width(words)
    vw = ui._readout_width(value)
    if lw + vw + 4 <= room:                 # side by side, centred under the knob
        x0 = cx - (lw + 4 + vw) / 2
        text(dl, x0, ty, hh, words, "micro", ui.FONT_MICRO, ui.DIM)
        text(dl, x0 + lw + 4, ty, hh, value, "num", ui.FONT_NUM, col)
    else:
        _centred(dl, cx, ty, hh, value, room, col)
    if p.modulated:
        _centred(dl, cx, ty + hh, hh, f"→ {panel._eff_text(p)}", room, col)
    return rect


def _centred(dl, cx: float, y: float, h: float, s: str, room: float, col) -> None:
    """`s` in the readout face centred on `cx`, cut to `room` px."""
    imgui.push_font(ui._FONTS["num"], ui.FONT_NUM)
    s = ui.fit_text(s, room)
    w = imgui.calc_text_size(s).x
    imgui.pop_font()
    text(dl, cx - w / 2, y, h, s, "num", ui.FONT_NUM, col)


def inline_pad(panel, pids, label: str) -> dict:
    """`pad` the full width at the cursor, in imgui's flow (the fx strip's
    row for a `@pair` or `@volume`). Its knobs' rects, by param id."""
    k = ui_kit.begin(panel)
    x, y, w, _ = ui_kit.block(0.0)
    h = pad_h(w, len(pids))
    with _m("uictx").chrome(k):
        rects = pad(panel, k, list(pids), label, (x, y, w, h))
    ui_kit.end_block((x, y, w, h))
    return rects


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
    menu = _m("menu")
    cap = 2 * menu.PAD + SELECT_ROWS_MAX * menu.ITEM_H
    chosen, _open = _m("interact").select(
        k, pid, x, y + (h - ui.FIELD_ROW_H) / 2, w, names[cur] if 0 <= cur < len(names) else "",
        items, size=SELECT_SIZE, disabled=_dim(panel), max_h=cap)
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
    return slider_h() if panel._real(panel.reg[pid]).kind is Kind.CONTINUOUS else ui.FIELD_ROW_H


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
        # the kit's Switch, its target the whole row (`interact.switch`'s `row`)
        clicked, _out = _m("interact").switch(k, pid, x + (fh - sw) / 2, y + (fh - sh) / 2, on,
                                               size="sm", disabled=dim, row=(x, y, w, fh))
        panel._tip(a)
        panel._ctx(a)
        panel._learn_frame(a)
        panel._mod_dot(p)
        if words:
            gap = imgui.get_style().item_inner_spacing.x
            imgui.set_cursor_screen_pos(imgui.ImVec2(x + fh + gap, y))
            imgui.align_text_to_frame_padding()
            imgui.text_colored(ui.TEXT if on else ui.DIM, words)
    ui_kit.end_block((x, y, w, fh))
    if clicked and not dim:
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


SELECT_ROWS_MAX = 12      # a Select shows this many rows, and scrolls past them (menu.popup's max_h)


def inline_select(panel, pid: str, width: float = -1, tip: str | None = None) -> bool | None:
    """`Panel._combo` on the kit, in the room the stock combo had (`width`
    as `inline_slider`'s): the kit's Select, one frame tall, its list
    `SELECT_ROWS_MAX` rows tall and scrolling past them. True when another
    name is chosen (None is never returned now; `Panel._combo` keeps the
    branch for the stock combo without the kit)."""
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

CHIP_VARIANT = "outline"  # an unlit chip: the kit's outline Button, a border and a faint fill
CHIP_RADIUS = "sm"        # its corners (tokens.RADII): a button's, not a pill's


def chip(label: str, size=None, lit: bool = False, color=None, *, pad=None,
         pill: bool = False, icon: str | None = None, variant: str | None = None,
         reveal: float = 1.0, join=None) -> bool:
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
        _m("comp_button").chip_chrome(
            k, dl, x, y, w, h, variant or ("default" if lit else CHIP_VARIANT), hot=hot,
            down=down, focus_f=focus, disabled=dim, join=join,
            radius=h / 2 if pill else min(_m("tokens").RADII[CHIP_RADIUS], h / 2))
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
    imgui.push_style_var(imgui.StyleVar_.frame_padding, imgui.ImVec2(0, (fh - ui.FONT_NUM) / 2))
    imgui.push_style_var(imgui.StyleVar_.grab_min_size, thumb)
    imgui.push_font(ui._FONTS["num"], ui.FONT_NUM)
    try:
        with _m("uictx").chrome(k):
            changed, v = I.slider(k, key, x, y, track, fh, value, lo, hi, fine=False,
                                  fmt=shown.replace("%", "%%"),
                                  flags=imgui.SliderFlags_.logarithmic if log else 0,
                                  frac=min(max(t0, 0.0), 1.0), origin=origin, box=not beside)
    finally:
        imgui.pop_font()
        imgui.pop_style_var(2)
    if not beside:
        _box_words(k, x, y, w, fh, shown, font, size, col)
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
        undo.by_hand(True)                  # (typed into it)
    return changed, v
